#!/usr/bin/env python3
"""Deterministically generate and verify live agent payloads from canonical governance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final


REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[1]
SCHEMA_LINE: Final = "=== GIGA DERIVED PAYLOAD v2 ==="
END_LINE: Final = "=== END GIGA DERIVED PAYLOAD METADATA ==="
AUTHORITY_LINE: Final = (
    "authority: DERIVED_ONLY; this payload cannot override either canonical source"
)
CANONICAL_SOURCES: Final = ("CHARTER.md", "CONTEXT.md")
_VERSION_PATTERN: Final = re.compile(
    r"^\*Version (?P<version>[0-9]+\.[0-9]+) — "
    r"(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})\.",
    re.MULTILINE,
)


@dataclass(frozen=True)
class PayloadSpec:
    template: str
    status: str


PAYLOAD_SPECS: Final = {
    "deploy/claude_preferences.txt": PayloadSpec(
        "deploy/templates/claude_preferences.txt",
        "UNVERIFIED_REPASTE",
    ),
    "deploy/chatgpt_custom_instructions.txt": PayloadSpec(
        "deploy/templates/chatgpt_custom_instructions.txt",
        "UNVERIFIED_REPASTE",
    ),
    "deploy/v3_operator_model.md": PayloadSpec(
        "deploy/templates/v3_operator_model.md",
        "STAGED_NOT_DEPLOYED",
    ),
}
PAYLOAD_STATUSES: Final = {
    relative: spec.status for relative, spec in PAYLOAD_SPECS.items()
}
TEMPLATE_PATHS: Final = tuple(spec.template for spec in PAYLOAD_SPECS.values())


class DerivedPayloadError(RuntimeError):
    """A canonical source, template, or live payload is unsafe, malformed, or stale."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_regular_file(root: Path, relative: str) -> bytes:
    path = root / relative
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise DerivedPayloadError(f"missing required file: {relative}") from exc
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise DerivedPayloadError(
            f"required file is not a regular non-symlink: {relative}"
        )
    if metadata.st_nlink != 1:
        raise DerivedPayloadError(f"required file has multiple hard links: {relative}")
    return path.read_bytes()


def _canonical_source_facts(
    root: Path,
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    lines: list[str] = []
    hashes: dict[str, str] = {}
    versions: dict[str, str] = {}
    dates: list[str] = []
    for relative in CANONICAL_SOURCES:
        raw = _read_regular_file(root, relative)
        digest = _sha256(raw)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DerivedPayloadError(
                f"{relative}: canonical source must be UTF-8"
            ) from exc
        match = _VERSION_PATTERN.search(text)
        if match is None:
            raise DerivedPayloadError(f"{relative}: missing canonical version and date")
        hashes[relative] = digest
        versions[relative] = match.group("version")
        dates.append(match.group("date"))
        lines.append(f"canonical-source: {relative} sha256={digest}")
    versions["derived_at"] = max(dates)
    return lines, hashes, versions


def _render_template(raw: bytes, relative: str, versions: dict[str, str]) -> bytes:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DerivedPayloadError(
            f"{relative}: adapter template must be UTF-8"
        ) from exc
    replacements = {
        "{{DERIVED_AT}}": versions["derived_at"],
        "{{CHARTER_VERSION}}": versions["CHARTER.md"],
        "{{CONTEXT_VERSION}}": versions["CONTEXT.md"],
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    if "{{" in text or "}}" in text:
        raise DerivedPayloadError(
            f"{relative}: unknown or incomplete template placeholder"
        )
    if not text:
        raise DerivedPayloadError(f"{relative}: adapter template is empty")
    if not text.endswith("\n"):
        raise DerivedPayloadError(
            f"{relative}: adapter template must end with a newline"
        )
    return text.encode("utf-8")


def render_derived_payloads(root: Path = REPOSITORY_ROOT) -> dict[str, bytes]:
    root = root.absolute()
    canonical_lines, _source_hashes, versions = _canonical_source_facts(root)
    rendered: dict[str, bytes] = {}
    for relative, spec in PAYLOAD_SPECS.items():
        template_raw = _read_regular_file(root, spec.template)
        body = _render_template(template_raw, spec.template, versions)
        header = [
            SCHEMA_LINE,
            *canonical_lines,
            f"adapter-template: {spec.template} sha256={_sha256(template_raw)}",
            f"derived-at: {versions['derived_at']}",
            f"deployment-status: {spec.status}",
            AUTHORITY_LINE,
            f"payload-body-sha256: {_sha256(body)}",
            END_LINE,
        ]
        rendered[relative] = "\n".join(header).encode("utf-8") + b"\n\n" + body
    return rendered


def _verify_payload(
    root: Path,
    relative: str,
    expected: bytes,
    expected_status: str,
) -> dict[str, object]:
    raw = _read_regular_file(root, relative)
    delimiter = f"{END_LINE}\n\n".encode()
    if raw.count(delimiter) != 1:
        raise DerivedPayloadError(
            f"{relative}: metadata terminator must occur exactly once"
        )
    header_raw, body = raw.split(delimiter, 1)
    try:
        header = header_raw.decode("utf-8").splitlines()
        body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DerivedPayloadError(f"{relative}: payload must be UTF-8") from exc
    if len(header) != 8 or header[0] != SCHEMA_LINE:
        raise DerivedPayloadError(f"{relative}: metadata schema or field count differs")
    if header[5] != f"deployment-status: {expected_status}":
        raise DerivedPayloadError(
            f"{relative}: deployment status differs from its admitted state"
        )
    if header[6] != AUTHORITY_LINE:
        raise DerivedPayloadError(
            f"{relative}: derived-only authority declaration differs"
        )
    if header[7] != f"payload-body-sha256: {_sha256(body)}":
        raise DerivedPayloadError(
            f"{relative}: payload body differs from its recorded identity"
        )
    if raw != expected:
        raise DerivedPayloadError(
            f"{relative}: payload differs from deterministic canonical generation"
        )
    return {
        "path": relative,
        "deployment_status": expected_status,
        "payload_sha256": _sha256(raw),
        "payload_body_sha256": _sha256(body),
    }


def verify_derived_payloads(root: Path = REPOSITORY_ROOT) -> dict[str, object]:
    root = root.absolute()
    _canonical_lines, source_hashes, _versions = _canonical_source_facts(root)
    rendered = render_derived_payloads(root)
    payloads = [
        _verify_payload(root, relative, rendered[relative], spec.status)
        for relative, spec in PAYLOAD_SPECS.items()
    ]
    return {
        "schema": "giga.derived-agent-payload-verification.v2",
        "status": "PASS",
        "canonical_sources": source_hashes,
        "payloads": payloads,
    }


def _write_atomic(root: Path, relative: str, content: bytes) -> None:
    destination = root / relative
    _read_regular_file(root, relative)
    parent = destination.parent
    parent_metadata = parent.lstat()
    if not stat.S_ISDIR(parent_metadata.st_mode) or parent.is_symlink():
        raise DerivedPayloadError(f"{relative}: destination parent is unsafe")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=parent)
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
        parent_descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_derived_payloads(root: Path = REPOSITORY_ROOT) -> list[str]:
    root = root.absolute()
    rendered = render_derived_payloads(root)
    current = {relative: _read_regular_file(root, relative) for relative in rendered}
    changed = [
        relative
        for relative, content in rendered.items()
        if current[relative] != content
    ]
    for relative in changed:
        content = rendered[relative]
        _write_atomic(root, relative, content)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument(
        "--write",
        action="store_true",
        help="atomically regenerate all tracked payloads before verification",
    )
    args = parser.parse_args()
    try:
        changed = write_derived_payloads(args.root) if args.write else []
        result = verify_derived_payloads(args.root)
    except DerivedPayloadError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    result["regenerated"] = changed
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
