#!/usr/bin/env python3
"""Build a Graphify knowledge graph through the authenticated local Codex CLI.

Graphify's headless extractor supports API-key backends and Claude CLI, but it has no Codex CLI
backend. This adapter keeps Graphify as the canonical detector/extractor/builder and supplies only
the missing subscription-backed semantic call. Source bytes are embedded in a bounded prompt;
Codex runs ephemerally in a disposable read-only directory with a closed JSON schema.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib.metadata
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twin_core.provider_adapters import codex_structured_with_usage  # noqa: E402

NODE_ID = re.compile(r"^[a-z0-9_]+$")
LINE_LOCATION = re.compile(r"^lines? ([1-9][0-9]*)(?:-([1-9][0-9]*))?$")
CONFIDENCE = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}
FILE_TYPES = {"code", "document", "paper", "image", "rationale", "concept"}
OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["nodes", "edges", "hyperedges"],
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id", "label", "file_type", "source_file", "source_location",
                    "source_url", "captured_at", "author", "contributor",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "file_type": {"type": "string", "enum": sorted(FILE_TYPES)},
                    "source_file": {"type": "string"},
                    "source_location": {"type": "string"},
                    "source_url": {"type": ["string", "null"]},
                    "captured_at": {"type": ["string", "null"]},
                    "author": {"type": ["string", "null"]},
                    "contributor": {"type": ["string", "null"]},
                },
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source", "target", "relation", "confidence", "confidence_score",
                    "source_file", "source_location", "weight",
                ],
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "relation": {"type": "string"},
                    "confidence": {"type": "string", "enum": sorted(CONFIDENCE)},
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "source_file": {"type": "string"},
                    "source_location": {"type": "string"},
                    "weight": {"type": "number"},
                },
            },
        },
        "hyperedges": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id", "label", "nodes", "relation", "confidence", "confidence_score",
                    "source_file",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "nodes": {"type": "array", "items": {"type": "string"}, "minItems": 3},
                    "relation": {"type": "string"},
                    "confidence": {
                        "type": "string", "enum": ["EXTRACTED", "INFERRED"]
                    },
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "source_file": {"type": "string"},
                },
            },
        },
    },
}


class GraphifyCodexRefusal(RuntimeError):
    """The local semantic extraction boundary refused an unsafe or invalid result."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _safe_relative(path: Path, root: Path, *, directory: bool = False) -> Path:
    absolute = Path(os.path.abspath(path))
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise GraphifyCodexRefusal("source escapes the admitted root") from exc
    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        info = os.lstat(current)
        if stat.S_ISLNK(info.st_mode):
            raise GraphifyCodexRefusal("source path contains a symlink")
        final = index == len(relative.parts) - 1
        if not final and not stat.S_ISDIR(info.st_mode):
            raise GraphifyCodexRefusal("source ancestor is not a directory")
        if final and directory != stat.S_ISDIR(info.st_mode):
            expected = "directory" if directory else "regular file"
            raise GraphifyCodexRefusal(f"source is not a {expected}")
        if final and not directory and not stat.S_ISREG(info.st_mode):
            raise GraphifyCodexRefusal("source is not a regular file")
    return relative


def _file_identity(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
        info.st_uid, info.st_size, info.st_mtime_ns,
    )


def _stable_read(path: Path, root: Path, root_descriptor: int) -> tuple[bytes, tuple[int, ...]]:
    relative = _safe_relative(path, root)
    expected_chain: list[tuple[int, ...]] = []
    current = root
    for part in relative.parts:
        current = current / part
        expected_chain.append(_file_identity(os.lstat(current)))
    directory_descriptor = os.dup(root_descriptor)
    try:
        for index, part in enumerate(relative.parts[:-1]):
            child = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_descriptor,
            )
            if _file_identity(os.fstat(child)) != expected_chain[index]:
                os.close(child)
                raise GraphifyCodexRefusal("source ancestor changed before descriptor admission")
            os.close(directory_descriptor)
            directory_descriptor = child
        descriptor = os.open(
            relative.name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_descriptor,
        )
        before = os.fstat(descriptor)
        if _file_identity(before) != expected_chain[-1]:
            raise GraphifyCodexRefusal("source changed before descriptor admission")
        if not stat.S_ISREG(before.st_mode):
            raise GraphifyCodexRefusal("source descriptor is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        if "descriptor" in locals():
            os.close(descriptor)
        os.close(directory_descriptor)
    identity = _file_identity(before)
    after_identity = _file_identity(after)
    if identity != after_identity:
        raise GraphifyCodexRefusal("source changed while it was being read")
    return b"".join(chunks), identity


def _publish_no_replace(staged: Path, output: Path) -> None:
    """Atomically publish a directory without replacing an existing destination."""
    if staged.parent.parent != output.parent:
        raise GraphifyCodexRefusal("staged graph is outside the selected output parent")
    parent_descriptor = os.open(
        output.parent,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        if sys.platform == "darwin":
            rename = getattr(libc, "renameatx_np", None)
            exclusive_flag = 4  # RENAME_EXCL
        elif sys.platform.startswith("linux"):
            rename = getattr(libc, "renameat2", None)
            exclusive_flag = 1  # RENAME_NOREPLACE
        else:
            rename = None
        if rename is None:
            raise GraphifyCodexRefusal("create-once graph publication is unavailable")
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        source_name = f"{staged.parent.name}/{staged.name}".encode()
        result = rename(parent_descriptor, source_name, parent_descriptor, output.name.encode(), exclusive_flag)
        if result != 0:
            error = ctypes.get_errno()
            if error in {errno.EEXIST, errno.ENOTEMPTY}:
                raise GraphifyCodexRefusal("output path appeared during graph construction")
            raise OSError(error, os.strerror(error))
    finally:
        os.close(parent_descriptor)


def _source_paths(files: Sequence[Path], root: Path) -> set[str]:
    paths: set[str] = set()
    for path in files:
        relative = _safe_relative(path, root)
        paths.add(relative.as_posix())
    return paths


def _line_location(value: Any, *, source_file: str, line_counts: Mapping[str, int]) -> None:
    if not isinstance(value, str):
        raise GraphifyCodexRefusal("semantic source location must be an exact line reference")
    match = LINE_LOCATION.fullmatch(value)
    if match is None:
        raise GraphifyCodexRefusal("semantic source location must use 'line N' or 'lines N-M'")
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if start > end or end > line_counts[source_file]:
        raise GraphifyCodexRefusal("semantic source location exceeds the admitted source")


def validate_semantic_result(
    value: Mapping[str, Any], *, admitted_sources: set[str], line_counts: Mapping[str, int]
) -> dict[str, Any]:
    if set(value) != {"nodes", "edges", "hyperedges"}:
        raise GraphifyCodexRefusal("semantic result fields do not match the closed schema")
    nodes = value["nodes"]
    edges = value["edges"]
    hyperedges = value["hyperedges"]
    if not all(isinstance(items, list) for items in (nodes, edges, hyperedges)):
        raise GraphifyCodexRefusal("semantic graph collections must be arrays")

    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise GraphifyCodexRefusal("semantic node must be an object")
        expected = {
            "id", "label", "file_type", "source_file", "source_location", "source_url",
            "captured_at", "author", "contributor",
        }
        if set(node) != expected:
            raise GraphifyCodexRefusal("semantic node fields do not match the closed schema")
        identifier = node["id"]
        if (
            not isinstance(identifier, str)
            or not NODE_ID.fullmatch(identifier)
            or identifier in node_ids
        ):
            raise GraphifyCodexRefusal("semantic node identity is invalid or duplicated")
        if not isinstance(node["label"], str) or not node["label"]:
            raise GraphifyCodexRefusal("semantic node label is invalid")
        if node["file_type"] not in FILE_TYPES:
            raise GraphifyCodexRefusal("semantic node file type is invalid")
        if node["source_file"] not in admitted_sources:
            raise GraphifyCodexRefusal("semantic node cites an unadmitted source")
        _line_location(
            node["source_location"],
            source_file=node["source_file"],
            line_counts=line_counts,
        )
        node_ids.add(identifier)

    for edge in edges:
        if not isinstance(edge, dict):
            raise GraphifyCodexRefusal("semantic edge must be an object")
        expected = {
            "source", "target", "relation", "confidence", "confidence_score", "source_file",
            "source_location", "weight",
        }
        if set(edge) != expected:
            raise GraphifyCodexRefusal("semantic edge fields do not match the closed schema")
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            raise GraphifyCodexRefusal("semantic edge references an unknown node")
        if edge["confidence"] not in CONFIDENCE:
            raise GraphifyCodexRefusal("semantic edge confidence class is invalid")
        score = edge["confidence_score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
            raise GraphifyCodexRefusal("semantic edge confidence score is invalid")
        if edge["source_file"] not in admitted_sources:
            raise GraphifyCodexRefusal("semantic edge cites an unadmitted source")
        _line_location(
            edge["source_location"],
            source_file=edge["source_file"],
            line_counts=line_counts,
        )

    for hyperedge in hyperedges:
        if not isinstance(hyperedge, dict):
            raise GraphifyCodexRefusal("semantic hyperedge must be an object")
        expected = {
            "id", "label", "nodes", "relation", "confidence", "confidence_score", "source_file"
        }
        if set(hyperedge) != expected:
            raise GraphifyCodexRefusal("semantic hyperedge fields do not match the closed schema")
        members = hyperedge.get("nodes")
        if (
            not isinstance(members, list)
            or len(members) < 3
            or any(member not in node_ids for member in members)
        ):
            raise GraphifyCodexRefusal("semantic hyperedge membership is invalid")
        if hyperedge.get("source_file") not in admitted_sources:
            raise GraphifyCodexRefusal("semantic hyperedge cites an unadmitted source")
    return json.loads(_canonical(value))


def codex_semantic_extract(
    files: Sequence[Path], *, root: Path, deep_mode: bool, model: str
) -> tuple[dict[str, Any], Mapping[str, int]]:
    from graphify.llm import _extraction_system

    root = Path(os.path.abspath(root))
    admitted = _source_paths(files, root)
    line_counts: dict[str, int] = {}
    prompt_parts: list[str] = []
    for path in files:
        relative = _safe_relative(path, root).as_posix()
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content[:20000].splitlines()
        line_counts[relative] = max(1, len(lines))
        numbered = "\n".join(f"{number}: {line}" for number, line in enumerate(lines, 1))
        prompt_parts.append(f"=== {relative} ===\n{numbered}")
    prompt = (
        _extraction_system(deep=deep_mode)
        + "\n\n"
        + "\n\n".join(prompt_parts)
        + "\n\nReturn only the closed extraction JSON object. Every semantic node and edge "
        "must cite an exact source_file and a 1-based source_location formatted as 'line N' "
        "or 'lines N-M'."
    )
    completed = codex_structured_with_usage(
        prompt,
        schema=OUTPUT_SCHEMA,
        timeout=600,
        model=model,
        reasoning_effort="low",
    )
    if completed is None:
        raise GraphifyCodexRefusal("authenticated Codex semantic worker failed")
    result, usage = completed
    return validate_semantic_result(
        result, admitted_sources=admitted, line_counts=line_counts
    ), usage


def _git_identity(root: Path) -> dict[str, Any] | None:
    def run(*args: str) -> bytes:
        proc = subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", *args],
            cwd=root,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if proc.returncode:
            raise GraphifyCodexRefusal(f"Git identity command failed: {' '.join(args)}")
        return proc.stdout

    probe = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=root, capture_output=True, timeout=30
    )
    if probe.returncode:
        return None
    repository = Path(probe.stdout.decode().strip()).resolve(strict=True)
    status = run("status", "--porcelain=v1", "-z", "--untracked-files=all")
    return {
        "repository": str(repository),
        "commit": run("rev-parse", "HEAD").decode().strip(),
        "tree": run("rev-parse", "HEAD^{tree}").decode().strip(),
        "status_sha256": _sha256(status),
        "status_bytes": len(status),
    }


def _validate_directory_tree(path: Path, root: Path) -> None:
    _safe_relative(path, root, directory=True)
    for current, directories, files in os.walk(path, followlinks=False):
        current_path = Path(current)
        _safe_relative(current_path, root, directory=True)
        for name in directories:
            _safe_relative(current_path / name, root, directory=True)
        for name in files:
            _safe_relative(current_path / name, root)


def _command_version(command: Sequence[str]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode:
        raise GraphifyCodexRefusal(f"runtime identity command failed: {' '.join(command)}")
    return (completed.stdout or completed.stderr).strip()


def _build_snapshot(
    source: Path,
    snapshot: Path,
    output: Path,
    *,
    model: str,
    deep_mode: bool,
    original_detection: Mapping[str, Any],
    records: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    from graphify.build import build_from_json
    from graphify.cluster import cluster, score_all
    from graphify.export import to_html, to_json
    from graphify.extract import extract
    from graphify.report import generate
    from graphify.analyze import god_nodes, surprising_connections, suggest_questions

    code_files = [Path(record["path"]) for record in records if record["category"] == "code"]
    semantic_files = [
        snapshot / record["path"]
        for record in records
        if record["category"] in {"document", "paper"}
    ]
    if not code_files and not semantic_files:
        raise GraphifyCodexRefusal("no supported safe sources found")

    if code_files:
        previous_directory = Path.cwd()
        try:
            os.chdir(snapshot)
            ast = extract(
                code_files,
                cache_root=Path(".graphify-cache"),
                parallel=False,
            )
        finally:
            os.chdir(previous_directory)
    else:
        ast = {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0}
    semantic, usage = (
        codex_semantic_extract(semantic_files, root=snapshot, deep_mode=deep_mode, model=model)
        if semantic_files
        else (
            {"nodes": [], "edges": [], "hyperedges": []},
            {"cached_input_tokens": 0, "input_tokens": 0, "output_tokens": 0},
        )
    )
    seen = {node["id"] for node in ast["nodes"]}
    nodes = list(ast["nodes"])
    for node in semantic["nodes"]:
        if node["id"] not in seen:
            nodes.append(node)
            seen.add(node["id"])
    extraction = {
        "nodes": nodes,
        "edges": ast["edges"] + semantic["edges"],
        "hyperedges": semantic["hyperedges"],
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
    }
    graph = build_from_json(extraction, directed=True)
    if graph.number_of_nodes() == 0:
        raise GraphifyCodexRefusal("Graphify extraction produced an empty graph")
    communities = cluster(graph)
    cohesion = score_all(graph, communities)
    labels = {community: f"Community {community}" for community in communities}
    questions = suggest_questions(graph, communities, labels)
    report = generate(
        graph,
        communities,
        cohesion,
        labels,
        god_nodes(graph),
        surprising_connections(graph, communities),
        original_detection,
        {"input": usage["input_tokens"], "output": usage["output_tokens"]},
        str(source),
        suggested_questions=questions,
    )

    output.mkdir(parents=True, mode=0o700)
    graph_dir = output / "graphify-out"
    graph_dir.mkdir(mode=0o700)
    extraction_path = graph_dir / ".graphify_extract.json"
    extraction_path.write_bytes(_canonical(extraction))
    graph_path = graph_dir / "graph.json"
    to_json(graph, communities, str(graph_path))
    html_path = graph_dir / "graph.html"
    to_html(graph, communities, str(html_path), labels)
    report_path = graph_dir / "GRAPH_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    source_manifest = [
        {
            "category": record["category"],
            "path": record["path"],
            "sha256": record["sha256"],
            "bytes": record["bytes"],
        }
        for record in records
    ]
    script_path = Path(__file__).resolve(strict=True)
    provider_path = (ROOT / "twin_core/provider_adapters.py").resolve(strict=True)
    manifest = {
        "schema": "giga.graphify-codex-checkpoint.v1",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_root": str(source),
        "source_identity": _git_identity(source),
        "backend": (
            {"name": "codex-cli", "model": model, "reasoning_effort": "low"}
            if semantic_files else {"name": "graphify-ast", "model": None, "reasoning_effort": None}
        ),
        "token_usage": dict(usage),
        "implementation": {
            "adapter_git": _git_identity(ROOT),
            "codex_cli_version": (
                _command_version(["codex", "--version"]) if semantic_files else None
            ),
            "graphify_version": importlib.metadata.version("graphifyy"),
            "provider_adapter_sha256": _sha256(provider_path.read_bytes()),
            "python_version": sys.version,
            "script_sha256": _sha256(script_path.read_bytes()),
        },
        "skipped_sensitive_count": len(original_detection.get("skipped_sensitive", [])),
        "sources": source_manifest,
        "graph": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "communities": len(communities),
            "directed": True,
            "sha256": _sha256(graph_path.read_bytes()),
            "html_sha256": _sha256(html_path.read_bytes()),
            "extraction_sha256": _sha256(extraction_path.read_bytes()),
        },
        "report_sha256": _sha256(report_path.read_bytes()),
    }
    manifest_path = graph_dir / "MANIFEST.json"
    manifest_path.write_bytes(_canonical(manifest))
    for path in graph_dir.iterdir():
        if path.is_file():
            os.chmod(path, 0o600)
    return manifest


def build_graph(source: Path, output: Path, *, model: str, deep_mode: bool) -> dict[str, Any]:
    from graphify.detect import detect
    from graphify.extract import collect_files

    supplied_source = Path(os.path.abspath(source))
    source_info = os.lstat(supplied_source)
    if stat.S_ISLNK(source_info.st_mode) or not stat.S_ISDIR(source_info.st_mode):
        raise GraphifyCodexRefusal("source root must be a non-symlink directory")
    source = supplied_source.resolve(strict=True)
    output = Path(os.path.abspath(output))
    if os.path.lexists(output):
        raise GraphifyCodexRefusal("output path already exists; refusing to overwrite a graph")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise GraphifyCodexRefusal("output parent must be an existing non-symlink directory")
    source_descriptor = os.open(
        source,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
    )
    source_identity = _file_identity(os.fstat(source_descriptor))
    if source_identity != _file_identity(os.lstat(source)):
        os.close(source_descriptor)
        raise GraphifyCodexRefusal("source root changed before descriptor admission")
    try:
        detection = detect(source)
        detected = detection.get("files", {})
        if detected.get("image") or detected.get("video"):
            raise GraphifyCodexRefusal("Codex backend currently admits text/code sources only")
        classified: dict[str, str] = {}
        for category in ("code", "document", "paper"):
            for raw in detected.get(category, []):
                path = Path(os.path.abspath(raw))
                info = os.lstat(path)
                if stat.S_ISDIR(info.st_mode):
                    _validate_directory_tree(path, source)
                    candidates = collect_files(path)
                else:
                    candidates = [path]
                for candidate in candidates:
                    relative = _safe_relative(candidate, source).as_posix()
                    previous = classified.setdefault(relative, category)
                    if previous != category:
                        raise GraphifyCodexRefusal(
                            "source has conflicting Graphify classifications"
                        )
        if not classified:
            raise GraphifyCodexRefusal("no supported safe sources found")

        with tempfile.TemporaryDirectory(prefix="giga-graphify-", dir=output.parent) as temporary:
            temporary_root = Path(temporary)
            snapshot = temporary_root / "source"
            snapshot.mkdir(mode=0o700)
            records: list[dict[str, Any]] = []
            retained: dict[str, tuple[bytes, tuple[int, ...]]] = {}
            for relative, category in sorted(classified.items()):
                original = source / relative
                data, identity = _stable_read(original, source, source_descriptor)
                retained[relative] = (data, identity)
                destination = snapshot / relative
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                destination.write_bytes(data)
                os.chmod(destination, 0o600)
                records.append({
                    "category": category,
                    "path": relative,
                    "sha256": _sha256(data),
                    "bytes": len(data),
                })
            staged_output = temporary_root / "result"
            manifest = _build_snapshot(
                source,
                snapshot,
                staged_output,
                model=model,
                deep_mode=deep_mode,
                original_detection=detection,
                records=records,
            )
            if _file_identity(os.fstat(source_descriptor)) != source_identity:
                raise GraphifyCodexRefusal("source root changed during graph construction")
            if _file_identity(os.lstat(source)) != source_identity:
                raise GraphifyCodexRefusal("source root path changed during graph construction")
            for relative, (expected_data, expected_identity) in retained.items():
                current_data, current_identity = _stable_read(
                    source / relative, source, source_descriptor
                )
                if current_data != expected_data or current_identity != expected_identity:
                    raise GraphifyCodexRefusal("source changed during graph construction")
            _publish_no_replace(staged_output, output)
        return manifest
    finally:
        os.close(source_descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--deep", action="store_true")
    args = parser.parse_args()
    try:
        manifest = build_graph(args.source, args.out, model=args.model, deep_mode=args.deep)
    except (GraphifyCodexRefusal, OSError, ValueError) as exc:
        print(f"graphify Codex backend refused: {exc}", file=os.sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
