from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.operations.archaeology.evidence import (
    canonical_bytes,
    validate_self_hash,
)
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)
from modules.operations.archaeology.semantic_graph import (
    GraphifyConfig,
    SemanticGraphError,
    _invoke_graphify,
    _normalize_graph,
    archive_legacy_graph,
    _validate_graph,
    current_semantic_run,
    locate_semantic_graph,
    refresh_semantic_graph,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


@pytest.fixture()
def stores(tmp_path: Path, monkeypatch):
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "src").mkdir()
    (root / "src/app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (root / "contract.json").write_text('{"schema":"fixture.v1"}\n', encoding="utf-8")
    (root / "architecture").mkdir()
    (root / "architecture/OVERVIEW.md").write_text(
        "# Overview\n\nArchitecture.\n", encoding="utf-8"
    )
    (root / "modules").mkdir()
    (root / "modules/MODULE.md").write_text(
        "# Module\n\nModule notes.\n", encoding="utf-8"
    )
    (root / "NOTES.md").write_text("# Notes\n\nGeneral notes.\n", encoding="utf-8")
    (root / "memory").mkdir()
    (root / "memory/private.md").write_text("private detail\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    inventory_store = tmp_path / "inventory"
    semantic_store = tmp_path / "semantic"
    refresh_navigation_inventory(root, inventory_store)

    def local_model(_config):
        return {
            "endpoint": "http://127.0.0.1:1235/v1",
            "model": "fixture-model",
            "advertised_models_sha256": "a" * 64,
            "advertised_models_count": 1,
        }

    def graphify(projection: Path, output: Path, _config, _home):
        nodes = []
        for path in sorted(item for item in projection.rglob("*") if item.is_file()):
            relative = path.relative_to(projection).as_posix()
            nodes.append(
                {
                    "id": "node_" + relative.replace("/", "_").replace(".", "_"),
                    "label": path.name,
                    "source_file": relative,
                    "source_location": "L1",
                    "file_type": "code",
                }
            )
        target = output / "graphify-out"
        target.mkdir(parents=True, exist_ok=True)
        (target / "graph.json").write_bytes(
            canonical_bytes(
                {
                    "nodes": nodes,
                    "edges": [],
                    "hyperedges": [],
                    "input_tokens": 10,
                    "output_tokens": 20,
                }
            )
        )
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
        "modules.operations.archaeology.semantic_graph._verify_local_model",
        local_model,
    )
    monkeypatch.setattr(
        "modules.operations.archaeology.semantic_graph._invoke_graphify", graphify
    )
    return root, inventory_store, semantic_store


def _config(documents: int) -> GraphifyConfig:
    return GraphifyConfig(
        python=Path(sys.executable),
        endpoint="http://127.0.0.1:1235/v1",
        model="fixture-model",
        max_new_documents=documents,
    )


def test_structural_files_are_immediate_and_documents_expand_incrementally(
    stores,
) -> None:
    _root, inventory_store, semantic_store = stores
    first = refresh_semantic_graph(inventory_store, semantic_store, _config(1))
    validate_self_hash(first.manifest)
    assert first.manifest["status"] == "PARTIAL"
    assert first.manifest["coverage"]["structural_selected"] == 2
    assert first.manifest["coverage"]["documents_selected"] == 1
    assert first.manifest["coverage"]["documents_total"] == 3
    assert any(
        item["path"] == "architecture/OVERVIEW.md"
        for item in first.manifest["coverage"]["selected_files"]
    )
    second = refresh_semantic_graph(inventory_store, semantic_store, _config(1))
    assert second.manifest["coverage"]["documents_selected"] == 2
    assert second.manifest["scan"]["incremental_from"] == first.manifest["run_id"]
    third = refresh_semantic_graph(inventory_store, semantic_store, _config(10))
    assert third.manifest["status"] == "CURRENT"
    assert (
        third.manifest["coverage"]["selected"]
        == third.manifest["coverage"]["supported"]
    )


def test_projection_never_contains_inventory_excluded_private_content(stores) -> None:
    _root, inventory_store, semantic_store = stores
    run = refresh_semantic_graph(inventory_store, semantic_store, _config(10))
    selected = {item["path"] for item in run.manifest["coverage"]["selected_files"]}
    assert "memory/private.md" not in selected
    projection = semantic_store / "workspace" / "input"
    assert not (projection / "memory/private.md").exists()
    assert run.manifest["limits"]["sensitive_content_projected"] is False
    assert run.manifest["limits"]["external_provider_used"] is False


def test_no_change_increment_preserves_exact_graph_bytes(stores) -> None:
    _root, inventory_store, semantic_store = stores
    first = refresh_semantic_graph(inventory_store, semantic_store, _config(10))
    second = refresh_semantic_graph(inventory_store, semantic_store, _config(0))
    assert second.manifest["coverage"]["delta_files"] == 0
    assert second.manifest["graphify"]["execution"]["status"] == (
        "SKIPPED_NO_CHANGED_SUPPORTED_FILES"
    )
    assert second.manifest["graph"]["sha256"] == first.manifest["graph"]["sha256"]
    assert (
        second.manifest["graph"]["raw_sha256"] == first.manifest["graph"]["raw_sha256"]
    )


def test_current_graph_is_content_authenticated(stores) -> None:
    _root, inventory_store, semantic_store = stores
    run = refresh_semantic_graph(inventory_store, semantic_store, _config(1))
    assert current_semantic_run(semantic_store).manifest == run.manifest
    graph = run.run_directory / "graphify-out/graph.json"
    graph.write_bytes(graph.read_bytes() + b"tamper")
    with pytest.raises(SemanticGraphError, match="graph hash mismatch"):
        current_semantic_run(semantic_store)


def test_machine_locator_returns_closed_exact_source_locations(stores) -> None:
    _root, inventory_store, semantic_store = stores
    run = refresh_semantic_graph(inventory_store, semantic_store, _config(10))
    result = locate_semantic_graph(semantic_store, "app application")
    validate_self_hash(result)
    assert result["schema"] == "giga.navigation.semantic-locate-result.v1"
    assert result["graph"]["run_id"] == run.manifest["run_id"]
    app = next(item for item in result["nodes"] if item["source_file"] == "src/app.py")
    assert app["source_location"] == "L1"
    assert app["matched_terms"] == ["app"]
    assert set(app) == {
        "id",
        "label",
        "source_file",
        "source_location",
        "file_type",
        "score",
        "matched_terms",
    }


def test_failed_refresh_preserves_previous_current(stores, monkeypatch) -> None:
    _root, inventory_store, semantic_store = stores
    first = refresh_semantic_graph(inventory_store, semantic_store, _config(1))

    def fail(*_args, **_kwargs):
        raise SemanticGraphError("injected Graphify failure")

    monkeypatch.setattr(
        "modules.operations.archaeology.semantic_graph._invoke_graphify", fail
    )
    with pytest.raises(SemanticGraphError, match="injected"):
        refresh_semantic_graph(inventory_store, semantic_store, _config(1))
    assert (
        current_semantic_run(semantic_store).manifest["run_id"]
        == first.manifest["run_id"]
    )
    assert not list(semantic_store.glob(".staging-*"))
    failure_receipts = list((semantic_store / "failures").glob("*/failure.json"))
    assert len(failure_receipts) == 1
    validate_self_hash(json.loads(failure_receipts[0].read_text(encoding="utf-8")))


def test_graph_validation_rejects_unadmitted_and_impossible_sources(
    tmp_path: Path,
) -> None:
    graph = tmp_path / "graph.json"
    selected = {"safe.md": object()}
    graph.write_bytes(
        canonical_bytes(
            {
                "nodes": [
                    {
                        "id": "x",
                        "source_file": "private.md",
                        "source_location": "L1",
                    }
                ],
                "edges": [],
                "hyperedges": [],
            }
        )
    )
    with pytest.raises(SemanticGraphError, match="unadmitted"):
        _validate_graph(graph, selected, {"safe.md": 2})
    payload = json.loads(graph.read_text())
    payload["nodes"][0]["source_file"] = "safe.md"
    payload["nodes"][0]["source_location"] = "L3"
    graph.write_bytes(canonical_bytes(payload))
    with pytest.raises(SemanticGraphError, match="outside"):
        _validate_graph(graph, selected, {"safe.md": 2})


def test_graph_validation_allows_only_completely_unsourced_external_nodes(
    tmp_path: Path,
) -> None:
    graph = tmp_path / "graph.json"
    graph.write_bytes(
        canonical_bytes(
            {
                "nodes": [
                    {
                        "id": "external",
                        "source_file": "",
                        "source_location": "",
                    }
                ],
                "edges": [],
                "hyperedges": [],
            }
        )
    )
    _payload, counts = _validate_graph(graph, {}, {})
    assert counts["unsourced_external_nodes"] == 1
    payload = json.loads(graph.read_text())
    payload["nodes"][0]["source_location"] = "L1"
    graph.write_bytes(canonical_bytes(payload))
    with pytest.raises(SemanticGraphError, match="unsourced"):
        _validate_graph(graph, {}, {})


def test_selected_document_must_contribute_source_linked_graph_content(
    tmp_path: Path,
) -> None:
    graph = tmp_path / "graph.json"
    graph.write_bytes(
        canonical_bytes(
            {
                "nodes": [{"id": "external", "source_file": "", "source_location": ""}],
                "edges": [],
                "hyperedges": [],
            }
        )
    )
    selected = {"architecture/OVERVIEW.md": SimpleNamespace(suffix=".md")}
    with pytest.raises(SemanticGraphError, match="no source-linked content"):
        _validate_graph(graph, selected, {"architecture/OVERVIEW.md": 3})


def test_unextractable_document_is_recorded_without_blocking_next_document(
    stores, monkeypatch
) -> None:
    _root, inventory_store, semantic_store = stores

    def omit_documents(projection: Path, output: Path, _config, _home):
        nodes = []
        for path in sorted(item for item in projection.rglob("*") if item.is_file()):
            relative = path.relative_to(projection).as_posix()
            if path.suffix in {".py", ".json"}:
                nodes.append(
                    {
                        "id": "node_" + relative.replace("/", "_").replace(".", "_"),
                        "label": path.name,
                        "source_file": relative,
                        "source_location": "L1",
                        "file_type": "code",
                    }
                )
        target = output / "graphify-out"
        target.mkdir(parents=True, exist_ok=True)
        (target / "graph.json").write_bytes(
            canonical_bytes(
                {
                    "nodes": nodes,
                    "edges": [],
                    "hyperedges": [],
                    "input_tokens": 10,
                    "output_tokens": 20,
                }
            )
        )
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
        "modules.operations.archaeology.semantic_graph._invoke_graphify",
        omit_documents,
    )
    first = refresh_semantic_graph(inventory_store, semantic_store, _config(1))
    assert first.manifest["status"] == "PARTIAL"
    assert first.manifest["failures"] == [
        {
            "type": "NO_SOURCE_LINKED_CONTENT",
            "path": "architecture/OVERVIEW.md",
            "retry": "ON_CONTENT_CHANGE",
        }
    ]
    assert (
        current_semantic_run(semantic_store).manifest["run_id"]
        == first.manifest["run_id"]
    )

    second = refresh_semantic_graph(inventory_store, semantic_store, _config(1))
    assert second.manifest["coverage"]["documents_selected"] == 2
    assert [item["path"] for item in second.manifest["failures"]] == [
        "architecture/OVERVIEW.md",
        "modules/MODULE.md",
    ]


def test_duplicate_symbol_ids_are_source_scoped_without_guessing_edges(
    tmp_path: Path,
) -> None:
    projection = tmp_path / "input"
    projection.mkdir()
    (projection / "a.py").write_text("ValueError\n", encoding="utf-8")
    (projection / "b.py").write_text("ValueError\n", encoding="utf-8")
    raw = tmp_path / "graph.raw.json"
    graph = tmp_path / "graph.json"
    raw.write_bytes(
        canonical_bytes(
            {
                "nodes": [
                    {
                        "id": "valueerror",
                        "label": "ValueError",
                        "source_file": "a.py",
                        "source_location": "L1",
                    },
                    {
                        "id": "valueerror",
                        "label": "ValueError",
                        "source_file": "b.py",
                        "source_location": "L1",
                    },
                ],
                "edges": [
                    {
                        "source": "valueerror",
                        "target": "valueerror",
                        "source_file": "a.py",
                        "source_location": "L1",
                    },
                    {
                        "source": "valueerror",
                        "target": "valueerror",
                        "source_file": "missing.py",
                        "source_location": "L1",
                    },
                ],
                "hyperedges": [],
            }
        )
    )
    counts = _normalize_graph(raw, graph, projection)
    payload = json.loads(graph.read_text(encoding="utf-8"))
    assert len({node["id"] for node in payload["nodes"]}) == 2
    assert payload["edges"][0]["source"] == payload["edges"][0]["target"]
    assert counts["unresolved_edges_removed"] == 1


def test_malformed_document_path_location_is_repaired_only_from_unique_label(
    tmp_path: Path,
) -> None:
    projection = tmp_path / "input"
    source = projection / "architecture/snapshot.md"
    source.parent.mkdir(parents=True)
    source.write_text("Header\nHuman Readable Name\nFooter\n", encoding="utf-8")
    raw = tmp_path / "graph.raw.json"
    graph = tmp_path / "graph.json"
    raw.write_bytes(
        canonical_bytes(
            {
                "nodes": [
                    {
                        "id": "repaired",
                        "label": "Human Readable Name",
                        "source_file": "architecture/snapshot.md",
                        "source_location": "architecture/01_LIGHT_MAP.md",
                    },
                    {
                        "id": "dropped",
                        "label": "Missing label",
                        "source_file": "architecture/snapshot.md",
                        "source_location": "architecture/01_LIGHT_MAP.md",
                    },
                ],
                "edges": [
                    {
                        "source": "repaired",
                        "target": "repaired",
                        "relation": "mentions",
                        "source_file": "architecture/snapshot.md",
                        "source_location": "architecture/01_LIGHT_MAP.md",
                    }
                ],
                "hyperedges": [],
            }
        )
    )
    counts = _normalize_graph(raw, graph, projection)
    payload = json.loads(graph.read_text(encoding="utf-8"))
    assert payload["nodes"] == [
        {
            "id": "repaired",
            "label": "Human Readable Name",
            "source_file": "architecture/snapshot.md",
            "source_location": "L2",
        }
    ]
    assert payload["edges"] == []
    assert counts["malformed_locations_repaired"] == 1
    assert counts["malformed_nodes_removed"] == 1
    assert counts["unresolved_edges_removed"] == 1


def test_unique_label_recovery_never_reads_outside_projection(tmp_path: Path) -> None:
    projection = tmp_path / "input"
    projection.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("External Label\n", encoding="utf-8")
    raw = tmp_path / "graph.raw.json"
    graph = tmp_path / "graph.json"
    raw.write_bytes(
        canonical_bytes(
            {
                "nodes": [
                    {
                        "id": "outside",
                        "label": "External Label",
                        "source_file": "../outside.md",
                        "source_location": "not-a-line",
                    }
                ],
                "edges": [],
                "hyperedges": [],
            }
        )
    )
    counts = _normalize_graph(raw, graph, projection)
    assert json.loads(graph.read_text(encoding="utf-8"))["nodes"] == []
    assert counts["malformed_nodes_removed"] == 1


def test_abandoned_staging_is_preserved_before_next_refresh(stores) -> None:
    _root, inventory_store, semantic_store = stores
    stale = semantic_store / ".staging-interrupted"
    stale.mkdir(parents=True)
    semantic_store.chmod(0o700)
    (stale / "partial.txt").write_text("partial", encoding="utf-8")
    refresh_semantic_graph(inventory_store, semantic_store, _config(1))
    preserved = semantic_store / "failures/interrupted"
    assert (preserved / "partial.txt").read_text(encoding="utf-8") == "partial"
    receipt = json.loads((preserved / "failure.json").read_text(encoding="utf-8"))
    validate_self_hash(receipt)
    assert receipt["status"] == "FAILED_INTERRUPTED_NOT_CURRENT"


def test_graphify_timeout_kills_the_full_process_group(tmp_path: Path) -> None:
    executable = tmp_path / "fake-graphify"
    executable.write_text(
        "#!/bin/sh\n/bin/sleep 30 &\necho $! > child.pid\nwait\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    projection = tmp_path / "input"
    projection.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    config = GraphifyConfig(
        python=executable,
        endpoint="http://127.0.0.1:1235/v1",
        model="fixture-model",
        process_timeout_seconds=1,
    )
    with pytest.raises(SemanticGraphError, match="process budget"):
        _invoke_graphify(projection, output, config, tmp_path / "home")
    child_pid = int((tmp_path / "child.pid").read_text(encoding="utf-8"))
    for _ in range(20):
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        pytest.fail("Graphify timeout left a descendant process alive")


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1:1235/v1",
        "http://example.com:1235/v1",
        "http://127.0.0.1:1235/v2",
        "http://user@127.0.0.1:1235/v1",
        "http://127.0.0.1/v1",
    ],
)
def test_non_loopback_or_ambiguous_model_endpoints_refuse(endpoint: str) -> None:
    with pytest.raises(SemanticGraphError, match="endpoint"):
        GraphifyConfig(endpoint=endpoint)


def test_source_drift_refuses_before_graph_publication(stores) -> None:
    root, inventory_store, semantic_store = stores
    (root / "src/app.py").write_text("def changed():\n    return 2\n", encoding="utf-8")
    with pytest.raises(SemanticGraphError, match="drifted|hash"):
        refresh_semantic_graph(inventory_store, semantic_store, _config(1))
    assert not (semantic_store / "CURRENT.json").exists()


def test_legacy_graph_is_archived_and_replaced_recoverably(stores) -> None:
    _root, inventory_store, semantic_store = stores
    refresh_semantic_graph(inventory_store, semantic_store, _config(1))
    legacy = semantic_store.parent / "legacy-graphify-out"
    legacy.mkdir()
    (legacy / "graph.json").write_bytes(
        canonical_bytes({"nodes": [{"id": "old"}], "links": [{"source": "old"}]})
    )
    (legacy / "query.md").write_text("private historical query\n", encoding="utf-8")
    manifest = archive_legacy_graph(legacy, semantic_store)
    validate_self_hash(manifest)
    assert manifest["status"] == "STALE_ARCHIVED"
    assert manifest["legacy_counts"] == {"nodes": 1, "edges": 1}
    assert legacy.is_symlink()
    assert legacy.resolve() == semantic_store.resolve()
    archive = semantic_store / "legacy" / manifest["archive_id"]
    assert (archive / "content/query.md").read_text(encoding="utf-8") == (
        "private historical query\n"
    )
