"""Canonical, self-hashed evidence helpers shared by Archaeology slices."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping


class EvidenceError(ValueError):
    """Evidence is malformed, mutable, or cannot be published safely."""


def canonical_bytes(value: Any) -> bytes:
    """Return the single UTF-8 representation accepted by the pipeline."""
    try:
        return (
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EvidenceError("evidence is not closed JSON data") from exc


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def seal_document(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Copy and self-hash a document, excluding only ``receipt_sha256``."""
    if not isinstance(payload, Mapping) or "receipt_sha256" in payload:
        raise EvidenceError(
            "unsealed evidence must be an object without receipt_sha256"
        )
    snapshot = json.loads(canonical_bytes(dict(payload)))
    snapshot["receipt_sha256"] = sha256_bytes(canonical_bytes(snapshot))
    return snapshot


def validate_self_hash(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise EvidenceError("sealed evidence must be an object")
    claimed = payload.get("receipt_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise EvidenceError("evidence has no canonical receipt_sha256")
    unsigned = dict(payload)
    del unsigned["receipt_sha256"]
    expected = sha256_bytes(canonical_bytes(unsigned))
    if claimed != expected:
        raise EvidenceError("evidence self-hash mismatch")


def write_atomic(path: Path, payload: bytes, *, mode: int = 0o600) -> None:
    """Atomically publish bytes without overwriting an existing evidence file."""
    path = path.resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists() or path.is_symlink():
        raise EvidenceError(f"evidence already exists: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        set_private_file_mode(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_path, path)
        set_private_path_mode(path, mode)
        sync_directory(path.parent)
    except FileExistsError as exc:
        raise EvidenceError(f"evidence already exists: {path}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temp_path.unlink(missing_ok=True)
