from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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
def call_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "pkg").mkdir()
    (root / "pkg/__init__.py").write_text("", encoding="utf-8")
    (root / "pkg/flow.py").write_text(
        """def leaf(value: int) -> int:
    return value + 1

def branch(value: int) -> int:
    if value > 0:
        return leaf(value)
    try:
        for item in range(2):
            if item == value:
                break
        else:
            raise ValueError("missing")
    except ValueError:
        return 0
    return leaf(value)

def dynamic(callback):
    return callback()
""",
        encoding="utf-8",
    )
    (root / "pkg/cli.py").write_text(
        """from .flow import branch

def main() -> int:
    return branch(1)
""",
        encoding="utf-8",
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


def test_m03_exact_callers_callees_and_unresolved_dynamic_calls(
    call_repository: Path, tmp_path: Path
) -> None:
    inventory, mapper, run = _compile(call_repository, tmp_path)
    counts = run.manifest["counts"]
    assert counts["python_calls"] == 6
    assert counts["python_calls_resolved"] == 3

    branch = _one(
        query_mapper(mapper, "pkg.flow.branch", maps=("calls",), fact_limit=100),
        "PYTHON_SYMBOL",
        "pkg.flow.branch",
    )
    callees = [
        item
        for item in branch["facts"]["relations"]
        if item["predicate"] == "CALLS" and item["direction"] == "OUTGOING"
    ]
    assert [item["other"]["qualified_name"] for item in callees] == [
        "pkg.flow.leaf",
        "pkg.flow.leaf",
    ]
    assert all(item["attributes"]["resolution"] == "EXACT_LEXICAL" for item in callees)

    incoming = _one(
        query_mapper(mapper, "pkg.flow.branch", maps=("calls",), fact_limit=100),
        "PYTHON_SYMBOL",
        "pkg.flow.branch",
    )
    assert any(
        item["predicate"] == "CALLS"
        and item["direction"] == "INCOMING"
        and item["other"]["qualified_name"] == "pkg.cli.main"
        and item["attributes"]["resolution"] == "EXACT_IMPORT"
        for item in incoming["facts"]["relations"]
    )

    dynamic = _one(
        query_mapper(mapper, "pkg.flow.dynamic", maps=("calls",), fact_limit=100),
        "PYTHON_SYMBOL",
        "pkg.flow.dynamic",
    )
    calls = [
        item
        for item in dynamic["facts"]["observations"]
        if item["predicate"] == "PYTHON_CALL"
    ]
    assert calls[0]["source"]["path"] == "pkg/flow.py"
    assert calls[0]["value"]["expression"] == "callback"
    assert calls[0]["value"]["resolution"] == "UNRESOLVED_NON_CALLABLE"
    assert calls[0]["value"]["target_entity_id"] is None

    second = tmp_path / "second"
    refresh_mapper(inventory, second)
    repeated = _one(
        query_mapper(second, "pkg.flow.branch", maps=("calls",)),
        "PYTHON_SYMBOL",
        "pkg.flow.branch",
    )
    assert repeated["entity_id"] == branch["entity_id"]


def test_m03_structured_control_paths_have_exact_branch_and_terminal_nodes(
    call_repository: Path, tmp_path: Path
) -> None:
    _inventory, mapper, run = _compile(call_repository, tmp_path)
    counts = run.manifest["counts"]
    assert counts["python_control_flows"] == 4
    assert counts["python_control_nodes"] == 20
    assert counts["python_control_edges"] == 13

    branch_result = query_mapper(
        mapper,
        "pkg.flow.branch",
        maps=("control_flow",),
        fact_limit=200,
    )
    branch = _one(
        branch_result,
        "PYTHON_SYMBOL",
        "pkg.flow.branch",
    )
    nodes = [
        item
        for item in branch["facts"]["relations"]
        if item["predicate"] == "HAS_CONTROL_NODE"
    ]
    assert {
        item["other"]["qualified_name"].split("::", 1)[1].split("@", 1)[0]
        for item in nodes
    } >= {
        "FUNCTION_ENTRY",
        "FUNCTION_EXIT",
        "IF",
        "TRY",
        "FOR",
        "RETURN",
        "RAISE",
    }

    if_node = _one(
        query_mapper(
            mapper,
            "pkg.flow.branch::IF@5:4",
            maps=("control_flow",),
            fact_limit=50,
        ),
        "CONTROL_NODE",
        "pkg.flow.branch::IF@5:4",
    )
    outgoing = {
        item["predicate"]
        for item in if_node["facts"]["relations"]
        if item["direction"] == "OUTGOING"
    }
    assert outgoing == {"BRANCH_FALSE", "BRANCH_TRUE"}
    observation = [
        item
        for item in if_node["facts"]["observations"]
        if item["predicate"] == "PYTHON_CONTROL_NODE"
    ][0]
    assert observation["source"] == {
        "path": "pkg/flow.py",
        "line_start": 5,
        "line_end": 6,
        "column_start": 4,
        "column_end": 26,
    }
    assert observation["value"]["attributes"]["condition"] == "value > 0"

    coverage = {item["map_id"]: item for item in branch_result["coverage"]}
    assert coverage["control_flow"]["disposition"] == "COVERED"
    assert (
        coverage["control_flow"]["details"]["implicit_exception_edges"] == "UNSUPPORTED"
    )


def test_m03_syntax_failure_degrades_calls_and_control_flow(
    call_repository: Path, tmp_path: Path
) -> None:
    (call_repository / "pkg/broken.py").write_text("def broken(:\n", encoding="utf-8")
    _inventory, mapper, _run = _compile(call_repository, tmp_path)
    result = query_mapper(mapper, "pkg.flow.branch", maps=("calls", "control_flow"))
    coverage = {item["map_id"]: item for item in result["coverage"]}
    assert coverage["calls"]["disposition"] == "PARTIAL"
    assert coverage["control_flow"]["disposition"] == "PARTIAL"
    assert coverage["calls"]["details"]["failures"][0]["path"] == "pkg/broken.py"


def test_m03_decorator_calls_belong_to_the_containing_scope(
    call_repository: Path, tmp_path: Path
) -> None:
    (call_repository / "pkg/decorated.py").write_text(
        """def decorate():
    def apply(function):
        return function
    return apply

@decorate()
def target():
    return None
""",
        encoding="utf-8",
    )
    _inventory, mapper, _run = _compile(call_repository, tmp_path)
    module = _one(
        query_mapper(mapper, "pkg.decorated", maps=("calls",), fact_limit=100),
        "PYTHON_MODULE",
        "pkg.decorated",
    )
    assert any(
        item["predicate"] == "CALLS"
        and item["direction"] == "OUTGOING"
        and item["other"]["qualified_name"] == "pkg.decorated.decorate"
        for item in module["facts"]["relations"]
    )
    target = _one(
        query_mapper(mapper, "pkg.decorated.target", maps=("calls",), fact_limit=100),
        "PYTHON_SYMBOL",
        "pkg.decorated.target",
    )
    assert not [
        item
        for item in target["facts"]["relations"]
        if item["predicate"] == "CALLS" and item["direction"] == "OUTGOING"
    ]


def test_m03_irrefutable_match_does_not_invent_a_no_case_path(
    call_repository: Path, tmp_path: Path
) -> None:
    (call_repository / "pkg/matching.py").write_text(
        """def choose(value):
    match value:
        case 1:
            return "one"
        case _:
            return "other"
""",
        encoding="utf-8",
    )
    _inventory, mapper, _run = _compile(call_repository, tmp_path)
    match_node = _one(
        query_mapper(
            mapper,
            "pkg.matching.choose::MATCH@2:4",
            maps=("control_flow",),
            fact_limit=20,
        ),
        "CONTROL_NODE",
        "pkg.matching.choose::MATCH@2:4",
    )
    outgoing = [
        item
        for item in match_node["facts"]["relations"]
        if item["direction"] == "OUTGOING"
    ]
    assert [item["predicate"] for item in outgoing] == ["MATCH_CASE", "MATCH_CASE"]
    assert sorted(item["attributes"]["index"] for item in outgoing) == [0, 1]


def test_m03_duplicate_qualified_definitions_retain_distinct_control_graphs(
    call_repository: Path, tmp_path: Path
) -> None:
    (call_repository / "pkg/duplicates.py").write_text(
        """def repeated():
    return 1

def repeated():
    return 2
""",
        encoding="utf-8",
    )
    _inventory, mapper, _run = _compile(call_repository, tmp_path)
    repeated = _one(
        query_mapper(
            mapper,
            "pkg.duplicates.repeated",
            maps=("control_flow",),
            fact_limit=100,
        ),
        "PYTHON_SYMBOL",
        "pkg.duplicates.repeated",
    )
    assert repeated["truth_class"] == "CONFLICT"
    entries = [
        item
        for item in repeated["facts"]["relations"]
        if item["predicate"] == "HAS_CONTROL_NODE"
        and item["other"]["qualified_name"].endswith("::FUNCTION_ENTRY")
    ]
    assert len(entries) == 2
    assert entries[0]["other"]["entity_id"] != entries[1]["other"]["entity_id"]
