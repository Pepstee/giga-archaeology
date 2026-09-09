"""Forced, deterministic context projection and Graphify-compatible graph refresh."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

from .memory_gate import _require_memory_gate, _require_corpus_access, _safe_directory
from .integrity import authority_path

SCHEMA = "giga.knowledge-refresh.v1"
CONTEXT_SCHEMA = "giga.context-projection.v1"
LINK = re.compile(r"\[\[([^\]]+)\]\]")
GraphifyRunner = Callable[[Path, Path], None]


class KnowledgeRefreshError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


CORE_SOURCE_FILES = (
    "__init__.py", "memory_gate.py", "memory_validation.py", "memory_proposals.py",
    "context_compiler.py", "knowledge_refresh.py", "telegram_pipeline.py",
    "integrity.py", "constitutional_authority.py",
)


def _code_sources() -> list[Path]:
    package = Path(__file__).absolute().parent
    paths = []
    for name in CORE_SOURCE_FILES:
        path = authority_path(package, name)
        if not path.is_file():
            raise KnowledgeRefreshError(f"executing source is missing: {name}")
        paths.append(path)
    if not paths:
        raise KnowledgeRefreshError("executing source identity cannot be empty")
    return paths


def _core_source_sha256(root: Path) -> str:
    rows = [{"path": f"twin_core/{path.name}", "sha256": _sha256(path)} for path in _code_sources()]
    return hashlib.sha256(_canonical(rows)).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    absolute = path.absolute()
    authority_path(Path(absolute.anchor), absolute.relative_to(absolute.anchor).as_posix())
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    rendered = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _graphify_paths(root: Path, private_output: Path) -> tuple[Path, Path]:
    absolute = private_output.absolute()
    anchor = Path(absolute.anchor)
    try:
        output = authority_path(anchor, absolute.relative_to(anchor).as_posix())
    except ValueError as exc:
        raise KnowledgeRefreshError("unsafe private output path") from exc
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise KnowledgeRefreshError("private output must be separate from the corpus/source root")
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output, 0o700)
    generated = output / "graphify"
    authority_path(output, "graphify")
    generated.mkdir(exist_ok=True, mode=0o700)
    return generated, output


def _run_graphify(root: Path, generated: Path) -> None:
    """Deterministically extract only the explicit executing Python source closure."""
    try:
        from graphify.extract import extract
    except ImportError as exc:
        raise KnowledgeRefreshError("deterministic code refresh requires the optional graphify runtime") from exc
    with tempfile.TemporaryDirectory(prefix="giga-private-code-graph-") as folder:
        stage = Path(folder).resolve()
        sources = []
        for path in _code_sources():
            destination = stage / path.name
            shutil.copy2(path, destination)
            sources.append(destination)
        graph = extract(sources, cache_root=stage / "cache", parallel=False)
        if not graph.get("nodes"):
            raise KnowledgeRefreshError("deterministic code extraction produced no nodes")
        for item in graph.get("nodes", []) + graph.get("edges", []):
            if item.get("source_file"):
                item["source_file"] = f"twin_core/{Path(item['source_file']).name}"
        _atomic_json(generated / "graph.json", graph)


def _context_projection(root: Path, gate: dict[str, Any]) -> dict[str, Any]:
    context = root / "CONTEXT.md"
    protocol = root / "CONTEXT_PROTOCOL.md"
    for path in (context, protocol):
        if not path.is_file() or path.is_symlink():
            raise KnowledgeRefreshError(f"canonical context source is missing or unsafe: {path.name}")
    active = [
        {"path": relative, "sha256": _sha256(root / relative)}
        for relative in gate["active_entry_paths"]
    ]
    projection: dict[str, Any] = {
        "schema": CONTEXT_SCHEMA,
        "canonical_context": {"path": "CONTEXT.md", "sha256": _sha256(context)},
        "context_protocol": {"path": "CONTEXT_PROTOCOL.md", "sha256": _sha256(protocol)},
        "memory_snapshot_sha256": gate["input_hashes"]["snapshot_sha256"],
        "active_truth_sha256": gate["input_hashes"]["active_truth_sha256"],
        "active_entries": active,
        "canonical_context_auto_mutated": False,
        "operator_review_required_for_canonical_change": True,
    }
    projection["projection_sha256"] = hashlib.sha256(_canonical(projection)).hexdigest()
    return projection


def _augment_graph(root: Path, graph_path: Path, projection: dict[str, Any]) -> dict[str, Any]:
    if not graph_path.is_file() or graph_path.is_symlink():
        raise KnowledgeRefreshError("graphify did not produce a safe graph.json")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = [
        node for node in graph.get("nodes", [])
        if not str(node.get("id", "")).startswith("giga-memory:")
        and node.get("id") != "giga-context:canonical"
    ]
    links = [
        link for link in graph.get("links", graph.get("edges", []))
        if not str(link.get("source", "")).startswith("giga-memory:")
        and not str(link.get("target", "")).startswith("giga-memory:")
        and link.get("source") != "giga-context:canonical"
        and link.get("target") != "giga-context:canonical"
    ]
    active_slugs = {
        Path(item["path"]).stem: item for item in projection["active_entries"]
    }
    nodes.append({
        "id": "giga-context:canonical",
        "label": "CONTEXT.md (canonical)",
        "file_type": "context",
        "source_file": "CONTEXT.md",
        "source_location": "L1",
        "confidence": "EXTRACTED",
    })
    for slug, item in sorted(active_slugs.items()):
        node_id = f"giga-memory:{slug}"
        path = root / item["path"]
        nodes.append({
            "id": node_id,
            "label": slug,
            "file_type": "memory",
            "source_file": item["path"],
            "source_location": "L1",
            "sha256": item["sha256"],
            "confidence": "EXTRACTED",
        })
        links.append({
            "source": "giga-context:canonical",
            "target": node_id,
            "relation": "active_truth_includes",
            "context": "mandatory memory gate active set",
            "confidence": "EXTRACTED",
            "source_file": item["path"],
            "source_location": "L1",
            "weight": 1.0,
        })
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in sorted(set(LINK.findall(text)) & active_slugs.keys()):
            links.append({
                "source": node_id,
                "target": f"giga-memory:{target}",
                "relation": "memory_link",
                "context": "canonical wiki-link",
                "confidence": "EXTRACTED",
                "source_file": item["path"],
                "source_location": "L1",
                "weight": 1.0,
            })
    graph["nodes"] = sorted(nodes, key=lambda item: str(item.get("id", "")))
    graph["links"] = sorted(
        links,
        key=lambda item: (
            str(item.get("source", "")), str(item.get("target", "")),
            str(item.get("relation", "")), str(item.get("source_file", "")),
        ),
    )
    graph.pop("edges", None)
    graph["giga_refresh"] = {
        "schema": SCHEMA,
        "projection_sha256": projection["projection_sha256"],
        "memory_snapshot_sha256": projection["memory_snapshot_sha256"],
        "active_truth_sha256": projection["active_truth_sha256"],
        "active_memory_nodes": len(active_slugs),
        "core_source_sha256": _core_source_sha256(root),
        "graphify_mode": "deterministic-code-update+active-memory-overlay",
    }
    graph["giga_refresh"]["graph_payload_sha256"] = hashlib.sha256(
        _canonical(graph)
    ).hexdigest()
    _atomic_json(graph_path, graph)
    return graph


def _refresh_knowledge(
    root: Path,
    *,
    private_output: Path,
    graphify_runner: GraphifyRunner | None = None,
) -> dict[str, Any]:
    """Refresh both derived context and graph; failure prevents a success claim."""
    root = _safe_directory(root)
    gate = _require_memory_gate(root, "pre-context")
    projection = _context_projection(root, gate)
    generated, output = _graphify_paths(root, private_output)
    (graphify_runner or _run_graphify)(root, generated)
    graph = _augment_graph(root, generated / "graph.json", projection)
    context_path = authority_path(output, "context/current.json")
    _atomic_json(context_path, projection)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "result": "passed",
        "checked_at": gate["checked_at"],
        "projection_sha256": projection["projection_sha256"],
        "graph_payload_sha256": graph["giga_refresh"]["graph_payload_sha256"],
        "memory_snapshot_sha256": projection["memory_snapshot_sha256"],
        "active_truth_sha256": projection["active_truth_sha256"],
        "active_memory_nodes": graph["giga_refresh"]["active_memory_nodes"],
        "core_source_sha256": graph["giga_refresh"]["core_source_sha256"],
    }
    receipt["receipt_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    _atomic_json(
        output / "context/refresh-receipts"
        / f"{receipt['receipt_sha256']}.json",
        receipt,
    )
    return receipt


def _validate_knowledge_refresh(root: Path, *, private_output: Path) -> dict[str, Any]:
    root = _safe_directory(root)
    gate = _require_memory_gate(root, "pre-context")
    expected = _context_projection(root, gate)
    generated, output = _graphify_paths(root, private_output)
    context_path = authority_path(output, "context/current.json")
    graph_path = authority_path(output, "graphify/graph.json")
    findings: list[str] = []
    try:
        current = json.loads(context_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        current = {}
        findings.append("context-projection-missing-or-invalid")
    if current != expected:
        findings.append("context-projection-stale")
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        graph = {}
        findings.append("knowledge-graph-missing-or-invalid")
    metadata = graph.get("giga_refresh", {})
    if metadata.get("projection_sha256") != expected["projection_sha256"]:
        findings.append("knowledge-graph-stale")
    if metadata.get("core_source_sha256") != _core_source_sha256(root):
        findings.append("knowledge-graph-code-source-stale")
    if metadata.get("graph_payload_sha256"):
        payload = json.loads(json.dumps(graph))
        payload["giga_refresh"].pop("graph_payload_sha256", None)
        if hashlib.sha256(_canonical(payload)).hexdigest() != metadata["graph_payload_sha256"]:
            findings.append("knowledge-graph-payload-hash")
    else:
        findings.append("knowledge-graph-payload-hash-missing")
    expected_nodes = {f"giga-memory:{Path(item['path']).stem}" for item in expected["active_entries"]}
    actual_nodes = {
        str(item.get("id")) for item in graph.get("nodes", [])
        if str(item.get("id", "")).startswith("giga-memory:")
    }
    if actual_nodes != expected_nodes:
        findings.append("knowledge-graph-active-set-mismatch")
    return {
        "schema": SCHEMA,
        "result": "passed" if not findings else "failed",
        "findings": sorted(set(findings)),
        "projection_sha256": expected["projection_sha256"],
        "memory_snapshot_sha256": expected["memory_snapshot_sha256"],
        "active_truth_sha256": expected["active_truth_sha256"],
    }


def _ensure_knowledge_current(root: Path, *, private_output: Path, graphify_runner: GraphifyRunner | None = None) -> dict[str, Any]:
    status = _validate_knowledge_refresh(root, private_output=private_output)
    if status["result"] == "passed":
        return status
    _refresh_knowledge(root, private_output=private_output, graphify_runner=graphify_runner)
    status = _validate_knowledge_refresh(root, private_output=private_output)
    if status["result"] != "passed":
        raise KnowledgeRefreshError(
            "knowledge refresh did not converge: " + ", ".join(status["findings"])
        )
    return status


def refresh_knowledge(root: Path, *, private_output: Path, **kwargs: Any) -> dict[str, Any]:
    _require_corpus_access()
    return _refresh_knowledge(root, private_output=private_output, **kwargs)


def validate_knowledge_refresh(root: Path, *, private_output: Path) -> dict[str, Any]:
    _require_corpus_access()
    return _validate_knowledge_refresh(root, private_output=private_output)


def ensure_knowledge_current(root: Path, *, private_output: Path, **kwargs: Any) -> dict[str, Any]:
    _require_corpus_access()
    return _ensure_knowledge_current(root, private_output=private_output, **kwargs)
