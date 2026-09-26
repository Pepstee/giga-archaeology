from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.history import (
    HistoryError,
    collect_recent_lineage,
)
from modules.operations.archaeology.map_catalog import route_query_maps
from modules.operations.archaeology.mapper import query_mapper, refresh_mapper
from modules.operations.archaeology.navigation_inventory import (
    classify_navigation_role,
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
def lineage_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "src").mkdir()
    (root / "src/app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (root / ".github").mkdir()
    (root / ".github/CODEOWNERS").write_text(
        "# exact declaration only\nsrc/*.py @fixture-team\n", encoding="utf-8"
    )
    (root / "memory").mkdir()
    (root / "memory/CODEOWNERS").write_text("* private-owner\n", encoding="utf-8")
    (root / "proofs").mkdir()
    (root / "proofs/owner.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    (root / "capabilities/manifests").mkdir(parents=True)
    (root / "capabilities/manifests/fixture-capability.json").write_text(
        json.dumps(
            {
                "schema": "giga.capability-adoption-manifest.v1",
                "id": "fixture-capability",
                "owner": "fixture/team",
                "responsibility": "Maintain the fixture application.",
                "claim": "ADOPTED",
                "implementation_paths": ["src/app.py"],
                "configuration_paths": [".github/CODEOWNERS"],
                "proof_paths": ["proofs/owner.json"],
                "entrypoint": {
                    "argv": ["python3", "src/app.py"],
                    "working_directory": ".",
                },
                "trigger": {"kind": "manual", "identity": "fixture"},
                "authority": {
                    "capabilities": ["fixture.read"],
                    "privacy": "faceless",
                    "external_effects": False,
                    "vault_required": False,
                },
                "recovery": {
                    "status_argv": ["python3", "src/app.py"],
                    "reconcile_argv": [],
                    "disable_argv": [],
                },
                "liveness_receipt": "capabilities/receipts/fixture-capability.json",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "introduce app")
    (root / "src/app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
    _git(root, "add", "src/app.py")
    _git(root, "commit", "-qm", "change app")
    return root


def _compile(root: Path, tmp_path: Path):
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    return mapper, refresh_mapper(inventory, mapper)


def test_m08_recent_git_lineage_is_exact_and_bounded(
    lineage_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["git_commits_mapped"] == 2
    assert run.manifest["counts"]["git_lineage_summaries_mapped"] == 1
    assert run.manifest["counts"]["git_current_path_changes"] == 5
    result = query_mapper(mapper, "src/app.py", maps=("git_lineage",), fact_limit=20)
    path = next(item for item in result["results"] if item["kind"] == "OWNERSHIP_PATH")
    changes = [
        fact
        for fact in path["facts"]["relations"]
        if fact["predicate"] == "CHANGED_CURRENT_PATH"
    ]
    assert len(changes) == 2
    assert {fact["attributes"]["status"] for fact in changes} == {"A", "M"}
    assert (
        result["coverage"][0]["details"]["rename_detection"]
        == "OBSERVED_GIT_SIMILARITY_M50"
    )
    assert result["coverage"][0]["details"]["head_ancestry_complete"] is True
    assert result["coverage"][0]["details"]["head_ancestry_commits"] == 2
    assert (
        result["coverage"][0]["details"]["symbol_lineage"]
        == "EXACT_UNCHANGED_BLOB_RENAMES_ONLY"
    )
    assert (
        result["coverage"][0]["details"]["historical_source_content_persisted"] is False
    )
    assert (
        result["coverage"][0]["details"]["historical_rename_source_content_loaded"]
        is False
    )


def test_m60_default_lineage_reaches_beyond_old_fifty_commit_window(
    lineage_repository: Path,
) -> None:
    (lineage_repository / "src/old_lost.py").write_text(
        "def forgotten():\n    return True\n", encoding="utf-8"
    )
    _git(lineage_repository, "add", "src/old_lost.py")
    _git(lineage_repository, "commit", "-qm", "add old lost implementation")
    _git(lineage_repository, "rm", "src/old_lost.py")
    _git(lineage_repository, "commit", "-qm", "delete old lost implementation")
    for ordinal in range(51):
        _git(
            lineage_repository,
            "commit",
            "--allow-empty",
            "-qm",
            f"later milestone {ordinal:02d}",
        )
    head = _git(lineage_repository, "rev-parse", "HEAD")
    lineage = collect_recent_lineage(
        lineage_repository,
        head,
        ["src/app.py"],
        current_paths=["src/app.py"],
    )
    assert len(lineage["commits"]) == 55
    assert lineage["coverage"]["head_ancestry_complete"] is True
    assert lineage["coverage"]["head_ancestry_commits"] == 55
    assert lineage["coverage"]["history_commit_cap"] == 2048
    assert [item["path"] for item in lineage["deleted_paths"]] == ["src/old_lost.py"]

    capped = collect_recent_lineage(
        lineage_repository,
        head,
        ["src/app.py"],
        current_paths=["src/app.py"],
        max_commits=50,
    )
    assert capped["coverage"]["head_ancestry_complete"] is False
    assert capped["deleted_paths"] == []


def test_m58_git_rename_predecessor_retains_bounded_current_path_lineage(
    lineage_repository: Path, tmp_path: Path
) -> None:
    _git(lineage_repository, "mv", "src/app.py", "src/intermediate.py")
    _git(lineage_repository, "commit", "-qm", "rename app to intermediate")
    _git(lineage_repository, "mv", "src/intermediate.py", "src/service.py")
    _git(lineage_repository, "commit", "-qm", "rename intermediate to service")
    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["git_renames_mapped"] == 2
    assert run.manifest["counts"]["git_historical_paths_mapped"] == 2
    assert run.manifest["counts"]["git_exact_blob_rename_boundaries"] == 2
    assert run.manifest["counts"]["git_exact_historical_symbols_mapped"] == 2

    current = query_mapper(
        mapper, "src/service.py", maps=("git_lineage",), fact_limit=30
    )
    current_path = next(
        item
        for item in current["results"]
        if item["kind"] == "OWNERSHIP_PATH"
        and item["qualified_name"] == "src/service.py"
    )
    rename = next(
        fact
        for fact in current_path["facts"]["relations"]
        if fact["predicate"] == "RENAMED_PATH_TO"
    )
    assert rename["direction"] == "INCOMING"
    assert rename["truth_class"] == "OBSERVED"
    assert rename["attributes"]["similarity_percent"] == 100
    assert rename["attributes"]["canonicality_claimed"] is False
    assert rename["other"]["qualified_name"] == "src/intermediate.py"

    historical = query_mapper(
        mapper, "src/app.py", maps=("git_lineage",), fact_limit=30
    )
    old_path = next(
        item
        for item in historical["results"]
        if item["kind"] == "HISTORICAL_PATH" and item["qualified_name"] == "src/app.py"
    )
    predicates = {fact["predicate"] for fact in old_path["facts"]["relations"]}
    assert "RENAMED_PATH_TO" in predicates
    assert "HISTORICAL_PREDECESSOR_OF_CURRENT_PATH" in predicates
    assert "CHANGED_HISTORICAL_PATH" in predicates
    assert old_path["attributes"]["current_path"] == "src/service.py"
    assert old_path["attributes"]["canonicality_claimed"] is False
    direct_rename = next(
        fact
        for fact in old_path["facts"]["relations"]
        if fact["predicate"] == "RENAMED_PATH_TO"
    )
    assert direct_rename["other"]["qualified_name"] == "src/intermediate.py"
    historical_symbol = next(
        item
        for item in historical["results"]
        if item["kind"] == "HISTORICAL_SYMBOL_OCCURRENCE"
        and item["qualified_name"] == "src/app.py::main"
    )
    assert historical_symbol["truth_class"] == "PROVEN"
    assert historical_symbol["attributes"]["content_loaded_from_history"] is False
    assert historical_symbol["attributes"]["exact_blob_continuity"] is True
    assert historical_symbol["attributes"]["module_identity_claimed"] is False
    assert historical_symbol["attributes"]["semantic_identity_inferred"] is False
    continuity = next(
        fact
        for fact in historical_symbol["facts"]["relations"]
        if fact["predicate"] == "EXACT_BLOB_CONTINUITY_TO_CURRENT_SYMBOL"
    )
    assert continuity["other"]["kind"] == "PYTHON_SYMBOL"
    assert continuity["other"]["qualified_name"] == "src.service.main"


def test_m61_post_rename_change_refuses_historical_symbol_continuity(
    lineage_repository: Path, tmp_path: Path
) -> None:
    _git(lineage_repository, "mv", "src/app.py", "src/renamed.py")
    _git(lineage_repository, "commit", "-qm", "rename app")
    (lineage_repository / "src/renamed.py").write_text(
        "def main():\n    return 99\n", encoding="utf-8"
    )
    _git(lineage_repository, "add", "src/renamed.py")
    _git(lineage_repository, "commit", "-qm", "change renamed app")

    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["git_renames_mapped"] == 1
    assert run.manifest["counts"]["git_exact_blob_rename_boundaries"] == 0
    assert run.manifest["counts"]["git_exact_historical_symbols_mapped"] == 0
    historical = query_mapper(
        mapper, "src/app.py main", maps=("git_lineage",), fact_limit=30
    )
    assert not any(
        item["kind"] == "HISTORICAL_SYMBOL_OCCURRENCE" for item in historical["results"]
    )


def test_m61_rename_from_sensitive_path_exposes_no_history_or_symbol(
    lineage_repository: Path, tmp_path: Path
) -> None:
    (lineage_repository / "private").mkdir()
    (lineage_repository / "private/secret.py").write_text(
        "class SecretImplementation:\n    pass\n", encoding="utf-8"
    )
    _git(lineage_repository, "add", "private/secret.py")
    _git(lineage_repository, "commit", "-qm", "add private implementation")
    _git(lineage_repository, "mv", "private/secret.py", "src/public.py")
    _git(lineage_repository, "commit", "-qm", "publish implementation")

    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["git_renames_mapped"] == 0
    assert run.manifest["counts"]["git_exact_historical_symbols_mapped"] == 0
    result = query_mapper(
        mapper,
        "private secret SecretImplementation",
        maps=("git_lineage",),
        fact_limit=30,
    )
    assert result["results"] == []
    assert result["coverage"][0]["details"]["renames_skipped_sensitive"] == 1


def test_m59_deleted_path_tombstone_excludes_current_and_sensitive_paths(
    lineage_repository: Path, tmp_path: Path
) -> None:
    (lineage_repository / "private").mkdir()
    (lineage_repository / "src/lost.py").write_text(
        "def lost():\n    return 'recoverable'\n", encoding="utf-8"
    )
    (lineage_repository / "src/readded.py").write_text(
        "def current():\n    return True\n", encoding="utf-8"
    )
    (lineage_repository / "private/secret.py").write_text(
        "SECRET = 'not-for-the-map'\n", encoding="utf-8"
    )
    _git(lineage_repository, "add", ".")
    _git(lineage_repository, "commit", "-qm", "add historical candidates")
    _git(
        lineage_repository,
        "rm",
        "src/lost.py",
        "src/readded.py",
        "private/secret.py",
    )
    _git(lineage_repository, "commit", "-qm", "remove historical candidates")
    (lineage_repository / "src/readded.py").write_text(
        "def current():\n    return True\n", encoding="utf-8"
    )
    _git(lineage_repository, "add", "src/readded.py")
    _git(lineage_repository, "commit", "-qm", "restore current path")

    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["git_deleted_paths_mapped"] == 1
    assert run.manifest["counts"]["git_deletion_events_mapped"] == 1
    deleted = query_mapper(mapper, "src/lost.py", maps=("git_lineage",), fact_limit=30)
    tombstone = next(
        item
        for item in deleted["results"]
        if item["kind"] == "DELETED_PATH" and item["qualified_name"] == "src/lost.py"
    )
    assert tombstone["attributes"]["content_loaded"] is False
    assert tombstone["attributes"]["current_path"] is False
    assert tombstone["attributes"]["restoration_permitted"] is False
    assert len(tombstone["attributes"]["last_blob_oid"]) == 40
    deletion = next(
        fact
        for fact in tombstone["facts"]["relations"]
        if fact["predicate"] == "DELETED_HISTORICAL_PATH"
    )
    assert deletion["direction"] == "INCOMING"
    assert deletion["truth_class"] == "PROVEN"
    assert (
        deletion["attributes"]["last_blob_oid"]
        == tombstone["attributes"]["last_blob_oid"]
    )
    assert (
        query_mapper(mapper, "private/secret.py", maps=("git_lineage",))["results"]
        == []
    )
    readded = query_mapper(
        mapper, "src/readded.py", maps=("git_lineage",), fact_limit=30
    )
    assert not any(item["kind"] == "DELETED_PATH" for item in readded["results"])


def test_m62_deleted_python_blob_maps_declarations_without_persisting_body(
    lineage_repository: Path, tmp_path: Path
) -> None:
    (lineage_repository / "src/forgotten_engine.py").write_text(
        "class ForgottenEngine:\n"
        "    async def recover(self):\n"
        "        return 'body-only-secret-token'\n\n"
        "def helper():\n"
        "    return 7\n",
        encoding="utf-8",
    )
    _git(lineage_repository, "add", "src/forgotten_engine.py")
    _git(lineage_repository, "commit", "-qm", "add forgotten engine")
    _git(lineage_repository, "rm", "src/forgotten_engine.py")
    _git(lineage_repository, "commit", "-qm", "remove forgotten engine")

    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["git_deleted_paths_mapped"] == 1
    assert run.manifest["counts"]["git_deleted_python_declarations_mapped"] == 3
    results = [
        *query_mapper(mapper, "ForgottenEngine", maps=("git_lineage",), fact_limit=50)[
            "results"
        ],
        *query_mapper(mapper, "helper", maps=("git_lineage",), fact_limit=50)[
            "results"
        ],
    ]
    declarations = {
        item["qualified_name"]: item
        for item in results
        if item["kind"] == "DELETED_PYTHON_DECLARATION"
    }
    assert set(declarations) == {
        "src/forgotten_engine.py::ForgottenEngine",
        "src/forgotten_engine.py::ForgottenEngine.recover",
        "src/forgotten_engine.py::helper",
    }
    method = declarations["src/forgotten_engine.py::ForgottenEngine.recover"]
    assert method["truth_class"] == "PROVEN"
    assert method["attributes"]["symbol_kind"] == "ASYNC_METHOD"
    assert method["attributes"]["content_loaded_for_parse"] is True
    assert method["attributes"]["content_persisted"] is False
    assert method["attributes"]["body_persisted"] is False
    assert method["attributes"]["restoration_permitted"] is False
    assert len(method["attributes"]["historical_blob_oid"]) == 40
    assert (
        query_mapper(
            mapper,
            "body-only-secret-token",
            maps=("git_lineage",),
            fact_limit=50,
        )["results"]
        == []
    )

    generic = query_mapper(
        mapper,
        "deleted Python declaration",
        maps=("git_lineage",),
        fact_limit=50,
    )
    assert generic["results"][0]["kind"] == "GIT_LINEAGE_SUMMARY"
    summary = generic["results"][0]
    assert summary["attributes"]["deleted_python_declarations"] == 3
    assert summary["attributes"]["deleted_paths"] == 1
    assert summary["attributes"]["absence_claim_permitted"] is False
    assert summary["attributes"]["restoration_permitted"] is False
    assert summary["attributes"]["whole_history_claimed"] is False
    assert {
        item["qualified_name"]
        for item in generic["results"]
        if item["kind"] == "DELETED_PYTHON_DECLARATION"
    } == set(declarations)


def test_m64_generic_history_language_returns_bounded_summary_first(
    lineage_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(lineage_repository, tmp_path)
    for term in ("changed", "historical symbol", "symbol evolution"):
        routing = route_query_maps(term)
        result = query_mapper(
            mapper,
            term,
            maps=routing["selected_maps"],
            search_query=routing["search_query"],
            routing=routing,
            fact_limit=50,
        )
        assert result["results"][0]["kind"] == "GIT_LINEAGE_SUMMARY"
        summary = result["results"][0]
        assert (
            summary["attributes"]["head"] == run.manifest["repository"]["git"]["head"]
        )
        assert summary["attributes"]["commits"] == 2
        assert summary["attributes"]["absence_claim_permitted"] is False
        assert summary["attributes"]["whole_history_claimed"] is False
        assert summary["ranking"]["algorithm"] == "giga.map-aware-query-order.v2"


def test_m62_invalid_historical_python_is_skipped_without_false_declaration(
    lineage_repository: Path, tmp_path: Path
) -> None:
    (lineage_repository / "src/invalid_lost.py").write_bytes(
        b"def false_symbol(:\n    return 'must-not-surface'\n"
    )
    (lineage_repository / "src/oversized_lost.py").write_bytes(
        b"def hidden_oversized():\n    pass\n#" + b"x" * (1024 * 1024)
    )
    _git(
        lineage_repository,
        "add",
        "src/invalid_lost.py",
        "src/oversized_lost.py",
    )
    _git(lineage_repository, "commit", "-qm", "add refused historical Python")
    _git(
        lineage_repository,
        "rm",
        "src/invalid_lost.py",
        "src/oversized_lost.py",
    )
    _git(lineage_repository, "commit", "-qm", "remove refused historical Python")

    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["git_deleted_paths_mapped"] == 2
    assert run.manifest["counts"]["git_deleted_python_declarations_mapped"] == 0
    for term in ("false_symbol", "hidden_oversized", "must-not-surface"):
        result = query_mapper(mapper, term, maps=("git_lineage",), fact_limit=50)
        assert not any(
            item["kind"] == "DELETED_PYTHON_DECLARATION" for item in result["results"]
        )
    details = result["coverage"][0]["details"]
    assert details["historical_python_blobs_parsed"] == 0
    assert details["historical_python_blobs_skipped"] == 2


def test_m08_ownership_roles_and_codeowners_never_mint_canonicality(
    lineage_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["canonical_source_candidates"] == 1
    app = query_mapper(mapper, "src/app.py", maps=("ownership_canonicality",))
    path = next(item for item in app["results"] if item["kind"] == "OWNERSHIP_PATH")
    assert path["attributes"]["role"] == "CANONICAL_SOURCE_CANDIDATE"
    assert path["attributes"]["canonicality_claimed"] is False

    owners = query_mapper(mapper, "src/*.py", maps=("ownership_canonicality",))
    rule = next(item for item in owners["results"] if item["kind"] == "CODEOWNER_RULE")
    assert rule["attributes"]["owners"] == ["@fixture-team"]
    assert rule["attributes"]["resolution"] == "DECLARATION_ONLY"
    assert rule["attributes"]["canonicality_claimed"] is False
    assert owners["coverage"][0]["details"]["canonical_authority_inferred"] is False
    private = query_mapper(mapper, "private-owner", maps=("ownership_canonicality",))
    assert private["results"] == []


def test_m57_exact_duplicates_join_to_ownership_roles_without_minting_owner(
    lineage_repository: Path, tmp_path: Path
) -> None:
    (lineage_repository / "archive").mkdir()
    (lineage_repository / "archive/app.py").write_bytes(
        (lineage_repository / "src/app.py").read_bytes()
    )
    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["exact_content_ownership_variant_groups"] == 1
    assert run.manifest["counts"]["exact_content_ownership_variant_bindings"] == 2

    active = query_mapper(
        mapper, "src/app.py", maps=("ownership_canonicality",), fact_limit=30
    )
    active_path = next(
        item
        for item in active["results"]
        if item["kind"] == "OWNERSHIP_PATH" and item["qualified_name"] == "src/app.py"
    )
    active_variant = next(
        fact
        for fact in active_path["facts"]["relations"]
        if fact["predicate"] == "HAS_EXACT_CONTENT_OWNERSHIP_VARIANT"
    )
    assert active_variant["direction"] == "INCOMING"
    assert active_variant["attributes"] == {
        "canonicality_claimed": False,
        "cleanup_permitted": False,
        "deletion_permitted": False,
        "path_role": "CANONICAL_SOURCE_CANDIDATE",
        "path_role_basis": "tracked-source-in-closest-repository",
        "variant_class": "EXACT_CONTENT",
    }

    archived = query_mapper(
        mapper, "archive/app.py", maps=("ownership_canonicality",), fact_limit=30
    )
    archived_path = next(
        item
        for item in archived["results"]
        if item["kind"] == "OWNERSHIP_PATH"
        and item["qualified_name"] == "archive/app.py"
    )
    archived_variant = next(
        fact
        for fact in archived_path["facts"]["relations"]
        if fact["predicate"] == "HAS_EXACT_CONTENT_OWNERSHIP_VARIANT"
    )
    assert archived_variant["attributes"]["path_role"] == "HISTORICAL_OR_ARCHIVED_COPY"
    assert archived_variant["attributes"]["canonicality_claimed"] is False
    coverage = next(
        item
        for item in archived["coverage"]
        if item["fact_class"] == "PATH_ROLE_AND_DECLARED_CODEOWNER"
    )
    assert coverage["details"]["exact_content_variant_groups"] == 1


def test_capability_manifest_projects_declaration_only_owner_contract(
    lineage_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["capability_owner_contracts"] == 1
    assert run.manifest["counts"]["capability_owner_contract_bindings"] == 3
    assert run.manifest["counts"]["capability_owner_contract_failures"] == 0
    result = query_mapper(
        mapper,
        "fixture-capability",
        maps=("ownership_canonicality",),
        fact_limit=30,
    )
    contract = next(
        item
        for item in result["results"]
        if item["kind"] == "CAPABILITY_OWNER_CONTRACT"
    )
    assert contract["attributes"]["owner"] == "fixture/team"
    assert (
        contract["attributes"]["validation"]
        == "CANONICAL_CAPABILITY_MANIFEST_VALIDATOR"
    )
    assert contract["attributes"]["declaration_only"] is True
    assert contract["attributes"]["canonicality_claimed"] is False
    assert contract["attributes"]["execution_authority_granted"] is False
    owner = query_mapper(
        mapper,
        "fixture/team",
        maps=("ownership_canonicality",),
        fact_limit=30,
    )
    declaration = next(
        item for item in owner["results"] if item["kind"] == "DECLARED_CAPABILITY_OWNER"
    )
    predicates = {fact["predicate"] for fact in declaration["facts"]["relations"]}
    assert "DECLARES_IMPLEMENTATION_RESPONSIBILITY_FOR" in predicates
    assert "DECLARES_CONFIGURATION_RESPONSIBILITY_FOR" in predicates
    assert "DECLARES_PROOF_RESPONSIBILITY_FOR" in predicates
    assert owner["coverage"][0]["details"]["canonical_authority_inferred"] is False


def test_invalid_capability_manifest_never_projects_owner_contract(
    lineage_repository: Path, tmp_path: Path
) -> None:
    manifest_path = (
        lineage_repository / "capabilities/manifests/fixture-capability.json"
    )
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    value["unknown"] = "forbidden"
    manifest_path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    mapper, run = _compile(lineage_repository, tmp_path)
    assert run.manifest["counts"]["capability_owner_contracts"] == 0
    assert run.manifest["counts"]["capability_owner_contract_failures"] == 1
    result = query_mapper(
        mapper, "fixture-capability", maps=("ownership_canonicality",)
    )
    assert not any(
        item["kind"] == "CAPABILITY_OWNER_CONTRACT" for item in result["results"]
    )
    contract_coverage = next(
        item
        for item in result["coverage"]
        if item["fact_class"] == "CAPABILITY_OWNER_CONTRACT_DECLARATION"
    )
    assert contract_coverage["disposition"] == "PARTIAL"
    assert contract_coverage["sources_failed"] == 1


def test_m08_lineage_refuses_head_drift_and_role_classifier_is_conservative(
    lineage_repository: Path,
) -> None:
    with pytest.raises(HistoryError, match="HEAD no longer matches"):
        collect_recent_lineage(lineage_repository, "0" * 40, ["src/app.py"])
    assert classify_navigation_role(
        "archive/old.py", repository_present=True, tracked=True
    ) == ("HISTORICAL_OR_ARCHIVED_COPY", "history-or-archive-path-component")
    assert classify_navigation_role(
        "src/app.py", repository_present=True, tracked=True
    ) == ("CANONICAL_SOURCE_CANDIDATE", "tracked-source-in-closest-repository")
