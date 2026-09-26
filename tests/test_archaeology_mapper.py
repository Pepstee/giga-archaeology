from __future__ import annotations

import json
import os
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from modules.operations.archaeology.evidence import (
    canonical_bytes,
    sha256_bytes,
    validate_self_hash,
)
from modules.operations.archaeology.map_catalog import route_query_maps
from modules.operations.archaeology.mapper import (
    MapperError,
    SUPPORTED_MAPS,
    _fragment_payload,
    audit_mapper,
    current_mapper_run,
    query_mapper,
    refresh_mapper,
)
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
    refresh_navigation_inventory_delta,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


@pytest.fixture()
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "mapped-fixture"\nversion = "1"\n', encoding="utf-8"
    )
    (root / "src/pkg").mkdir(parents=True)
    (root / "src/pkg/__init__.py").write_text("", encoding="utf-8")
    (root / "src/pkg/main.py").write_text(
        "def main():\n    return 1\n", encoding="utf-8"
    )
    (root / "docs").mkdir()
    (root / "docs/guide.md").write_text("# Guide\n", encoding="utf-8")
    (root / "memory").mkdir()
    (root / "memory/private.md").write_text("private\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _database(run) -> sqlite3.Connection:
    connection = sqlite3.connect(run.run_directory / "facts.sqlite3")
    connection.row_factory = sqlite3.Row
    return connection


def test_m01_compiles_authenticated_inventory_and_structure(
    repository: Path, tmp_path: Path
) -> None:
    inventory = refresh_navigation_inventory(repository, tmp_path / "inventory")
    run = refresh_mapper(tmp_path / "inventory", tmp_path / "mapper")
    validate_self_hash(run.manifest)
    assert run.manifest["inventory"]["run_id"] == inventory.manifest["run_id"]
    assert run.manifest["maps"]["inventory"] == "AVAILABLE"
    assert run.manifest["maps"]["structure"] == "AVAILABLE_PARTIAL"
    assert {"inventory", "structure"} <= set(run.manifest["maps"]["available"])
    assert {
        key: run.manifest["counts"][key]
        for key in (
            "federated_artifacts",
            "artifacts",
            "directories",
            "logical_containers",
            "sensitive_metadata",
        )
    } == {
        "federated_artifacts": 5,
        "artifacts": 5,
        "directories": 5,
        "logical_containers": 2,
        "sensitive_metadata": 1,
    }
    connection = _database(run)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "sources",
            "entities",
            "artifact_properties",
            "relations",
            "observations",
            "locations",
            "derivations",
            "coverage",
            "conflicts",
            "map_views",
            "run_inputs",
        } <= tables
        observation_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list('observations')")
        }
        assert "observations_entity_idx" in observation_indexes
        assert [
            row[2]
            for row in connection.execute(
                "PRAGMA index_info('observations_entity_idx')"
            )
        ] == ["entity_id", "predicate"]
        entity_id = connection.execute(
            "SELECT entity_id FROM observations ORDER BY entity_id LIMIT 1"
        ).fetchone()[0]
        location_plan = {
            row[3]
            for row in connection.execute(
                """EXPLAIN QUERY PLAN
                   SELECT l.path,l.byte_start,l.byte_end,l.line_start,l.line_end,
                          l.column_start,l.column_end
                   FROM locations l
                   JOIN observations o ON o.observation_id=l.location_id
                   WHERE o.entity_id=?
                   ORDER BY CASE o.predicate
                              WHEN 'PYTHON_DEFINITION' THEN 0
                              WHEN 'SHELL_DEFINITION' THEN 0
                              WHEN 'JAVASCRIPT_DEFINITION' THEN 0
                              ELSE 1
                            END,
                            o.predicate,o.observation_id LIMIT 1""",
                (entity_id,),
            )
        }
        assert any("observations_entity_idx" in detail for detail in location_plan)
        assert all("SCAN o" not in detail for detail in location_plan)
        assert (
            connection.execute("SELECT count(*) FROM artifact_properties").fetchone()[0]
            == 0
        )
    finally:
        connection.close()

    sensitive = query_mapper(tmp_path / "mapper", "memory/private.md")
    assert sensitive["results"][0]["privacy_class"] == "SENSITIVE_METADATA"


def test_project_manifest_change_reuses_all_python_source_fragments(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import modules.operations.archaeology.python_map as python_map

    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    refresh_mapper(inventory_store, mapper_store)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("project metadata change reparsed Python source")

    monkeypatch.setattr(python_map.ast, "parse", forbidden)
    (repository / "pyproject.toml").write_text(
        '[project]\nname = "mapped-fixture"\nversion = "2"\n'
        '[project.scripts]\nfixture = "pkg.main:main"\n',
        encoding="utf-8",
    )
    refresh_navigation_inventory(repository, inventory_store)
    second = refresh_mapper(inventory_store, mapper_store)

    assert second.manifest["scan"]["python_fragments"] == {
        "total": 3,
        "reused": 2,
        "recomputed": 1,
        "deleted": 0,
    }
    result = query_mapper(mapper_store, "fixture", maps=("api_events",))
    assert any(
        item["kind"] == "ENTRYPOINT"
        and item["attributes"]["kind"] == "PYTHON_PROJECT_SCRIPT"
        for item in result["results"]
    )


def test_cached_fragment_payload_refuses_corruption_and_ambiguous_disposition() -> None:
    payload = {"file": {"path": "pkg/main.py"}, "failure": None}
    payload_json = canonical_bytes(payload).decode("utf-8").rstrip("\n")
    row = {
        "path": "pkg/main.py",
        "fragment_kind": "PYTHON_SOURCE",
        "source_identity_sha256": "a" * 64,
        "context_sha256": "b" * 64,
        "extractor_sha256": "c" * 64,
        "payload_sha256": sha256_bytes(payload_json.encode("utf-8")),
        "payload_json": payload_json,
        "first_seen_run_id": "run-1",
    }
    assert _fragment_payload(
        row,
        expected_kind="PYTHON_SOURCE",
        expected_source_identity="a" * 64,
        expected_context="b" * 64,
        expected_extractor="c" * 64,
    ) == (payload, "run-1")

    with pytest.raises(MapperError, match="payload hash mismatch"):
        _fragment_payload(
            {**row, "payload_sha256": "d" * 64},
            expected_kind="PYTHON_SOURCE",
            expected_source_identity="a" * 64,
            expected_context="b" * 64,
            expected_extractor="c" * 64,
        )

    ambiguous = {"file": None, "failure": None}
    ambiguous_json = canonical_bytes(ambiguous).decode("utf-8").rstrip("\n")
    with pytest.raises(MapperError, match="disposition is ambiguous"):
        _fragment_payload(
            {
                **row,
                "payload_json": ambiguous_json,
                "payload_sha256": sha256_bytes(ambiguous_json.encode("utf-8")),
            },
            expected_kind="PYTHON_SOURCE",
            expected_source_identity="a" * 64,
            expected_context="b" * 64,
            expected_extractor="c" * 64,
        )


def test_mapper_propagates_partial_inventory_truthfully(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    (repository / "src/pkg/main.py").write_text(
        "def main():\n    return 2\n", encoding="utf-8"
    )
    _git(repository, "add", "src/pkg/main.py")
    _git(repository, "commit", "-qm", "architecture milestone")
    inventory = refresh_navigation_inventory_delta(repository, inventory_store)
    run = refresh_mapper(inventory_store, mapper_store)
    assert inventory.manifest["status"] == "PARTIAL"
    assert run.manifest["status"] == "PARTIAL"
    pointer = json.loads((mapper_store / "CURRENT.json").read_text(encoding="utf-8"))
    assert pointer["status"] == "PARTIAL"


def test_unified_derivations_close_source_and_parent_provenance(
    repository: Path, tmp_path: Path
) -> None:
    refresh_navigation_inventory(repository, tmp_path / "inventory")
    run = refresh_mapper(tmp_path / "inventory", tmp_path / "mapper")
    connection = _database(run)
    try:
        assert run.manifest["counts"]["derivations"] > 0
        for table, fact_id in (
            ("entities", "entity_id"),
            ("relations", "relation_id"),
            ("observations", "observation_id"),
        ):
            missing = connection.execute(
                f"""SELECT COUNT(*) FROM {table} f
                    WHERE f.source_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM derivations d
                        WHERE d.fact_id=f.{fact_id}
                          AND d.parent_kind='SOURCE'
                          AND d.parent_id=f.source_id
                    )"""
            ).fetchone()[0]
            assert missing == 0
        assert (
            connection.execute(
                """SELECT COUNT(*) FROM relations r WHERE NOT EXISTS (
                       SELECT 1 FROM derivations d
                       WHERE d.fact_id=r.relation_id
                         AND d.parent_kind='SUBJECT_ENTITY'
                         AND d.parent_id=r.subject_id
                   ) OR NOT EXISTS (
                       SELECT 1 FROM derivations d
                       WHERE d.fact_id=r.relation_id
                         AND d.parent_kind='OBJECT_ENTITY'
                         AND d.parent_id=r.object_id
                   )"""
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                """SELECT COUNT(*) FROM observations o WHERE NOT EXISTS (
                       SELECT 1 FROM derivations d
                       WHERE d.fact_id=o.observation_id
                         AND d.parent_kind='SUBJECT_ENTITY'
                         AND d.parent_id=o.entity_id
                   )"""
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()


def test_mapper_audit_proves_all_views_provenance_and_confidence(
    repository: Path, tmp_path: Path
) -> None:
    refresh_navigation_inventory(repository, tmp_path / "inventory")
    refresh_mapper(tmp_path / "inventory", tmp_path / "mapper")

    audit = audit_mapper(tmp_path / "mapper")

    validate_self_hash(audit)
    assert audit["status"] == "PASS"
    assert audit["failures"] == []
    assert audit["checks"]["map_registration"] == {
        "status": "PASS",
        "expected": 22,
        "registered_views": 22,
        "covered_maps": 22,
    }
    assert audit["checks"]["all_map_query_probe"]["maps"] == 22
    assert audit["claims"]["all_22_map_views_queryable"] is True
    assert audit["claims"]["fact_integrity_satisfied"] is True
    assert audit["claims"]["exhaustive_architecture_claim_allowed"] is False
    assert audit["claims"]["execution_authority_granted"] is False


def test_inferred_confidence_uses_closed_rubric_and_other_truths_use_none(
    repository: Path, tmp_path: Path
) -> None:
    refresh_navigation_inventory(repository, tmp_path / "inventory")
    run = refresh_mapper(tmp_path / "inventory", tmp_path / "mapper")
    connection = _database(run)
    try:
        for table in ("entities", "relations", "observations"):
            assert (
                connection.execute(
                    f"""SELECT COUNT(*) FROM {table}
                        WHERE truth_class='INFERRED' AND confidence<>0.75"""
                ).fetchone()[0]
                == 0
            )
            assert (
                connection.execute(
                    f"""SELECT COUNT(*) FROM {table}
                        WHERE truth_class<>'INFERRED' AND confidence IS NOT NULL"""
                ).fetchone()[0]
                == 0
            )
    finally:
        connection.close()


def test_structure_query_returns_exact_source_and_ancestry(
    repository: Path, tmp_path: Path
) -> None:
    refresh_navigation_inventory(repository, tmp_path / "inventory")
    run = refresh_mapper(tmp_path / "inventory", tmp_path / "mapper")
    result = query_mapper(tmp_path / "mapper", "src/pkg/main.py", maps=("structure",))
    validate_self_hash(result)
    assert result["mapper_run_id"] == run.manifest["run_id"]
    assert result["result_count"] == 1
    artifact = result["results"][0]
    assert artifact["kind"] == "ARTIFACT"
    assert artifact["qualified_name"] == "src/pkg/main.py"
    assert len(artifact["source"]["identity_sha256"]) == 64
    assert (
        artifact["source"]["identity_sha256"]
        != artifact["attributes"]["content_sha256"]
    )
    assert [item["qualified_name"] for item in artifact["ancestors"]] == [
        "src/pkg",
        "src",
        ".",
        ".",
    ]
    assert [item["kind"] for item in artifact["ancestors"]] == [
        "DIRECTORY",
        "DIRECTORY",
        "DIRECTORY",
        "REPOSITORY",
    ]
    assert [
        (item["fact_class"], item["disposition"]) for item in result["coverage"]
    ] == [
        ("FILESYSTEM_CONTAINMENT", "COVERED"),
        ("LOGICAL_CONTAINER", "COVERED"),
        ("LOGICAL_CONTAINER_FORMAT_SUPPORT", "PARTIAL"),
    ]

    project = query_mapper(tmp_path / "mapper", "PYTHON_PROJECT:.", maps=("structure",))
    assert project["result_count"] == 1
    assert project["results"][0]["kind"] == "LOGICAL_CONTAINER"
    assert project["results"][0]["attributes"] == {
        "container_kind": "PYTHON_PROJECT",
        "markers": ["pyproject.toml"],
        "root_path": ".",
    }
    package = query_mapper(
        tmp_path / "mapper", "PYTHON_PACKAGE:src/pkg", maps=("structure",)
    )
    assert package["result_count"] == 1
    assert package["results"][0]["attributes"]["markers"] == ["src/pkg/__init__.py"]


def test_query_truncation_is_exact(repository: Path, tmp_path: Path) -> None:
    refresh_navigation_inventory(repository, tmp_path / "inventory")
    refresh_mapper(tmp_path / "inventory", tmp_path / "mapper")
    exact = query_mapper(tmp_path / "mapper", "main.py", limit=1)
    assert exact["result_count"] == 1
    assert exact["truncated"] is False
    many = query_mapper(tmp_path / "mapper", "src", limit=1)
    assert many["result_count"] == 1
    assert many["truncated"] is True


def test_query_routing_receipt_refuses_query_search_and_view_drift(
    repository: Path, tmp_path: Path
) -> None:
    refresh_navigation_inventory(repository, tmp_path / "inventory")
    refresh_mapper(tmp_path / "inventory", tmp_path / "mapper")
    route = route_query_maps("coverage report")

    with pytest.raises(MapperError, match="different query"):
        query_mapper(
            tmp_path / "mapper",
            "different query",
            maps=route["selected_maps"],
            search_query=route["search_query"],
            routing=route,
        )
    with pytest.raises(MapperError, match="different search query"):
        query_mapper(
            tmp_path / "mapper",
            "coverage report",
            maps=route["selected_maps"],
            search_query="different",
            routing=route,
        )
    with pytest.raises(MapperError, match="different views"):
        query_mapper(
            tmp_path / "mapper",
            "coverage report",
            maps=("inventory",),
            search_query=route["search_query"],
            routing=route,
        )
    tampered = dict(route)
    tampered["fallback"] = "tampered"
    with pytest.raises(MapperError, match="routing receipt is invalid"):
        query_mapper(
            tmp_path / "mapper",
            "coverage report",
            maps=route["selected_maps"],
            search_query=route["search_query"],
            routing=tampered,
        )


def test_same_inventory_is_idempotent_and_changed_inventory_publishes_new_run(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    first = refresh_mapper(inventory_store, mapper_store)
    same = refresh_mapper(inventory_store, mapper_store)
    assert same.manifest["run_id"] == first.manifest["run_id"]

    (repository / "src/pkg/extra.py").write_text("VALUE = 2\n", encoding="utf-8")
    refresh_navigation_inventory(repository, inventory_store)
    second = refresh_mapper(inventory_store, mapper_store)
    assert second.manifest["run_id"] != first.manifest["run_id"]
    assert second.manifest["scan"]["incremental_from"] == first.manifest["run_id"]
    assert first.run_directory.is_dir()
    assert (
        current_mapper_run(mapper_store).manifest["run_id"] == second.manifest["run_id"]
    )


def test_unchanged_python_input_reuses_stable_facts_without_running_producer(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    first = refresh_mapper(inventory_store, mapper_store)
    first_database = _database(first)
    try:
        producer_ids = tuple(
            row[0]
            for row in first_database.execute(
                "SELECT producer_id FROM producer_inputs ORDER BY producer_id"
            )
        )
        first_relations = {
            row[0]
            for row in first_database.execute(
                """SELECT relation_id FROM relations
                   WHERE producer_id IN (?,?,?)""",
                producer_ids,
            )
        }
        first_observations = {
            row[0]
            for row in first_database.execute(
                """SELECT observation_id FROM observations
                   WHERE producer_id IN (?,?,?)""",
                producer_ids,
            )
        }
    finally:
        first_database.close()

    (repository / "docs/guide.md").write_text("# Guide\n\nUpdated.\n", encoding="utf-8")
    refresh_navigation_inventory(repository, inventory_store)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("unchanged compound Python producer was rerun")

    monkeypatch.setattr(
        "modules.operations.archaeology.mapper._build_python_maps", forbidden
    )
    second = refresh_mapper(inventory_store, mapper_store)
    assert second.manifest["scan"]["incremental_scope"] == (
        "compound-python-producer-with-source-fragments"
    )
    assert second.manifest["scan"]["incremental_source_granularity"] == (
        "per-file-extraction-and-source-owned-fact-reuse"
    )
    assert second.manifest["scan"]["python_fragments"] == {
        "total": 3,
        "reused": 3,
        "recomputed": 0,
        "deleted": 0,
    }
    assert second.manifest["scan"]["cross_file_resolution"] == (
        "REUSED_WITH_UNCHANGED_PRODUCER_GROUP"
    )
    assert second.manifest["scan"]["producers_reused"] == 3
    assert second.manifest["scan"]["facts_reused"] > 0
    assert second.manifest["scan"]["facts_recomputed"] == 0

    second_database = _database(second)
    try:
        assert {
            row[0]
            for row in second_database.execute(
                """SELECT relation_id FROM relations
                   WHERE producer_id IN (?,?,?)""",
                producer_ids,
            )
        } == first_relations
        assert {
            row[0]
            for row in second_database.execute(
                """SELECT observation_id FROM observations
                   WHERE producer_id IN (?,?,?)""",
                producer_ids,
            )
        } == first_observations
        assert {
            row[0]
            for row in second_database.execute(
                "SELECT DISTINCT execution FROM producer_inputs"
            )
        } == {"REUSED"}
        assert (
            second_database.execute(
                """SELECT COUNT(*) FROM entities
                   WHERE producer_id IN (?,?,?)
                     AND (first_seen_run_id<>? OR last_seen_run_id<>?)""",
                (
                    *producer_ids,
                    first.manifest["inventory"]["run_id"],
                    second.manifest["inventory"]["run_id"],
                ),
            ).fetchone()[0]
            == 0
        )
    finally:
        second_database.close()
    assert audit_mapper(mapper_store)["status"] == "PASS"


def test_changed_python_source_invalidates_group_and_preserves_entity_history(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repository / "src/pkg/extra.py").write_text(
        "def stable_helper():\n    return 7\n", encoding="utf-8"
    )
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    first = refresh_mapper(inventory_store, mapper_store)
    original = __import__(
        "modules.operations.archaeology.mapper", fromlist=["_build_python_maps"]
    )._build_python_maps
    calls = 0

    def observed(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        "modules.operations.archaeology.mapper._build_python_maps", observed
    )
    (repository / "src/pkg/main.py").write_text(
        "def main():\n    return 2\n", encoding="utf-8"
    )
    refresh_navigation_inventory(repository, inventory_store)
    second = refresh_mapper(inventory_store, mapper_store)
    assert calls == 1
    assert second.manifest["scan"]["producers_partial"] > 0
    assert second.manifest["scan"]["facts_reused"] > 0
    assert second.manifest["scan"]["facts_recomputed"] > 0
    assert second.manifest["scan"]["python_fragments"] == {
        "total": 4,
        "reused": 3,
        "recomputed": 1,
        "deleted": 0,
    }
    assert second.manifest["scan"]["cross_file_resolution"] == (
        "AFFECTED_SOURCES_RECOMPUTED_PUBLIC_SURFACE_STABLE"
    )
    connection = _database(second)
    try:
        assert {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT execution FROM producer_inputs"
            )
        } <= {"PARTIAL", "RECOMPUTED", "REUSED"}
        assert "PARTIAL" in {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT execution FROM producer_inputs"
            )
        }
        module = connection.execute(
            """SELECT first_seen_run_id,last_seen_run_id FROM entities
               WHERE entity_kind='PYTHON_MODULE' AND qualified_name='pkg.main'"""
        ).fetchone()
        assert tuple(module) == (
            first.manifest["inventory"]["run_id"],
            second.manifest["inventory"]["run_id"],
        )
    finally:
        connection.close()

    assert audit_mapper(mapper_store)["status"] == "PASS"
    cold = refresh_mapper(inventory_store, tmp_path / "cold-mapper")
    warm_db = _database(second)
    cold_db = _database(cold)
    try:
        projections = (
            """SELECT entity_id,entity_kind,name,qualified_name,source_id,
                      truth_class,confidence,producer_id,privacy_class,attributes_json
               FROM entities ORDER BY entity_id""",
            """SELECT relation_id,subject_id,predicate,object_id,source_id,
                      truth_class,confidence,producer_id,attributes_json
               FROM relations ORDER BY relation_id""",
            """SELECT observation_id,entity_id,predicate,value_json,source_id,
                      truth_class,confidence,producer_id
               FROM observations ORDER BY observation_id""",
            "SELECT * FROM locations ORDER BY location_id",
            "SELECT * FROM coverage ORDER BY producer_id,map_id,fact_class,scope",
            "SELECT * FROM map_views ORDER BY map_id",
        )
        for sql in projections:
            assert warm_db.execute(sql).fetchall() == cold_db.execute(sql).fetchall()
    finally:
        warm_db.close()
        cold_db.close()


def test_producer_implementation_identity_invalidates_unchanged_sources(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    refresh_mapper(inventory_store, mapper_store)
    (repository / "docs/guide.md").write_text("# Guide v2\n", encoding="utf-8")
    refresh_navigation_inventory(repository, inventory_store)
    monkeypatch.setattr(
        "modules.operations.archaeology.mapper._producer_hash", lambda: "f" * 64
    )
    second = refresh_mapper(inventory_store, mapper_store)
    assert second.manifest["scan"]["producers_recomputed"] == 3
    assert second.manifest["scan"]["facts_recomputed"] > 0
    assert second.manifest["scan"]["python_fragments"] == {
        "total": 3,
        "reused": 3,
        "recomputed": 0,
        "deleted": 0,
    }


def test_python_public_surface_change_falls_back_to_full_projection(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    refresh_mapper(inventory_store, mapper_store)

    (repository / "src/pkg/main.py").write_text(
        "def renamed_main():\n    return 2\n", encoding="utf-8"
    )
    refresh_navigation_inventory(repository, inventory_store)
    second = refresh_mapper(inventory_store, mapper_store)

    assert second.manifest["scan"]["producers_partial"] == 0
    assert second.manifest["scan"]["producers_reused"] == 0
    assert second.manifest["scan"]["facts_reused"] == 0
    assert second.manifest["scan"]["cross_file_resolution"] == (
        "GLOBAL_RECOMPUTED_FROM_ASSEMBLED_FRAGMENTS"
    )
    connection = _database(second)
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM projection_reuse").fetchone()[0]
            == 0
        )
        assert {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT execution FROM producer_inputs"
            )
        } == {"RECOMPUTED"}
    finally:
        connection.close()
    assert audit_mapper(mapper_store)["status"] == "PASS"


def test_changed_python_file_is_the_only_source_reparsed(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import modules.operations.archaeology.python_map as python_map

    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    refresh_mapper(inventory_store, mapper_store)
    original_parse = python_map.ast.parse
    parsed: list[str] = []

    def observed(source, filename="<unknown>", *args, **kwargs):
        parsed.append(filename)
        return original_parse(source, filename=filename, *args, **kwargs)

    monkeypatch.setattr(python_map.ast, "parse", observed)
    (repository / "src/pkg/main.py").write_text(
        "def main():\n    return 3\n", encoding="utf-8"
    )
    refresh_navigation_inventory(repository, inventory_store)
    second = refresh_mapper(inventory_store, mapper_store)

    assert parsed == ["src/pkg/main.py"]
    assert second.manifest["scan"]["python_fragments"]["recomputed"] == 1
    assert (
        audit_mapper(mapper_store)["checks"]["python_fragment_closure"]["status"]
        == "PASS"
    )


def test_deleted_python_fragment_is_removed_without_reparsing_survivors(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import modules.operations.archaeology.python_map as python_map

    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    refresh_mapper(inventory_store, mapper_store)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("deleting one file reparsed an unchanged Python file")

    monkeypatch.setattr(python_map.ast, "parse", forbidden)
    (repository / "src/pkg/main.py").unlink()
    refresh_navigation_inventory(repository, inventory_store)
    second = refresh_mapper(inventory_store, mapper_store)

    assert second.manifest["scan"]["python_fragments"] == {
        "total": 2,
        "reused": 2,
        "recomputed": 0,
        "deleted": 1,
    }
    connection = _database(second)
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM python_fragments WHERE path='src/pkg/main.py'"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM entities WHERE qualified_name='pkg.main'"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()
    assert audit_mapper(mapper_store)["checks"]["python_fragment_closure"] == {
        "status": "PASS",
        "violations": 0,
        "fragments": 2,
        "reused": 2,
        "recomputed": 0,
        "deleted": 1,
        "resolution_scope": "GLOBAL_RECOMPUTED_FROM_ASSEMBLED_FRAGMENTS",
    }


def test_package_context_change_reparses_only_affected_modules(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    refresh_mapper(inventory_store, mapper_store)
    (repository / "src/__init__.py").write_text("", encoding="utf-8")
    refresh_navigation_inventory(repository, inventory_store)
    second = refresh_mapper(inventory_store, mapper_store)

    assert second.manifest["scan"]["python_fragments"] == {
        "total": 4,
        "reused": 1,
        "recomputed": 3,
        "deleted": 0,
    }
    result = query_mapper(mapper_store, "src.pkg.main", maps=("symbols",))
    assert any(item["qualified_name"] == "src.pkg.main" for item in result["results"])


def test_executable_mode_change_invalidates_only_affected_source_fragment(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    refresh_mapper(inventory_store, mapper_store)
    source = repository / "src/pkg/main.py"
    source.chmod(0o755)
    refresh_navigation_inventory(repository, inventory_store)
    second = refresh_mapper(inventory_store, mapper_store)

    assert second.manifest["scan"]["python_fragments"] == {
        "total": 3,
        "reused": 2,
        "recomputed": 1,
        "deleted": 0,
    }
    result = query_mapper(mapper_store, "src/pkg/main.py", maps=("api_events",))
    assert any(
        item["kind"] == "ENTRYPOINT"
        and item["attributes"]["kind"] == "PYTHON_EXECUTABLE_FILE"
        for item in result["results"]
    )


def test_byte_identical_commit_transition_does_not_invalidate_python_facts(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    first = refresh_mapper(inventory_store, mapper_store)
    (repository / "src/pkg/main.py").write_text(
        "def main():\n    return 2\n", encoding="utf-8"
    )
    refresh_navigation_inventory(repository, inventory_store)
    dirty = refresh_mapper(inventory_store, mapper_store)
    assert dirty.manifest["scan"]["producers_recomputed"] >= 1
    assert dirty.manifest["scan"]["facts_recomputed"] > 0
    _git(repository, "add", "src/pkg/main.py")
    _git(repository, "commit", "-qm", "same bytes become committed")
    refresh_navigation_inventory(repository, inventory_store)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Git metadata alone reran the Python producer")

    monkeypatch.setattr(
        "modules.operations.archaeology.mapper._build_python_maps", forbidden
    )
    committed = refresh_mapper(inventory_store, mapper_store)
    assert committed.manifest["scan"]["producers_reused"] == 3
    assert committed.manifest["scan"]["facts_reused"] > 0
    connection = _database(committed)
    try:
        module = connection.execute(
            """SELECT first_seen_run_id,last_seen_run_id FROM entities
               WHERE entity_kind='PYTHON_MODULE' AND qualified_name='pkg.main'"""
        ).fetchone()
        assert tuple(module) == (
            first.manifest["inventory"]["run_id"],
            committed.manifest["inventory"]["run_id"],
        )
    finally:
        connection.close()


def test_failed_refresh_preserves_previous_current(
    repository: Path, tmp_path: Path, monkeypatch
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    first = refresh_mapper(inventory_store, mapper_store)
    (repository / "new.md").write_text("new\n", encoding="utf-8")
    refresh_navigation_inventory(repository, inventory_store)

    def fail(*_args, **_kwargs):
        raise MapperError("injected compiler failure")

    monkeypatch.setattr("modules.operations.archaeology.mapper._build_database", fail)
    with pytest.raises(MapperError, match="injected compiler failure"):
        refresh_mapper(inventory_store, mapper_store)
    assert (
        current_mapper_run(mapper_store).manifest["run_id"] == first.manifest["run_id"]
    )
    assert not list(mapper_store.glob(".staging-*"))


def test_refresh_reuses_only_when_inventory_and_compiler_identity_match(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory)
    first = refresh_mapper(inventory, mapper)
    assert (
        refresh_mapper(inventory, mapper).manifest["run_id"] == first.manifest["run_id"]
    )
    compiler = dict(first.manifest["compiler"])
    compiler["sha256"] = "f" * 64
    monkeypatch.setattr(
        "modules.operations.archaeology.mapper._compiler_identity",
        lambda: compiler,
    )
    second = refresh_mapper(inventory, mapper)
    assert second.manifest["run_id"] != first.manifest["run_id"]
    assert second.manifest["scan"]["incremental_from"] == first.manifest["run_id"]


def test_current_refuses_database_tamper_and_runtime_view_without_input_is_partial(
    repository: Path, tmp_path: Path
) -> None:
    refresh_navigation_inventory(repository, tmp_path / "inventory")
    run = refresh_mapper(tmp_path / "inventory", tmp_path / "mapper")
    runtime = query_mapper(tmp_path / "mapper", "main", maps=("runtime_topology",))
    assert runtime["result_count"] == 0
    assert runtime["coverage"][0]["disposition"] == "PARTIAL"
    assert runtime["coverage"][0]["details"]["map_authority"] is False
    database = run.run_directory / "facts.sqlite3"
    database.write_bytes(database.read_bytes() + b"tamper")
    with pytest.raises(MapperError, match="database hash mismatch"):
        current_mapper_run(tmp_path / "mapper")


def test_store_is_private_external_and_cli_runs(
    repository: Path, tmp_path: Path
) -> None:
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(repository, inventory_store)
    with pytest.raises(MapperError, match="outside"):
        refresh_mapper(inventory_store, repository / "mapper-store")

    root = Path(__file__).resolve().parents[1]
    refreshed = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.operations.scripts.archaeology",
            "mapper-refresh",
            "--inventory-store",
            str(inventory_store),
            "--mapper-store",
            str(mapper_store),
        ],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert json.loads(refreshed.stdout)["entities"] >= 13
    queried = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.operations.scripts.archaeology",
            "mapper-query",
            "main.py",
            "--mapper-store",
            str(mapper_store),
            "--view",
            "structure",
        ],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    result = json.loads(queried.stdout)
    validate_self_hash(result)
    assert result["results"][0]["qualified_name"] == "src/pkg/main.py"
    assert result["routing"]["mode"] == "EXPLICIT"
    assert result["routing"]["selected_maps"] == ["structure"]

    automatic = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.operations.scripts.archaeology",
            "mapper-query",
            "JAA application preparation",
            "--mapper-store",
            str(mapper_store),
        ],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    automatic_result = json.loads(automatic.stdout)
    validate_self_hash(automatic_result)
    assert automatic_result["routing"]["mode"] == "AUTO_DETERMINISTIC"
    assert automatic_result["routing"]["fallback"] == (
        "ALL_REGISTERED_MAPS_NO_INTENT_MATCH"
    )
    assert set(automatic_result["maps"]) == set(SUPPORTED_MAPS)
    audited = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.operations.scripts.archaeology",
            "mapper-audit",
            "--mapper-store",
            str(mapper_store),
        ],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    audit = json.loads(audited.stdout)
    validate_self_hash(audit)
    assert audit["status"] == "PASS"
    assert audit["checks"]["all_map_query_probe"]["maps"] == 22
    assert stat.S_IMODE(mapper_store.stat().st_mode) == 0o700
    assert stat.S_IMODE((mapper_store / "CURRENT.json").stat().st_mode) == 0o600
    assert (
        stat.S_IMODE(
            (current_mapper_run(mapper_store).run_directory / "facts.sqlite3")
            .stat()
            .st_mode
        )
        == 0o600
    )
    assert not (repository / "mapper-store").exists()
    assert os.getuid() == mapper_store.stat().st_uid
