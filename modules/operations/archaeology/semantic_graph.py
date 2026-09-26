"""Privacy-gated, local-only Graphify semantic navigation layer.

The deterministic inventory is the complete file map.  This module projects
only inventory-admitted content into a private workspace, invokes Graphify
through an explicitly loopback OpenAI-compatible endpoint, validates every
reported source location, and atomically publishes an immutable graph run.

Code and structured JSON are extracted structurally in every run.  Prose is
added incrementally because local inference is intentionally bounded.  Until
all supported prose is covered the manifest says ``PARTIAL``; the graph remains
useful but never pretends to be complete or authoritative.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import shutil
import sqlite3
import stat
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .evidence import canonical_bytes, seal_document, sha256_bytes, validate_self_hash
from .navigation_inventory import NavigationRun, _replace_atomic, current_navigation_run


SEMANTIC_SCHEMA = "giga.navigation.semantic-graph-manifest.v1"
SEMANTIC_POINTER_SCHEMA = "giga.navigation.semantic-current-pointer.v1"
SEMANTIC_LOCATE_SCHEMA = "giga.navigation.semantic-locate-result.v1"
LEGACY_ARCHIVE_SCHEMA = "giga.navigation.legacy-graph-archive.v1"
GRAPHIFY_CODE_SUFFIXES = frozenset(
    {
        ".c",
        ".cc",
        ".cpp",
        ".go",
        ".h",
        ".hpp",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".kt",
        ".kts",
        ".lua",
        ".mjs",
        ".php",
        ".py",
        ".pyi",
        ".rb",
        ".rs",
        ".sh",
        ".sql",
        ".swift",
        ".ts",
        ".tsx",
        ".zsh",
    }
)
GRAPHIFY_DOCUMENT_SUFFIXES = frozenset(
    {".html", ".md", ".rst", ".txt", ".yaml", ".yml"}
)
GRAPHIFY_SUPPORTED_SUFFIXES = GRAPHIFY_CODE_SUFFIXES | GRAPHIFY_DOCUMENT_SUFFIXES
CONFIDENCE_VALUES = frozenset({"EXTRACTED", "INFERRED"})
LOCATION_RE = re.compile(r"^L?(?P<start>[1-9][0-9]*)(?:-L?(?P<end>[1-9][0-9]*))?$")
EXTERNAL_PROVIDER_ENV = (
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_PROFILE",
    "AZURE_OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "MOONSHOT_API_KEY",
    "OPENAI_API_KEY",
)


class SemanticGraphError(ValueError):
    """The semantic graph cannot be produced or authenticated safely."""


def _tree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise SemanticGraphError(f"legacy graph contains a symlink: {relative}")
        if stat.S_ISDIR(metadata.st_mode):
            entries.append(
                {
                    "path": relative,
                    "kind": "directory",
                    "mode": stat.S_IMODE(metadata.st_mode),
                }
            )
        elif stat.S_ISREG(metadata.st_mode):
            digest, size = _file_sha256(path)
            entries.append(
                {
                    "path": relative,
                    "kind": "regular",
                    "mode": stat.S_IMODE(metadata.st_mode),
                    "size": size,
                    "sha256": digest,
                }
            )
        else:
            raise SemanticGraphError(
                f"legacy graph contains an unsupported file: {relative}"
            )
    return entries


@dataclass(frozen=True)
class GraphifyConfig:
    python: Path = (
        Path.home() / "Documents/developer-tools/giga-graphify-local/.venv/bin/python"
    )
    endpoint: str = "http://127.0.0.1:1235/v1"
    model: str = "mlx-community/Qwen2.5-3B-Instruct-4bit"
    token_budget: int = 6000
    max_output_tokens: int = 4096
    max_new_documents: int = 1
    max_workers: int = 4
    request_timeout_seconds: int = 600
    process_timeout_seconds: int = 780

    def __post_init__(self) -> None:
        if not self.model or "\x00" in self.model:
            raise SemanticGraphError("model must be a non-empty identifier")
        for name in (
            "token_budget",
            "max_output_tokens",
            "max_workers",
            "request_timeout_seconds",
            "process_timeout_seconds",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or value <= 0:
                raise SemanticGraphError(f"{name} must be positive")
        if isinstance(self.max_new_documents, bool) or self.max_new_documents < 0:
            raise SemanticGraphError("max_new_documents must be zero or positive")
        _local_endpoint(self.endpoint)


@dataclass(frozen=True)
class SemanticRun:
    run_directory: Path
    manifest: Mapping[str, Any]


@dataclass(frozen=True)
class _File:
    path: str
    sha256: str
    size: int
    mtime_ns: int
    ctime_ns: int
    mode: int
    suffix: str


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _file_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _local_endpoint(value: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/v1"
    ):
        raise SemanticGraphError(
            "Graphify endpoint must be exact loopback HTTP with a /v1 path"
        )
    try:
        _ = parsed.port
    except ValueError as exc:
        raise SemanticGraphError("Graphify endpoint has an invalid port") from exc
    if parsed.port is None:
        raise SemanticGraphError("Graphify endpoint must include an explicit port")
    return parsed


def _verify_local_model(config: GraphifyConfig) -> dict[str, Any]:
    _local_endpoint(config.endpoint)
    request = urllib.request.Request(
        f"{config.endpoint.rstrip('/')}/models",
        headers={"Accept": "application/json"},
        method="GET",
    )

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
            raise SemanticGraphError("local model endpoint attempted a redirect")

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=10) as response:  # noqa: S310 - loopback fixed
            raw = response.read(1024 * 1024 + 1)
            status = response.status
    except (OSError, urllib.error.URLError) as exc:
        raise SemanticGraphError(f"local model endpoint is unavailable: {exc}") from exc
    if status != 200 or len(raw) > 1024 * 1024:
        raise SemanticGraphError(
            "local model endpoint returned an invalid model response"
        )
    try:
        payload = json.loads(raw.decode("utf-8", "strict"))
        identifiers = sorted(
            item["id"]
            for item in payload["data"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )
    except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticGraphError(
            "local model endpoint returned malformed JSON"
        ) from exc
    if config.model not in identifiers:
        raise SemanticGraphError(
            f"configured local model is not loaded: {config.model}"
        )
    return {
        "endpoint": config.endpoint,
        "model": config.model,
        "advertised_models_sha256": sha256_bytes(canonical_bytes(identifiers)),
        "advertised_models_count": len(identifiers),
    }


def _private_store(path: Path) -> Path:
    resolved = path.resolve(strict=False)
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = resolved.lstat()
    if resolved.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise SemanticGraphError("semantic store must be a real directory")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise SemanticGraphError("semantic store must be current-UID mode 0700")
    return resolved


def _inventory_files(inventory: NavigationRun) -> tuple[Path, dict[str, _File], int]:
    root = Path(inventory.manifest["root"]["path"]).resolve(strict=True)
    database = inventory.run_directory / inventory.manifest["database"]["path"]
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """SELECT path,content_sha256,size_bytes,mtime_ns,ctime_ns,mode,suffix
               FROM files
               WHERE semantic_eligible = 1
                 AND hash_status IN ('hashed','reused')
                 AND kind = 'regular'
                 AND size_bytes > 0
               ORDER BY path"""
        ).fetchall()
    finally:
        connection.close()
    result = {
        row[0]: _File(
            path=row[0],
            sha256=row[1],
            size=row[2],
            mtime_ns=row[3],
            ctime_ns=row[4],
            mode=row[5],
            suffix=row[6],
        )
        for row in rows
        if row[6] in GRAPHIFY_SUPPORTED_SUFFIXES
    }
    return root, result, len(rows) - len(result)


def _read_semantic_current(store: Path) -> SemanticRun | None:
    pointer_path = store / "CURRENT.json"
    if not pointer_path.exists():
        return None
    try:
        pointer_raw = pointer_path.read_bytes()
        pointer = json.loads(pointer_raw)
        validate_self_hash(pointer)
        if pointer.get("schema") != SEMANTIC_POINTER_SCHEMA:
            raise SemanticGraphError("unsupported semantic pointer schema")
        run = store / "runs" / pointer["run_id"]
        manifest_raw = (run / "manifest.json").read_bytes()
        if sha256_bytes(manifest_raw) != pointer["manifest_file_sha256"]:
            raise SemanticGraphError("semantic manifest file hash mismatch")
        manifest = json.loads(manifest_raw)
        validate_self_hash(manifest)
        if manifest["receipt_sha256"] != pointer["manifest_receipt_sha256"]:
            raise SemanticGraphError("semantic manifest receipt mismatch")
        graph = run / manifest["graph"]["path"]
        graph_sha, _ = _file_sha256(graph)
        if graph_sha != manifest["graph"]["sha256"]:
            raise SemanticGraphError("semantic graph hash mismatch")
        raw_graph = run / manifest["graph"]["raw_path"]
        raw_graph_sha, _ = _file_sha256(raw_graph)
        if raw_graph_sha != manifest["graph"]["raw_sha256"]:
            raise SemanticGraphError("raw semantic graph hash mismatch")
        return SemanticRun(run_directory=run, manifest=manifest)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, SemanticGraphError):
            raise
        raise SemanticGraphError(f"current semantic graph is unusable: {exc}") from exc


def current_semantic_run(store: Path) -> SemanticRun:
    current = _read_semantic_current(store.resolve(strict=True))
    if current is None:
        raise SemanticGraphError("no current semantic graph exists")
    return current


def archive_legacy_graph(legacy_path: Path, semantic_store: Path) -> dict[str, Any]:
    """Move a legacy ignored graph into private stale evidence and install a stable link."""
    semantic_store = _private_store(semantic_store)
    current_semantic_run(semantic_store)
    legacy_path = legacy_path.absolute()
    metadata = legacy_path.lstat()
    if legacy_path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise SemanticGraphError("legacy graph path must be a real directory")
    if os.path.commonpath((str(legacy_path), str(semantic_store))) == str(legacy_path):
        raise SemanticGraphError("semantic store cannot be inside the legacy graph")
    entries = _tree_entries(legacy_path)
    graph_path = legacy_path / "graph.json"
    try:
        old_graph = json.loads(graph_path.read_text(encoding="utf-8", errors="strict"))
        old_nodes = len(old_graph.get("nodes", []))
        old_edges = len(old_graph.get("edges", old_graph.get("links", [])))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise SemanticGraphError("legacy graph.json is not readable JSON") from exc
    archive_id = (
        f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid.uuid4().hex[:12]}"
    )
    archive = semantic_store / "legacy" / archive_id
    archive.parent.mkdir(exist_ok=True, mode=0o700)
    archive.mkdir(mode=0o700)
    content = archive / "content"
    try:
        os.rename(legacy_path, content)
        for directory, _subdirs, names in os.walk(content):
            os.chmod(directory, 0o700)
            for name in names:
                os.chmod(Path(directory) / name, 0o600)
        manifest = seal_document(
            {
                "schema": LEGACY_ARCHIVE_SCHEMA,
                "status": "STALE_ARCHIVED",
                "archive_id": archive_id,
                "archived_at": _utc_now(),
                "original_path": str(legacy_path),
                "replacement_target": str(semantic_store),
                "reason": "narrow retrospective graph did not represent the GIGA folder",
                "legacy_counts": {"nodes": old_nodes, "edges": old_edges},
                "entries": len(entries),
                "entries_sha256": sha256_bytes(canonical_bytes(entries)),
                "tree": entries,
                "recoverable": True,
            }
        )
        manifest_path = archive / "manifest.json"
        manifest_path.write_bytes(canonical_bytes(manifest))
        os.chmod(manifest_path, 0o600)
        temporary = legacy_path.with_name(f".{legacy_path.name}.{archive_id}.tmp")
        os.symlink(semantic_store, temporary)
        os.replace(temporary, legacy_path)
        return manifest
    except BaseException:
        if legacy_path.is_symlink():
            legacy_path.unlink()
        if content.exists() and not legacy_path.exists():
            os.rename(content, legacy_path)
        raise


def _priority(path: str, size: int) -> tuple[int, int, int, str]:
    first = PurePosixPath(path).parts[0]
    order = {
        "architecture": 0,
        "contracts": 1,
        "modules": 2,
        "scripts": 3,
        "tests": 4,
        "deploy": 5,
        "market-aligner": 6,
        "job-application-automation": 7,
        "research": 8,
        "twin_core": 9,
        "projects": 20,
        "upstreams": 30,
    }
    return order.get(first, 10), size, len(PurePosixPath(path).parts), path


def _select_files(
    files: Mapping[str, _File], previous: SemanticRun | None, max_new_documents: int
) -> tuple[dict[str, _File], int, int]:
    previous_paths: set[str] = set()
    if previous is not None:
        previous_paths = {
            item["path"]
            for item in previous.manifest["coverage"]["selected_files"]
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
    structural = {
        path for path, item in files.items() if item.suffix in GRAPHIFY_CODE_SUFFIXES
    }
    documents = {
        path
        for path, item in files.items()
        if item.suffix in GRAPHIFY_DOCUMENT_SUFFIXES
    }
    retained_documents = documents & previous_paths
    new_documents = sorted(
        documents - previous_paths,
        key=lambda path: _priority(path, files[path].size),
    )[:max_new_documents]
    selected_paths = structural | retained_documents | set(new_documents)
    return (
        {path: files[path] for path in sorted(selected_paths)},
        len(new_documents),
        len(documents),
    )


def _stable_copy(root: Path, record: _File, destination: Path) -> int:
    source = root / record.path
    before = source.lstat()
    expected = (
        record.size,
        record.mtime_ns,
        record.ctime_ns,
        record.mode,
    )
    observed = (
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
        stat.S_IMODE(before.st_mode),
    )
    if source.is_symlink() or not stat.S_ISREG(before.st_mode) or observed != expected:
        raise SemanticGraphError(
            f"inventory source drifted before projection: {record.path}"
        )
    descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise SemanticGraphError(f"source identity changed: {record.path}")
        chunks: list[bytes] = []
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        opened.st_dev,
        opened.st_ino,
        opened.st_size,
        opened.st_mtime_ns,
        opened.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise SemanticGraphError(f"source changed during projection: {record.path}")
    if digest.hexdigest() != record.sha256:
        raise SemanticGraphError(f"inventory hash does not match source: {record.path}")
    content = b"".join(chunks)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.write_bytes(content)
    os.chmod(destination, 0o600)
    os.utime(destination, ns=(record.mtime_ns, record.mtime_ns), follow_symlinks=False)
    return max(1, content.count(b"\n") + (0 if content.endswith(b"\n") else 1))


def _prepare_projection(
    workspace: Path, root: Path, selected: Mapping[str, _File]
) -> tuple[Path, dict[str, int]]:
    next_path = workspace / "input.next"
    current = workspace / "input"
    previous = workspace / "input.previous"
    shutil.rmtree(next_path, ignore_errors=True)
    shutil.rmtree(previous, ignore_errors=True)
    next_path.mkdir(parents=True, mode=0o700)
    line_counts: dict[str, int] = {}
    try:
        for relative, record in selected.items():
            line_counts[relative] = _stable_copy(root, record, next_path / relative)
        next_fd = os.open(next_path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(next_fd)
        finally:
            os.close(next_fd)
        if current.exists():
            os.rename(current, previous)
        os.rename(next_path, current)
        shutil.rmtree(previous, ignore_errors=True)
        return current, line_counts
    except Exception:
        shutil.rmtree(next_path, ignore_errors=True)
        if not current.exists() and previous.exists():
            os.rename(previous, current)
        raise


def _prepare_delta_projection(
    workspace: Path,
    projection: Path,
    delta: Mapping[str, _File],
) -> Path:
    next_path = workspace / "delta.next"
    current = workspace / "delta"
    shutil.rmtree(next_path, ignore_errors=True)
    next_path.mkdir(parents=True, mode=0o700)
    for relative in delta:
        destination = next_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(projection / relative, destination)
        os.chmod(destination, 0o600)
    if current.exists():
        shutil.rmtree(current)
    os.rename(next_path, current)
    return current


def _delta_files(
    selected: Mapping[str, _File], previous: SemanticRun | None
) -> tuple[dict[str, _File], set[str]]:
    if previous is None:
        return dict(selected), set()
    previous_files = {
        item["path"]: item["sha256"]
        for item in previous.manifest["coverage"]["selected_files"]
    }
    force_structural = (
        previous.manifest["graph"].get("structural_files_sourced", 0) == 0
    )
    delta = {
        path: record
        for path, record in selected.items()
        if previous_files.get(path) != record.sha256
        or (force_structural and record.suffix in GRAPHIFY_CODE_SUFFIXES)
    }
    retained = {
        path
        for path, record in selected.items()
        if path not in delta and previous_files.get(path) == record.sha256
    }
    return delta, retained


def _merge_raw_graph(
    previous: SemanticRun | None,
    delta_raw_path: Path,
    retained_paths: set[str],
    destination: Path,
) -> dict[str, int]:
    delta = json.loads(delta_raw_path.read_text(encoding="utf-8", errors="strict"))
    retained: dict[str, Any] = {"nodes": [], "edges": [], "hyperedges": []}
    retained_input_tokens = 0
    retained_output_tokens = 0
    if previous is not None and retained_paths:
        previous_path = previous.run_directory / previous.manifest["graph"]["raw_path"]
        retained_source = json.loads(
            previous_path.read_text(encoding="utf-8", errors="strict")
        )
        retained["nodes"] = [
            item
            for item in retained_source["nodes"]
            if item.get("source_file") in retained_paths
            or item.get("source_file") in (None, "")
        ]
        retained["edges"] = [
            item
            for item in retained_source["edges"]
            if item.get("source_file") in retained_paths
        ]
        retained["hyperedges"] = [
            item
            for item in retained_source["hyperedges"]
            if item.get("source_file") in retained_paths
        ]
        retained_input_tokens = int(retained_source.get("input_tokens", 0) or 0)
        retained_output_tokens = int(retained_source.get("output_tokens", 0) or 0)
    combined = {
        "nodes": retained["nodes"] + delta["nodes"],
        "edges": retained["edges"] + delta["edges"],
        "hyperedges": retained["hyperedges"] + delta["hyperedges"],
        "input_tokens": retained_input_tokens + int(delta.get("input_tokens", 0) or 0),
        "output_tokens": retained_output_tokens
        + int(delta.get("output_tokens", 0) or 0),
    }
    destination.write_bytes(canonical_bytes(combined))
    return {
        "delta_nodes": len(delta["nodes"]),
        "delta_edges": len(delta["edges"]),
        "retained_nodes": len(retained["nodes"]),
        "retained_edges": len(retained["edges"]),
    }


def _graphify_environment(config: GraphifyConfig, home: Path) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    return {
        "GRAPHIFY_API_TIMEOUT": str(config.request_timeout_seconds),
        "GRAPHIFY_MAX_OUTPUT_TOKENS": str(config.max_output_tokens),
        "GRAPHIFY_OLLAMA_NUM_CTX": "16384",
        "GRAPHIFY_OLLAMA_PARALLEL": "1",
        "HOME": str(home),
        "LC_ALL": "C",
        "NO_PROXY": "127.0.0.1,::1",
        "OLLAMA_API_KEY": "local-only",
        "OLLAMA_BASE_URL": config.endpoint,
        "OLLAMA_MODEL": config.model,
        "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TZ": "UTC",
    }


def _invoke_graphify(
    projection: Path, output: Path, config: GraphifyConfig, home: Path
) -> dict[str, Any]:
    python = config.python.expanduser().absolute()
    if not python.is_file() or not os.access(python, os.X_OK):
        raise SemanticGraphError("Graphify Python must be an executable file")
    argv = [
        str(python),
        "-m",
        "graphify",
        "extract",
        str(projection),
        "--backend",
        "ollama",
        "--model",
        config.model,
        "--token-budget",
        str(config.token_budget),
        "--max-concurrency",
        "1",
        "--max-workers",
        str(config.max_workers),
        "--api-timeout",
        str(config.request_timeout_seconds),
        "--no-cluster",
        "--out",
        str(output),
    ]
    process = subprocess.Popen(
        argv,
        cwd=projection.parent,
        env=_graphify_environment(config, home),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=config.process_timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise SemanticGraphError(
            f"Graphify exceeded the {config.process_timeout_seconds}-second process budget"
        ) from exc
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise
    result = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    stdout_path = output / "graphify.stdout"
    stderr_path = output / "graphify.stderr"
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    os.chmod(stdout_path, 0o600)
    os.chmod(stderr_path, 0o600)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace")[-4000:]
        raise SemanticGraphError(
            f"Graphify extraction failed ({result.returncode}): {detail}"
        )
    return {
        "argv": argv,
        "stdout_sha256": sha256_bytes(result.stdout),
        "stdout_bytes": len(result.stdout),
        "stdout_path": "graphify.stdout",
        "stderr_sha256": sha256_bytes(result.stderr),
        "stderr_bytes": len(result.stderr),
        "stderr_path": "graphify.stderr",
        "exit_code": result.returncode,
    }


def _location(value: str, lines: int) -> None:
    match = LOCATION_RE.fullmatch(value)
    if match is None:
        raise SemanticGraphError(
            f"Graphify emitted a malformed source location: {value!r}"
        )
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    if start > end or end > lines:
        raise SemanticGraphError(
            f"Graphify source location is outside the source: {value!r}"
        )


def _unique_label_location(projection: Path, source: str, label: Any) -> str | None:
    """Return an exact line only when a model label has one source occurrence."""
    if not isinstance(label, str) or not label.strip():
        return None
    pure = PurePosixPath(source)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        return None
    try:
        root = projection.resolve(strict=True)
        candidate = (root / pure).resolve(strict=True)
        candidate.relative_to(root)
        lines = candidate.read_text(encoding="utf-8", errors="strict").splitlines()
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    matches = [index for index, line in enumerate(lines, 1) if label in line]
    return f"L{matches[0]}" if len(matches) == 1 else None


def _normalize_graph(
    raw_path: Path,
    graph_path: Path,
    projection: Path,
) -> dict[str, int]:
    """Source-scope duplicate IDs and drop edges that cannot resolve exactly."""
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticGraphError("Graphify raw graph is not strict UTF-8 JSON") from exc
    if not isinstance(raw, dict) or not all(
        isinstance(raw.get(key), list) for key in ("nodes", "edges", "hyperedges")
    ):
        raise SemanticGraphError("Graphify raw graph has an invalid root shape")

    exact_nodes: dict[bytes, dict[str, Any]] = {}
    malformed_nodes_removed = 0
    malformed_locations_repaired = 0
    for value in raw["nodes"]:
        if not isinstance(value, dict):
            raise SemanticGraphError("Graphify raw node is not an object")
        node = dict(value)
        source = node.get("source_file")
        location = node.get("source_location")
        if source not in (None, "") and (
            location in (None, "")
            or not isinstance(location, str)
            or LOCATION_RE.fullmatch(location) is None
        ):
            location = _unique_label_location(projection, source, node.get("label"))
            if location is None:
                malformed_nodes_removed += 1
                continue
            node["source_location"] = location
            malformed_locations_repaired += 1
        exact_nodes.setdefault(canonical_bytes(node), node)

    by_original: dict[str, list[dict[str, Any]]] = {}
    for node in exact_nodes.values():
        identifier = node.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise SemanticGraphError("Graphify raw node has no id")
        by_original.setdefault(identifier, []).append(node)

    normalized_nodes: list[dict[str, Any]] = []
    for identifier, group in sorted(by_original.items()):
        for node in sorted(group, key=lambda item: canonical_bytes(item)):
            normalized = dict(node)
            if len(group) > 1:
                identity = {
                    "id": identifier,
                    "label": node.get("label"),
                    "source_file": node.get("source_file"),
                    "source_location": node.get("source_location"),
                    "file_type": node.get("file_type"),
                }
                normalized["id"] = (
                    f"{identifier}__{sha256_bytes(canonical_bytes(identity))[:16]}"
                )
            node["normalized_id"] = normalized["id"]
            normalized_nodes.append(normalized)

    def resolve(identifier: Any, source_file: Any) -> str | None:
        if not isinstance(identifier, str):
            return None
        candidates = by_original.get(identifier, [])
        if len(candidates) == 1:
            return candidates[0]["normalized_id"]
        same_source = [
            item for item in candidates if item.get("source_file") == source_file
        ]
        if len(same_source) == 1:
            return same_source[0]["normalized_id"]
        return None

    normalized_edges: dict[bytes, dict[str, Any]] = {}
    unresolved_edges = 0
    for value in raw["edges"]:
        if not isinstance(value, dict):
            unresolved_edges += 1
            continue
        edge = dict(value)
        if edge.get("source_file") not in (None, ""):
            location = edge.get("source_location")
            if not isinstance(location, str) or LOCATION_RE.fullmatch(location) is None:
                unresolved_edges += 1
                continue
        source_id = resolve(edge.get("source"), edge.get("source_file"))
        target_id = resolve(edge.get("target"), edge.get("source_file"))
        if source_id is None or target_id is None:
            unresolved_edges += 1
            continue
        edge["source"] = source_id
        edge["target"] = target_id
        normalized_edges.setdefault(canonical_bytes(edge), edge)

    normalized_hyperedges: dict[bytes, dict[str, Any]] = {}
    unresolved_hyperedges = 0
    for value in raw["hyperedges"]:
        if not isinstance(value, dict) or not isinstance(value.get("nodes"), list):
            unresolved_hyperedges += 1
            continue
        item = dict(value)
        if item.get("source_file") not in (None, ""):
            location = item.get("source_location")
            if not isinstance(location, str) or LOCATION_RE.fullmatch(location) is None:
                unresolved_hyperedges += 1
                continue
        resolved = [
            resolve(identifier, item.get("source_file")) for identifier in item["nodes"]
        ]
        if any(identifier is None for identifier in resolved):
            unresolved_hyperedges += 1
            continue
        item["nodes"] = resolved
        normalized_hyperedges.setdefault(canonical_bytes(item), item)

    graph = {
        **{
            key: value
            for key, value in raw.items()
            if key not in {"nodes", "edges", "hyperedges"}
        },
        "nodes": normalized_nodes,
        "edges": list(normalized_edges.values()),
        "hyperedges": list(normalized_hyperedges.values()),
    }
    graph_path.write_bytes(canonical_bytes(graph))
    return {
        "raw_nodes": len(raw["nodes"]),
        "malformed_nodes_removed": malformed_nodes_removed,
        "malformed_locations_repaired": malformed_locations_repaired,
        "exact_duplicate_nodes_removed": len(raw["nodes"]) - len(exact_nodes),
        "source_scoped_node_ids": sum(
            len(group) for group in by_original.values() if len(group) > 1
        ),
        "unresolved_edges_removed": unresolved_edges,
        "exact_duplicate_edges_removed": len(raw["edges"])
        - unresolved_edges
        - len(normalized_edges),
        "unresolved_hyperedges_removed": unresolved_hyperedges,
    }


def _validate_graph(
    graph_path: Path,
    selected: Mapping[str, _File],
    line_counts: Mapping[str, int],
    *,
    allow_uncovered_documents: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = graph_path.read_bytes()
    try:
        graph = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticGraphError("Graphify graph is not strict UTF-8 JSON") from exc
    if not isinstance(graph, dict):
        raise SemanticGraphError("Graphify graph root must be an object")
    for key in ("nodes", "edges", "hyperedges"):
        if not isinstance(graph.get(key), list):
            raise SemanticGraphError(f"Graphify graph has no {key} list")
    node_ids: set[str] = set()
    unsourced_nodes = 0
    sourced_paths: set[str] = set()
    selected_paths = set(selected)
    for node in graph["nodes"]:
        if (
            not isinstance(node, dict)
            or not isinstance(node.get("id"), str)
            or not node["id"]
        ):
            raise SemanticGraphError("Graphify node has no stable id")
        if node["id"] in node_ids:
            raise SemanticGraphError(f"Graphify node id is duplicated: {node['id']}")
        node_ids.add(node["id"])
        source = node.get("source_file")
        location = node.get("source_location")
        if source in (None, ""):
            if location not in (None, ""):
                raise SemanticGraphError(
                    "Graphify unsourced node has a source location"
                )
            unsourced_nodes += 1
        else:
            if source not in selected_paths:
                raise SemanticGraphError(
                    f"Graphify node cites an unadmitted source: {source}"
                )
            if not isinstance(location, str):
                raise SemanticGraphError("Graphify sourced node has no source location")
            _location(location, line_counts[source])
            sourced_paths.add(source)
    for edge in graph["edges"]:
        if (
            not isinstance(edge, dict)
            or not isinstance(edge.get("source"), str)
            or not isinstance(edge.get("target"), str)
            or not isinstance(edge.get("relation"), str)
        ):
            raise SemanticGraphError("Graphify edge is malformed")
        confidence = edge.get("confidence")
        if confidence not in CONFIDENCE_VALUES:
            raise SemanticGraphError(
                f"Graphify edge has invalid confidence: {confidence!r}"
            )
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            raise SemanticGraphError("Graphify edge cites an unknown node")
        source = edge.get("source_file")
        location = edge.get("source_location")
        if source is not None:
            if source not in selected_paths:
                raise SemanticGraphError(
                    f"Graphify edge cites an unadmitted source: {source}"
                )
            if not isinstance(location, str):
                raise SemanticGraphError("Graphify sourced edge has no source location")
            _location(location, line_counts[source])
            sourced_paths.add(source)
    for hyperedge in graph["hyperedges"]:
        if (
            not isinstance(hyperedge, dict)
            or not isinstance(hyperedge.get("nodes"), list)
            or len(hyperedge["nodes"]) < 2
            or any(identifier not in node_ids for identifier in hyperedge["nodes"])
        ):
            raise SemanticGraphError("Graphify hyperedge is malformed")
        if hyperedge.get("confidence") not in CONFIDENCE_VALUES:
            raise SemanticGraphError("Graphify hyperedge has invalid confidence")
        source = hyperedge.get("source_file")
        location = hyperedge.get("source_location")
        if source not in (None, ""):
            if source not in selected_paths:
                raise SemanticGraphError(
                    f"Graphify hyperedge cites an unadmitted source: {source}"
                )
            if not isinstance(location, str):
                raise SemanticGraphError(
                    "Graphify sourced hyperedge has no source location"
                )
            _location(location, line_counts[source])
            sourced_paths.add(source)
    uncovered_documents = sorted(
        path
        for path, record in selected.items()
        if record.suffix in GRAPHIFY_DOCUMENT_SUFFIXES and path not in sourced_paths
    )
    if uncovered_documents and not allow_uncovered_documents:
        raise SemanticGraphError(
            "Graphify returned no source-linked content for selected documents: "
            + ", ".join(uncovered_documents[:10])
        )
    if any(
        record.suffix in GRAPHIFY_CODE_SUFFIXES for record in selected.values()
    ) and not any(
        path in sourced_paths and record.suffix in GRAPHIFY_CODE_SUFFIXES
        for path, record in selected.items()
    ):
        raise SemanticGraphError(
            "Graphify returned no source-linked structural content"
        )
    return graph, {
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "hyperedges": len(graph["hyperedges"]),
        "sourced_files": len(sourced_paths),
        "structural_files_sourced": sum(
            path in sourced_paths and record.suffix in GRAPHIFY_CODE_SUFFIXES
            for path, record in selected.items()
        ),
        "document_files_sourced": sum(
            path in sourced_paths and record.suffix in GRAPHIFY_DOCUMENT_SUFFIXES
            for path, record in selected.items()
        ),
        "input_tokens": int(graph.get("input_tokens", 0) or 0),
        "output_tokens": int(graph.get("output_tokens", 0) or 0),
        "unsourced_external_nodes": unsourced_nodes,
        "uncovered_documents": uncovered_documents,
    }


def _preserve_failure(
    store: Path,
    staging: Path,
    run_id: str,
    inventory: NavigationRun,
    started_at: str,
    error: BaseException,
) -> None:
    failures = store / "failures"
    failures.mkdir(exist_ok=True, mode=0o700)
    destination = failures / run_id
    if destination.exists():
        return
    if staging.exists():
        os.rename(staging, destination)
    else:
        destination.mkdir(mode=0o700)
    receipt = seal_document(
        {
            "schema": "giga.navigation.semantic-refresh-failure.v1",
            "status": "FAILED_NOT_CURRENT",
            "run_id": run_id,
            "started_at": started_at,
            "failed_at": _utc_now(),
            "inventory_run_id": inventory.manifest["run_id"],
            "inventory_receipt_sha256": inventory.manifest["receipt_sha256"],
            "error_type": type(error).__name__,
            "reason": str(error)[-4000:],
        }
    )
    (destination / "failure.json").write_bytes(canonical_bytes(receipt))
    for directory, _subdirs, names in os.walk(destination):
        os.chmod(directory, 0o700)
        for name in names:
            os.chmod(Path(directory) / name, 0o600)


def _recover_staging(store: Path) -> None:
    """Preserve abandoned staging directories before starting another refresh."""
    failures = store / "failures"
    failures.mkdir(exist_ok=True, mode=0o700)
    for staging in sorted(store.glob(".staging-*")):
        if not staging.is_dir() or staging.is_symlink():
            raise SemanticGraphError(f"unsafe stale semantic staging path: {staging}")
        run_id = staging.name.removeprefix(".staging-")
        destination = failures / run_id
        if destination.exists():
            raise SemanticGraphError(
                f"semantic failure destination already exists: {destination}"
            )
        os.rename(staging, destination)
        receipt = seal_document(
            {
                "schema": "giga.navigation.semantic-refresh-failure.v1",
                "status": "FAILED_INTERRUPTED_NOT_CURRENT",
                "run_id": run_id,
                "failed_at": _utc_now(),
                "reason": "staging directory survived without atomic publication",
            }
        )
        (destination / "failure.json").write_bytes(canonical_bytes(receipt))
        for directory, _subdirs, names in os.walk(destination):
            os.chmod(directory, 0o700)
            for name in names:
                os.chmod(Path(directory) / name, 0o600)


def _render_report(manifest: Mapping[str, Any]) -> str:
    coverage = manifest["coverage"]
    graph = manifest["graph"]
    return "\n".join(
        [
            "# GIGA local semantic navigation graph",
            "",
            f"- Status: **{manifest['status']}**",
            f"- Inventory run: `{manifest['inventory']['run_id']}`",
            f"- Selected safe files: {coverage['selected']:,} / {coverage['supported']:,}",
            f"- Structural files: {coverage['structural_selected']:,}",
            f"- Prose files: {coverage['documents_selected']:,} / {coverage['documents_total']:,}",
            f"- Graph nodes: {graph['nodes']:,}",
            f"- Graph edges: {graph['edges']:,}",
            f"- Model endpoint: `{manifest['local_model']['endpoint']}`",
            f"- Model: `{manifest['local_model']['model']}`",
            f"- Graph SHA-256: `{graph['sha256']}`",
            f"- Receipt SHA-256: `{manifest['receipt_sha256']}`",
            "",
            "The graph is a local navigation index, not authority. EXTRACTED edges are parser observations;",
            "INFERRED edges are model hypotheses. Every sourced node and edge was checked against an exact",
            "inventory-admitted path and line range. Sensitive and unsupported content remains outside the projection.",
            "",
        ]
    )


def refresh_semantic_graph(
    inventory_store: Path,
    semantic_store: Path,
    config: GraphifyConfig | None = None,
) -> SemanticRun:
    """Incrementally refresh the local Graphify layer and publish it atomically."""
    config = config or GraphifyConfig()
    inventory = current_navigation_run(inventory_store)
    semantic_store = _private_store(semantic_store)
    _recover_staging(semantic_store)
    previous = _read_semantic_current(semantic_store)
    root, files, unsupported = _inventory_files(inventory)
    selected, new_documents, documents_total = _select_files(
        files, previous, config.max_new_documents
    )
    if not selected:
        raise SemanticGraphError("inventory has no Graphify-supported safe files")
    local_model = _verify_local_model(config)
    workspace = semantic_store / "workspace"
    workspace.mkdir(exist_ok=True, mode=0o700)
    projection, line_counts = _prepare_projection(workspace, root, selected)
    delta, retained_paths = _delta_files(selected, previous)
    delta_projection = _prepare_delta_projection(workspace, projection, delta)
    run_id = (
        f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid.uuid4().hex[:12]}"
    )
    output = semantic_store / f".staging-{run_id}"
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(mode=0o700)
    started_at = _utc_now()
    started = time.monotonic()
    try:
        graphify_output = output / "graphify-out"
        if delta:
            execution = _invoke_graphify(
                delta_projection, output, config, workspace / "home"
            )
            delta_raw_path = graphify_output / "graph.json"
        else:
            if previous is None:
                raise SemanticGraphError(
                    "semantic extraction has no delta and no prior graph"
                )
            graphify_output.mkdir(parents=True, mode=0o700)
            shutil.copy2(
                previous.run_directory / "graphify-out/manifest.json",
                graphify_output / "manifest.json",
            )
            delta_raw_path = graphify_output / "graph.delta.raw.json"
            delta_raw_path.write_bytes(
                canonical_bytes({"nodes": [], "edges": [], "hyperedges": []})
            )
            execution = {
                "argv": [],
                "exit_code": 0,
                "status": "SKIPPED_NO_CHANGED_SUPPORTED_FILES",
                "stdout_path": None,
                "stdout_sha256": sha256_bytes(b""),
                "stdout_bytes": 0,
                "stderr_path": None,
                "stderr_sha256": sha256_bytes(b""),
                "stderr_bytes": 0,
            }
        if delta_raw_path.name != "graph.delta.raw.json":
            renamed_delta = graphify_output / "graph.delta.raw.json"
            os.rename(delta_raw_path, renamed_delta)
            delta_raw_path = renamed_delta
        graph_path = graphify_output / "graph.json"
        raw_graph_path = output / "graphify-out" / "graph.raw.json"
        merge_counts = _merge_raw_graph(
            previous, delta_raw_path, retained_paths, raw_graph_path
        )
        normalization = _normalize_graph(raw_graph_path, graph_path, projection)
        graph, graph_counts = _validate_graph(
            graph_path,
            selected,
            line_counts,
            allow_uncovered_documents=True,
        )
        uncovered_documents = graph_counts.pop("uncovered_documents")
        extraction_failures = [
            {
                "type": "NO_SOURCE_LINKED_CONTENT",
                "path": path,
                "retry": "ON_CONTENT_CHANGE",
            }
            for path in uncovered_documents
        ]
        graph_sha, graph_bytes = _file_sha256(graph_path)
        raw_graph_sha, raw_graph_bytes = _file_sha256(raw_graph_path)
        graphify_manifest_path = output / "graphify-out" / "manifest.json"
        graphify_manifest_sha, graphify_manifest_bytes = _file_sha256(
            graphify_manifest_path
        )
        graphify_python = config.python.expanduser().absolute()
        python_sha, _ = _file_sha256(graphify_python)
        selected_files = [
            {"path": item.path, "sha256": item.sha256, "suffix": item.suffix}
            for item in selected.values()
        ]
        structural_selected = sum(
            item.suffix in GRAPHIFY_CODE_SUFFIXES for item in selected.values()
        )
        documents_selected = len(selected) - structural_selected
        supported = len(files)
        status = (
            "CURRENT"
            if len(selected) == supported and not extraction_failures
            else "PARTIAL"
        )
        manifest = seal_document(
            {
                "schema": SEMANTIC_SCHEMA,
                "authority": "non-authoritative-local-navigation-index",
                "authority_granted": False,
                "status": status,
                "run_id": run_id,
                "root": str(root),
                "scan": {
                    "started_at": started_at,
                    "finished_at": _utc_now(),
                    "duration_seconds": round(time.monotonic() - started, 6),
                    "incremental_from": previous.manifest["run_id"]
                    if previous is not None
                    else None,
                },
                "inventory": {
                    "store": str(Path(inventory_store).resolve(strict=True)),
                    "run_id": inventory.manifest["run_id"],
                    "manifest_receipt_sha256": inventory.manifest["receipt_sha256"],
                    "database_sha256": inventory.manifest["database"]["sha256"],
                    "row_digest_sha256": inventory.manifest["database"][
                        "row_digest_sha256"
                    ],
                },
                "coverage": {
                    "inventory_semantic_eligible": inventory.manifest["counts"][
                        "semantic_eligible"
                    ],
                    "supported": supported,
                    "unsupported": unsupported,
                    "selected": len(selected),
                    "structural_selected": structural_selected,
                    "documents_selected": documents_selected,
                    "documents_total": documents_total,
                    "new_documents": new_documents,
                    "delta_files": len(delta),
                    "retained_files": len(retained_paths),
                    "selected_files_sha256": sha256_bytes(
                        canonical_bytes(selected_files)
                    ),
                    "selected_files": selected_files,
                },
                "local_model": {
                    **local_model,
                    "external_provider_environment_removed": list(
                        EXTERNAL_PROVIDER_ENV
                    ),
                    "max_concurrency": 1,
                },
                "graphify": {
                    "python": str(graphify_python),
                    "python_sha256": python_sha,
                    "token_budget": config.token_budget,
                    "max_output_tokens": config.max_output_tokens,
                    "graphify_manifest_sha256": graphify_manifest_sha,
                    "graphify_manifest_bytes": graphify_manifest_bytes,
                    "execution": execution,
                },
                "graph": {
                    "path": "graphify-out/graph.json",
                    "sha256": graph_sha,
                    "bytes": graph_bytes,
                    "raw_path": "graphify-out/graph.raw.json",
                    "raw_sha256": raw_graph_sha,
                    "raw_bytes": raw_graph_bytes,
                    "merge": merge_counts,
                    "normalization": normalization,
                    **graph_counts,
                },
                "failures": extraction_failures,
                "limits": {
                    "external_provider_used": False,
                    "sensitive_content_projected": False,
                    "graph_is_authority": False,
                    "graph_substitutes_for_source": False,
                },
            }
        )
        (output / "manifest.json").write_bytes(canonical_bytes(manifest))
        (output / "REPORT.md").write_text(_render_report(manifest), encoding="utf-8")
        for directory, _subdirs, names in os.walk(output):
            os.chmod(directory, 0o700)
            for name in names:
                os.chmod(Path(directory) / name, 0o600)
        runs = semantic_store / "runs"
        runs.mkdir(exist_ok=True, mode=0o700)
        run_directory = runs / run_id
        os.rename(output, run_directory)
        manifest_raw = (run_directory / "manifest.json").read_bytes()
        pointer = seal_document(
            {
                "schema": SEMANTIC_POINTER_SCHEMA,
                "run_id": run_id,
                "status": status,
                "updated_at": manifest["scan"]["finished_at"],
                "manifest_file_sha256": sha256_bytes(manifest_raw),
                "manifest_receipt_sha256": manifest["receipt_sha256"],
            }
        )
        _replace_atomic(semantic_store / "CURRENT.json", canonical_bytes(pointer))
        return SemanticRun(run_directory=run_directory, manifest=manifest)
    except BaseException as exc:
        _preserve_failure(semantic_store, output, run_id, inventory, started_at, exc)
        raise


def query_semantic_graph(
    semantic_store: Path,
    question: str,
    *,
    budget: int = 2000,
    python: Path | None = None,
) -> str:
    """Run Graphify's scoped query over the authenticated current graph."""
    if not question or "\x00" in question:
        raise SemanticGraphError("question must be non-empty and contain no NUL")
    if isinstance(budget, bool) or not 100 <= budget <= 20_000:
        raise SemanticGraphError("budget must be between 100 and 20000")
    current = current_semantic_run(semantic_store)
    graph = current.run_directory / current.manifest["graph"]["path"]
    executable = (
        (python or Path(current.manifest["graphify"]["python"])).expanduser().absolute()
    )
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise SemanticGraphError("Graphify Python must be an executable file")
    result = subprocess.run(
        [
            str(executable),
            "-m",
            "graphify",
            "query",
            question,
            "--budget",
            str(budget),
            "--graph",
            str(graph),
        ],
        env={
            "HOME": str(
                Path(semantic_store).resolve(strict=True) / "workspace" / "home"
            ),
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TZ": "UTC",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise SemanticGraphError(
            f"Graphify query failed: {result.stderr.decode('utf-8', 'replace')[-2000:]}"
        )
    return result.stdout.decode("utf-8", "strict")


def locate_semantic_graph(
    semantic_store: Path, query: str, *, limit: int = 100
) -> dict[str, Any]:
    """Deterministically locate graph nodes without parsing Graphify's prose output."""
    if not query or "\x00" in query:
        raise SemanticGraphError("query must be non-empty and contain no NUL")
    if isinstance(limit, bool) or not 1 <= limit <= 500:
        raise SemanticGraphError("limit must be between 1 and 500")
    terms = sorted(
        {
            value.casefold()
            for value in re.findall(r"[A-Za-z0-9_.-]+", query)
            if len(value) >= 2
        }
    )
    if not terms:
        raise SemanticGraphError("query contains no searchable terms")
    current = current_semantic_run(semantic_store)
    graph_path = current.run_directory / current.manifest["graph"]["path"]
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticGraphError("current graph is not strict UTF-8 JSON") from exc
    selected: list[dict[str, Any]] = []
    for node in graph["nodes"]:
        fields = {
            "id": node.get("id"),
            "label": node.get("label"),
            "source_file": node.get("source_file"),
            "source_location": node.get("source_location"),
            "file_type": node.get("file_type"),
        }
        searchable = "\n".join(
            str(value).casefold() for value in fields.values() if value
        )
        matched = [term for term in terms if term in searchable]
        if not matched:
            continue
        label = str(fields["label"] or "").casefold()
        source = str(fields["source_file"] or "").casefold()
        score = sum(
            10 if label == term else 4 if term in label else 2 if term in source else 1
            for term in matched
        )
        selected.append(
            {
                **fields,
                "score": score,
                "matched_terms": matched,
            }
        )
    selected.sort(
        key=lambda item: (
            -item["score"],
            str(item["source_file"] or ""),
            str(item["source_location"] or ""),
            str(item["id"]),
        )
    )
    selected = selected[:limit]
    identifiers = {item["id"] for item in selected}
    edges = [
        {
            "source": edge.get("source"),
            "target": edge.get("target"),
            "relation": edge.get("relation"),
            "confidence": edge.get("confidence"),
            "source_file": edge.get("source_file"),
            "source_location": edge.get("source_location"),
        }
        for edge in graph["edges"]
        if edge.get("source") in identifiers and edge.get("target") in identifiers
    ]
    edges.sort(
        key=lambda item: (
            str(item["source"]),
            str(item["relation"]),
            str(item["target"]),
            str(item["source_file"] or ""),
        )
    )
    return seal_document(
        {
            "schema": SEMANTIC_LOCATE_SCHEMA,
            "status": "PASS",
            "authority": "non-authoritative-semantic-navigation-result",
            "authority_granted": False,
            "query": query,
            "terms": terms,
            "limit": limit,
            "graph": {
                "run_id": current.manifest["run_id"],
                "manifest_receipt_sha256": current.manifest["receipt_sha256"],
                "sha256": current.manifest["graph"]["sha256"],
                "inventory_run_id": current.manifest["inventory"]["run_id"],
                "inventory_manifest_receipt_sha256": current.manifest["inventory"][
                    "manifest_receipt_sha256"
                ],
            },
            "nodes": selected,
            "edges": edges,
        }
    )
