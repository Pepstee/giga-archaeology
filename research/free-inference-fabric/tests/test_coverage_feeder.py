from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("coverage_feeder", ROOT / "scripts/coverage_feeder.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def report(missing: list[int] | None = None) -> dict:
    missing = [37, 39] if missing is None else missing
    return {
        "files": {
            "src/giga_inference_fabric/source_packets.py": {
                "summary": {
                    "covered_lines": 125,
                    "missing_lines": len(missing),
                    "num_statements": 127,
                    "percent_covered": 98.425,
                },
                "missing_lines": missing,
            }
        }
    }


def test_coverage_observation_is_deterministic_and_source_bound():
    first = MODULE.coverage_observation(report())
    second = MODULE.coverage_observation(report([39, 37, 39]))
    assert first == second
    assert first["target_sha256"]
    assert set(first["test_sha256"]) == {
        "tests/test_source_packets.py",
        "tests/test_source_packet_generation_benchmark.py",
    }


def test_coverage_observation_rejects_missing_or_ambiguous_target():
    with pytest.raises(ValueError, match="files object"):
        MODULE.coverage_observation({})
    payload = report()
    payload["files"]["copy/source_packets.py"] = payload["files"]["src/giga_inference_fabric/source_packets.py"]
    with pytest.raises(ValueError, match="exactly one"):
        MODULE.coverage_observation(payload)


def test_measure_refuses_failed_test_command(monkeypatch):
    class Failed:
        returncode = 1
        stdout = "collection failed"
        stderr = ""

    monkeypatch.setattr(MODULE.subprocess, "run", lambda *args, **kwargs: Failed())
    with pytest.raises(RuntimeError, match="failed closed"):
        MODULE.measure()


def test_benchmark_target_binding_is_current():
    assert MODULE.benchmark_matches_target() is True


def test_benchmark_target_binding_rejects_stale_packet(tmp_path: Path, monkeypatch):
    packet = tmp_path / "source-packet.json"
    packet.write_text(json.dumps({
        "files": [{
            "path": "src/giga_inference_fabric/source_packets.py",
            "sha256": "0" * 64,
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(MODULE, "SOURCE_PACKET", packet)
    assert MODULE.benchmark_matches_target() is False


def test_v1_state_migrates_to_complete_admission_history(tmp_path: Path):
    state = tmp_path / "feeder.json"
    state.write_text(json.dumps({
        "schema": "giga.coverage-feeder-state.v1",
        "last_observed": MODULE.BOOTSTRAP_FINGERPRINT,
        "last_enqueued": MODULE.BOOTSTRAP_FINGERPRINT,
        "work_id": MODULE.BOOTSTRAP_WORK_ID,
    }), encoding="utf-8")
    migrated = MODULE.read_state(state)
    assert migrated == {
        "schema": "giga.coverage-feeder-state.v2",
        "last_observed": MODULE.BOOTSTRAP_FINGERPRINT,
        "admitted_fingerprints": {
            MODULE.BOOTSTRAP_FINGERPRINT: MODULE.BOOTSTRAP_WORK_ID,
        },
    }


def test_refresh_then_current_gap_becomes_ready_not_no_change():
    changed = "1" * 64
    state = {
        "schema": "giga.coverage-feeder-state.v2",
        "last_observed": changed,
        "admitted_fingerprints": {MODULE.BOOTSTRAP_FINGERPRINT: MODULE.BOOTSTRAP_WORK_ID},
    }
    assert MODULE.decide_status(
        state, fingerprint=changed, pending=None, benchmark_current=False,
    ) == "BENCHMARK_REFRESH_REQUIRED"
    assert MODULE.decide_status(
        state, fingerprint=changed, pending=None, benchmark_current=True,
    ) == "READY_TO_ENQUEUE"


def test_history_prevents_repeat_and_state_loss_cannot_misbind_pending_work():
    admitted = {
        "schema": "giga.coverage-feeder-state.v2",
        "last_observed": "2" * 64,
        "admitted_fingerprints": {"2" * 64: "work-two", "3" * 64: "work-three"},
    }
    assert MODULE.decide_status(
        admitted, fingerprint="2" * 64, pending=None, benchmark_current=True,
    ) == "NO_CHANGE"
    empty = {
        "schema": "giga.coverage-feeder-state.v2",
        "last_observed": None,
        "admitted_fingerprints": {},
    }
    assert MODULE.decide_status(
        empty, fingerprint="4" * 64, pending=MODULE.BOOTSTRAP_WORK_ID,
        benchmark_current=True,
    ) == "DEFER_PENDING"
    assert MODULE.decide_status(
        empty, fingerprint=MODULE.BOOTSTRAP_FINGERPRINT,
        pending=MODULE.BOOTSTRAP_WORK_ID, benchmark_current=True,
    ) == "BOUND_TO_PENDING"
