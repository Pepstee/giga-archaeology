from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.mapper import (
    current_mapper_run,
    query_mapper,
    refresh_mapper,
)
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


@pytest.fixture()
def python_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "pyproject.toml").write_text(
        """[project]
name = "mapped-python"
version = "1"
[project.scripts]
fixture = "pkg.cli:main"
""",
        encoding="utf-8",
    )
    (root / "pkg").mkdir()
    (root / "pkg/__init__.py").write_text("", encoding="utf-8")
    (root / "pkg/base.py").write_text(
        """class Base:
    pass

def helper(value: str) -> int:
    return len(value)
""",
        encoding="utf-8",
    )
    (root / "pkg/cli.py").write_text(
        """import argparse
import pkg.base as base_module
from .base import Base

class Child(Base):
    value: int = 1

    def run(self, item: str) -> int:
        return base_module.helper(item)

def main() -> int:
    return 0

def build_parser():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers()
    command = commands.add_parser("run")
    command.add_argument("--name")
    command.set_defaults(func=main)
    return parser

if __name__ == "__main__":
    raise SystemExit(main())
""",
        encoding="utf-8",
    )
    (root / "pkg/never_import.py").write_text(
        'raise RuntimeError("mapper imported target code")\n', encoding="utf-8"
    )
    (root / "memory").mkdir()
    (root / "memory/private.py").write_text(
        "def secret_symbol():\n    return 'private'\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _compile(root: Path, tmp_path: Path):
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory_store)
    run = refresh_mapper(inventory_store, mapper_store)
    return inventory_store, mapper_store, run


def _one(result: dict, kind: str, qualified_name: str) -> dict:
    matches = [
        item
        for item in result["results"]
        if item["kind"] == kind and item["qualified_name"] == qualified_name
    ]
    assert len(matches) == 1, result["results"]
    return matches[0]


def test_m02_definitions_references_imports_types_and_entrypoints(
    python_repository: Path, tmp_path: Path
) -> None:
    inventory, mapper, run = _compile(python_repository, tmp_path)
    assert run.manifest["maps"] == {
        "available": [
            "inventory",
            "structure",
            "symbols",
            "dependencies",
            "types",
            "api_events",
            "calls",
            "control_flow",
            "data_flow_taint",
            "security_capabilities",
            "database_lineage",
            "build_deployment",
            "tests_coverage",
            "quality_findings",
            "duplicates_similarity",
            "reachability",
            "git_lineage",
            "ownership_canonicality",
            "requirements_decisions",
            "evidence_claims",
            "runtime_topology",
            "semantic_graphify",
        ],
        "inventory": "AVAILABLE",
        "structure": "AVAILABLE_PARTIAL",
        "logical_packages": "AVAILABLE_SUPPORTED_MARKERS",
        "symbols": "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_PARTIAL",
        "dependencies": "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_PARTIAL",
        "types": "AVAILABLE_PYTHON_PARTIAL",
        "api_events": "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_ENTRYPOINT_PARTIAL",
        "calls": "AVAILABLE_PYTHON_BASH_JAVASCRIPT_TYPESCRIPT_STATIC_PARTIAL",
        "control_flow": "AVAILABLE_PYTHON_STRUCTURED_PARTIAL",
        "data_flow_taint": "AVAILABLE_PYTHON_STATIC_MAY_FLOW_PARTIAL",
        "security_capabilities": "AVAILABLE_PYTHON_EFFECT_SURFACE_PARTIAL",
        "database_lineage": "AVAILABLE_PYTHON_LITERAL_SQL_PARTIAL",
        "build_deployment": "AVAILABLE_SAFE_DECLARATION_PARTIAL",
        "tests_coverage": "AVAILABLE_STATIC_TEST_AND_COVERAGE_ARTIFACT_PARTIAL",
        "quality_findings": "AVAILABLE_ARTIFACT_AND_SELF_HASHED_RECEIPT_CLAIM_PARTIAL",
        "duplicates_similarity": "AVAILABLE_EXACT_AND_PYTHON_STRUCTURE_PARTIAL",
        "reachability": "AVAILABLE_STATIC_WITH_USAGE_COUNTEREVIDENCE_PARTIAL",
        "git_lineage": "AVAILABLE_SEARCHABLE_LINEAGE_SUMMARY_AND_EXACT_HISTORY_FACTS_PARTIAL",
        "ownership_canonicality": "AVAILABLE_PATH_ROLE_OWNER_CONTRACT_AND_EXACT_VARIANTS_PARTIAL",
        "requirements_decisions": "AVAILABLE_STRICT_DOCUMENT_HEADING_MARKDOWN_JSON_PATH_AND_EXPLICIT_ID_PARTIAL",
        "evidence_claims": "AVAILABLE_SELF_HASH_AND_EXACT_BINDING_PARTIAL",
        "runtime_topology": "AVAILABLE_EXTERNAL_GATE_STATUS_PARTIAL",
        "semantic_graphify": "AVAILABLE_FEDERATED_LOCAL_GRAPHIFY_PARTIAL",
    }
    counts = run.manifest["counts"]
    assert counts["python_files"] == 4
    assert counts["python_parse_failures"] == 0
    assert counts["python_modules"] == 4
    assert counts["python_symbols"] > 8
    assert counts["python_imports"] == 3
    assert counts["python_imports_unresolved_or_external"] == 1
    assert counts["python_references_resolved"] > 0
    assert counts["python_entrypoints"] >= 5

    child_result = query_mapper(mapper, "pkg.cli.Child", maps=("symbols", "types"))
    child = _one(child_result, "PYTHON_SYMBOL", "pkg.cli.Child")
    assert child["confidence"] is None
    assert {item["parent_kind"] for item in child["derivations"]} == {"SOURCE"}
    definition = [
        item
        for item in child["facts"]["observations"]
        if item["predicate"] == "PYTHON_DEFINITION"
    ]
    assert definition[0]["source"]["path"] == "pkg/cli.py"
    assert definition[0]["source"]["line_start"] == 5
    assert {item["parent_kind"] for item in definition[0]["derivations"]} == {
        "SOURCE",
        "SUBJECT_ENTITY",
    }
    reachability = [
        item
        for item in child["facts"]["observations"]
        if item["predicate"] == "STATIC_REACHABILITY"
    ]
    assert len(reachability) == 1
    assert reachability[0]["truth_class"] == "INFERRED"
    assert reachability[0]["confidence"] == 0.75
    inheritance = [
        item
        for item in child["facts"]["relations"]
        if item["predicate"] == "INHERITS" and item["direction"] == "OUTGOING"
    ]
    assert inheritance[0]["other"]["qualified_name"] == "pkg.base.Base"
    assert {item["parent_kind"] for item in inheritance[0]["derivations"]} == {
        "SOURCE",
        "SUBJECT_ENTITY",
        "OBJECT_ENTITY",
    }

    base_result = query_mapper(mapper, "pkg.base.Base", maps=("symbols", "types"))
    base = _one(base_result, "PYTHON_SYMBOL", "pkg.base.Base")
    assert any(
        item["predicate"] == "PYTHON_REFERENCE"
        and item["role"] == "TARGETED"
        and item["value"]["resolution"] == "EXACT_IMPORT"
        for item in base["facts"]["observations"]
    )

    module_result = query_mapper(mapper, "pkg.cli", maps=("dependencies",))
    module = _one(module_result, "PYTHON_MODULE", "pkg.cli")
    imported = {
        item["other"]["qualified_name"]
        for item in module["facts"]["relations"]
        if item["predicate"] == "IMPORTS" and item["direction"] == "OUTGOING"
    }
    assert imported == {"pkg.base"}
    unresolved = [
        item
        for item in module["facts"]["observations"]
        if item["predicate"] == "PYTHON_IMPORT"
        and item["value"]["resolution"] == "UNRESOLVED_OR_EXTERNAL"
    ]
    assert [item["value"]["module"] for item in unresolved] == ["argparse"]

    endpoint_result = query_mapper(mapper, "fixture", maps=("api_events",))
    endpoint = _one(endpoint_result, "ENTRYPOINT", "PYTHON_PROJECT_SCRIPT:fixture")
    assert endpoint["source"]["path"] == "pyproject.toml"
    assert any(
        item["predicate"] == "HANDLED_BY"
        and item["other"]["qualified_name"] == "pkg.cli.main"
        for item in endpoint["facts"]["relations"]
    )
    second_mapper = tmp_path / "second-mapper"
    refresh_mapper(inventory, second_mapper)
    repeated = _one(
        query_mapper(second_mapper, "pkg.cli.Child", maps=("symbols",)),
        "PYTHON_SYMBOL",
        "pkg.cli.Child",
    )
    assert repeated["entity_id"] == child["entity_id"]


def test_m02_parse_failure_and_sensitive_exclusion_are_honest(
    python_repository: Path, tmp_path: Path
) -> None:
    (python_repository / "pkg/broken.py").write_text("def broken(:\n", encoding="utf-8")
    inventory_store, mapper, run = _compile(python_repository, tmp_path)
    assert run.manifest["counts"]["python_parse_failures"] == 1
    result = query_mapper(mapper, "secret_symbol", maps=("symbols",))
    assert result["result_count"] == 0
    coverage = {item["map_id"]: item for item in result["coverage"]}
    assert coverage["symbols"]["disposition"] == "PARTIAL"
    assert coverage["symbols"]["details"]["failures"][0]["path"] == "pkg/broken.py"
    assert coverage["symbols"]["scope"] == "semantic-eligible-python"

    previous = current_mapper_run(mapper)
    (python_repository / "pkg/cli.py").write_text(
        "def changed():\n    pass\n", encoding="utf-8"
    )
    drifted = refresh_mapper(inventory_store, tmp_path / "different-mapper")
    assert drifted.manifest["status"] == "PARTIAL"
    assert drifted.manifest["counts"]["python_parse_failures"] == 1
    drift_result = query_mapper(
        tmp_path / "different-mapper", "pkg.cli", maps=("symbols",)
    )
    drift_coverage = {item["map_id"]: item for item in drift_result["coverage"]}
    failure = next(
        item
        for item in drift_coverage["symbols"]["details"]["failures"]
        if item["status"] == "FAILED_SOURCE_SNAPSHOT"
    )
    assert failure["path"] == "pkg/cli.py"
    assert failure["status"] == "FAILED_SOURCE_SNAPSHOT"
    assert failure["error_class"] == "PythonMapError"
    assert len(failure["error_sha256"]) == 64
    assert set(failure["maps"]) >= {"symbols", "dependencies", "calls"}
    assert current_mapper_run(mapper).manifest["run_id"] == previous.manifest["run_id"]


def test_m02_fact_store_has_exact_locations_and_no_target_import(
    python_repository: Path, tmp_path: Path
) -> None:
    _inventory, _mapper, run = _compile(python_repository, tmp_path)
    connection = sqlite3.connect(run.run_directory / "facts.sqlite3")
    try:
        definitions = connection.execute(
            "SELECT count(*) FROM observations WHERE predicate='PYTHON_DEFINITION'"
        ).fetchone()[0]
        locations = connection.execute("SELECT count(*) FROM locations").fetchone()[0]
        dangling = connection.execute(
            """SELECT count(*) FROM observations o
               LEFT JOIN locations l ON l.location_id=o.observation_id
               WHERE o.predicate IN ('PYTHON_DEFINITION','PYTHON_REFERENCE','PYTHON_IMPORT')
                 AND l.location_id IS NULL"""
        ).fetchone()[0]
        producer = connection.execute(
            "SELECT configuration_json FROM producers WHERE producer_id='producer:python-map-extractor:v1'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert definitions > 0
    assert locations >= definitions
    assert dangling == 0
    assert json.loads(producer)["imports_target_code"] is False


def test_m02_project_manifest_failure_only_degrades_api_coverage(
    python_repository: Path, tmp_path: Path
) -> None:
    (python_repository / "pyproject.toml").write_text("[project\n", encoding="utf-8")
    _inventory, mapper, run = _compile(python_repository, tmp_path)
    assert run.manifest["counts"]["python_parse_failures"] == 0
    assert run.manifest["counts"]["python_project_manifest_failures"] == 1
    api = query_mapper(mapper, "pkg.cli", maps=("api_events",))
    symbols = query_mapper(mapper, "pkg.cli", maps=("symbols",))
    python_api = next(
        item
        for item in api["coverage"]
        if item["fact_class"] == "PYTHON_CLI_ENTRYPOINT"
    )
    python_symbols = next(
        item
        for item in symbols["coverage"]
        if item["fact_class"] == "PYTHON_SYMBOL_AND_REFERENCE"
    )
    assert python_api["disposition"] == "PARTIAL"
    assert python_api["details"]["failures"][0]["path"] == "pyproject.toml"
    assert python_symbols["disposition"] == "COVERED"
    assert python_symbols["details"]["failures"] == []
