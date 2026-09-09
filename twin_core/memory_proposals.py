"""Deterministic validation and crash-retry-safe commit for model memory proposals.

Models never receive direct write authority through this interface.  They return a bounded JSON
proposal; code projects it into a temporary copy, validates the complete memory, and only then
commits creates/replacements.  Deletion is intentionally unsupported.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Callable

from .memory_gate import (
    MemoryGateError,
    _require_memory_gate,
    _require_corpus_access,
    _safe_directory,
    _validate_memory_gate,
    _write_rollback_receipt,
)
from .memory_validation import validate_memory as _validate_memory


SCHEMA_VERSION = 1
MAX_OPERATIONS = 8
MAX_CONTENT_BYTES = 400_000
ENTRY_PATH = re.compile(r"^entries/\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


@dataclass(frozen=True)
class MemoryOperation:
    operation: str
    path: str
    content: str
    expected_sha256: str | None

    @property
    def content_sha256(self) -> str:
        return _sha256_bytes(self.content.encode("utf-8"))


@dataclass(frozen=True)
class ValidatedProposal:
    reply: str
    operations: tuple[MemoryOperation, ...]
    baseline_errors: int
    baseline_warnings: int
    source_snapshot_sha256: str
    projected_snapshot_sha256: str


def _safe_target(memory_root: Path, relative: str) -> Path:
    if relative != "INDEX.md" and not ENTRY_PATH.fullmatch(relative):
        raise ValueError(f"unsupported memory path: {relative!r}")
    candidate = memory_root / relative
    for component in (candidate, *candidate.parents):
        if component == memory_root.parent:
            break
        if component.is_symlink():
            raise ValueError(f"memory path traverses a symlink: {relative!r}")
    target = candidate.resolve()
    try:
        target.relative_to(memory_root.resolve())
    except ValueError as exc:
        raise ValueError(f"memory path escapes root: {relative!r}") from exc
    if target.exists() and target.is_symlink():
        raise ValueError(f"memory path is a symlink: {relative!r}")
    return target


def parse_proposal(value: Mapping[str, Any]) -> tuple[str, tuple[MemoryOperation, ...]]:
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    reply = value.get("reply")
    operations = value.get("operations")
    if not isinstance(reply, str) or not reply.strip() or len(reply) > 3_900:
        raise ValueError("reply must be non-empty text no longer than 3900 characters")
    if not isinstance(operations, list) or len(operations) > MAX_OPERATIONS:
        raise ValueError(f"operations must be a list of at most {MAX_OPERATIONS} items")
    parsed: list[MemoryOperation] = []
    seen: set[str] = set()
    total_bytes = 0
    for item in operations:
        if not isinstance(item, dict):
            raise ValueError("each memory operation must be an object")
        operation = item.get("operation")
        path = item.get("path")
        content = item.get("content")
        expected = item.get("expected_sha256")
        if operation not in {"create", "replace"}:
            raise ValueError("operation must be create or replace; deletion is forbidden")
        if not isinstance(path, str) or path in seen:
            raise ValueError("operation paths must be unique strings")
        if not isinstance(content, str) or "\x00" in content:
            raise ValueError("operation content must be NUL-free UTF-8 text")
        if operation == "replace" and (
            not isinstance(expected, str) or not SHA256.fullmatch(expected)
        ):
            raise ValueError("replace requires the exact current lowercase SHA-256")
        if operation == "create" and expected is not None:
            raise ValueError("create expected_sha256 must be null")
        total_bytes += len(content.encode("utf-8"))
        if total_bytes > MAX_CONTENT_BYTES:
            raise ValueError("proposal content exceeds the bounded write budget")
        parsed.append(MemoryOperation(operation, path, content, expected))
        seen.add(path)
    return reply.strip(), tuple(parsed)


def _validate_proposal(memory_root: Path, value: Mapping[str, Any]) -> ValidatedProposal:
    memory_root = _safe_directory(memory_root)
    if not memory_root.is_dir():
        raise ValueError("memory root does not exist")
    if any(path.is_symlink() for path in memory_root.rglob("*")):
        raise ValueError("memory store contains a symlink; refusing staged projection")
    pre_commit = _require_memory_gate(memory_root.parent, "pre-commit")
    reply, operations = parse_proposal(value)
    baseline = _validate_memory(memory_root)
    baseline_counts = baseline["counts"]
    assert isinstance(baseline_counts, dict)
    active_paths = set(pre_commit["active_entry_paths"])

    for item in operations:
        target = _safe_target(memory_root, item.path)
        if (
            item.operation == "replace"
            and item.path != "INDEX.md"
            and f"memory/{item.path}" not in active_paths
        ):
            raise ValueError(f"replacement of inactive or tombstoned memory is forbidden: {item.path}")
        if item.operation == "create":
            if target.exists() and _sha256_path(target) != item.content_sha256:
                raise ValueError(f"create target already exists with different content: {item.path}")
        elif not target.is_file():
            raise ValueError(f"replace target is missing: {item.path}")
        elif _sha256_path(target) not in {item.expected_sha256, item.content_sha256}:
            raise ValueError(f"replace precondition failed: {item.path}")

    with tempfile.TemporaryDirectory(prefix="giga-memory-stage-") as folder:
        stage = Path(folder).resolve() / "memory"
        shutil.copytree(memory_root, stage, symlinks=False)
        for item in operations:
            target = _safe_target(stage, item.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item.content, encoding="utf-8")
        projected_gate = _validate_memory_gate(
            memory_root.parent, "pre-commit", memory_root=stage, write_receipt=False
        )
        projected = _validate_memory(stage)
    projected_counts = projected["counts"]
    assert isinstance(projected_counts, dict)
    if int(projected_counts["error"]) > 0:
        messages = "; ".join(
            str(item["message"]) for item in projected["findings"]
            if isinstance(item, dict) and item.get("severity") == "error"
        )
        raise ValueError(f"projected memory is invalid: {messages}")
    if int(projected_counts["warning"]) > int(baseline_counts["warning"]):
        raise ValueError("proposal introduces new memory warnings")
    if projected_gate["result"] != "passed":
        raise ValueError(
            "projected memory failed the mandatory gate: "
            + ", ".join(projected_gate["findings"])
        )
    return ValidatedProposal(
        reply=reply,
        operations=operations,
        baseline_errors=int(baseline_counts["error"]),
        baseline_warnings=int(baseline_counts["warning"]),
        source_snapshot_sha256=pre_commit["input_hashes"]["snapshot_sha256"],
        projected_snapshot_sha256=projected_gate["input_hashes"]["snapshot_sha256"],
    )


def _commit_proposal(memory_root: Path, proposal: ValidatedProposal, *, refresh_callback: Callable[[Path], None] | None = None) -> list[dict[str, str]]:
    """Commit one proposal transaction; restore and verify every target on any failure."""
    memory_root = _safe_directory(memory_root)
    current_gate = _require_memory_gate(memory_root.parent, "pre-commit")
    current_snapshot = current_gate["input_hashes"]["snapshot_sha256"]
    already_applied = all(
        _safe_target(memory_root, item.path).is_file()
        and _sha256_path(_safe_target(memory_root, item.path)) == item.content_sha256
        for item in proposal.operations
    )
    if current_snapshot != proposal.source_snapshot_sha256 and not already_applied:
        raise ValueError("memory snapshot changed after proposal validation")
    # Commit index last so readers never see an index pointing at an entry not yet written.
    ordered = sorted(proposal.operations, key=lambda item: item.path == "INDEX.md")
    artifacts: list[dict[str, str]] = []
    originals = {
        item.path: (_safe_target(memory_root, item.path).read_bytes()
                    if _safe_target(memory_root, item.path).exists() else None)
        for item in ordered
    }
    try:
        for item in ordered:
            target = _safe_target(memory_root, item.path)
            if target.exists():
                current = _sha256_path(target)
                if current == item.content_sha256:
                    artifacts.append({"path": item.path, "sha256": current})
                    continue
                if item.operation == "create":
                    raise ValueError(f"create target appeared before commit: {item.path}")
                if current != item.expected_sha256:
                    raise ValueError(f"replace target changed before commit: {item.path}")
            elif item.operation == "replace":
                raise ValueError(f"replace target disappeared before commit: {item.path}")
            _atomic_write(target, item.content.encode("utf-8"))
            artifacts.append({"path": item.path, "sha256": item.content_sha256})
        final_gate = _require_memory_gate(memory_root.parent, "post-commit")
        if final_gate["input_hashes"]["snapshot_sha256"] != proposal.projected_snapshot_sha256:
            raise RuntimeError("committed memory does not match validated projection")
        final = _validate_memory(memory_root)
        final_counts = final["counts"]
        assert isinstance(final_counts, dict)
        if not final["ok"] or int(final_counts["warning"]) > proposal.baseline_warnings:
            raise RuntimeError("committed memory failed deterministic validation")
        if refresh_callback is not None:
            refresh_callback(memory_root.parent)
        return artifacts
    except Exception as exc:
        for relative, content in originals.items():
            target = _safe_target(memory_root, relative)
            if content is None:
                target.unlink(missing_ok=True)
            else:
                _atomic_write(target, content)
        restored = _validate_memory_gate(
            memory_root.parent, "pre-commit", write_receipt=False
        )
        restored_hash = restored["input_hashes"]["snapshot_sha256"]
        if restored_hash != current_snapshot or restored["result"] != "passed":
            raise MemoryGateError("memory rollback failed exact snapshot verification") from exc
        _write_rollback_receipt(
            memory_root,
            source_snapshot_sha256=current_snapshot,
            restored_snapshot_sha256=restored_hash,
            error=f"{type(exc).__name__}: {exc}",
        )
        try:
            if refresh_callback is not None:
                refresh_callback(memory_root.parent)
        except Exception as refresh_exc:
            raise MemoryGateError(
                "memory restored but derived knowledge refresh failed"
            ) from refresh_exc
        raise


def _atomic_write(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def proposal_json_schema() -> str:
    """Compact contract embedded in provider prompts."""
    return json.dumps(
        {
            "schema_version": 1,
            "reply": "Telegram reply, <=3900 characters",
            "operations": [
                {
                    "operation": "create|replace",
                    "path": "entries/YYYY-MM-DD-slug.md|INDEX.md",
                    "expected_sha256": "null for create; exact current SHA-256 for replace",
                    "content": "complete replacement UTF-8 content",
                }
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def proposal_output_schema() -> dict[str, Any]:
    """Strict JSON Schema used by provider adapters when supported."""
    operation = {
        "type": "object",
        "additionalProperties": False,
        "required": ["operation", "path", "expected_sha256", "content"],
        "properties": {
            "operation": {"type": "string", "enum": ["create", "replace"]},
            "path": {"type": "string"},
            "expected_sha256": {"type": ["string", "null"]},
            "content": {"type": "string"},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "reply", "operations"],
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "reply": {"type": "string"},
            "operations": {"type": "array", "maxItems": MAX_OPERATIONS, "items": operation},
        },
    }


def validate_proposal(memory_root: Path, value: Mapping[str, Any]) -> ValidatedProposal:
    _require_corpus_access()
    return _validate_proposal(memory_root, value)


def commit_proposal(memory_root: Path, proposal: ValidatedProposal) -> list[dict[str, str]]:
    _require_corpus_access()
    return _commit_proposal(memory_root, proposal)
