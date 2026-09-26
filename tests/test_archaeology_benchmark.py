from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from modules.operations.archaeology.benchmark import (
    BenchmarkError,
    run_context_benchmark,
    run_mapper_benchmark,
)
from modules.operations.archaeology.evidence import validate_self_hash
from modules.operations.archaeology.mapper import refresh_mapper
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "src/jaa").mkdir(parents=True)
    (root / "src/jaa/compiler.py").write_text(
        "def compile_documents():\n    return 'ready'\n", encoding="utf-8"
    )
    (root / "src/jaa/application_preparation.py").write_text(
        "from .compiler import compile_documents\n\n"
        "def prepare_application():\n    return compile_documents()\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir()
    (root / "tests/test_application_preparation.py").write_text(
        "def test_prepare_application():\n    assert True\n", encoding="utf-8"
    )
    (root / "unrelated.md").write_bytes(b"x" * 200_000)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    refresh_mapper(inventory, mapper)
    corpus = tmp_path / "corpus.json"
    corpus.write_text(
        json.dumps(
            {
                "schema": "giga.archaeologist.mapper-benchmark-corpus.v1",
                "corpus_id": "fixture-v1",
                "reviewed_at": "2026-08-30T00:00:00Z",
                "review_scope": "FULL_PATH_SET",
                "cases": [
                    {
                        "id": "application-preparation",
                        "question": "Find the implementation and test.",
                        "dossier": "implementation",
                        "terms": ["application_preparation"],
                        "expected_path_globs": [
                            "src/jaa/application_preparation.py",
                            "tests/test_application_preparation.py",
                        ],
                        "relevant_path_globs": [
                            "src/jaa/application_preparation.py",
                            "tests/test_application_preparation.py",
                        ],
                        "min_precision_basis_points": 10000,
                        "min_recall_basis_points": 10000,
                        "limit_per_term": 50,
                        "overall_limit": 100,
                        "include_semantic": False,
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return mapper, corpus


def _context_corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "context-corpus.json"
    corpus.write_text(
        json.dumps(
            {
                "schema": "giga.archaeologist.context-benchmark-corpus.v1",
                "corpus_id": "fixture-context-v1",
                "reviewed_at": "2026-08-30T00:00:00Z",
                "donor": {
                    "name": "Aider repo-map",
                    "url": "https://github.com/Aider-AI/aider/blob/main/aider/repomap.py",
                    "commit": "5dc9490bb35f9729ef2c95d00a19ccd30c26339c",
                    "reviewed_mechanisms": [
                        "definition-reference graph",
                        "personalized PageRank",
                        "fixed token budget",
                    ],
                },
                "cases": [
                    {
                        "id": "application-preparation-context",
                        "question": "Locate the implementation and its called compiler.",
                        "dossier": "implementation",
                        "terms": ["application_preparation"],
                        "token_budget": 1000,
                        "include_semantic": False,
                        "expected_anchors": [
                            {
                                "id": "implementation",
                                "path": "src/jaa/application_preparation.py",
                                "kind": "PYTHON_MODULE",
                                "qualified_name": "src.jaa.application_preparation",
                                "max_rank": 3,
                                "relationship_expanded": False,
                            },
                            {
                                "id": "compiler",
                                "path": "src/jaa/compiler.py",
                                "kind": "PYTHON_SYMBOL",
                                "qualified_name": "src.jaa.compiler.compile_documents",
                                "max_rank": 20,
                                "relationship_expanded": True,
                            },
                        ],
                        "relevant_path_globs": ["src/jaa/*.py", "tests/*.py"],
                        "min_anchor_recall_basis_points": 10000,
                        "min_precision_basis_points": 10000,
                        "min_relationship_anchor_count": 1,
                        "min_budget_utilization_basis_points": 0,
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return corpus


def test_benchmark_measures_recall_precision_and_token_reduction(
    tmp_path: Path,
) -> None:
    mapper, corpus = _fixture(tmp_path)
    result = run_mapper_benchmark(mapper, corpus)
    validate_self_hash(result)
    assert result["status"] == "PASS"
    case = result["cases"][0]
    assert case["precision_basis_points"] == 10000
    assert case["recall_basis_points"] == 10000
    assert case["estimated_token_reduction_basis_points"] > 0
    assert result["summary"]["broad_completeness_claimed"] is False
    assert result["authority_granted"] is False


def test_benchmark_reports_failed_reviewed_threshold_without_false_pass(
    tmp_path: Path,
) -> None:
    mapper, corpus = _fixture(tmp_path)
    payload = json.loads(corpus.read_text())
    payload["cases"][0]["expected_path_globs"].append("missing.py")
    corpus.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    result = run_mapper_benchmark(mapper, corpus)
    assert result["status"] == "PARTIAL"
    assert result["cases"][0]["status"] == "FAILED_REVIEWED_THRESHOLD"
    assert result["cases"][0]["recall_basis_points"] < 10000


def test_benchmark_refuses_open_or_duplicate_key_corpus(tmp_path: Path) -> None:
    mapper, corpus = _fixture(tmp_path)
    payload = json.loads(corpus.read_text())
    payload["unexpected"] = True
    corpus.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(BenchmarkError, match="root is not closed"):
        run_mapper_benchmark(mapper, corpus)

    corpus.write_text(
        '{"schema":"giga.archaeologist.mapper-benchmark-corpus.v1",'
        '"schema":"duplicate"}\n',
        encoding="utf-8",
    )
    with pytest.raises(BenchmarkError, match="duplicate benchmark key"):
        run_mapper_benchmark(mapper, corpus)


def test_context_benchmark_proves_rank_budget_and_relationship_expansion(
    tmp_path: Path,
) -> None:
    mapper, _ = _fixture(tmp_path)
    result = run_context_benchmark(mapper, _context_corpus(tmp_path))
    validate_self_hash(result)
    assert result["status"] == "PASS"
    case = result["cases"][0]
    assert case["anchor_recall_basis_points"] == 10000
    assert case["relevant_entry_precision_basis_points"] == 10000
    assert case["matched_relationship_anchor_count"] == 1
    assert case["deterministic_replay"] is True
    assert case["all_selected_entries_source_bound"] is True
    assert case["token_budget"]["used"] <= case["token_budget"]["requested"]
    assert result["summary"]["broad_completeness_claimed"] is False
    assert result["authority_granted"] is False


def test_context_benchmark_does_not_false_pass_missing_or_direct_only_anchor(
    tmp_path: Path,
) -> None:
    mapper, _ = _fixture(tmp_path)
    corpus = _context_corpus(tmp_path)
    payload = json.loads(corpus.read_text())
    payload["cases"][0]["expected_anchors"][1]["qualified_name"] = (
        "jaa.compiler.missing"
    )
    corpus.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    result = run_context_benchmark(mapper, corpus)
    assert result["status"] == "PARTIAL"
    assert result["cases"][0]["status"] == "FAILED_REVIEWED_THRESHOLD"
    assert result["cases"][0]["anchors"][1]["observed_rank"] is None

    payload = json.loads(_context_corpus(tmp_path).read_text())
    payload["cases"][0]["expected_anchors"][0]["relationship_expanded"] = True
    corpus.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    result = run_context_benchmark(mapper, corpus)
    assert result["status"] == "PARTIAL"
    assert result["cases"][0]["anchors"][0]["status"] == ("MISSING_OR_MISRANKED")


def test_context_benchmark_refuses_open_duplicate_or_unsafe_corpus(
    tmp_path: Path,
) -> None:
    mapper, _ = _fixture(tmp_path)
    corpus = _context_corpus(tmp_path)
    payload = json.loads(corpus.read_text())
    payload["unexpected"] = True
    corpus.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(BenchmarkError, match="root is not closed"):
        run_context_benchmark(mapper, corpus)

    corpus.write_text(
        '{"schema":"giga.archaeologist.context-benchmark-corpus.v1",'
        '"schema":"duplicate"}\n',
        encoding="utf-8",
    )
    with pytest.raises(BenchmarkError, match="duplicate benchmark key"):
        run_context_benchmark(mapper, corpus)

    corpus = _context_corpus(tmp_path)
    payload = json.loads(corpus.read_text())
    payload["cases"][0]["expected_anchors"][0]["path"] = "../escape.py"
    corpus.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(BenchmarkError, match="anchor path is unsafe"):
        run_context_benchmark(mapper, corpus)


def test_context_benchmark_cli_returns_the_same_closed_contract(
    tmp_path: Path,
) -> None:
    mapper, _ = _fixture(tmp_path)
    corpus = _context_corpus(tmp_path)
    command = [
        "python3",
        "-m",
        "modules.operations.scripts.archaeology",
        "mapper-context-benchmark",
        "--mapper-store",
        str(mapper),
        "--corpus",
        str(corpus),
    ]
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    payload = json.loads(result.stdout)
    validate_self_hash(payload)
    assert payload["schema"] == "giga.archaeologist.context-benchmark-result.v1"
    assert payload["status"] == "PASS"
    assert result.stderr == ""
