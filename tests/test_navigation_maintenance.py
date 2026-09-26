from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from modules.operations.archaeology.evidence import validate_self_hash
from modules.operations.archaeology.navigation_maintenance import (
    run_navigation_maintenance,
)
from modules.operations.archaeology.semantic_graph import GraphifyConfig
from modules.operations.archaeology.scip_map import ScipRefreshConfig, ScipStoreRun


def _graphify() -> GraphifyConfig:
    return GraphifyConfig(
        python=Path("/fixture/python"),
        endpoint="http://127.0.0.1:1235/v1",
        model="fixture-model",
        max_new_documents=0,
    )


def _scip(tmp_path: Path) -> ScipRefreshConfig:
    return ScipRefreshConfig(
        store=tmp_path / "scip",
        node=tmp_path / "node",
        python_indexer_entrypoint=tmp_path / "scip-python.js",
        python_package_json=tmp_path / "scip-python-package.json",
        typescript_indexer_entrypoint=tmp_path / "scip-typescript.js",
        typescript_package_json=tmp_path / "scip-typescript-package.json",
    )


def test_maintenance_composes_both_layers_and_seals_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    semantic_store = tmp_path / "semantic"

    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_navigation_inventory",
        lambda *_args: SimpleNamespace(
            manifest={
                "status": "CURRENT",
                "run_id": "inventory-run",
                "receipt_sha256": "a" * 64,
                "counts": {"files": 12},
            }
        ),
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance._ensure_model",
        lambda *_args: (None, None, None),
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_semantic_graph",
        lambda *_args: SimpleNamespace(
            manifest={
                "status": "PARTIAL",
                "run_id": "semantic-run",
                "receipt_sha256": "b" * 64,
                "graph": {"nodes": 30, "edges": 40},
            }
        ),
    )

    receipt = run_navigation_maintenance(
        root,
        tmp_path / "inventory",
        semantic_store,
        reason="test",
        graphify=_graphify(),
        model_server_executable=tmp_path / "server",
        model_path=tmp_path / "model",
    )
    validate_self_hash(receipt)
    assert receipt["status"] == "PASS"
    assert receipt["inventory"]["run_id"] == "inventory-run"
    assert receipt["semantic"]["run_id"] == "semantic-run"
    assert receipt["mapper"] is None
    assert receipt["retention"]["status"] == "PASS"
    assert receipt["retention"]["plan_status"] == "NO_ACTION"
    pointer = json.loads((semantic_store / "maintenance/CURRENT.json").read_text())
    validate_self_hash(pointer)
    assert pointer["maintenance_receipt_sha256"] == receipt["receipt_sha256"]


def test_maintenance_failure_is_receipted_and_non_blocking(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    def fail(*_args):
        raise RuntimeError("injected inventory failure")

    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_navigation_inventory",
        fail,
    )
    receipt = run_navigation_maintenance(
        root,
        tmp_path / "inventory",
        tmp_path / "semantic",
        reason="daily",
        graphify=_graphify(),
        model_server_executable=tmp_path / "server",
        model_path=tmp_path / "model",
    )
    validate_self_hash(receipt)
    assert receipt["status"] == "FAILED_NON_BLOCKING"
    assert receipt["error"]["type"] == "RuntimeError"
    assert receipt["retention"] == {
        "status": "SKIPPED_REFRESH_NOT_PUBLISHED",
        "reason": "retention runs only after authenticated inventory/mapper publication",
    }
    assert receipt["normal_engineering_blocked"] is False


def test_maintenance_refreshes_mapper_when_semantic_refresh_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    semantic_store = tmp_path / "semantic"

    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_navigation_inventory",
        lambda *_args: SimpleNamespace(
            manifest={
                "status": "CURRENT",
                "run_id": "inventory-run",
                "receipt_sha256": "a" * 64,
                "counts": {"files": 12},
            }
        ),
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance._ensure_model",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("model unavailable")),
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.mapper.refresh_mapper",
        lambda *_args, **_kwargs: SimpleNamespace(
            manifest={
                "status": "CURRENT",
                "run_id": "mapper-run",
                "receipt_sha256": "c" * 64,
                "inventory": {"run_id": "inventory-run"},
                "counts": {"entities": 20, "relations": 30},
            }
        ),
    )
    receipt = run_navigation_maintenance(
        root,
        tmp_path / "inventory",
        semantic_store,
        mapper_store=tmp_path / "mapper",
        reason="daily",
        graphify=_graphify(),
        model_server_executable=tmp_path / "server",
        model_path=tmp_path / "model",
    )
    validate_self_hash(receipt)
    assert receipt["status"] == "PARTIAL_NON_BLOCKING"
    assert receipt["semantic"] is None
    assert receipt["mapper"]["run_id"] == "mapper-run"
    assert receipt["errors"][0]["phase"] == "semantic"
    assert receipt["normal_engineering_blocked"] is False


def test_milestone_mode_uses_delta_and_skips_six_minute_semantic_lane(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    semantic_store = tmp_path / "semantic"
    calls = {"full": 0, "delta": 0, "semantic": 0}

    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_navigation_inventory",
        lambda *_args: calls.__setitem__("full", calls["full"] + 1),
    )

    def delta(*_args):
        calls["delta"] += 1
        return SimpleNamespace(
            manifest={
                "status": "PARTIAL",
                "run_id": "delta-run",
                "receipt_sha256": "d" * 64,
                "counts": {"files": 12},
            }
        )

    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_navigation_inventory_delta",
        delta,
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_semantic_graph",
        lambda *_args: calls.__setitem__("semantic", calls["semantic"] + 1),
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.mapper.refresh_mapper",
        lambda *_args, **_kwargs: SimpleNamespace(
            manifest={
                "status": "PARTIAL",
                "run_id": "mapper-delta",
                "receipt_sha256": "e" * 64,
                "inventory": {"run_id": "delta-run"},
                "counts": {"entities": 20, "relations": 30},
            }
        ),
    )
    receipt = run_navigation_maintenance(
        root,
        tmp_path / "inventory",
        semantic_store,
        mapper_store=tmp_path / "mapper",
        reason="post-commit-milestone",
        mode="delta",
        graphify=_graphify(),
        model_server_executable=tmp_path / "server",
        model_path=tmp_path / "model",
    )
    assert calls == {"full": 0, "delta": 1, "semantic": 0}
    assert receipt["status"] == "PASS"
    assert receipt["mode"] == "delta"
    assert receipt["inventory"]["status"] == "PARTIAL"
    assert receipt["semantic"]["status"] == "SKIPPED_FAST_DELTA"
    assert receipt["mapper"]["status"] == "PARTIAL"


def test_maintenance_refreshes_scip_before_mapper_and_binds_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    manifest_paths = (tmp_path / "scip/runs/scip-run/projects/python/manifest.json",)
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_navigation_inventory_delta",
        lambda *_args: SimpleNamespace(
            manifest={
                "status": "PARTIAL",
                "run_id": "inventory-run",
                "receipt_sha256": "a" * 64,
                "counts": {"files": 12},
            }
        ),
    )

    def refresh_scip(*_args, **_kwargs):
        calls["scip"] = True
        return ScipStoreRun(
            tmp_path / "scip",
            tmp_path / "scip/runs/scip-run",
            {
                "status": "OBSERVED_LOCAL_PRECISION_STORE",
                "run_id": "scip-run",
                "receipt_sha256": "b" * 64,
                "inventory": {"run_id": "inventory-run"},
                "indexes": [{"manifest_path": "projects/python/manifest.json"}],
                "counts": {
                    "indexes": 1,
                    "documents": 7,
                    "occurrences": 80,
                    "bytes": 900,
                },
            },
        )

    def refresh_mapper(*_args, **kwargs):
        assert calls["scip"] is True
        calls["mapper_scip_manifests"] = kwargs["scip_manifests"]
        return SimpleNamespace(
            manifest={
                "status": "PARTIAL",
                "run_id": "mapper-run",
                "receipt_sha256": "c" * 64,
                "inventory": {"run_id": "inventory-run"},
                "counts": {"entities": 20, "relations": 30},
            }
        )

    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_scip_store",
        refresh_scip,
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.mapper.refresh_mapper", refresh_mapper
    )
    receipt = run_navigation_maintenance(
        root,
        tmp_path / "inventory",
        tmp_path / "semantic",
        mapper_store=tmp_path / "mapper",
        scip=_scip(tmp_path),
        reason="post-commit-milestone",
        mode="delta",
        graphify=_graphify(),
        model_server_executable=tmp_path / "server",
        model_path=tmp_path / "model",
        retention_enabled=False,
    )

    assert receipt["status"] == "PASS"
    assert receipt["scip"] == {
        "status": "OBSERVED_LOCAL_PRECISION_STORE",
        "run_id": "scip-run",
        "receipt_sha256": "b" * 64,
        "inventory_run_id": "inventory-run",
        "catalog_inventory_run_id": "inventory-run",
        "inventory_binding_status": "EXACT_INVENTORY_RECEIPT",
        "indexes": 1,
        "documents": 7,
        "occurrences": 80,
        "bytes": 900,
        "excluded_files": 0,
    }
    assert calls["mapper_scip_manifests"] == manifest_paths


def test_maintenance_preserves_mapper_when_configured_scip_refresh_fails(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    mapper_called = False
    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_navigation_inventory_delta",
        lambda *_args: SimpleNamespace(
            manifest={
                "status": "PARTIAL",
                "run_id": "inventory-run",
                "receipt_sha256": "a" * 64,
                "counts": {"files": 12},
            }
        ),
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_maintenance.refresh_scip_store",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("injected SCIP refresh failure")
        ),
    )

    def refresh_mapper(*_args, **_kwargs):
        nonlocal mapper_called
        mapper_called = True

    monkeypatch.setattr(
        "modules.operations.archaeology.mapper.refresh_mapper", refresh_mapper
    )
    receipt = run_navigation_maintenance(
        root,
        tmp_path / "inventory",
        tmp_path / "semantic",
        mapper_store=tmp_path / "mapper",
        scip=_scip(tmp_path),
        reason="post-commit-milestone",
        mode="delta",
        graphify=_graphify(),
        model_server_executable=tmp_path / "server",
        model_path=tmp_path / "model",
    )

    assert receipt["status"] == "FAILED_NON_BLOCKING"
    assert receipt["error"]["phase"] == "scip"
    assert receipt["scip"] is None
    assert receipt["mapper"] is None
    assert mapper_called is False
    assert receipt["normal_engineering_blocked"] is False
