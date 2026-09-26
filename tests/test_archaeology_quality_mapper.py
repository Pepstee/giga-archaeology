from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.evidence import canonical_bytes, seal_document
from modules.operations.archaeology.mapper import query_mapper, refresh_mapper
from modules.operations.archaeology.map_catalog import route_query_maps
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)
from modules.operations.archaeology.quality_map import (
    QUALITY_POLICY_SHA256,
    command_repository_path_candidates,
    is_python_test_path,
    parse_coverage_json,
    parse_receipt_quality_claims,
    quality_asset_role,
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
def quality_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "app.py").write_text(
        "def helper(value: int) -> int:\n"
        "    return value + 1\n\n"
        "def coverage() -> str:\n"
        "    return 'symbol named coverage'\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir()
    (root / "tests/test_app.py").write_text(
        "from app import helper\n\ndef test_helper():\n    assert helper(1) == 2\n",
        encoding="utf-8",
    )
    (root / "coverage.json").write_text(
        json.dumps(
            {
                "meta": {"version": "7.0", "branch_coverage": False},
                "files": {
                    "app.py": {
                        "summary": {
                            "covered_lines": 2,
                            "missing_lines": 0,
                            "num_statements": 2,
                            "percent_covered": 100.0,
                        },
                        "executed_lines": [1, 2],
                    }
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
    (root / "deploy/evidence/canary").mkdir(parents=True)
    (root / "deploy/evidence/canary/private.sarif").write_text(
        '{"runs":[{"results":[{"message":{"text":"private"}}]}]}\n',
        encoding="utf-8",
    )
    (root / "receipts/M50").mkdir(parents=True)
    receipt = seal_document(
        {
            "schema": "fixture.quality-receipt.v1",
            "status": "PASS",
            "proofs": [
                {
                    "id": "focused-quality",
                    "command": [
                        "python3",
                        "-m",
                        "pytest",
                        "-q",
                        "tests/test_app.py::test_helper",
                    ],
                    "result": "2 passed",
                    "status": "PASS",
                },
                {
                    "id": "ruff-check",
                    "command": ["ruff", "check", "."],
                    "result": "F401 reported by receipt",
                    "status": "FAIL",
                },
                {
                    "id": "unsupported-command-shape",
                    "command": "pytest -q",
                    "result": "must not project",
                    "status": "PASS",
                },
            ],
        }
    )
    (root / "receipts/M50/quality.json").write_bytes(canonical_bytes(receipt))
    (root / "receipts/M50/invalid-quality.json").write_bytes(
        canonical_bytes(
            {
                "schema": "fixture.quality-receipt.v1",
                "status": "PASS",
                "proofs": [
                    {
                        "id": "must-not-project",
                        "command": ["python3", "-m", "pytest", "-q"],
                        "result": "self hash is invalid",
                        "status": "PASS",
                    }
                ],
                "receipt_sha256": "0" * 64,
            }
        )
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _compile(root: Path, tmp_path: Path):
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    return mapper, refresh_mapper(inventory, mapper)


def test_quality_classifiers_are_closed_and_bounded() -> None:
    assert is_python_test_path("tests/test_app.py")
    assert is_python_test_path("pkg/widget_test.py")
    assert not is_python_test_path("pkg/contest.py")
    assert quality_asset_role("coverage.json") == "COVERAGE_REPORT"
    assert quality_asset_role("notes.json") is None
    assert parse_coverage_json(b'{"files":{},"files":{}}') is None
    assert parse_coverage_json(b'{"files":{"app.py":{"summary":{}}}}') is None
    parsed = parse_receipt_quality_claims(
        {
            "proofs": [
                {
                    "id": "pytest",
                    "command": ["python3", "-m", "pytest", "-q"],
                    "result": "1 passed",
                    "status": "PASS",
                },
                {
                    "id": "pytest",
                    "command": ["python3", "-m", "pytest", "-q"],
                    "result": "duplicate id",
                    "status": "PASS",
                },
            ]
        }
    )
    assert len(parsed["claims"]) == 1
    assert parsed["claims"][0]["check_family"] == "PYTEST"
    assert parsed["claims"][0]["execution_independently_verified"] is False
    assert parsed["rejected_items"] == 1
    assert command_repository_path_candidates(
        [
            "python3",
            "-m",
            "pytest",
            "-q",
            "tests/test_app.py::test_helper",
            "/tmp/outside.py",
            "../outside.py",
            "tests\\wrong.py",
            ".",
        ]
    ) == [
        {
            "argument_index": 4,
            "path": "tests/test_app.py",
            "selector": "test_helper",
        }
    ]
    assert len(QUALITY_POLICY_SHA256) == 64


def test_m06_test_candidates_link_static_targets_without_claiming_execution(
    quality_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(quality_repository, tmp_path)
    assert run.manifest["counts"]["python_test_candidates"] == 1
    assert run.manifest["counts"]["static_test_targets"] >= 2
    result = query_mapper(
        mapper, "test_helper", maps=("tests_coverage",), fact_limit=50
    )
    candidate = next(
        item for item in result["results"] if item["kind"] == "TEST_CASE_CANDIDATE"
    )
    assert candidate["truth_class"] == "INFERRED"
    assert candidate["attributes"]["execution_status"] == "NOT_OBSERVED"
    targets = {
        item["other"]["qualified_name"]
        for item in candidate["facts"]["relations"]
        if item["predicate"] == "STATICALLY_CALLS_TEST_TARGET"
    }
    assert "app.helper" in targets


def test_m06_coverage_and_quality_artifacts_preserve_unknown_freshness(
    quality_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(quality_repository, tmp_path)
    assert run.manifest["counts"]["coverage_files"] == 1
    assert run.manifest["counts"]["coverage_source_links"] == 1
    coverage = query_mapper(mapper, "app.py", maps=("tests_coverage",), fact_limit=50)
    record = next(
        item for item in coverage["results"] if item["kind"] == "COVERAGE_FILE"
    )
    assert record["attributes"]["coverage_summary"]["percent_covered"] == 100.0
    assert record["attributes"]["freshness"] == "UNKNOWN"
    assert (
        record["attributes"]["source_tree_binding"] == "ABSENT_UNLESS_SEPARATELY_PROVEN"
    )
    quality = query_mapper(mapper, "ruff.toml", maps=("quality_findings",))
    artifact = quality["results"][0]
    assert artifact["attributes"]["execution_status"] == "NOT_EVALUATED"
    assert artifact["attributes"]["source_tree_binding"] == "UNKNOWN"
    assert "private" not in str(quality)
    assert quality["coverage"][0]["details"]["finding_content_parsed"] is False


def test_m50_self_hashed_receipt_proofs_are_navigable_claims_not_execution_truth(
    quality_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(quality_repository, tmp_path)
    assert run.manifest["counts"]["quality_check_claims"] == 2
    assert run.manifest["counts"]["quality_check_claims_rejected"] == 1
    passed = query_mapper(
        mapper, "focused-quality", maps=("quality_findings",), fact_limit=50
    )
    claim = next(
        item for item in passed["results"] if item["kind"] == "QUALITY_CHECK_CLAIM"
    )
    assert claim["truth_class"] == "OBSERVED"
    assert claim["attributes"]["reported_status"] == "PASS"
    assert claim["attributes"]["reported_result"] == "2 passed"
    assert claim["attributes"]["check_family"] == "PYTEST"
    assert claim["attributes"]["execution_independently_verified"] is False
    assert claim["attributes"]["source_receipt_self_hash_state"] == "VALID"
    modules = query_mapper(mapper, "tests/test_app.py", maps=("symbols",), limit=100)[
        "results"
    ]
    module = next(item for item in modules if item["kind"] == "PYTHON_MODULE")
    assert claim["attributes"]["current_inventory_path_refs"] == [
        {
            "argument_index": 4,
            "content_sha256": module["attributes"]["content_sha256"],
            "execution_source_binding": False,
            "match_semantics": "LEXICAL_CURRENT_INVENTORY_PATH",
            "path": "tests/test_app.py",
            "selector": "test_helper",
        }
    ]
    module_link = next(
        fact
        for fact in claim["facts"]["relations"]
        if fact["predicate"] == "RECEIPT_COMMAND_LEXICALLY_REFERENCES_CURRENT_MODULE"
    )
    assert module_link["other"]["qualified_name"] == "tests.test_app"
    assert module_link["attributes"]["receipt_execution_cwd_proven"] is False
    assert module_link["attributes"]["receipt_execution_source_binding"] is False
    assert any(
        fact["predicate"] == "RECEIPT_REPORTS_QUALITY_STATUS"
        and fact["truth_class"] == "OBSERVED"
        and fact["value"]["execution_independently_verified"] is False
        for fact in claim["facts"]["observations"]
    )

    failed = query_mapper(
        mapper, "ruff-check", maps=("quality_findings",), fact_limit=50
    )
    failure = next(
        item for item in failed["results"] if item["kind"] == "QUALITY_CHECK_CLAIM"
    )
    assert failure["attributes"]["reported_status"] == "FAIL"
    assert failure["attributes"]["check_family"] == "RUFF_CHECK"
    refused = query_mapper(
        mapper, "must-not-project", maps=("quality_findings",), fact_limit=50
    )
    assert refused["results"] == []


def test_auto_query_ranks_primary_coverage_entities_before_dependency_symbols(
    quality_repository: Path, tmp_path: Path
) -> None:
    mapper, _run = _compile(quality_repository, tmp_path)
    route = route_query_maps("coverage report")
    result = query_mapper(
        mapper,
        "coverage report",
        maps=route["selected_maps"],
        search_query=route["search_query"],
        routing=route,
        limit=20,
    )
    assert result["ranking_policy"] == {
        "algorithm": "giga.map-aware-query-order.v1",
        "map_catalog_receipt_sha256": route["map_catalog_receipt_sha256"],
        "primary_maps": ["tests_coverage", "quality_findings"],
        "dependency_only_matches_rank_after_primary_maps": True,
        "lexical_match_breaks_ties_within_map_fit": True,
        "derived_not_fact": True,
    }
    primary = [
        item for item in result["results"] if item["ranking"]["primary_map_match"]
    ]
    dependency = [
        item for item in result["results"] if not item["ranking"]["primary_map_match"]
    ]
    assert primary
    assert primary[0]["kind"] == "COVERAGE_FILE"
    assert all(
        item["kind"] in {"COVERAGE_FILE", "QUALITY_ARTIFACT"} for item in primary
    )
    assert any(
        item["kind"] == "PYTHON_SYMBOL" and item["name"] == "coverage"
        for item in dependency
    )
    assert result["results"] == primary + dependency
