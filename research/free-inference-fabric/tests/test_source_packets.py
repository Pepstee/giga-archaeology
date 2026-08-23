from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from giga_inference_fabric.benchmarks import build_benchmark_contract
from giga_inference_fabric.cli import queue_add, source_packet, worker_once
from giga_inference_fabric.source_packets import (
    build_source_packet,
    load_source_packet,
    verify_source_packet,
)
from giga_inference_fabric.store import ExperimentStore


def test_source_packet_is_deterministic_portable_and_hash_bound(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "a.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
    (root / "b.json").write_text('{"enabled":true}\n', encoding="utf-8")
    first = build_source_packet(root, "example", ["b.json", "a.py"])
    second = build_source_packet(root, "example", ["a.py", "b.json"])
    assert first == second
    assert [row["path"] for row in first["files"]] == ["a.py", "b.json"]
    assert first["files"][0]["lines"][1] == "    return 42"
    assert verify_source_packet(first) is first

    output = tmp_path / "packet.json"
    output.write_text(json.dumps(first), encoding="utf-8")
    assert load_source_packet(output)["packet_sha256"] == first["packet_sha256"]
    first["files"][0]["lines"][1] = "    return 43"
    try:
        verify_source_packet(first)
    except ValueError as exc:
        assert "content hash" in str(exc)
    else:
        raise AssertionError("edited source packet content was accepted")


def test_source_packet_rejects_escape_symlink_and_high_confidence_secret(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("SAFE = True\n", encoding="utf-8")
    (root / "link.py").symlink_to(outside)
    for files, expected in [(["../outside.py"], "bounded relative"), (["link.py"], "symlink")]:
        try:
            build_source_packet(root, "example", files)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("unsafe source path was accepted")

    (root / "secret.txt").write_text(
        "-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n", encoding="utf-8",
    )
    try:
        build_source_packet(root, "example", ["secret.txt"])
    except ValueError as exc:
        assert "secret pattern" in str(exc)
    else:
        raise AssertionError("secret-bearing source file was accepted")


def test_source_packet_validation_is_total_and_caps_are_fail_closed(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "source.py").write_text("SAFE = True\n", encoding="utf-8")
    with pytest.raises(ValueError, match="internally consistent"):
        build_source_packet(root, "example", ["source.py"], max_total_bytes=1, max_file_bytes=2)
    packet = build_source_packet(root, "example", ["source.py"])
    packet["files"][0]["path"] = 7
    with pytest.raises(ValueError, match="must be a string"):
        verify_source_packet(packet)
    packet = build_source_packet(root, "example", ["source.py"])
    with pytest.raises(ValueError, match="per-file byte cap"):
        verify_source_packet(packet, max_total_bytes=20, max_file_bytes=5)


def test_source_packet_command_is_idempotent_and_refuses_drift(tmp_path: Path, capsys):
    root = tmp_path / "project"
    root.mkdir()
    (root / "source.py").write_text("SAFE = True\n", encoding="utf-8")
    output = tmp_path / "packet.json"
    args = SimpleNamespace(
        source_root=root, project="example", file=["source.py"],
        max_total_bytes=200_000, max_file_bytes=100_000, output=output,
    )
    assert source_packet(args) == 0
    first = output.read_bytes()
    capsys.readouterr()
    assert source_packet(args) == 0
    assert output.read_bytes() == first
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="refusing overwrite"):
        source_packet(args)


def test_queue_identity_binds_context_evaluator_and_returns_canonical_work_id(
    tmp_path: Path, capsys,
):
    db = tmp_path / "experiments.sqlite3"

    def args(context: str, required: list[str], work_id: str) -> SimpleNamespace:
        return SimpleNamespace(
            db=db, work_id=work_id, idempotency_key=None, project="example",
            workload="documentation", objective="document", prompt="return report",
            context=context, source_packet=None, require=required, forbid=[], check_command=[],
            evaluator_cwd=None, command_timeout=30, priority=0, max_attempts=2,
        )

    assert queue_add(args("packet-a", ["report"], "work-a")) == 0
    first = json.loads(capsys.readouterr().out)
    assert queue_add(args("packet-b", ["report"], "work-b")) == 0
    second = json.loads(capsys.readouterr().out)
    assert first["idempotency_key"] != second["idempotency_key"]
    assert queue_add(args("packet-a", ["report"], "bogus-new-id")) == 0
    duplicate = json.loads(capsys.readouterr().out)
    assert duplicate["inserted"] is False
    assert duplicate["work_id"] == "work-a"


def test_queue_rejects_source_packet_for_another_project(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "source.py").write_text("SAFE = True\n", encoding="utf-8")
    packet = build_source_packet(root, "project-a", ["source.py"])
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    args = SimpleNamespace(
        db=tmp_path / "experiments.sqlite3", work_id="work-a", idempotency_key=None,
        project="project-b", workload="documentation", objective="document",
        prompt="return report", context="", source_packet=packet_path, benchmark_id=None,
        require=["report"], forbid=[], check_command=[], evaluator_cwd=None,
        command_timeout=30, priority=0, max_attempts=2,
    )
    with pytest.raises(SystemExit, match="does not match"):
        queue_add(args)


def test_benchmark_queue_rechecks_immutable_binding_before_lease(
    tmp_path: Path, monkeypatch, capsys,
):
    fixture = tmp_path / "benchmark"
    fixture.mkdir()
    (fixture / "benchmark.json").write_text("{}\n", encoding="utf-8")
    verifier = fixture / "verify_candidate.py"
    verifier.write_text("raise SystemExit(0)\n", encoding="utf-8")
    binding = build_benchmark_contract(fixture, "python3 verify_candidate.py")
    db = tmp_path / "experiments.sqlite3"
    store = ExperimentStore(db)
    try:
        store.register_benchmark(
            "architecture-001", "example", "architecture-map", "map architecture",
            binding["fixture_ref"], "python3 verify_candidate.py", {"binding": binding},
        )
    finally:
        store.close()
    queue_args = SimpleNamespace(
        db=db, work_id="work-architecture", idempotency_key=None, project="example",
        workload="architecture-map", benchmark_id="architecture-001",
        objective="map architecture", prompt="return JSON", context="", source_packet=None,
        require=[], forbid=[], check_command=[], evaluator_cwd=None, command_timeout=30,
        priority=0, max_attempts=2,
    )
    assert queue_add(queue_args) == 0
    capsys.readouterr()
    verifier.write_text("raise SystemExit(1)\n", encoding="utf-8")
    monkeypatch.setattr(
        "giga_inference_fabric.cli.discover_openrouter_models",
        lambda: (_ for _ in ()).throw(AssertionError("discovery must not run on drift")),
    )
    worker_args = SimpleNamespace(
        db=db, lease_minutes=30, local_only=False, candidates=1, critics=0, rounds=1,
        daily_remote_limit=40, use_opencode_auth=True, free_model=[], local_model=[],
        local_base_url="http://127.0.0.1:11434/v1", privacy="internal",
        require_zdr=False, max_remote_calls=1, max_output_tokens=512,
        min_distinct_models=1,
    )
    with pytest.raises(SystemExit, match="drift"):
        worker_once(worker_args)
    store = ExperimentStore(db)
    try:
        row = store.connection.execute(
            "SELECT status,attempts,benchmark_id FROM work_queue WHERE work_id='work-architecture'"
        ).fetchone()
        assert tuple(row) == ("QUEUED", 0, "architecture-001")
    finally:
        store.close()


def test_worker_budget_wait_does_not_lease_or_discover_models(tmp_path: Path, monkeypatch, capsys):
    db = tmp_path / "experiments.sqlite3"
    store = ExperimentStore(db)
    try:
        store.enqueue(
            work_id="work-1", idempotency_key="one", project="example",
            workload="documentation", objective="document source", prompt="return report",
            context="bounded packet", evaluator={
                "schema": "giga.evaluator-contract.v1", "required": ["report"],
                "forbidden": [], "commands": [], "cwd": None, "timeout_seconds": 30,
            }, max_attempts=2,
        )
    finally:
        store.close()
    monkeypatch.setattr(
        "giga_inference_fabric.cli.discover_openrouter_models",
        lambda: (_ for _ in ()).throw(AssertionError("model discovery must not run")),
    )
    args = SimpleNamespace(
        db=db, lease_minutes=30, local_only=False, candidates=3, critics=2, rounds=4,
        daily_remote_limit=1, use_opencode_auth=True, free_model=[], local_model=[],
        local_base_url="http://127.0.0.1:11434/v1", privacy="internal",
        require_zdr=False, max_remote_calls=50, max_output_tokens=512,
        min_distinct_models=2,
    )
    assert worker_once(args) == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "BUDGET_WAIT" and payload["worst_case_remote_calls"] == 36
    store = ExperimentStore(db)
    try:
        row = store.connection.execute(
            "SELECT status,attempts FROM work_queue WHERE work_id='work-1'"
        ).fetchone()
        assert tuple(row) == ("QUEUED", 0)
    finally:
        store.close()


def test_worker_rejects_partially_admitted_cell_before_leasing(tmp_path: Path):
    db = tmp_path / "experiments.sqlite3"
    store = ExperimentStore(db)
    try:
        store.enqueue(
            work_id="work-1", idempotency_key="one", project="example",
            workload="documentation", objective="document source", prompt="return report",
            context="bounded packet", evaluator={
                "schema": "giga.evaluator-contract.v1", "required": ["report"],
                "forbidden": [], "commands": [], "cwd": None, "timeout_seconds": 30,
            }, max_attempts=2,
        )
    finally:
        store.close()
    args = SimpleNamespace(
        db=db, lease_minutes=30, local_only=False, candidates=2, critics=1, rounds=2,
        daily_remote_limit=40, use_opencode_auth=True, free_model=[], local_model=[],
        local_base_url="http://127.0.0.1:11434/v1", privacy="internal",
        require_zdr=False, max_remote_calls=7, max_output_tokens=512,
        min_distinct_models=2,
    )
    with pytest.raises(SystemExit, match="cannot admit"):
        worker_once(args)
    store = ExperimentStore(db)
    try:
        row = store.connection.execute(
            "SELECT status,attempts FROM work_queue WHERE work_id='work-1'"
        ).fetchone()
        assert tuple(row) == ("QUEUED", 0)
    finally:
        store.close()
