from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from modules.operations.archaeology.evidence import validate_self_hash
from modules.operations.archaeology.map_catalog import (
    COVERAGE_STATES,
    MAP_ENTITY_KINDS,
    MAPS,
    TRUTH_CLASSES,
    build_map_catalog,
    map_by_id,
    route_query_maps,
)


EXPECTED_MAPS = {
    "inventory",
    "structure",
    "symbols",
    "dependencies",
    "calls",
    "control_flow",
    "data_flow_taint",
    "types",
    "api_events",
    "database_lineage",
    "build_deployment",
    "runtime_topology",
    "tests_coverage",
    "quality_findings",
    "duplicates_similarity",
    "reachability",
    "git_lineage",
    "ownership_canonicality",
    "requirements_decisions",
    "evidence_claims",
    "security_capabilities",
    "semantic_graphify",
}


def test_catalog_is_complete_deterministic_closed_and_non_authorizing() -> None:
    first = build_map_catalog()
    second = build_map_catalog()
    assert first == second
    validate_self_hash(first)
    assert first["authority_granted"] is False
    assert first["truth_classes"] == list(TRUTH_CLASSES)
    assert first["coverage_states"] == list(COVERAGE_STATES)
    assert {item["id"] for item in first["maps"]} == EXPECTED_MAPS
    assert len(first["maps"]) == len(EXPECTED_MAPS) == 22
    assert all(item["authority_granted"] is False for item in first["maps"])
    assert set(MAP_ENTITY_KINDS) == EXPECTED_MAPS
    assert first["entity_kinds"] == {
        identifier: sorted(MAP_ENTITY_KINDS[identifier])
        for identifier in first["entity_kinds"]
    }


def test_dependencies_and_dossiers_reference_only_registered_maps() -> None:
    catalog = build_map_catalog()
    registered = {item["id"] for item in catalog["maps"]}
    for item in catalog["maps"]:
        assert item["id"] not in item["dependencies"]
        assert set(item["dependencies"]) <= registered
        assert item["question"]
        assert item["acceptance"]
        assert item["producer"]
        assert item["slice"].startswith("M")
    assert {item["id"] for item in catalog["dossiers"]} == {
        "architecture",
        "implementation",
        "debugging",
        "consolidation",
        "archaeology",
        "deletion_review",
        "security_review",
        "claim_review",
    }
    for dossier in catalog["dossiers"]:
        assert dossier["maps"]
        assert len(dossier["maps"]) == len(set(dossier["maps"]))
        assert set(dossier["maps"]) <= registered
        assert (
            dossier["implementation_state"] == "IMPLEMENTED_M12_BOUNDED_QUERY_PLANNER"
        )


def test_every_current_foundation_is_truthfully_qualified() -> None:
    states = {item["id"]: item["implementation_state"] for item in MAPS}
    assert states["inventory"] == "IMPLEMENTED_M01"
    assert states["structure"] == "IMPLEMENTED_M01_PARTIAL"
    assert (
        states["symbols"]
        == "IMPLEMENTED_M30_PYTHON_AST_SCIP_BASH_AND_JAVASCRIPT_TYPESCRIPT_PARTIAL"
    )
    assert (
        states["dependencies"]
        == "IMPLEMENTED_M30_PYTHON_AST_SCIP_BASH_AND_JAVASCRIPT_TYPESCRIPT_PARTIAL"
    )
    assert states["types"] == "IMPLEMENTED_M26_PYTHON_AST_AND_SCIP_PARTIAL"
    assert (
        states["api_events"]
        == "IMPLEMENTED_M30_PYTHON_BASH_AND_JAVASCRIPT_TYPESCRIPT_PARTIAL"
    )
    assert (
        states["calls"]
        == "IMPLEMENTED_M30_PYTHON_BASH_AND_JAVASCRIPT_TYPESCRIPT_PARTIAL"
    )
    assert states["control_flow"] == "IMPLEMENTED_M03_PYTHON_PARTIAL"
    assert (
        states["semantic_graphify"]
        == "IMPLEMENTED_M11_FEDERATED_LOCAL_GRAPHIFY_PARTIAL"
    )
    assert states["data_flow_taint"] == "IMPLEMENTED_M04_PYTHON_PARTIAL"
    assert states["security_capabilities"] == "IMPLEMENTED_M04_PYTHON_PARTIAL"
    assert states["database_lineage"] == "IMPLEMENTED_M05_PYTHON_LITERAL_PARTIAL"
    assert states["build_deployment"] == "IMPLEMENTED_M05_SAFE_DECLARATION_PARTIAL"
    assert (
        states["tests_coverage"]
        == "IMPLEMENTED_M06_STATIC_AND_COVERAGE_ARTIFACT_PARTIAL"
    )
    assert (
        states["quality_findings"]
        == "IMPLEMENTED_M51_RECEIPT_CLAIM_CURRENT_PATH_PROVENANCE_PARTIAL"
    )
    assert (
        states["runtime_topology"]
        == "IMPLEMENTED_M10_EXTERNAL_CAPABILITY_GATE_STATUS_PARTIAL"
    )
    assert (
        states["requirements_decisions"]
        == "IMPLEMENTED_M54_GOVERNED_MARKDOWN_AND_JSON_PATH_REFERENCE_PARTIAL"
    )
    assert "COMPLETE" not in set(states.values())


def test_map_lookup_refuses_unknown_identifier() -> None:
    assert map_by_id("inventory")["producer"] == "navigation_inventory"
    try:
        map_by_id("not-a-map")
    except KeyError as exc:
        assert exc.args == ("not-a-map",)
    else:
        raise AssertionError("unknown map did not refuse")


def test_query_router_is_deterministic_dependency_complete_and_auditable() -> None:
    first = route_query_maps("Find the FastAPI route and database writes")
    second = route_query_maps("Find the FastAPI route and database writes")
    assert first == second
    validate_self_hash(first)
    assert first["map_catalog_receipt_sha256"] == build_map_catalog()["receipt_sha256"]
    assert first["mode"] == "AUTO_DETERMINISTIC"
    assert first["fallback"] is None
    assert {item["id"] for item in first["matched_rules"]} == {
        "entrypoint-navigation",
        "database-navigation",
    }
    assert {"inventory", "structure", "symbols", "dependencies"} <= set(
        first["selected_maps"]
    )
    assert {"api_events", "database_lineage"} <= set(first["selected_maps"])
    assert first["primary_maps"] == ["api_events", "database_lineage"]
    assert first["search_query"] == "fastapi"

    lineage = route_query_maps("Git rename lineage")
    assert lineage["search_query"] == "rename"
    for query, expected_search in (
        ("lost implementation", "lost"),
        ("forgotten implementation", "forgotten"),
        ("historical symbol", "historical"),
        ("deleted Python declaration", "python declaration"),
        ("symbol evolution", "evolution"),
        ("changed", "changed"),
    ):
        routed = route_query_maps(query)
        assert routed["fallback"] is None
        expected_primary = (
            ["symbols", "types", "git_lineage"]
            if "symbol" in query or "implementation" in query
            else ["git_lineage"]
        )
        assert routed["primary_maps"] == expected_primary
        assert routed["search_query"] == expected_search
    coverage = route_query_maps("coverage report")
    assert coverage["search_query"] == "coverage"


def test_query_router_falls_back_to_every_map_without_hiding_coverage() -> None:
    route = route_query_maps("JAA application preparation")
    validate_self_hash(route)
    assert route["fallback"] == "ALL_REGISTERED_MAPS_NO_INTENT_MATCH"
    assert route["search_query"] == "JAA application preparation"
    assert route["selected_maps"] == [item["id"] for item in MAPS]
    assert route["primary_maps"] == route["selected_maps"]


def test_explicit_query_route_preserves_exact_requested_views() -> None:
    route = route_query_maps(
        "route", requested_maps=("api_events", "api_events", "symbols")
    )
    validate_self_hash(route)
    assert route["mode"] == "EXPLICIT"
    assert route["search_query"] == "route"
    assert route["selected_maps"] == ["api_events", "symbols"]
    assert route["primary_maps"] == ["api_events", "symbols"]
    assert route["dependency_expansion"] is False
    assert route["fallback"] is None


def test_cli_exposes_full_catalog_and_one_selected_map() -> None:
    root = Path(__file__).resolve().parents[1]
    full = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.operations.scripts.archaeology",
            "map-catalog",
        ],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    payload = json.loads(full.stdout)
    validate_self_hash(payload)
    assert {item["id"] for item in payload["maps"]} == EXPECTED_MAPS

    selected = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.operations.scripts.archaeology",
            "map-catalog",
            "--map",
            "control_flow",
        ],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert json.loads(selected.stdout)["map"]["id"] == "control_flow"
