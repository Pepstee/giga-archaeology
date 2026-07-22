#!/usr/bin/env python3
"""Create consistent, checksummed SQLite backups without interrupting writers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--keep", type=int, default=30)
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.destination.resolve() / stamp
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema_version": 1, "created_at_utc": stamp, "databases": {}}
    names = ("jobs.sqlite3", "career_pipeline.sqlite3", "scrapling_elements.sqlite3")
    for name in names:
        source = args.source.resolve() / name
        if not source.is_file():
            raise RuntimeError(f"authoritative database is missing: {source}")
        destination = output / name
        with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as target:
            source_connection.backup(target)
        with sqlite3.connect(f"file:{destination}?mode=ro&immutable=1", uri=True) as check:
            integrity = str(check.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise RuntimeError(f"backup integrity failed for {destination}: {integrity}")
        receipt["databases"][name] = {
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
            "integrity_check": integrity,
        }
    (output / "manifest.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )

    completed = sorted(
        path for path in args.destination.resolve().iterdir()
        if path.is_dir() and (path / "manifest.json").is_file()
    )
    for expired in completed[:-max(1, args.keep)]:
        for child in expired.iterdir():
            if child.is_file():
                child.unlink()
        expired.rmdir()
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
