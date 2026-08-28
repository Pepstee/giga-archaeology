from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from modules.operations.archaeologist.evidence import validate_self_hash
from modules.operations.archaeologist.navigation_maintenance import run_navigation_maintenance
from modules.operations.archaeologist.semantic_graph import GraphifyConfig


def _graphify() -> GraphifyConfig:
    return GraphifyConfig(
        python=Path("/fixture/python"),
        endpoint="http://127.0.0.1:1235/v1",
        model="fixture-model",
        max_new_documents=0,
    )


def test_maintenance_composes_both_layers_and_seals_receipt(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "root"
    root.mkdir()
    semantic_store = tmp_path / "semantic"

    monkeypatch.setattr(
        "modules.operations.archaeologist.navigation_maintenance.refresh_navigation_inventory",
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
        "modules.operations.archaeologist.navigation_maintenance._ensure_model",
        lambda *_args: (None, None, None),
    )
    monkeypatch.setattr(
        "modules.operations.archaeologist.navigation_maintenance.refresh_semantic_graph",
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
    pointer = json.loads((semantic_store / "maintenance/CURRENT.json").read_text())
    validate_self_hash(pointer)
    assert pointer["maintenance_receipt_sha256"] == receipt["receipt_sha256"]


def test_maintenance_failure_is_receipted_and_non_blocking(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "root"
    root.mkdir()

    def fail(*_args):
        raise RuntimeError("injected inventory failure")

    monkeypatch.setattr(
        "modules.operations.archaeologist.navigation_maintenance.refresh_navigation_inventory",
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
    assert receipt["normal_engineering_blocked"] is False
