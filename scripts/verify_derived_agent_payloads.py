#!/usr/bin/env python3
"""Fail closed when a live agent payload drifts from its canonical sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
from datetime import date
from pathlib import Path
from typing import Final


REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[1]
SCHEMA_LINE: Final = "=== GIGA DERIVED PAYLOAD v1 ==="
END_LINE: Final = "=== END GIGA DERIVED PAYLOAD METADATA ==="
AUTHORITY_LINE: Final = (
    "authority: DERIVED_ONLY; this payload cannot override either canonical source"
)
CANONICAL_SOURCES: Final = ("CHARTER.md", "CONTEXT.md")
PAYLOAD_STATUSES: Final = {
    "deploy/claude_preferences.txt": "UNVERIFIED_REPASTE",
    "deploy/chatgpt_custom_instructions.txt": "UNVERIFIED_REPASTE",
    "deploy/v3_operator_model.md": "STAGED_NOT_DEPLOYED",
}


class DerivedPayloadError(RuntimeError):
    """A live payload is missing, unsafe, malformed, or stale."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_regular_file(root: Path, relative: str) -> bytes:
    path = root / relative
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise DerivedPayloadError(f"missing required file: {relative}") from exc
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise DerivedPayloadError(f"required file is not a regular non-symlink: {relative}")
    if metadata.st_nlink != 1:
        raise DerivedPayloadError(f"required file has multiple hard links: {relative}")
    return path.read_bytes()


def _canonical_source_lines(root: Path) -> tuple[list[str], dict[str, str]]:
    lines: list[str] = []
    hashes: dict[str, str] = {}
    for relative in CANONICAL_SOURCES:
        digest = _sha256(_read_regular_file(root, relative))
        hashes[relative] = digest
        lines.append(f"canonical-source: {relative} sha256={digest}")
    return lines, hashes


def _verify_payload(
    root: Path,
    relative: str,
    expected_status: str,
    canonical_lines: list[str],
) -> dict[str, object]:
    raw = _read_regular_file(root, relative)
    delimiter = f"{END_LINE}\n\n".encode()
    if raw.count(delimiter) != 1:
        raise DerivedPayloadError(f"{relative}: metadata terminator must occur exactly once")
    header_raw, body = raw.split(delimiter, 1)
    try:
        header = header_raw.decode("utf-8").splitlines()
        body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DerivedPayloadError(f"{relative}: payload must be UTF-8") from exc
    if not body:
        raise DerivedPayloadError(f"{relative}: derived payload body is empty")
    if len(header) != 7 or header[0] != SCHEMA_LINE:
        raise DerivedPayloadError(f"{relative}: metadata schema or field count differs")
    if header[1:3] != canonical_lines:
        raise DerivedPayloadError(f"{relative}: canonical source identity is stale or reordered")
    if not header[3].startswith("derived-at: "):
        raise DerivedPayloadError(f"{relative}: missing derived-at date")
    try:
        date.fromisoformat(header[3].removeprefix("derived-at: "))
    except ValueError as exc:
        raise DerivedPayloadError(f"{relative}: derived-at is not an ISO date") from exc
    if header[4] != f"deployment-status: {expected_status}":
        raise DerivedPayloadError(f"{relative}: deployment status differs from its admitted state")
    if header[5] != AUTHORITY_LINE:
        raise DerivedPayloadError(f"{relative}: derived-only authority declaration differs")
    body_digest = _sha256(body)
    if header[6] != f"payload-body-sha256: {body_digest}":
        raise DerivedPayloadError(f"{relative}: payload body differs from its recorded identity")
    return {
        "path": relative,
        "deployment_status": expected_status,
        "payload_sha256": _sha256(raw),
        "payload_body_sha256": body_digest,
    }


def verify_derived_payloads(root: Path = REPOSITORY_ROOT) -> dict[str, object]:
    root = root.absolute()
    canonical_lines, source_hashes = _canonical_source_lines(root)
    payloads = [
        _verify_payload(root, relative, status, canonical_lines)
        for relative, status in PAYLOAD_STATUSES.items()
    ]
    return {
        "schema": "giga.derived-agent-payload-verification.v1",
        "status": "PASS",
        "canonical_sources": source_hashes,
        "payloads": payloads,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    args = parser.parse_args()
    try:
        result = verify_derived_payloads(args.root)
    except DerivedPayloadError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
