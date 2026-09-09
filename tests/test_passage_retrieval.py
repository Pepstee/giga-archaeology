from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import types
from pathlib import Path

import pytest

from twin_core.passage_retrieval import (
    Passage,
    PassageRetrievalError,
    _dense_ranking_sha256,
    _model_cache_manifest,
    bm25_rank,
    dense_cosine_rank,
    dense_ranking_from_batch,
    dense_rankings_from_batch,
    fastembed_dense_ranking_batch,
    index_archived_receipts,
    reciprocal_rank_fusion,
    retrieve_passages,
)
from twin_core.scientific_pipeline_cli import main
from twin_core.web_acquisition import (
    PublicWebAcquirer,
    WebResponse,
    load_archived_text,
)


class FakeTransport:
    name = "fake:static"

    def __init__(self, bodies: dict[str, str]) -> None:
        self.bodies = bodies

    def fetch(self, url: str, *, timeout_seconds: int) -> WebResponse:
        assert timeout_seconds == 30
        return WebResponse(
            url=url,
            status=200,
            headers={"content-type": "text/plain"},
            body=self.bodies[url].encode(),
            fetched_at="2026-08-30T08:00:00+00:00",
        )


def _public_resolver(host: str, port: int, *, type: int) -> list[tuple]:
    assert host and type == socket.SOCK_STREAM
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _archive(tmp_path: Path) -> tuple[Path, list[Path]]:
    repository = tmp_path / "repository"
    repository.mkdir()
    archive = tmp_path / "archive"
    urls = {
        "https://example.com/en": (
            "Research systems verify every citation against an exact archived quote. "
            "Unrelated weather forecasts are not research evidence."
        ),
        "https://example.edu/zh": (
            "研究系统应验证每条引用并保留准确来源。天气预报与引用验证无关。"
        ),
    }
    acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=archive,
        transport=FakeTransport(urls),
        resolver=_public_resolver,
    )
    receipts = [acquirer.acquire(url).receipt_path for url in urls]
    return archive, receipts


def test_indexes_verified_archive_and_bm25_ranks_bilingual_passages(tmp_path: Path) -> None:
    archive, receipts = _archive(tmp_path)
    passages = index_archived_receipts(
        archive, receipts, maximum_characters=80, overlap_characters=10
    )
    english = bm25_rank("exact citation quote", passages)
    chinese = bm25_rank("验证引用 来源", passages)
    by_id = {passage.passage_id: passage for passage in passages}
    assert "exact archived quote" in by_id[english[0][0]].text
    assert "验证每条引用" in by_id[chinese[0][0]].text
    passage = by_id[english[0][0]]
    matching_receipt = next(path for path in receipts if path.stem == passage.receipt_sha256)
    _, _, archived_text = load_archived_text(matching_receipt, archive)
    assert passage.text == archived_text[passage.start : passage.end]


def test_retrieval_fuses_rankings_and_preserves_provenance(tmp_path: Path) -> None:
    archive, receipts = _archive(tmp_path)
    passages = index_archived_receipts(archive, receipts)
    lexical = bm25_rank("citation evidence", passages)
    dense = [passage.passage_id for passage in reversed(passages)]
    result = retrieve_passages(
        "citation evidence", passages, dense_ranking=dense, limit=2, per_source=2
    )
    assert result["rankers"] == ["bm25", "dense"]
    assert result["claim_authority"] is False
    assert len({row["receipt_sha256"] for row in result["results"]}) == 2
    assert result["selection_policy"] == (
        "boilerplate_weighted_relevance_with_source_round_robin"
    )
    assert result["results"][0]["receipt_sha256"]
    assert result["results"][0]["bm25_score"] == dict(lexical).get(
        result["results"][0]["passage_id"], 0.0
    )


def test_receipt_metadata_scope_filters_before_every_ranker_and_is_auditable(
    tmp_path: Path,
) -> None:
    archive, receipts = _archive(tmp_path)
    passages = index_archived_receipts(archive, receipts)
    scope = {
        "schema_version": "giga.research-receipt-metadata-scope.v1",
        "filters": {
            "source_hosts": ["example.com"],
            "content_types": ["TEXT/PLAIN"],
            "trust_classes": ["untrusted_external_source"],
            "source_kinds": ["public_web"],
        },
    }
    result = retrieve_passages(
        "citation evidence",
        passages,
        dense_ranking=[passage.passage_id for passage in reversed(passages)],
        metadata_scope=scope,
        limit=2,
        per_source=2,
    )

    assert result["schema_version"] == "giga.research-passage-retrieval.v2"
    assert result["selection_policy"].startswith("metadata_scoped_")
    assert result["indexed_passages"] == 2
    assert result["eligible_passages"] == 1
    assert result["rankers"] == ["bm25", "dense"]
    assert [row["receipt_metadata"]["source_host"] for row in result["results"]] == [
        "example.com"
    ]
    receipt = result["metadata_scope"]
    assert receipt["filters"]["content_types"] == ["text/plain"]
    assert receipt["indexed_receipt_count"] == 2
    assert receipt["eligible_receipt_count"] == 1
    assert receipt["excluded_receipt_count"] == 1
    assert receipt["eligible_passage_count"] == 1
    assert len(receipt["metadata_scope_sha256"]) == 64


def test_receipt_metadata_scope_rejects_unknown_or_unsafe_contracts() -> None:
    passages = [
        Passage("p", "a" * 64, "b" * 64, "https://example.com", 0, 4, "evidence")
    ]
    with pytest.raises(PassageRetrievalError, match="unexpected"):
        retrieve_passages(
            "evidence",
            passages,
            metadata_scope={
                "schema_version": "giga.research-receipt-metadata-scope.v1",
                "filters": {"source_hosts": ["example.com"]},
                "operator_note": "not receipt metadata",
            },
        )
    with pytest.raises(PassageRetrievalError, match="unknown"):
        retrieve_passages(
            "evidence",
            passages,
            metadata_scope={
                "schema_version": "giga.research-receipt-metadata-scope.v1",
                "filters": {"author_names": ["unbound"]},
            },
        )
    with pytest.raises(PassageRetrievalError, match="source kinds"):
        retrieve_passages(
            "evidence",
            passages,
            metadata_scope={
                "schema_version": "giga.research-receipt-metadata-scope.v1",
                "filters": {"source_kinds": ["remote_drive"]},
            },
        )


def test_bibliography_chrome_is_downweighted_but_remains_auditable() -> None:
    useful = Passage("useful", "a" * 64, "b" * 64, "https://example.edu", 0, 80, (
        "Bird migration navigation combines magnetic cues with celestial and olfactory maps."
    ))
    chrome = Passage("chrome", "c" * 64, "d" * 64, "https://journal.example", 0, 120, (
        "Bird migration navigation cues. Google Scholar PubMed Download references. "
        "Bird migration navigation cues."
    ))

    ranked = bm25_rank("bird migration navigation cues", [chrome, useful])

    assert ranked[0][0] == "useful"
    result = retrieve_passages(
        "bird migration navigation cues", [chrome, useful], limit=2, per_source=1
    )
    weights = {row["passage_id"]: row["content_weight"] for row in result["results"]}
    assert weights == {"useful": 1.0, "chrome": 0.2}


def test_invalid_fusion_and_unknown_dense_passage_fail() -> None:
    with pytest.raises(PassageRetrievalError, match="unique"):
        reciprocal_rank_fusion({"bm25": ["one", "one"]})
    with pytest.raises(PassageRetrievalError, match="unknown"):
        retrieve_passages("query", [], dense_ranking=["ghost"])
    with pytest.raises(PassageRetrievalError, match="k1"):
        bm25_rank("query", [], k1=0)


def test_weighted_fusion_is_explicit_and_validated() -> None:
    rankings = {"bm25": ["lexical", "semantic"], "dense": ["semantic", "lexical"]}
    assert reciprocal_rank_fusion(
        rankings, weights={"bm25": 0.25, "dense": 1.0}
    )[0][0] == "semantic"
    assert reciprocal_rank_fusion(
        rankings, weights={"bm25": 1.0, "dense": 0.25}
    )[0][0] == "lexical"
    with pytest.raises(PassageRetrievalError, match="cover every ranker"):
        reciprocal_rank_fusion(rankings, weights={"bm25": 1.0})
    with pytest.raises(PassageRetrievalError, match="not all zero"):
        reciprocal_rank_fusion(rankings, weights={"bm25": 0.0, "dense": 0.0})


def test_dense_cosine_ranking_is_complete_and_deterministic() -> None:
    passages = [
        Passage("irrelevant", "a" * 64, "b" * 64, "https://a.example", 0, 4, "rain"),
        Passage("semantic", "c" * 64, "d" * 64, "https://b.example", 0, 8, "evidence"),
    ]
    ranked = dense_cosine_rank(passages, [1.0, 0.0], [[0.0, 1.0], [1.0, 0.0]])
    assert ranked == [("semantic", 1.0), ("irrelevant", 0.0)]
    with pytest.raises(PassageRetrievalError, match="cover every"):
        dense_cosine_rank(passages, [1.0], [[1.0]])
    with pytest.raises(PassageRetrievalError, match="finite and non-zero"):
        dense_cosine_rank(passages[:1], [0.0], [[1.0]])

    class ArrayLike(list[float]):
        def __bool__(self) -> bool:
            raise ValueError("array truth value is ambiguous")

    assert dense_cosine_rank(passages[:1], ArrayLike([1.0]), [ArrayLike([1.0])]) == [
        ("irrelevant", 1.0)
    ]


def test_model_cache_manifest_retains_files_without_double_counting_symlinks(
    tmp_path: Path,
) -> None:
    blob = tmp_path / "blobs" / "model"
    blob.parent.mkdir()
    blob.write_bytes(b"x" * 8192)
    snapshot = tmp_path / "models--owner--model" / "snapshots" / ("a" * 40)
    snapshot.mkdir(parents=True)
    try:
        (snapshot / "model.onnx").symlink_to(blob)
    except OSError:
        pytest.skip("symlinks are unavailable")
    manifest = _model_cache_manifest(tmp_path)
    assert manifest["file_count"] == 2
    assert manifest["logical_file_bytes"] == 16384
    assert manifest["unique_physical_bytes"] < manifest["logical_file_bytes"]
    assert len(manifest["files"]) == 2
    assert manifest["snapshot_revisions"] == ["a" * 40]


def test_dense_ranking_hash_excludes_runtime_telemetry() -> None:
    result = {
        "schema_version": "giga.research-dense-ranking.v1",
        "engine": "fastembed",
        "engine_version": "0.8.0",
        "model": "model",
        "model_source": "source",
        "model_file": "model.onnx",
        "model_license": "apache-2.0",
        "dimension": 2,
        "model_cache": {
            "manifest_sha256": "a" * 64,
            "snapshot_revisions": ["b" * 40],
        },
        "passage_count": 1,
        "scores": [{"passage_id": "p1", "cosine_similarity": 0.75}],
        "passage_ids": ["p1"],
        "elapsed_ms": 10,
    }
    first = _dense_ranking_sha256(result)
    result["elapsed_ms"] = 999
    assert _dense_ranking_sha256(result) == first
    result["scores"][0]["cosine_similarity"] = 0.5
    assert _dense_ranking_sha256(result) != first


def test_dense_batch_embeds_corpus_once_and_materialises_verified_rankings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"query": 0, "passage": 0, "destroyed": 0}

    class FakeTextEmbedding:
        @classmethod
        def list_supported_models(cls) -> list[dict[str, object]]:
            return [
                {
                    "model": "controlled-model",
                    "sources": {"hf": "controlled/source"},
                    "model_file": "model.onnx",
                    "license": "apache-2.0",
                    "dim": 2,
                }
            ]

        def __init__(self, *, cache_dir: str, **_: object) -> None:
            Path(cache_dir, "model.onnx").write_bytes(b"controlled model")

        def __del__(self) -> None:
            calls["destroyed"] += 1

        def query_embed(self, values: list[str], **_: object) -> list[list[float]]:
            calls["query"] += 1
            return [[1.0, 0.0] if value == "alpha" else [0.0, 1.0] for value in values]

        def passage_embed(self, values: list[str], **_: object) -> list[list[float]]:
            calls["passage"] += 1
            return [[1.0, 0.0] if value == "alpha passage" else [0.0, 1.0] for value in values]

    monkeypatch.setitem(sys.modules, "fastembed", types.SimpleNamespace(TextEmbedding=FakeTextEmbedding))
    monkeypatch.setattr(
        "twin_core.passage_retrieval.version", lambda _: "controlled-version"
    )
    passages = [
        Passage("p-alpha", "a" * 64, "b" * 64, "https://a.example", 0, 5, "alpha passage"),
        Passage("p-beta", "c" * 64, "d" * 64, "https://b.example", 0, 4, "beta passage"),
    ]
    batch = fastembed_dense_ranking_batch(
        {"q-beta": "beta", "q-alpha": "alpha"},
        passages,
        model_name="controlled-model",
        cache_root=tmp_path,
    )
    assert calls == {"query": 1, "passage": 1, "destroyed": 1}
    assert batch["query_count"] == 2
    assert batch["rankings"][0]["query_id"] == "q-alpha"
    alpha = dense_ranking_from_batch(batch, "q-alpha")
    assert alpha["passage_ids"] == ["p-alpha", "p-beta"]
    assert alpha["batch_sha256"] == batch["batch_sha256"]
    assert set(dense_rankings_from_batch(batch)) == {"q-alpha", "q-beta"}

    batch["rankings"][0]["passage_ids"].reverse()
    with pytest.raises(PassageRetrievalError, match="batch hash differs"):
        dense_ranking_from_batch(batch, "q-alpha")


def test_tampered_receipt_is_rejected(tmp_path: Path) -> None:
    archive, receipts = _archive(tmp_path)
    receipts[0].write_text("{}", encoding="utf-8")
    with pytest.raises(PassageRetrievalError, match="filename"):
        index_archived_receipts(archive, receipts)


def test_tampered_text_projection_is_rejected(tmp_path: Path) -> None:
    archive, receipts = _archive(tmp_path)
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    text_sha = receipt["text_sha256"]
    (archive / "text" / text_sha[:2] / text_sha).write_text("tampered", encoding="utf-8")
    with pytest.raises(PassageRetrievalError, match="hash differs"):
        index_archived_receipts(archive, receipts)


def test_noncanonical_forged_receipt_is_rejected(tmp_path: Path) -> None:
    archive, receipts = _archive(tmp_path)
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    noncanonical = (json.dumps(receipt, indent=2) + "\n").encode()
    digest = hashlib.sha256(noncanonical).hexdigest()
    forged = archive / "receipts" / digest[:2] / f"{digest}.json"
    forged.parent.mkdir(exist_ok=True)
    forged.write_bytes(noncanonical)
    with pytest.raises(PassageRetrievalError, match="canonical"):
        index_archived_receipts(archive, [forged])








