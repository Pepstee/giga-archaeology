#!/usr/bin/env python3
"""Create and compare content manifests for the Gigabyte factory migration.

The manifest follows no symlinks and binds every included path, entry type, portable mode,
regular-file size/hash and symlink target. Ownership and mtimes are deliberately omitted because
the migration crosses macOS and WSL; they are not content identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from datetime import datetime, timezone
from typing import Any, Iterable


SCHEMA = "giga.factory-tree-manifest.v1"
RECEIPT_SCHEMA = "giga.factory-tree-comparison.v1"
CHUNK_BYTES = 1024 * 1024


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalise_excludes(values: Iterable[str]) -> tuple[str, ...]:
    normalised: set[str] = set()
    for value in values:
        candidate = str(PurePosixPath(value.strip().lstrip("/")))
        if candidate in ("", ".") or candidate == ".." or candidate.startswith("../"):
            raise ValueError(f"unsafe exclude: {value!r}")
        normalised.add(candidate.rstrip("/"))
    return tuple(sorted(normalised))


def _excluded(relative: str, excludes: tuple[str, ...]) -> bool:
    return any(relative == item or relative.startswith(item + "/") for item in excludes)


def _entry(path: Path, relative: str) -> dict[str, Any]:
    info = path.lstat()
    mode = format(stat.S_IMODE(info.st_mode), "04o")
    base: dict[str, Any] = {"path": relative, "mode": mode}
    if stat.S_ISREG(info.st_mode):
        base.update(type="file", size=info.st_size, sha256=_sha256_file(path))
    elif stat.S_ISDIR(info.st_mode):
        base.update(type="directory")
    elif stat.S_ISLNK(info.st_mode):
        # Symlink permission bits are not portable. macOS commonly reports 0755 while
        # Linux reports 0777 and does not permit chmod(2) to change the link itself.
        # Bind the target exactly and use one canonical cross-platform mode.
        base.update(type="symlink", mode="0777", target=os.readlink(path))
    elif stat.S_ISFIFO(info.st_mode):
        base.update(type="fifo")
    elif stat.S_ISSOCK(info.st_mode):
        base.update(type="socket")
    elif stat.S_ISCHR(info.st_mode):
        base.update(type="character-device", device=info.st_rdev)
    elif stat.S_ISBLK(info.st_mode):
        base.update(type="block-device", device=info.st_rdev)
    else:
        base.update(type="unknown")
    return base


def _walk(root: Path, excludes: tuple[str, ...]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    def visit(directory: Path, prefix: str = "") -> None:
        with os.scandir(directory) as iterator:
            children = sorted(iterator, key=lambda item: item.name)
        for child in children:
            relative = f"{prefix}/{child.name}" if prefix else child.name
            if _excluded(relative, excludes):
                continue
            path = Path(child.path)
            item = _entry(path, relative)
            entries.append(item)
            if item["type"] == "directory":
                visit(path, relative)
            if len(entries) % 5000 == 0:
                print(f"manifested {len(entries):,} entries", file=sys.stderr, flush=True)

    visit(root)
    return entries


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def create_manifest(root: Path, output: Path, excludes: tuple[str, ...]) -> None:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"manifest root is not a directory: {root}")
    entries = _walk(root, excludes)
    payload = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "excludes": list(excludes),
        "entry_count": len(entries),
        "file_count": sum(item["type"] == "file" for item in entries),
        "regular_file_bytes": sum(item.get("size", 0) for item in entries),
        "entries": entries,
    }
    payload["content_digest"] = _sha256_json(entries)
    _atomic_json(output, payload)
    print(
        f"{root}: {payload['entry_count']:,} entries, {payload['file_count']:,} files, "
        f"{payload['regular_file_bytes']:,} bytes, digest {payload['content_digest']}"
    )


def compare_manifests(source_path: Path, destination_path: Path, output: Path) -> bool:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    destination = json.loads(destination_path.read_text(encoding="utf-8"))
    for label, manifest in (("source", source), ("destination", destination)):
        if manifest.get("schema") != SCHEMA:
            raise ValueError(f"{label} manifest has unsupported schema")
        if _sha256_json(manifest.get("entries")) != manifest.get("content_digest"):
            raise ValueError(f"{label} manifest content digest is invalid")

    source_entries = {item["path"]: item for item in source["entries"]}
    destination_entries = {item["path"]: item for item in destination["entries"]}
    missing = sorted(source_entries.keys() - destination_entries.keys())
    unexpected = sorted(destination_entries.keys() - source_entries.keys())
    changed = sorted(
        path
        for path in source_entries.keys() & destination_entries.keys()
        if source_entries[path] != destination_entries[path]
    )
    passed = not missing and not unexpected and not changed
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "source_manifest_sha256": _sha256_file(source_path),
        "destination_manifest_sha256": _sha256_file(destination_path),
        "source_content_digest": source["content_digest"],
        "destination_content_digest": destination["content_digest"],
        "source_entry_count": source["entry_count"],
        "destination_entry_count": destination["entry_count"],
        "missing_count": len(missing),
        "unexpected_count": len(unexpected),
        "changed_count": len(changed),
        "missing": missing[:100],
        "unexpected": unexpected[:100],
        "changed": changed[:100],
        "difference_lists_truncated_at": 100,
    }
    _atomic_json(output, receipt)
    print(
        f"passed={passed} missing={len(missing)} unexpected={len(unexpected)} "
        f"changed={len(changed)}"
    )
    return passed


def prune_appledouble(
    root: Path,
    source_path: Path,
    destination_path: Path,
    output: Path,
) -> None:
    """Remove only manifest-proven AppleDouble transfer artefacts.

    macOS archive tools may add ``._*`` regular files containing extended-attribute
    metadata. They are not source-tree entries. This operation fails closed unless every
    destination-only entry is a regular ``._*`` file whose current bytes still match the
    destination manifest. No source path, directory, symlink or non-AppleDouble path can be
    removed by this command.
    """
    root = root.resolve(strict=True)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    destination = json.loads(destination_path.read_text(encoding="utf-8"))
    for label, manifest in (("source", source), ("destination", destination)):
        if manifest.get("schema") != SCHEMA:
            raise ValueError(f"{label} manifest has unsupported schema")
        if _sha256_json(manifest.get("entries")) != manifest.get("content_digest"):
            raise ValueError(f"{label} manifest content digest is invalid")

    source_entries = {item["path"]: item for item in source["entries"]}
    destination_entries = {item["path"]: item for item in destination["entries"]}
    unexpected = sorted(destination_entries.keys() - source_entries.keys())
    if not unexpected:
        raise ValueError("destination manifest contains no unexpected entries")

    rejected = [
        relative
        for relative in unexpected
        if not Path(relative).name.startswith("._")
        or destination_entries[relative].get("type") != "file"
    ]
    if rejected:
        preview = json.dumps(rejected[:100], ensure_ascii=False)
        raise ValueError(
            f"destination has {len(rejected)} non-AppleDouble unexpected entries: {preview}"
        )

    approved: list[tuple[Path, dict[str, Any]]] = []
    for relative in unexpected:
        item = destination_entries[relative]
        path = root / relative
        current = _entry(path, relative)
        if current != item:
            raise ValueError(f"AppleDouble candidate changed since manifest: {relative}")
        approved.append((path, item))

    removed_bytes = sum(item.get("size", 0) for _, item in approved)
    for path, _ in approved:
        path.unlink()

    receipt = {
        "schema": "giga.factory-appledouble-prune.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "source_manifest_sha256": _sha256_file(source_path),
        "destination_manifest_sha256": _sha256_file(destination_path),
        "removed_count": len(approved),
        "removed_bytes": removed_bytes,
        "removed_paths_digest": _sha256_json(unexpected),
    }
    _atomic_json(output, receipt)
    print(f"removed={len(approved)} bytes={removed_bytes}")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("--root", type=Path, required=True)
    manifest.add_argument("--output", type=Path, required=True)
    manifest.add_argument("--exclude", action="append", default=[])
    compare = subparsers.add_parser("compare")
    compare.add_argument("--source", type=Path, required=True)
    compare.add_argument("--destination", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)
    prune = subparsers.add_parser("prune-appledouble")
    prune.add_argument("--root", type=Path, required=True)
    prune.add_argument("--source", type=Path, required=True)
    prune.add_argument("--destination", type=Path, required=True)
    prune.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    if arguments.command == "manifest":
        create_manifest(
            arguments.root,
            arguments.output,
            _normalise_excludes(arguments.exclude),
        )
        return 0
    if arguments.command == "compare":
        return 0 if compare_manifests(arguments.source, arguments.destination, arguments.output) else 1
    prune_appledouble(
        arguments.root,
        arguments.source,
        arguments.destination,
        arguments.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
