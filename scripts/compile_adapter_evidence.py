#!/usr/bin/env python3
"""Compile and verify repository-local adapter evidence."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from twin_core.adapter_evidence import (  # noqa: E402
    AdapterEvidenceError,
    canonical_json,
    compile_registry,
    render_summary,
)


def _destination(root: Path, relative: str | Path) -> Path:
    relative = Path(relative)
    if relative.is_absolute():
        raise AdapterEvidenceError("absolute output paths are forbidden")
    destination = (root / relative).resolve()
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise AdapterEvidenceError("output path escapes repository root") from exc
    return destination


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--observed-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--manifest-dir", default="adapters/manifests")
    parser.add_argument("--stale-after-seconds", type=int, default=30 * 86_400)
    parser.add_argument("--output", default="outputs/adapter-evidence/registry.json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        payload = compile_registry(
            root,
            args.observed_at,
            manifest_dir=args.manifest_dir,
            stale_after_seconds=args.stale_after_seconds,
        )
        serialized = canonical_json(payload)
        if not args.no_write:
            _write_atomic(_destination(root, args.output), serialized)
        sys.stdout.write(serialized if args.json else render_summary(payload))
        return 0
    except (AdapterEvidenceError, OSError) as exc:
        print(f"adapter-evidence: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
