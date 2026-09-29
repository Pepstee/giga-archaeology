from __future__ import annotations

import gzip
import json
import os
import sqlite3
import stat
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from modules.operations.archaeology.os_support import lock_file
from modules.operations.archaeology.evidence import (
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
)
from modules.operations.archaeology.retention import (
    DERIVED_MAP_ACTIVE_CONSUMER_REGISTRY_SCHEMA,
    M77_DERIVED_MAP_LIVENESS_OBSERVATION_SCHEMA,
    M77_SCOPED_DERIVED_MAP_LIVENESS_ASSESSMENT_SCHEMA,
    M77_TASK_LEASE_CENSUS_SCHEMA,
    M75_MAC_DERIVED_MAP_RETENTION_CANDIDATE_PLAN_SCHEMA,
    RETENTION_PLAN_SCHEMA,
    RETENTION_RUN_SCHEMA,
    RetentionError,
    RetentionPolicy,
    assess_cross_store_derived_map_lineage,
    assess_derived_family_retention,
    build_m74_private_ledger_binding_correction,
    build_m77_scoped_derived_map_liveness_assessment,
    compact_inactive_generation,
    compact_inactive_scip_generation,
    compact_inactive_semantic_generation,
    inspect_retention_receipt,
    plan_navigation_retention,
    recover_current_compacted_mapper,
    render_cross_store_derived_map_lineage_report,
    render_retention_receipt_inspection,
    render_m77_scoped_derived_map_liveness_report,
    restore_compacted_generation,
    restore_compacted_scip_generation,
    restore_compacted_semantic_generation,
    run_navigation_retention,
    run_scip_round_trip_canary,
    run_semantic_round_trip_canary,
    verify_compacted_generation_restore_stream,
    verify_scip_compacted_generation_restore_stream,
    verify_semantic_compacted_generation_restore_stream,
    write_cross_store_derived_map_lineage_assessment,
    write_m74_private_ledger_binding_correction,
    write_m75_mac_derived_map_retention_candidate_plan,
    observe_m77_derived_map_liveness,
    write_m77_scoped_derived_map_liveness_assessment,
)
from modules.operations.scripts.archaeology import main as archaeology_main


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


def _scip_run(store: Path, run_id: str) -> dict:
    _private(store / "runs")
    run = _private(store / "runs" / run_id)
    catalog = seal_document(
        {
            "schema": "giga.archaeologist.scip-store-catalog.v1",
            "status": "OBSERVED_LOCAL_PRECISION_STORE",
            "authority": "non-authoritative-atomic-code-intelligence-evidence",
            "authority_granted": False,
            "run_id": run_id,
            "generated_at": f"2026-08-{int(run_id[6:8]):02d}T00:00:00Z",
            "inventory": {"run_id": f"inventory-{run_id}"},
            "discovery": {"projects": [], "counts": {}, "receipt_sha256": "a" * 64},
            "indexes": [],
            "counts": {"indexes": 0, "documents": 0, "occurrences": 0, "bytes": 0},
            "publication": {
                "atomic": True,
                "previous_generation_preserved_on_failure": True,
                "source_text_embedded": False,
            },
        }
    )
    _write(run / "catalog.json", canonical_bytes(catalog))
    return catalog


def _scip_run_with_index(store: Path, run_id: str) -> dict:
    _private(store / "runs")
    run = _private(store / "runs" / run_id)
    project = _private(run / "projects" / "fixture-project")
    index = f"scip:{run_id}".encode()
    _write(project / "index.scip", index)
    project_manifest = seal_document(
        {
            "schema": "giga.archaeologist.scip-index-manifest.v1",
            "status": "OBSERVED_LOCAL_PRECISION_INDEX",
            "authority": "non-authoritative-optional-code-intelligence-evidence",
            "authority_granted": False,
            "generated_at": f"2026-08-{int(run_id[6:8]):02d}T00:00:00Z",
            "inventory": {"run_id": f"inventory-{run_id}"},
            "sources": {"excluded_files": []},
            "index": {
                "path": "index.scip",
                "sha256": sha256_bytes(index),
                "bytes": len(index),
            },
            "counts": {},
            "tool": {},
            "limitations": {},
        }
    )
    manifest_path = project / "manifest.json"
    _write(manifest_path, canonical_bytes(project_manifest))
    catalog = seal_document(
        {
            "schema": "giga.archaeologist.scip-store-catalog.v1",
            "status": "OBSERVED_LOCAL_PRECISION_STORE",
            "authority": "non-authoritative-atomic-code-intelligence-evidence",
            "authority_granted": False,
            "run_id": run_id,
            "generated_at": f"2026-08-{int(run_id[6:8]):02d}T00:00:00Z",
            "inventory": {"run_id": f"inventory-{run_id}"},
            "discovery": {"projects": [], "counts": {}, "receipt_sha256": "a" * 64},
            "indexes": [
                {
                    "project_id": "python:fixture",
                    "project_root": ".",
                    "language": "python",
                    "manifest_path": "projects/fixture-project/manifest.json",
                    "manifest_file_sha256": sha256_bytes(
                        canonical_bytes(project_manifest)
                    ),
                    "manifest_receipt_sha256": project_manifest["receipt_sha256"],
                    "index_sha256": sha256_bytes(index),
                    "index_bytes": len(index),
                    "source_closure_sha256": "b" * 64,
                    "documents": 1,
                    "occurrences": 1,
                    "excluded_files": 0,
                }
            ],
            "counts": {
                "indexes": 1,
                "documents": 1,
                "occurrences": 1,
                "bytes": len(index),
            },
            "publication": {
                "atomic": True,
                "previous_generation_preserved_on_failure": True,
                "source_text_embedded": False,
            },
        }
    )
    _write(run / "catalog.json", canonical_bytes(catalog))
    return catalog


def _point_scip_current(store: Path, catalog: dict) -> None:
    raw = (store / "runs" / catalog["run_id"] / "catalog.json").read_bytes()
    pointer = seal_document(
        {
            "schema": "giga.archaeologist.scip-store-current.v1",
            "status": catalog["status"],
            "run_id": catalog["run_id"],
            "catalog_file_sha256": sha256_bytes(raw),
            "catalog_receipt_sha256": catalog["receipt_sha256"],
            "updated_at": catalog["generated_at"],
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


def _inventory_plan(plan: dict) -> dict:
    return next(item for item in plan["stores"] if item["kind"] == "inventory")


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


def _git_command(repository: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repository), *args],
        text=True,
    ).strip()


def _source_repository(path: Path) -> Path:
    repository = _private(path)
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Fixture"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "<redacted-email>"],
        cwd=repository,
        check=True,
    )
    _write(repository / "source.txt", b"stable source\n")
    subprocess.run(["git", "add", "source.txt"], cwd=repository, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "stable source"],
        cwd=repository,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_DATE": "2026-08-01T00:00:00+0000",
            "GIT_COMMITTER_DATE": "2026-08-01T00:00:00+0000",
        },
    )
    return repository


def _git_identity(repository: Path, *, clean: bool = True) -> dict:
    return {
        "branch": "main",
        "head": _git_command(repository, "rev-parse", "HEAD"),
        "tree": _git_command(repository, "rev-parse", "HEAD^{tree}"),
        "stable_during_scan": True,
        "before": {"clean": clean},
        "after": {"clean": clean},
    }


def _bind_inventory_source(
    store: Path,
    manifest: dict,
    repository: Path,
    *,
    clean: bool = True,
) -> dict:
    unsigned = {key: value for key, value in manifest.items() if key != "receipt_sha256"}
    unsigned["schema"] = "giga.navigation.inventory-manifest.v2"
    unsigned["git"] = _git_identity(repository, clean=clean)
    unsigned["root"] = {
        "path": str(repository),
        "mode": 0o700,
        "uid": os.getuid(),
    }
    rebound = seal_document(unsigned)
    _write(
        store / "runs" / rebound["run_id"] / "manifest.json",
        canonical_bytes(rebound),
    )
    _point_current(store, "inventory", rebound)
    return rebound


def _single_inventory_store(
    runtime_root: Path,
    name: str,
    run_id: str,
    repository: Path,
    *,
    clean: bool = True,
) -> Path:
    store = _private(runtime_root / name)
    manifest = _success_run(store, "inventory", run_id)
    _bind_inventory_source(store, manifest, repository, clean=clean)
    return store


def _mapper_store_referencing_inventory(
    runtime_root: Path,
    name: str,
    run_id: str,
    repository: Path,
    inventory_run_id: str,
) -> Path:
    store = _private(runtime_root / name)
    manifest = _success_run(store, "mapper", run_id)
    unsigned = {key: value for key, value in manifest.items() if key != "receipt_sha256"}
    unsigned["schema"] = "giga.archaeologist.mapper-manifest.v2"
    unsigned["repository"] = {
        "git": _git_identity(repository, clean=True),
        "root": {"path": str(repository), "mode": 0o700, "uid": os.getuid()},
    }
    unsigned["inventory"] = {"run_id": inventory_run_id}
    rebound = seal_document(unsigned)
    _write(
        store / "runs" / rebound["run_id"] / "manifest.json",
        canonical_bytes(rebound),
    )
    _point_current(store, "mapper", rebound)
    return store


def _active_consumer_registry(
    *, active_run_ids: list[str] | None = None, negative_run_ids: list[str] | None = None
) -> dict:
    return seal_document(
        {
            "schema": DERIVED_MAP_ACTIVE_CONSUMER_REGISTRY_SCHEMA,
            "authority": "authoritative-derived-map-runtime-liveness",
            "active_run_ids": active_run_ids or [],
            "negative_run_ids": negative_run_ids or [],
        }
    )


def _regular_file_bytes(*roots: Path) -> int:
    total = 0
    for root in roots:
        for path in root.rglob("*"):
            metadata = path.lstat()
            if not path.is_symlink() and stat.S_ISREG(metadata.st_mode):
                total += metadata.st_size
    return total


def _m74_fixture_expected_counts(assessment: dict) -> dict[str, int]:
    return {
        "current_pointer_count": assessment["scope"]["current_pointer_count"],
        "derived_store_family_count": assessment["scope"][
            "derived_store_family_count"
        ],
        "metadata_store_family_count": assessment["scope"][
            "non_payload_current_store_count"
        ],
        "generation_records": assessment["counts"]["generation_records"],
        "payload_records": assessment["counts"]["payload_records"],
        "regular_file_count": assessment["byte_accounting"]["regular_file_count"],
        "regular_file_bytes": assessment["byte_accounting"]["regular_file_bytes"],
    }


def _m74_binding_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    layout_name: str = "operator_private_layout",
    active_consumer_registry: dict | None = None,
) -> tuple[dict, dict, Path, Path]:
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._payload_open_consumer_status",
        lambda _path: {"status": "NONE"},
    )
    layout = _private(tmp_path / layout_name)
    source = _source_repository(layout / "source")
    runtime_a = _private(layout / "runtime-a")
    runtime_b = _private(layout / "runtime-b")
    run_ids = [_run_id(day, "m74layout") for day in range(1, 5)]
    for index, run_id in enumerate(run_ids):
        _single_inventory_store(
            runtime_a if index % 2 == 0 else runtime_b,
            f"store-{index}",
            run_id,
            source,
        )
    parent_assessment_path = _private(layout / "public") / "assessment.json"
    private_ledger_path = _private(layout / "private-ledgers") / "ledger.json"
    assessment = write_cross_store_derived_map_lineage_assessment(
        (runtime_a, runtime_b),
        public_output=parent_assessment_path,
        private_ledger_output=private_ledger_path,
        active_consumer_registry=active_consumer_registry,
        now=datetime(2026, 8, 31, tzinfo=UTC),
    )
    ledger = json.loads(private_ledger_path.read_text(encoding="utf-8"))
    for generation in ledger["generations"]:
        if generation.get("current_status") is None:
            generation["current_status"] = "CURRENT"
    ledger_unsigned = dict(ledger)
    del ledger_unsigned["receipt_sha256"]
    ledger = seal_document(ledger_unsigned)
    _write(private_ledger_path, canonical_bytes(ledger))
    validate_self_hash(ledger)
    return assessment, ledger, parent_assessment_path, private_ledger_path


def _m75_multi_run_binding_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    active_consumer_registry: dict | None = None,
    dirty_oldest: bool = False,
) -> tuple[dict, dict, Path, Path, list[str]]:
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._payload_open_consumer_status",
        lambda _path: {"status": "NONE"},
    )
    layout = _private(tmp_path / "operator_private_layout")
    source = _source_repository(layout / "source")
    runtime = _private(layout / "runtime")
    store = _private(runtime / "store")
    run_ids = [_run_id(day, "m75lineage") for day in range(1, 5)]
    previous = None
    for index, run_id in enumerate(run_ids):
        manifest = _success_run(store, "inventory", run_id, previous)
        _bind_inventory_source(
            store,
            manifest,
            source,
            clean=not (dirty_oldest and index == 0),
        )
        previous = run_id
    parent_assessment_path = _private(layout / "public") / "assessment.json"
    private_ledger_path = _private(layout / "private-ledgers") / "ledger.json"
    assessment = write_cross_store_derived_map_lineage_assessment(
        (runtime,),
        public_output=parent_assessment_path,
        private_ledger_output=private_ledger_path,
        active_consumer_registry=active_consumer_registry,
        now=datetime(2026, 8, 31, tzinfo=UTC),
    )
    ledger = json.loads(private_ledger_path.read_text(encoding="utf-8"))
    for generation in ledger["generations"]:
        if generation.get("current_status") is None:
            generation["current_status"] = "CURRENT"
    ledger_unsigned = dict(ledger)
    del ledger_unsigned["receipt_sha256"]
    ledger = seal_document(ledger_unsigned)
    _write(private_ledger_path, canonical_bytes(ledger))
    validate_self_hash(ledger)
    return assessment, ledger, parent_assessment_path, private_ledger_path, run_ids


def _m75_graph_status() -> dict:
    return {
        "queried_existing_graph_first": True,
        "reported_status": "PARTIAL_STALE",
        "local_graph_output_present": False,
        "runtime_graph_outputs_observed": 1,
        "refresh_performed": False,
        "covers_m75_current_commit": False,
        "covers_m69_to_m74_current_census": False,
        "reason": "existing_graph_index_does_not_cover_current_milestone",
    }


def _m74_correction_for_fixture(
    assessment: dict,
    ledger: dict,
    *,
    now: datetime | None = None,
) -> dict:
    return build_m74_private_ledger_binding_correction(
        assessment,
        ledger,
        now=now or datetime(2026, 8, 31, 1, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
    )


def _write_m75_resealed_ledger(
    tmp_path: Path,
    ledger: dict,
    label: str,
    mutate,
) -> tuple[dict, Path]:
    mutated = json.loads(canonical_bytes(ledger))
    del mutated["receipt_sha256"]
    mutate(mutated)
    resealed = seal_document(mutated)
    ledger_path = _private(tmp_path / f"m75-{label}") / "ledger.json"
    _write(ledger_path, canonical_bytes(resealed))
    validate_self_hash(resealed)
    return resealed, ledger_path


def _m77_graph_status() -> dict:
    return {
        "queried_existing_graph_first": True,
        "reported_status": "PARTIAL_STALE",
        "local_graph_output_present": False,
        "runtime_graph_outputs_observed": 2,
        "refresh_performed": False,
        "covers_m77_current_commit": False,
        "covers_m76_to_m77_candidate": False,
        "reason": "existing_graph_index_does_not_cover_current_m77_candidate",
    }


def _m77_alias_census(
    schema: str,
    aliases: tuple[str, ...],
    *,
    active: tuple[str, ...] = (),
    unknown: tuple[str, ...] = (),
) -> dict:
    return seal_document(
        {
            "schema": schema,
            "status": "COMPLETE",
            "covered_generation_aliases": list(aliases),
            "active_generation_aliases": list(active),
            "unknown_generation_aliases": list(unknown),
        }
    )


def _m77_complete_task_census(aliases: tuple[str, ...]) -> dict:
    return _m77_alias_census(M77_TASK_LEASE_CENSUS_SCHEMA, aliases)


def _m77_complete_capability_liveness(aliases: tuple[str, ...]) -> dict:
    return _m77_alias_census(
        "giga.archaeology.capability-adoption-liveness-binding.v1",
        aliases,
    )


def _m77_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    active_consumer_registry: dict | None = None,
    dirty_oldest: bool = False,
) -> tuple[dict, dict, dict, dict, Path, Path, Path, Path, tuple[str, ...], dict]:
    run_ids = [_run_id(day, "m75lineage") for day in range(1, 5)]
    assessment, ledger, assessment_path, ledger_path, _run_ids = (
        _m75_multi_run_binding_fixture(
            tmp_path,
            monkeypatch,
            active_consumer_registry=active_consumer_registry
            or _active_consumer_registry(
                active_run_ids=[run_ids[-1]],
                negative_run_ids=run_ids[:-1],
            ),
            dirty_oldest=dirty_oldest,
        )
    )
    correction = _m74_correction_for_fixture(assessment, ledger)
    correction_path = _private(tmp_path / "m77-m74-correction") / "correction.json"
    _write(correction_path, canonical_bytes(correction))
    m75_path = _private(tmp_path / "m77-m75") / "plan.json"
    plan = write_m75_mac_derived_map_retention_candidate_plan(
        assessment_path,
        ledger_path,
        correction_path,
        m75_path,
        graph_status=_m75_graph_status(),
        now=datetime(2026, 8, 31, 12, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
    )
    cohort_aliases = ("generation-000004",)
    cohort_row = next(
        row
        for row in plan["generations"]
        if row["plan_generation_alias"] == cohort_aliases[0]
    )
    expected_cohort_bytes = {
        cohort_aliases[0]: (cohort_row["kind"], cohort_row["payload_bytes"])
    }
    return (
        assessment,
        ledger,
        correction,
        plan,
        assessment_path,
        ledger_path,
        correction_path,
        m75_path,
        cohort_aliases,
        expected_cohort_bytes,
    )


def _m77_patch_clean_liveness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._m77_process_argv_evidence",
        lambda aliases: {
            "status": "COMPLETE",
            "active_generation_aliases": [],
            "matched_process_count": 0,
        },
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._m77_launchd_evidence",
        lambda: {
            "status": "COMPLETE",
            "observed_label_count": 2,
            "active_label_count": 0,
        },
    )


def _m77_resealed_observation(observation: dict, mutate) -> dict:
    tampered = json.loads(canonical_bytes(observation))
    del tampered["receipt_sha256"]
    mutate(tampered)
    resealed = seal_document(tampered)
    validate_self_hash(resealed)
    return resealed


def _compacted_mapper_store(tmp_path: Path) -> tuple[Path, Path, dict]:
    store = _private(tmp_path / "mapper")
    run_id = _run_id(29, "compacted")
    run = _private(_private(store / "runs") / run_id)
    database = run / "facts.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE facts (value TEXT NOT NULL)")
    connection.execute("INSERT INTO facts VALUES ('observed-current-generation')")
    connection.commit()
    connection.close()
    os.chmod(database, 0o600)
    database_raw = database.read_bytes()
    manifest = seal_document(
        {
            "schema": "fixture.mapper.v1",
            "run_id": run_id,
            "scan": {"finished_at": "2026-08-29T18:01:16.000000Z"},
            "database": {
                "path": "facts.sqlite3",
                "sha256": sha256_bytes(database_raw),
                "bytes": len(database_raw),
            },
        }
    )
    manifest_raw = canonical_bytes(manifest)
    _write(run / "manifest.json", manifest_raw)
    _point_current(store, "mapper", manifest)
    archive_raw = gzip.compress(database_raw, compresslevel=9, mtime=0)
    _write(run / "facts.sqlite3.gz", archive_raw)
    compaction = seal_document(
        {
            "schema": "giga.archaeologist.retention-compaction.v1",
            "status": "COMPRESSED",
            "kind": "mapper",
            "run_id": run_id,
            "compacted_at": "2026-08-30T06:49:20.211128Z",
            "source": {
                "path": "facts.sqlite3",
                "sha256": sha256_bytes(database_raw),
                "bytes": len(database_raw),
                "mode": 0o600,
            },
            "compressed": {
                "algorithm": "gzip-9-mtime-zero",
                "path": "facts.sqlite3.gz",
                "sha256": sha256_bytes(archive_raw),
                "bytes": len(archive_raw),
            },
            "manifest": {
                "path": "manifest.json",
                "sha256": sha256_bytes(manifest_raw),
                "bytes": len(manifest_raw),
                "receipt_sha256": manifest["receipt_sha256"],
            },
            "repository_cleanup_authority": False,
        }
    )
    _write(run / "compaction.json", canonical_bytes(compaction))
    database.unlink()
    return store, run, compaction


def _legacy_plan() -> dict:
    return seal_document(
        {
            "schema": "giga.archaeologist.retention-plan.v1",
            "status": "NO_ACTION",
            "authority": "map-generation-storage-lifecycle-only",
            "repository_cleanup_authority": False,
            "generated_at": "2026-08-30T20:31:11.239904Z",
            "policy": {"keep_successes": 3},
            "reference_roots": ["/private/operator-only/reference"],
            "reference_scan_complete": True,
            "reference_failures": [],
            "candidate_generations": 0,
            "candidate_bytes": 0,
            "storage_quota_satisfied_after_plan": True,
            "stores": [{"root": "/private/operator-only/store"}],
        }
    )


def _legacy_run(plan: dict) -> dict:
    return seal_document(
        {
            "schema": "giga.archaeologist.retention-run.v1",
            "status": "PASS",
            "mode": "DRY_RUN",
            "run_id": "20260830T203111.239904Z-fixture",
            "finished_at": "2026-08-30T20:31:11.239904Z",
            "plan_receipt_sha256": plan["receipt_sha256"],
            "plan_status": plan["status"],
            "candidate_generations": 0,
            "candidate_bytes": 0,
            "storage_quota_satisfied_after_plan": True,
            "quarantine": None,
            "purges": [],
            "recovered_quarantines": [],
            "repository_cleanup_authority": False,
        }
    )


def _assert_absent_from_text(text: str, forbidden: tuple[str, ...]) -> None:
    for token in forbidden:
        assert token not in text


def test_historical_retention_inspection_is_authenticated_safe_and_explicit(
    tmp_path: Path,
) -> None:
    plan = _legacy_plan()
    private_root = tmp_path / "PRIVATE-OPERATOR-ROOT-DO-NOT-EMIT"
    path = private_root / "nested" / "SECRET-PLAN-LOCATION.json"
    _write(path, canonical_bytes(plan))

    inspection = inspect_retention_receipt(
        path, expected_raw_sha256=sha256_bytes(path.read_bytes())
    )

    validate_self_hash(inspection)
    assert inspection["receipt"]["schema"].endswith("retention-plan.v1")
    assert inspection["receipt"]["current_writer_version"] == 3
    assert inspection["receipt"]["compatibility"] == (
        "HISTORICAL_AUTHENTICATED_COMPATIBILITY"
    )
    assert inspection["receipt"]["missing_current_generation_fields"] == [
        "compaction_candidate_generations",
        "compaction_candidate_bytes",
    ]
    assert inspection["receipt"]["safe_collection_counts"]["stores"] == {
        "state": "OBSERVED",
        "count": 1,
    }
    rendered = json.dumps(inspection, sort_keys=True)
    _assert_absent_from_text(
        rendered,
        (
            "/private/operator-only",
            str(path),
            str(private_root),
            private_root.name,
            path.name,
        ),
    )
    assert "path" not in inspection["source"]
    assert inspection["source"]["literal_path_disclosed"] is False
    assert inspection["source"]["path_derived_identity_disclosed"] is False
    content_identity = inspection["source"]["identity"]
    assert content_identity == {
        "purpose": "retention-receipt-content",
        "algorithm": "content-addressed-retention-receipt-v1",
        "raw_sha256": inspection["source"]["raw_sha256"],
        "receipt_sha256": inspection["source"]["receipt_sha256"],
        "literal_path_disclosed": False,
        "path_derived_identity_disclosed": False,
    }
    assert inspection["source"]["historical_bytes_rewritten"] is False
    assert inspection["claims"]["cleanup_permitted"] is False
    assert inspection["claims"]["purge_permitted"] is False


def test_identical_receipt_bytes_at_different_private_paths_share_public_identity(
    tmp_path: Path,
) -> None:
    raw = canonical_bytes(_legacy_plan())
    first_root = tmp_path / "PRIVATE-FIRST-ROOT-DO-NOT-EMIT"
    second_root = tmp_path / "PRIVATE-SECOND-ROOT-DO-NOT-EMIT"
    first = first_root / "nested" / "SECRET-FIRST-PLAN.json"
    second = second_root / "other" / "SECRET-SECOND-PLAN.json"
    _write(first, raw)
    _write(second, raw)

    first_inspection = inspect_retention_receipt(first)
    second_inspection = inspect_retention_receipt(second)

    assert first_inspection["source"]["identity"] == second_inspection["source"][
        "identity"
    ]
    assert first_inspection["source"]["identity"]["receipt_sha256"] == _legacy_plan()[
        "receipt_sha256"
    ]
    combined = json.dumps(
        [first_inspection, second_inspection], sort_keys=True
    ) + render_retention_receipt_inspection(first_inspection)
    _assert_absent_from_text(
        combined,
        (
            str(first),
            str(second),
            str(first_root),
            str(second_root),
            first_root.name,
            second_root.name,
            first.name,
            second.name,
        ),
    )


def test_historical_run_inspection_and_cli_machine_human_views(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = _legacy_run(_legacy_plan())
    private_root = tmp_path / "PRIVATE-CLI-ROOT-DO-NOT-EMIT"
    path = private_root / "nested" / "SECRET-RUN-RECEIPT.json"
    _write(path, canonical_bytes(run))
    digest = sha256_bytes(path.read_bytes())

    assert (
        archaeology_main(
            [
                "retention-inspect-receipt",
                "--receipt",
                str(path),
                "--expected-raw-sha256",
                digest,
            ]
        )
        == 0
    )
    machine = json.loads(capsys.readouterr().out)
    validate_self_hash(machine)
    machine_text = json.dumps(machine, sort_keys=True)
    _assert_absent_from_text(
        machine_text,
        (str(path), str(private_root), private_root.name, path.name),
    )
    assert machine["receipt"]["family"] == "run"
    assert machine["receipt"]["current_writer_version"] == 2
    assert machine["receipt"]["safe_collection_counts"]["compactions"] == {
        "state": "UNKNOWN_MISSING_LEGACY_FIELD",
        "count": None,
    }
    assert (
        archaeology_main(
            [
                "retention-inspect-receipt",
                "--receipt",
                str(path),
                "--format",
                "human",
            ]
        )
        == 0
    )
    human = capsys.readouterr().out
    _assert_absent_from_text(
        human,
        (str(path), str(private_root), private_root.name, path.name),
    )
    assert "run v1 (current writer v2)" in human
    assert "Source identity: retention-receipt-content:" in human
    assert "Cleanup/quarantine/purge authority: none" in human


def test_retention_receipt_open_failure_uses_opaque_identity_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    private_root = tmp_path / "PRIVATE-MISSING-ROOT-DO-NOT-EMIT"
    missing = private_root / "nested" / "SECRET-MISSING-RECEIPT.json"
    second_root = tmp_path / "PRIVATE-SECOND-MISSING-ROOT-DO-NOT-EMIT"
    second_missing = second_root / "other" / "SECRET-SECOND-MISSING.json"
    forbidden = (
        str(missing),
        str(second_missing),
        str(private_root),
        str(second_root),
        private_root.name,
        second_root.name,
        missing.name,
        second_missing.name,
    )

    with pytest.raises(RetentionError) as direct:
        inspect_retention_receipt(missing)
    direct_text = str(direct.value)
    _assert_absent_from_text(direct_text, forbidden)
    assert "cannot open retention receipt safely" in direct_text
    assert direct_text.endswith("retention-receipt-location:CONTENT_UNAVAILABLE")

    with pytest.raises(RetentionError) as second_direct:
        inspect_retention_receipt(second_missing)
    second_direct_text = str(second_direct.value)
    _assert_absent_from_text(second_direct_text, forbidden)
    assert second_direct_text == direct_text

    assert (
        archaeology_main(
            [
                "retention-inspect-receipt",
                "--receipt",
                str(missing),
            ]
        )
        == 2
    )
    stderr = capsys.readouterr().err
    _assert_absent_from_text(stderr, forbidden)
    refusal = json.loads(stderr)
    assert refusal["status"] == "REFUSED"
    assert refusal["reason"] == direct_text

    assert (
        archaeology_main(
            [
                "retention-inspect-receipt",
                "--receipt",
                str(second_missing),
            ]
        )
        == 2
    )
    second_stderr = capsys.readouterr().err
    _assert_absent_from_text(second_stderr, forbidden)
    assert json.loads(second_stderr)["reason"] == direct_text


def test_retention_receipt_json_failure_uses_opaque_identity_only(
    tmp_path: Path,
) -> None:
    private_root = tmp_path / "PRIVATE-BAD-JSON-ROOT-DO-NOT-EMIT"
    path = private_root / "nested" / "SECRET-BAD-RECEIPT.json"
    _write(path, b'{"schema":')
    forbidden = (str(path), str(private_root), private_root.name, path.name)

    with pytest.raises(RetentionError) as error:
        inspect_retention_receipt(path)
    error_text = str(error.value)
    _assert_absent_from_text(error_text, forbidden)
    assert "retention receipt is not strict UTF-8 JSON" in error_text


def test_retention_json_failures_use_generic_non_path_identity(
    tmp_path: Path,
) -> None:
    first_root = _private(tmp_path / "PRIVATE-FIRST-BAD-POINTER-DO-NOT-EMIT")
    second_root = _private(tmp_path / "PRIVATE-SECOND-BAD-POINTER-DO-NOT-EMIT")
    for root in (first_root, second_root):
        _private(root / "runs")
        _write(root / "CURRENT.json", b'{"schema":')

    forbidden = (
        str(first_root),
        str(second_root),
        first_root.name,
        second_root.name,
        "CURRENT.json",
    )

    with pytest.raises(RetentionError) as first:
        plan_navigation_retention(
            first_root,
            tmp_path / "missing-mapper",
            tmp_path / "missing-semantic",
        )
    with pytest.raises(RetentionError) as second:
        plan_navigation_retention(
            second_root,
            tmp_path / "missing-mapper",
            tmp_path / "missing-semantic",
        )

    first_text = str(first.value)
    second_text = str(second.value)
    assert first_text == second_text
    _assert_absent_from_text(first_text, forbidden)
    assert first_text == "invalid retention JSON input: retention-json-input:CONTENT_UNAVAILABLE"


def test_retention_inspection_human_renderer_never_emits_source_path(
    tmp_path: Path,
) -> None:
    plan = _legacy_plan()
    private_root = tmp_path / "PRIVATE-HUMAN-ROOT-DO-NOT-EMIT"
    path = private_root / "nested" / "SECRET-HUMAN-PLAN.json"
    _write(path, canonical_bytes(plan))
    inspection = inspect_retention_receipt(path)

    rendered = render_retention_receipt_inspection(inspection)

    _assert_absent_from_text(
        rendered,
        (str(path), str(private_root), private_root.name, path.name),
    )
    assert "Source identity: retention-receipt-content:" in rendered
    assert "Raw identity:" in rendered


def test_retention_inspection_refuses_tamper_wrong_hash_duplicate_and_unknown(
    tmp_path: Path,
) -> None:
    plan = _legacy_plan()
    path = tmp_path / "plan.json"
    _write(path, canonical_bytes(plan))
    with pytest.raises(RetentionError, match="does not match expectation"):
        inspect_retention_receipt(path, expected_raw_sha256="0" * 64)

    tampered = {**plan, "status": "FALSE_SUCCESS"}
    _write(tmp_path / "tampered.json", canonical_bytes(tampered))
    with pytest.raises(RetentionError, match="self-hash mismatch"):
        inspect_retention_receipt(tmp_path / "tampered.json")

    unknown = seal_document({"schema": "fixture.retention.v99", "status": "PASS"})
    _write(tmp_path / "unknown.json", canonical_bytes(unknown))
    with pytest.raises(RetentionError, match="unsupported retention receipt schema"):
        inspect_retention_receipt(tmp_path / "unknown.json")

    _write(
        tmp_path / "duplicate.json",
        b'{"schema":"a","schema":"b","receipt_sha256":"' + b"0" * 64 + b'"}',
    )
    with pytest.raises(RetentionError, match="duplicate JSON field"):
        inspect_retention_receipt(tmp_path / "duplicate.json")


def test_current_retention_writer_versions_remain_v3_plan_and_v2_run(
    tmp_path: Path,
) -> None:
    inventory, mapper, semantic, _ids = _fixture_stores(tmp_path)
    plan = plan_navigation_retention(
        inventory,
        mapper,
        semantic,
        policy=_policy(),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )
    run = run_navigation_retention(
        inventory,
        mapper,
        semantic,
        policy=_policy(),
        apply=False,
        now=datetime(2026, 8, 30, 0, 1, tzinfo=UTC),
    )

    assert plan["schema"] == RETENTION_PLAN_SCHEMA
    assert plan["schema"].endswith("retention-plan.v3")
    assert run["schema"] == RETENTION_RUN_SCHEMA
    assert run["schema"].endswith("retention-run.v2")
    assert "compaction_candidate_generations" in plan
    assert "compaction_candidate_bytes" in plan
    assert "compactions" in run


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
        "age-window-expired",
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


def test_four_recent_successes_make_only_oldest_a_candidate(tmp_path: Path) -> None:
    ids = [_run_id(30, f"recent{index}") for index in range(1, 5)]
    inventory, mapper, semantic, _ = _fixture_stores(tmp_path, inventory_ids=ids)

    plan = plan_navigation_retention(
        inventory,
        mapper,
        semantic,
        now=datetime(2026, 8, 30, 12, tzinfo=UTC),
    )

    by_id = {item["run_id"]: item for item in _inventory_plan(plan)["generations"]}
    assert by_id[ids[0]]["age_seconds"] == 12 * 60 * 60
    assert by_id[ids[0]]["disposition"] == "QUARANTINE_CANDIDATE"
    assert "minimum-age-window" in by_id[ids[0]]["reasons"]
    assert "outside-success-generation-window" in by_id[ids[0]]["reasons"]
    assert all(by_id[run_id]["disposition"] == "RETAIN" for run_id in ids[1:])


@pytest.mark.parametrize("generation_count", (1, 2, 3))
def test_up_to_three_recent_successes_are_retained(
    tmp_path: Path, generation_count: int
) -> None:
    ids = [_run_id(30, f"recent{index}") for index in range(1, generation_count + 1)]
    inventory, mapper, semantic, _ = _fixture_stores(tmp_path, inventory_ids=ids)

    plan = plan_navigation_retention(
        inventory,
        mapper,
        semantic,
        now=datetime(2026, 8, 30, 12, tzinfo=UTC),
    )

    inventory_generations = _inventory_plan(plan)["generations"]
    assert len(inventory_generations) == generation_count
    assert all(item["disposition"] == "RETAIN" for item in inventory_generations)


def test_old_success_is_candidate_inside_newest_three_unless_referenced(
    tmp_path: Path,
) -> None:
    ids = [_run_id(day, f"old{day}") for day in range(1, 4)]
    inventory, mapper, semantic, _ = _fixture_stores(tmp_path, inventory_ids=ids)

    plan = plan_navigation_retention(
        inventory,
        mapper,
        semantic,
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    by_id = {item["run_id"]: item for item in _inventory_plan(plan)["generations"]}
    assert "recent-recovery-window" in by_id[ids[0]]["reasons"]
    assert "age-window-expired" in by_id[ids[0]]["reasons"]
    assert by_id[ids[0]]["disposition"] == "QUARANTINE_CANDIDATE"
    assert by_id[ids[1]]["disposition"] == "RETAIN"
    assert "inventory:current.incremental_from" in by_id[ids[1]]["reasons"]
    assert by_id[ids[2]]["disposition"] == "RETAIN"
    assert "inventory:CURRENT" in by_id[ids[2]]["reasons"]


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
        "modules.operations.archaeology.retention.os.rename", fail_second
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
        "modules.operations.archaeology.retention", fromlist=["_external_references"]
    )._external_references
    calls = 0

    def reference_race(run_ids, roots):
        nonlocal calls
        calls += 1
        if calls == 2:
            return ({next(iter(run_ids)): ["/new/reference.json"]}, [])
        return real_scan(run_ids, roots)

    monkeypatch.setattr(
        "modules.operations.archaeology.retention._external_references",
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
        "modules.operations.archaeology.retention", fromlist=["_write_create_once"]
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
        "modules.operations.archaeology.retention._write_create_once",
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


def test_running_retention_lock_fails_closed_without_mutation(tmp_path: Path) -> None:
    inventory, mapper, semantic, ids = _fixture_stores(tmp_path)
    retention = _private(semantic / "retention")
    lock_path = retention / "retention.lock"
    with lock_path.open("a+b") as lock:
        os.chmod(lock_path, 0o600)
        lock_file(lock, blocking=False)
        with pytest.raises(RetentionError, match="already running"):
            run_navigation_retention(
                inventory,
                mapper,
                semantic,
                policy=_policy(),
                apply=True,
                now=datetime(2026, 8, 30, tzinfo=UTC),
            )

    assert all((inventory / "runs" / run_id).is_dir() for run_id in ids)
    assert not (retention / "CURRENT.json").exists()
    assert not (retention / "quarantine").exists()


def test_scip_retention_never_selects_current_generation(tmp_path: Path) -> None:
    inventory, mapper, semantic, _ids = _fixture_stores(tmp_path)
    scip = _private(tmp_path / "scip")
    catalogs = [_scip_run(scip, _run_id(day, f"scip{day}")) for day in range(1, 5)]
    _point_scip_current(scip, catalogs[-1])
    policy = RetentionPolicy(
        keep_successes=2,
        keep_failures=1,
        min_age_seconds=0,
        quarantine_grace_seconds=1000,
        inventory_max_bytes=1024 * 1024,
        mapper_max_bytes=1024 * 1024,
        semantic_max_bytes=1024 * 1024,
        scip_max_bytes=1,
        failure_max_bytes=1024 * 1024,
    )

    plan = plan_navigation_retention(
        inventory,
        mapper,
        semantic,
        scip_store=scip,
        policy=policy,
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    scip_plan = next(item for item in plan["stores"] if item["kind"] == "scip")
    generations = {item["run_id"]: item for item in scip_plan["generations"]}
    assert generations[catalogs[-1]["run_id"]]["disposition"] == "RETAIN"
    assert "scip:CURRENT" in generations[catalogs[-1]["run_id"]]["reasons"]
    assert any(
        item["disposition"] == "QUARANTINE_CANDIDATE"
        for item in scip_plan["generations"]
    )


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
        "modules.operations.archaeology.retention", fromlist=["_write_create_once"]
    )
    real_write = module._write_create_once

    def fail_receipt(path: Path, payload) -> None:
        if path.name == "compaction.json":
            raise OSError("injected compaction receipt failure")
        real_write(path, payload)

    monkeypatch.setattr(
        "modules.operations.archaeology.retention._write_create_once", fail_receipt
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
        "modules.operations.archaeology.retention._write_create_once", real_write
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


def test_compacted_generation_restore_stream_verification_is_read_only(
    tmp_path: Path,
) -> None:
    store, run, compaction = _compacted_mapper_store(tmp_path)
    before = _file_snapshot(store)

    verification = verify_compacted_generation_restore_stream(
        "mapper", run, now=datetime(2026, 8, 30, 9, tzinfo=UTC)
    )

    validate_self_hash(verification)
    assert verification["status"] == "PASS"
    assert verification["mutation_authority"] is False
    assert verification["exact_restore_stream_verified"] is True
    assert verification["raw_database_installed"] is False
    assert verification["compaction_receipt_sha256"] == compaction["receipt_sha256"]
    assert _file_snapshot(store) == before


def test_restore_stream_cli_writes_an_immutable_verification_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _store, run, _compaction = _compacted_mapper_store(tmp_path)
    output = tmp_path / "restore-verification.json"

    result = archaeology_main(
        [
            "retention-verify-restore-stream",
            "--kind",
            "mapper",
            "--generation",
            str(run),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    observed = json.loads(capsys.readouterr().out)
    assert json.loads(output.read_text()) == observed
    validate_self_hash(observed)
    assert observed["exact_restore_stream_verified"] is True


def test_exact_current_mapper_compaction_recovers_once_and_preserves_evidence(
    tmp_path: Path,
) -> None:
    store, run, compaction = _compacted_mapper_store(tmp_path)
    archive_before = (run / "facts.sqlite3.gz").read_bytes()
    receipt_before = (run / "compaction.json").read_bytes()

    recovered = recover_current_compacted_mapper(
        store, now=datetime(2026, 8, 30, 7, tzinfo=UTC)
    )
    repeated = recover_current_compacted_mapper(
        store, now=datetime(2026, 8, 30, 8, tzinfo=UTC)
    )

    validate_self_hash(recovered)
    assert recovered["status"] == "RECOVERED"
    assert recovered["compaction_receipt_sha256"] == compaction["receipt_sha256"]
    assert recovered["archive_preserved"] is True
    assert repeated == recovered
    assert (run / "facts.sqlite3.gz").read_bytes() == archive_before
    assert (run / "compaction.json").read_bytes() == receipt_before
    database = run / "facts.sqlite3"
    assert database.stat().st_nlink == 1
    assert database.stat().st_mode & 0o777 == 0o600
    assert sha256_bytes(database.read_bytes()) == compaction["source"]["sha256"]
    connection = sqlite3.connect(f"file:{database}?mode=ro&immutable=1", uri=True)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT value FROM facts").fetchone() == (
            "observed-current-generation",
        )
    finally:
        connection.close()


def test_current_mapper_recovery_refuses_tampered_compaction_before_publication(
    tmp_path: Path,
) -> None:
    store, run, _compaction = _compacted_mapper_store(tmp_path)
    tampered = json.loads((run / "compaction.json").read_text())
    tampered["source"]["bytes"] += 1
    _write(run / "compaction.json", canonical_bytes(tampered))

    with pytest.raises(RetentionError, match="compaction receipt self-hash mismatch"):
        recover_current_compacted_mapper(store)

    assert not (run / "facts.sqlite3").exists()
    assert not (run / "recovery.json").exists()


def test_current_mapper_recovery_refuses_archive_drift_before_publication(
    tmp_path: Path,
) -> None:
    store, run, _compaction = _compacted_mapper_store(tmp_path)
    _write(run / "facts.sqlite3.gz", b"not-the-bound-archive")

    with pytest.raises(
        RetentionError, match="compressed mapper database binding mismatch"
    ):
        recover_current_compacted_mapper(store)

    assert not (run / "facts.sqlite3").exists()
    assert not (run / "recovery.json").exists()


def test_current_mapper_recovery_refuses_missing_archive_as_closed_failure(
    tmp_path: Path,
) -> None:
    store, run, _compaction = _compacted_mapper_store(tmp_path)
    (run / "facts.sqlite3.gz").unlink()

    with pytest.raises(RetentionError, match="compressed mapper database is missing"):
        recover_current_compacted_mapper(store)

    assert not (run / "facts.sqlite3").exists()
    assert not (run / "recovery.json").exists()


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


def _derived_assessment_stores(
    tmp_path: Path,
) -> tuple[Path, Path, Path, list[str], list[str], list[str]]:
    inventory, _mapper, semantic, inventory_ids = _fixture_stores(tmp_path)
    semantic_ids = [
        *[_run_id(day, f"semantic{day}") for day in range(1, 5)],
        _run_id(5, "semantic"),
    ]
    for run_id in semantic_ids[:-1]:
        _success_run(semantic, "semantic", run_id)
    scip = _private(tmp_path / "scip")
    scip_ids = [_run_id(day, f"scipindex{day}") for day in range(1, 6)]
    catalogs = [_scip_run_with_index(scip, run_id) for run_id in scip_ids]
    _point_scip_current(scip, catalogs[-1])
    return inventory, semantic, scip, inventory_ids, semantic_ids, scip_ids


def _file_snapshot(root: Path) -> list[tuple[str, int, str]]:
    return [
        (
            path.relative_to(root).as_posix(),
            path.stat().st_size,
            sha256_bytes(path.read_bytes()),
        )
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]


def _semantic_payload_paths(semantic: Path, run_id: str) -> tuple[Path, Path]:
    run = semantic / "runs" / run_id
    return run / "graphify-out/graph.json", run / "graphify-out/graph.raw.json"


def test_semantic_compaction_refuses_current_and_newest_three_raw_generations(
    tmp_path: Path,
) -> None:
    _inventory, semantic, _scip, _inventory_ids, semantic_ids, _scip_ids = (
        _derived_assessment_stores(tmp_path)
    )

    for run_id in semantic_ids[-3:]:
        with pytest.raises(
            RetentionError, match="newest three semantic generations must remain raw"
        ):
            compact_inactive_semantic_generation(
                semantic,
                run_id,
                inactive_reason="fixture generation remains in recovery window",
            )
        assert all(path.is_file() for path in _semantic_payload_paths(semantic, run_id))
        assert not (semantic / "runs" / run_id / "semantic-compaction.json").exists()


def test_semantic_compaction_preserves_evidence_verifies_and_restores_exactly(
    tmp_path: Path,
) -> None:
    _inventory, semantic, _scip, _inventory_ids, semantic_ids, _scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    run_id = semantic_ids[0]
    run = semantic / "runs" / run_id
    graph, raw_graph = _semantic_payload_paths(semantic, run_id)
    expected = {path: path.read_bytes() for path in (graph, raw_graph)}
    _write(run / "REPORT.md", b"preserved report\n")
    _write(run / "graphify-out/graph.delta.raw.json", b'{"delta":true}\n')
    preserved = {
        path: path.read_bytes()
        for path in (
            run / "manifest.json",
            run / "REPORT.md",
            run / "graphify-out/graph.delta.raw.json",
        )
    }

    compacted = compact_inactive_semantic_generation(
        semantic,
        run_id,
        inactive_reason="outside newest-three fixture recovery window",
        now=datetime(2026, 8, 30, 10, tzinfo=UTC),
    )

    validate_self_hash(compacted)
    assert compacted["status"] == "PASS"
    assert compacted["generation_rank"] == 5
    assert compacted["newest_three_raw_protected"] is True
    assert all(not path.exists() for path in (graph, raw_graph))
    assert all(Path(f"{path}.gz").is_file() for path in (graph, raw_graph))
    assert all(path.read_bytes() == payload for path, payload in preserved.items())
    receipt = json.loads((run / "semantic-compaction.json").read_text())
    validate_self_hash(receipt)
    assert receipt["receipt_sha256"] == compacted["compaction_receipt_sha256"]

    before_verification = _file_snapshot(run)
    verification = verify_semantic_compacted_generation_restore_stream(
        run, now=datetime(2026, 8, 30, 11, tzinfo=UTC)
    )
    validate_self_hash(verification)
    assert verification["status"] == "PASS"
    assert verification["exact_restore_stream_verified"] is True
    assert verification["raw_artifacts_installed"] == 0
    assert _file_snapshot(run) == before_verification

    assessment = assess_derived_family_retention(
        _inventory,
        semantic,
        scip_store=_scip,
        policy=_policy(),
        now=datetime(2026, 8, 30, 12, tzinfo=UTC),
    )
    semantic_store = next(
        store for store in assessment["stores"] if store["kind"] == "semantic"
    )
    assessed = next(
        row for row in semantic_store["generations"] if row["run_id"] == run_id
    )
    assert assessed["disposition"] == "ALREADY_COMPACTED_AUTHENTICATED"
    assert assessed["artifact_bytes"] == 0

    restored = restore_compacted_semantic_generation(
        run, now=datetime(2026, 8, 30, 13, tzinfo=UTC)
    )
    repeated = restore_compacted_semantic_generation(
        run, now=datetime(2026, 8, 30, 14, tzinfo=UTC)
    )
    validate_self_hash(restored)
    assert restored["status"] == "RESTORED"
    assert repeated["status"] == "ALREADY_RESTORED"
    assert {path: path.read_bytes() for path in (graph, raw_graph)} == expected
    assert all(Path(f"{path}.gz").is_file() for path in (graph, raw_graph))
    assert (run / "semantic-compaction.json").is_file()
    assert all(path.read_bytes() == payload for path, payload in preserved.items())


def test_semantic_compaction_receipt_failure_preserves_raw_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inventory, semantic, _scip, _inventory_ids, semantic_ids, _scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    run_id = semantic_ids[0]
    run = semantic / "runs" / run_id
    payloads = _semantic_payload_paths(semantic, run_id)
    expected = {path: path.read_bytes() for path in payloads}
    module = __import__(
        "modules.operations.archaeology.retention", fromlist=["_write_create_once"]
    )
    real_write = module._write_create_once

    def fail_receipt(path: Path, payload) -> None:
        if path.name == "semantic-compaction.json":
            raise OSError("injected semantic receipt failure")
        real_write(path, payload)

    monkeypatch.setattr(
        "modules.operations.archaeology.retention._write_create_once", fail_receipt
    )
    with pytest.raises(OSError, match="injected semantic receipt failure"):
        compact_inactive_semantic_generation(
            semantic,
            run_id,
            inactive_reason="outside newest-three fixture recovery window",
        )
    assert {path: path.read_bytes() for path in payloads} == expected
    assert not (run / "semantic-compaction.json").exists()
    assert all(Path(f"{path}.gz").is_file() for path in payloads)

    monkeypatch.setattr(
        "modules.operations.archaeology.retention._write_create_once", real_write
    )
    resumed = compact_inactive_semantic_generation(
        semantic,
        run_id,
        inactive_reason="outside newest-three fixture recovery window",
    )
    assert resumed["status"] == "PASS"
    assert all(not path.exists() for path in payloads)


def test_semantic_archive_tamper_refuses_verification_and_restore(
    tmp_path: Path,
) -> None:
    _inventory, semantic, _scip, _inventory_ids, semantic_ids, _scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    run_id = semantic_ids[0]
    run = semantic / "runs" / run_id
    compact_inactive_semantic_generation(
        semantic,
        run_id,
        inactive_reason="outside newest-three fixture recovery window",
    )
    graph, _raw_graph = _semantic_payload_paths(semantic, run_id)
    _write(Path(f"{graph}.gz"), b"tampered")

    with pytest.raises(RetentionError, match="compressed artifact binding mismatch"):
        verify_semantic_compacted_generation_restore_stream(run)
    with pytest.raises(RetentionError, match="compressed artifact binding mismatch"):
        restore_compacted_semantic_generation(run)
    assert not graph.exists()


def test_semantic_round_trip_canary_is_deterministic_and_non_installing(
    tmp_path: Path,
) -> None:
    _inventory, semantic, _scip, _inventory_ids, semantic_ids, _scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    run = semantic / "runs" / semantic_ids[0]
    before = _file_snapshot(run)
    timestamp = datetime(2026, 8, 30, 15, tzinfo=UTC)

    first = run_semantic_round_trip_canary(run, now=timestamp)
    repeated = run_semantic_round_trip_canary(run, now=timestamp)

    validate_self_hash(first)
    assert repeated == first
    assert first["status"] == "PASS"
    assert first["mutation_authority"] is False
    assert first["exact_restore_stream_verified"] is True
    assert first["temporary_archives_removed"] is True
    assert first["source_generation_unchanged"] is True
    assert len(first["sources"]) == len(first["compressed"]) == 2
    assert _file_snapshot(run) == before


def test_semantic_round_trip_cli_writes_immutable_canary_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _inventory, semantic, _scip, _inventory_ids, semantic_ids, _scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    output = tmp_path / "semantic-round-trip.json"

    result = archaeology_main(
        [
            "retention-canary-semantic-round-trip",
            "--generation",
            str(semantic / "runs" / semantic_ids[0]),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    observed = json.loads(capsys.readouterr().out)
    assert json.loads(output.read_text()) == observed
    validate_self_hash(observed)
    assert observed["schema"] == "giga.archaeology.semantic-round-trip-canary.v1"


def _scip_payload_paths(scip: Path, run_id: str) -> tuple[Path, ...]:
    return tuple(sorted((scip / "runs" / run_id / "projects").glob("*/index.scip")))


def test_scip_compaction_refuses_current_and_newest_three_raw_generations(
    tmp_path: Path,
) -> None:
    _inventory, _semantic, scip, _inventory_ids, _semantic_ids, scip_ids = (
        _derived_assessment_stores(tmp_path)
    )

    for run_id in scip_ids[-3:]:
        with pytest.raises(
            RetentionError, match="newest three SCIP generations must remain raw"
        ):
            compact_inactive_scip_generation(
                scip,
                run_id,
                inactive_reason="fixture generation remains in recovery window",
            )
        assert all(path.is_file() for path in _scip_payload_paths(scip, run_id))
        assert not (scip / "runs" / run_id / "scip-compaction.json").exists()


def test_scip_compaction_preserves_evidence_verifies_and_restores_exactly(
    tmp_path: Path,
) -> None:
    inventory, semantic, scip, _inventory_ids, _semantic_ids, scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    run_id = scip_ids[0]
    run = scip / "runs" / run_id
    indexes = _scip_payload_paths(scip, run_id)
    expected = {path: path.read_bytes() for path in indexes}
    _write(run / "REPORT.md", b"preserved SCIP report\n")
    _write(run / "history/source-closure.json", b'{"preserved":true}\n')
    preserved = {
        path: path.read_bytes()
        for path in (
            run / "catalog.json",
            run / "projects/fixture-project/manifest.json",
            run / "REPORT.md",
            run / "history/source-closure.json",
        )
    }

    compacted = compact_inactive_scip_generation(
        scip,
        run_id,
        inactive_reason="outside newest-three fixture recovery window",
        now=datetime(2026, 8, 30, 10, tzinfo=UTC),
    )

    validate_self_hash(compacted)
    assert compacted["status"] == "PASS"
    assert compacted["generation_rank"] == 5
    assert compacted["newest_three_raw_protected"] is True
    assert all(not path.exists() for path in indexes)
    assert all(Path(f"{path}.gz").is_file() for path in indexes)
    assert all(path.read_bytes() == payload for path, payload in preserved.items())
    receipt = json.loads((run / "scip-compaction.json").read_text())
    validate_self_hash(receipt)
    assert receipt["receipt_sha256"] == compacted["compaction_receipt_sha256"]

    before_verification = _file_snapshot(run)
    verification = verify_scip_compacted_generation_restore_stream(
        run, now=datetime(2026, 8, 30, 11, tzinfo=UTC)
    )
    validate_self_hash(verification)
    assert verification["status"] == "PASS"
    assert verification["exact_restore_stream_verified"] is True
    assert verification["raw_artifacts_installed"] == 0
    assert _file_snapshot(run) == before_verification

    assessment = assess_derived_family_retention(
        inventory,
        semantic,
        scip_store=scip,
        policy=_policy(),
        now=datetime(2026, 8, 30, 12, tzinfo=UTC),
    )
    scip_store = next(store for store in assessment["stores"] if store["kind"] == "scip")
    assessed = next(row for row in scip_store["generations"] if row["run_id"] == run_id)
    assert assessed["disposition"] == "ALREADY_COMPACTED_AUTHENTICATED"
    assert assessed["artifact_bytes"] == 0

    restored = restore_compacted_scip_generation(
        run, now=datetime(2026, 8, 30, 13, tzinfo=UTC)
    )
    repeated = restore_compacted_scip_generation(
        run, now=datetime(2026, 8, 30, 14, tzinfo=UTC)
    )
    validate_self_hash(restored)
    assert restored["status"] == "RESTORED"
    assert repeated["status"] == "ALREADY_RESTORED"
    assert {path: path.read_bytes() for path in indexes} == expected
    assert all(Path(f"{path}.gz").is_file() for path in indexes)
    assert all(path.read_bytes() == payload for path, payload in preserved.items())


def test_scip_compaction_receipt_failure_preserves_raw_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inventory, _semantic, scip, _inventory_ids, _semantic_ids, scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    run_id = scip_ids[0]
    run = scip / "runs" / run_id
    indexes = _scip_payload_paths(scip, run_id)
    expected = {path: path.read_bytes() for path in indexes}
    module = __import__(
        "modules.operations.archaeology.retention", fromlist=["_write_create_once"]
    )
    real_write = module._write_create_once

    def fail_receipt(path: Path, payload) -> None:
        if path.name == "scip-compaction.json":
            raise OSError("injected SCIP receipt failure")
        real_write(path, payload)

    monkeypatch.setattr(
        "modules.operations.archaeology.retention._write_create_once", fail_receipt
    )
    with pytest.raises(OSError, match="injected SCIP receipt failure"):
        compact_inactive_scip_generation(
            scip,
            run_id,
            inactive_reason="outside newest-three fixture recovery window",
        )
    assert {path: path.read_bytes() for path in indexes} == expected
    assert not (run / "scip-compaction.json").exists()
    assert all(Path(f"{path}.gz").is_file() for path in indexes)

    monkeypatch.setattr(
        "modules.operations.archaeology.retention._write_create_once", real_write
    )
    resumed = compact_inactive_scip_generation(
        scip,
        run_id,
        inactive_reason="outside newest-three fixture recovery window",
    )
    assert resumed["status"] == "PASS"
    assert all(not path.exists() for path in indexes)


def test_scip_unbound_or_tampered_payload_refuses_compaction_and_restore(
    tmp_path: Path,
) -> None:
    _inventory, _semantic, scip, _inventory_ids, _semantic_ids, scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    run_id = scip_ids[0]
    run = scip / "runs" / run_id
    index = _scip_payload_paths(scip, run_id)[0]
    original = index.read_bytes()
    _write(index, b"unbound SCIP bytes")
    with pytest.raises(RetentionError, match="artifact binding mismatch"):
        compact_inactive_scip_generation(
            scip,
            run_id,
            inactive_reason="outside newest-three fixture recovery window",
        )
    _write(index, original)

    compact_inactive_scip_generation(
        scip,
        run_id,
        inactive_reason="outside newest-three fixture recovery window",
    )
    _write(Path(f"{index}.gz"), b"tampered")
    with pytest.raises(RetentionError, match="compressed artifact binding mismatch"):
        verify_scip_compacted_generation_restore_stream(run)
    with pytest.raises(RetentionError, match="compressed artifact binding mismatch"):
        restore_compacted_scip_generation(run)
    assert not index.exists()


def test_scip_round_trip_canary_is_deterministic_non_installing_and_cli_bound(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _inventory, _semantic, scip, _inventory_ids, _semantic_ids, scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    run = scip / "runs" / scip_ids[0]
    before = _file_snapshot(run)
    timestamp = datetime(2026, 8, 30, 15, tzinfo=UTC)
    first = run_scip_round_trip_canary(run, now=timestamp)
    repeated = run_scip_round_trip_canary(run, now=timestamp)

    validate_self_hash(first)
    assert repeated == first
    assert first["status"] == "PASS"
    assert first["mutation_authority"] is False
    assert first["exact_restore_stream_verified"] is True
    assert first["temporary_archives_removed"] is True
    assert first["source_generation_unchanged"] is True
    assert _file_snapshot(run) == before

    output = tmp_path / "scip-round-trip.json"
    result = archaeology_main(
        [
            "retention-canary-scip-round-trip",
            "--generation",
            str(run),
            "--output",
            str(output),
        ]
    )
    assert result == 0
    observed = json.loads(capsys.readouterr().out)
    assert json.loads(output.read_text()) == observed
    validate_self_hash(observed)
    assert observed["schema"] == "giga.archaeology.scip-round-trip-canary.v1"


def test_derived_family_assessment_classifies_artifacts_and_protects_newest_three(
    tmp_path: Path,
) -> None:
    inventory, semantic, scip, inventory_ids, semantic_ids, scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    before = _file_snapshot(tmp_path)

    assessment = assess_derived_family_retention(
        inventory,
        semantic,
        scip_store=scip,
        policy=_policy(),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    validate_self_hash(assessment)
    assert assessment["status"] == "DRY_RUN_CANDIDATES"
    assert assessment["mutation_authority"] is False
    assert assessment["repository_cleanup_authority"] is False
    assert assessment["source_history_retirement_authority"] is False
    assert assessment["candidate_generations"] == 6
    assert assessment["restore_ready_generations"] == 6
    assert assessment["blocked_restore_adapter_generations"] == 0
    stores = {store["kind"]: store for store in assessment["stores"]}
    inventory_rows = {row["run_id"]: row for row in stores["inventory"]["generations"]}
    semantic_rows = {row["run_id"]: row for row in stores["semantic"]["generations"]}
    scip_rows = {row["run_id"]: row for row in stores["scip"]["generations"]}
    assert all(
        inventory_rows[run_id]["newest_three_raw_protected"]
        for run_id in inventory_ids[-3:]
    )
    assert all(
        inventory_rows[run_id]["disposition"]
        == "DRY_RUN_COMPRESSION_CANDIDATE"
        for run_id in inventory_ids[:2]
    )
    assert inventory_rows[inventory_ids[0]]["artifacts"][0][
        "artifact_class"
    ] == "SQLITE_DATABASE"
    assert all(
        semantic_rows[run_id]["disposition"]
        == "DRY_RUN_COMPRESSION_CANDIDATE"
        for run_id in semantic_ids[:2]
    )
    assert all(
        semantic_rows[run_id]["restore_capability"]
        == "AUTHENTICATED_SEMANTIC_GZIP_V1"
        for run_id in semantic_ids[:2]
    )
    assert {
        item["artifact_class"]
        for item in semantic_rows[semantic_ids[0]]["artifacts"]
    } == {"CONTENT_ADDRESSED_JSON_OUTPUT"}
    assert all(
        scip_rows[run_id]["disposition"]
        == "DRY_RUN_COMPRESSION_CANDIDATE"
        for run_id in scip_ids[:2]
    )
    assert all(
        scip_rows[run_id]["restore_capability"] == "AUTHENTICATED_SCIP_GZIP_V1"
        for run_id in scip_ids[:2]
    )
    assert scip_rows[scip_ids[0]]["artifacts"][0][
        "artifact_class"
    ] == "CONTENT_ADDRESSED_SCIP_INDEX"
    assert "catalog.json" in scip_rows[scip_ids[0]]["preserved_paths"]
    assert "projects/fixture-project/manifest.json" in scip_rows[scip_ids[0]][
        "preserved_paths"
    ]
    assert _file_snapshot(tmp_path) == before


def test_derived_family_assessment_is_deterministic_and_reference_failures_block(
    tmp_path: Path,
) -> None:
    inventory, semantic, scip, inventory_ids, _semantic_ids, _scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    timestamp = datetime(2026, 8, 30, tzinfo=UTC)
    first = assess_derived_family_retention(
        inventory, semantic, scip_store=scip, policy=_policy(), now=timestamp
    )
    repeated = assess_derived_family_retention(
        inventory, semantic, scip_store=scip, policy=_policy(), now=timestamp
    )
    assert repeated == first

    target = tmp_path / "reference-target"
    _write(target, inventory_ids[0].encode())
    unsafe_root = tmp_path / "unsafe-reference-root"
    unsafe_root.symlink_to(target)
    blocked = assess_derived_family_retention(
        inventory,
        semantic,
        scip_store=scip,
        reference_roots=(unsafe_root,),
        policy=_policy(),
        now=timestamp,
    )
    assert blocked["status"] == "PARTIAL_NO_ACTION"
    assert blocked["reference_scan_complete"] is False
    inventory_rows = next(
        store for store in blocked["stores"] if store["kind"] == "inventory"
    )["generations"]
    assert any(
        row["disposition"] == "BLOCKED_REFERENCE_SCAN_INCOMPLETE"
        for row in inventory_rows
    )


def test_derived_family_assessment_refuses_content_addressed_artifact_drift(
    tmp_path: Path,
) -> None:
    inventory, semantic, scip, _inventory_ids, semantic_ids, _scip_ids = (
        _derived_assessment_stores(tmp_path)
    )
    drifted = semantic / "runs" / semantic_ids[0] / "graphify-out/graph.json"
    _write(drifted, b"changed")

    with pytest.raises(RetentionError, match="artifact binding mismatch"):
        assess_derived_family_retention(
            inventory,
            semantic,
            scip_store=scip,
            policy=_policy(),
            now=datetime(2026, 8, 30, tzinfo=UTC),
        )


def test_derived_family_assessment_cli_emits_the_closed_dry_run_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inventory, semantic, scip, _inventory_ids, _semantic_ids, _scip_ids = (
        _derived_assessment_stores(tmp_path)
    )

    result = archaeology_main(
        [
            "retention-assess-derived",
            "--inventory-store",
            str(inventory),
            "--semantic-store",
            str(semantic),
            "--scip-store",
            str(scip),
            "--output",
            str(tmp_path / "assessment.json"),
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    validate_self_hash(payload)
    assert payload["schema"] == (
        "giga.archaeology.derived-family-retention-assessment.v1"
    )
    assert payload["mutation_authority"] is False
    written = json.loads((tmp_path / "assessment.json").read_text())
    assert written == payload
    assert (tmp_path / "assessment.json").stat().st_mode & 0o777 == 0o600


def test_navigation_retention_cli_defaults_to_a_sealed_dry_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inventory, mapper, semantic, _ids = _fixture_stores(tmp_path)
    references = _private(tmp_path / "references")

    result = archaeology_main(
        [
            "navigation-retention",
            "--inventory-store",
            str(inventory),
            "--semantic-store",
            str(semantic),
            "--mapper-store",
            str(mapper),
            "--reference-root",
            str(references),
            "--keep-successes",
            "5",
            "--keep-failures",
            "2",
            "--min-age-seconds",
            "0",
            "--quarantine-grace-seconds",
            "0",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    validate_self_hash(payload)
    assert payload["mode"] == "DRY_RUN"
    plan = json.loads(
        (
            semantic
            / "retention"
            / "runs"
            / payload["run_id"]
            / "plan.json"
        ).read_text()
    )
    assert plan["policy"]["keep_successes"] == 5
    assert plan["policy"]["keep_failures"] == 2
    assert plan["policy"]["min_age_seconds"] == 0
    assert plan["policy"]["quarantine_grace_seconds"] == 0
    assert payload["quarantine"] is None
    assert payload["purges"] == []


def test_cross_store_lineage_closes_per_store_newest_three_loophole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._payload_open_consumer_status",
        lambda _path: {"status": "NONE"},
    )
    repository = _source_repository(tmp_path / "source")
    runtime_a = _private(tmp_path / "runtime-a")
    runtime_b = _private(tmp_path / "runtime-b")
    run_ids = [_run_id(day, f"lineage{day}") for day in range(1, 5)]
    for index, run_id in enumerate(run_ids):
        root = runtime_a if index % 2 == 0 else runtime_b
        _single_inventory_store(root, f"store-{index}", run_id, repository)

    assessment = assess_cross_store_derived_map_lineage(
        (runtime_a, runtime_b),
        active_consumer_registry=_active_consumer_registry(
            active_run_ids=[run_ids[-1]], negative_run_ids=run_ids[:-1]
        ),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    validate_self_hash(assessment)
    assert assessment["schema"] == (
        "giga.archaeology.cross-store-derived-map-lineage-assessment.v1"
    )
    assert assessment["scope"]["derived_store_family_count"] == 4
    assert assessment["classification_counts"] == {
        "PAYLOAD_RETIRE_CANDIDATE": 1,
        "RETAIN_CURRENT": 1,
        "RETAIN_GLOBAL_RECENT": 2,
    }
    assert assessment["byte_accounting"]["sum_invariant"]["status"] == "PASS"
    assert assessment["byte_accounting"]["regular_file_bytes"] == _regular_file_bytes(
        runtime_a, runtime_b
    )
    assert (
        assessment["counts"]["total_regular_file_bytes"]
        == assessment["byte_accounting"]["regular_file_bytes"]
    )
    assert (
        assessment["counts"]["protected_regular_file_bytes"]
        + assessment["counts"]["candidate_payload_bytes"]
        == assessment["counts"]["total_regular_file_bytes"]
    )
    generations = {item["generation_alias"]: item for item in assessment["generations"]}
    by_run = {
        generations[payload["generation_alias"]]["run_id"]: payload["classification"]
        for payload in assessment["payloads"]
    }
    assert by_run[run_ids[0]] == "PAYLOAD_RETIRE_CANDIDATE"
    assert by_run[run_ids[-1]] == "RETAIN_CURRENT"
    assert generations[
        next(
            payload["generation_alias"]
            for payload in assessment["payloads"]
            if generations[payload["generation_alias"]]["run_id"] == run_ids[0]
        )
    ]["local_current_pointer"] is True


def test_cross_store_lineage_dirty_source_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._payload_open_consumer_status",
        lambda _path: {"status": "NONE"},
    )
    repository = _source_repository(tmp_path / "source")
    runtime_a = _private(tmp_path / "runtime-a")
    runtime_b = _private(tmp_path / "runtime-b")
    run_ids = [_run_id(day, f"dirty{day}") for day in range(1, 5)]
    for index, run_id in enumerate(run_ids):
        root = runtime_a if index % 2 == 0 else runtime_b
        _single_inventory_store(
            root, f"dirty-store-{index}", run_id, repository, clean=False
        )

    assessment = assess_cross_store_derived_map_lineage(
        (runtime_a, runtime_b),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    generations = {item["generation_alias"]: item for item in assessment["generations"]}
    by_run = {
        generations[payload["generation_alias"]]["run_id"]: payload["classification"]
        for payload in assessment["payloads"]
    }
    assert by_run[run_ids[0]] == "RETAIN_NONREGENERABLE_DIRTY_SOURCE"
    assert assessment["classification_counts"][
        "RETAIN_NONREGENERABLE_DIRTY_SOURCE"
    ] == 1


def test_cross_store_lineage_missing_liveness_registry_blocks_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._payload_open_consumer_status",
        lambda _path: {"status": "NONE"},
    )
    repository = _source_repository(tmp_path / "source")
    runtime_a = _private(tmp_path / "runtime-a")
    runtime_b = _private(tmp_path / "runtime-b")
    run_ids = [_run_id(day, f"nolive{day}") for day in range(1, 5)]
    for index, run_id in enumerate(run_ids):
        root = runtime_a if index % 2 == 0 else runtime_b
        _single_inventory_store(root, f"store-{index}", run_id, repository)

    assessment = assess_cross_store_derived_map_lineage(
        (runtime_a, runtime_b),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    generations = {item["generation_alias"]: item for item in assessment["generations"]}
    by_run = {
        generations[payload["generation_alias"]]["run_id"]: payload["classification"]
        for payload in assessment["payloads"]
    }
    assert by_run[run_ids[0]] == "UNKNOWN_BLOCKED"
    assert "PAYLOAD_RETIRE_CANDIDATE" not in assessment["classification_counts"]
    assert assessment["active_consumer_registry"]["status"] == "UNKNOWN"


def test_cross_store_lineage_accounts_for_unrecognized_generation_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._payload_open_consumer_status",
        lambda _path: {"status": "NONE"},
    )
    repository = _source_repository(tmp_path / "source")
    runtime = _private(tmp_path / "runtime")
    run_id = _run_id(1, "unknownbytes")
    store = _single_inventory_store(runtime, "store", run_id, repository)
    _write(store / "runs" / run_id / "unbound.sqlite3", b"not in manifest")

    assessment = assess_cross_store_derived_map_lineage(
        (runtime,),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    validate_self_hash(assessment)
    byte_accounting = assessment["byte_accounting"]
    assert byte_accounting["sum_invariant"]["status"] == "PASS"
    assert byte_accounting["regular_file_bytes"] == _regular_file_bytes(runtime)
    assert byte_accounting["class_bytes"]["UNSUPPORTED_UNKNOWN"] == len(
        b"not in manifest"
    )
    assert byte_accounting["unrecognized_or_unsupported_bytes"] == len(
        b"not in manifest"
    )
    assert assessment["counts"]["candidate_payload_bytes"] == 0
    assert (
        assessment["counts"]["protected_regular_file_bytes"]
        == assessment["counts"]["total_regular_file_bytes"]
    )


def test_cross_store_lineage_distinguishes_active_and_metadata_only_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._payload_open_consumer_status",
        lambda _path: {"status": "NONE"},
    )
    repository = _source_repository(tmp_path / "source")
    runtime_a = _private(tmp_path / "runtime-a")
    runtime_b = _private(tmp_path / "runtime-b")
    run_ids = [_run_id(day, f"refs{day}") for day in range(1, 6)]
    for index, run_id in enumerate(run_ids):
        root = runtime_a if index % 2 == 0 else runtime_b
        _single_inventory_store(root, f"inventory-{index}", run_id, repository)
    mapper_store = _mapper_store_referencing_inventory(
        runtime_b,
        "live-mapper",
        _run_id(6, "mapperrefs"),
        repository,
        run_ids[1],
    )
    mapper_run_id = json.loads((mapper_store / "CURRENT.json").read_text())["run_id"]
    references = _private(tmp_path / "historical-references")
    _write(references / "receipt.json", run_ids[0].encode())

    assessment = assess_cross_store_derived_map_lineage(
        (runtime_a, runtime_b),
        reference_roots=(references,),
        active_consumer_registry=_active_consumer_registry(
            active_run_ids=[mapper_run_id], negative_run_ids=run_ids
        ),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )

    generations = {item["generation_alias"]: item for item in assessment["generations"]}
    payloads_by_run = {
        generations[payload["generation_alias"]]["run_id"]: payload
        for payload in assessment["payloads"]
        if generations[payload["generation_alias"]]["kind"] == "inventory"
    }
    assert payloads_by_run[run_ids[1]]["classification"] == "RETAIN_ACTIVE_CONSUMER"
    assert payloads_by_run[run_ids[0]]["classification"] == "PAYLOAD_RETIRE_CANDIDATE"
    assert payloads_by_run[run_ids[0]]["metadata_only_reference_count"] == 1


def test_cross_store_lineage_unknown_current_schema_refuses_generically(
    tmp_path: Path,
) -> None:
    runtime = _private(tmp_path / "runtime")
    store = _private(runtime / "unknown-store")
    pointer = seal_document(
        {
            "schema": "fixture.unknown-current.v1",
            "status": "CURRENT",
            "run_id": _run_id(1, "unknown"),
        }
    )
    _write(store / "CURRENT.json", canonical_bytes(pointer))

    with pytest.raises(RetentionError, match="unsupported cross-store CURRENT schema"):
        assess_cross_store_derived_map_lineage(
            (runtime,),
            now=datetime(2026, 8, 30, tzinfo=UTC),
        )


def test_cross_store_lineage_public_outputs_are_layout_independent_and_private(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._payload_open_consumer_status",
        lambda _path: {"status": "NONE"},
    )
    timestamp = "2026-08-30T00:00:00Z"
    first_layout = tmp_path / "alpha_private_operator_layout"
    second_layout = tmp_path / "bravo_private_operator_layout"
    first_source = _source_repository(first_layout / "source")
    second_source = _private(second_layout / "source")
    subprocess.run(
        ["git", "clone", "-q", str(first_source), str(second_source)],
        check=True,
    )
    first_runtime_a = _private(first_layout / "runtime-a")
    first_runtime_b = _private(first_layout / "runtime-b")
    second_runtime_a = _private(second_layout / "runtime-a")
    second_runtime_b = _private(second_layout / "runtime-b")
    run_ids = [_run_id(day, f"layout{day}") for day in range(1, 5)]
    for index, run_id in enumerate(run_ids):
        _single_inventory_store(
            first_runtime_a if index % 2 == 0 else first_runtime_b,
            f"alpha-store-{index}",
            run_id,
            first_source,
        )
        _single_inventory_store(
            second_runtime_a if index % 2 == 0 else second_runtime_b,
            f"beta-store-{index}",
            run_id,
            second_source,
        )
    _write(
        first_runtime_a / "private-ledgers" / "old-ledger.json",
        b"path-bearing private evidence",
    )
    _write(
        second_runtime_a / "private-ledgers" / "old-ledger.json",
        b"path-bearing private evidence",
    )

    first = assess_cross_store_derived_map_lineage(
        (first_runtime_a, first_runtime_b),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )
    second = assess_cross_store_derived_map_lineage(
        (second_runtime_a, second_runtime_b),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )
    assert first == second
    assert first["byte_accounting"]["sum_invariant"]["status"] == "PASS"
    assert first["byte_accounting"][
        "excluded_but_counted_private_workspace_bytes"
    ] == len(b"path-bearing private evidence")
    assert render_cross_store_derived_map_lineage_report(first) == (
        render_cross_store_derived_map_lineage_report(second)
    )

    public_output = tmp_path / "public.json"
    report_output = tmp_path / "report.md"
    private_output = _private(tmp_path / "private-ledgers") / "ledger.json"
    written = write_cross_store_derived_map_lineage_assessment(
        (first_runtime_a, first_runtime_b),
        public_output=public_output,
        report_output=report_output,
        private_ledger_output=private_output,
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )
    assert json.loads(public_output.read_text(encoding="utf-8")) == written
    validate_self_hash(json.loads(private_output.read_text(encoding="utf-8")))

    assert (
        archaeology_main(
            [
                "retention-assess-derived-lineage",
                "--runtime-root",
                str(first_runtime_a),
                "--runtime-root",
                str(first_runtime_b),
                "--format",
                "human",
                "--generated-at",
                timestamp,
            ]
        )
        == 0
    )
    first_cli = capsys.readouterr().out
    assert (
        archaeology_main(
            [
                "retention-assess-derived-lineage",
                "--runtime-root",
                str(second_runtime_a),
                "--runtime-root",
                str(second_runtime_b),
                "--format",
                "human",
                "--generated-at",
                timestamp,
            ]
        )
        == 0
    )
    second_cli = capsys.readouterr().out
    assert first_cli == second_cli

    public_text = (
        json.dumps(first, sort_keys=True)
        + render_cross_store_derived_map_lineage_report(first)
        + public_output.read_text(encoding="utf-8")
        + report_output.read_text(encoding="utf-8")
        + first_cli
    )
    private_text = private_output.read_text(encoding="utf-8")
    for forbidden in (
        str(first_layout),
        str(second_layout),
        str(first_source),
        str(second_source),
        first_layout.name,
        second_layout.name,
        "alpha-store",
        "beta-store",
    ):
        assert forbidden not in public_text
    for expected_private in (str(first_layout), str(first_source), "alpha-store"):
        assert expected_private in private_text


def test_cross_store_lineage_missing_roots_use_generic_failure_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_a = tmp_path / "alpha_private_missing_root" / "runtime"
    missing_b = tmp_path / "beta_private_missing_root" / "runtime"
    with pytest.raises(RetentionError) as first_error:
        assess_cross_store_derived_map_lineage((missing_a,))
    with pytest.raises(RetentionError) as second_error:
        assess_cross_store_derived_map_lineage((missing_b,))
    assert str(first_error.value) == str(second_error.value)

    assert (
        archaeology_main(
            ["retention-assess-derived-lineage", "--runtime-root", str(missing_a)]
        )
        == 2
    )
    first = capsys.readouterr()
    assert (
        archaeology_main(
            ["retention-assess-derived-lineage", "--runtime-root", str(missing_b)]
        )
        == 2
    )
    second = capsys.readouterr()
    assert first.err == second.err
    assert first.out == second.out == ""
    for forbidden in (
        str(missing_a),
        str(missing_b),
        missing_a.parent.name,
        missing_b.parent.name,
    ):
        assert forbidden not in str(first_error.value)
        assert forbidden not in first.err


def test_m74_private_ledger_binding_projection_is_aggregate_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assessment, ledger, _assessment_path, _ledger_path = _m74_binding_fixture(
        tmp_path, monkeypatch
    )
    expected_counts = _m74_fixture_expected_counts(assessment)
    expected_byte_classes = assessment["byte_accounting"]["class_bytes"]

    correction = build_m74_private_ledger_binding_correction(
        assessment,
        ledger,
        now=datetime(2026, 8, 31, 1, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=expected_counts,
        expected_byte_class_bytes=expected_byte_classes,
    )

    validate_self_hash(correction)
    projection = correction["safe_projection"]
    validate_self_hash(projection)
    assert correction["status"] == "PENDING_INDEPENDENT_REVIEW"
    assert correction["safe_projection_receipt_sha256"] == projection[
        "receipt_sha256"
    ]
    assert projection["counts"] == expected_counts
    assert projection["byte_accounting"]["class_bytes"] == expected_byte_classes
    assert projection["byte_accounting"]["sum_invariant_status"] == "PASS"
    public_text = json.dumps(correction, sort_keys=True)
    for forbidden in (
        str(tmp_path),
        "operator_private_layout",
        "runtime-a",
        "runtime-b",
        "store-0",
        "ledger.json",
        ledger["receipt_sha256"],
        sha256_bytes(canonical_bytes(ledger)),
        "/",
        "\\",
    ):
        assert forbidden not in public_text

    tampered_unsigned = json.loads(canonical_bytes(ledger))
    del tampered_unsigned["receipt_sha256"]
    tampered_unsigned["byte_accounting"]["regular_file_bytes"] += 1
    tampered = seal_document(tampered_unsigned)
    with pytest.raises(
        RetentionError,
        match="M74 private ledger correction refused: CONTENT_UNAVAILABLE",
    ):
        build_m74_private_ledger_binding_correction(
            assessment,
            tampered,
            now=datetime(2026, 8, 31, 1, tzinfo=UTC),
            expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
            expected_counts=expected_counts,
            expected_byte_class_bytes=expected_byte_classes,
        )


def test_m74_private_ledger_binding_writer_validates_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assessment, _ledger, assessment_path, ledger_path = _m74_binding_fixture(
        tmp_path, monkeypatch
    )
    expected_counts = _m74_fixture_expected_counts(assessment)
    expected_byte_classes = assessment["byte_accounting"]["class_bytes"]
    output = _private(tmp_path / "public-correction") / "correction.json"

    written = write_m74_private_ledger_binding_correction(
        assessment_path,
        ledger_path,
        output,
        now=datetime(2026, 8, 31, 1, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=expected_counts,
        expected_byte_class_bytes=expected_byte_classes,
    )

    assert json.loads(output.read_text(encoding="utf-8")) == written
    validate_self_hash(written)
    assert output.stat().st_mode & 0o777 == 0o600

    wrong_parent_output = _private(tmp_path / "wrong-parent") / "correction.json"
    with pytest.raises(
        RetentionError,
        match="M74 private ledger correction refused: CONTENT_UNAVAILABLE",
    ):
        write_m74_private_ledger_binding_correction(
            assessment_path,
            ledger_path,
            wrong_parent_output,
            now=datetime(2026, 8, 31, 1, tzinfo=UTC),
            expected_parent_assessment_receipt_sha256="0" * 64,
            expected_counts=expected_counts,
            expected_byte_class_bytes=expected_byte_classes,
        )
    assert not wrong_parent_output.exists()

    os.chmod(ledger_path, 0o644)
    mode_failure_output = _private(tmp_path / "mode-failure") / "correction.json"
    with pytest.raises(
        RetentionError,
        match="M74 private ledger correction refused: CONTENT_UNAVAILABLE",
    ):
        write_m74_private_ledger_binding_correction(
            assessment_path,
            ledger_path,
            mode_failure_output,
            now=datetime(2026, 8, 31, 1, tzinfo=UTC),
            expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
            expected_counts=expected_counts,
            expected_byte_class_bytes=expected_byte_classes,
        )
    assert not mode_failure_output.exists()


def test_m74_private_ledger_binding_failures_are_generic_and_publish_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assessment, ledger, assessment_path, _ledger_path = _m74_binding_fixture(
        tmp_path, monkeypatch
    )
    expected_counts = _m74_fixture_expected_counts(assessment)
    expected_byte_classes = assessment["byte_accounting"]["class_bytes"]
    missing_a = tmp_path / "alpha_missing_private_layout" / "ledger.json"
    missing_b = tmp_path / "bravo_missing_private_layout" / "ledger.json"
    bad_self_hash_a = _private(tmp_path / "alpha_bad_hash") / "ledger.json"
    bad_self_hash_b = _private(tmp_path / "bravo_bad_hash") / "ledger.json"
    _write(bad_self_hash_a, b'{"receipt_sha256":"0000"}\n')
    _write(bad_self_hash_b, b'{"receipt_sha256":"1111"}\n')
    bad_schema = json.loads(canonical_bytes(ledger))
    del bad_schema["receipt_sha256"]
    bad_schema["schema"] = "fixture.invalid-private-ledger.v1"
    bad_schema_path = _private(tmp_path / "mismatched_schema") / "ledger.json"
    _write(bad_schema_path, canonical_bytes(seal_document(bad_schema)))

    errors = []
    for index, candidate in enumerate(
        (missing_a, missing_b, bad_self_hash_a, bad_self_hash_b, bad_schema_path),
        start=1,
    ):
        output = _private(tmp_path / f"failure-output-{index}") / "correction.json"
        with pytest.raises(RetentionError) as raised:
            write_m74_private_ledger_binding_correction(
                assessment_path,
                candidate,
                output,
                now=datetime(2026, 8, 31, 1, tzinfo=UTC),
                expected_parent_assessment_receipt_sha256=(
                    assessment["receipt_sha256"]
                ),
                expected_counts=expected_counts,
                expected_byte_class_bytes=expected_byte_classes,
            )
        errors.append(str(raised.value))
        assert not output.exists()
    assert errors == [
        "M74 private ledger correction refused: CONTENT_UNAVAILABLE"
    ] * len(errors)


def test_m74_private_ledger_binding_public_bytes_are_layout_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_assessment, first_ledger, first_assessment_path, first_ledger_path = (
        _m74_binding_fixture(
            tmp_path,
            monkeypatch,
            layout_name="alpha_operator_private_layout",
        )
    )
    second_assessment, second_ledger, second_assessment_path, second_ledger_path = (
        _m74_binding_fixture(
            tmp_path,
            monkeypatch,
            layout_name="bravo_operator_private_layout",
        )
    )
    assert first_assessment == second_assessment
    assert first_ledger["receipt_sha256"] != second_ledger["receipt_sha256"]
    expected_counts = _m74_fixture_expected_counts(first_assessment)
    expected_byte_classes = first_assessment["byte_accounting"]["class_bytes"]
    first_output = _private(tmp_path / "first-public") / "correction.json"
    second_output = _private(tmp_path / "second-public") / "correction.json"

    write_m74_private_ledger_binding_correction(
        first_assessment_path,
        first_ledger_path,
        first_output,
        now=datetime(2026, 8, 31, 1, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=first_assessment[
            "receipt_sha256"
        ],
        expected_counts=expected_counts,
        expected_byte_class_bytes=expected_byte_classes,
    )
    write_m74_private_ledger_binding_correction(
        second_assessment_path,
        second_ledger_path,
        second_output,
        now=datetime(2026, 8, 31, 1, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=second_assessment[
            "receipt_sha256"
        ],
        expected_counts=expected_counts,
        expected_byte_class_bytes=expected_byte_classes,
    )

    assert first_output.read_bytes() == second_output.read_bytes()
    public_text = first_output.read_text(encoding="utf-8")
    for forbidden in (
        str(tmp_path),
        "alpha_operator_private_layout",
        "bravo_operator_private_layout",
        "runtime-a",
        "runtime-b",
        "source",
        "ledger.json",
        first_ledger["receipt_sha256"],
        second_ledger["receipt_sha256"],
        sha256_bytes(canonical_bytes(first_ledger)),
        sha256_bytes(canonical_bytes(second_ledger)),
        "/",
        "\\",
    ):
        assert forbidden not in public_text


def _write_m74_correction_fixture(path: Path, correction: dict) -> None:
    _write(path, canonical_bytes(correction))


def test_m75_candidate_plan_applies_or_stale_rule_and_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_ids = [_run_id(day, "m75lineage") for day in range(1, 5)]
    assessment, ledger, assessment_path, ledger_path, _run_ids = (
        _m75_multi_run_binding_fixture(
            tmp_path,
            monkeypatch,
            active_consumer_registry=_active_consumer_registry(
                active_run_ids=[run_ids[-1]],
                negative_run_ids=run_ids[:-1],
            ),
        )
    )
    correction = _m74_correction_for_fixture(assessment, ledger)
    correction_path = _private(tmp_path / "m74-correction") / "correction.json"
    _write_m74_correction_fixture(correction_path, correction)
    output = _private(tmp_path / "m75-public") / "plan.json"

    plan = write_m75_mac_derived_map_retention_candidate_plan(
        assessment_path,
        ledger_path,
        correction_path,
        output,
        graph_status=_m75_graph_status(),
        now=datetime(2026, 8, 31, 12, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
    )

    validate_self_hash(plan)
    assert json.loads(output.read_text(encoding="utf-8")) == plan
    assert plan["schema"] == M75_MAC_DERIVED_MAP_RETENTION_CANDIDATE_PLAN_SCHEMA
    assert plan["zero_action"]["payload_move_delete_quarantine_purge_performed"] is False
    assert plan["candidate_plan"]["recoverable_quarantine_candidate_generations"] == 1
    assert plan["candidate_plan"][
        "absence_of_live_consumer_registry_treated_as_negative_proof"
    ] is False
    assert plan["payload_bijection"]["status"] == "PASS"
    assert (
        plan["payload_bijection"]["top_level_payload_records"]
        == plan["payload_bijection"]["nested_generation_payload_records"]
        == plan["census"]["payload_records"]
    )
    assert plan["payload_bijection"]["nested_payload_bytes"] == assessment[
        "counts"
    ]["total_payload_bytes"]
    assert plan["payload_bijection"]["classification_counts"] == assessment[
        "classification_counts"
    ]
    assert plan["payload_bijection"]["classification_bytes"] == assessment[
        "classification_bytes"
    ]
    rows = {row["global_lineage_rank"]: row for row in plan["generations"]}
    assert rows[1]["classification"] == "RETAIN_CURRENT_POINTER"
    assert rows[2]["stale_by_age_gt_24h"] is True
    assert rows[2]["classification"] == "RETAIN_GLOBAL_RECENT"
    assert rows[3]["classification"] == "RETAIN_GLOBAL_RECENT"
    assert rows[4]["stale_by_rank_gt_newest_three"] is True
    assert rows[4]["classification"] == "PAYLOAD_RETIRE_CANDIDATE"
    assert rows[4]["recommendation"] == "RECOVERABLE_QUARANTINE_CANDIDATE"


def test_m75_candidate_plan_rejects_nested_payload_bijection_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_ids = [_run_id(day, "m75lineage") for day in range(1, 5)]
    assessment, ledger, assessment_path, _ledger_path, _run_ids = (
        _m75_multi_run_binding_fixture(
            tmp_path,
            monkeypatch,
            active_consumer_registry=_active_consumer_registry(
                active_run_ids=[run_ids[-1]],
                negative_run_ids=run_ids[:-1],
            ),
        )
    )
    expected_counts = _m74_fixture_expected_counts(assessment)
    expected_byte_classes = assessment["byte_accounting"]["class_bytes"]

    def duplicate_alias(data: dict) -> None:
        first_alias = data["payloads"][0]["payload_alias"]
        second_alias = data["payloads"][1]["payload_alias"]
        data["payloads"][1]["payload_alias"] = first_alias
        for generation in data["generations"]:
            for payload in generation["payloads"]:
                if payload["payload_alias"] == second_alias:
                    payload["payload_alias"] = first_alias

    def empty_nested_payloads(data: dict) -> None:
        for generation in data["generations"]:
            generation["payloads"] = []

    def missing_nested_payload(data: dict) -> None:
        data["generations"][0]["payloads"].pop()

    def extra_nested_payload(data: dict) -> None:
        extra = dict(data["generations"][0]["payloads"][0])
        extra["payload_alias"] = f"{extra['payload_alias']}-extra"
        data["generations"][0]["payloads"].append(extra)

    def mismatched_nested_bytes(data: dict) -> None:
        data["generations"][0]["payloads"][0]["bytes"] += 1

    def mismatched_nested_classification(data: dict) -> None:
        data["generations"][0]["payloads"][0]["classification"] = "UNKNOWN_BLOCKED"

    def cross_generation_substitution(data: dict) -> None:
        data["generations"][0]["payloads"][0]["generation_alias"] = data[
            "generations"
        ][1]["generation_alias"]

    errors = []
    mutations = (
        ("empty-nested", empty_nested_payloads),
        ("duplicate-alias", duplicate_alias),
        ("missing-nested", missing_nested_payload),
        ("extra-nested", extra_nested_payload),
        ("mismatched-bytes", mismatched_nested_bytes),
        ("mismatched-class", mismatched_nested_classification),
        ("cross-generation", cross_generation_substitution),
    )
    for label, mutate in mutations:
        tampered_ledger, tampered_ledger_path = _write_m75_resealed_ledger(
            tmp_path,
            ledger,
            label,
            mutate,
        )
        tampered_correction = _m74_correction_for_fixture(
            assessment,
            tampered_ledger,
        )
        correction_path = _private(tmp_path / f"m74-correction-{label}") / "m74.json"
        _write_m74_correction_fixture(correction_path, tampered_correction)
        output = _private(tmp_path / f"m75-public-{label}") / "plan.json"
        with pytest.raises(RetentionError) as raised:
            write_m75_mac_derived_map_retention_candidate_plan(
                assessment_path,
                tampered_ledger_path,
                correction_path,
                output,
                graph_status=_m75_graph_status(),
                now=datetime(2026, 8, 31, 12, tzinfo=UTC),
                expected_parent_assessment_receipt_sha256=(
                    assessment["receipt_sha256"]
                ),
                expected_counts=expected_counts,
                expected_byte_class_bytes=expected_byte_classes,
            )
        errors.append(str(raised.value))
        assert not output.exists()
    assert errors == [
        "M75 derived-map retention candidate plan refused: CONTENT_UNAVAILABLE"
    ] * len(mutations)


def test_m75_candidate_plan_blocks_when_live_consumer_absence_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assessment, ledger, assessment_path, ledger_path, _run_ids = (
        _m75_multi_run_binding_fixture(tmp_path, monkeypatch)
    )
    correction = _m74_correction_for_fixture(assessment, ledger)
    correction_path = _private(tmp_path / "m74-correction") / "correction.json"
    _write_m74_correction_fixture(correction_path, correction)
    output = _private(tmp_path / "m75-public") / "plan.json"

    plan = write_m75_mac_derived_map_retention_candidate_plan(
        assessment_path,
        ledger_path,
        correction_path,
        output,
        graph_status=_m75_graph_status(),
        now=datetime(2026, 8, 31, 12, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
    )

    assert plan["candidate_plan"]["recoverable_quarantine_candidate_generations"] == 0
    assert "UNKNOWN_BLOCKED" in plan["candidate_plan"]["classification_counts"]
    assert any(
        "ACTIVE_CONSUMER_ABSENCE_NOT_PROVED" in row["blockers"]
        for row in plan["generations"]
        if row["global_lineage_rank"] > 3
    )


def test_m75_candidate_plan_blocks_unknown_schema_even_with_registry_negative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_ids = [_run_id(day, "m75lineage") for day in range(1, 5)]
    assessment, ledger, assessment_path, _ledger_path, _run_ids = (
        _m75_multi_run_binding_fixture(
            tmp_path,
            monkeypatch,
            active_consumer_registry=_active_consumer_registry(
                active_run_ids=[run_ids[-1]],
                negative_run_ids=run_ids[:-1],
            ),
        )
    )
    mutated = json.loads(canonical_bytes(ledger))
    del mutated["receipt_sha256"]
    for generation in mutated["generations"]:
        if generation["global_lineage_rank"] == 4:
            generation["manifest_schema"] = "fixture.unknown-map-manifest.v1"
    ledger = seal_document(mutated)
    ledger_path = _private(tmp_path / "unknown-schema-ledger") / "ledger.json"
    _write(ledger_path, canonical_bytes(ledger))
    correction = _m74_correction_for_fixture(assessment, ledger)
    correction_path = _private(tmp_path / "m74-correction") / "correction.json"
    _write_m74_correction_fixture(correction_path, correction)
    output = _private(tmp_path / "m75-public") / "plan.json"

    plan = write_m75_mac_derived_map_retention_candidate_plan(
        assessment_path,
        ledger_path,
        correction_path,
        output,
        graph_status=_m75_graph_status(),
        now=datetime(2026, 8, 31, 12, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
    )

    stale_oldest = next(
        row for row in plan["generations"] if row["global_lineage_rank"] == 4
    )
    assert stale_oldest["stale"] is True
    assert stale_oldest["manifest_schema_supported"] is False
    assert stale_oldest["classification"] == "UNKNOWN_BLOCKED"
    assert "UNKNOWN_OR_UNSUPPORTED_SCHEMA" in stale_oldest["blockers"]
    assert plan["candidate_plan"]["recoverable_quarantine_candidate_generations"] == 0


def test_m75_candidate_plan_blocks_dirty_or_incomplete_payload_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_ids = [_run_id(day, "m75lineage") for day in range(1, 5)]
    assessment, ledger, assessment_path, ledger_path, _run_ids = (
        _m75_multi_run_binding_fixture(
            tmp_path,
            monkeypatch,
            active_consumer_registry=_active_consumer_registry(
                active_run_ids=[run_ids[-1]],
                negative_run_ids=run_ids[:-1],
            ),
            dirty_oldest=True,
        )
    )
    correction = _m74_correction_for_fixture(assessment, ledger)
    correction_path = _private(tmp_path / "m74-correction") / "correction.json"
    _write_m74_correction_fixture(correction_path, correction)
    output = _private(tmp_path / "m75-public") / "plan.json"

    plan = write_m75_mac_derived_map_retention_candidate_plan(
        assessment_path,
        ledger_path,
        correction_path,
        output,
        graph_status=_m75_graph_status(),
        now=datetime(2026, 8, 31, 12, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
    )

    stale_oldest = next(
        row for row in plan["generations"] if row["global_lineage_rank"] == 4
    )
    assert stale_oldest["stale"] is True
    assert stale_oldest["classification"] == "UNKNOWN_BLOCKED"
    assert "PAYLOAD_STATE_DIRTY_OR_NONREGENERABLE" in stale_oldest["blockers"]
    assert plan["candidate_plan"]["recoverable_quarantine_candidate_generations"] == 0


def test_m75_candidate_plan_public_bytes_are_layout_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_assessment, first_ledger, first_assessment_path, first_ledger_path = (
        _m74_binding_fixture(
            tmp_path,
            monkeypatch,
            layout_name="alpha_operator_private_layout",
        )
    )
    second_assessment, second_ledger, second_assessment_path, second_ledger_path = (
        _m74_binding_fixture(
            tmp_path,
            monkeypatch,
            layout_name="bravo_operator_private_layout",
        )
    )
    assert first_assessment == second_assessment
    first_correction = _m74_correction_for_fixture(first_assessment, first_ledger)
    second_correction = _m74_correction_for_fixture(second_assessment, second_ledger)
    assert first_correction == second_correction
    first_correction_path = _private(tmp_path / "first-correction") / "m74.json"
    second_correction_path = _private(tmp_path / "second-correction") / "m74.json"
    _write_m74_correction_fixture(first_correction_path, first_correction)
    _write_m74_correction_fixture(second_correction_path, second_correction)
    first_output = _private(tmp_path / "first-public") / "plan.json"
    second_output = _private(tmp_path / "second-public") / "plan.json"
    expected_counts = _m74_fixture_expected_counts(first_assessment)
    expected_byte_classes = first_assessment["byte_accounting"]["class_bytes"]

    write_m75_mac_derived_map_retention_candidate_plan(
        first_assessment_path,
        first_ledger_path,
        first_correction_path,
        first_output,
        graph_status=_m75_graph_status(),
        now=datetime(2026, 8, 31, 12, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=first_assessment[
            "receipt_sha256"
        ],
        expected_counts=expected_counts,
        expected_byte_class_bytes=expected_byte_classes,
    )
    write_m75_mac_derived_map_retention_candidate_plan(
        second_assessment_path,
        second_ledger_path,
        second_correction_path,
        second_output,
        graph_status=_m75_graph_status(),
        now=datetime(2026, 8, 31, 12, tzinfo=UTC),
        expected_parent_assessment_receipt_sha256=second_assessment[
            "receipt_sha256"
        ],
        expected_counts=expected_counts,
        expected_byte_class_bytes=expected_byte_classes,
    )

    assert first_output.read_bytes() == second_output.read_bytes()
    public_text = first_output.read_text(encoding="utf-8")
    for forbidden in (
        str(tmp_path),
        "alpha_operator_private_layout",
        "bravo_operator_private_layout",
        "runtime-a",
        "runtime-b",
        "source",
        "ledger.json",
        first_ledger["receipt_sha256"],
        second_ledger["receipt_sha256"],
        sha256_bytes(canonical_bytes(first_ledger)),
        sha256_bytes(canonical_bytes(second_ledger)),
        "/",
        "\\",
    ):
        assert forbidden not in public_text


def test_m75_candidate_plan_failures_are_generic_and_publish_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assessment, ledger, assessment_path, ledger_path = _m74_binding_fixture(
        tmp_path, monkeypatch
    )
    correction = _m74_correction_for_fixture(assessment, ledger)
    correction_path = _private(tmp_path / "m74-correction") / "correction.json"
    _write_m74_correction_fixture(correction_path, correction)
    expected_counts = _m74_fixture_expected_counts(assessment)
    expected_byte_classes = assessment["byte_accounting"]["class_bytes"]
    missing_ledger_a = tmp_path / "alpha_missing_private_layout" / "ledger.json"
    missing_ledger_b = tmp_path / "bravo_missing_private_layout" / "ledger.json"
    bad_correction = json.loads(canonical_bytes(correction))
    del bad_correction["receipt_sha256"]
    bad_correction["safe_projection"]["counts"]["payload_records"] += 1
    bad_correction_path = _private(tmp_path / "bad-correction") / "m74.json"
    _write(bad_correction_path, canonical_bytes(seal_document(bad_correction)))
    bad_graph = dict(_m75_graph_status())
    bad_graph["reason"] = "contains/private/layout"

    errors = []
    for index, (candidate_ledger, candidate_correction, graph_status) in enumerate(
        (
            (missing_ledger_a, correction_path, _m75_graph_status()),
            (missing_ledger_b, correction_path, _m75_graph_status()),
            (ledger_path, bad_correction_path, _m75_graph_status()),
            (ledger_path, correction_path, bad_graph),
        ),
        start=1,
    ):
        output = _private(tmp_path / f"failure-output-{index}") / "plan.json"
        with pytest.raises(RetentionError) as raised:
            write_m75_mac_derived_map_retention_candidate_plan(
                assessment_path,
                candidate_ledger,
                candidate_correction,
                output,
                graph_status=graph_status,
                now=datetime(2026, 8, 31, 12, tzinfo=UTC),
                expected_parent_assessment_receipt_sha256=(
                    assessment["receipt_sha256"]
                ),
                expected_counts=expected_counts,
                expected_byte_class_bytes=expected_byte_classes,
            )
        errors.append(str(raised.value))
        assert not output.exists()
    assert errors == [
        "M75 derived-map retention candidate plan refused: CONTENT_UNAVAILABLE"
    ] * len(errors)


def test_m77_liveness_canary_promotes_only_fully_proved_inactive_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    (
        assessment,
        ledger,
        correction,
        plan,
        _assessment_path,
        _ledger_path,
        _correction_path,
        _m75_path,
        cohort_aliases,
        expected_bytes,
    ) = _m77_fixture(tmp_path, monkeypatch)
    observation = observe_m77_derived_map_liveness(
        ledger,
        plan,
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        task_lease_census=_m77_complete_task_census(cohort_aliases),
        capability_adoption_liveness=_m77_complete_capability_liveness(
            cohort_aliases
        ),
        now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
    )

    result = build_m77_scoped_derived_map_liveness_assessment(
        assessment,
        ledger,
        correction,
        plan,
        observation,
        graph_status=_m77_graph_status(),
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        now=datetime(2026, 8, 31, 12, 31, tzinfo=UTC),
        expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
        task_lease_census=_m77_complete_task_census(cohort_aliases),
        capability_adoption_liveness=_m77_complete_capability_liveness(
            cohort_aliases
        ),
    )

    validate_self_hash(observation)
    validate_self_hash(result)
    assert observation["schema"] == M77_DERIVED_MAP_LIVENESS_OBSERVATION_SCHEMA
    assert result["schema"] == M77_SCOPED_DERIVED_MAP_LIVENESS_ASSESSMENT_SCHEMA
    assert result["candidate_plan"]["recoverable_quarantine_candidate_generations"] == 1
    assert result["candidate_plan"]["consumer_proof_alone_clears_other_blockers"] is False
    row = result["generations"][0]
    assert row["liveness"] == "INACTIVE_PROVED"
    assert row["payload_state"] == "PASS"
    assert row["classification"] == "PAYLOAD_RETIRE_CANDIDATE"
    assert row["recommendation"] == "RECOVERABLE_QUARANTINE_CANDIDATE"
    public_text = canonical_bytes(result).decode() + render_m77_scoped_derived_map_liveness_report(result)
    for forbidden in (str(tmp_path), "operator_private_layout", "ledger.json", "/", "\\"):
        assert forbidden not in public_text


def test_m77_liveness_keeps_unknown_when_required_sources_are_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    (
        assessment,
        ledger,
        correction,
        plan,
        _assessment_path,
        _ledger_path,
        _correction_path,
        _m75_path,
        cohort_aliases,
        expected_bytes,
    ) = _m77_fixture(tmp_path, monkeypatch)
    observation = observe_m77_derived_map_liveness(
        ledger,
        plan,
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
    )

    result = build_m77_scoped_derived_map_liveness_assessment(
        assessment,
        ledger,
        correction,
        plan,
        observation,
        graph_status=_m77_graph_status(),
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        now=datetime(2026, 8, 31, 12, 31, tzinfo=UTC),
        expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
    )

    row = result["generations"][0]
    assert row["liveness"] == "UNKNOWN"
    assert row["classification"] == "UNKNOWN_BLOCKED"
    assert "M77_LIVENESS_UNKNOWN" in row["blockers"]
    assert result["candidate_plan"]["recoverable_quarantine_candidate_generations"] == 0


def test_m77_rejects_resealed_unknown_to_inactive_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    (
        assessment,
        ledger,
        correction,
        plan,
        _assessment_path,
        _ledger_path,
        _correction_path,
        _m75_path,
        cohort_aliases,
        expected_bytes,
    ) = _m77_fixture(tmp_path, monkeypatch)
    observation = observe_m77_derived_map_liveness(
        ledger,
        plan,
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
    )

    def promote_unknown(tampered: dict) -> None:
        tampered["runs"][0]["liveness"] = "INACTIVE_PROVED"
        tampered["runs"][0]["reasons"] = [
            "ALL_REQUIRED_SOURCES_OBSERVED_NO_ACTIVE_BINDING"
        ]
        tampered["liveness_counts"] = {"INACTIVE_PROVED": 1}
        tampered["source_completeness"]["codex_task_lease_census"] = True
        tampered["source_completeness"]["capability_adoption_liveness"] = True
        tampered["shared_sources"]["codex_task_lease_census"] = {
            "status": "COMPLETE",
            "covered_generation_count": 1,
        }
        tampered["shared_sources"]["capability_adoption_liveness"] = {
            "status": "COMPLETE",
            "covered_generation_count": 1,
        }

    forged = _m77_resealed_observation(observation, promote_unknown)

    with pytest.raises(RetentionError, match="M77 derived-map liveness assessment refused"):
        build_m77_scoped_derived_map_liveness_assessment(
            assessment,
            ledger,
            correction,
            plan,
            forged,
            graph_status=_m77_graph_status(),
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_bytes,
            now=datetime(2026, 8, 31, 12, 31, tzinfo=UTC),
            expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
            expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
            expected_counts=_m74_fixture_expected_counts(assessment),
            expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
        )


def test_m77_rejects_resealed_row_source_reason_and_count_mismatches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    (
        assessment,
        ledger,
        correction,
        plan,
        _assessment_path,
        _ledger_path,
        _correction_path,
        _m75_path,
        cohort_aliases,
        expected_bytes,
    ) = _m77_fixture(tmp_path, monkeypatch)
    task_census = _m77_complete_task_census(cohort_aliases)
    capability_liveness = _m77_complete_capability_liveness(cohort_aliases)
    observation = observe_m77_derived_map_liveness(
        ledger,
        plan,
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        task_lease_census=task_census,
        capability_adoption_liveness=capability_liveness,
        now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
    )

    def row_status(tampered: dict) -> None:
        tampered["runs"][0]["open_consumer_probe"]["status"] = "ACTIVE"

    def row_reason(tampered: dict) -> None:
        tampered["runs"][0]["reasons"] = ["FORGED_REASON"]

    def source_status(tampered: dict) -> None:
        tampered["shared_sources"]["codex_task_lease_census"]["status"] = "UNKNOWN"

    def source_count(tampered: dict) -> None:
        tampered["shared_sources"]["codex_task_lease_census"][
            "covered_generation_count"
        ] += 1

    def liveness_count(tampered: dict) -> None:
        tampered["liveness_counts"]["INACTIVE_PROVED"] += 1

    for mutate in (
        row_status,
        row_reason,
        source_status,
        source_count,
        liveness_count,
    ):
        forged = _m77_resealed_observation(observation, mutate)
        with pytest.raises(
            RetentionError,
            match="M77 derived-map liveness assessment refused",
        ):
            build_m77_scoped_derived_map_liveness_assessment(
                assessment,
                ledger,
                correction,
                plan,
                forged,
                graph_status=_m77_graph_status(),
                cohort_aliases=cohort_aliases,
                expected_cohort_bytes=expected_bytes,
                now=datetime(2026, 8, 31, 12, 31, tzinfo=UTC),
                expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
                expected_parent_assessment_receipt_sha256=assessment[
                    "receipt_sha256"
                ],
                expected_counts=_m74_fixture_expected_counts(assessment),
                expected_byte_class_bytes=assessment["byte_accounting"][
                    "class_bytes"
                ],
                task_lease_census=task_census,
                capability_adoption_liveness=capability_liveness,
            )


def test_m77_liveness_retains_active_consumer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    (
        assessment,
        ledger,
        correction,
        plan,
        _assessment_path,
        _ledger_path,
        _correction_path,
        _m75_path,
        cohort_aliases,
        expected_bytes,
    ) = _m77_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "modules.operations.archaeology.retention._payload_open_consumer_status",
        lambda _path: {"status": "ACTIVE", "reason": "fixture-open"},
    )
    observation = observe_m77_derived_map_liveness(
        ledger,
        plan,
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        task_lease_census=_m77_complete_task_census(cohort_aliases),
        capability_adoption_liveness=_m77_complete_capability_liveness(
            cohort_aliases
        ),
        now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
    )

    result = build_m77_scoped_derived_map_liveness_assessment(
        assessment,
        ledger,
        correction,
        plan,
        observation,
        graph_status=_m77_graph_status(),
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        now=datetime(2026, 8, 31, 12, 31, tzinfo=UTC),
        expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
        task_lease_census=_m77_complete_task_census(cohort_aliases),
        capability_adoption_liveness=_m77_complete_capability_liveness(
            cohort_aliases
        ),
    )

    row = result["generations"][0]
    assert row["liveness"] == "ACTIVE"
    assert row["classification"] == "RETAIN_ACTIVE_CONSUMER"
    assert row["recommendation"] == "NO_RETENTION_ACTION_RECOMMENDED"


def test_m77_rejects_expired_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    (
        assessment,
        ledger,
        correction,
        plan,
        _assessment_path,
        _ledger_path,
        _correction_path,
        _m75_path,
        cohort_aliases,
        expected_bytes,
    ) = _m77_fixture(tmp_path, monkeypatch)
    observation = observe_m77_derived_map_liveness(
        ledger,
        plan,
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        task_lease_census=_m77_complete_task_census(cohort_aliases),
        capability_adoption_liveness=_m77_complete_capability_liveness(
            cohort_aliases
        ),
        now=datetime(2026, 8, 31, 12, tzinfo=UTC),
        freshness_seconds=60,
    )

    with pytest.raises(RetentionError, match="M77 derived-map liveness assessment refused"):
        build_m77_scoped_derived_map_liveness_assessment(
            assessment,
            ledger,
            correction,
            plan,
            observation,
            graph_status=_m77_graph_status(),
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_bytes,
            now=datetime(2026, 8, 31, 12, 2, tzinfo=UTC),
            expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
            expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
            expected_counts=_m74_fixture_expected_counts(assessment),
            expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
            task_lease_census=_m77_complete_task_census(cohort_aliases),
            capability_adoption_liveness=_m77_complete_capability_liveness(
                cohort_aliases
            ),
        )


def test_m77_consumer_proof_does_not_clear_dirty_source_blocker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    (
        assessment,
        ledger,
        correction,
        plan,
        _assessment_path,
        _ledger_path,
        _correction_path,
        _m75_path,
        cohort_aliases,
        expected_bytes,
    ) = _m77_fixture(tmp_path, monkeypatch, dirty_oldest=True)
    observation = observe_m77_derived_map_liveness(
        ledger,
        plan,
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        task_lease_census=_m77_complete_task_census(cohort_aliases),
        capability_adoption_liveness=_m77_complete_capability_liveness(
            cohort_aliases
        ),
        now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
    )

    result = build_m77_scoped_derived_map_liveness_assessment(
        assessment,
        ledger,
        correction,
        plan,
        observation,
        graph_status=_m77_graph_status(),
        cohort_aliases=cohort_aliases,
        expected_cohort_bytes=expected_bytes,
        now=datetime(2026, 8, 31, 12, 31, tzinfo=UTC),
        expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
        expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
        expected_counts=_m74_fixture_expected_counts(assessment),
        expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
        task_lease_census=_m77_complete_task_census(cohort_aliases),
        capability_adoption_liveness=_m77_complete_capability_liveness(
            cohort_aliases
        ),
    )

    row = result["generations"][0]
    assert row["liveness"] == "INACTIVE_PROVED"
    assert row["classification"] == "UNKNOWN_BLOCKED"
    assert "MISSING_OR_NONREGENERABLE_PROVENANCE" in row["blockers"]


def test_m77_rejects_alias_substitution_and_duplicate_nested_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    (
        assessment,
        ledger,
        _correction,
        plan,
        assessment_path,
        ledger_path,
        correction_path,
        m75_path,
        cohort_aliases,
        expected_bytes,
    ) = _m77_fixture(tmp_path, monkeypatch)
    tampered = json.loads(canonical_bytes(plan))
    del tampered["receipt_sha256"]
    tampered["generations"][3]["payload_bytes"] += 1
    tampered_path = _private(tmp_path / "m77-tampered-plan") / "plan.json"
    _write(tampered_path, canonical_bytes(seal_document(tampered)))
    output = _private(tmp_path / "m77-public") / "assessment.json"

    with pytest.raises(RetentionError, match="M77 derived-map liveness assessment refused"):
        write_m77_scoped_derived_map_liveness_assessment(
            assessment_path,
            ledger_path,
            correction_path,
            tampered_path,
            output,
            graph_status=_m77_graph_status(),
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_bytes,
            task_lease_census=_m77_complete_task_census(cohort_aliases),
            capability_adoption_liveness=_m77_complete_capability_liveness(
                cohort_aliases
            ),
            now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
            expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
            expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
            expected_counts=_m74_fixture_expected_counts(assessment),
            expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
        )
    assert not output.exists()

    duplicate_raw = canonical_bytes(plan).replace(
        b'"kind":"inventory"',
        b'"kind":"inventory","kind":"inventory"',
        1,
    )
    duplicate_path = _private(tmp_path / "m77-duplicate-plan") / "plan.json"
    _write(duplicate_path, duplicate_raw)
    duplicate_output = _private(tmp_path / "m77-public-duplicate") / "assessment.json"
    with pytest.raises(RetentionError) as raised:
        write_m77_scoped_derived_map_liveness_assessment(
            assessment_path,
            ledger_path,
            correction_path,
            duplicate_path,
            duplicate_output,
            graph_status=_m77_graph_status(),
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_bytes,
            task_lease_census=_m77_complete_task_census(cohort_aliases),
            capability_adoption_liveness=_m77_complete_capability_liveness(
                cohort_aliases
            ),
            now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
            expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
            expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
            expected_counts=_m74_fixture_expected_counts(assessment),
            expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
        )
    assert str(raised.value) == "M77 derived-map liveness assessment refused: CONTENT_UNAVAILABLE"
    assert not duplicate_output.exists()


def test_m77_missing_payload_proof_refuses_and_publishes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    (
        assessment,
        ledger,
        _correction,
        _plan,
        assessment_path,
        ledger_path,
        correction_path,
        m75_path,
        cohort_aliases,
        expected_bytes,
    ) = _m77_fixture(tmp_path, monkeypatch)
    selected = ledger["generations"][3]
    payload_path = Path(selected["payloads"][0]["private_artifact_path"])
    payload_path.unlink()
    output = _private(tmp_path / "m77-public-missing") / "assessment.json"

    with pytest.raises(RetentionError) as raised:
        write_m77_scoped_derived_map_liveness_assessment(
            assessment_path,
            ledger_path,
            correction_path,
            m75_path,
            output,
            graph_status=_m77_graph_status(),
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_bytes,
            task_lease_census=_m77_complete_task_census(cohort_aliases),
            capability_adoption_liveness=_m77_complete_capability_liveness(
                cohort_aliases
            ),
            now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
            expected_m75_plan_receipt_sha256=None,
            expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
            expected_counts=_m74_fixture_expected_counts(assessment),
            expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
        )
    assert str(raised.value) == "M77 derived-map liveness assessment refused: CONTENT_UNAVAILABLE"
    assert not output.exists()


def test_m77_public_bytes_are_layout_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m77_patch_clean_liveness(monkeypatch)
    first = _m77_fixture(tmp_path / "alpha", monkeypatch)
    second = _m77_fixture(tmp_path / "bravo", monkeypatch)
    output_a = _private(tmp_path / "m77-alpha-public") / "assessment.json"
    report_a = _private(tmp_path / "m77-alpha-public") / "report.md"
    output_b = _private(tmp_path / "m77-bravo-public") / "assessment.json"
    report_b = _private(tmp_path / "m77-bravo-public") / "report.md"

    for fixture, output, report in ((first, output_a, report_a), (second, output_b, report_b)):
        (
            assessment,
            _ledger,
            _correction,
            plan,
            assessment_path,
            ledger_path,
            correction_path,
            m75_path,
            aliases,
            expected_bytes,
        ) = fixture
        write_m77_scoped_derived_map_liveness_assessment(
            assessment_path,
            ledger_path,
            correction_path,
            m75_path,
            output,
            report_output=report,
            graph_status=_m77_graph_status(),
            cohort_aliases=aliases,
            expected_cohort_bytes=expected_bytes,
            task_lease_census=_m77_complete_task_census(aliases),
            capability_adoption_liveness=_m77_complete_capability_liveness(aliases),
            now=datetime(2026, 8, 31, 12, 30, tzinfo=UTC),
            expected_m75_plan_receipt_sha256=plan["receipt_sha256"],
            expected_parent_assessment_receipt_sha256=assessment["receipt_sha256"],
            expected_counts=_m74_fixture_expected_counts(assessment),
            expected_byte_class_bytes=assessment["byte_accounting"]["class_bytes"],
        )

    assert output_a.read_bytes() == output_b.read_bytes()
    assert report_a.read_bytes() == report_b.read_bytes()
    public_text = output_a.read_text(encoding="utf-8") + report_a.read_text(
        encoding="utf-8"
    )
    for forbidden in (str(tmp_path), "alpha", "bravo", "ledger.json", "/", "\\"):
        assert forbidden not in public_text
