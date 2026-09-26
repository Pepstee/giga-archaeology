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
from typing import Any, Mapping, Sequence

from .memory_validation import validate_memory


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


def validate_proposal(memory_root: Path, value: Mapping[str, Any]) -> ValidatedProposal:
    memory_root = memory_root.resolve()
    if not memory_root.is_dir():
        raise ValueError("memory root does not exist")
    if any(path.is_symlink() for path in memory_root.rglob("*")):
        raise ValueError("memory store contains a symlink; refusing staged projection")
    reply, operations = parse_proposal(value)
    baseline = validate_memory(memory_root)
    baseline_counts = baseline["counts"]
    assert isinstance(baseline_counts, dict)

    for item in operations:
        target = _safe_target(memory_root, item.path)
        if item.operation == "create":
            if target.exists() and _sha256_path(target) != item.content_sha256:
                raise ValueError(f"create target already exists with different content: {item.path}")
        elif not target.is_file():
            raise ValueError(f"replace target is missing: {item.path}")
        elif _sha256_path(target) not in {item.expected_sha256, item.content_sha256}:
            raise ValueError(f"replace precondition failed: {item.path}")

    with tempfile.TemporaryDirectory(prefix="giga-memory-stage-") as folder:
        stage = Path(folder) / "memory"
        shutil.copytree(memory_root, stage, symlinks=False)
        for item in operations:
            target = _safe_target(stage, item.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item.content, encoding="utf-8")
        projected = validate_memory(stage)
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
    return ValidatedProposal(
        reply=reply,
        operations=operations,
        baseline_errors=int(baseline_counts["error"]),
        baseline_warnings=int(baseline_counts["warning"]),
    )


def commit_proposal(memory_root: Path, proposal: ValidatedProposal) -> list[dict[str, str]]:
    """Commit a validated proposal atomically per file; exact partial replays are idempotent."""
    memory_root = memory_root.resolve()
    # Commit index last so readers never see an index pointing at an entry not yet written.
    ordered = sorted(proposal.operations, key=lambda item: item.path == "INDEX.md")
    artifacts: list[dict[str, str]] = []
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
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        temporary_path = Path(temporary)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(item.content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, target)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        artifacts.append({"path": item.path, "sha256": item.content_sha256})
    final = validate_memory(memory_root)
    final_counts = final["counts"]
    assert isinstance(final_counts, dict)
    if not final["ok"] or int(final_counts["warning"]) > proposal.baseline_warnings:
        raise RuntimeError("committed memory failed deterministic validation")
    return artifacts


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
