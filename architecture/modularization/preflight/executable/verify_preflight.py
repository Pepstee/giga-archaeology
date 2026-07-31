#!/usr/bin/env python3
"""Verify the Wave 0B preflight and private recovery seal without modifying them."""
from __future__ import annotations
import argparse, hashlib, json, os, stat
from pathlib import Path

DEFAULT_ROOT = Path("/Users/admin/Documents/giga-user")
DEFAULT_BACKUP = Path("/Users/admin/.giga/backups/giga-modularization-preflight-20260730")

def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()

def verify_manifest(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = []
    base = path.parent
    entries = data.get("entries", [])
    canonical = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != data.get("manifest_digest"):
        errors.append(f"manifest digest mismatch: {path}")
    for entry in entries:
        target = base / entry["path"]
        if not target.is_file():
            errors.append(f"missing: {target}")
        elif target.stat().st_size != entry["size"] or digest(target) != entry["sha256"]:
            errors.append(f"changed: {target}")
    return errors

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--backup", type=Path, default=DEFAULT_BACKUP)
    args = parser.parse_args()
    output = args.root / "architecture/modularization/preflight/executable"
    errors = verify_manifest(output / "preflight-manifest.json")
    errors += verify_manifest(args.backup / "backup-manifest.json")
    backup_mode = stat.S_IMODE(args.backup.stat().st_mode)
    if backup_mode & 0o077:
        errors.append(f"backup is not owner-only: {args.backup} mode={backup_mode:o}")
    for path in args.backup.iterdir():
        if path.is_file() and stat.S_IMODE(path.stat().st_mode) & 0o077:
            errors.append(f"backup file is not owner-only: {path}")
    result = {"ok": not errors, "errors": errors, "output": str(output), "backup": str(args.backup)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
