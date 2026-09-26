from __future__ import annotations

import gzip
import json
import subprocess
import sys
from pathlib import Path

import pytest

from modules.operations.archaeology import divergence
from modules.operations.archaeology.divergence import (
    DivergenceError,
    build_derived_payload_verifier_lineage,
    build_cross_worktree_behavior_map,
    build_cross_worktree_identity_map,
    build_cross_worktree_static_fact_map,
    render_derived_payload_verifier_lineage_report,
    write_derived_payload_verifier_lineage,
    write_cross_worktree_behavior_map,
    write_cross_worktree_identity_map,
    write_cross_worktree_static_fact_map,
)
from modules.operations.archaeology.evidence import (
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def _repository(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.name", "Fixture")
    _git(path, "config", "user.email", "<redacted-email>")
    return path


def _commit(root: Path, message: str) -> None:
    _git(root, "add", ".")
    _git(root, "commit", "-qm", message)


def _clone_repository(source: Path, target: Path) -> Path:
    subprocess.run(
        ["/usr/bin/git", "clone", "-q", str(source), str(target)], check=True
    )
    _git(target, "config", "user.name", "Fixture")
    _git(target, "config", "user.email", "<redacted-email>")
    return target


def _related_repositories(tmp_path: Path) -> tuple[Path, Path, Path]:
    canonical = _repository(tmp_path / "canonical")
    (canonical / "src").mkdir()
    (canonical / "src/tool.py").write_text(
        "BASE = 1\n\ndef shared():\n    return BASE\n", encoding="utf-8"
    )
    (canonical / "README.md").write_text("same\n", encoding="utf-8")
    _commit(canonical, "base")
    donor = tmp_path / "donor"
    subprocess.run(
        ["/usr/bin/git", "clone", "-q", str(canonical), str(donor)], check=True
    )
    _git(donor, "config", "user.name", "Fixture")
    _git(donor, "config", "user.email", "<redacted-email>")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "CURRENT.json").write_text("{}\n", encoding="utf-8")
    return canonical, donor, runtime


def test_identity_map_binds_superset_unique_dirty_and_ancestry(tmp_path: Path) -> None:
    canonical, donor, runtime = _related_repositories(tmp_path)
    (donor / "src/tool.py").write_text(
        "BASE = 1\n\ndef shared():\n    return BASE\n\ndef extra():\n    return 2\n",
        encoding="utf-8",
    )
    (donor / "src/unique.py").write_text(
        "def unique():\n    return 3\n", encoding="utf-8"
    )
    _commit(donor, "donor capability")
    (donor / "README.md").write_text("dirty\n", encoding="utf-8")
    (donor / "scratch.py").write_text("UNTRACKED = True\n", encoding="utf-8")
    before = _git(donor, "status", "--porcelain=v1", "--untracked-files=all")

    payload = build_cross_worktree_identity_map(
        canonical, [donor], runtime_roots=[runtime]
    )

    validate_self_hash(payload)
    validate_self_hash(payload["zero_mutation"])
    comparison = {
        item["path"]: item["classification"]
        for item in payload["donors"][0]["path_comparisons"]
    }
    assert comparison["src/tool.py"] == "DONOR_STRICT_SYMBOL_SUPERSET"
    assert comparison["src/unique.py"] == "UNIQUE_TO_DONOR_UNKNOWN_USEFULNESS"
    assert comparison["README.md"] == "INDETERMINATE_DIFFERENT_CONTENT"
    assert payload["donors"][0]["ancestry"]["canonical_is_ancestor_of_donor"]
    dirty = payload["donors"][0]["observation"]["dirty"]
    assert {item["path"] for item in dirty["safe_entries"]} == {
        "README.md",
        "scratch.py",
    }
    assert all(
        identity["content_sha256"]
        for item in dirty["safe_entries"]
        for identity in item["identities"]
    )
    assert _git(donor, "status", "--porcelain=v1", "--untracked-files=all") == before
    assert payload["claims"]["no_feature_loss"] is False
    assert (
        payload["capability_fact_coverage"]["public_export_identity"]
        == "UNKNOWN_NOT_EXTRACTED_M69"
    )


def test_divergent_symbol_sets_are_conflict_not_equivalence(tmp_path: Path) -> None:
    canonical, donor, _runtime = _related_repositories(tmp_path)
    (canonical / "src/tool.py").write_text(
        "def shared():\n    return 1\n\ndef canonical_only():\n    return 2\n",
        encoding="utf-8",
    )
    _commit(canonical, "canonical divergence")
    (donor / "src/tool.py").write_text(
        "def shared():\n    return 1\n\ndef donor_only():\n    return 3\n",
        encoding="utf-8",
    )
    _commit(donor, "donor divergence")

    payload = build_cross_worktree_identity_map(canonical, [donor])
    tool = next(
        item
        for item in payload["donors"][0]["path_comparisons"]
        if item["path"] == "src/tool.py"
    )
    assert tool["classification"] == "CONFLICTING_SYMBOL_IDENTITY_SET"
    assert tool["semantic_equivalence_claimed"] is False
    ancestry = payload["donors"][0]["ancestry"]
    assert ancestry["status"] == "PROVEN"
    assert ancestry["canonical_is_ancestor_of_donor"] is False
    assert ancestry["donor_is_ancestor_of_canonical"] is False


def test_runtime_drift_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical, donor, runtime = _related_repositories(tmp_path)
    original = divergence._runtime_snapshot
    calls = 0

    def changing_snapshot(path: Path) -> dict[str, object]:
        nonlocal calls
        calls += 1
        result = original(path)
        if calls > 1:
            result = {**result, "metadata_tree_sha256": "f" * 64}
        return result

    monkeypatch.setattr(divergence, "_runtime_snapshot", changing_snapshot)
    with pytest.raises(DivergenceError, match="changed during comparison"):
        build_cross_worktree_identity_map(canonical, [donor], runtime_roots=[runtime])


def test_writer_is_create_once_and_keeps_outputs_outside_subjects(
    tmp_path: Path,
) -> None:
    canonical, donor, runtime = _related_repositories(tmp_path)
    output = tmp_path / "evidence"
    payload = write_cross_worktree_identity_map(
        canonical, [donor], output, runtime_roots=[runtime]
    )
    assert (output / "divergence.json").is_file()
    assert (output / "DIVERGENCE_REPORT.md").is_file()
    assert payload["zero_mutation"]["status"] == "PASS"
    with pytest.raises(DivergenceError, match="must not already exist"):
        write_cross_worktree_identity_map(canonical, [donor], output)


def _m69_predecessor(canonical: Path, donor: Path, output: Path) -> Path:
    write_cross_worktree_identity_map(canonical, [donor], output)
    return output / "divergence.json"


def _m70_predecessor(
    canonical: Path,
    donor: Path,
    m69: Path,
    output: Path,
) -> Path:
    write_cross_worktree_static_fact_map(canonical, [donor], m69, output)
    return output / "static_divergence.json.gz"


def test_static_fact_map_closes_four_python_fact_classes(tmp_path: Path) -> None:
    canonical, donor, runtime = _related_repositories(tmp_path)
    predecessor = _m69_predecessor(canonical, donor, tmp_path / "m69")
    (canonical / "src/tool.py").write_text(
        "import os\nBASE = 1\n__all__ = ['shared']\n\n"
        "def helper():\n    return os.getcwd()\n\n"
        "def shared():\n    return helper(), BASE\n",
        encoding="utf-8",
    )
    (canonical / "src/__init__.py").write_text(
        "from .tool import shared\n", encoding="utf-8"
    )
    _commit(canonical, "canonical static facts")
    (donor / "src/tool.py").write_text(
        "import os\nfrom pathlib import Path\nBASE = 2\nEXTRA = 3\n"
        "__all__ = ['extra', 'shared']\n\n"
        "def helper():\n    return os.getcwd()\n\n"
        "def shared():\n    return helper(), BASE\n\n"
        "def extra():\n    return Path('.')\n",
        encoding="utf-8",
    )
    (donor / "src/__init__.py").write_text(
        "from .tool import extra, shared\n", encoding="utf-8"
    )
    _commit(donor, "donor static facts")

    payload = build_cross_worktree_static_fact_map(
        canonical, [donor], predecessor, runtime_roots=[runtime]
    )

    validate_self_hash(payload)
    validate_self_hash(payload["zero_mutation"])
    canonical_facts = payload["canonical_static_facts"]["facts"]
    assert any(
        fact["identity"]["target"] == "src.tool.BASE"
        for fact in canonical_facts["assignments_constants"]
    )
    assert any(
        fact["kind"] == "EXPLICIT___ALL__"
        and fact["identity"]["exported_name"] == "shared"
        for fact in canonical_facts["public_exports"]
    )
    assert any(
        fact["kind"] == "PACKAGE_REEXPORT"
        and fact["identity"]["exported_name"] == "shared"
        for fact in canonical_facts["public_exports"]
    )
    assert any(
        fact["identity"]["module"] == "os" for fact in canonical_facts["imports"]
    )
    assert any(
        fact["kind"] == "STATIC_CALLSITE_COUNTEREVIDENCE"
        and fact["identity"]["expression"] == "helper"
        and fact["runtime_reachability_proved"] is False
        for fact in canonical_facts["callers_references"]
    )
    comparison = payload["comparisons"][0]["families"]
    assert comparison["assignments_constants"]["classification"] == "CONFLICTING"
    assert comparison["public_exports"]["donor_only"]
    assert payload["claims"]["no_feature_loss"] is False
    assert payload["claims"]["runtime_reachability_proved"] is False


def test_static_fact_map_preserves_dynamic_uncertainty(tmp_path: Path) -> None:
    canonical, donor, _runtime = _related_repositories(tmp_path)
    predecessor = _m69_predecessor(canonical, donor, tmp_path / "m69")
    (canonical / "src/tool.py").write_text(
        "import importlib\n__all__ = make_exports()\n"
        "VALUE = importlib.import_module('example')\n"
        "def use(obj):\n    return getattr(obj, 'value')\n",
        encoding="utf-8",
    )
    _commit(canonical, "dynamic uncertainty")

    payload = build_cross_worktree_static_fact_map(canonical, [donor], predecessor)
    unknown = {
        item["classification"] for item in payload["canonical_static_facts"]["unknowns"]
    }
    assert "UNSUPPORTED_DYNAMIC___ALL__" in unknown
    assert "UNSUPPORTED_DYNAMIC_OR_REFLECTIVE_CALL" in unknown


def test_static_writer_is_create_once_and_binds_m69(tmp_path: Path) -> None:
    canonical, donor, runtime = _related_repositories(tmp_path)
    predecessor = _m69_predecessor(canonical, donor, tmp_path / "m69")
    output = tmp_path / "m70"
    payload = write_cross_worktree_static_fact_map(
        canonical,
        [donor],
        predecessor,
        output,
        runtime_roots=[runtime],
    )
    machine = output / "static_divergence.json.gz"
    assert machine.is_file()
    restored = json.loads(gzip.decompress(machine.read_bytes()))
    validate_self_hash(restored)
    assert restored == payload
    assert (output / "STATIC_DIVERGENCE_REPORT.md").is_file()
    assert payload["predecessor_m69"]["rewritten"] is False
    with pytest.raises(DivergenceError, match="must not already exist"):
        write_cross_worktree_static_fact_map(canonical, [donor], predecessor, output)


def test_behavior_map_binds_structure_tests_entrypoints_and_history(
    tmp_path: Path,
) -> None:
    canonical, donor, runtime = _related_repositories(tmp_path)
    m69 = _m69_predecessor(canonical, donor, tmp_path / "m69")
    (canonical / "src/tool.py").write_text(
        "BASE = 1\n__all__ = ['shared']\n\n"
        "def helper(value: int) -> int:\n    return value + BASE\n\n"
        "def shared(value: int = 1) -> int:\n    return helper(value)\n",
        encoding="utf-8",
    )
    (canonical / "tests").mkdir()
    (canonical / "tests/test_tool.py").write_text(
        "from src.tool import shared\n\ndef test_shared():\n    assert shared() == 2\n",
        encoding="utf-8",
    )
    (canonical / "pyproject.toml").write_text(
        "[project]\nname = 'fixture'\nversion = '0.0.0'\n"
        "[project.scripts]\nfixture = 'src.tool:shared'\n",
        encoding="utf-8",
    )
    _commit(canonical, "canonical behavior")
    (donor / "src/tool.py").write_text(
        "BASE = 2\nEXTRA = 3\n__all__ = ['shared', 'extra']\n\n"
        "def helper(value: int) -> int:\n    return value * BASE\n\n"
        "def shared(value: str = '1') -> str:\n"
        "    return toolbox.helper(value)\n\n"
        "def extra() -> int:\n    return EXTRA\n",
        encoding="utf-8",
    )
    (donor / "tests").mkdir()
    (donor / "tests/test_tool.py").write_text(
        "from src.tool import extra, shared\n\n"
        "def test_shared():\n    assert shared() == 2\n\n"
        "def test_extra():\n    assert extra() == 3\n",
        encoding="utf-8",
    )
    (donor / "pyproject.toml").write_text(
        "[project]\nname = 'fixture'\nversion = '0.0.0'\n"
        "[project.scripts]\nfixture = 'src.tool:shared'\n",
        encoding="utf-8",
    )
    _commit(donor, "donor behavior")
    m70 = _m70_predecessor(canonical, donor, m69, tmp_path / "m70")

    payload = build_cross_worktree_behavior_map(
        canonical,
        [donor],
        m69,
        m70,
        runtime_roots=[runtime],
    )

    validate_self_hash(payload)
    validate_self_hash(payload["zero_mutation"])
    assert payload["counts"]["m70_review_clusters"] > 0
    assert payload["counts"]["catalog_tests_and_fixtures"] >= 3
    assert payload["counts"]["catalog_entrypoints"] >= 2
    assert payload["counts"]["catalog_history_summaries"] > 0
    actionable = [
        item["evidence"]
        for item in payload["evidence_sets"]
        if item["evidence"]["cluster"]["kind"]
        in {"CONFLICT_REVIEW", "DONOR_ONLY_FACT_REVIEW"}
    ]
    assert actionable
    assert any(
        evidence["counterevidence"]["symbol_structure_divergences"]
        for evidence in actionable
    )
    assert any(
        evidence["corroborating_evidence"]["donor_static_test_references"]
        for evidence in actionable
    )
    assert any(
        evidence["corroborating_evidence"]["donor_declared_entrypoints"]
        for evidence in actionable
    )
    assert payload["claims"]["behavioral_equivalence"] is False
    assert payload["claims"]["retirement_safety"] is False
    assert payload["zero_mutation"]["status"] == "PASS"


def test_behavior_map_preserves_dynamic_unknowns_compactly(tmp_path: Path) -> None:
    canonical, donor, _runtime = _related_repositories(tmp_path)
    m69 = _m69_predecessor(canonical, donor, tmp_path / "m69")
    (canonical / "src/tool.py").write_text(
        "import importlib\n__all__ = make_exports()\n"
        "VALUE = importlib.import_module('example')\n"
        "def use(obj):\n    return getattr(obj, 'value')\n",
        encoding="utf-8",
    )
    _commit(canonical, "dynamic canonical")
    (donor / "src/tool.py").write_text(
        "import importlib\n__all__ = make_exports()\n"
        "VALUE = importlib.import_module('other')\n"
        "def use(obj):\n    return getattr(obj, 'other')\n",
        encoding="utf-8",
    )
    _commit(donor, "dynamic donor")
    m70 = _m70_predecessor(canonical, donor, m69, tmp_path / "m70")

    payload = build_cross_worktree_behavior_map(canonical, [donor], m69, m70)

    unknown_sets = [
        item["evidence"]
        for item in payload["evidence_sets"]
        if item["evidence"]["cluster"]["kind"] == "UNSUPPORTED_OR_UNKNOWN_REVIEW"
    ]
    assert unknown_sets
    for evidence in unknown_sets:
        assert evidence["corroborating_evidence"]["exact_symbol_structures"] == []
        assert evidence["corroborating_evidence"]["donor_static_test_references"] == []
        assert evidence["corroborating_evidence"]["donor_git_path_lineage"] == []
        assert evidence["counterevidence"]["symbol_structure_divergences"] == []
        assert len(evidence["unknown"]) == 1
        assert evidence["subjects"]["unknown_record_count"] > 0


def test_behavior_writer_is_deterministic_create_once_and_drift_safe(
    tmp_path: Path,
) -> None:
    canonical, donor, runtime = _related_repositories(tmp_path)
    m69 = _m69_predecessor(canonical, donor, tmp_path / "m69")
    (donor / "src/tool.py").write_text(
        "BASE = 1\nEXTRA = 2\n\ndef shared():\n    return BASE\n\n"
        "def extra():\n    return EXTRA\n",
        encoding="utf-8",
    )
    _commit(donor, "donor facts")
    m70 = _m70_predecessor(canonical, donor, m69, tmp_path / "m70")
    output = tmp_path / "m71"

    payload = write_cross_worktree_behavior_map(
        canonical,
        [donor],
        m69,
        m70,
        output,
        runtime_roots=[runtime],
    )
    machine = output / "behavior_divergence.json.gz"
    compressed = machine.read_bytes()
    restored = json.loads(gzip.decompress(compressed))
    validate_self_hash(restored)
    assert restored == payload
    assert compressed[:2] == b"\x1f\x8b"
    assert int.from_bytes(compressed[4:8], "little") == 0
    assert len(compressed) < 100_000_000
    with pytest.raises(DivergenceError, match="must not already exist"):
        write_cross_worktree_behavior_map(canonical, [donor], m69, m70, output)

    (donor / "src/tool.py").write_text("DRIFT = True\n", encoding="utf-8")
    with pytest.raises(DivergenceError, match="donor drifted from exact M70"):
        build_cross_worktree_behavior_map(canonical, [donor], m69, m70)


V1_DERIVED_PAYLOAD_VERIFIER = """
SCHEMA_LINE = "=== GIGA DERIVED PAYLOAD v1 ==="
END_LINE = "=== END GIGA DERIVED PAYLOAD METADATA ==="
AUTHORITY_LINE = "authority: DERIVED_ONLY; this payload cannot override either canonical source"
CANONICAL_SOURCES = ("CHARTER.md", "CONTEXT.md")
PAYLOAD_STATUSES = {
    "deploy/claude_preferences.txt": "UNVERIFIED_REPASTE",
    "deploy/chatgpt_preferences.md": "UNVERIFIED_REPASTE",
    "deploy/v3_agent_payload.md": "STAGED_NOT_DEPLOYED",
}


def verify_derived_payloads():
    metadata_keys = (
        "canonical-source-sha256",
        "deployment-status",
        "body_sha256",
        "st_nlink",
        "symlink",
    )
    return {
        "schema": "giga.derived-agent-payload-verification.v1",
        "metadata_keys": metadata_keys,
    }
"""

V2_DERIVED_PAYLOAD_VERIFIER = """
SCHEMA_LINE = "=== GIGA DERIVED PAYLOAD v2 ==="
END_LINE = "=== END GIGA DERIVED PAYLOAD METADATA ==="
AUTHORITY_LINE = "authority: DERIVED_ONLY; this payload cannot override either canonical source"
CANONICAL_SOURCES = ("CHARTER.md", "CONTEXT.md")
PAYLOAD_STATUSES = {
    "deploy/claude_preferences.txt": "DEPLOYED",
    "deploy/chatgpt_preferences.md": "DEPLOYED",
    "deploy/v3_agent_payload.md": "STAGED_NOT_DEPLOYED",
}
UNVERIFIED_STATUSES = {
    "deploy/claude_preferences.txt": "UNVERIFIED_REPASTE",
    "deploy/chatgpt_preferences.md": "UNVERIFIED_REPASTE",
    "deploy/v3_agent_payload.md": "STAGED_NOT_DEPLOYED",
}
PAYLOAD_SPECS = {"claude": {"output": "deploy/claude_preferences.txt"}}
ACTIVATION_EVIDENCE_PATH = "deploy/activation_evidence.json"
ACTIVATION_SOURCE_COMMIT = "d4d0416650732331cdf98c216cf3fea6a9abd14a"


def _strict_object(pairs):
    return dict(pairs)


def _strict_json(raw):
    return _strict_object(tuple())


def render_derived_payloads():
    return {"canonical-source-sha256": "f" * 64, "deployment-status": "DEPLOYED"}


def _verify_activation_evidence():
    return {"schema": "giga.agent-payload-activation.v2"}


def verify_derived_payloads():
    marker_keys = ("body_sha256", "st_nlink", "symlink")
    return {
        "schema": "giga.derived-agent-payload-verification.v2",
        "marker_keys": marker_keys,
    }


def write_derived_payloads():
    return render_derived_payloads()


def main():
    return "--write"
"""


def _payload_lineage_repositories(
    tmp_path: Path,
) -> tuple[Path, list[Path], Path, Path, Path]:
    canonical = _repository(tmp_path / "canonical")
    (canonical / "src").mkdir()
    (canonical / "src/tool.py").write_text("def shared():\n    return 1\n")
    (canonical / "scripts").mkdir()
    (canonical / "scripts/verify_derived_agent_payloads.py").write_text(
        V1_DERIVED_PAYLOAD_VERIFIER,
        encoding="utf-8",
    )
    _commit(canonical, "v1 derived payload verifier")

    donor_v1 = tmp_path / "donor_v1"
    subprocess.run(
        ["/usr/bin/git", "clone", "-q", str(canonical), str(donor_v1)], check=True
    )
    _git(donor_v1, "config", "user.name", "Fixture")
    _git(donor_v1, "config", "user.email", "<redacted-email>")

    (canonical / "scripts/verify_derived_agent_payloads.py").write_text(
        V2_DERIVED_PAYLOAD_VERIFIER,
        encoding="utf-8",
    )
    (canonical / "deploy/templates").mkdir(parents=True)
    (canonical / "deploy").mkdir(exist_ok=True)
    (canonical / "capabilities/manifests").mkdir(parents=True)
    (canonical / "capabilities/receipts").mkdir(parents=True)
    (canonical / "deploy/activation_evidence.json").write_text(
        '{"schema":"giga.agent-payload-activation.v2","self_sha256":"x"}\n',
        encoding="utf-8",
    )
    (canonical / "capabilities/manifests/derived-agent-payloads.json").write_text(
        '{"schema":"giga.capability-adoption-manifest.v1","id":"derived-agent-payloads"}\n',
        encoding="utf-8",
    )
    (canonical / "capabilities/receipts/derived-agent-payloads.json").write_text(
        '{"schema":"giga.capability-liveness-receipt.v1","status":"PASS"}\n',
        encoding="utf-8",
    )
    (canonical / "deploy/claude_preferences.txt").write_text(
        "=== GIGA DERIVED PAYLOAD v2 ===\nbody\n",
        encoding="utf-8",
    )
    _commit(canonical, "v2 activation verifier")

    donor_current = tmp_path / "donor_current"
    subprocess.run(
        ["/usr/bin/git", "clone", "-q", str(canonical), str(donor_current)],
        check=True,
    )
    _git(donor_current, "config", "user.name", "Fixture")
    _git(donor_current, "config", "user.email", "<redacted-email>")

    donor_absent = tmp_path / "donor_absent"
    subprocess.run(
        ["/usr/bin/git", "clone", "-q", str(canonical), str(donor_absent)],
        check=True,
    )
    _git(donor_absent, "config", "user.name", "Fixture")
    _git(donor_absent, "config", "user.email", "<redacted-email>")
    (donor_absent / "scripts/verify_derived_agent_payloads.py").unlink()
    _commit(donor_absent, "remove verifier")

    donors = [donor_v1, donor_current, donor_absent]
    m69 = _m69_predecessor(canonical, donors[0], tmp_path / "m69_seed")
    m69_output = tmp_path / "m69_all"
    write_cross_worktree_identity_map(canonical, donors, m69_output)
    m69 = m69_output / "divergence.json"
    m70 = _m70_predecessor(canonical, donors[0], m69, tmp_path / "m70_seed")
    m70_output = tmp_path / "m70_all"
    write_cross_worktree_static_fact_map(canonical, donors, m69, m70_output)
    m70 = m70_output / "static_divergence.json.gz"
    m71_output = tmp_path / "m71_all"
    write_cross_worktree_behavior_map(canonical, donors, m69, m70, m71_output)
    m71 = m71_output / "behavior_divergence.json.gz"
    return canonical, donors, m69, m70, m71


def test_derived_payload_lineage_classifies_v1_current_and_absent(
    tmp_path: Path,
) -> None:
    canonical, donors, m69, m70, m71 = _payload_lineage_repositories(tmp_path)

    payload = build_derived_payload_verifier_lineage(
        canonical,
        donors,
        m69,
        m70,
        m71,
    )

    validate_self_hash(payload)
    validate_self_hash(payload["zero_mutation"])
    assert payload["schema"] == divergence.DERIVED_PAYLOAD_LINEAGE_SCHEMA
    assert payload["counts"]["historical_v1_variants"] == 1
    assert payload["counts"]["exact_current_canonical"] == 1
    assert payload["counts"]["absent_from_donor"] == 1
    assert payload["counts"]["m71_matching_verifier_evidence_sets"] > 0
    assert payload["claims"]["whole_donor_retirement"] is False
    assert payload["claims"]["no_feature_loss"] is False
    assert payload["claims"]["drop_in_v1_compatibility"] is False
    dispositions = {
        item["fact_id"]: item["classification"] for item in payload["fact_dispositions"]
    }
    assert (
        dispositions["derived-payload-v1-verifier-source"]
        == "SUPERSEDED_HISTORY_QUERYABLE"
    )
    v1 = next(
        item
        for item in payload["compatibility_matrix"]
        if item["classification"] == "HISTORICAL_V1_VARIANT"
    )
    assert v1["donor_slot"] == "donor-01"
    assert "donor_root" not in v1
    assert payload["canonical_candidate"]["slot"] == "canonical"
    assert "root" not in payload["canonical_candidate"]
    assert all("root" not in item for item in payload["donors"])
    assert all("root" not in item for item in payload["zero_mutation"]["repositories"])
    assert (
        v1["backward_compatibility"]["v1_output_schema_drop_in"]
        == "NO_CURRENT_VERIFIER_EMITS_V2"
    )
    assert v1["whole_donor_retirement_permitted"] is False


def _assert_no_m73_private_terms(text: str, terms: list[str]) -> None:
    forbidden = [
        *terms,
        "donor_v1",
        "donor_current",
        "donor_absent",
        "m69_all",
        "m70_all",
        "m71_all",
        "donor_root",
        '"root":',
        'path_hash_public": true',
        "path-derived",
    ]
    for term in forbidden:
        assert term not in text


def test_derived_payload_lineage_public_output_is_layout_independent_and_private(
    tmp_path: Path,
) -> None:
    first_layout = tmp_path / "alpha_private_operator_layout"
    first_layout.mkdir()
    canonical, donors, m69, m70, m71 = _payload_lineage_repositories(first_layout)
    second_layout = tmp_path / "beta_private_operator_layout"
    second_layout.mkdir()
    canonical_clone = _clone_repository(
        canonical, second_layout / "second_private_canonical_copy"
    )
    donor_clones = [
        _clone_repository(donor, second_layout / f"second_private_donor_copy_{index}")
        for index, donor in enumerate(donors, start=1)
    ]

    first_payload = build_derived_payload_verifier_lineage(
        canonical,
        donors,
        m69,
        m70,
        m71,
    )
    second_payload = build_derived_payload_verifier_lineage(
        canonical_clone,
        donor_clones,
        m69,
        m70,
        m71,
    )

    assert first_payload == second_payload
    first_report = render_derived_payload_verifier_lineage_report(first_payload)
    second_report = render_derived_payload_verifier_lineage_report(second_payload)
    assert first_report == second_report
    serialized = (
        json.dumps(first_payload, sort_keys=True)
        + "\n"
        + first_report
        + "\n"
        + json.dumps(second_payload, sort_keys=True)
        + "\n"
        + second_report
    )
    _assert_no_m73_private_terms(
        serialized,
        [
            str(first_layout),
            str(second_layout),
            first_layout.name,
            second_layout.name,
            "second_private_canonical_copy",
            "second_private_donor_copy_1",
            "second_private_donor_copy_2",
            "second_private_donor_copy_3",
        ],
    )

    first_output = tmp_path / "m73_first_cli"
    second_output = tmp_path / "m73_second_cli"
    commands = []
    for root, donor_set, output in (
        (canonical, donors, first_output),
        (canonical_clone, donor_clones, second_output),
    ):
        commands.append(
            [
                sys.executable,
                "-m",
                "modules.operations.scripts.archaeology",
                "derived-payload-lineage",
                "--canonical",
                str(root),
                "--m69",
                str(m69),
                "--m70",
                str(m70),
                "--m71",
                str(m71),
                "--output",
                str(output),
                *[
                    argument
                    for donor in donor_set
                    for argument in ("--donor", str(donor))
                ],
            ]
        )
    first_result = subprocess.run(
        commands[0],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=True,
    )
    second_result = subprocess.run(
        commands[1],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=True,
    )
    assert first_result.stdout == second_result.stdout
    assert first_result.stderr == second_result.stderr == ""
    assert json.loads((first_output / "derived_payload_lineage.json").read_text()) == (
        json.loads((second_output / "derived_payload_lineage.json").read_text())
    )
    assert (first_output / "DERIVED_PAYLOAD_LINEAGE_REPORT.md").read_text(
        encoding="utf-8"
    ) == (second_output / "DERIVED_PAYLOAD_LINEAGE_REPORT.md").read_text(
        encoding="utf-8"
    )
    _assert_no_m73_private_terms(
        first_result.stdout
        + second_result.stdout
        + (first_output / "derived_payload_lineage.json").read_text(encoding="utf-8")
        + (first_output / "DERIVED_PAYLOAD_LINEAGE_REPORT.md").read_text(
            encoding="utf-8"
        ),
        [
            str(first_layout),
            str(second_layout),
            first_layout.name,
            second_layout.name,
            "second_private_canonical_copy",
        ],
    )


def test_derived_payload_lineage_cli_refuses_private_missing_paths_generically(
    tmp_path: Path,
) -> None:
    canonical, donors, m69, m70, m71 = _payload_lineage_repositories(tmp_path)
    missing_a = tmp_path / "alpha_private_missing_root" / "candidate"
    missing_b = tmp_path / "beta_private_missing_root" / "candidate"
    results = []
    for missing, output in (
        (missing_a, tmp_path / "missing_a_output"),
        (missing_b, tmp_path / "missing_b_output"),
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "modules.operations.scripts.archaeology",
                "derived-payload-lineage",
                "--canonical",
                str(missing),
                "--m69",
                str(m69),
                "--m70",
                str(m70),
                "--m71",
                str(m71),
                "--output",
                str(output),
                *[argument for donor in donors for argument in ("--donor", str(donor))],
            ],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
        results.append(result)

    assert [result.returncode for result in results] == [2, 2]
    assert results[0].stdout == results[1].stdout == ""
    assert results[0].stderr == results[1].stderr
    refusal = json.loads(results[0].stderr)
    assert refusal == {
        "reason": "DERIVED_PAYLOAD_LINEAGE_INPUT_UNAVAILABLE_OR_INVALID",
        "status": "REFUSED",
    }
    _assert_no_m73_private_terms(
        results[0].stderr + results[1].stderr,
        [
            str(missing_a),
            str(missing_b),
            missing_a.parent.name,
            missing_b.parent.name,
            missing_a.name,
            missing_b.name,
        ],
    )


def test_derived_payload_lineage_writer_and_cli_are_create_once(
    tmp_path: Path,
) -> None:
    canonical, donors, m69, m70, m71 = _payload_lineage_repositories(tmp_path)
    output = tmp_path / "m73"

    payload = write_derived_payload_verifier_lineage(
        canonical,
        donors,
        m69,
        m70,
        m71,
        output,
    )

    machine = output / "derived_payload_lineage.json"
    restored = json.loads(machine.read_text(encoding="utf-8"))
    validate_self_hash(restored)
    assert restored == payload
    assert (output / "DERIVED_PAYLOAD_LINEAGE_REPORT.md").is_file()
    with pytest.raises(DivergenceError, match="must not already exist"):
        write_derived_payload_verifier_lineage(canonical, donors, m69, m70, m71, output)

    cli_output = tmp_path / "m73_cli"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.operations.scripts.archaeology",
            "derived-payload-lineage",
            "--canonical",
            str(canonical),
            "--m69",
            str(m69),
            "--m70",
            str(m70),
            "--m71",
            str(m71),
            "--output",
            str(cli_output),
            *[argument for donor in donors for argument in ("--donor", str(donor))],
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=True,
    )
    summary = json.loads(result.stdout)
    assert summary["status"] == "PARTIAL_FACT_LEVEL_DISPOSITION"
    assert (cli_output / "derived_payload_lineage.json").is_file()


def _m76_write_old_surface(root: Path, exports: tuple[str, ...]) -> None:
    package = root / "modules/operations/archaeologist"
    package.mkdir(parents=True, exist_ok=True)
    imports = ["from .tool import shared, changed"]
    if "extra" in exports:
        imports.append("from .extra import extra")
        (package / "extra.py").write_text(
            "def extra():\n    return 3\n", encoding="utf-8"
        )
    (package / "tool.py").write_text(
        "def shared():\n    return 1\n\ndef changed():\n    return 1\n",
        encoding="utf-8",
    )
    (package / "__init__.py").write_text(
        "\n".join(imports) + "\n\n__all__ = " + repr(list(exports)) + "\n",
        encoding="utf-8",
    )


def _m76_write_current_surface(
    root: Path,
    *,
    exports: tuple[str, ...] = ("shared", "changed", "extra"),
    changed_module: str = "tool",
) -> None:
    canonical_package = root / "modules/operations/archaeology"
    legacy_package = root / "modules/operations/archaeologist"
    canonical_package.mkdir(parents=True, exist_ok=True)
    legacy_package.mkdir(parents=True, exist_ok=True)
    (canonical_package / "tool.py").write_text(
        "def shared():\n    return 1\n\ndef changed():\n    return 2\n",
        encoding="utf-8",
    )
    (canonical_package / "alternate.py").write_text(
        "def changed():\n    return 2\n", encoding="utf-8"
    )
    (canonical_package / "extra.py").write_text(
        "def extra():\n    return 3\n", encoding="utf-8"
    )
    changed_import = (
        "from .alternate import changed"
        if changed_module == "alternate"
        else "from .tool import shared, changed"
    )
    imports = [changed_import] if changed_module == "alternate" else [changed_import]
    if changed_module == "alternate":
        imports.insert(0, "from .tool import shared")
    if "extra" in exports:
        imports.append("from .extra import extra")
    (canonical_package / "__init__.py").write_text(
        "\n".join(imports) + "\n\n__all__ = " + repr(list(exports)) + "\n",
        encoding="utf-8",
    )
    (legacy_package / "__init__.py").write_text(
        '"""Compatibility bridge."""\n\n'
        "from __future__ import annotations\n\n"
        "import importlib\n"
        "import sys\n\n"
        '_CANONICAL_PACKAGE = "modules.operations.archaeology"\n'
        "_SUBMODULES = ('tool', 'alternate', 'extra')\n"
        "_canonical = importlib.import_module(_CANONICAL_PACKAGE)\n"
        "for _name in _SUBMODULES:\n"
        "    _module = importlib.import_module(f'{_CANONICAL_PACKAGE}.{_name}')\n"
        "    globals()[_name] = _module\n"
        "    sys.modules[f'{__name__}.{_name}'] = _module\n"
        "for _name in _canonical.__all__:\n"
        "    globals()[_name] = getattr(_canonical, _name)\n"
        "__all__ = tuple(_canonical.__all__)\n",
        encoding="utf-8",
    )


def _m76_export_surface_repositories(
    tmp_path: Path,
    *,
    current_exports: tuple[str, ...] = ("shared", "changed", "extra"),
    changed_module: str = "tool",
) -> tuple[Path, Path, Path, Path, Path, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    canonical = _repository(tmp_path / "canonical")
    _m76_write_old_surface(canonical, ("shared", "changed"))
    _commit(canonical, "base old surface")
    donor = _clone_repository(canonical, tmp_path / "donor")

    _m76_write_old_surface(canonical, ("shared", "changed", "extra"))
    _commit(canonical, "old surface conflict")
    evidence = {
        "subjects": {
            "subject_names": ["__all__"],
            "subject_fact_count": 2,
            "subject_fact_ids_sha256": sha256_bytes(
                canonical_bytes(["canonical-all", "donor-all"])
            ),
        }
    }
    evidence_set_id = sha256_bytes(canonical_bytes(evidence))
    cluster_id = sha256_bytes(canonical_bytes({"ordinal": 0, "subject": "__all__"}))
    zero = seal_document(
        {
            "schema": divergence.ZERO_MUTATION_SCHEMA,
            "status": "PASS",
            "authority_granted": False,
        }
    )
    m69_payload = seal_document(
        {
            "schema": divergence.DIVERGENCE_SCHEMA,
            "status": "PARTIAL_IDENTITY_LAYER",
            "authority_granted": False,
            "cleanup_permitted": False,
            "zero_mutation": zero,
        }
    )
    donor_snapshot = divergence._repository_snapshot(donor)
    m70_payload = seal_document(
        {
            "schema": divergence.STATIC_DIVERGENCE_SCHEMA,
            "status": "PARTIAL_STATIC_FACT_LAYER",
            "authority_granted": False,
            "cleanup_permitted": False,
            "zero_mutation": zero,
            "review_clusters": [
                {
                    "priority": 1,
                    "kind": "CONFLICT_REVIEW",
                    "family": "assignments_constants",
                    "donor_root": str(donor.resolve()),
                    "candidate_count": 1,
                }
            ],
            "donor_static_facts": [
                {"root": str(donor.resolve()), "repository": donor_snapshot}
            ],
        }
    )
    m71_payload = seal_document(
        {
            "schema": divergence.BEHAVIOR_DIVERGENCE_SCHEMA,
            "status": "PARTIAL_BEHAVIORAL_COUNTEREVIDENCE_LAYER",
            "authority_granted": False,
            "cleanup_permitted": False,
            "zero_mutation": zero,
            "cluster_bindings": [
                {
                    "cluster_id": cluster_id,
                    "m70_ordinal": 0,
                    "evidence_set_id": evidence_set_id,
                }
            ],
            "evidence_sets": [
                {
                    "evidence_set_id": evidence_set_id,
                    "evidence": evidence,
                    "evidence_sha256": sha256_bytes(canonical_bytes(evidence)),
                }
            ],
        }
    )
    m69_dir = tmp_path / "m69"
    m69_dir.mkdir()
    m69 = m69_dir / "divergence.json"
    m69.write_bytes(canonical_bytes(m69_payload))
    m70_dir = tmp_path / "m70"
    m70_dir.mkdir()
    m70 = m70_dir / "static_divergence.json.gz"
    m70.write_bytes(
        gzip.compress(canonical_bytes(m70_payload), compresslevel=9, mtime=0)
    )
    m71_dir = tmp_path / "m71"
    m71_dir.mkdir()
    m71 = m71_dir / "behavior_divergence.json.gz"
    m71.write_bytes(
        gzip.compress(canonical_bytes(m71_payload), compresslevel=9, mtime=0)
    )

    _m76_write_current_surface(
        canonical,
        exports=current_exports,
        changed_module=changed_module,
    )
    _commit(canonical, "renamed current surface")
    return canonical, donor, m69, m70, m71, evidence_set_id


def test_m76_export_surface_disposition_proves_subset_and_records_drift(
    tmp_path: Path,
) -> None:
    canonical, donor, m69, m70, m71, evidence_set_id = _m76_export_surface_repositories(
        tmp_path
    )
    before = _git(donor, "status", "--porcelain=v1", "--untracked-files=all")

    payload = divergence.build_m76_export_surface_disposition(
        canonical,
        donor,
        m69,
        m70,
        m71,
        evidence_set_id=evidence_set_id,
    )

    validate_self_hash(payload)
    validate_self_hash(payload["zero_mutation"])
    comparison = payload["public_surface_comparison"]
    assert payload["schema"] == divergence.EXPORT_SURFACE_DISPOSITION_SCHEMA
    assert payload["fact_disposition"]["classification"] == (
        "CANONICAL_STRICT_SUPERSET_SUPERSEDED_DONOR_SURFACE"
    )
    assert comparison["canonical_export_count"] == 3
    assert comparison["donor_export_count"] == 2
    assert comparison["missing_donor_export_count"] == 0
    assert comparison["canonical_extra_export_count"] == 1
    assert comparison["binding_target_match_count"] == 2
    assert comparison["implementation_exact_symbol_ast_count"] == 1
    assert comparison["implementation_drift_count"] == 1
    assert payload["claims"]["whole_file_equivalence"] is False
    assert payload["claims"]["whole_worktree_equivalence"] is False
    assert payload["claims"]["behavioral_equivalence"] is False
    assert _git(donor, "status", "--porcelain=v1", "--untracked-files=all") == before


def test_m76_export_surface_disposition_can_refuse_missing_and_conflicting_exports(
    tmp_path: Path,
) -> None:
    missing = _m76_export_surface_repositories(
        tmp_path / "missing", current_exports=("shared", "extra")
    )
    payload = divergence.build_m76_export_surface_disposition(
        *missing[:5], evidence_set_id=missing[5]
    )
    assert (
        payload["public_surface_comparison"]["classification"]
        == "CONFLICTING_DONOR_EXPORTS_MISSING_FROM_CANONICAL"
    )
    assert payload["claims"]["single_export_assignment_disposed"] is False

    conflict = _m76_export_surface_repositories(
        tmp_path / "conflict", changed_module="alternate"
    )
    payload = divergence.build_m76_export_surface_disposition(
        *conflict[:5], evidence_set_id=conflict[5]
    )
    assert (
        payload["public_surface_comparison"]["classification"]
        == "CANONICAL_EXPORT_SURFACE_PRESENT_WITH_BINDING_UNKNOWNS"
    )
    assert payload["claims"]["single_export_assignment_disposed"] is False


def _assert_no_m76_private_terms(text: str, terms: list[str]) -> None:
    forbidden = [
        *terms,
        "private_alpha",
        "private_beta",
        "donor_root",
        '"root":',
        "path-derived",
        'path_hash_public": true',
    ]
    for term in forbidden:
        assert term not in text


def test_m76_export_surface_output_is_layout_independent_and_pathless(
    tmp_path: Path,
) -> None:
    first = tmp_path / "private_alpha_layout"
    first.mkdir()
    canonical, donor, m69, m70, m71, evidence_set_id = _m76_export_surface_repositories(
        first
    )
    second = tmp_path / "private_beta_layout"
    second.mkdir()
    canonical_clone = _clone_repository(canonical, second / "second_canonical")
    donor_clone = _clone_repository(donor, second / "second_donor")

    first_payload = divergence.build_m76_export_surface_disposition(
        canonical, donor, m69, m70, m71, evidence_set_id=evidence_set_id
    )
    second_payload = divergence.build_m76_export_surface_disposition(
        canonical_clone,
        donor_clone,
        m69,
        m70,
        m71,
        evidence_set_id=evidence_set_id,
    )

    assert first_payload == second_payload
    first_report = divergence.render_m76_export_surface_disposition_report(
        first_payload
    )
    second_report = divergence.render_m76_export_surface_disposition_report(
        second_payload
    )
    assert first_report == second_report
    serialized = (
        json.dumps(first_payload, sort_keys=True)
        + "\n"
        + first_report
        + "\n"
        + json.dumps(second_payload, sort_keys=True)
        + "\n"
        + second_report
    )
    _assert_no_m76_private_terms(
        serialized,
        [
            str(first),
            str(second),
            first.name,
            second.name,
            "second_canonical",
            "second_donor",
        ],
    )


def test_m76_export_surface_refuses_private_missing_inputs_generically(
    tmp_path: Path,
) -> None:
    canonical, donor, m69, m70, m71, evidence_set_id = _m76_export_surface_repositories(
        tmp_path
    )
    missing_a = tmp_path / "private_alpha_missing" / "candidate"
    missing_b = tmp_path / "private_beta_missing" / "candidate"
    errors = []
    for missing in (missing_a, missing_b):
        with pytest.raises(DivergenceError) as exc:
            divergence.build_m76_export_surface_disposition(
                missing,
                donor,
                m69,
                m70,
                m71,
                evidence_set_id=evidence_set_id,
            )
        errors.append(str(exc.value))
    assert errors == [divergence.M76_REFUSAL, divergence.M76_REFUSAL]
    _assert_no_m76_private_terms(
        "\n".join(errors),
        [str(missing_a), str(missing_b), missing_a.parent.name, missing_b.parent.name],
    )
    assert _git(canonical, "status", "--porcelain=v1", "--untracked-files=all") == ""


def test_m76_export_surface_refuses_tampered_predecessor_and_writes_no_output(
    tmp_path: Path,
) -> None:
    canonical, donor, m69, m70, m71, evidence_set_id = _m76_export_surface_repositories(
        tmp_path
    )
    tampered = tmp_path / "tampered_m69.json"
    tampered.write_text(
        '{"schema":"x","schema":"y","receipt_sha256":"' + "0" * 64 + '"}\n',
        encoding="utf-8",
    )
    output = tmp_path / "should_not_exist"

    with pytest.raises(DivergenceError, match=divergence.M76_REFUSAL):
        divergence.write_m76_export_surface_disposition(
            canonical,
            donor,
            tampered,
            m70,
            m71,
            output,
            evidence_set_id=evidence_set_id,
        )

    assert not output.exists()


def _m77r2_cli_source(commands: tuple[str, ...]) -> str:
    parser_lines = [
        "def _parser():",
        "    parser = argparse.ArgumentParser(prog='fixture')",
        "    subcommands = parser.add_subparsers(dest='command', required=True)",
    ]
    main_lines = [
        "def main(argv=None):",
        "    args = _parser().parse_args(argv)",
    ]
    for command in commands:
        variable = command.replace("-", "_")
        parser_lines.extend(
            [
                f"    {variable} = subcommands.add_parser('{command}')",
                f"    {variable}.add_argument('--input')",
            ]
        )
        main_lines.extend(
            [
                f"    if args.command == '{command}':",
                f"        return run_{variable}()",
            ]
        )
    main_lines.append("    return 0")
    helpers = [
        f"def run_{command.replace('-', '_')}():\n    return 0"
        for command in commands
    ]
    return (
        "from __future__ import annotations\n\n"
        "import argparse\n\n"
        + "\n".join(parser_lines)
        + "\n\n"
        + "\n\n".join(helpers)
        + "\n\n"
        + "\n".join(main_lines)
        + "\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )


def _m77r2_write_wrapper(root: Path) -> None:
    script_dir = root / "modules/operations/scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "archaeologist.py").write_text(
        '"""Compatibility entrypoint."""\n\n'
        "from __future__ import annotations\n\n"
        "from modules.operations.scripts.archaeology import main\n\n"
        'if __name__ == "__main__":\n'
        "    raise SystemExit(main())\n",
        encoding="utf-8",
    )


def _m77r2_write_cli(root: Path, file_name: str, commands: tuple[str, ...]) -> None:
    script_dir = root / "modules/operations/scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / file_name).write_text(_m77r2_cli_source(commands), encoding="utf-8")


def _m77r2_predecessors(
    tmp_path: Path,
    canonical: Path,
    donors: tuple[Path, ...],
    *,
    include_absent_donor: bool = True,
) -> tuple[Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    zero = seal_document(
        {
            "schema": divergence.ZERO_MUTATION_SCHEMA,
            "status": "PASS",
            "authority_granted": False,
        }
    )
    donor_entries = []
    wrapper = canonical / "modules/operations/scripts/archaeologist.py"
    canonical_cli = canonical / "modules/operations/scripts/archaeology.py"
    wrapper_identity = {
        "sha256": sha256_bytes(wrapper.read_bytes()),
        "git_blob_oid": _git(
            canonical, "hash-object", "--", "modules/operations/scripts/archaeologist.py"
        ),
        "symbols": [],
    }
    canonical_cli_identity = {
        "sha256": sha256_bytes(canonical_cli.read_bytes()),
        "git_blob_oid": _git(
            canonical, "hash-object", "--", "modules/operations/scripts/archaeology.py"
        ),
        "symbols": ["function:_parser", "function:main"],
    }
    for donor in donors:
        donor_cli = donor / "modules/operations/scripts/archaeologist.py"
        donor_cli_identity = {
            "sha256": sha256_bytes(donor_cli.read_bytes()),
            "git_blob_oid": _git(
                donor, "hash-object", "--", "modules/operations/scripts/archaeologist.py"
            ),
            "symbols": ["function:_parser", "function:main"],
        }
        donor_entries.append(
            {
                "observation": {
                    "root": str(donor.resolve()),
                    "repository": divergence._repository_snapshot(donor),
                },
                "ancestry": {
                    "merge_base": _git(canonical, "rev-parse", "HEAD"),
                    "canonical_is_ancestor_of_donor": False,
                    "donor_is_ancestor_of_canonical": False,
                    "donor_unique_commit_count": 1,
                    "canonical_unique_commit_count": 1,
                    "samples_complete": True,
                },
                "path_comparisons": [
                    {
                        "path": "modules/operations/scripts/archaeologist.py",
                        "classification": "DONOR_STRICT_SYMBOL_SUPERSET",
                        "canonical": wrapper_identity,
                        "donor": donor_cli_identity,
                        "semantic_equivalence_claimed": False,
                        "usefulness_claimed": False,
                        "retirement_permitted": False,
                    },
                    {
                        "path": "modules/operations/scripts/archaeology.py",
                        "classification": "ABSENT_FROM_DONOR",
                        "canonical": canonical_cli_identity,
                        "donor": None,
                        "semantic_equivalence_claimed": False,
                        "usefulness_claimed": False,
                        "retirement_permitted": False,
                    },
                ],
            }
        )
    if include_absent_donor:
        absent = _clone_repository(canonical, tmp_path / "absent_donor")
        (absent / "modules/operations/scripts/archaeologist.py").unlink()
        _commit(absent, "remove old entrypoint")
        donor_entries.append(
            {
                "observation": {
                    "root": str(absent.resolve()),
                    "repository": divergence._repository_snapshot(absent),
                },
                "ancestry": {
                    "merge_base": _git(canonical, "rev-parse", "HEAD"),
                    "canonical_is_ancestor_of_donor": False,
                    "donor_is_ancestor_of_canonical": False,
                    "donor_unique_commit_count": 1,
                    "canonical_unique_commit_count": 1,
                    "samples_complete": True,
                },
                "path_comparisons": [
                    {
                        "path": "modules/operations/scripts/archaeologist.py",
                        "classification": "ABSENT_FROM_DONOR",
                        "canonical": wrapper_identity,
                        "donor": None,
                        "semantic_equivalence_claimed": False,
                        "usefulness_claimed": False,
                        "retirement_permitted": False,
                    },
                    {
                        "path": "modules/operations/scripts/archaeology.py",
                        "classification": "ABSENT_FROM_DONOR",
                        "canonical": canonical_cli_identity,
                        "donor": None,
                        "semantic_equivalence_claimed": False,
                        "usefulness_claimed": False,
                        "retirement_permitted": False,
                    },
                ],
            }
        )
    m69_payload = seal_document(
        {
            "schema": divergence.DIVERGENCE_SCHEMA,
            "status": "PARTIAL_IDENTITY_LAYER",
            "authority_granted": False,
            "cleanup_permitted": False,
            "zero_mutation": zero,
            "donors": donor_entries,
        }
    )
    m70_payload = seal_document(
        {
            "schema": divergence.STATIC_DIVERGENCE_SCHEMA,
            "status": "PARTIAL_STATIC_FACT_LAYER",
            "authority_granted": False,
            "cleanup_permitted": False,
            "zero_mutation": zero,
        }
    )
    m71_payload = seal_document(
        {
            "schema": divergence.BEHAVIOR_DIVERGENCE_SCHEMA,
            "status": "PARTIAL_BEHAVIORAL_COUNTEREVIDENCE_LAYER",
            "authority_granted": False,
            "cleanup_permitted": False,
            "zero_mutation": zero,
        }
    )
    m69 = tmp_path / "m69.json"
    m69.write_bytes(canonical_bytes(m69_payload))
    m70 = tmp_path / "m70.json.gz"
    m70.write_bytes(gzip.compress(canonical_bytes(m70_payload), compresslevel=9, mtime=0))
    m71 = tmp_path / "m71.json.gz"
    m71.write_bytes(gzip.compress(canonical_bytes(m71_payload), compresslevel=9, mtime=0))
    return m69, m70, m71


def _m77r2_repositories(
    tmp_path: Path,
    *,
    canonical_commands: tuple[str, ...] = ("inventory", "history", "extra"),
    donor_commands: tuple[str, ...] = ("inventory", "history"),
) -> tuple[Path, tuple[Path, ...], Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    canonical = _repository(tmp_path / "canonical")
    _m77r2_write_wrapper(canonical)
    _m77r2_write_cli(canonical, "archaeology.py", canonical_commands)
    _commit(canonical, "canonical cli")
    donor = _clone_repository(canonical, tmp_path / "donor")
    _m77r2_write_cli(donor, "archaeologist.py", donor_commands)
    (donor / "modules/operations/scripts/archaeology.py").unlink()
    _commit(donor, "old archaeologist cli")
    m69, m70, m71 = _m77r2_predecessors(tmp_path, canonical, (donor,))
    return canonical, (donor,), m69, m70, m71


def test_cli_donor_superset_disposition_proves_donor_commands_are_retained(
    tmp_path: Path,
) -> None:
    canonical, donors, m69, m70, m71 = _m77r2_repositories(tmp_path)
    before = _git(donors[0], "status", "--porcelain=v1", "--untracked-files=all")

    payload = divergence.build_cli_donor_superset_disposition(
        canonical, m69, m70, m71
    )

    validate_self_hash(payload)
    validate_self_hash(payload["zero_mutation"])
    assert payload["schema"] == divergence.CLI_DONOR_SUPERSET_DISPOSITION_SCHEMA
    assert payload["fact_disposition"]["classification"] == (
        "CANONICAL_ARCHAEOLOGY_CLI_RETAINS_ALL_M69_DONOR_STRICT_SYMBOL_SUPERSET_COMMANDS"
    )
    assert payload["summary"]["unique_donor_command_count"] == 2
    assert payload["summary"]["canonical_command_count"] == 3
    assert payload["summary"]["missing_command_count"] == 0
    assert payload["summary"]["missing_argument_tuple_count"] == 0
    assert payload["summary"]["missing_dispatch_call_count"] == 0
    assert payload["summary"]["source_integration_required"] is False
    assert payload["claims"]["whole_file_equivalence"] is False
    assert payload["claims"]["no_feature_loss"] is False
    assert _git(donors[0], "status", "--porcelain=v1", "--untracked-files=all") == before


def test_cli_donor_superset_disposition_records_missing_behaviour_without_overclaim(
    tmp_path: Path,
) -> None:
    canonical, _donors, m69, m70, m71 = _m77r2_repositories(
        tmp_path,
        canonical_commands=("inventory",),
        donor_commands=("inventory", "history"),
    )

    payload = divergence.build_cli_donor_superset_disposition(
        canonical, m69, m70, m71
    )

    assert payload["fact_disposition"]["classification"] == (
        "PARTIAL_OR_UNKNOWN_CLI_DONOR_SUPERSET_DISPOSITION"
    )
    assert payload["summary"]["missing_command_count"] == 1
    assert payload["summary"]["source_integration_required"] is True
    classifications = {
        row["classification"]
        for donor in payload["donors"]
        for row in donor["command_rows"]
    }
    assert "MIGRATE_USEFUL_OR_UNKNOWN_COMMAND_MISSING" in classifications
    assert payload["claims"]["cli_family_disposed"] is False


def _assert_no_cli_superset_private_terms(text: str, terms: list[str]) -> None:
    forbidden = [
        *terms,
        "private_alpha",
        "private_beta",
        "donor_root",
        '"root":',
        "path-derived",
        'path_hash_public": true',
    ]
    for term in forbidden:
        assert term not in text


def test_cli_donor_superset_output_is_path_safe_and_cli_writes_once(
    tmp_path: Path,
) -> None:
    private_alpha = tmp_path / "private_alpha_layout"
    canonical, _donors, m69, m70, m71 = _m77r2_repositories(private_alpha)
    output = tmp_path / "out"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "modules.operations.scripts.archaeology",
            "cli-superset-disposition",
            "--canonical",
            str(canonical),
            "--m69",
            str(m69),
            "--m70",
            str(m70),
            "--m71",
            str(m71),
            "--output",
            str(output),
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=True,
    )

    summary = json.loads(result.stdout)
    assert summary["status"] == "PARTIAL_FACT_LEVEL_DISPOSITION"
    restored = json.loads(
        (output / "cli_donor_superset_disposition.json").read_text(encoding="utf-8")
    )
    validate_self_hash(restored)
    validate_self_hash(restored["zero_mutation"])
    report = (output / "CLI_DONOR_SUPERSET_DISPOSITION_REPORT.md").read_text(
        encoding="utf-8"
    )
    _assert_no_cli_superset_private_terms(
        result.stdout + result.stderr + json.dumps(restored, sort_keys=True) + report,
        [
            str(private_alpha),
            str(canonical),
            private_alpha.name,
            "private_alpha_layout",
        ],
    )
    with pytest.raises(DivergenceError, match="must not exist"):
        divergence.write_cli_donor_superset_disposition(canonical, m69, m70, m71, output)


def test_cli_donor_superset_refuses_missing_and_tampered_inputs_generically(
    tmp_path: Path,
) -> None:
    canonical, _donors, m69, m70, m71 = _m77r2_repositories(tmp_path)
    tampered = tmp_path / "tampered.json"
    tampered.write_text(
        '{"schema":"x","schema":"y","receipt_sha256":"' + "0" * 64 + '"}\n',
        encoding="utf-8",
    )
    output = tmp_path / "should_not_exist"

    with pytest.raises(DivergenceError) as exc:
        divergence.write_cli_donor_superset_disposition(
            canonical, tampered, m70, m71, output
        )
    assert str(exc.value) == divergence.CLI_SUPERSET_REFUSAL
    assert not output.exists()

    missing_a = tmp_path / "private_alpha_missing" / "repo"
    missing_b = tmp_path / "private_beta_missing" / "repo"
    results = []
    for missing, out in ((missing_a, tmp_path / "a"), (missing_b, tmp_path / "b")):
        results.append(
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "modules.operations.scripts.archaeology",
                    "cli-superset-disposition",
                    "--canonical",
                    str(missing),
                    "--m69",
                    str(m69),
                    "--m70",
                    str(m70),
                    "--m71",
                    str(m71),
                    "--output",
                    str(out),
                ],
                cwd=Path.cwd(),
                text=True,
                capture_output=True,
                check=False,
            )
        )
    assert [result.returncode for result in results] == [2, 2]
    assert results[0].stdout == results[1].stdout == ""
    assert results[0].stderr == results[1].stderr
    assert json.loads(results[0].stderr) == {
        "reason": "CLI_DONOR_SUPERSET_INPUT_UNAVAILABLE_OR_INVALID",
        "status": "REFUSED",
    }
    _assert_no_cli_superset_private_terms(
        results[0].stderr + results[1].stderr,
        [
            str(missing_a),
            str(missing_b),
            missing_a.parent.name,
            missing_b.parent.name,
            missing_a.name,
            missing_b.name,
        ],
    )
