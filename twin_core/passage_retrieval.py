"""Deterministic passage indexing, BM25 ranking and reciprocal-rank fusion."""

from __future__ import annotations

import gc
import hashlib
import json
import math
import os
import re
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .source_quality import search_tokens
from .web_acquisition import WebAcquisitionError, load_archived_text


class PassageRetrievalError(ValueError):
    """Archived evidence cannot be indexed or ranked reproducibly."""


DEFAULT_DENSE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DENSE_RANKING_SCHEMA = "giga.research-dense-ranking.v1"
DENSE_RANKING_BATCH_SCHEMA = "giga.research-dense-ranking-batch.v1"
RECEIPT_METADATA_SCOPE_SCHEMA = "giga.research-receipt-metadata-scope.v1"


_BOILERPLATE_MARKERS = (
    "download references",
    "explore all metrics",
    "google scholar",
    "prices may be subject",
    "references\n",
    "save article",
    "similar content being viewed",
    "skip to main content",
    "track your research",
    "pubmed",
)


def passage_content_weight(text: str) -> float:
    """Downweight likely navigation/reference chrome without removing evidence."""
    folded = text.casefold()
    markers = sum(min(3, folded.count(marker)) for marker in _BOILERPLATE_MARKERS)
    if markers >= 3:
        return 0.20
    if markers == 2:
        return 0.50
    return 1.0


@dataclass(frozen=True)
class Passage:
    passage_id: str
    receipt_sha256: str
    text_sha256: str
    source_url: str
    start: int
    end: int
    text: str
    receipt_metadata: tuple[tuple[str, str], ...] = ()


_METADATA_SCOPE_FIELDS = frozenset(
    {
        "receipt_sha256s",
        "source_hosts",
        "content_types",
        "trust_classes",
        "source_kinds",
    }
)
_SCOPE_VALUE_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
_HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")


def _source_host(source_url: str) -> str | None:
    try:
        parsed = urlsplit(source_url)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return parsed.hostname.casefold().rstrip(".")


def _receipt_metadata(receipt: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """Project only canonical receipt fields that may safely scope retrieval."""
    metadata: dict[str, str] = {}
    source_url = receipt.get("final_url")
    if isinstance(source_url, str):
        source_host = _source_host(source_url)
        if source_host is not None:
            metadata["source_host"] = source_host
    for field in ("content_type", "trust_class"):
        value = receipt.get(field)
        if isinstance(value, str) and value:
            metadata[field] = value.casefold()
    source_kind = receipt.get("source_kind")
    if isinstance(source_kind, str) and source_kind:
        metadata["source_kind"] = source_kind.casefold()
    elif str(receipt.get("schema_version", "")).startswith("giga.research-local-source"):
        metadata["source_kind"] = "local_document"
    else:
        metadata["source_kind"] = "public_web"
    return tuple(sorted(metadata.items()))


def _normalise_metadata_scope(metadata_scope: Mapping[str, Any]) -> dict[str, list[str]]:
    if not isinstance(metadata_scope, Mapping):
        raise PassageRetrievalError("metadata scope must be an object")
    if set(metadata_scope) != {"schema_version", "filters"}:
        raise PassageRetrievalError("metadata scope has unexpected fields")
    if metadata_scope.get("schema_version") != RECEIPT_METADATA_SCOPE_SCHEMA:
        raise PassageRetrievalError("metadata scope has the wrong schema")
    raw_filters = metadata_scope.get("filters")
    if not isinstance(raw_filters, Mapping):
        raise PassageRetrievalError("metadata scope filters must be an object")
    unknown = set(raw_filters) - _METADATA_SCOPE_FIELDS
    if unknown:
        raise PassageRetrievalError("metadata scope contains an unknown filter")
    if not raw_filters:
        raise PassageRetrievalError("metadata scope requires at least one filter")
    filters: dict[str, list[str]] = {}
    for field in sorted(raw_filters):
        values = raw_filters[field]
        if not isinstance(values, list) or not values:
            raise PassageRetrievalError("metadata scope filters must be non-empty arrays")
        normalised: list[str] = []
        for value in values:
            if not isinstance(value, str) or not value:
                raise PassageRetrievalError("metadata scope filter values must be non-empty strings")
            folded = value.casefold().rstrip(".") if field == "source_hosts" else value.casefold()
            if field == "receipt_sha256s":
                if len(folded) != 64 or any(character not in "0123456789abcdef" for character in folded):
                    raise PassageRetrievalError("metadata scope receipt hashes must be SHA-256 values")
            elif field == "source_hosts":
                if not _HOST_RE.fullmatch(folded) or "/" in folded or ":" in folded:
                    raise PassageRetrievalError("metadata scope source hosts must be canonical host names")
            elif field == "content_types":
                if "/" not in folded or not _SCOPE_VALUE_RE.fullmatch(folded.replace("/", ":")):
                    raise PassageRetrievalError("metadata scope content types are invalid")
            elif field == "source_kinds":
                if folded not in {"public_web", "local_document"}:
                    raise PassageRetrievalError("metadata scope source kinds are invalid")
            elif not _SCOPE_VALUE_RE.fullmatch(folded):
                raise PassageRetrievalError("metadata scope values are invalid")
            normalised.append(folded)
        filters[field] = sorted(set(normalised))
    return filters


def _scope_passages(
    passages: Sequence[Passage], metadata_scope: Mapping[str, Any] | None
) -> tuple[list[Passage], dict[str, Any] | None]:
    if metadata_scope is None:
        return list(passages), None
    filters = _normalise_metadata_scope(metadata_scope)
    receipt_metadata: dict[str, dict[str, str]] = {}
    for passage in passages:
        values = dict(passage.receipt_metadata)
        source_host = _source_host(passage.source_url)
        if source_host is not None:
            values.setdefault("source_host", source_host)
        prior = receipt_metadata.setdefault(passage.receipt_sha256, values)
        if prior != values:
            raise PassageRetrievalError("one receipt has inconsistent retrieval metadata")

    def matches(receipt_sha256: str, values: Mapping[str, str]) -> bool:
        metadata_field = {
            "source_hosts": "source_host",
            "content_types": "content_type",
            "trust_classes": "trust_class",
            "source_kinds": "source_kind",
        }
        for field, expected in filters.items():
            actual = (
                receipt_sha256
                if field == "receipt_sha256s"
                else values.get(metadata_field[field])
            )
            if actual not in expected:
                return False
        return True

    eligible_receipts = {
        receipt_sha256
        for receipt_sha256, values in receipt_metadata.items()
        if matches(receipt_sha256, values)
    }
    eligible = [passage for passage in passages if passage.receipt_sha256 in eligible_receipts]
    identity = {
        "schema_version": RECEIPT_METADATA_SCOPE_SCHEMA,
        "filters": filters,
    }
    return eligible, {
        **identity,
        "metadata_scope_sha256": hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "indexed_receipt_count": len(receipt_metadata),
        "eligible_receipt_count": len(eligible_receipts),
        "excluded_receipt_count": len(receipt_metadata) - len(eligible_receipts),
        "indexed_passage_count": len(passages),
        "eligible_passage_count": len(eligible),
        "excluded_passage_count": len(passages) - len(eligible),
    }


def _passage_id(receipt_sha256: str, start: int, end: int, text: str) -> str:
    payload = f"{receipt_sha256}:{start}:{end}:".encode() + text.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def chunk_archived_text(
    receipt_sha256: str,
    receipt: Mapping[str, Any],
    text: str,
    *,
    maximum_characters: int = 1200,
    overlap_characters: int = 180,
) -> list[Passage]:
    """Split archived text into stable, exact-offset passages."""
    if maximum_characters < 40:
        raise PassageRetrievalError("maximum_characters must be at least 40")
    if not 0 <= overlap_characters < maximum_characters:
        raise PassageRetrievalError("overlap_characters must be smaller than the passage")
    if not text.strip():
        return []
    text_sha = receipt.get("text_sha256")
    source_url = receipt.get("final_url")
    if not isinstance(text_sha, str) or not isinstance(source_url, str):
        raise PassageRetrievalError("receipt lacks text provenance")
    receipt_metadata = _receipt_metadata(receipt)
    passages: list[Passage] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + maximum_characters)
        if end < len(text):
            boundary = max(text.rfind("\n", start + 1, end), text.rfind(" ", start + 1, end))
            if boundary > start + maximum_characters // 2:
                end = boundary
        raw = text[start:end]
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        clean_start = start + leading
        clean_end = start + trailing
        if clean_start < clean_end:
            passage_text = text[clean_start:clean_end]
            passages.append(
                Passage(
                    passage_id=_passage_id(receipt_sha256, clean_start, clean_end, passage_text),
                    receipt_sha256=receipt_sha256,
                    text_sha256=text_sha,
                    source_url=source_url,
                    start=clean_start,
                    end=clean_end,
                    text=passage_text,
                    receipt_metadata=receipt_metadata,
                )
            )
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap_characters)
        if next_start > 0 and not text[next_start - 1].isspace():
            boundary = text.find(" ", next_start, end)
            if boundary != -1:
                next_start = boundary + 1
        start = next_start
    return passages


def index_archived_receipts(
    archive_root: Path,
    receipt_paths: Sequence[Path],
    *,
    maximum_characters: int = 1200,
    overlap_characters: int = 180,
) -> list[Passage]:
    """Verify receipts and construct a deterministic in-memory passage index."""
    passages: list[Passage] = []
    seen_receipts: set[str] = set()
    for path in receipt_paths:
        try:
            receipt_sha, receipt, text = load_archived_text(path, archive_root)
        except WebAcquisitionError as exc:
            raise PassageRetrievalError(str(exc)) from exc
        if receipt_sha in seen_receipts:
            raise PassageRetrievalError("receipt list contains a duplicate")
        seen_receipts.add(receipt_sha)
        passages.extend(
            chunk_archived_text(
                receipt_sha,
                receipt,
                text,
                maximum_characters=maximum_characters,
                overlap_characters=overlap_characters,
            )
        )
    return passages


def bm25_rank(
    query: str,
    passages: Sequence[Passage],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[tuple[str, float]]:
    """Rank passages using explainable Okapi BM25 over multilingual search tokens."""
    if k1 <= 0 or not 0 <= b <= 1:
        raise PassageRetrievalError("BM25 requires k1 > 0 and b from 0 to 1")
    query_terms = search_tokens(query)
    if not query_terms:
        raise PassageRetrievalError("query has no searchable terms")
    if not passages:
        return []
    documents = [search_tokens(passage.text) for passage in passages]
    average_length = sum(len(document) for document in documents) / len(documents)
    document_frequency = Counter(term for document in documents for term in set(document))
    scores: list[tuple[str, float]] = []
    for passage, document in zip(passages, documents, strict=True):
        frequencies = Counter(document)
        score = 0.0
        for term in sorted(set(query_terms)):
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse_frequency = math.log(
                1
                + (len(documents) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            normalisation = frequency + k1 * (1 - b + b * len(document) / max(average_length, 1.0))
            score += inverse_frequency * frequency * (k1 + 1) / normalisation
        score *= passage_content_weight(passage.text)
        if score > 0:
            scores.append((passage.passage_id, score))
    return sorted(scores, key=lambda item: (-item[1], item[0]))


def reciprocal_rank_fusion(
    rankings: Mapping[str, Sequence[str]],
    *,
    rank_constant: int = 60,
    weights: Mapping[str, float] | None = None,
) -> list[tuple[str, float]]:
    """Fuse named rankings without making incomparable raw scores commensurate."""
    if rank_constant < 1:
        raise PassageRetrievalError("rank_constant must be positive")
    ranker_weights = dict(weights or {name: 1.0 for name in rankings})
    if set(ranker_weights) != set(rankings):
        raise PassageRetrievalError("fusion weights must cover every ranker exactly")
    if any(
        isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or not math.isfinite(float(weight))
        or float(weight) < 0
        for weight in ranker_weights.values()
    ) or not any(float(weight) > 0 for weight in ranker_weights.values()):
        raise PassageRetrievalError("fusion weights must be finite, non-negative and not all zero")
    totals: dict[str, float] = {}
    for name, ranking in rankings.items():
        if not name or len(ranking) != len(set(ranking)):
            raise PassageRetrievalError("every named ranking must have unique passage ids")
        for rank, passage_id in enumerate(ranking, start=1):
            totals[passage_id] = totals.get(passage_id, 0.0) + float(
                ranker_weights[name]
            ) / (rank_constant + rank)
    return sorted(totals.items(), key=lambda item: (-item[1], item[0]))


def dense_cosine_rank(
    passages: Sequence[Passage],
    query_vector: Sequence[float],
    passage_vectors: Sequence[Sequence[float]],
) -> list[tuple[str, float]]:
    """Rank exact passages by cosine similarity with deterministic tie-breaking."""
    if len(passage_vectors) != len(passages):
        raise PassageRetrievalError("dense embeddings must cover every indexed passage")
    if len(query_vector) == 0:
        raise PassageRetrievalError("dense query embedding must not be empty")
    dimension = len(query_vector)
    query_values = [float(value) for value in query_vector]
    query_norm = math.sqrt(sum(value * value for value in query_values))
    if not math.isfinite(query_norm) or query_norm == 0:
        raise PassageRetrievalError("dense query embedding must be finite and non-zero")
    scores: list[tuple[str, float]] = []
    for passage, vector in zip(passages, passage_vectors, strict=True):
        if len(vector) != dimension:
            raise PassageRetrievalError("dense embedding dimensions differ")
        values = [float(value) for value in vector]
        vector_norm = math.sqrt(sum(value * value for value in values))
        if not math.isfinite(vector_norm) or vector_norm == 0:
            raise PassageRetrievalError("dense passage embedding must be finite and non-zero")
        similarity = sum(left * right for left, right in zip(query_values, values, strict=True)) / (
            query_norm * vector_norm
        )
        if not math.isfinite(similarity):
            raise PassageRetrievalError("dense cosine similarity is not finite")
        scores.append((passage.passage_id, similarity))
    return sorted(scores, key=lambda item: (-item[1], item[0]))


def _model_cache_manifest(model_cache: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    logical_file_bytes = 0
    unique_physical_bytes = 0
    physical_files: set[tuple[int, int]] = set()
    for path in sorted(model_cache.rglob("*")):
        if not path.is_file() or path.name.endswith(".lock"):
            continue
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        logical_file_bytes += size
        stat = path.stat()
        physical_identity = (stat.st_dev, stat.st_ino)
        if physical_identity not in physical_files:
            physical_files.add(physical_identity)
            unique_physical_bytes += int(getattr(stat, "st_blocks", 0)) * 512 or size
        rows.append(
            {
                "path": path.relative_to(model_cache).as_posix(),
                "sha256": digest.hexdigest(),
                "bytes": size,
            }
        )
    if not rows:
        raise PassageRetrievalError("dense model cache contains no verifiable files")
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    revisions = sorted(
        path.name
        for path in model_cache.glob("models--*/snapshots/*")
        if path.is_dir()
    )
    return {
        "file_count": len(rows),
        "logical_file_bytes": logical_file_bytes,
        "unique_physical_bytes": unique_physical_bytes,
        "files": rows,
        "manifest_sha256": hashlib.sha256(encoded).hexdigest(),
        "snapshot_revisions": revisions,
    }


def _dense_ranking_sha256(result: Mapping[str, Any]) -> str:
    model_cache = result.get("model_cache")
    if not isinstance(model_cache, Mapping):
        raise PassageRetrievalError("dense ranking lacks a model-cache manifest")
    identity = {
        key: result.get(key)
        for key in (
            "schema_version",
            "engine",
            "engine_version",
            "model",
            "model_source",
            "model_file",
            "model_license",
            "dimension",
            "passage_count",
            "scores",
            "passage_ids",
        )
    }
    identity["model_cache"] = {
        "manifest_sha256": model_cache.get("manifest_sha256"),
        "snapshot_revisions": model_cache.get("snapshot_revisions"),
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def dense_ranking_identity_sha256(result: Mapping[str, Any]) -> str:
    """Return the deterministic identity hash used by a dense ranking artifact."""
    return _dense_ranking_sha256(result)


def validate_dense_ranking(
    result: Mapping[str, Any], *, expected_query: str | None = None
) -> dict[str, Any]:
    """Verify a dense ranking's order, scores, cache receipt and identity hash."""
    if result.get("schema_version") != DENSE_RANKING_SCHEMA:
        raise PassageRetrievalError("invalid dense ranking schema")
    passage_ids = result.get("passage_ids")
    scores = result.get("scores")
    if (
        not isinstance(passage_ids, list)
        or not passage_ids
        or not all(isinstance(value, str) and value for value in passage_ids)
        or len(passage_ids) != len(set(passage_ids))
        or not isinstance(scores, list)
        or len(scores) != len(passage_ids)
        or result.get("passage_count") != len(passage_ids)
    ):
        raise PassageRetrievalError("dense ranking corpus or score count is invalid")
    for passage_id, row in zip(passage_ids, scores, strict=True):
        if (
            not isinstance(row, Mapping)
            or row.get("passage_id") != passage_id
            or isinstance(row.get("cosine_similarity"), bool)
            or not isinstance(row.get("cosine_similarity"), (int, float))
            or not math.isfinite(float(row["cosine_similarity"]))
        ):
            raise PassageRetrievalError("dense ranking scores differ from passage order")
    query = result.get("query")
    if query is not None and (
        not isinstance(query, str)
        or not query.strip()
        or expected_query is not None
        and query != expected_query
    ):
        raise PassageRetrievalError("dense ranking query differs")
    if result.get("ranking_sha256") != _dense_ranking_sha256(result):
        raise PassageRetrievalError("dense ranking hash differs from its contents")
    return dict(result)


def _dense_batch_sha256(result: Mapping[str, Any]) -> str:
    identity = {
        key: result.get(key)
        for key in (
            "schema_version",
            "engine",
            "engine_version",
            "model",
            "model_source",
            "model_file",
            "model_license",
            "dimension",
            "passage_count",
            "query_count",
            "rankings",
        )
    }
    model_cache = result.get("model_cache")
    if not isinstance(model_cache, Mapping):
        raise PassageRetrievalError("dense ranking batch lacks a model-cache manifest")
    identity["model_cache"] = {
        "manifest_sha256": model_cache.get("manifest_sha256"),
        "snapshot_revisions": model_cache.get("snapshot_revisions"),
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fastembed_dense_ranking_batch(
    queries: Mapping[str, str],
    passages: Sequence[Passage],
    *,
    model_name: str = DEFAULT_DENSE_MODEL,
    cache_root: Path,
    batch_size: int = 64,
    threads: int | None = None,
) -> dict[str, Any]:
    """Embed one corpus once and produce provenance-bound rankings for many queries."""
    if not queries:
        raise PassageRetrievalError("dense ranking batch requires queries")
    ordered_queries = sorted(queries.items())
    if any(not query_id.strip() or not query.strip() for query_id, query in ordered_queries):
        raise PassageRetrievalError("dense ranking batch query IDs and text must not be empty")
    if not passages:
        raise PassageRetrievalError("dense ranking requires indexed passages")
    if batch_size < 1 or threads is not None and threads < 1:
        raise PassageRetrievalError("dense batch size and thread count must be positive")
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise PassageRetrievalError(
            "owned dense retrieval requires the research-dense optional dependency"
        ) from exc
    supported = {str(row["model"]): row for row in TextEmbedding.list_supported_models()}
    descriptor = supported.get(model_name)
    if descriptor is None:
        raise PassageRetrievalError("dense model is not in FastEmbed's supported model registry")
    root = cache_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    model_key = hashlib.sha256(model_name.encode("utf-8")).hexdigest()[:24]
    model_cache = root / model_key
    model_cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(model_cache, 0o700)
    started = time.perf_counter()
    model = None
    try:
        model = TextEmbedding(
            model_name=model_name,
            cache_dir=str(model_cache),
            threads=threads,
        )
        query_vectors = list(
            model.query_embed(
                [query for _, query in ordered_queries],
                batch_size=1,
            )
        )
        passage_vectors = list(
            model.passage_embed(
                [passage.text for passage in passages], batch_size=batch_size
            )
        )
    except (OSError, RuntimeError, StopIteration, ValueError) as exc:
        raise PassageRetrievalError(f"dense model execution failed: {exc}") from exc
    finally:
        if model is not None:
            # ONNX Runtime can retain native locks until interpreter teardown on macOS.
            # Destroy the session while Python and its synchronization primitives are
            # still alive; vectors are materialised above and no longer depend on it.
            del model
            gc.collect()
    if len(query_vectors) != len(ordered_queries):
        raise PassageRetrievalError("dense model did not embed every batch query")
    try:
        package_version = version("fastembed")
    except PackageNotFoundError as exc:
        raise PassageRetrievalError("fastembed package metadata is unavailable") from exc
    model_source = descriptor.get("sources") or {}
    cache_manifest = _model_cache_manifest(model_cache)
    common = {
        "engine": "fastembed",
        "engine_version": package_version,
        "model": model_name,
        "model_source": model_source.get("hf") or model_source.get("url"),
        "model_file": descriptor.get("model_file"),
        "model_license": descriptor.get("license"),
        "dimension": int(descriptor.get("dim", len(query_vectors[0]))),
        "model_cache": cache_manifest,
        "passage_count": len(passages),
    }
    rankings = []
    for (query_id, query), query_vector in zip(ordered_queries, query_vectors, strict=True):
        ranking = dense_cosine_rank(passages, query_vector, passage_vectors)
        single = {
            "schema_version": DENSE_RANKING_SCHEMA,
            **common,
            "scores": [
                {"passage_id": passage_id, "cosine_similarity": score}
                for passage_id, score in ranking
            ],
            "passage_ids": [passage_id for passage_id, _ in ranking],
        }
        rankings.append(
            {
                "query_id": query_id,
                "query": query,
                "scores": single["scores"],
                "passage_ids": single["passage_ids"],
                "ranking_sha256": _dense_ranking_sha256(single),
            }
        )
    result = {
        "schema_version": DENSE_RANKING_BATCH_SCHEMA,
        **common,
        "query_count": len(rankings),
        "rankings": rankings,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "elapsed_scope": (
            "model_initialisation_query_and_passage_embedding_and_cache_verification_shared_"
            "across_batch"
        ),
        "cost_usd": 0.0,
        "cost_scope": (
            "provider_api_charges_for_local_embedding_execution_only; excludes local "
            "compute, energy, storage and model-download transfer"
        ),
        "claim_authority": False,
    }
    return {**result, "batch_sha256": _dense_batch_sha256(result)}


def dense_rankings_from_batch(batch: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Verify one batch once and materialise every legacy-compatible ranking."""
    if batch.get("schema_version") != DENSE_RANKING_BATCH_SCHEMA:
        raise PassageRetrievalError("invalid dense ranking batch schema")
    if batch.get("batch_sha256") != _dense_batch_sha256(batch):
        raise PassageRetrievalError("dense ranking batch hash differs")
    rankings = batch.get("rankings")
    if not isinstance(rankings, list):
        raise PassageRetrievalError("dense ranking batch lacks rankings")
    if batch.get("query_count") != len(rankings):
        raise PassageRetrievalError("dense ranking batch query count differs")
    results = {}
    for row in rankings:
        if not isinstance(row, Mapping):
            raise PassageRetrievalError("dense ranking batch rows must be objects")
        query_id = row.get("query_id")
        if not isinstance(query_id, str) or not query_id or query_id in results:
            raise PassageRetrievalError("dense ranking batch query IDs must be unique text")
        result = {
            "schema_version": DENSE_RANKING_SCHEMA,
            **{
                key: batch.get(key)
                for key in (
                    "engine",
                    "engine_version",
                    "model",
                    "model_source",
                    "model_file",
                    "model_license",
                    "dimension",
                    "model_cache",
                    "passage_count",
                    "elapsed_ms",
                    "elapsed_scope",
                    "cost_usd",
                    "cost_scope",
                )
            },
            "query_id": query_id,
            "query": row.get("query"),
            "scores": row.get("scores"),
            "passage_ids": row.get("passage_ids"),
            "ranking_sha256": row.get("ranking_sha256"),
            "batch_sha256": batch.get("batch_sha256"),
            "batch_query_count": batch.get("query_count"),
            "claim_authority": False,
        }
        try:
            results[query_id] = validate_dense_ranking(
                result, expected_query=str(row.get("query") or "")
            )
        except PassageRetrievalError as exc:
            raise PassageRetrievalError(
                "dense ranking hash differs from batch contents"
            ) from exc
    return results


def dense_ranking_from_batch(batch: Mapping[str, Any], query_id: str) -> dict[str, Any]:
    """Materialise one verified legacy-compatible ranking from a shared batch."""
    results = dense_rankings_from_batch(batch)
    if query_id not in results:
        raise PassageRetrievalError("dense ranking batch query ID is missing")
    return results[query_id]


def fastembed_dense_ranking(
    query: str,
    passages: Sequence[Passage],
    *,
    model_name: str = DEFAULT_DENSE_MODEL,
    cache_root: Path,
    batch_size: int = 64,
    threads: int | None = None,
) -> dict[str, Any]:
    """Generate a locally executed, model-provenance-bound dense passage ranking."""
    if not query.strip():
        raise PassageRetrievalError("dense query must not be empty")
    batch = fastembed_dense_ranking_batch(
        {"single-query": query},
        passages,
        model_name=model_name,
        cache_root=cache_root,
        batch_size=batch_size,
        threads=threads,
    )
    return dense_ranking_from_batch(batch, "single-query")


def retrieve_passages(
    query: str,
    passages: Sequence[Passage],
    *,
    dense_ranking: Sequence[str] | None = None,
    metadata_scope: Mapping[str, Any] | None = None,
    ranker_weights: Mapping[str, float] | None = None,
    rank_constant: int = 60,
    limit: int = 10,
    per_source: int = 3,
) -> dict[str, Any]:
    """Return provenance-complete ranked evidence candidates, never accepted claims."""
    if limit < 1 or per_source < 1:
        raise PassageRetrievalError("limit and per_source must be positive")
    indexed_passages = list(passages)
    known_indexed = {passage.passage_id: passage for passage in indexed_passages}
    scoped_passages, scope_receipt = _scope_passages(indexed_passages, metadata_scope)
    lexical = bm25_rank(query, scoped_passages)
    known = {passage.passage_id: passage for passage in scoped_passages}
    rankings = {"bm25": [passage_id for passage_id, _ in lexical]}
    if dense_ranking is not None:
        if any(passage_id not in known_indexed for passage_id in dense_ranking):
            raise PassageRetrievalError("dense ranking references an unknown passage")
        rankings["dense"] = [passage_id for passage_id in dense_ranking if passage_id in known]
    fused = reciprocal_rank_fusion(
        rankings,
        rank_constant=rank_constant,
        weights=ranker_weights,
    )
    selected: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    lexical_scores = dict(lexical)
    selected_ids: set[str] = set()
    for source_quota in range(1, per_source + 1):
        for passage_id, fusion_score in fused:
            if passage_id in selected_ids:
                continue
            passage = known[passage_id]
            if source_counts[passage.receipt_sha256] >= source_quota:
                continue
            source_counts[passage.receipt_sha256] += 1
            selected_ids.add(passage_id)
            passage_data = asdict(passage)
            passage_data["receipt_metadata"] = dict(passage.receipt_metadata)
            selected.append(
                {
                    **passage_data,
                    "bm25_score": lexical_scores.get(passage_id, 0.0),
                    "content_weight": passage_content_weight(passage.text),
                    "fusion_score": fusion_score,
                    "authority": "evidence_candidate_only",
                }
            )
            if len(selected) == limit:
                break
        if len(selected) == limit:
            break
    result = {
        "schema_version": "giga.research-passage-retrieval.v2",
        "query": query,
        "rankers": list(rankings),
        "ranker_weights": dict(
            ranker_weights or {name: 1.0 for name in rankings}
        ),
        "rank_constant": rank_constant,
        "indexed_passages": len(indexed_passages),
        "eligible_passages": len(scoped_passages),
        "results": selected,
        "selection_policy": (
            "metadata_scoped_boilerplate_weighted_relevance_with_source_round_robin"
            if scope_receipt is not None
            else "boilerplate_weighted_relevance_with_source_round_robin"
        ),
        "claim_authority": False,
    }
    if scope_receipt is not None:
        result["metadata_scope"] = scope_receipt
    return result
