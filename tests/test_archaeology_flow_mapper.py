from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.flow_policy import (
    FLOW_POLICY_VERSION,
    POLICY_SHA256,
)
from modules.operations.archaeology.mapper import query_mapper, refresh_mapper
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
def flow_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "flow.py").write_text(
        """import logging
import subprocess as sp

def risky():
    raw = input()
    command = raw
    sp.run(command)
    logging.info(command)
    return command

def direct():
    sp.run(input())

def literal():
    sp.run(["echo", "ok"])

def write(path, payload):
    handle = open(path, "w")
    handle.write(payload)

def unknown(source, sink):
    sink(source)

def duplicate(raw):
    same, same = raw
""",
        encoding="utf-8",
    )
    (root / "memory").mkdir()
    (root / "memory/private.py").write_text(
        "def hidden():\n    return input()\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _compile(root: Path, tmp_path: Path):
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    run = refresh_mapper(inventory, mapper)
    return inventory, mapper, run


def _one(result: dict, kind: str, qualified_name: str) -> dict:
    matches = [
        item
        for item in result["results"]
        if item["kind"] == kind and item["qualified_name"] == qualified_name
    ]
    assert len(matches) == 1, result["results"]
    return matches[0]


def test_m04_policy_bound_sources_effects_and_possible_paths(
    flow_repository: Path, tmp_path: Path
) -> None:
    _inventory, mapper, run = _compile(flow_repository, tmp_path)
    counts = run.manifest["counts"]
    assert counts["python_data_sources"] == 2
    assert counts["python_security_effects"] == 5
    assert counts["python_possible_taint_paths"] == 3
    assert counts["python_static_flows"] >= 8
    assert run.manifest["compiler"]["flow_policy"] == FLOW_POLICY_VERSION
    assert run.manifest["compiler"]["flow_policy_sha256"] == POLICY_SHA256

    source_result = query_mapper(
        mapper,
        "UNTRUSTED_STDIN:flow.risky",
        maps=("data_flow_taint", "security_capabilities"),
        fact_limit=100,
    )
    source = _one(
        source_result,
        "DATA_SOURCE",
        "UNTRUSTED_STDIN:flow.risky@5:10",
    )
    assert source["truth_class"] == "INFERRED"
    assert source["attributes"]["runtime_observed"] is False
    reaches = [
        item
        for item in source["facts"]["relations"]
        if item["predicate"] == "MAY_REACH_EFFECT"
    ]
    assert {item["other"]["qualified_name"].split(":", 1)[0] for item in reaches} == {
        "OUTPUT_DISCLOSURE",
        "PROCESS_EXECUTION",
    }
    assert all(item["truth_class"] == "INFERRED" for item in reaches)
    assert all(item["attributes"]["vulnerability_claim"] is False for item in reaches)
    assert all(item["attributes"]["runtime_observed"] is False for item in reaches)
    coverage = {item["map_id"]: item for item in source_result["coverage"]}
    assert coverage["data_flow_taint"]["details"]["clean_result_claim"] == "FORBIDDEN"
    assert (
        coverage["security_capabilities"]["details"]["capability_granted_by_map"]
        is False
    )


def test_m04_aliases_direct_sources_and_effect_boundaries_are_precise(
    flow_repository: Path, tmp_path: Path
) -> None:
    _inventory, mapper, _run = _compile(flow_repository, tmp_path)
    process = query_mapper(
        mapper,
        "PROCESS_EXECUTION",
        maps=("security_capabilities",),
        limit=20,
        fact_limit=50,
    )
    effects = [item for item in process["results"] if item["kind"] == "SECURITY_EFFECT"]
    assert len(effects) == 3
    assert all(item["attributes"]["expression"] == "subprocess.run" for item in effects)
    assert all(
        item["attributes"]["authority_status"] == "NOT_EVALUATED" for item in effects
    )
    assert all(
        item["attributes"]["execution_status"] == "NOT_OBSERVED" for item in effects
    )

    direct = _one(
        query_mapper(
            mapper,
            "UNTRUSTED_STDIN:flow.direct",
            maps=("data_flow_taint",),
            fact_limit=50,
        ),
        "DATA_SOURCE",
        "UNTRUSTED_STDIN:flow.direct@12:11",
    )
    assert any(
        item["predicate"] == "MAY_REACH_EFFECT"
        and item["other"]["qualified_name"].startswith("PROCESS_EXECUTION:flow.direct")
        for item in direct["facts"]["relations"]
    )

    filesystem = query_mapper(
        mapper,
        "FILESYSTEM_WRITE",
        maps=("security_capabilities",),
        fact_limit=20,
    )
    assert filesystem["result_count"] == 1
    assert filesystem["results"][0]["source"]["path"] == "flow.py"

    unknown = _one(
        query_mapper(
            mapper,
            "flow.unknown",
            maps=("calls", "security_capabilities"),
            fact_limit=50,
        ),
        "PYTHON_SYMBOL",
        "flow.unknown",
    )
    assert not [
        item
        for item in unknown["facts"]["relations"]
        if item["predicate"] == "MAY_CAUSE_EFFECT"
    ]
    assert (
        query_mapper(
            mapper,
            "hidden",
            maps=("data_flow_taint", "security_capabilities"),
        )["result_count"]
        == 0
    )


def test_m04_syntax_failure_forbids_false_clean_result(
    flow_repository: Path, tmp_path: Path
) -> None:
    (flow_repository / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    _inventory, mapper, _run = _compile(flow_repository, tmp_path)
    result = query_mapper(
        mapper,
        "flow.risky",
        maps=("data_flow_taint", "security_capabilities"),
    )
    coverage = {item["map_id"]: item for item in result["coverage"]}
    assert coverage["data_flow_taint"]["disposition"] == "PARTIAL"
    assert coverage["security_capabilities"]["disposition"] == "PARTIAL"
    assert coverage["data_flow_taint"]["details"]["failures"][0]["path"] == "broken.py"


def test_m04_duplicate_derivations_collapse_to_one_exact_flow(
    flow_repository: Path, tmp_path: Path
) -> None:
    _inventory, mapper, _run = _compile(flow_repository, tmp_path)
    same = _one(
        query_mapper(
            mapper,
            "flow.duplicate.same",
            maps=("data_flow_taint",),
            fact_limit=50,
        ),
        "PYTHON_SYMBOL",
        "flow.duplicate.same",
    )
    incoming = [
        item
        for item in same["facts"]["relations"]
        if item["predicate"] == "MAY_FLOW_TO" and item["direction"] == "INCOMING"
    ]
    assert len(incoming) == 1
    assert incoming[0]["other"]["qualified_name"] == "flow.duplicate.raw"
