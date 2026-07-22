"""Machine-derived health snapshot for the current GIGA runtime."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import subprocess
from pathlib import Path
from typing import Any

from .memory_validation import validate_memory
from .store import DEFAULT_DATABASE, TwinStore


def _mode(path: Path) -> str | None:
    return oct(stat.S_IMODE(path.stat().st_mode)) if path.exists() else None


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _process_running(pattern: str) -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern], capture_output=True, text=True, timeout=3, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _prediction_stats(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"predictions": 0, "open": 0, "adjudications": 0, "runs": 0}
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    try:
        return {
            "predictions": int(connection.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]),
            "open": int(connection.execute("SELECT COUNT(*) FROM predictions WHERE resolved_at IS NULL").fetchone()[0]),
            "adjudications": int(connection.execute("SELECT COUNT(*) FROM auto_prediction_adjudications").fetchone()[0]),
            "runs": int(connection.execute("SELECT COUNT(*) FROM auto_prediction_runs").fetchone()[0]),
        }
    finally:
        connection.close()


def snapshot(giga_root: Path, database: Path = DEFAULT_DATABASE) -> dict[str, Any]:
    giga_root = giga_root.resolve()
    jarvis = Path.home() / ".jarvis"
    raw = giga_root / "corpus" / "raw"
    snapshots = sorted(raw.glob("prompts_*.jsonl"))
    current = snapshots[-1] if snapshots else None
    state_path = jarvis / "daily_knowledge_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    store = TwinStore(database)
    memory = validate_memory(giga_root / "memory")
    prediction = _prediction_stats(jarvis / "prediction_ledger.sqlite3")
    return {
        "giga_root": str(giga_root),
        "memory": memory,
        "corpus": {
            "current_snapshot": str(current) if current else None,
            "current_records": _line_count(current) if current else 0,
            "current_sha256": _sha256(current) if current else None,
        },
        "daily": {
            "seen_fingerprints": len(state.get("seen", [])),
            "last_success_vietnam": state.get("last_success_vietnam"),
            "last_provider": state.get("last_provider"),
        },
        "prediction": prediction,
        "processes": {"jarvis": _process_running("scripts/jarvis_telegram.py")},
        "permissions": {
            "jarvis_dir": _mode(jarvis),
            "config": _mode(jarvis / "config.json"),
            "state": _mode(state_path),
            "offset": _mode(jarvis / "offset.json"),
            "twin_dir": _mode(database.expanduser().resolve().parent),
            "twin_database": _mode(database.expanduser().resolve()),
        },
        "twin_store": store.counts(),
    }

