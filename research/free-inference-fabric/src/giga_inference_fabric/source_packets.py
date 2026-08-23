from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath


SCHEMA = "giga.source-packet.v1"
DEFAULT_MAX_TOTAL_BYTES = 200_000
DEFAULT_MAX_FILE_BYTES = 100_000
DEFAULT_MAX_PACKET_BYTES = 1_000_000
DENIED_NAMES = {".env", "auth.json", "credentials.json", "id_rsa", "id_ed25519"}
DENIED_SUFFIXES = {".pem", ".p12", ".pfx", ".key"}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


def _canonical_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalise_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str):
        raise ValueError("source packet path must be a string")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or path == PurePosixPath(".") or ".." in path.parts:
        raise ValueError(f"source packet path must be a bounded relative path: {value!r}")
    if path.name in DENIED_NAMES or path.suffix.lower() in DENIED_SUFFIXES:
        raise ValueError(f"source packet path is secret-bearing by policy: {value}")
    if any(part in {".git", ".svn", "node_modules", "__pycache__"} for part in path.parts):
        raise ValueError(f"source packet path enters a denied directory: {value}")
    return path


def _read_admitted_file(root: Path, relative: PurePosixPath, max_file_bytes: int) -> dict:
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"source packet file traverses a symlink: {relative}")
    resolved = cursor.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError(f"source packet file escapes the admitted root: {relative}")
    data = resolved.read_bytes()
    if len(data) > max_file_bytes:
        raise ValueError(f"source packet file exceeds per-file byte cap: {relative}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"source packet file is not strict UTF-8 text: {relative}") from exc
    if "\x00" in text or "\r" in text:
        raise ValueError(f"source packet file contains unsupported binary/CR content: {relative}")
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        raise ValueError(f"source packet file matches a high-confidence secret pattern: {relative}")
    trailing_newline = text.endswith("\n")
    if not text:
        lines: list[str] = []
    elif trailing_newline:
        lines = text[:-1].split("\n")
    else:
        lines = text.split("\n")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "line_count": len(lines),
        "trailing_newline": trailing_newline,
        "lines": lines,
    }


def build_source_packet(
    source_root: Path,
    project: str,
    files: list[str],
    *,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> dict:
    if not isinstance(project, str) or not project.strip():
        raise ValueError("source packet project must be non-empty")
    if max_total_bytes < 1 or max_file_bytes < 1 or max_file_bytes > max_total_bytes:
        raise ValueError("source packet byte caps must be positive and internally consistent")
    if source_root.is_symlink():
        raise ValueError("source packet root cannot be a symlink")
    root = source_root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("source packet root must be a directory")
    if not files:
        raise ValueError("source packet requires at least one explicit file")
    relative_files = [_normalise_relative_path(value) for value in files]
    if len(set(relative_files)) != len(relative_files):
        raise ValueError("source packet contains duplicate file paths")
    rows = [
        _read_admitted_file(root, relative, max_file_bytes)
        for relative in sorted(relative_files, key=lambda item: item.as_posix())
    ]
    total_bytes = sum(row["bytes"] for row in rows)
    if total_bytes > max_total_bytes:
        raise ValueError("source packet exceeds total byte cap")
    payload = {
        "schema": SCHEMA,
        "project": project.strip(),
        "total_source_bytes": total_bytes,
        "files": rows,
    }
    return {**payload, "packet_sha256": _canonical_hash(payload)}


def verify_source_packet(
    packet: dict,
    *,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> dict:
    if max_total_bytes < 1 or max_file_bytes < 1 or max_file_bytes > max_total_bytes:
        raise ValueError("source packet byte caps must be positive and internally consistent")
    if set(packet) != {"schema", "project", "total_source_bytes", "files", "packet_sha256"}:
        raise ValueError("source packet has unknown or missing top-level fields")
    if (
        packet["schema"] != SCHEMA
        or not isinstance(packet["project"], str)
        or not packet["project"].strip()
        or packet["project"] != packet["project"].strip()
    ):
        raise ValueError("source packet identity is invalid")
    rows = packet["files"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("source packet files must be a non-empty list")
    expected_fields = {"path", "sha256", "bytes", "line_count", "trailing_newline", "lines"}
    seen = set()
    total = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise ValueError("source packet file row is malformed")
        relative = _normalise_relative_path(row["path"])
        if relative.as_posix() in seen:
            raise ValueError("source packet repeats a file path")
        seen.add(relative.as_posix())
        if (
            not isinstance(row["sha256"], str)
            or not isinstance(row["bytes"], int)
            or isinstance(row["bytes"], bool)
            or row["bytes"] < 0
            or not isinstance(row["line_count"], int)
            or isinstance(row["line_count"], bool)
            or row["line_count"] < 0
            or not isinstance(row["lines"], list)
            or not all(isinstance(line, str) for line in row["lines"])
        ):
            raise ValueError("source packet lines are malformed")
        if row["line_count"] != len(row["lines"]) or not isinstance(row["trailing_newline"], bool):
            raise ValueError("source packet line metadata is inconsistent")
        text = "\n".join(row["lines"]) + ("\n" if row["trailing_newline"] else "")
        data = text.encode("utf-8")
        if row["bytes"] != len(data) or row["sha256"] != hashlib.sha256(data).hexdigest():
            raise ValueError("source packet file content hash is invalid")
        if len(data) > max_file_bytes:
            raise ValueError("source packet file exceeds per-file byte cap")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            raise ValueError("source packet contains a high-confidence secret pattern")
        total += len(data)
    if rows != sorted(rows, key=lambda row: row["path"]):
        raise ValueError("source packet file order is non-deterministic")
    if (
        not isinstance(packet["total_source_bytes"], int)
        or isinstance(packet["total_source_bytes"], bool)
        or packet["total_source_bytes"] != total
        or total > max_total_bytes
    ):
        raise ValueError("source packet total byte count is invalid")
    payload = {key: value for key, value in packet.items() if key != "packet_sha256"}
    if (
        not isinstance(packet["packet_sha256"], str)
        or packet["packet_sha256"] != _canonical_hash(payload)
    ):
        raise ValueError("source packet binding hash is invalid")
    return packet


def load_source_packet(
    path: Path,
    *,
    max_packet_bytes: int = DEFAULT_MAX_PACKET_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("source packet must be a regular non-symlink file")
    if max_packet_bytes < 1 or path.stat().st_size > max_packet_bytes:
        raise ValueError("source packet JSON exceeds transport byte cap")
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("source packet is not valid JSON") from exc
    if not isinstance(packet, dict):
        raise ValueError("source packet root must be an object")
    return verify_source_packet(
        packet, max_total_bytes=max_total_bytes, max_file_bytes=max_file_bytes,
    )
