from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from modules.operations.archaeologist.evidence import (
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
)
from modules.operations.archaeologist.retention import (
    RetentionError,
    RetentionPolicy,
    compact_inactive_generation,
    plan_navigation_retention,
    restore_compacted_generation,
    run_navigation_retention,
)


def _private(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)
    return path


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    path.write_bytes(raw)
    os.chmod(path, 0o600)


def _run_id(day: int, suffix: str) -> str:
    return f"202608{day:02d}T000000.000000Z-{suffix:0>12}"


def _success_run(
    store: Path, kind: str, run_id: str, previous: str | None = None
) -> dict:
    _private(store / "runs")
    run = _private(store / "runs" / run_id)
    scan = {
        "finished_at": f"2026-08-{int(run_id[6:8]):02d}T00:00:00.000000Z",
        "incremental_from": previous,
    }
    if kind in {"inventory", "mapper"}:
        name = "inventory.sqlite3" if kind == "inventory" else "facts.sqlite3"
        raw = f"{kind}:{run_id}".encode()
        _write(run / name, raw)
        manifest = seal_document(
            {
                "schema": f"fixture.{kind}.v1",
                "run_id": run_id,
                "scan": scan,
                "database": {
                    "path": name,
                    "sha256": sha256_bytes(raw),
                    "bytes": len(raw),
                },
            }
        )
    else:
        graph = b'{"nodes":[],"edges":[]}'
        raw_graph = b'{"nodes":[],"edges":[],"raw":true}'
        _write(run / "graphify-out/graph.json", graph)
        _write(run / "graphify-out/graph.raw.json", raw_graph)
        manifest = seal_document(
            {
                "schema": "fixture.semantic.v1",
                "run_id": run_id,
                "scan": scan,
                "graph": {
                    "path": "graphify-out/graph.json",
                    "sha256": sha256_bytes(graph),
                    "bytes": len(graph),
                    "raw_path": "graphify-out/graph.raw.json",
                    "raw_sha256": sha256_bytes(raw_graph),
                    "raw_bytes": len(raw_graph),
                },
            }
        )
    _write(run / "manifest.json", canonical_bytes(manifest))
    return manifest


def _point_current(store: Path, kind: str, manifest: dict) -> None:
    schemas = {
        "inventory": "giga.navigation.current-pointer.v1",
        "mapper": "giga.archaeologist.mapper-current-pointer.v1",
        "semantic": "giga.navigation.semantic-current-pointer.v1",
    }
    pointer = seal_document(
        {
            "schema": schemas[kind],
            "run_id": manifest["run_id"],
            "manifest_file_sha256": sha256_bytes(
                (store / "runs" / manifest["run_id"] / "manifest.json").read_bytes()
            ),
            "manifest_receipt_sha256": manifest["receipt_sha256"],
        }
    )
    _write(store / "CURRENT.json", canonical_bytes(pointer))


def _fixture_stores(
    tmp_path: Path, *, inventory_ids: list[str] | None = None
) -> tuple[Path, Path, Path, list[str]]:
    inventory = _private(tmp_path / "inventory")
    mapper = _private(tmp_path / "mapper")
    semantic = _private(tmp_path / "semantic")
    ids = inventory_ids or [_run_id(day, f"i{day}") for day in range(1, 6)]
    previous = None
    manifests = []
    for run_id in ids:
        manifests.append(_success_run(inventory, "inventory", run_id, previous))
        previous = run_id
    _point_current(inventory, "inventory", manifests[-1])
    mapper_manifest = _success_run(mapper, "mapper", _run_id(5, "mapper"))
    mapper_manifest["inventory"] = {"run_id": ids[-1]}
    mapper_manifest = seal_document(
        {
            key: value
            for key, value in mapper_manifest.items()
            if key != "receipt_sha256"
        }
    )
    _write(
        mapper / "runs" / mapper_manifest["run_id"] / "manifest.json",
        canonical_bytes(mapper_manifest),
    )
    _point_current(mapper, "mapper", mapper_manifest)
    semantic_manifest = _success_run(semantic, "semantic", _run_id(5, "semantic"))
    semantic_manifest["inventory"] = {"run_id": ids[-1]}
    semantic_manifest = seal_document(
        {
            key: value
            for key, value in semantic_manifest.items()
            if key != "receipt_sha256"
        }
    )
    _write(
        semantic / "runs" / semantic_manifest["run_id"] / "manifest.json",
        canonical_bytes(semantic_manifest),
    )
    _point_current(semantic, "semantic", semantic_manifest)
    return inventory, mapper, semantic, ids


def _policy(*, grace: int = 1000) -> RetentionPolicy:
    return RetentionPolicy(
        keep_successes=2,
        keep_failures=1,
        min_age_seconds=0,
        quarantine_grace_seconds=grace,
        inventory_max_bytes=1,
        mapper_max_bytes=1024 * 1024,
        semantic_max_bytes=1024 * 1024,
        failure_max_bytes=1,
    )


def test_plan_preserves_current_predecessor_recent_and_external_references(
    tmp_path: Path,
) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    references = _private(tmp_path / "references")
    _write(references / "receipt.json", json.dumps({"run_id": ids[0]}).encode())

    plan = plan_navigation_retention(
        inventory,
        mapper,
        semantic,
        reference_roots=(references,),
        policy=_policy(),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    validate_self_hash(plan)
    assert plan["status"] == "MIXED_CANDIDATES"
    inventory_plan = next(
        item for item in plan["stores"] if item["kind"] == "inventory"
    )
    by_id = {item["run_id"]: item for item in inventory_plan["generations"]}
    assert by_id[ids[0]]["disposition"] == "RETAIN"
    assert by_id[ids[0]]["external_references"] == [str(references / "receipt.json")]
    assert by_id[ids[0]]["compaction_disposition"] == "COMPACT_CANDIDATE"
    assert by_id[ids[-1]]["reasons"] == [
        "inventory:CURRENT",
        "mapper:current.inventory",
        "recent-recovery-window",
        "semantic:current.inventory",
    ]
    assert "inventory:current.incremental_from" in by_id[ids[-2]]["reasons"]
    assert {
        item["run_id"]
        for item in inventory_plan["generations"]
        if item["disposition"] == "QUARANTINE_CANDIDATE"
    } == {ids[1], ids[2]}


def test_plan_quarantines_generations_outside_newest_three_before_24_hours(
    tmp_path: Path,
) -> None:
    ids = [f"20260830T00000{second}.000000Z-same{second:08d}" for second in range(5)]
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path, inventory_ids=ids)
    policy = RetentionPolicy(
        keep_successes=3,
        keep_failures=2,
        min_age_seconds=24 * 60 * 60,
        quarantine_grace_seconds=7 * 24 * 60 * 60,
        inventory_max_bytes=256 * 1024 * 1024,
        mapper_max_bytes=2 * 1024 * 1024 * 1024,
        semantic_max_bytes=2 * 1024 * 1024 * 1024,
        failure_max_bytes=512 * 1024 * 1024,
    )

    plan = plan_navigation_retention(
        inventory,
        mapper,
        semantic,
        policy=policy,
        now=datetime(2026, 8, 30, 0, 5, tzinfo=UTC),
    )

    validate_self_hash(plan)
    assert plan["status"] == "QUARANTINE_CANDIDATES"
    inventory_plan = next(
        item for item in plan["stores"] if item["kind"] == "inventory"
    )
    assert inventory_plan["total_bytes"] < inventory_plan["quota_bytes"]
    ordered = sorted(
        inventory_plan["generations"], key=lambda item: item["generation_rank"]
    )
    assert [item["generation_rank"] for item in ordered] == [1, 2, 3, 4, 5]
    assert all(item["age_seconds"] < policy.min_age_seconds for item in ordered)
    assert {
        item["run_id"]
        for item in ordered
        if item["disposition"] == "QUARANTINE_CANDIDATE"
    } == set(ids[:2])
    assert all(not item["stale_by_age"] for item in ordered)
    assert [item["stale_by_generation"] for item in ordered] == [
        False,
        False,
        False,
        True,
        True,
    ]


def test_incomplete_reference_scan_fails_closed_without_candidates(
    tmp_path: Path,
) -> None:
    inventory, mapper, semantic, _ids = _fixture_stores(tmp_path)
    references = _private(tmp_path / "references")
    (references / "unsafe").symlink_to(tmp_path / "missing")

    plan = plan_navigation_retention(
        inventory,
        mapper,
        semantic,
        reference_roots=(references,),
        policy=_policy(),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    assert plan["status"] == "PARTIAL_NO_ACTION"
    assert plan["reference_scan_complete"] is False
    assert plan["candidate_generations"] == 0


def test_apply_quarantines_then_later_purges_and_keeps_receipts(tmp_path: Path) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    first = datetime(2026, 8, 30, tzinfo=UTC)

    applied = run_navigation_retention(
        inventory,
        mapper,
        semantic,
        policy=_policy(grace=3600),
        apply=True,
        now=first,
    )

    validate_self_hash(applied)
    assert applied["quarantine"]["generations"] == 3
    assert not (inventory / "runs" / ids[0]).exists()
    assert not (inventory / "runs" / ids[1]).exists()
    assert not (inventory / "runs" / ids[2]).exists()
    assert (inventory / "runs" / ids[-1]).exists()
    assert applied["purges"] == []

    purged = run_navigation_retention(
        inventory,
        mapper,
        semantic,
        policy=_policy(grace=3600),
        apply=True,
        now=first + timedelta(hours=2),
    )

    assert len(purged["purges"]) == 1
    assert purged["purges"][0]["generations"] == 3
    assert purged["purges"][0]["bytes_reclaimed"] > 0
    quarantine = semantic / "retention/quarantine"
    first_batch = next(
        path for path in quarantine.iterdir() if (path / "purge.json").exists()
    )
    validate_self_hash(json.loads((first_batch / "intent.json").read_text()))
    validate_self_hash(json.loads((first_batch / "outcome.json").read_text()))
    validate_self_hash(json.loads((first_batch / "purge.json").read_text()))
    assert not any((first_batch / "inventory").glob("*"))


def test_quarantine_failure_rolls_back_every_moved_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    real_rename = os.rename
    moved = 0

    def fail_second(
        source: os.PathLike[str] | str, destination: os.PathLike[str] | str
    ) -> None:
        nonlocal moved
        if "/runs/" in str(source) and "/quarantine/" in str(destination):
            moved += 1
            if moved == 2:
                raise OSError("injected quarantine failure")
        real_rename(source, destination)

    monkeypatch.setattr(
        "modules.operations.archaeologist.retention.os.rename", fail_second
    )
    with pytest.raises(OSError, match="injected quarantine failure"):
        run_navigation_retention(
            inventory,
            mapper,
            semantic,
            policy=_policy(),
            apply=True,
            now=datetime(2026, 8, 30, tzinfo=UTC),
        )
    assert all((inventory / "runs" / run_id).is_dir() for run_id in ids)
    outcomes = list((semantic / "retention/quarantine").glob("*/outcome.json"))
    assert len(outcomes) == 1
    assert json.loads(outcomes[0].read_text())["status"] == "ROLLED_BACK"


def test_corrupt_current_pointer_refuses_before_any_move(tmp_path: Path) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    pointer = json.loads((inventory / "CURRENT.json").read_text())
    pointer["run_id"] = ids[0]
    _write(inventory / "CURRENT.json", canonical_bytes(pointer))

    with pytest.raises(RetentionError, match="CURRENT pointer self-hash mismatch"):
        run_navigation_retention(
            inventory,
            mapper,
            semantic,
            policy=_policy(),
            apply=True,
            now=datetime(2026, 8, 30, tzinfo=UTC),
        )
    assert all((inventory / "runs" / run_id).is_dir() for run_id in ids)


def test_reference_appearing_after_plan_refuses_before_quarantine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    real_scan = __import__(
        "modules.operations.archaeologist.retention", fromlist=["_external_references"]
    )._external_references
    calls = 0

    def reference_race(run_ids, roots):
        nonlocal calls
        calls += 1
        if calls == 2:
            return ({next(iter(run_ids)): ["/new/reference.json"]}, [])
        return real_scan(run_ids, roots)

    monkeypatch.setattr(
        "modules.operations.archaeologist.retention._external_references",
        reference_race,
    )
    with pytest.raises(RetentionError, match="changed between planning and quarantine"):
        run_navigation_retention(
            inventory,
            mapper,
            semantic,
            policy=_policy(),
            apply=True,
            now=datetime(2026, 8, 30, tzinfo=UTC),
        )
    assert all((inventory / "runs" / run_id).is_dir() for run_id in ids)


def test_semantic_failure_payload_purge_preserves_failure_receipts(
    tmp_path: Path,
) -> None:
    inventory, mapper, semantic, _ids = _fixture_stores(tmp_path)
    failures = _private(semantic / "failures")
    failure_ids = [_run_id(day, f"failure{day}") for day in range(1, 4)]
    for run_id in failure_ids:
        directory = _private(failures / run_id)
        receipt = seal_document(
            {
                "schema": "giga.navigation.semantic-refresh-failure.v1",
                "status": "FAILED_NOT_CURRENT",
                "run_id": run_id,
                "failed_at": f"2026-08-{int(run_id[6:8]):02d}T00:00:00Z",
            }
        )
        _write(directory / "failure.json", canonical_bytes(receipt))
        _write(directory / "large-staging.bin", b"x" * 128)

    _private(semantic / "retention")
    preserved = _private(semantic / "retention/failure-receipts")
    _write(
        preserved / f"{failure_ids[0]}.json",
        (failures / failure_ids[0] / "failure.json").read_bytes(),
    )

    result = run_navigation_retention(
        inventory,
        mapper,
        semantic,
        policy=_policy(grace=0),
        apply=True,
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    assert result["purges"]
    assert (preserved / f"{failure_ids[0]}.json").is_file()
    assert (preserved / f"{failure_ids[1]}.json").is_file()
    validate_self_hash(json.loads((preserved / f"{failure_ids[0]}.json").read_text()))
    assert (failures / failure_ids[-1]).is_dir()


def test_interrupted_intent_without_outcome_is_rolled_back_on_next_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    module = __import__(
        "modules.operations.archaeologist.retention", fromlist=["_write_create_once"]
    )
    real_write = module._write_create_once
    interrupted = False

    def interrupt_outcome(path: Path, payload) -> None:
        nonlocal interrupted
        if path.name == "outcome.json" and not interrupted:
            interrupted = True
            raise SystemExit("injected process death after quarantine moves")
        real_write(path, payload)

    monkeypatch.setattr(
        "modules.operations.archaeologist.retention._write_create_once",
        interrupt_outcome,
    )
    with pytest.raises(SystemExit, match="injected process death"):
        run_navigation_retention(
            inventory,
            mapper,
            semantic,
            policy=_policy(),
            apply=True,
            now=datetime(2026, 8, 30, tzinfo=UTC),
        )
    assert not (inventory / "runs" / ids[0]).exists()

    recovered = run_navigation_retention(
        inventory,
        mapper,
        semantic,
        policy=_policy(),
        apply=False,
        now=datetime(2026, 8, 30, 0, 1, tzinfo=UTC),
    )

    assert len(recovered["recovered_quarantines"]) == 1
    assert all((inventory / "runs" / run_id).is_dir() for run_id in ids)
    outcomes = list((semantic / "retention/quarantine").glob("*/outcome.json"))
    assert len(outcomes) == 1
    outcome = json.loads(outcomes[0].read_text())
    validate_self_hash(outcome)
    assert outcome["status"] == "ROLLED_BACK_INTERRUPTED"


def test_referenced_stale_database_is_compacted_and_exactly_restorable(
    tmp_path: Path,
) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    references = _private(tmp_path / "references")
    _write(references / "receipt.json", ids[0].encode())
    run = inventory / "runs" / ids[0]
    raw_path = run / "inventory.sqlite3"
    expected = raw_path.read_bytes()

    applied = run_navigation_retention(
        inventory,
        mapper,
        semantic,
        reference_roots=(references,),
        policy=_policy(grace=3600),
        apply=True,
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    assert len(applied["compactions"]) == 1
    assert applied["compactions"][0]["run_id"] == ids[0]
    assert not raw_path.exists()
    compressed = run / "inventory.sqlite3.gz"
    assert compressed.is_file()
    assert compressed.read_bytes()[4:8] == b"\0\0\0\0"
    receipt = json.loads((run / "compaction.json").read_text())
    validate_self_hash(receipt)
    assert receipt["source"]["sha256"] == sha256_bytes(expected)
    assert receipt["compressed"]["algorithm"] == "gzip-9-mtime-zero"

    restored = restore_compacted_generation("inventory", run)

    validate_self_hash(restored)
    assert restored["status"] == "RESTORED"
    assert raw_path.read_bytes() == expected
    assert raw_path.stat().st_mode & 0o777 == 0o600
    assert restore_compacted_generation("inventory", run)["status"] == (
        "ALREADY_RESTORED"
    )


def test_corrupt_preexisting_gzip_refuses_without_removing_raw_database(
    tmp_path: Path,
) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    references = _private(tmp_path / "references")
    _write(references / "receipt.json", ids[0].encode())
    run = inventory / "runs" / ids[0]
    raw_path = run / "inventory.sqlite3"
    expected = raw_path.read_bytes()
    _write(run / "inventory.sqlite3.gz", b"not-the-authenticated-gzip")

    with pytest.raises(RetentionError, match="pre-existing compressed map differs"):
        run_navigation_retention(
            inventory,
            mapper,
            semantic,
            reference_roots=(references,),
            policy=_policy(),
            apply=True,
            now=datetime(2026, 8, 30, tzinfo=UTC),
        )

    assert raw_path.read_bytes() == expected
    assert not (run / "compaction.json").exists()


def test_failure_before_compaction_receipt_preserves_raw_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    references = _private(tmp_path / "references")
    _write(references / "receipt.json", ids[0].encode())
    run = inventory / "runs" / ids[0]
    raw_path = run / "inventory.sqlite3"
    expected = raw_path.read_bytes()
    module = __import__(
        "modules.operations.archaeologist.retention", fromlist=["_write_create_once"]
    )
    real_write = module._write_create_once

    def fail_receipt(path: Path, payload) -> None:
        if path.name == "compaction.json":
            raise OSError("injected compaction receipt failure")
        real_write(path, payload)

    monkeypatch.setattr(
        "modules.operations.archaeologist.retention._write_create_once", fail_receipt
    )
    with pytest.raises(OSError, match="injected compaction receipt failure"):
        run_navigation_retention(
            inventory,
            mapper,
            semantic,
            reference_roots=(references,),
            policy=_policy(),
            apply=True,
            now=datetime(2026, 8, 30, tzinfo=UTC),
        )
    assert raw_path.read_bytes() == expected
    assert (run / "inventory.sqlite3.gz").is_file()
    assert not (run / "compaction.json").exists()

    monkeypatch.setattr(
        "modules.operations.archaeologist.retention._write_create_once", real_write
    )
    resumed = run_navigation_retention(
        inventory,
        mapper,
        semantic,
        reference_roots=(references,),
        policy=_policy(),
        apply=True,
        now=datetime(2026, 8, 30, 0, 1, tzinfo=UTC),
    )
    assert len(resumed["compactions"]) == 1
    assert not raw_path.exists()


def test_current_and_recent_databases_are_never_compaction_candidates(
    tmp_path: Path,
) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    references = _private(tmp_path / "references")
    _write(references / "receipt.json", "\n".join(ids[-2:]).encode())

    plan = plan_navigation_retention(
        inventory,
        mapper,
        semantic,
        reference_roots=(references,),
        policy=_policy(),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    inventory_plan = next(
        item for item in plan["stores"] if item["kind"] == "inventory"
    )
    by_id = {item["run_id"]: item for item in inventory_plan["generations"]}
    assert by_id[ids[-1]]["compaction_disposition"] == "RETAIN_RAW"
    assert by_id[ids[-2]]["compaction_disposition"] == "RETAIN_RAW"


def test_explicit_inactive_current_generation_is_compacted_and_restorable(
    tmp_path: Path,
) -> None:
    inventory, _mapper, _semantic, ids = _fixture_stores(tmp_path)
    run = inventory / "runs" / ids[-1]
    raw_path = run / "inventory.sqlite3"
    expected = raw_path.read_bytes()
    pointer_before = (inventory / "CURRENT.json").read_bytes()

    result = compact_inactive_generation(
        "inventory",
        run,
        inactive_reason="superseded milestone map; source and manifest retained",
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    validate_self_hash(result)
    assert result["status"] == "PASS"
    assert result["run_id"] == ids[-1]
    assert result["source_bytes"] == len(expected)
    assert result["logical_bytes_reclaimed"] >= 0
    assert not raw_path.exists()
    assert (run / "inventory.sqlite3.gz").is_file()
    assert (inventory / "CURRENT.json").read_bytes() == pointer_before

    restored = restore_compacted_generation("inventory", run)
    assert restored["status"] == "RESTORED"
    assert raw_path.read_bytes() == expected


@pytest.mark.parametrize("reason", ["", "\x00unsafe"])
def test_inactive_compaction_requires_a_bounded_truthful_reason(
    tmp_path: Path, reason: str
) -> None:
    inventory, _mapper, _semantic, ids = _fixture_stores(tmp_path)
    run = inventory / "runs" / ids[-1]

    with pytest.raises(RetentionError, match="reason is invalid"):
        compact_inactive_generation(
            "inventory",
            run,
            inactive_reason=reason,
        )

    assert (run / "inventory.sqlite3").is_file()
