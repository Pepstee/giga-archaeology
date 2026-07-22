"""Read-only cross-service heartbeat and queue telemetry for operator status."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


SCHEMA = "giga.cross-service-monitor.v1"
RUNTIME_SCHEMA = "giga.operator-status-evidence.v1"
MAX_CONFIG_BYTES = 256 * 1024
MAX_TAIL_BYTES = 1024 * 1024
STATES = ("healthy", "degraded", "stale", "unavailable")


class CrossServiceMonitorError(ValueError):
    """Raised when a monitor declaration or observed event is unsafe or malformed."""


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise CrossServiceMonitorError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CrossServiceMonitorError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CrossServiceMonitorError("timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _read_config(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CrossServiceMonitorError("monitor config must be a regular non-symlink file")
    if path.stat().st_size > MAX_CONFIG_BYTES:
        raise CrossServiceMonitorError("monitor config is too large")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CrossServiceMonitorError("monitor config is malformed") from exc
    if not isinstance(value, dict):
        raise CrossServiceMonitorError("monitor config must be an object")
    return value


def _process_running(pattern: str) -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern], capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _tail_json(path: Path) -> Mapping[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CrossServiceMonitorError("event source is not a regular non-symlink file")
    size = path.stat().st_size
    with path.open("rb") as handle:
        handle.seek(max(0, size - MAX_TAIL_BYTES))
        raw = handle.read(MAX_TAIL_BYTES)
    lines = [line for line in raw.splitlines() if line.strip()]
    if not lines:
        raise CrossServiceMonitorError("event source is empty")
    try:
        event = json.loads(lines[-1].decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CrossServiceMonitorError("last event is malformed") from exc
    if not isinstance(event, dict):
        raise CrossServiceMonitorError("last event must be an object")
    return event


def _validate_service(record: Any) -> dict[str, Any]:
    required = {"id", "source_type", "event_path", "max_silence_seconds", "process_pattern"}
    if not isinstance(record, dict) or set(record) != required:
        raise CrossServiceMonitorError("service declaration has invalid fields")
    service_id = record["id"]
    if not isinstance(service_id, str) or not service_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in service_id):
        raise CrossServiceMonitorError("service id must be lowercase kebab-case")
    event_path = record["event_path"]
    if not isinstance(event_path, str) or not Path(event_path).is_absolute():
        raise CrossServiceMonitorError("event_path must be an explicit absolute path")
    if record["source_type"] not in {"jsonl", "file"}:
        raise CrossServiceMonitorError("source_type must be jsonl or file")
    silence = record["max_silence_seconds"]
    if isinstance(silence, bool) or not isinstance(silence, int) or silence < 0:
        raise CrossServiceMonitorError("max_silence_seconds must be non-negative")
    pattern = record["process_pattern"]
    if pattern is not None and (not isinstance(pattern, str) or not pattern.strip()):
        raise CrossServiceMonitorError("process_pattern must be null or a non-empty string")
    return record


def collect(
    config_path: Path,
    observed_at: str,
    *,
    process_probe: Callable[[str], bool] = _process_running,
) -> dict[str, Any]:
    """Collect bounded observations; configuration never supplies executable commands."""
    now = _timestamp(observed_at)
    config = _read_config(config_path)
    if set(config) != {"schema_version", "services"} or config["schema_version"] != SCHEMA:
        raise CrossServiceMonitorError("unsupported monitor config schema")
    services = config["services"]
    if not isinstance(services, list) or not services:
        raise CrossServiceMonitorError("services must be a non-empty array")
    records: list[dict[str, Any]] = []
    ids: set[str] = set()
    for raw in services:
        service = _validate_service(raw)
        if service["id"] in ids:
            raise CrossServiceMonitorError(f"duplicate service id: {service['id']}")
        ids.add(service["id"])
        path = Path(service["event_path"])
        running = None if service["process_pattern"] is None else process_probe(service["process_pattern"])
        try:
            if service["source_type"] == "jsonl":
                event = _tail_json(path)
                event_ts = event.get("ts")
                if isinstance(event_ts, (int, float)) and not isinstance(event_ts, bool):
                    last_at = datetime.fromtimestamp(event_ts, timezone.utc)
                else:
                    last_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                event_kind = event.get("kind")
            else:
                if path.is_symlink() or not path.is_file():
                    raise CrossServiceMonitorError("heartbeat source is not a regular non-symlink file")
                last_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                event_kind = "file-update"
            age = (now - last_at).total_seconds()
            if age < 0:
                raise CrossServiceMonitorError("last event is dated in the future")
            state = "stale" if age > service["max_silence_seconds"] else "healthy"
            if running is False:
                state = "degraded"
            record = {
                "id": service["id"], "state": state, "running": running,
                "event_path": str(path), "last_event_at": last_at.isoformat(),
                "last_event_kind": event_kind, "age_seconds": age,
            }
        except (OSError, CrossServiceMonitorError) as exc:
            record = {
                "id": service["id"], "state": "unavailable", "running": running,
                "event_path": str(path), "last_event_at": None,
                "last_event_kind": None, "age_seconds": None, "error": str(exc),
            }
        records.append(record)
    records.sort(key=lambda item: item["id"])
    unhealthy = [item["id"] for item in records if item["state"] != "healthy"]
    running_count = sum(item["running"] is True for item in records)
    signal_state = "healthy" if not unhealthy else "degraded"
    return {
        "schema": RUNTIME_SCHEMA,
        "observed_at": observed_at,
        "signals": {
            "activeAgents": {
                "value": {"running_processes": running_count, "services": records},
                "state": signal_state,
            },
            "queueState": {
                "value": {"services": records, "unhealthy_services": unhealthy},
                "state": signal_state,
            },
        },
    }


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
