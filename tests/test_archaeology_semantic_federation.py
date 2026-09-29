from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from modules.operations.archaeology.dossier import build_context_projection
from modules.operations.archaeology.evidence import (
    canonical_bytes,
    validate_self_hash,
)
from modules.operations.archaeology.mapper import (
    MapperError,
    query_mapper,
    refresh_mapper,
)
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)
from modules.operations.archaeology.semantic_graph import (
    GraphifyConfig,
    refresh_semantic_graph,
)


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


@pytest.fixture()
def semantic_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "src").mkdir()
    (root / "src/jaa.py").write_text(
        "def prepare_application():\n    return 'ready'\n", encoding="utf-8"
    )
    (root / "architecture").mkdir()
    (root / "architecture/JAA.md").write_text(
        "# JAA application preparation\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    inventory_store = tmp_path / "inventory"
    semantic_store = tmp_path / "semantic"
    mapper_store = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory_store)

    monkeypatch.setattr(
        "modules.operations.archaeology.semantic_graph._verify_local_model",
        lambda _config: {
            "endpoint": "http://127.0.0.1:1235/v1",
            "model": "fixture-model",
            "advertised_models_sha256": "a" * 64,
            "advertised_models_count": 1,
        },
    )

    def graphify(projection: Path, output: Path, _config, _home):
        target = output / "graphify-out"
        target.mkdir(parents=True, exist_ok=True)
        graph = {
            "nodes": [
                {
                    "id": "jaa-code",
                    "label": "JAA application preparation implementation",
                    "source_file": "src/jaa.py",
                    "source_location": "L1-L2",
                    "file_type": "code",
                },
                {
                    "id": "jaa-doc",
                    "label": "JAA application preparation decision",
                    "source_file": "architecture/JAA.md",
                    "source_location": "L1",
                    "file_type": "document",
                },
            ],
            "edges": [
                {
                    "source": "jaa-code",
                    "target": "jaa-doc",
                    "relation": "DOCUMENTED_BY",
                    "confidence": "EXTRACTED",
                    "source_file": "src/jaa.py",
                    "source_location": "L1",
                }
            ],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
        }
        (target / "graph.json").write_bytes(canonical_bytes(graph))
        (target / "manifest.json").write_bytes(canonical_bytes({"fixture": True}))
        return {
            "argv": ["fixture-graphify"],
            "stdout_sha256": "b" * 64,
            "stdout_bytes": 0,
            "stderr_sha256": "b" * 64,
            "stderr_bytes": 0,
            "exit_code": 0,
        }

    monkeypatch.setattr(
        "modules.operations.archaeology.semantic_graph._invoke_graphify", graphify
    )
    config = GraphifyConfig(
        python=Path(sys.executable),
        endpoint="http://127.0.0.1:1235/v1",
        model="fixture-model",
        max_new_documents=10,
    )
    refresh_semantic_graph(inventory_store, semantic_store, config)
    return root, inventory_store, semantic_store, mapper_store, config


def test_federated_semantic_query_retains_provenance_without_copying_graph_rows(
    semantic_fixture,
) -> None:
    _root, inventory_store, semantic_store, mapper_store, _config = semantic_fixture
    run = refresh_mapper(inventory_store, mapper_store, semantic_store=semantic_store)
    assert run.manifest["semantic_input"]["freshness"] == "CURRENT_INVENTORY_MATCH"
    assert run.manifest["counts"]["semantic_nodes_available"] == 2
    connection = sqlite3.connect(run.run_directory / "facts.sqlite3")
    try:
        assert (
            connection.execute(
                "SELECT count(*) FROM entities WHERE entity_kind='SEMANTIC_CONCEPT'"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()

    result = query_mapper(
        mapper_store,
        "JAA application preparation",
        maps=("semantic_graphify",),
    )
    validate_self_hash(result)
    assert result["authority_granted"] is False
    assert result["result_count"] == 2
    code = next(
        item for item in result["results"] if item["source"]["path"] == "src/jaa.py"
    )
    assert code["kind"] == "SEMANTIC_CONCEPT"
    assert code["truth_class"] == "INFERRED"
    assert code["source"]["source_location"] == "L1-L2"
    assert code["attributes"]["source_freshness"] == "CURRENT_SOURCE_MATCH"
    assert code["attributes"]["deterministic_fact_override"] is False
    assert code["facts"]["semantic_relations"][0]["relation"] == "DOCUMENTED_BY"
    assert code["facts"]["semantic_relations"][0]["semantic_confidence"] == "EXTRACTED"


def test_semantic_source_staleness_is_visible_and_store_advance_refuses(
    semantic_fixture,
) -> None:
    root, inventory_store, semantic_store, mapper_store, config = semantic_fixture
    refresh_mapper(inventory_store, mapper_store, semantic_store=semantic_store)
    (root / "src/jaa.py").write_text(
        "def prepare_application():\n    return 'changed'\n", encoding="utf-8"
    )
    refresh_navigation_inventory(root, inventory_store)
    stale = refresh_mapper(inventory_store, mapper_store, semantic_store=semantic_store)
    assert stale.manifest["semantic_input"]["freshness"] == "STALE_INVENTORY_MISMATCH"
    result = query_mapper(mapper_store, "JAA application", maps=("semantic_graphify",))
    code = next(
        item for item in result["results"] if item["source"]["path"] == "src/jaa.py"
    )
    assert code["attributes"]["source_freshness"] == "STALE_SOURCE_HASH"
    context = build_context_projection(
        mapper_store,
        "architecture",
        ("JAA application",),
        token_budget=512,
        allowed_source_paths={"src/jaa.py", "architecture/JAA.md"},
    )
    assert not any(
        item["kind"] == "SEMANTIC_CONCEPT" and item["source"]["path"] == "src/jaa.py"
        for item in context["entries"]
    )
    assert context["non_live_source_candidates_excluded"] >= 1

    refresh_semantic_graph(inventory_store, semantic_store, config)
    with pytest.raises(MapperError, match="advanced or drifted"):
        query_mapper(mapper_store, "JAA", maps=("semantic_graphify",))


def test_semantic_store_must_be_private_canonical_and_absence_is_partial(
    semantic_fixture, tmp_path: Path
) -> None:
    _root, inventory_store, semantic_store, mapper_store, _config = semantic_fixture
    without = refresh_mapper(inventory_store, mapper_store)
    result = query_mapper(mapper_store, "JAA", maps=("semantic_graphify",))
    assert without.manifest["semantic_input"] is None
    assert result["result_count"] == 0
    assert result["coverage"][0]["disposition"] == "PARTIAL"

    unsafe = tmp_path / "unsafe-semantic"
    os.chmod(semantic_store, 0o755)
    with pytest.raises(MapperError, match="canonical private directory"):
        refresh_mapper(inventory_store, unsafe, semantic_store=semantic_store)


def test_semantic_store_from_another_repository_is_refused(
    semantic_fixture, tmp_path: Path
) -> None:
    _root, _inventory, semantic_store, _mapper, _config = semantic_fixture
    other = tmp_path / "other-repository"
    other.mkdir()
    _git(other, "init", "-q")
    _git(other, "config", "user.name", "Fixture")
    _git(other, "config", "user.email", "<redacted-email>")
    (other / "src.py").write_text("value = 1\n", encoding="utf-8")
    _git(other, "add", ".")
    _git(other, "commit", "-qm", "other")
    other_inventory = tmp_path / "other-inventory"
    refresh_navigation_inventory(other, other_inventory)

    with pytest.raises(MapperError, match="different repository root"):
        refresh_mapper(
            other_inventory,
            tmp_path / "other-mapper",
            semantic_store=semantic_store,
        )
