from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from modules.operations.archaeology.dossier import (
    DossierError,
    build_context_projection,
    build_dossier,
    lexical_token_count,
)
from modules.operations.archaeology.evidence import validate_self_hash
from modules.operations.archaeology.mapper import refresh_mapper
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


@pytest.fixture()
def dossier_store(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "src/jaa").mkdir(parents=True)
    (root / "src/jaa/compiler.py").write_text(
        "def compile_documents():\n    return 'ready'\n", encoding="utf-8"
    )
    (root / "src/jaa/__pycache__").mkdir()
    (root / "src/jaa/__pycache__/compiler.cpython-314.pyc").write_bytes(
        b"generated compiler cache"
    )
    source = (
        "from .compiler import compile_documents\n\n"
        "def prepare_application():\n"
        "    return compile_documents()\n"
    )
    (root / "src/jaa/application_preparation.py").write_text(source, encoding="utf-8")
    (root / ".codex-tmp-copy/internal/jaa").mkdir(parents=True)
    (root / ".codex-tmp-copy/internal/jaa/application_preparation.py").write_text(
        source, encoding="utf-8"
    )
    (root / "archive/jaa").mkdir(parents=True)
    (root / "archive/jaa/application_preparation.py").write_text(
        source, encoding="utf-8"
    )
    (root / "tests").mkdir()
    (root / "tests/test_jaa_application_preparation.py").write_text(
        "def test_prepare_application():\n    assert True\n", encoding="utf-8"
    )
    (root / "work_orders").mkdir()
    (root / "work_orders/WO-JAA-APPLICATION-PREPARATION.json").write_text(
        json.dumps(
            {
                "schema": "fixture.work-order.v1",
                "work_order_id": "WO-JAA-APPLICATION-PREPARATION",
                "status": "PASS",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "receipts/WO-JAA-APPLICATION-PREPARATION").mkdir(parents=True)
    (root / "receipts/WO-JAA-APPLICATION-PREPARATION/attestation.json").write_text(
        json.dumps(
            {
                "schema": "fixture.attestation.v1",
                "status": "PASS",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    refresh_mapper(inventory, mapper)
    return mapper


def test_implementation_dossier_locates_code_copies_tests_and_evidence(
    dossier_store: Path,
) -> None:
    dossier = build_dossier(
        dossier_store,
        "implementation",
        ("JAA", "application_preparation", "APPLICATION-PREPARATION"),
        limit_per_term=100,
        overall_limit=500,
        include_semantic=False,
    )
    validate_self_hash(dossier)
    paths = {item["path"] for item in dossier["consulted_sources"]}
    assert "src/jaa/application_preparation.py" in paths
    assert ".codex-tmp-copy/internal/jaa/application_preparation.py" in paths
    assert "archive/jaa/application_preparation.py" in paths
    assert "tests/test_jaa_application_preparation.py" in paths
    assert "work_orders/WO-JAA-APPLICATION-PREPARATION.json" in paths

    by_path = {item["path"]: item for item in dossier["consulted_sources"]}
    assert (
        by_path["src/jaa/application_preparation.py"]["ownership"]["role"]
        == "CANONICAL_SOURCE_CANDIDATE"
    )
    assert (
        by_path[".codex-tmp-copy/internal/jaa/application_preparation.py"][
            "location_class"
        ]
        == "TEMPORARY_WORKING_COPY"
    )
    assert (
        by_path["archive/jaa/application_preparation.py"]["ownership"]["role"]
        == "HISTORICAL_OR_ARCHIVED_COPY"
    )
    assert (
        by_path["archive/jaa/application_preparation.py"]["location_class"]
        == "HISTORY_OR_EVIDENCE_PATH"
    )
    assert (
        by_path["work_orders/WO-JAA-APPLICATION-PREPARATION.json"]["location_class"]
        == "HISTORY_OR_EVIDENCE_PATH"
    )
    assert dossier["claims"]["canonical_owner_asserted"] is False
    assert dossier["claims"]["no_feature_loss_allowed"] is False
    assert dossier["claims"]["complete_inventory_allowed"] is False
    assert dossier["claims"]["current_architecture_allowed"] is False
    assert dossier["authority_granted"] is False
    assert dossier["query_receipts"]
    assert len(dossier["query_receipts"]) == 3
    assert dossier["query_receipts"][0]["map_ids"] == dossier["options"]["maps"]


def test_model_facing_dossier_omits_dependency_cache_artifacts(
    dossier_store: Path,
) -> None:
    dossier = build_dossier(
        dossier_store,
        "architecture",
        ("compiler",),
        limit_per_term=100,
        overall_limit=500,
        include_semantic=False,
    )
    paths = {item["path"] for item in dossier["consulted_sources"]}
    assert "src/jaa/compiler.py" in paths
    assert "src/jaa/__pycache__/compiler.cpython-314.pyc" not in paths
    assert dossier["omissions"]["navigation_policy_count"] >= 1


def test_dossier_terms_add_matching_primary_maps_without_all_map_fallback(
    dossier_store: Path,
) -> None:
    dossier = build_dossier(
        dossier_store,
        "architecture",
        ("attestation", "eldritch-fuchsia"),
        limit_per_term=100,
        overall_limit=500,
        include_semantic=False,
    )
    assert "evidence_claims" not in dossier["options"]["base_maps"]
    assert dossier["options"]["maps_added_by_term_routing"] == ["evidence_claims"]
    assert "evidence_claims" in dossier["options"]["maps"]
    assert dossier["routing_policy"] == {
        "algorithm": "giga.dossier-term-route-union.v1",
        "fallback_routes_expand_dossier": False,
        "matched_primary_maps_expand_dossier": True,
        "fixed_dossier_maps_preserved": True,
        "derived_not_fact": True,
    }
    assert dossier["term_routes"][0]["primary_maps"] == ["evidence_claims"]
    assert (
        dossier["term_routes"][1]["fallback"] == "ALL_REGISTERED_MAPS_NO_INTENT_MATCH"
    )
    assert any(
        item["kind"] == "EVIDENCE_DOCUMENT"
        and item["qualified_name"]
        == "receipts/WO-JAA-APPLICATION-PREPARATION/attestation.json"
        for item in dossier["results"]
    )
    evidence = next(
        item
        for item in dossier["results"]
        if item["kind"] == "EVIDENCE_DOCUMENT"
        and item["qualified_name"]
        == "receipts/WO-JAA-APPLICATION-PREPARATION/attestation.json"
    )
    assert evidence["primary_map_matched_terms"] == ["attestation"]

    context = build_context_projection(
        dossier_store,
        "architecture",
        ("attestation",),
        token_budget=128,
        include_semantic=False,
    )
    assert context["entries"][0]["kind"] == "EVIDENCE_DOCUMENT"
    assert context["entries"][0]["ranking"]["primary_map_term_matches"] == 1
    assert context["ranking"]["algorithm"] == (
        "giga.personalized-file-rank.v3-precision-deduplicated-map-aware"
    )
    assert context["term_routes"][0]["primary_maps"] == ["evidence_claims"]
    assert context["routing_policy"] == dossier["routing_policy"]


def test_dossier_reports_partial_coverage_and_budget_omissions(
    dossier_store: Path,
) -> None:
    dossier = build_dossier(
        dossier_store,
        "implementation",
        ("application",),
        limit_per_term=2,
        overall_limit=1,
    )
    assert dossier["completeness"] == "PARTIAL"
    assert dossier["omissions"]["results_omitted_by_overall_budget"] > 0
    assert dossier["claims"]["complete_inventory_allowed"] is False
    assert dossier["claims"]["current_architecture_allowed"] is False
    assert dossier["result_count"] == 1


@pytest.mark.parametrize(
    "dossier_id",
    (
        "architecture",
        "implementation",
        "debugging",
        "consolidation",
        "archaeology",
        "deletion_review",
        "security_review",
        "claim_review",
    ),
)
def test_every_catalogued_dossier_runs_through_the_same_bounded_owner(
    dossier_store: Path, dossier_id: str
) -> None:
    dossier = build_dossier(
        dossier_store,
        dossier_id,
        ("JAA",),
        limit_per_term=10,
        overall_limit=25,
        include_semantic=False,
    )
    validate_self_hash(dossier)
    assert dossier["dossier"] == dossier_id
    assert dossier["authority_granted"] is False
    assert dossier["claims"]["deletion_authority_granted"] is False
    assert dossier["claims"]["execution_authority_granted"] is False


def test_dossier_refuses_unknown_or_malformed_requests(dossier_store: Path) -> None:
    with pytest.raises(DossierError, match="unknown dossier"):
        build_dossier(dossier_store, "unknown", ("JAA",))
    with pytest.raises(DossierError, match="between 1 and 16"):
        build_dossier(dossier_store, "implementation", ())
    with pytest.raises(DossierError, match="bounded strings"):
        build_dossier(dossier_store, "implementation", ("bad\x00term",))


def test_dossier_cli_returns_the_same_closed_contract(dossier_store: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.operations.scripts.archaeology",
            "mapper-dossier",
            "implementation",
            "JAA",
            "application_preparation",
            "--mapper-store",
            str(dossier_store),
            "--without-semantic",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    payload = json.loads(result.stdout)
    validate_self_hash(payload)
    assert payload["schema"] == "giga.archaeologist.mapper-dossier.v2"
    assert payload["dossier"] == "implementation"


def test_context_projection_ranks_canonical_code_and_obeys_exact_budget(
    dossier_store: Path,
) -> None:
    projection = build_context_projection(
        dossier_store,
        "implementation",
        ("application_preparation",),
        token_budget=1000,
        include_semantic=False,
    )
    validate_self_hash(projection)
    assert projection["schema"] == "giga.archaeologist.mapper-context.v1"
    assert projection["budget"]["unit"] == "giga.lexical-token.v1"
    assert projection["budget"]["model_token_equivalence_claimed"] is False
    assert projection["budget"]["used"] == lexical_token_count(projection["context"])
    assert projection["budget"]["used"] <= 1000
    assert projection["ranking"]["derived_not_authoritative"] is True
    assert projection["authority_granted"] is False
    assert all(
        item["attributes"].get("symbol_kind") not in {"PARAMETER", "VARIABLE"}
        for item in projection["entries"]
        if item["kind"] == "PYTHON_SYMBOL"
    )
    active = next(
        item
        for item in projection["entries"]
        if item.get("source", {}).get("path") == "src/jaa/application_preparation.py"
    )
    history = next(
        item
        for item in projection["entries"]
        if item.get("source", {}).get("path")
        == "archive/jaa/application_preparation.py"
    )
    temporary = next(
        item
        for item in projection["entries"]
        if item.get("source", {}).get("path")
        == ".codex-tmp-copy/internal/jaa/application_preparation.py"
    )
    assert active["ranking"]["score"] > history["ranking"]["score"]
    assert active["ranking"]["score"] > temporary["ranking"]["score"]
    related = next(
        item
        for item in projection["entries"]
        if item.get("source", {}).get("path") == "src/jaa/compiler.py"
    )
    assert related["matched_terms"] == []
    assert related["relation_context"]
    assert active["ranking"]["score"] > related["ranking"]["score"]


def test_context_projection_reports_budget_omissions_without_completeness_claim(
    dossier_store: Path,
) -> None:
    projection = build_context_projection(
        dossier_store,
        "implementation",
        ("application",),
        token_budget=32,
        include_semantic=False,
    )
    assert projection["budget"]["used"] <= 32
    assert projection["omissions"]["count"] > 0
    assert projection["completeness"] == "PARTIAL"
    assert projection["claims"]["complete_inventory_allowed"] is False
    assert projection["claims"]["current_architecture_allowed"] is False


def test_context_cli_returns_ranked_bounded_projection(dossier_store: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "modules.operations.scripts.archaeology",
        "mapper-context",
        "implementation",
        "JAA",
        "application_preparation",
        "--mapper-store",
        str(dossier_store),
        "--token-budget",
        "96",
        "--without-semantic",
    ]
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    replay = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert replay.stdout == result.stdout
    assert replay.stderr == result.stderr == ""
    payload = json.loads(result.stdout)
    validate_self_hash(payload)
    assert payload["schema"] == "giga.archaeologist.mapper-context.v1"
    assert payload["budget"]["used"] <= 96


@pytest.mark.parametrize("budget", (True, 31, 65_537))
def test_context_projection_refuses_invalid_budgets(
    dossier_store: Path, budget: int
) -> None:
    with pytest.raises(DossierError, match="token_budget"):
        build_context_projection(
            dossier_store,
            "implementation",
            ("JAA",),
            token_budget=budget,
        )
