#!/usr/bin/env python3
"""Compile read-only cross-service telemetry for operator status."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from twin_core.cross_service_monitor import (  # noqa: E402
    CrossServiceMonitorError, canonical_json, collect,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=root / "monitoring/services.json")
    parser.add_argument("--observed-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--output", type=Path, default=root / "outputs/runtime/cross-services.json")
    args = parser.parse_args()
    try:
        payload = collect(args.config, args.observed_at)
        content = canonical_json(payload)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{args.output.name}.", dir=args.output.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, args.output)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
        sys.stdout.write(content)
        return 0
    except (CrossServiceMonitorError, OSError) as exc:
        print(f"cross-service-monitor: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
