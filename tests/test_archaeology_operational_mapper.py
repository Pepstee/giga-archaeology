from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.mapper import query_mapper, refresh_mapper
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)
from modules.operations.archaeology.operational_map import (
    OPERATIONAL_POLICY_SHA256,
    build_asset_role,
    parse_sql_literal,
    safe_build_declarations,
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
def operational_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "operational-map"\nversion = "1"\n', encoding="utf-8"
    )
    (root / "app.py").write_text(
        """import sqlite3

def run():
    database = sqlite3.connect("state.sqlite3")
    database.execute("CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY)")
    database.execute("INSERT INTO jobs (id) VALUES (1)")
    database.execute("SELECT jobs.id FROM jobs JOIN employers ON employers.id = jobs.id")
    dynamic = "DELETE FROM jobs"
    database.execute(dynamic)

def unknown_scope(cursor):
    cursor.execute("DELETE FROM audit_log")
""",
        encoding="utf-8",
    )
    (root / "BUNDLE.json").write_text(
        '{"schema":"bundle.v1","status":"BUILT","product_commit":"'
        + "a" * 40
        + '","secret_token":"must-not-project"}\n',
        encoding="utf-8",
    )
    (root / "deploy/releases").mkdir(parents=True)
    (root / "deploy/releases/current.json").write_text(
        '{"status":"VERIFIED_LOCAL_SELECTION_CANDIDATE","selected":false,'
        '"artifact_sha256":"' + "b" * 64 + '"}\n',
        encoding="utf-8",
    )
    (root / "deploy/evidence/canary").mkdir(parents=True)
    (root / "deploy/evidence/canary/BUNDLE.json").write_text(
        '{"status":"PRIVATE_CANARY"}\n', encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _compile(root: Path, tmp_path: Path):
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    return mapper, refresh_mapper(inventory, mapper)


def test_closed_sql_and_build_classifiers_refuse_ambiguous_input() -> None:
    assert parse_sql_literal("SELECT * FROM jobs") == {
        "grammar": "sqlite-literal-single-statement.v1",
        "operation": "READ",
        "statement_sha256": "96ef8ea48e1a054a1dc024d0c2e1d326703628ddf4a6fa7196a45bd539267fc0",
        "tables": ["jobs"],
    }
    assert parse_sql_literal("SELECT * FROM jobs; DELETE FROM jobs") is None
    assert parse_sql_literal("SELECT " + "x" * 1_000_000) is None
    assert build_asset_role("deploy/releases/current.json") == "RELEASE_DECLARATION"
    assert build_asset_role("notes.json") is None
    assert (
        safe_build_declarations("BUNDLE.json", b'{"status":"PASS","status":"FAIL"}')
        == []
    )
    assert len(OPERATIONAL_POLICY_SHA256) == 64


def test_m05_literal_database_lineage_is_source_bound_and_partial(
    operational_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(operational_repository, tmp_path)
    counts = run.manifest["counts"]
    assert counts["python_declared_databases"] == 2
    assert counts["python_declared_data_objects"] == 3
    assert counts["python_literal_sql_operations"] == 5
    result = query_mapper(mapper, "jobs", maps=("database_lineage",), fact_limit=50)
    table = next(item for item in result["results"] if item["kind"] == "DATA_OBJECT")
    assert table["name"] == "jobs"
    predicates = {item["predicate"] for item in table["facts"]["relations"]}
    assert {
        "DECLARES_DATA_OBJECT",
        "DECLARES_SCHEMA_OBJECT",
        "MAY_READ_DATA_OBJECT",
        "MAY_WRITE_DATA_OBJECT",
    } <= predicates
    assert all(
        item["attributes"].get("runtime_observed") is False
        for item in table["facts"]["relations"]
    )
    coverage = result["coverage"][0]
    assert coverage["disposition"] == "PARTIAL"
    assert coverage["details"]["row_content_read"] is False
    unknown = query_mapper(
        mapper, "audit_log", maps=("database_lineage",), fact_limit=50
    )["results"][0]
    assert unknown["truth_class"] == "INFERRED"
    assert unknown["attributes"]["database_scope"] == "UNKNOWN"
    assert any(
        item["predicate"] == "POSSIBLY_CONTAINS_DATA_OBJECT"
        and item["truth_class"] == "INFERRED"
        for item in unknown["facts"]["relations"]
    )


def test_m05_build_projection_is_safe_and_never_claims_deployment(
    operational_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(operational_repository, tmp_path)
    assert run.manifest["counts"]["build_assets"] == 3
    result = query_mapper(mapper, "BUNDLE.json", maps=("build_deployment",))
    bundle = next(item for item in result["results"] if item["kind"] == "BUILD_ASSET")
    assert bundle["source"]["path"] == "BUNDLE.json"
    assert bundle["attributes"]["deployment_status"] == "NOT_EVALUATED"
    assert bundle["attributes"]["runtime_observed"] is False
    declarations = bundle["attributes"]["safe_declarations"]
    assert {item["key_path"] for item in declarations} == {
        "product_commit",
        "schema",
        "status",
    }
    assert "must-not-project" not in str(bundle)
    assert not any(
        item["source"]["path"].startswith("deploy/evidence/")
        for item in result["results"]
    )
    coverage = result["coverage"][0]
    assert coverage["details"]["deployment_status_evaluated"] is False
    assert coverage["details"]["private_evidence_read"] is False
