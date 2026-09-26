from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

from modules.operations.archaeology.consultation import _preserved_inputs
from modules.operations.archaeology.consultation import consult_before_decision
from modules.operations.archaeology.evidence import validate_self_hash
from modules.operations.archaeology.mapper import refresh_mapper
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "src").mkdir()
    (root / "src/router.py").write_text(
        "class ArchitectureRouter:\n    pass\n", encoding="utf-8"
    )
    (root / "src/__pycache__").mkdir()
    (root / "src/__pycache__/ArchitectureRouter.cpython-314.pyc").write_bytes(
        b"generated ArchitectureRouter cache"
    )
    (root / "unrelated.txt").write_text("old\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def test_architecture_consultation_compiles_relevant_paths_and_stays_partial(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory_store)
    refresh_mapper(inventory_store, mapper_store)

    (root / "src/router.py").write_text(
        "class ArchitectureRouter:\n    mode = 'strict'\n", encoding="utf-8"
    )
    (root / "unrelated.txt").write_text("uncovered dirty file\n", encoding="utf-8")
    receipt_path = tmp_path / "receipts" / "architecture.json"
    receipt = consult_before_decision(
        root,
        inventory_store,
        mapper_store,
        task_id="ARCH-001",
        task_class="architecture",
        terms=("ArchitectureRouter",),
        receipt_path=receipt_path,
        relevant_paths=("src/router.py",),
    )

    validate_self_hash(receipt)
    assert receipt["status"] == "READY_FOR_BOUNDED_DECISION"
    assert receipt["refresh"]["mode"] == "RELEVANT_PATH_DELTA"
    assert receipt["refresh"]["inventory_status"] == "PARTIAL"
    assert receipt["refresh"]["mapper_status"] == "PARTIAL"
    assert receipt["refresh"]["mapper_reused_for_verified_paths"] is False
    assert "unrelated.txt" in receipt["refresh"]["uncovered_git_visible_paths"]
    assert receipt["claims"]["bounded_architectural_decision_ready"] is True
    assert receipt["claims"]["whole_folder_current"] is False
    assert receipt["claims"]["current_architecture_allowed"] is False
    assert receipt["claims"]["no_feature_loss_allowed"] is False
    assert receipt["schema"] == "giga.archaeology.architecture-consultation.v2"
    assert receipt["retrieval"] == {
        "mode": "RANKED_CONTEXT",
        "token_budget": 512,
        "entry_count": receipt["ranked_context"]["entry_count"],
        "consulted_source_count": len(receipt["consulted_sources"]),
    }
    assert receipt["ranked_context"]["budget"]["used"] <= 512
    assert all(item["inventory_live_match"] for item in receipt["consulted_sources"])
    assert not any(
        "__pycache__" in item["path"] for item in receipt["consulted_sources"]
    )
    assert not any(
        "__pycache__" in path for path in receipt["refresh"]["relevant_paths"]
    )
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600


def test_consultation_preserves_every_authenticated_mapper_input() -> None:
    previous = SimpleNamespace(
        manifest={
            "runtime_inputs": [{"path": "/private/runtime-registry.json"}],
            "semantic_input": {"store": "/private/semantic-store"},
            "scip_inputs": [
                {"manifest_path": "/private/scip/python/manifest.json"},
                {"manifest_path": "/private/scip/typescript/manifest.json"},
            ],
        }
    )
    runtime, semantic, scip = _preserved_inputs(previous)
    assert runtime == (Path("/private/runtime-registry.json"),)
    assert semantic == Path("/private/semantic-store")
    assert scip == (
        Path("/private/scip/python/manifest.json"),
        Path("/private/scip/typescript/manifest.json"),
    )


def test_exhaustive_consultation_performs_full_reconciliation(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory_store)
    refresh_mapper(inventory_store, mapper_store)
    receipt = consult_before_decision(
        root,
        inventory_store,
        mapper_store,
        task_id="ARCH-EXHAUSTIVE-001",
        task_class="architecture",
        terms=("ArchitectureRouter",),
        receipt_path=tmp_path / "receipts" / "exhaustive.json",
        exhaustive=True,
    )
    assert receipt["refresh"]["mode"] == "FULL_RECONCILIATION"
    assert receipt["refresh"]["inventory_status"] == "CURRENT"
    assert receipt["refresh"]["mapper_status"] == "CURRENT"
    # Exhaustive claims still depend on each map family's declared coverage;
    # a full filesystem scan alone cannot promote a partial static map.
    assert receipt["claims"]["whole_folder_current"] is False


def test_consultation_refreshes_only_ranked_context_sources(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    for index in range(20):
        (root / f"architecture-history-{index:02d}.md").write_text(
            f"ArchitectureRouter retrospective evidence {index}\n", encoding="utf-8"
        )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "historical evidence")
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory_store)
    refresh_mapper(inventory_store, mapper_store)

    receipt = consult_before_decision(
        root,
        inventory_store,
        mapper_store,
        task_id="ARCH-RANKED-001",
        task_class="architecture",
        terms=("ArchitectureRouter",),
        receipt_path=tmp_path / "receipts" / "ranked.json",
        relevant_paths=("src/router.py",),
    )

    assert receipt["status"] == "READY_FOR_BOUNDED_DECISION"
    assert receipt["retrieval"]["mode"] == "RANKED_CONTEXT"
    assert receipt["retrieval"]["consulted_source_count"] < 21
    assert {item["path"] for item in receipt["consulted_sources"]} == {"src/router.py"}
    assert receipt["consulted_sources"][0]["selection_basis"] == "RANKED_CONTEXT"


def test_explicit_relevant_path_is_verified_even_when_not_ranked(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory_store)
    refresh_mapper(inventory_store, mapper_store)

    receipt = consult_before_decision(
        root,
        inventory_store,
        mapper_store,
        task_id="ARCH-EXPLICIT-001",
        task_class="architecture",
        terms=("ArchitectureRouter",),
        receipt_path=tmp_path / "receipts" / "explicit.json",
        relevant_paths=("unrelated.txt",),
    )

    explicit = next(
        item for item in receipt["consulted_sources"] if item["path"] == "unrelated.txt"
    )
    assert explicit["inventory_live_match"] is True
    assert explicit["selection_basis"] == "EXPLICIT_RELEVANT_PATH"
    assert explicit["source_identity_sha256"]


def test_consultation_filters_ranked_paths_removed_by_a_rename(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory_store)
    refresh_mapper(inventory_store, mapper_store)

    (root / "src/router.py").rename(root / "src/architecture.py")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "rename canonical module")
    refresh_navigation_inventory(root, inventory_store)

    receipt = consult_before_decision(
        root,
        inventory_store,
        mapper_store,
        task_id="ARCH-RENAME-001",
        task_class="architecture",
        terms=("ArchitectureRouter",),
        receipt_path=tmp_path / "receipts" / "rename.json",
        relevant_paths=("src/architecture.py",),
    )

    assert receipt["status"] == "READY_FOR_BOUNDED_DECISION"
    consulted = {item["path"] for item in receipt["consulted_sources"]}
    assert consulted == {"src/architecture.py"}
    assert "src/router.py" not in receipt["ranked_context"]["context"]
    assert receipt["failures"] == []


def test_unchanged_relevant_paths_reuse_authenticated_inventory_and_mapper(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    inventory_store = tmp_path / "inventory"
    mapper_store = tmp_path / "mapper"
    inventory = refresh_navigation_inventory(root, inventory_store)
    mapper = refresh_mapper(inventory_store, mapper_store)
    (root / "unrelated.txt").write_text("uncovered dirty file\n", encoding="utf-8")

    receipt = consult_before_decision(
        root,
        inventory_store,
        mapper_store,
        task_id="ARCH-FAST-001",
        task_class="architecture",
        terms=("ArchitectureRouter",),
        receipt_path=tmp_path / "receipts" / "fast.json",
        relevant_paths=("src/router.py",),
    )

    assert receipt["status"] == "READY_FOR_BOUNDED_DECISION"
    assert receipt["refresh"]["inventory_run_id"] != inventory.manifest["run_id"]
    assert receipt["refresh"]["mapper_run_id"] == mapper.manifest["run_id"]
    assert receipt["refresh"]["mapper_inventory_run_id"] == inventory.manifest["run_id"]
    assert receipt["refresh"]["inventory_reused_current"] is False
    assert receipt["refresh"]["mapper_reused_for_verified_paths"] is True
    assert receipt["refresh"]["verified_reused_paths"] == ["src/router.py"]
    assert receipt["refresh"]["uncovered_git_visible_paths"] == ["unrelated.txt"]
    assert receipt["claims"]["whole_folder_current"] is False
