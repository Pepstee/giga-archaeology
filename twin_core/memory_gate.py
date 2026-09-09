"""Mandatory fail-closed validation gate for every memory-dependent stage."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .memory_validation import _frontmatter, validate_memory
from .integrity import authority_path
from .constitutional_authority import AuthorityRefused

SCHEMA = "giga.memory.validation-receipt.v1"
VALIDATOR_VERSION = "giga.memory.mandatory-gate.v1"
STAGES = {
    "pre-context",
    "pre-proposal",
    "pre-commit",
    "post-commit",
    "pre-scheduled",
    "post-scheduled",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class MemoryGateError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_rollback_receipt(
    memory_root: Path,
    *,
    source_snapshot_sha256: str,
    restored_snapshot_sha256: str,
    error: str,
) -> dict[str, Any]:
    """Record a content-addressed rollback after the authoritative snapshot is restored."""
    body: dict[str, Any] = {
        "gate_schema": SCHEMA,
        "stage": "post-commit",
        "validator_version": VALIDATOR_VERSION,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "input_hashes": {
            "source_snapshot_sha256": source_snapshot_sha256,
            "restored_snapshot_sha256": restored_snapshot_sha256,
        },
        "result": "rolled-back",
        "findings": [error[:2_000]],
        "active_entry_paths": [],
    }
    body["receipt_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    destination = (
        memory_root / "validation/receipts"
        / f"post-commit-rollback-{body['receipt_sha256']}.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not destination.exists():
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{destination.name}.", dir=destination.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return body


def _tombstones(giga_root: Path, memory_root: Path) -> tuple[dict[str, Any], list[str]]:
    path = memory_root / "tombstones.v1.json"
    findings: list[str] = []
    if not path.is_file() or path.is_symlink():
        return {"entries": []}, ["tombstone-ledger-missing-or-unsafe"]
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"entries": []}, ["tombstone-ledger-invalid"]
    if set(ledger) != {"schema", "append_only", "deletion_performed", "entries"}:
        findings.append("tombstone-ledger-fields")
    if ledger.get("schema") != "giga.memory.legacy-tombstones.v1":
        findings.append("tombstone-ledger-schema")
    if ledger.get("append_only") is not True or ledger.get("deletion_performed") is not False:
        findings.append("tombstone-ledger-destructive")
    ids: set[str] = set()
    targets: set[str] = set()
    for item in ledger.get("entries", []):
        expected = {
            "tombstone_id", "target_path", "target_sha256", "reason", "rationale",
            "effective_date", "authorized_by", "evidence", "replacement",
            "invalidates_derivatives",
        }
        if not isinstance(item, dict) or set(item) != expected:
            findings.append("tombstone-fields")
            continue
        target = item["target_path"]
        basis = {
            "target_path": target,
            "target_sha256": item["target_sha256"],
            "reason": item["reason"],
            "effective_date": item["effective_date"],
            "authorized_by": item["authorized_by"],
            "replacement": item["replacement"],
        }
        expected_id = f"tmb:{hashlib.sha256(_canonical(basis)).hexdigest()}"
        if item["tombstone_id"] != expected_id or item["tombstone_id"] in ids:
            findings.append("tombstone-id")
        ids.add(item["tombstone_id"])
        if target in targets:
            findings.append("tombstone-duplicate-target")
        targets.add(target)
        if not target.startswith("memory/entries/") or ".." in Path(target).parts:
            findings.append("tombstone-target-path")
            continue
        target_path = memory_root / Path(target).relative_to("memory")
        try:
            replacement_path = authority_path(giga_root, item["replacement"])
            evidence_path = authority_path(giga_root, item["evidence"])
        except (ValueError, TypeError) as exc:
            raise MemoryGateError("unsafe tombstone reference") from exc
        if (
            not target_path.is_file()
            or target_path.is_symlink()
            or not SHA256.fullmatch(item["target_sha256"])
            or _sha256(target_path) != item["target_sha256"]
        ):
            findings.append("tombstone-target-hash")
        if not replacement_path.is_file() or replacement_path.is_symlink():
            findings.append("tombstone-replacement")
        if not evidence_path.is_file() or evidence_path.is_symlink():
            findings.append("tombstone-evidence")
        parsed = _frontmatter(target_path.read_text(encoding="utf-8")) if target_path.is_file() else None
        if parsed is None or parsed[0].get("status") == "active":
            findings.append("tombstone-target-still-active")
        if item["reason"] not in {"operator-retracted", "superseded", "false", "privacy", "duplicate", "expired", "corrupt", "policy"}:
            findings.append("tombstone-reason")
        if item["authorized_by"] not in {"operator", "deterministic-policy"}:
            findings.append("tombstone-authority")
        if item["invalidates_derivatives"] is not True:
            findings.append("tombstone-invalidation")
    return ledger, findings


def _validate_memory_gate(
    giga_root: Path,
    stage: str,
    *,
    memory_root: Path | None = None,
    write_receipt: bool = True,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise MemoryGateError(f"unsupported memory validation stage: {stage}")
    giga_root = _safe_directory(giga_root)
    memory_root = _safe_directory(memory_root or giga_root / "memory")
    findings: list[str] = []
    if any(path.is_symlink() for path in [memory_root, *memory_root.rglob("*")]):
        raise MemoryGateError("memory-symlink; refusing before reading contents")
    legacy = validate_memory(memory_root)
    if not legacy["ok"]:
        findings.extend(
            f"legacy:{item['code']}:{Path(item['path']).name}"
            for item in legacy["findings"]
            if item["severity"] == "error"
        )
    tombstones, tombstone_findings = _tombstones(giga_root, memory_root)
    findings.extend(tombstone_findings)
    tombstoned = {item.get("target_path") for item in tombstones.get("entries", []) if isinstance(item, dict)}

    source_rows: list[dict[str, Any]] = []
    active_rows: list[dict[str, str]] = []
    source_times: list[float] = []
    for path in sorted(
        item
        for item in memory_root.rglob("*")
        if item.is_file()
        and tuple(item.relative_to(memory_root).parts[:2]) != ("validation", "receipts")
    ):
        relative_memory = path.relative_to(memory_root).as_posix()
        relative = f"memory/{relative_memory}"
        digest = _sha256(path)
        source_rows.append({"path": relative, "bytes": path.stat().st_size, "sha256": digest})
        source_times.append(path.stat().st_mtime)
        if relative_memory.startswith("entries/") and relative_memory.endswith(".md"):
            parsed = _frontmatter(path.read_text(encoding="utf-8", errors="replace"))
            status = parsed[0].get("status") if parsed else None
            if status == "active" and relative not in tombstoned:
                active_rows.append({"path": relative, "sha256": digest})
    snapshot_hash = hashlib.sha256(_canonical(source_rows)).hexdigest()
    active_hash = hashlib.sha256(_canonical(active_rows)).hexdigest()
    checked_at = datetime.fromtimestamp(max(source_times, default=0), timezone.utc).isoformat()
    body = {
        "gate_schema": SCHEMA,
        "stage": stage,
        "validator_version": VALIDATOR_VERSION,
        "checked_at": checked_at,
        "input_hashes": {
            "snapshot_sha256": snapshot_hash,
            "active_truth_sha256": active_hash,
            "tombstones_sha256": hashlib.sha256(_canonical(tombstones)).hexdigest(),
        },
        "result": "passed" if not findings else "failed",
        "findings": sorted(findings),
        "active_entry_paths": [row["path"] for row in active_rows],
    }
    body["receipt_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    if write_receipt:
        destination = memory_root / "validation/receipts" / f"{stage}-{body['receipt_sha256']}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if destination.exists() and destination.read_text(encoding="utf-8") != rendered:
            raise MemoryGateError("append-only memory gate receipt collision")
        if not destination.exists():
            descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(rendered)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, destination)
            finally:
                Path(temporary).unlink(missing_ok=True)
    return body


def _require_memory_gate(giga_root: Path, stage: str, **kwargs: Any) -> dict[str, Any]:
    receipt = _validate_memory_gate(giga_root, stage, **kwargs)
    if receipt["result"] != "passed":
        raise MemoryGateError(f"memory {stage} gate failed: {', '.join(receipt['findings'])}")
    return receipt


def _safe_directory(path: Path) -> Path:
    absolute = path.absolute()
    anchor = Path(absolute.anchor)
    try:
        candidate = authority_path(anchor, absolute.relative_to(anchor).as_posix())
    except ValueError as exc:
        raise MemoryGateError("unsafe memory directory") from exc
    if not candidate.is_dir():
        raise MemoryGateError("memory directory is missing")
    return candidate.resolve()


def _require_corpus_access() -> None:
    # The retained constitutional candidate has no host-bound corpus activation.
    # Do not accept a caller boolean, arbitrary root, or synthetic receipt as a grant.
    raise AuthorityRefused("HOST_BOUND_CORPUS_ACTIVATION_REQUIRED: corpus access is unavailable")


def validate_memory_gate(giga_root: Path, stage: str, **kwargs: Any) -> dict[str, Any]:
    """Public corpus boundary; the internal validator is retained for synthetic tests."""
    _require_corpus_access()
    return _validate_memory_gate(giga_root, stage, **kwargs)


def require_memory_gate(giga_root: Path, stage: str, **kwargs: Any) -> dict[str, Any]:
    _require_corpus_access()
    return _require_memory_gate(giga_root, stage, **kwargs)


def write_rollback_receipt(memory_root: Path, **kwargs: Any) -> dict[str, Any]:
    _require_corpus_access()
    return _write_rollback_receipt(memory_root, **kwargs)
