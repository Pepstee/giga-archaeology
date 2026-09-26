from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.cleanup_map import (
    CLEANUP_POLICY_SHA256,
    PYTHON_STRUCTURE_POLICY_SHA256,
)
from modules.operations.archaeology.mapper import query_mapper, refresh_mapper
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
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
def cleanup_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "pyproject.toml").write_text(
        '[project]\nname="cleanup-fixture"\nversion="0.1"\n'
        '[project.scripts]\ncleanup-fixture="app:main"\n',
        encoding="utf-8",
    )
    (root / "app.py").write_text(
        "def used():\n    return 1\n\n"
        "def main():\n    return used()\n\n"
        "def apparently_unused():\n    return 2\n",
        encoding="utf-8",
    )
    (root / "usage_signals.py").write_text(
        "def referenced_target():\n    return 3\n\n"
        "def reference_holder():\n    return referenced_target\n\n"
        "def marker(value):\n    return value\n\n"
        "@marker\n"
        "def decorated_target():\n    return 4\n\n"
        "def dynamic_target():\n    return 5\n\n"
        "def dynamic_holder(module):\n"
        "    return getattr(module, 'dynamic_target')\n\n"
        "def unknown_target():\n    return 6\n",
        encoding="utf-8",
    )
    (root / "other_usage.py").write_text(
        "def dynamic_target():\n    return 7\n",
        encoding="utf-8",
    )
    (root / "copy_a.txt").write_text("same safe bytes\n", encoding="utf-8")
    (root / "copy_b.txt").write_text("same safe bytes\n", encoding="utf-8")
    (root / "clone_a.py").write_text(
        "def collect_values(items):\n"
        "    selected = []\n"
        "    for item in items:\n"
        "        if item > 3:\n"
        "            selected.append(transform(item))\n"
        "    return selected\n",
        encoding="utf-8",
    )
    (root / "clone_b.py").write_text(
        "def gather_entries(entries):\n"
        "    result = []\n"
        "    for entry in entries:\n"
        "        if entry > 3:\n"
        "            result.append(transform(entry))\n"
        "    return result\n",
        encoding="utf-8",
    )
    (root / "different_literal.py").write_text(
        "def gather_other(entries):\n"
        "    result = []\n"
        "    for entry in entries:\n"
        "        if entry > 4:\n"
        "            result.append(transform(entry))\n"
        "    return result\n",
        encoding="utf-8",
    )
    (root / "different_annotation_a.py").write_text(
        "def annotated(items: Alpha) -> Alpha:\n"
        "    selected: list[Alpha] = []\n"
        "    selected.extend(items)\n"
        "    return selected\n",
        encoding="utf-8",
    )
    (root / "different_annotation_b.py").write_text(
        "def annotated(items: Beta) -> Beta:\n"
        "    selected: list[Beta] = []\n"
        "    selected.extend(items)\n"
        "    return selected\n",
        encoding="utf-8",
    )
    (root / "method_a.py").write_text(
        "class FirstVisitor:\n"
        "    def visit_ClassDef(self, node):\n"
        "        selected = []\n"
        "        for item in node.body:\n"
        "            if item is not None:\n"
        "                selected.append(transform(item))\n"
        "        return selected\n",
        encoding="utf-8",
    )
    (root / "method_b.py").write_text(
        "class SecondVisitor:\n"
        "    def visit_ClassDef(self, node):\n"
        "        result = []\n"
        "        for entry in node.body:\n"
        "            if entry is not None:\n"
        "                result.append(transform(entry))\n"
        "        return result\n",
        encoding="utf-8",
    )
    (root / "memory").mkdir()
    (root / "memory/private_a.txt").write_text("same private bytes\n", encoding="utf-8")
    (root / "memory/private_b.txt").write_text("same private bytes\n", encoding="utf-8")
    (root / "memory/private_clone.py").write_text(
        "def private_clone(items):\n"
        "    selected = []\n"
        "    for item in items:\n"
        "        if item > 3:\n"
        "            selected.append(transform(item))\n"
        "    return selected\n",
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _compile(root: Path, tmp_path: Path):
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    return mapper, refresh_mapper(inventory, mapper)


def test_m07_exact_duplicates_are_navigable_without_cleanup_authority(
    cleanup_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(cleanup_repository, tmp_path)
    assert run.manifest["counts"]["exact_duplicate_groups"] >= 1
    result = query_mapper(mapper, "copy_a.txt", maps=("duplicates_similarity",))
    member = next(
        item for item in result["results"] if item["kind"] == "DUPLICATE_MEMBER"
    )
    assert member["attributes"]["cleanup_permitted"] is False
    group = next(
        fact["other"]
        for fact in member["facts"]["relations"]
        if fact["predicate"] == "HAS_EXACT_DUPLICATE_MEMBER"
    )
    assert group["kind"] == "DUPLICATE_GROUP"
    group_result = query_mapper(
        mapper,
        member["attributes"]["content_sha256"],
        maps=("duplicates_similarity",),
    )
    exact_group = next(
        item for item in group_result["results"] if item["kind"] == "DUPLICATE_GROUP"
    )
    assert exact_group["attributes"]["similarity_tier"] == "EXACT_CONTENT"
    assert result["coverage"][0]["details"]["deletion_permitted"] is False
    assert result["coverage"][0]["details"]["policy_sha256"] == CLEANUP_POLICY_SHA256


def test_m07_sensitive_duplicate_paths_are_not_projected(
    cleanup_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(cleanup_repository, tmp_path)
    assert run.manifest["counts"]["duplicate_groups_skipped_policy"] >= 1
    result = query_mapper(mapper, "private_a.txt", maps=("duplicates_similarity",))
    assert result["results"] == []


def test_m29_alpha_renamed_python_structure_is_navigable_without_equivalence_claim(
    cleanup_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(cleanup_repository, tmp_path)
    assert run.manifest["counts"]["structural_duplicate_groups"] >= 1
    assert run.manifest["counts"]["structural_duplicate_members"] >= 2
    result = query_mapper(mapper, "collect_values", maps=("duplicates_similarity",))
    member = next(
        item
        for item in result["results"]
        if item["kind"] == "STRUCTURAL_DUPLICATE_MEMBER"
    )
    assert member["truth_class"] == "OBSERVED"
    assert member["attributes"]["cleanup_permitted"] is False
    assert member["attributes"]["semantic_equivalence_claimed"] is False
    assert (
        member["attributes"]["normalization_policy_sha256"]
        == PYTHON_STRUCTURE_POLICY_SHA256
    )
    group_id = next(
        fact["other"]["entity_id"]
        for fact in member["facts"]["relations"]
        if fact["predicate"] == "HAS_STRUCTURAL_DUPLICATE_MEMBER"
    )
    group = query_mapper(
        mapper,
        member["attributes"]["fingerprint_sha256"],
        maps=("duplicates_similarity",),
    )
    observed = next(item for item in group["results"] if item["entity_id"] == group_id)
    assert observed["attributes"]["copies"] == 2
    assert observed["attributes"]["cross_file"] is True
    assert observed["attributes"]["similarity_tier"] == "NORMALIZED_PYTHON_AST_EXACT"
    coverage = next(
        item
        for item in group["coverage"]
        if item["fact_class"] == "PYTHON_NORMALIZED_AST_STRUCTURAL_GROUP"
    )
    assert coverage["details"]["semantic_similarity"] == "UNSUPPORTED"
    assert coverage["details"]["deletion_permitted"] is False


def test_m29_literals_and_sensitive_sources_are_not_false_structural_matches(
    cleanup_repository: Path, tmp_path: Path
) -> None:
    mapper, _run = _compile(cleanup_repository, tmp_path)
    changed = query_mapper(mapper, "gather_other", maps=("duplicates_similarity",))
    assert changed["results"] == []
    private = query_mapper(mapper, "private_clone", maps=("duplicates_similarity",))
    assert private["results"] == []
    annotations = query_mapper(mapper, "annotated", maps=("duplicates_similarity",))
    assert annotations["results"] == []


def test_m29_structural_method_identity_matches_python_symbol_kind(
    cleanup_repository: Path, tmp_path: Path
) -> None:
    mapper, _run = _compile(cleanup_repository, tmp_path)

    result = query_mapper(mapper, "visit_ClassDef", maps=("duplicates_similarity",))

    members = [
        item
        for item in result["results"]
        if item["kind"] == "STRUCTURAL_DUPLICATE_MEMBER"
    ]
    assert {item["attributes"]["qualified_name"] for item in members} == {
        "method_a.FirstVisitor.visit_ClassDef",
        "method_b.SecondVisitor.visit_ClassDef",
    }


def test_m07_static_not_reached_is_an_inferred_hypothesis_not_dead_code(
    cleanup_repository: Path, tmp_path: Path
) -> None:
    mapper, _run = _compile(cleanup_repository, tmp_path)
    reached = query_mapper(mapper, "used", maps=("reachability",))
    used = next(
        item for item in reached["results"] if item["qualified_name"] == "app.used"
    )
    used_observation = next(
        fact
        for fact in used["facts"]["observations"]
        if fact["predicate"] == "STATIC_REACHABILITY"
    )
    assert used_observation["value"]["state"] == "REACHED_FROM_SUPPORTED_STATIC_ROOT"

    uncertain = query_mapper(mapper, "apparently_unused", maps=("reachability",))
    symbol = next(
        item
        for item in uncertain["results"]
        if item["qualified_name"] == "app.apparently_unused"
    )
    observation = next(
        fact
        for fact in symbol["facts"]["observations"]
        if fact["predicate"] == "STATIC_REACHABILITY"
    )
    assert observation["truth_class"] == "INFERRED"
    assert observation["value"]["state"] == "NOT_REACHED_BY_SUPPORTED_STATIC_ROOTS"
    assert observation["value"]["deletion_permitted"] is False
    assert uncertain["coverage"][0]["details"]["dead_code_claim"] == "FORBIDDEN"


def test_m56_usage_counterevidence_preserves_exact_observed_and_unknown_tiers(
    cleanup_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(cleanup_repository, tmp_path)
    assert run.manifest["counts"]["usage_counterevidence_facts"] > 0

    bounded = query_mapper(
        mapper,
        "referenced_target",
        maps=("reachability",),
        fact_limit=1,
    )
    bounded_symbol = next(
        item
        for item in bounded["results"]
        if item["qualified_name"] == "usage_signals.referenced_target"
    )
    assert [item["predicate"] for item in bounded_symbol["facts"]["observations"]] == [
        "STATIC_REACHABILITY"
    ]
    assert bounded_symbol["facts"]["observations_truncated"] is True

    referenced = query_mapper(mapper, "referenced_target", maps=("reachability",))
    referenced_symbol = next(
        item
        for item in referenced["results"]
        if item["qualified_name"] == "usage_signals.referenced_target"
    )
    referenced_facts = referenced_symbol["facts"]["observations"]
    assert referenced_symbol["source"]["location"]["line_start"] == 1
    static = next(
        item for item in referenced_facts if item["predicate"] == "STATIC_REACHABILITY"
    )
    assert static["value"]["state"] == "NOT_REACHED_BY_SUPPORTED_STATIC_ROOTS"
    assert static["value"]["usage_counterevidence"]["state"] == ("PRESENT_EXACT_STATIC")
    exact = [
        item
        for item in referenced_facts
        if item["predicate"] == "DELETION_COUNTEREVIDENCE"
    ]
    assert any(item["value"]["kind"] == "RESOLVED_REFERENCE" for item in exact)
    assert all(item["truth_class"] == "PROVEN" for item in exact)

    decorated = query_mapper(mapper, "decorated_target", maps=("reachability",))
    decorated_symbol = next(
        item
        for item in decorated["results"]
        if item["qualified_name"] == "usage_signals.decorated_target"
    )
    decorated_facts = decorated_symbol["facts"]["observations"]
    decorated_static = next(
        item for item in decorated_facts if item["predicate"] == "STATIC_REACHABILITY"
    )
    assert decorated_static["value"]["usage_counterevidence"]["state"] == (
        "PRESENT_OBSERVED_SYNTAX"
    )
    declaration = next(
        item
        for item in decorated_facts
        if item["predicate"] == "DELETION_COUNTEREVIDENCE"
    )
    assert declaration["truth_class"] == "OBSERVED"
    assert declaration["value"]["kind"] == "DECORATED_DEFINITION"

    dynamic = query_mapper(mapper, "dynamic_target", maps=("reachability",))
    dynamic_symbol = next(
        item
        for item in dynamic["results"]
        if item["qualified_name"] == "usage_signals.dynamic_target"
    )
    dynamic_facts = dynamic_symbol["facts"]["observations"]
    dynamic_static = next(
        item for item in dynamic_facts if item["predicate"] == "STATIC_REACHABILITY"
    )
    assert dynamic_static["value"]["dynamic_counterevidence"] == (
        "PRESENT_OBSERVED_NAME_MATCH"
    )
    dynamic_signal = next(
        item
        for item in dynamic_facts
        if item["predicate"] == "DELETION_COUNTEREVIDENCE"
    )
    assert dynamic_signal["truth_class"] == "OBSERVED"
    assert dynamic_signal["value"]["target_binding"] == (
        "LEXICAL_NAME_MATCH_NOT_SEMANTIC_BINDING"
    )
    assert dynamic_signal["value"]["details"]["matching_candidate_count"] == 2

    unknown = query_mapper(mapper, "unknown_target", maps=("reachability",))
    unknown_symbol = next(
        item
        for item in unknown["results"]
        if item["qualified_name"] == "usage_signals.unknown_target"
    )
    unknown_facts = unknown_symbol["facts"]["observations"]
    unknown_static = next(
        item for item in unknown_facts if item["predicate"] == "STATIC_REACHABILITY"
    )
    assert unknown_static["value"]["usage_counterevidence"] == {
        "exact_facts": 0,
        "observed_facts": 0,
        "state": "UNKNOWN",
    }
    assert not any(
        item["predicate"] == "DELETION_COUNTEREVIDENCE" for item in unknown_facts
    )
    coverage = unknown["coverage"][0]
    assert coverage["details"]["dead_code_claim"] == "FORBIDDEN"
    assert coverage["details"]["counterevidence_facts"] > 0
