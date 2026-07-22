#!/usr/bin/env python3
"""Write a compact read-only health snapshot for SSH/Tailscale retrieval."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def unit_state(name: str) -> str:
    result = subprocess.run(
        ("systemctl", "is-active", name), text=True, capture_output=True, check=False,
    )
    return (result.stdout or result.stderr).strip() or f"exit-{result.returncode}"


def counts(path: Path) -> dict[str, int | str]:
    wanted = {
        "postings", "normalised_jobs", "scores", "pipeline_jobs",
        "employer_research_queue",
    }
    result: dict[str, int | str] = {}
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            tables = {
                str(row[0]) for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for table in sorted(tables & wanted):
                result[table] = int(
                    connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                )
            result["integrity_check"] = str(
                connection.execute("PRAGMA quick_check").fetchone()[0]
            )
    except (OSError, sqlite3.DatabaseError) as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--orchestrator-root", type=Path, required=True)
    args = parser.parse_args()
    payload = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": os.uname().nodename,
        "units": {
            name: unit_state(name)
            for name in (
                "orchestrator-v3.service",
                "market-aligner-collector.service",
                "market-aligner-processor.timer",
                "giga-database-backup.timer",
            )
        },
        "databases": {
            "jobs": counts(args.shared / "jobs.sqlite3"),
            "career": counts(args.shared / "career_pipeline.sqlite3"),
        },
        "orchestrator": {
            "stop_armed": (args.orchestrator_root / "STOP").exists(),
            "event_log_bytes": (
                (args.orchestrator_root / "state/tasks.events.log").stat().st_size
                if (args.orchestrator_root / "state/tasks.events.log").is_file() else 0
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
