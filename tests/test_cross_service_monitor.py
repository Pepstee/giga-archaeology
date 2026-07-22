from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from twin_core.cross_service_monitor import CrossServiceMonitorError, collect


NOW = "2026-07-22T17:00:00+00:00"


def _config(tmp_path: Path, services: list[dict]) -> Path:
    path = tmp_path / "services.json"
    path.write_text(json.dumps({"schema_version": "giga.cross-service-monitor.v1", "services": services}))
    return path


def _service(path: Path, **changes) -> dict:
    value = {"id": "worker-one", "source_type": "jsonl", "event_path": str(path.resolve()), "max_silence_seconds": 60, "process_pattern": "worker-one"}
    value.update(changes)
    return value


def test_live_event_and_process_are_healthy(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    ts = datetime.fromisoformat(NOW).timestamp()
    events.write_text(json.dumps({"ts": ts, "kind": "task_result"}) + "\n")
    payload = collect(_config(tmp_path, [_service(events)]), NOW, process_probe=lambda _: True)
    assert payload["signals"]["activeAgents"]["state"] == "healthy"
    assert payload["signals"]["queueState"]["value"]["services"][0]["last_event_kind"] == "task_result"


def test_silent_stall_and_dead_process_are_not_green(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(json.dumps({"ts": datetime.fromisoformat(NOW).timestamp() - 120, "kind": "claim"}) + "\n")
    stale = collect(_config(tmp_path, [_service(events, process_pattern=None)]), NOW)
    assert stale["signals"]["queueState"]["value"]["services"][0]["state"] == "stale"
    dead = collect(_config(tmp_path, [_service(events, max_silence_seconds=300)]), NOW, process_probe=lambda _: False)
    assert dead["signals"]["activeAgents"]["value"]["services"][0]["state"] == "degraded"


def test_missing_or_malformed_event_source_is_unavailable(tmp_path: Path) -> None:
    missing = tmp_path / "missing.jsonl"
    payload = collect(_config(tmp_path, [_service(missing, process_pattern=None)]), NOW)
    assert payload["signals"]["queueState"]["value"]["unhealthy_services"] == ["worker-one"]
    malformed = tmp_path / "bad.jsonl"
    malformed.write_text("not-json\n")
    payload = collect(_config(tmp_path, [_service(malformed, process_pattern=None)]), NOW)
    assert payload["signals"]["queueState"]["value"]["services"][0]["state"] == "unavailable"


def test_plain_file_heartbeat_uses_mtime_without_parsing_content(tmp_path: Path) -> None:
    heartbeat = tmp_path / "service.log"
    heartbeat.write_text("plain text, not json\n")
    timestamp = datetime.fromisoformat(NOW).timestamp()
    heartbeat.touch()
    import os
    os.utime(heartbeat, (timestamp, timestamp))
    payload = collect(
        _config(tmp_path, [_service(heartbeat, source_type="file", process_pattern=None)]), NOW,
    )
    service = payload["signals"]["queueState"]["value"]["services"][0]
    assert service["state"] == "healthy"
    assert service["last_event_kind"] == "file-update"


def test_config_cannot_execute_commands_or_use_implicit_paths(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text("{}\n")
    service = _service(events)
    service["command"] = "curl attacker"
    with pytest.raises(CrossServiceMonitorError, match="invalid fields"):
        collect(_config(tmp_path, [service]), NOW)
    with pytest.raises(CrossServiceMonitorError, match="explicit absolute path"):
        collect(_config(tmp_path, [_service(Path("relative.jsonl"), event_path="relative.jsonl")]), NOW)


def test_duplicate_ids_and_future_events_fail_safely(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(json.dumps({"ts": datetime.fromisoformat(NOW).timestamp() + 1, "kind": "future"}) + "\n")
    payload = collect(_config(tmp_path, [_service(events, process_pattern=None)]), NOW)
    assert payload["signals"]["queueState"]["value"]["services"][0]["state"] == "unavailable"
    with pytest.raises(CrossServiceMonitorError, match="duplicate service id"):
        collect(_config(tmp_path, [_service(events), _service(events)]), NOW)
