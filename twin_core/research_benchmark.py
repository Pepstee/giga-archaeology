"""Deterministic, bilingual benchmark scoring for research-system outputs."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from fractions import Fraction
from itertools import combinations
from math import isfinite, log2
from pathlib import Path
from random import Random
from statistics import median
from typing import Any

from .passage_retrieval import (
    PassageRetrievalError,
    reciprocal_rank_fusion,
    validate_dense_ranking,
)
from .research_export import (
    SYNTHESIS_PROPOSAL_SCHEMA,
    build_synthesis_packet,
    render_extractive_article,
    render_synthesis_article,
    validate_synthesis_proposal,
)
from .research_project import project_plan_sha256, validate_project_plan
from .source_quality import assess_authority, lexical_support, registrable_domain

BENCHMARK_RUN_SCHEMA = "giga.research-benchmark-run.v2"
BENCHMARK_SCORE_SCHEMA = "giga.research-benchmark-score.v2"
BENCHMARK_MEASUREMENT_SCHEMA = "giga.research-benchmark-measurement.v1"
RETRIEVAL_ABLATION_SCHEMA = "giga.research-retrieval-ablation.v1"
RETRIEVAL_COHORT_MANIFEST_SCHEMA = "giga.research-retrieval-cohort-manifest.v1"
RETRIEVAL_COHORT_SCORE_SCHEMA = "giga.research-retrieval-cohort-score.v1"
DEEPRESEARCH_BENCH_COMMIT = "469cce54ea7f6a63c163d3d9fec879cf289ec484"
DEEPRESEARCH_BENCH_RACE_MODEL = "gpt-5.5"
DEEPRESEARCH_BENCH_FACT_MODEL = "gpt-5.4-mini"
DEEPRESEARCH_BENCH_COHORT_SCHEMA = "giga.deepresearch-bench-cohort.v1"
DEEPRESEARCH_BENCH_CAMPAIGN_SCHEMA = "giga.deepresearch-bench-campaign-plan.v1"
DEEPRESEARCH_BENCH_ADMISSION_SCHEMA = "giga.deepresearch-bench-campaign-admission.v1"
REPORTBENCH_COMMIT = "ca3d65b9ff3136fd7e6107955eeb711b2a7fd894"
REPORTBENCH_CASE_SCHEMA = "giga.reportbench-case-manifest.v1"
REPORTBENCH_V1_1_SHA256 = "7fbcbf9872b5db745a4ad98e121abaa5bb9f47ec0dccb8310477fbc57b197dcd"
DEEPSYNTH_BENCH_COMMIT = "77fa6615fac6dc1033f32f86cedb87ac6f6326f6"
DEEPSYNTH_SCORE_SCHEMA = "giga.deepsynth-static-score.v1"
PDRBENCH_COMMIT = "5b43f9f188c747d154fc7666812ab93b7ca6a3c2"
PDRBENCH_CASE_SCHEMA = "giga.pdrbench-case-manifest.v1"
PDRBENCH_OFFICIAL_ARTIFACTS = {
    "e1b782361ec57ac3b21c34a143c74a34a57b42df222e42b7d6efb978ff998091": {
        "language": "en",
        "case_count": 250,
        "cohort": "task_universe",
    },
    "1532a3258c46537667eb90a434f030e918d17965cdb67481dd3399b1ddbcacfd": {
        "language": "zh",
        "case_count": 250,
        "cohort": "task_universe",
    },
    "201a0dd791930a8e8e2b852078b3e3b3855bfcaf4c50485584aa22ca7ba0b116": {
        "language": "en",
        "case_count": 150,
        "cohort": "released_evaluation",
    },
    "9a088f49fdf8fce9cd25a6800d1f265eccafd89b787c9a30aaef72ad43b1e616": {
        "language": "zh",
        "case_count": 150,
        "cohort": "released_evaluation",
    },
}
_PDRBENCH_PERSONALIZATION_DIMENSIONS = (
    "goal_alignment",
    "content_alignment",
    "presentation_fit",
    "actionability_practicality",
)
_PDRBENCH_QUALITY_DIMENSIONS = (
    "depth_insight",
    "logical_coherence",
    "clarity_readability",
)
_RACE_DIMENSIONS = (
    "comprehensiveness",
    "insight",
    "instruction_following",
    "readability",
)
_COMPARISON_BOOTSTRAP_RESAMPLES = 20_000
_COMPARISON_RANDOMISATION_RESAMPLES = 20_000
_EXACT_SIGN_FLIP_MAX_CASES = 16
_MIN_SUPERIORITY_CASES = 5
_MIN_RETRIEVAL_COHORT_CASES_PER_LANGUAGE = 20
_RETRIEVAL_COHORT_ALLOWED_LICENSES = {
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "cc-by-4.0",
    "mit",
    "odc-by-1.0",
}


class ResearchBenchmarkError(ValueError):
    """A benchmark input cannot produce a comparable, reproducible score."""


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _canonical_artifact_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _retrieval_metrics(
    passage_ids: Sequence[str],
    receipt_by_passage: Mapping[str, str],
    relevant_receipts: set[str],
    *,
    cutoff: int,
    relevance_grade_by_receipt: Mapping[str, float] | None = None,
) -> dict[str, float | int | None]:
    top = list(passage_ids[:cutoff])
    grades = relevance_grade_by_receipt or {
        receipt: 1.0 for receipt in relevant_receipts
    }
    relevance_scores = [grades.get(receipt_by_passage[passage_id], 0.0) for passage_id in top]
    relevant_flags = [score > 0 for score in relevance_scores]
    relevant_found = len(
        {receipt_by_passage[passage_id] for passage_id in top} & relevant_receipts
    )
    first_rank = next(
        (rank for rank, relevant in enumerate(relevant_flags, start=1) if relevant),
        None,
    )
    dcg = sum(
        score / log2(rank + 1)
        for rank, score in enumerate(relevance_scores, start=1)
        if score > 0
    )
    ideal_dcg = sum(
        score / log2(rank + 1)
        for rank, score in enumerate(sorted(grades.values(), reverse=True)[:cutoff], start=1)
    )
    return {
        "returned": len(passage_ids),
        "relevant_receipts_at_k": relevant_found,
        "recall_at_k": _ratio(relevant_found, len(relevant_receipts)),
        "precision_at_k": _ratio(sum(relevant_flags), cutoff),
        "reciprocal_rank": _ratio(1, first_rank) if first_rank else 0.0,
        "ndcg_at_k": _ratio(dcg, ideal_dcg),
        "first_relevant_rank": first_rank,
    }


def score_retrieval_ablation(
    specification: Mapping[str, Any],
    bm25_result: Mapping[str, Any],
    hybrid_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Score BM25, owned dense and hybrid rankings against one exact gold corpus."""
    if specification.get("schema_version") != "giga.research-retrieval-microbenchmark.v1":
        raise ResearchBenchmarkError("invalid retrieval microbenchmark schema")
    query = specification.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ResearchBenchmarkError("retrieval microbenchmark requires a query")
    if bm25_result.get("query") != query or hybrid_result.get("query") != query:
        raise ResearchBenchmarkError("retrieval artifacts use a different query")
    indexed = hybrid_result.get("indexed_passages")
    if (
        isinstance(indexed, bool)
        or not isinstance(indexed, int)
        or indexed < 1
        or bm25_result.get("indexed_passages") != indexed
    ):
        raise ResearchBenchmarkError("retrieval artifacts must share a positive corpus size")
    cutoff = specification.get("cutoff", 2)
    if isinstance(cutoff, bool) or not isinstance(cutoff, int) or not 1 <= cutoff <= indexed:
        raise ResearchBenchmarkError("retrieval cutoff must fit the indexed corpus")
    corpus_receipts = specification.get("corpus_receipt_sha256s")
    relevant_receipts = specification.get("relevant_receipt_sha256s")
    if (
        not isinstance(corpus_receipts, list)
        or not corpus_receipts
        or not all(isinstance(value, str) and len(value) == 64 for value in corpus_receipts)
        or len(corpus_receipts) != len(set(corpus_receipts))
    ):
        raise ResearchBenchmarkError("retrieval corpus receipts must be unique SHA-256 values")
    if (
        not isinstance(relevant_receipts, list)
        or not relevant_receipts
        or not all(isinstance(value, str) and len(value) == 64 for value in relevant_receipts)
        or not set(relevant_receipts) <= set(corpus_receipts)
    ):
        raise ResearchBenchmarkError("relevant receipts must be a non-empty corpus subset")
    relevance_grades_raw = specification.get("relevance_grade_by_receipt")
    relevance_grades: dict[str, float] | None = None
    if relevance_grades_raw is not None:
        if not isinstance(relevance_grades_raw, Mapping):
            raise ResearchBenchmarkError("retrieval relevance grades must be an object")
        relevance_grades = {}
        for receipt, grade in relevance_grades_raw.items():
            if (
                not isinstance(receipt, str)
                or receipt not in relevant_receipts
                or isinstance(grade, bool)
                or not isinstance(grade, (int, float))
                or not isfinite(float(grade))
                or float(grade) <= 0
            ):
                raise ResearchBenchmarkError(
                    "retrieval relevance grades require positive finite values for relevant receipts"
                )
            relevance_grades[receipt] = float(grade)
        if set(relevance_grades) != set(relevant_receipts):
            raise ResearchBenchmarkError(
                "retrieval relevance grades must cover every relevant receipt exactly"
            )
    hybrid_rows = hybrid_result.get("results")
    bm25_rows = bm25_result.get("results")
    if not isinstance(hybrid_rows, list) or len(hybrid_rows) != indexed:
        raise ResearchBenchmarkError("hybrid benchmark artifact must expose every passage")
    if not isinstance(bm25_rows, list):
        raise ResearchBenchmarkError("BM25 benchmark artifact requires results")
    receipt_by_passage: dict[str, str] = {}
    for row in hybrid_rows:
        if not isinstance(row, Mapping):
            raise ResearchBenchmarkError("hybrid result rows must be objects")
        passage_id = row.get("passage_id")
        receipt = row.get("receipt_sha256")
        if (
            not isinstance(passage_id, str)
            or passage_id in receipt_by_passage
            or not isinstance(receipt, str)
            or receipt not in corpus_receipts
        ):
            raise ResearchBenchmarkError("hybrid result provenance is incomplete or duplicated")
        receipt_by_passage[passage_id] = receipt
    if set(receipt_by_passage.values()) != set(corpus_receipts):
        raise ResearchBenchmarkError("hybrid artifact does not cover the declared corpus receipts")
    dense_provider = hybrid_result.get("dense_provider")
    if (
        not isinstance(dense_provider, Mapping)
        or dense_provider.get("schema_version") != "giga.research-dense-ranking.v1"
    ):
        raise ResearchBenchmarkError("hybrid artifact lacks owned dense-ranking provenance")
    dense_ids = dense_provider.get("passage_ids")
    if not isinstance(dense_ids, list) or set(dense_ids) != set(receipt_by_passage):
        raise ResearchBenchmarkError("dense ranking does not cover the exact passage corpus")
    try:
        dense_provider = validate_dense_ranking(
            dense_provider, expected_query=query
        )
    except PassageRetrievalError as exc:
        raise ResearchBenchmarkError(str(exc)) from exc
    bm25_ids = [str(row.get("passage_id")) for row in bm25_rows if isinstance(row, Mapping)]
    hybrid_ids = [str(row["passage_id"]) for row in hybrid_rows]
    if len(bm25_ids) != len(set(bm25_ids)) or any(
        passage_id not in receipt_by_passage for passage_id in bm25_ids
    ):
        raise ResearchBenchmarkError("BM25 ranking contains unknown or duplicate passages")
    fusion_policy_raw = hybrid_result.get("fusion_policy") or {}
    if not isinstance(fusion_policy_raw, Mapping):
        raise ResearchBenchmarkError("hybrid fusion policy must be an object")
    algorithm = fusion_policy_raw.get("algorithm", "reciprocal_rank_fusion")
    rank_constant = fusion_policy_raw.get("rank_constant", 60)
    ranker_weights = fusion_policy_raw.get(
        "ranker_weights", {"bm25": 1.0, "dense": 1.0}
    )
    if algorithm != "reciprocal_rank_fusion":
        raise ResearchBenchmarkError("unsupported hybrid fusion algorithm")
    if isinstance(rank_constant, bool) or not isinstance(rank_constant, int):
        raise ResearchBenchmarkError("hybrid rank constant must be an integer")
    if not isinstance(ranker_weights, Mapping):
        raise ResearchBenchmarkError("hybrid ranker weights must be an object")
    try:
        expected_hybrid_ids = [
            passage_id
            for passage_id, _ in reciprocal_rank_fusion(
                {"bm25": bm25_ids, "dense": [str(value) for value in dense_ids]},
                rank_constant=rank_constant,
                weights=ranker_weights,
            )
        ]
    except PassageRetrievalError as exc:
        raise ResearchBenchmarkError(str(exc)) from exc
    if hybrid_ids != expected_hybrid_ids:
        raise ResearchBenchmarkError("hybrid ranking differs from its declared fusion policy")
    relevant = set(relevant_receipts)
    rankings = {
        "bm25": _retrieval_metrics(
            bm25_ids,
            receipt_by_passage,
            relevant,
            cutoff=cutoff,
            relevance_grade_by_receipt=relevance_grades,
        ),
        "dense": _retrieval_metrics(
            [str(value) for value in dense_ids],
            receipt_by_passage,
            relevant,
            cutoff=cutoff,
            relevance_grade_by_receipt=relevance_grades,
        ),
        "hybrid_rrf": _retrieval_metrics(
            hybrid_ids,
            receipt_by_passage,
            relevant,
            cutoff=cutoff,
            relevance_grade_by_receipt=relevance_grades,
        ),
    }
    result = {
        "schema_version": RETRIEVAL_ABLATION_SCHEMA,
        "query": query,
        "cutoff": cutoff,
        "indexed_passages": indexed,
        "corpus_receipts": len(corpus_receipts),
        "relevant_receipts": len(relevant_receipts),
        "relevance_mode": "graded" if relevance_grades is not None else "binary",
        "rankings": rankings,
        "deltas": {
            "dense_recall_at_k_minus_bm25": (
                rankings["dense"]["recall_at_k"] - rankings["bm25"]["recall_at_k"]
            ),
            "hybrid_recall_at_k_minus_bm25": (
                rankings["hybrid_rrf"]["recall_at_k"]
                - rankings["bm25"]["recall_at_k"]
            ),
            "dense_ndcg_at_k_minus_bm25": (
                rankings["dense"]["ndcg_at_k"] - rankings["bm25"]["ndcg_at_k"]
            ),
        },
        "dense_provider": {
            key: dense_provider.get(key)
            for key in (
                "engine",
                "engine_version",
                "model",
                "model_source",
                "model_license",
                "dimension",
                "model_cache",
                "ranking_sha256",
                "query",
                "query_id",
                "batch_sha256",
                "batch_query_count",
                "elapsed_ms",
                "elapsed_scope",
                "cost_usd",
                "cost_scope",
            )
        },
        "hybrid_policy": {
            "algorithm": algorithm,
            "rank_constant": rank_constant,
            "ranker_weights": {
                name: float(ranker_weights[name]) for name in sorted(ranker_weights)
            },
        },
        "artifacts": {
            "specification_sha256": _canonical_artifact_sha256(specification),
            "bm25_sha256": _canonical_artifact_sha256(bm25_result),
            "hybrid_sha256": _canonical_artifact_sha256(hybrid_result),
        },
        "claim_authority": False,
    }
    identity = {
        key: result[key]
        for key in (
            "schema_version",
            "query",
            "cutoff",
            "indexed_passages",
            "corpus_receipts",
            "relevant_receipts",
            "relevance_mode",
            "rankings",
            "deltas",
            "hybrid_policy",
            "claim_authority",
        )
    }
    identity["dense_provider"] = {
        key: result["dense_provider"].get(key)
        for key in (
            "engine",
            "engine_version",
            "model",
            "model_source",
            "model_license",
            "dimension",
            "model_cache",
            "ranking_sha256",
            "query",
            "query_id",
            "batch_sha256",
            "batch_query_count",
        )
    }
    return {**result, "result_identity_sha256": _canonical_artifact_sha256(identity)}


def _validate_retrieval_cohort_dataset(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ResearchBenchmarkError("retrieval cohort datasets must be objects")
    required_text = ("dataset_id", "language", "source_url", "revision", "license")
    for field in required_text:
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ResearchBenchmarkError(f"retrieval cohort dataset {field} must be text")
    if value["language"] not in {"en", "zh"}:
        raise ResearchBenchmarkError("retrieval cohort dataset language must be en or zh")
    if not value["source_url"].startswith("https://"):
        raise ResearchBenchmarkError("retrieval cohort dataset source_url must use HTTPS")
    if not _git_commit(value["revision"]):
        raise ResearchBenchmarkError("retrieval cohort dataset revision must be a Git commit")
    licence = value["license"].strip().casefold()
    if licence in {"unknown", "noassertion", "not specified"}:
        raise ResearchBenchmarkError("retrieval cohort dataset license must be explicit")
    if licence not in _RETRIEVAL_COHORT_ALLOWED_LICENSES:
        raise ResearchBenchmarkError("retrieval cohort dataset license is not approved")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ResearchBenchmarkError("retrieval cohort dataset requires artifact receipts")
    names: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise ResearchBenchmarkError("retrieval cohort artifacts must be objects")
        name = artifact.get("name")
        size = artifact.get("bytes")
        if (
            not isinstance(name, str)
            or not name
            or name in names
            or not _digest(artifact.get("sha256"))
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 1
        ):
            raise ResearchBenchmarkError("retrieval cohort artifact receipt is invalid")
        names.add(name)
    return dict(value)


def _retrieval_cohort_aggregate(
    cases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    methods = ("bm25", "dense", "hybrid_rrf")
    metrics = ("recall_at_k", "precision_at_k", "reciprocal_rank", "ndcg_at_k")
    aggregate: dict[str, Any] = {}
    for method in methods:
        aggregate[method] = {}
        for metric in metrics:
            values = [float(case["score"]["rankings"][method][metric]) for case in cases]
            aggregate[method][metric] = {
                "mean": sum(values) / len(values),
                "median": float(median(values)),
                "minimum": min(values),
                "maximum": max(values),
            }
    return aggregate


def _retrieval_cohort_comparisons(
    cases: Sequence[Mapping[str, Any]], *, group: str
) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    for metric in ("recall_at_k", "precision_at_k", "reciprocal_rank", "ndcg_at_k"):
        metric_rows = []
        for method in ("dense", "hybrid_rrf"):
            deltas = [
                float(case["score"]["rankings"][method][metric])
                - float(case["score"]["rankings"]["bm25"][metric])
                for case in cases
            ]
            metric_rows.append(
                {
                    "metric": metric,
                    "left_system": method,
                    "right_system": "bm25",
                    "case_count": len(cases),
                    "statistics": _paired_quality_statistics(
                        deltas,
                        seed_material={
                            "group": group,
                            "metric": metric,
                            "method": method,
                            "case_ids": [case["case_id"] for case in cases],
                        },
                    ),
                }
            )
        _apply_holm_adjustment(metric_rows)
        for row in metric_rows:
            statistics = row["statistics"]
            interval = statistics["bootstrap_confidence_interval_95"]
            if len(cases) < _MIN_RETRIEVAL_COHORT_CASES_PER_LANGUAGE:
                state = "insufficient_cases"
            elif statistics["holm_adjusted_p_value"] > 0.05:
                state = "not_established"
            elif interval["lower"] > 0:
                state = "left_superior"
            elif interval["upper"] < 0:
                state = "right_superior"
            else:
                state = "not_established"
            row["superiority_state"] = state
            row["superior_system"] = (
                row["left_system"]
                if state == "left_superior"
                else row["right_system"]
                if state == "right_superior"
                else None
            )
        comparisons.extend(metric_rows)
    return comparisons


def score_retrieval_cohort(
    manifest: Mapping[str, Any], scores: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Aggregate a provenance-bound external multilingual retrieval cohort."""
    if manifest.get("schema_version") != RETRIEVAL_COHORT_MANIFEST_SCHEMA:
        raise ResearchBenchmarkError("invalid retrieval cohort manifest schema")
    cohort_id = manifest.get("cohort_id")
    if not isinstance(cohort_id, str) or not cohort_id.strip():
        raise ResearchBenchmarkError("retrieval cohort_id must be non-empty text")
    selection = manifest.get("selection")
    if not isinstance(selection, Mapping):
        raise ResearchBenchmarkError("retrieval cohort requires a selection receipt")
    selected_count = selection.get("selected_source_cases")
    universe_count = selection.get("source_universe_cases")
    if (
        not isinstance(selection.get("method"), str)
        or not selection["method"].strip()
        or not _digest(selection.get("seed_sha256"))
        or isinstance(selected_count, bool)
        or not isinstance(selected_count, int)
        or selected_count < 1
        or isinstance(universe_count, bool)
        or not isinstance(universe_count, int)
        or universe_count < selected_count
        or not _digest(selection.get("selected_source_ids_sha256"))
    ):
        raise ResearchBenchmarkError("retrieval cohort selection receipt is invalid")
    datasets_raw = manifest.get("datasets")
    if not isinstance(datasets_raw, list) or not datasets_raw:
        raise ResearchBenchmarkError("retrieval cohort requires datasets")
    datasets = [_validate_retrieval_cohort_dataset(value) for value in datasets_raw]
    dataset_by_id = {dataset["dataset_id"]: dataset for dataset in datasets}
    if len(dataset_by_id) != len(datasets):
        raise ResearchBenchmarkError("retrieval cohort dataset IDs must be unique")
    cases_raw = manifest.get("cases")
    if not isinstance(cases_raw, list) or not cases_raw:
        raise ResearchBenchmarkError("retrieval cohort requires cases")
    if len(scores) != len(cases_raw):
        raise ResearchBenchmarkError("retrieval cohort score count differs from manifest")
    score_by_sha: dict[str, Mapping[str, Any]] = {}
    for score in scores:
        if score.get("schema_version") != RETRIEVAL_ABLATION_SCHEMA:
            raise ResearchBenchmarkError("retrieval cohort contains an invalid score schema")
        digest = _canonical_artifact_sha256(score)
        if digest in score_by_sha:
            raise ResearchBenchmarkError("retrieval cohort contains duplicate score artifacts")
        score_by_sha[digest] = score
    cases: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    seen_source_keys: set[tuple[str, str]] = set()
    cutoffs: set[int] = set()
    corpus_sizes: set[int] = set()
    dense_identities: set[tuple[Any, ...]] = set()
    for case in cases_raw:
        if not isinstance(case, Mapping):
            raise ResearchBenchmarkError("retrieval cohort cases must be objects")
        case_id = case.get("case_id")
        dataset_id = case.get("dataset_id")
        source_query_id = case.get("source_query_id")
        language = case.get("language")
        query = case.get("query")
        score_sha = case.get("score_sha256")
        if (
            not isinstance(case_id, str)
            or not case_id
            or case_id in seen_case_ids
            or not isinstance(dataset_id, str)
            or dataset_id not in dataset_by_id
            or not isinstance(source_query_id, str)
            or not source_query_id
            or (dataset_id, source_query_id) in seen_source_keys
            or language != dataset_by_id[dataset_id]["language"]
            or not isinstance(query, str)
            or not query.strip()
            or not _digest(score_sha)
            or score_sha not in score_by_sha
        ):
            raise ResearchBenchmarkError("retrieval cohort case receipt is invalid")
        score = score_by_sha[score_sha]
        if score.get("query") != query:
            raise ResearchBenchmarkError("retrieval cohort case query differs from its score")
        dense = score.get("dense_provider")
        if not isinstance(dense, Mapping):
            raise ResearchBenchmarkError("retrieval cohort score lacks dense provenance")
        cache = dense.get("model_cache")
        if not isinstance(cache, Mapping) or not _digest(cache.get("manifest_sha256")):
            raise ResearchBenchmarkError("retrieval cohort dense model cache is unbound")
        if str(dense.get("model_license", "")).strip().casefold() not in (
            _RETRIEVAL_COHORT_ALLOWED_LICENSES
        ):
            raise ResearchBenchmarkError("retrieval cohort dense model license is not approved")
        dense_identities.add(
            (
                dense.get("engine"),
                dense.get("engine_version"),
                dense.get("model"),
                dense.get("model_source"),
                dense.get("model_license"),
                dense.get("dimension"),
                cache.get("manifest_sha256"),
                tuple(cache.get("snapshot_revisions") or ()),
            )
        )
        seen_case_ids.add(case_id)
        seen_source_keys.add((dataset_id, source_query_id))
        cutoffs.add(int(score["cutoff"]))
        corpus_sizes.add(int(score["indexed_passages"]))
        cases.append({**dict(case), "score": score})
    if len(dense_identities) != 1:
        raise ResearchBenchmarkError("retrieval cohort must use one exact dense model identity")
    if len(cutoffs) != 1:
        raise ResearchBenchmarkError("retrieval cohort scores must use one cutoff")
    source_ids_by_dataset = {
        dataset_id: [
            case["source_query_id"] for case in cases if case["dataset_id"] == dataset_id
        ]
        for dataset_id in dataset_by_id
    }
    source_id_sequences = list(source_ids_by_dataset.values())
    if (
        not source_id_sequences
        or any(sequence != source_id_sequences[0] for sequence in source_id_sequences[1:])
        or len(source_id_sequences[0]) != selected_count
        or _canonical_artifact_sha256(source_id_sequences[0])
        != selection["selected_source_ids_sha256"]
    ):
        raise ResearchBenchmarkError(
            "retrieval cohort cases differ from the declared paired selection"
        )
    if len(cases) != selected_count * len(datasets):
        raise ResearchBenchmarkError(
            "retrieval cohort must contain every selected source case for every dataset"
        )
    language_groups = {
        language: [case for case in cases if case["language"] == language]
        for language in sorted({case["language"] for case in cases})
    }
    groups = {"overall": cases, **language_groups}
    group_results = {
        group: {
            "case_count": len(group_cases),
            "aggregate": _retrieval_cohort_aggregate(group_cases),
            "comparisons": _retrieval_cohort_comparisons(group_cases, group=group),
        }
        for group, group_cases in groups.items()
    }
    bilingual = set(language_groups) == {"en", "zh"}
    enough_per_language = bilingual and all(
        len(language_groups[language]) >= _MIN_RETRIEVAL_COHORT_CASES_PER_LANGUAGE
        for language in ("en", "zh")
    )
    bm25_baseline_superiority = {}
    for group, group_result in group_results.items():
        row = next(
            comparison
            for comparison in group_result["comparisons"]
            if comparison["metric"] == "ndcg_at_k"
            and comparison["left_system"] == "hybrid_rrf"
        )
        bm25_baseline_superiority[group] = {
            "state": row["superiority_state"],
            "mean_delta": row["statistics"]["mean_delta"],
            "confidence_interval_95": row["statistics"][
                "bootstrap_confidence_interval_95"
            ],
            "holm_adjusted_p_value": row["statistics"]["holm_adjusted_p_value"],
        }
    return {
        "schema_version": RETRIEVAL_COHORT_SCORE_SCHEMA,
        "cohort_id": cohort_id,
        "case_count": len(cases),
        "source_case_count": selected_count,
        "dataset_count": len(datasets),
        "languages": sorted(language_groups),
        "cutoff": next(iter(cutoffs)),
        "indexed_passage_counts": sorted(corpus_sizes),
        "groups": group_results,
        "hybrid_ndcg_superiority_over_bm25": bm25_baseline_superiority,
        "eligibility": {
            "external_dataset_revisions_bound": True,
            "dataset_licenses_explicit": True,
            "paired_bilingual_cases": bilingual,
            "minimum_cases_per_language": _MIN_RETRIEVAL_COHORT_CASES_PER_LANGUAGE,
            "enough_cases_per_language": enough_per_language,
        },
        "claim_scope": (
            "external paired retrieval cohort; comparisons establish only differences "
            "against the rerun BM25 baseline under this manifest"
        ),
        "competitive_superiority_established": False,
        "claim_authority": False,
        "artifacts": {
            "manifest_sha256": _canonical_artifact_sha256(manifest),
            "score_sha256s": sorted(score_by_sha),
        },
    }


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _paired_quality_statistics(
    deltas: Sequence[float], *, seed_material: Mapping[str, Any]
) -> dict[str, Any]:
    if not deltas:
        raise ResearchBenchmarkError("paired comparison requires at least one case")
    seed_digest = hashlib.sha256(
        json.dumps(seed_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    bootstrap_random = Random(int(seed_digest[:16], 16))
    case_count = len(deltas)
    bootstrap_means = [
        sum(deltas[bootstrap_random.randrange(case_count)] for _ in range(case_count))
        / case_count
        for _ in range(_COMPARISON_BOOTSTRAP_RESAMPLES)
    ]
    observed = abs(sum(deltas) / case_count)
    if case_count <= _EXACT_SIGN_FLIP_MAX_CASES:
        sign_flip_count = 1 << case_count
        extreme = 0
        for mask in range(sign_flip_count):
            candidate = abs(
                sum(
                    delta if mask & (1 << index) else -delta
                    for index, delta in enumerate(deltas)
                )
                / case_count
            )
            if candidate + 1e-15 >= observed:
                extreme += 1
        p_value = extreme / sign_flip_count
        randomisation_method = "exact_paired_sign_flip"
        randomisation_samples = sign_flip_count
    else:
        sign_random = Random(int(seed_digest[16:32], 16))
        extreme = 1
        for _ in range(_COMPARISON_RANDOMISATION_RESAMPLES):
            candidate = abs(
                sum(
                    delta if sign_random.getrandbits(1) else -delta for delta in deltas
                )
                / case_count
            )
            if candidate + 1e-15 >= observed:
                extreme += 1
        p_value = extreme / (_COMPARISON_RANDOMISATION_RESAMPLES + 1)
        randomisation_method = "deterministic_monte_carlo_paired_sign_flip"
        randomisation_samples = _COMPARISON_RANDOMISATION_RESAMPLES
    return {
        "mean_delta": sum(deltas) / case_count,
        "median_delta": float(median(deltas)),
        "wins": sum(delta > 1e-12 for delta in deltas),
        "ties": sum(abs(delta) <= 1e-12 for delta in deltas),
        "losses": sum(delta < -1e-12 for delta in deltas),
        "bootstrap_confidence_interval_95": {
            "lower": _percentile(bootstrap_means, 0.025),
            "upper": _percentile(bootstrap_means, 0.975),
            "method": "deterministic_paired_percentile_bootstrap",
            "resamples": _COMPARISON_BOOTSTRAP_RESAMPLES,
            "seed_sha256": seed_digest,
        },
        "randomisation_p_value_two_sided": p_value,
        "randomisation_method": randomisation_method,
        "randomisation_samples": randomisation_samples,
    }


def _apply_holm_adjustment(pairwise: list[dict[str, Any]]) -> None:
    ordered = sorted(
        enumerate(pairwise),
        key=lambda item: item[1]["statistics"]["randomisation_p_value_two_sided"],
    )
    running_adjusted = 0.0
    comparison_count = len(ordered)
    for rank, (index, row) in enumerate(ordered):
        raw = float(row["statistics"]["randomisation_p_value_two_sided"])
        adjusted = min(1.0, raw * (comparison_count - rank))
        running_adjusted = max(running_adjusted, adjusted)
        pairwise[index]["statistics"]["holm_adjusted_p_value"] = running_adjusted


def _classify_pairwise_superiority(row: dict[str, Any]) -> None:
    stats = row["statistics"]
    interval = stats["bootstrap_confidence_interval_95"]
    if row["case_count"] < _MIN_SUPERIORITY_CASES:
        row["superiority_state"] = "insufficient_cases"
        row["superior_system"] = None
    elif stats["holm_adjusted_p_value"] > 0.05:
        row["superiority_state"] = "not_established"
        row["superior_system"] = None
    elif interval["lower"] > 0:
        row["superiority_state"] = "left_superior"
        row["superior_system"] = row["left_system"]
    elif interval["upper"] < 0:
        row["superiority_state"] = "right_superior"
        row["superior_system"] = row["right_system"]
    else:
        row["superiority_state"] = "not_established"
        row["superior_system"] = None


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ResearchBenchmarkError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ResearchBenchmarkError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ResearchBenchmarkError(f"{field} must include a timezone")
    return parsed


def _digest(value: Any) -> bool:
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def _git_commit(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _validated_run(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != BENCHMARK_RUN_SCHEMA:
        raise ResearchBenchmarkError(f"schema_version must be {BENCHMARK_RUN_SCHEMA}")
    required_text = ("system", "case_id", "language", "question")
    for field in required_text:
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ResearchBenchmarkError(f"{field} must be non-empty text")
    if value["language"] not in {"en", "zh", "mixed"}:
        raise ResearchBenchmarkError("language must be en, zh, or mixed")
    explicit_latency = "latency_ms" in value
    latency = value.get("latency_ms") if explicit_latency else None
    if latency is not None and (
        isinstance(latency, bool) or not isinstance(latency, (int, float)) or latency < 0
    ):
        raise ResearchBenchmarkError("latency_ms must be null or a non-negative number")
    started = None
    finished = None
    if not explicit_latency or latency is not None:
        started = _timestamp(value.get("started_at"), "started_at")
        finished = _timestamp(value.get("finished_at"), "finished_at")
        if finished < started:
            raise ResearchBenchmarkError("finished_at precedes started_at")
    latency_scope = value.get("latency_scope")
    if explicit_latency and latency is not None and (
        not isinstance(latency_scope, str) or not latency_scope.strip()
    ):
        raise ResearchBenchmarkError("measured latency_ms requires a non-empty latency_scope")
    if explicit_latency and latency is None and latency_scope is not None:
        raise ResearchBenchmarkError("unknown latency_ms requires a null or absent latency_scope")
    if not explicit_latency:
        latency = int((finished - started).total_seconds() * 1000)
        latency_scope = "end_to_end_wall_clock"
    sources = value.get("sources")
    claims = value.get("claims")
    expected_terms = value.get("expected_terms")
    if not isinstance(sources, list) or not isinstance(claims, list):
        raise ResearchBenchmarkError("sources and claims must be arrays")
    if not all(isinstance(source, Mapping) for source in sources):
        raise ResearchBenchmarkError("every source must be an object")
    if not all(isinstance(claim, Mapping) for claim in claims):
        raise ResearchBenchmarkError("every claim must be an object")
    source_ids = [source.get("source_id") for source in sources]
    if not all(isinstance(source_id, str) and source_id.strip() for source_id in source_ids):
        raise ResearchBenchmarkError("every source must have a non-empty source_id")
    if len(source_ids) != len(set(source_ids)):
        raise ResearchBenchmarkError("source_id values must be unique")
    if not isinstance(expected_terms, list):
        raise ResearchBenchmarkError("expected_terms must be an array")
    expected_concepts: list[list[str]] = []
    for item in expected_terms:
        aliases = [item] if isinstance(item, str) else item
        if (
            not isinstance(aliases, list)
            or not aliases
            or not all(isinstance(alias, str) and alias.strip() for alias in aliases)
        ):
            raise ResearchBenchmarkError(
                "each expected term must be text or a non-empty array of text aliases"
            )
        normalised = list(dict.fromkeys(alias.strip() for alias in aliases))
        expected_concepts.append(normalised)
    cost = value.get("cost_usd")
    if cost is not None and (
        isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0
    ):
        raise ResearchBenchmarkError("cost_usd must be null or a non-negative number")
    cost_scope = value.get("cost_scope")
    if cost is not None and (not isinstance(cost_scope, str) or not cost_scope.strip()):
        raise ResearchBenchmarkError("measured cost_usd requires a non-empty cost_scope")
    if cost is None and cost_scope is not None:
        raise ResearchBenchmarkError("unknown cost_usd requires a null or absent cost_scope")
    minimum_sources = value.get("minimum_sources", 3)
    if (
        isinstance(minimum_sources, bool)
        or not isinstance(minimum_sources, int)
        or minimum_sources < 1
    ):
        raise ResearchBenchmarkError("minimum_sources must be a positive integer")
    return {
        **value,
        "started": started,
        "finished": finished,
        "latency_ms": int(latency) if latency is not None else None,
        "latency_scope": latency_scope.strip() if isinstance(latency_scope, str) else None,
        "cost_usd": float(cost) if cost is not None else None,
        "cost_scope": cost_scope.strip() if isinstance(cost_scope, str) else None,
        "expected_concepts": expected_concepts,
    }


def build_synthesis_benchmark_run(
    packet: Mapping[str, Any],
    proposal: Mapping[str, Any],
    measurement: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert one validated synthesis into the canonical deterministic score input."""
    if measurement.get("schema_version") != BENCHMARK_MEASUREMENT_SCHEMA:
        raise ResearchBenchmarkError(
            f"measurement schema_version must be {BENCHMARK_MEASUREMENT_SCHEMA}"
        )
    validated = validate_synthesis_proposal(packet, proposal)
    known = {str(row["evidence_id"]): row for row in packet.get("evidence", [])}
    sources_by_receipt: dict[str, dict[str, Any]] = {}
    for row in known.values():
        receipt = str(row.get("receipt_sha256", ""))
        if not _digest(receipt):
            raise ResearchBenchmarkError("synthesis evidence lacks a valid receipt digest")
        source = {
            "source_id": receipt,
            "url": str(row.get("source_url", "")),
            "receipt_sha256": receipt,
            "content_sha256": str(row.get("content_sha256", "")),
            "fetched_at": row.get("fetched_at"),
        }
        previous = sources_by_receipt.get(receipt)
        if previous is not None and previous != source:
            raise ResearchBenchmarkError(
                "one receipt maps to conflicting synthesis source metadata"
            )
        sources_by_receipt[receipt] = source
    claims: list[dict[str, Any]] = []
    for section in validated["sections"]:
        for paragraph in section["paragraphs"]:
            rows = [known[evidence_id] for evidence_id in paragraph["evidence_ids"]]
            source_ids = list(dict.fromkeys(str(row["receipt_sha256"]) for row in rows))
            claims.append(
                {
                    "text": paragraph["text"],
                    "source_ids": source_ids,
                    "evidence": [
                        {
                            "source_id": str(row["receipt_sha256"]),
                            "quote": str(row["text"]),
                            "evidence_id": str(row["evidence_id"]),
                        }
                        for row in rows
                    ],
                    "review_status": "pending",
                    "position": "supports",
                }
            )
    run = {
        "schema_version": BENCHMARK_RUN_SCHEMA,
        "system": measurement.get("system"),
        "case_id": measurement.get("case_id"),
        "language": measurement.get("language"),
        "question": packet.get("question"),
        "started_at": measurement.get("started_at"),
        "finished_at": measurement.get("finished_at"),
        "cost_usd": measurement.get("cost_usd"),
        "cost_scope": measurement.get("cost_scope"),
        "minimum_sources": measurement.get("minimum_sources", 3),
        "expected_terms": measurement.get("expected_terms", []),
        "require_contradiction": measurement.get("require_contradiction", False),
        "sources": list(sources_by_receipt.values()),
        "claims": claims,
        "source_packet_sha256": packet.get("packet_sha256"),
        "source_run_id": packet.get("run_id"),
    }
    _validated_run(run)
    return run


def build_extractive_benchmark_run(
    plan: Mapping[str, Any],
    research_run: Mapping[str, Any],
    measurement: Mapping[str, Any],
) -> dict[str, Any]:
    """Score a verified extractive run through the canonical synthesis evidence contract."""
    packet = build_synthesis_packet(plan, research_run)
    evidence = packet.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ResearchBenchmarkError("extractive benchmark run requires retrieved evidence")
    proposal = {
        "schema_version": SYNTHESIS_PROPOSAL_SCHEMA,
        "packet_sha256": packet["packet_sha256"],
        "run_id": packet["run_id"],
        "sections": [
            {
                "section_id": outline["section_id"],
                "heading": outline["heading"],
                "paragraphs": [
                    {
                        "text": row["text"],
                        "evidence_ids": [row["evidence_id"]],
                    }
                    for row in evidence
                    if row["subquestion_id"] == outline["section_id"]
                ],
            }
            for outline in packet["outline"]
        ],
    }
    if any(not section["paragraphs"] for section in proposal["sections"]):
        raise ResearchBenchmarkError(
            "extractive benchmark run lacks evidence for an outline section"
        )
    benchmark_run = build_synthesis_benchmark_run(packet, proposal, measurement)
    return {
        **benchmark_run,
        "generation_mode": "deterministic-extractive",
        "source_project_id": research_run.get("project_id"),
    }


def score_benchmark_run(value: Mapping[str, Any]) -> dict[str, Any]:
    """Score one system/case run without an LLM judge or network access."""
    run = _validated_run(value)
    sources = run["sources"]
    claims = run["claims"]
    source_ids = {source.get("source_id") for source in sources if source.get("source_id")}
    citation_valid = 0
    support_scores: list[float] = []
    reviewed = 0
    contradiction_claims = 0
    for claim in claims:
        cited = claim.get("source_ids", [])
        evidence = claim.get("evidence", [])
        cited_ids = set(cited) if isinstance(cited, list) else set()
        if (
            isinstance(cited, list)
            and cited
            and all(isinstance(source_id, str) for source_id in cited)
            and cited_ids <= source_ids
        ):
            citation_valid += 1
        candidate_spans = (
            [span for span in evidence if isinstance(span, Mapping)]
            if isinstance(evidence, list)
            else []
        )
        spans = [
            span
            for span in candidate_spans
            if span.get("source_id") in cited_ids and span.get("source_id") in source_ids
        ]
        support_scores.append(
            lexical_support(
                str(claim.get("text", "")),
                " ".join(str(span.get("quote", "")) for span in spans),
            )
        )
        if claim.get("review_status") in {"accept", "reject"}:
            reviewed += 1
        if claim.get("position") == "contradicts":
            contradiction_claims += 1

    provenance_complete = sum(
        bool(source.get("url"))
        and _digest(source.get("receipt_sha256"))
        and _digest(source.get("content_sha256"))
        and bool(source.get("fetched_at"))
        for source in sources
    )
    domains = {
        registrable_domain(str(source.get("url", ""))) for source in sources if source.get("url")
    }
    authority_scores = [assess_authority(str(source.get("url", ""))).score for source in sources]
    combined_parts = [str(claim.get("text", "")) for claim in claims]
    for claim in claims:
        evidence = claim.get("evidence", [])
        if isinstance(evidence, list):
            combined_parts.extend(
                str(span.get("quote", "")) for span in evidence if isinstance(span, Mapping)
            )
    combined = " ".join(combined_parts)
    covered_terms = sum(
        any(lexical_support(alias, combined) >= 1.0 for alias in aliases)
        for aliases in run["expected_concepts"]
    )
    contradiction_required = bool(run.get("require_contradiction", False))
    metrics = {
        "citation_existence_accuracy": _ratio(citation_valid, len(claims)),
        "citation_lexical_support_mean": _ratio(sum(support_scores), len(support_scores)),
        "citation_lexical_support_pass_rate": _ratio(
            sum(score >= 0.20 for score in support_scores), len(support_scores)
        ),
        "provenance_completeness": _ratio(provenance_complete, len(sources)),
        "expected_term_coverage": _ratio(covered_terms, len(run["expected_concepts"])),
        "expected_concept_count": len(run["expected_concepts"]),
        "source_authority_mean": _ratio(sum(authority_scores), len(authority_scores)),
        "source_domain_diversity": _ratio(len(domains), len(sources)),
        "source_depth": min(1.0, _ratio(len(sources), run["minimum_sources"])),
        "human_review_rate": _ratio(reviewed, len(claims)),
        "contradiction_coverage": 1.0
        if not contradiction_required or contradiction_claims
        else 0.0,
        "source_count": len(sources),
        "claim_count": len(claims),
        "latency_ms": run["latency_ms"],
        "latency_state": "measured" if run["latency_ms"] is not None else "unknown",
        "latency_scope": run["latency_scope"],
        "cost_usd": run["cost_usd"],
        "cost_state": "measured" if run["cost_usd"] is not None else "unknown",
        "cost_scope": run["cost_scope"],
    }
    weights = {
        "citation_existence_accuracy": 0.15,
        "citation_lexical_support_pass_rate": 0.15,
        "provenance_completeness": 0.15,
        "expected_term_coverage": 0.15,
        "source_authority_mean": 0.10,
        "source_domain_diversity": 0.05,
        "source_depth": 0.10,
        "human_review_rate": 0.10,
        "contradiction_coverage": 0.05,
    }
    quality = sum(float(metrics[name]) * weight for name, weight in weights.items())
    return {
        "schema_version": BENCHMARK_SCORE_SCHEMA,
        "system": run["system"],
        "case_id": run["case_id"],
        "language": run["language"],
        "metrics": metrics,
        "quality_score": quality,
        "weights": weights,
        "limitations": [
            "lexical support does not establish semantic entailment",
            "domain authority is a conservative heuristic",
            "quality_score excludes model-judge insight and readability scores",
        ],
    }


def compare_scores(
    scores: Sequence[Mapping[str, Any]],
    *,
    system_aliases: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Aggregate comparable cases per system and expose quality/efficiency separately."""
    if not scores:
        raise ResearchBenchmarkError("at least one score is required")
    cases_by_system: dict[str, set[str]] = {}
    members_by_system: dict[str, set[str]] = {}
    rows_by_system: dict[str, list[Mapping[str, Any]]] = {}
    seen_runs: set[tuple[str, str]] = set()
    aliases = dict(system_aliases or {})
    reference_weights: dict[str, float] | None = None
    if not all(
        isinstance(source, str)
        and source.strip()
        and isinstance(target, str)
        and target.strip()
        for source, target in aliases.items()
    ):
        raise ResearchBenchmarkError("system aliases must map non-empty names to non-empty names")
    for score in scores:
        if score.get("schema_version") != BENCHMARK_SCORE_SCHEMA:
            raise ResearchBenchmarkError("comparison received an unrecognised score")
        producer = score.get("system")
        case_value = score.get("case_id")
        metrics = score.get("metrics")
        weights = score.get("weights")
        quality = score.get("quality_score")
        if not isinstance(producer, str) or not producer.strip():
            raise ResearchBenchmarkError("comparison score system must be non-empty text")
        if not isinstance(case_value, str) or not case_value.strip():
            raise ResearchBenchmarkError("comparison score case_id must be non-empty text")
        if not isinstance(metrics, Mapping) or not isinstance(weights, Mapping):
            raise ResearchBenchmarkError("comparison score metrics and weights must be objects")
        if isinstance(quality, bool) or not isinstance(quality, (int, float)):
            raise ResearchBenchmarkError("comparison quality_score must be numeric")
        typed_weights: dict[str, float] = {}
        recomputed_quality = 0.0
        for name, weight in weights.items():
            metric = metrics.get(name)
            if (
                not isinstance(name, str)
                or isinstance(weight, bool)
                or not isinstance(weight, (int, float))
                or isinstance(metric, bool)
                or not isinstance(metric, (int, float))
            ):
                raise ResearchBenchmarkError(
                    "comparison weighted metrics and weights must be numeric"
                )
            typed_weights[name] = float(weight)
            recomputed_quality += float(metric) * float(weight)
        if abs(recomputed_quality - float(quality)) > 1e-12:
            raise ResearchBenchmarkError("comparison quality_score does not match weighted metrics")
        if reference_weights is None:
            reference_weights = typed_weights
        elif typed_weights != reference_weights:
            raise ResearchBenchmarkError("comparison scores must use identical metric weights")
        system = aliases.get(producer, producer)
        case_id = case_value
        run_key = (system, case_id)
        if run_key in seen_runs:
            raise ResearchBenchmarkError("comparison contains a duplicate system/case score")
        seen_runs.add(run_key)
        cases_by_system.setdefault(system, set()).add(case_id)
        members_by_system.setdefault(system, set()).add(producer)
        rows_by_system.setdefault(system, []).append(score)
    case_sets = list(cases_by_system.values())
    if any(case_set != case_sets[0] for case_set in case_sets[1:]):
        raise ResearchBenchmarkError("systems must be scored on identical case sets")
    systems: list[dict[str, Any]] = []
    for system in sorted(cases_by_system):
        rows = rows_by_system[system]
        costs = [row["metrics"].get("cost_usd") for row in rows]
        scopes = {row["metrics"].get("cost_scope") for row in rows}
        cost_comparable = (
            all(isinstance(cost, (int, float)) for cost in costs)
            and len(scopes) == 1
            and all(isinstance(scope, str) and scope.strip() for scope in scopes)
        )
        latencies = [row["metrics"].get("latency_ms") for row in rows]
        latency_scopes = {row["metrics"].get("latency_scope") for row in rows}
        latency_comparable = all(
            isinstance(latency, (int, float)) for latency in latencies
        ) and len(latency_scopes) == 1 and all(
            isinstance(scope, str) and scope.strip() for scope in latency_scopes
        )
        systems.append(
            {
                "system": system,
                "system_members": sorted(members_by_system[system]),
                "case_count": len(rows),
                "quality_score_mean": sum(float(row["quality_score"]) for row in rows) / len(rows),
                "latency_ms_mean": (
                    sum(float(latency) for latency in latencies) / len(rows)
                    if latency_comparable
                    else None
                ),
                "latency_scope": next(iter(latency_scopes)) if latency_comparable else None,
                "latency_comparable": latency_comparable,
                "cost_usd_total": sum(float(cost) for cost in costs) if cost_comparable else None,
                "cost_scope": next(iter(scopes)) if cost_comparable else None,
                "cost_comparable": cost_comparable,
            }
        )
    comparable_scopes = {row["cost_scope"] for row in systems if row["cost_comparable"]}
    all_costs_comparable = len(comparable_scopes) == 1 and all(
        row["cost_comparable"] for row in systems
    )
    comparable_latency_scopes = {
        row["latency_scope"] for row in systems if row["latency_comparable"]
    }
    all_latencies_comparable = len(comparable_latency_scopes) == 1 and all(
        row["latency_comparable"] for row in systems
    )
    systems.sort(
        key=lambda row: (
            -row["quality_score_mean"],
            row["cost_usd_total"] if all_costs_comparable else 0.0,
            row["latency_ms_mean"] if all_latencies_comparable else 0.0,
            row["system"],
        )
    )
    pairwise_quality: list[dict[str, Any]] = []
    metric_names = sorted(reference_weights or {})
    for left_system, right_system in combinations(sorted(rows_by_system), 2):
        left_by_case = {str(row["case_id"]): row for row in rows_by_system[left_system]}
        right_by_case = {str(row["case_id"]): row for row in rows_by_system[right_system]}
        case_rows = []
        for case_id in sorted(case_sets[0]):
            left_quality = float(left_by_case[case_id]["quality_score"])
            right_quality = float(right_by_case[case_id]["quality_score"])
            case_rows.append(
                {
                    "case_id": case_id,
                    "left_quality_score": left_quality,
                    "right_quality_score": right_quality,
                    "delta": left_quality - right_quality,
                }
            )
        deltas = [row["delta"] for row in case_rows]
        metric_mean_deltas = {
            name: sum(
                float(left_by_case[case_id]["metrics"][name])
                - float(right_by_case[case_id]["metrics"][name])
                for case_id in sorted(case_sets[0])
            )
            / len(case_rows)
            for name in metric_names
        }
        pairwise_quality.append(
            {
                "left_system": left_system,
                "right_system": right_system,
                "case_count": len(case_rows),
                "cases": case_rows,
                "metric_mean_deltas": metric_mean_deltas,
                "statistics": _paired_quality_statistics(
                    deltas,
                    seed_material={
                        "left_system": left_system,
                        "right_system": right_system,
                        "cases": case_rows,
                    },
                ),
            }
        )
    _apply_holm_adjustment(pairwise_quality)
    for row in pairwise_quality:
        _classify_pairwise_superiority(row)
    leader = systems[0]["system"]
    leader_pairs = [
        row
        for row in pairwise_quality
        if leader in {row["left_system"], row["right_system"]}
    ]
    leader_statistically_superior = bool(leader_pairs) and len(leader_pairs) == len(systems) - 1 and all(
        row["superior_system"] == leader for row in leader_pairs
    )
    return {
        "schema_version": "giga.research-benchmark-comparison.v3",
        "case_ids": sorted(case_sets[0]),
        "systems": systems,
        "system_aliases": dict(sorted(aliases.items())),
        "leader": leader,
        "leader_statistically_superior": leader_statistically_superior,
        "pairwise_quality": pairwise_quality,
        "cost_comparable": all_costs_comparable,
        "cost_comparison_note": (
            "all systems report measured cost under one identical scope"
            if all_costs_comparable
            else "cost is excluded from ranking because it is unknown or measured under different scopes"
        ),
        "latency_comparable": all_latencies_comparable,
        "latency_comparison_note": (
            "all systems report measured latency under one identical scope"
            if all_latencies_comparable
            else "latency is excluded from ranking because it is unknown or measured under different scopes"
        ),
        "claim_boundary": (
            "leader is descriptive for this exact case set and deterministic metric suite; "
            "superiority requires at least five paired cases, a 95% paired bootstrap interval "
            "excluding zero and a Holm-adjusted two-sided paired randomisation p-value <= 0.05"
        ),
    }


def load_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchBenchmarkError(f"cannot read benchmark JSON from {path}") from exc
    if not isinstance(value, Mapping):
        raise ResearchBenchmarkError("benchmark JSON must contain an object")
    return value


def import_deepresearch_bench_cases(
    path: Path, *, require_official_set: bool = True
) -> dict[str, Any]:
    """Validate the Apache-2.0 DRB query JSONL and emit canonical case metadata."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ResearchBenchmarkError(f"cannot read DeepResearch Bench cases from {path}") from exc
    cases: list[dict[str, Any]] = []
    identifiers: set[int] = set()
    for line_number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ResearchBenchmarkError(f"invalid DRB JSON on line {line_number}") from exc
        if not isinstance(row, Mapping):
            raise ResearchBenchmarkError(f"DRB line {line_number} must be an object")
        identifier = row.get("id")
        language = row.get("language")
        topic = row.get("topic")
        prompt = row.get("prompt")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier < 1:
            raise ResearchBenchmarkError(f"DRB line {line_number} has an invalid id")
        if identifier in identifiers:
            raise ResearchBenchmarkError("DRB case ids must be unique")
        if language not in {"en", "zh"}:
            raise ResearchBenchmarkError(f"DRB case {identifier} has an invalid language")
        if (
            not isinstance(topic, str)
            or not topic.strip()
            or not isinstance(prompt, str)
            or not prompt.strip()
        ):
            raise ResearchBenchmarkError(f"DRB case {identifier} lacks topic or prompt text")
        identifiers.add(identifier)
        cases.append(
            {
                "case_id": f"drb-{identifier:03d}",
                "upstream_id": identifier,
                "language": language,
                "topic": topic.strip(),
                "question": prompt.strip(),
            }
        )
    cases.sort(key=lambda row: row["upstream_id"])
    languages = Counter(row["language"] for row in cases)
    if require_official_set and (
        len(cases) != 100
        or languages != Counter({"en": 50, "zh": 50})
        or identifiers != set(range(1, 101))
    ):
        raise ResearchBenchmarkError(
            "official DRB set must contain ids 1-100 with 50 en and 50 zh cases"
        )
    return {
        "schema_version": "giga.research-benchmark-case-manifest.v1",
        "benchmark": "DeepResearch Bench",
        "upstream_repository": "https://github.com/Ayanami0730/deep_research_bench",
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "upstream_license": "Apache-2.0",
        "case_count": len(cases),
        "languages": dict(sorted(languages.items())),
        "cases": cases,
        "execution_state": "cases_imported_not_run",
    }


def _jsonl(path: Path, label: str) -> list[Mapping[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ResearchBenchmarkError(f"cannot read {label} JSONL from {path}") from exc
    rows: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ResearchBenchmarkError(f"invalid {label} JSON on line {line_number}") from exc
        if not isinstance(row, Mapping):
            raise ResearchBenchmarkError(f"{label} line {line_number} must be an object")
        rows.append(row)
    return rows


def _csv_rows(path: Path, label: str) -> list[Mapping[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ResearchBenchmarkError(f"{label} CSV lacks a header")
            rows = [dict(row) for row in reader]
    except OSError as exc:
        raise ResearchBenchmarkError(f"cannot read {label} CSV from {path}") from exc
    if not rows:
        raise ResearchBenchmarkError(f"{label} CSV cannot be empty")
    return rows


def _csv_count(row: Mapping[str, str], field: str, label: str) -> int:
    value = row.get(field)
    try:
        number = float(value) if value is not None else float("nan")
    except ValueError as exc:
        raise ResearchBenchmarkError(f"{label} {field} must be a non-negative integer") from exc
    if not isfinite(number) or number < 0 or not number.is_integer():
        raise ResearchBenchmarkError(f"{label} {field} must be a non-negative integer")
    return int(number)


def import_reportbench_cases(
    path: Path, *, require_official_set: bool = True
) -> dict[str, Any]:
    """Validate the Apache-2.0 ReportBench v1.1 academic-survey task contract."""
    rows = _jsonl(path, "ReportBench case")
    cases: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for line_number, row in enumerate(rows, start=1):
        identifier = row.get("arxiv_id")
        prompt = row.get("prompt")
        domain = row.get("application_domain")
        update_date = row.get("update_date")
        if (
            not isinstance(identifier, str)
            or not identifier.strip()
            or not isinstance(prompt, str)
            or not prompt.strip()
            or not isinstance(domain, str)
            or not domain.strip()
            or not isinstance(update_date, str)
            or not update_date.strip()
        ):
            raise ResearchBenchmarkError(
                f"ReportBench line {line_number} lacks arxiv_id, prompt, domain or update_date"
            )
        identifier = identifier.strip()
        if identifier in identifiers:
            raise ResearchBenchmarkError("ReportBench arxiv_id values must be unique")
        identifiers.add(identifier)
        cases.append(
            {
                "case_id": f"reportbench-{identifier}",
                "arxiv_id": identifier,
                "question": prompt.strip(),
                "application_domain": domain.strip(),
                "knowledge_cutoff": update_date.strip(),
            }
        )
    cases.sort(key=lambda row: row["arxiv_id"])
    artifact_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if require_official_set and (
        len(cases) != 100 or artifact_sha256 != REPORTBENCH_V1_1_SHA256
    ):
        raise ResearchBenchmarkError(
            "official ReportBench v1.1 requires the exact pinned 100-case artifact"
        )
    return {
        "schema_version": REPORTBENCH_CASE_SCHEMA,
        "benchmark": "ReportBench v1.1",
        "upstream_repository": "https://github.com/ByteDance-BandAI/ReportBench",
        "upstream_commit": REPORTBENCH_COMMIT,
        "upstream_license": "Apache-2.0",
        "artifact_sha256": artifact_sha256,
        "case_count": len(cases),
        "application_domains": dict(
            sorted(Counter(row["application_domain"] for row in cases).items())
        ),
        "cases": cases,
        "execution_state": "cases_imported_not_run",
    }


def import_reportbench_results(
    case_path: Path,
    related_work_csv: Path,
    statement_metrics_csv: Path,
    *,
    system: str,
    require_official_set: bool = True,
) -> dict[str, Any]:
    """Reproduce ReportBench count-based aggregates without rerunning its model judges."""
    if not isinstance(system, str) or not system.strip():
        raise ResearchBenchmarkError("ReportBench result system must be non-empty text")
    manifest = import_reportbench_cases(case_path, require_official_set=require_official_set)
    expected = {row["arxiv_id"] for row in manifest["cases"]}
    related_rows = _csv_rows(related_work_csv, "ReportBench related-work result")
    statement_rows = _csv_rows(statement_metrics_csv, "ReportBench statement result")

    def keyed(
        rows: Sequence[Mapping[str, str]], label: str
    ) -> dict[str, Mapping[str, str]]:
        output: dict[str, Mapping[str, str]] = {}
        for row in rows:
            identifier = row.get("arxiv_id")
            if not isinstance(identifier, str) or not identifier.strip():
                raise ResearchBenchmarkError(f"{label} row lacks arxiv_id")
            identifier = identifier.strip()
            if identifier in output:
                raise ResearchBenchmarkError(f"{label} arxiv_id values must be unique")
            output[identifier] = row
        if set(output) != expected:
            missing = sorted(expected - set(output))
            extra = sorted(set(output) - expected)
            raise ResearchBenchmarkError(
                f"{label} case set differs from the ReportBench manifest: "
                f"missing={missing[:5]} extra={extra[:5]}"
            )
        return output

    related = keyed(related_rows, "ReportBench related-work result")
    statements = keyed(statement_rows, "ReportBench statement result")
    totals = Counter()
    case_metrics = []
    for identifier in sorted(expected):
        related_row = related[identifier]
        statement_row = statements[identifier]
        predicted = _csv_count(related_row, "predicted_count", identifier)
        ground_truth = _csv_count(related_row, "ground_truth_count", identifier)
        intersection = _csv_count(related_row, "intersection_count", identifier)
        citations = _csv_count(statement_row, "total_citations", identifier)
        non_citations = _csv_count(statement_row, "total_no_citations", identifier)
        matched = _csv_count(statement_row, "matched_statements", identifier)
        aligned = _csv_count(statement_row, "aligned_statements", identifier)
        non_cited_correct = _csv_count(statement_row, "no_citations_correct", identifier)
        non_cited_incorrect = _csv_count(statement_row, "no_citations_incorrect", identifier)
        non_cited_tie = _csv_count(statement_row, "no_citations_tie", identifier)
        if intersection > min(predicted, ground_truth):
            raise ResearchBenchmarkError(
                f"ReportBench {identifier} intersection exceeds a source denominator"
            )
        if matched > citations or aligned > matched:
            raise ResearchBenchmarkError(
                f"ReportBench {identifier} citation counts violate their denominators"
            )
        if non_cited_correct + non_cited_incorrect + non_cited_tie > non_citations:
            raise ResearchBenchmarkError(
                f"ReportBench {identifier} non-cited verdicts exceed extracted statements"
            )
        counts = {
            "predicted_references": predicted,
            "ground_truth_references": ground_truth,
            "matched_references": intersection,
            "cited_statements": citations,
            "source_matched_statements": matched,
            "aligned_cited_statements": aligned,
            "non_cited_statements": non_citations,
            "non_cited_correct": non_cited_correct,
            "non_cited_incorrect": non_cited_incorrect,
            "non_cited_tie": non_cited_tie,
            "non_cited_unverified": non_citations
            - non_cited_correct
            - non_cited_incorrect
            - non_cited_tie,
        }
        totals.update(counts)
        case_metrics.append({"arxiv_id": identifier, **counts})
    evaluated_non_cited = totals["non_cited_correct"] + totals["non_cited_incorrect"]
    return {
        "schema_version": "giga.reportbench-result-import.v1",
        "benchmark": "ReportBench v1.1",
        "system": system.strip(),
        "upstream_commit": REPORTBENCH_COMMIT,
        "case_count": len(case_metrics),
        "case_ids": [f"reportbench-{row['arxiv_id']}" for row in case_metrics],
        "metrics": {
            "reference_precision": _ratio(
                totals["matched_references"], totals["predicted_references"]
            ),
            "reference_recall": _ratio(
                totals["matched_references"], totals["ground_truth_references"]
            ),
            "reference_f1": _ratio(
                2 * totals["matched_references"],
                totals["predicted_references"] + totals["ground_truth_references"],
            ),
            "references_per_report": _ratio(totals["predicted_references"], len(case_metrics)),
            "citation_source_match_rate": _ratio(
                totals["source_matched_statements"], totals["cited_statements"]
            ),
            "citation_statement_alignment_rate": _ratio(
                totals["aligned_cited_statements"], totals["source_matched_statements"]
            ),
            "non_cited_factual_accuracy": _ratio(
                totals["non_cited_correct"], evaluated_non_cited
            ),
            "non_cited_verdict_coverage": _ratio(
                evaluated_non_cited + totals["non_cited_tie"],
                totals["non_cited_statements"],
            ),
            "cited_statements_per_report": _ratio(
                totals["cited_statements"], len(case_metrics)
            ),
            "non_cited_statements_per_report": _ratio(
                totals["non_cited_statements"], len(case_metrics)
            ),
        },
        "counts": dict(sorted(totals.items())),
        "cases": case_metrics,
        "artifacts": {
            "cases_sha256": manifest["artifact_sha256"],
            "related_work_sha256": hashlib.sha256(related_work_csv.read_bytes()).hexdigest(),
            "statement_metrics_sha256": hashlib.sha256(
                statement_metrics_csv.read_bytes()
            ).hexdigest(),
        },
        "configured_default_judge_model_at_upstream_commit": "gpt-4o-mini",
        "artifact_judge_models": None,
        "artifact_judge_model_state": "not_embedded_in_aggregate_csv_rows",
        "execution_state": "official_shape_results_imported_not_rerun",
        "claim_boundary": (
            "count-based aggregates reproduced from upstream result CSVs; semantic judgments, "
            "web fact checks, latency and cost were not rerun or inferred"
        ),
    }


def import_pdrbench_cases(
    path: Path, *, require_official_set: bool = True
) -> dict[str, Any]:
    """Validate one pinned Personalized Deep Research Bench query cohort."""
    rows = _jsonl(path, "PDR-Bench case")
    artifact_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    official = PDRBENCH_OFFICIAL_ARTIFACTS.get(artifact_sha256)
    if require_official_set and official is None:
        raise ResearchBenchmarkError(
            "official PDR-Bench import requires an exact pinned query artifact"
        )
    identifiers: set[int] = set()
    task_persona_pairs: set[tuple[int, str]] = set()
    cases: list[dict[str, Any]] = []
    languages: set[str] = set()
    for line_number, row in enumerate(rows, start=1):
        identifier = row.get("id")
        task_identifier = row.get("taskid")
        persona_identifier = row.get("userid")
        domain = row.get("domain")
        language = row.get("language")
        task = row.get("task")
        query = row.get("query")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0:
            raise ResearchBenchmarkError(f"PDR-Bench line {line_number} has invalid id")
        if (
            isinstance(task_identifier, bool)
            or not isinstance(task_identifier, int)
            or task_identifier <= 0
        ):
            raise ResearchBenchmarkError(
                f"PDR-Bench line {line_number} has invalid taskid"
            )
        if (
            not isinstance(persona_identifier, str)
            or not persona_identifier.strip()
            or not isinstance(domain, str)
            or not domain.strip()
            or language not in {"en", "zh"}
            or not isinstance(task, str)
            or not task.strip()
            or not isinstance(query, str)
            or not query.strip()
        ):
            raise ResearchBenchmarkError(
                f"PDR-Bench line {line_number} lacks persona, domain, language, task or query"
            )
        if task.strip() not in query:
            raise ResearchBenchmarkError(
                f"PDR-Bench line {line_number} query does not contain its paired task"
            )
        pair = (task_identifier, persona_identifier.strip())
        if identifier in identifiers or pair in task_persona_pairs:
            raise ResearchBenchmarkError("PDR-Bench ids and task-persona pairs must be unique")
        identifiers.add(identifier)
        task_persona_pairs.add(pair)
        languages.add(language)
        cases.append(
            {
                "case_id": f"pdrbench-{language}-{identifier:03d}",
                "benchmark_id": identifier,
                "task_id": task_identifier,
                "persona_id": persona_identifier.strip(),
                "domain": domain.strip(),
                "language": language,
                "task": task.strip(),
                "prompt": query,
                "prompt_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            }
        )
    cases.sort(key=lambda row: row["benchmark_id"])
    if len(languages) != 1:
        raise ResearchBenchmarkError("one PDR-Bench artifact must contain exactly one language")
    if require_official_set and (
        len(cases) != official["case_count"] or next(iter(languages)) != official["language"]
    ):
        raise ResearchBenchmarkError("PDR-Bench artifact metadata differs from its pinned cohort")
    if official and official["case_count"] == 250 and identifiers != set(range(1, 251)):
        raise ResearchBenchmarkError(
            "PDR-Bench task-universe ids must form the complete 1-250 set"
        )
    language = next(iter(languages))
    return {
        "schema_version": PDRBENCH_CASE_SCHEMA,
        "benchmark": "Personalized Deep Research Bench",
        "upstream_repository": (
            "https://github.com/OPPO-PersonalAI/PersonalizedDeepResearchBench"
        ),
        "upstream_commit": PDRBENCH_COMMIT,
        "upstream_license": "Apache-2.0",
        "artifact_sha256": artifact_sha256,
        "cohort": official["cohort"] if official else "custom_contract_test",
        "language": language,
        "case_count": len(cases),
        "task_count": len({row["task_id"] for row in cases}),
        "persona_count": len({row["persona_id"] for row in cases}),
        "task_persona_pair_count": len(task_persona_pairs),
        "domains": dict(sorted(Counter(row["domain"] for row in cases).items())),
        "cases": cases,
        "execution_state": "cases_imported_not_run",
    }


def _pdrbench_result_rows(
    path: Path,
    expected: set[int],
    label: str,
) -> dict[int, Mapping[str, Any]]:
    rows = _jsonl(path, label)
    keyed: dict[int, Mapping[str, Any]] = {}
    for row in rows:
        identifier = row.get("id")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0:
            raise ResearchBenchmarkError(f"{label} row has invalid id")
        if identifier in keyed:
            raise ResearchBenchmarkError(f"{label} ids must be unique")
        if "error" in row:
            raise ResearchBenchmarkError(f"{label} row {identifier} contains an evaluation error")
        keyed[identifier] = row
    if set(keyed) != expected:
        missing = sorted(expected - set(keyed))
        extra = sorted(set(keyed) - expected)
        raise ResearchBenchmarkError(
            f"{label} case set differs from the PDR-Bench manifest: "
            f"missing={missing[:5]} extra={extra[:5]}"
        )
    return keyed


def _pdrbench_score(row: Mapping[str, Any], field: str, label: str) -> float:
    value = row.get(field)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or not 0 <= float(value) <= 10
    ):
        raise ResearchBenchmarkError(f"{label} {field} must be a finite score from 0 to 10")
    return float(value)


def import_pdrbench_results(
    case_path: Path,
    personalization_path: Path,
    quality_path: Path,
    reliability_path: Path,
    *,
    system: str,
    require_official_set: bool = True,
) -> dict[str, Any]:
    """Import a complete P/Q/R cohort without rerunning PDR-Bench model judges."""
    if not isinstance(system, str) or not system.strip():
        raise ResearchBenchmarkError("PDR-Bench result system must be non-empty text")
    manifest = import_pdrbench_cases(case_path, require_official_set=require_official_set)
    expected = {row["benchmark_id"] for row in manifest["cases"]}
    personalization = _pdrbench_result_rows(
        personalization_path, expected, "PDR-Bench personalization result"
    )
    quality = _pdrbench_result_rows(quality_path, expected, "PDR-Bench quality result")
    reliability = _pdrbench_result_rows(
        reliability_path, expected, "PDR-Bench reliability result"
    )
    score_fields = (
        *_PDRBENCH_PERSONALIZATION_DIMENSIONS,
        "p_overall_score",
        *_PDRBENCH_QUALITY_DIMENSIONS,
        "q_overall_score",
    )
    score_totals = Counter({field: 0.0 for field in score_fields})
    case_metrics: list[dict[str, Any]] = []
    reliability_counts = Counter()
    for identifier in sorted(expected):
        p_row = personalization[identifier]
        q_row = quality[identifier]
        scores: dict[str, float] = {}
        for field in (*_PDRBENCH_PERSONALIZATION_DIMENSIONS, "p_overall_score"):
            scores[field] = _pdrbench_score(p_row, field, f"PDR-Bench case {identifier}")
        for field in (*_PDRBENCH_QUALITY_DIMENSIONS, "q_overall_score"):
            scores[field] = _pdrbench_score(q_row, field, f"PDR-Bench case {identifier}")
        p_values = [scores[field] for field in _PDRBENCH_PERSONALIZATION_DIMENSIONS]
        q_values = [scores[field] for field in _PDRBENCH_QUALITY_DIMENSIONS]
        if not min(p_values) <= scores["p_overall_score"] <= max(p_values):
            raise ResearchBenchmarkError(
                f"PDR-Bench case {identifier} P overall lies outside its dimensions"
            )
        if not min(q_values) <= scores["q_overall_score"] <= max(q_values):
            raise ResearchBenchmarkError(
                f"PDR-Bench case {identifier} Q overall lies outside its dimensions"
            )
        score_totals.update(scores)

        r_row = reliability[identifier]
        claims = r_row.get("factual_claims")
        grouped = r_row.get("factual_claims_deduped")
        if not isinstance(claims, list) or not isinstance(grouped, Mapping):
            raise ResearchBenchmarkError(
                f"PDR-Bench reliability case {identifier} lacks factual claim contracts"
            )
        row_counts = Counter()
        row_counts["extracted_factual_claims"] = len(claims)
        for source_url, source in grouped.items():
            if not isinstance(source_url, str) or not isinstance(source, Mapping):
                raise ResearchBenchmarkError("PDR-Bench reliability sources must be objects")
            facts = source.get("facts")
            if not isinstance(facts, list) or not all(isinstance(fact, str) for fact in facts):
                raise ResearchBenchmarkError("PDR-Bench reliability source lacks facts")
            row_counts["deduplicated_factual_claims"] += len(facts)
            if source_url in {"", "no_url"}:
                row_counts["uncited_claims"] += len(facts)
                continue
            row_counts["cited_claims"] += len(facts)
            if source.get("validate_error") is not None:
                row_counts["validation_error_claims"] += len(facts)
                continue
            validations = source.get("validate_res")
            if not isinstance(validations, list) or len(validations) != len(facts):
                raise ResearchBenchmarkError(
                    "PDR-Bench reliability validation count must match cited facts"
                )
            for validation in validations:
                if not isinstance(validation, Mapping):
                    raise ResearchBenchmarkError(
                        "PDR-Bench reliability validation must be an object"
                    )
                verdict = validation.get("result")
                if verdict not in {"supported", "unsupported", "unknown"}:
                    raise ResearchBenchmarkError(
                        "PDR-Bench reliability validation has an unknown result"
                    )
                row_counts[f"{verdict}_claims"] += 1
        reliability_counts.update(row_counts)
        case_metrics.append({"benchmark_id": identifier, **scores, **dict(row_counts)})

    count = len(case_metrics)
    means = {field: score_totals[field] / count for field in score_fields}
    factual_accuracy = 10 * _ratio(
        reliability_counts["supported_claims"], reliability_counts["cited_claims"]
    )
    citation_coverage = 10 * _ratio(
        reliability_counts["cited_claims"],
        reliability_counts["deduplicated_factual_claims"],
    )
    reliability_score = (factual_accuracy + citation_coverage) / 2
    return {
        "schema_version": "giga.pdrbench-result-import.v1",
        "benchmark": "Personalized Deep Research Bench",
        "system": system.strip(),
        "upstream_commit": PDRBENCH_COMMIT,
        "cohort": manifest["cohort"],
        "language": manifest["language"],
        "case_count": count,
        "case_ids": [f"pdrbench-{manifest['language']}-{identifier:03d}" for identifier in sorted(expected)],
        "metrics": {
            **means,
            "factual_accuracy": factual_accuracy,
            "citation_coverage": citation_coverage,
            "r_overall_score": reliability_score,
            "pqr_overall_score": (
                means["p_overall_score"] + means["q_overall_score"] + reliability_score
            )
            / 3,
        },
        "reliability_counts": dict(sorted(reliability_counts.items())),
        "cases": case_metrics,
        "artifacts": {
            "cases_sha256": manifest["artifact_sha256"],
            "personalization_sha256": hashlib.sha256(
                personalization_path.read_bytes()
            ).hexdigest(),
            "quality_sha256": hashlib.sha256(quality_path.read_bytes()).hexdigest(),
            "reliability_sha256": hashlib.sha256(reliability_path.read_bytes()).hexdigest(),
        },
        "configured_quality_and_personalization_judge_at_upstream_commit": "gpt-5",
        "configured_reliability_judge_at_upstream_commit": "gpt-5-mini",
        "artifact_judge_models": None,
        "artifact_judge_model_state": "not_embedded_in_result_rows",
        "execution_state": "official_shape_results_imported_not_rerun",
        "claim_boundary": (
            "P/Q scores and R verdicts imported from complete upstream-shape artifacts; "
            "judge calls, web retrieval, latency and cost were not rerun or inferred"
        ),
    }


def _deepsynth_task_id(value: Any, label: str) -> str:
    if isinstance(value, bool):
        raise ResearchBenchmarkError(f"{label} task id must be a positive integer")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and value.strip().isdigit():
        number = int(value.strip())
    else:
        raise ResearchBenchmarkError(f"{label} task id must be a positive integer")
    if not 1 <= number <= 999:
        raise ResearchBenchmarkError(f"{label} task id must be between 1 and 999")
    return f"{number:03d}"


def _deepsynth_parse_answer(value: Any, label: str) -> Any:
    if not isinstance(value, str):
        return value
    content = value.strip()
    lowered = content.lower()
    if lowered.startswith("<answer>"):
        content = content[len("<answer>") :].lstrip(" :\t\r\n")
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ResearchBenchmarkError(
            f"{label} string answer must contain strict JSON, optionally after <Answer>"
        ) from exc


def _deepsynth_records(
    payload: Any,
    *,
    label: str,
    answer_field: str,
) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    answers: dict[str, Any] = {}
    metadata: dict[str, Mapping[str, Any]] = {}
    if isinstance(payload, Mapping):
        entries = [(identifier, answer, {}) for identifier, answer in payload.items()]
    elif isinstance(payload, list):
        entries = []
        for index, row in enumerate(payload, start=1):
            if not isinstance(row, Mapping):
                raise ResearchBenchmarkError(f"{label} row {index} must be an object")
            if "Question Number" not in row or answer_field not in row:
                raise ResearchBenchmarkError(
                    f"{label} row {index} lacks Question Number or {answer_field}"
                )
            entries.append((row["Question Number"], row[answer_field], row))
    else:
        raise ResearchBenchmarkError(f"{label} must be a task map or row array")
    if not entries:
        raise ResearchBenchmarkError(f"{label} cannot be empty")
    for raw_identifier, answer, row_metadata in entries:
        identifier = _deepsynth_task_id(raw_identifier, label)
        if identifier in answers:
            raise ResearchBenchmarkError(f"{label} task ids must be unique")
        answers[identifier] = _deepsynth_parse_answer(answer, f"{label} {identifier}")
        metadata[identifier] = row_metadata
    return answers, metadata


def _deepsynth_normalize(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "none"
    if isinstance(value, float):
        if not isfinite(value):
            raise ResearchBenchmarkError("DeepSynth answers cannot contain non-finite numbers")
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value).strip().lower()


def _deepsynth_flatten(value: Any, prefix: str = "") -> dict[str, str]:
    if isinstance(value, Mapping):
        flattened: dict[str, str] = {}
        for key, child in value.items():
            if not isinstance(key, str) or not key:
                raise ResearchBenchmarkError("DeepSynth object keys must be non-empty strings")
            child_prefix = f"{prefix}.{key}" if prefix else key
            flattened.update(_deepsynth_flatten(child, child_prefix))
        return flattened
    if isinstance(value, list):
        flattened = {}
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            flattened.update(_deepsynth_flatten(child, child_prefix))
        return flattened
    return {prefix or "<root>": _deepsynth_normalize(value)}


def _deepsynth_partial_similarity(gold: str, prediction: str) -> float:
    if gold == prediction:
        return 1.0
    try:
        gold_number = float(gold)
        prediction_number = float(prediction)
    except ValueError:
        gold_characters = set(gold)
        prediction_characters = set(prediction)
        union = gold_characters | prediction_characters
        similarity = len(gold_characters & prediction_characters) / len(union) if union else 1.0
        if gold in prediction or prediction in gold:
            similarity = max(similarity, 0.6)
        return similarity
    if gold_number == 0:
        return 1.0 if prediction_number == 0 else 0.0
    relative_error = abs(gold_number - prediction_number) / abs(gold_number)
    if relative_error < 0.01:
        return 0.9
    if relative_error < 0.05:
        return 0.7
    if relative_error < 0.10:
        return 0.5
    return 0.0


def _deepsynth_optional_measurement(
    row: Mapping[str, Any], field: str, identifier: str
) -> float | None:
    value = row.get(field)
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or float(value) < 0
    ):
        raise ResearchBenchmarkError(
            f"DeepSynth prediction {identifier} {field} must be finite and non-negative"
        )
    return float(value)


def score_deepsynth_static(
    gold_path: Path,
    predictions_path: Path,
    *,
    system: str,
) -> dict[str, Any]:
    """Score a complete DeepSynth-shaped cohort with strict task-set binding."""
    if not isinstance(system, str) or not system.strip():
        raise ResearchBenchmarkError("DeepSynth system must be non-empty text")
    try:
        gold_payload = json.loads(gold_path.read_text(encoding="utf-8"))
        prediction_payload = json.loads(predictions_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchBenchmarkError("cannot read DeepSynth JSON artifacts") from exc
    gold, _ = _deepsynth_records(
        gold_payload, label="DeepSynth gold", answer_field="Answers"
    )
    predictions, prediction_rows = _deepsynth_records(
        prediction_payload, label="DeepSynth prediction", answer_field="answer"
    )
    if set(predictions) != set(gold):
        missing = sorted(set(gold) - set(predictions))
        extra = sorted(set(predictions) - set(gold))
        raise ResearchBenchmarkError(
            "DeepSynth predictions must cover exactly the gold task set: "
            f"missing={missing[:5]} extra={extra[:5]}"
        )

    totals = Counter()
    cases: list[dict[str, Any]] = []
    cost_values: list[float] = []
    latency_values: list[float] = []
    for identifier in sorted(gold):
        gold_flat = _deepsynth_flatten(gold[identifier])
        prediction_flat = _deepsynth_flatten(predictions[identifier])
        gold_keys = set(gold_flat)
        prediction_keys = set(prediction_flat)
        common = gold_keys & prediction_keys
        exact_matches = sum(gold_flat[key] == prediction_flat[key] for key in common)
        partial_similarity = sum(
            _deepsynth_partial_similarity(gold_flat[key], prediction_flat[key])
            for key in common
        )
        precision = _ratio(exact_matches, len(prediction_flat))
        recall = _ratio(exact_matches, len(gold_flat))
        f1 = _ratio(2 * precision * recall, precision + recall)
        exact_task = gold_flat == prediction_flat
        row = prediction_rows[identifier]
        cost = _deepsynth_optional_measurement(row, "cost_usd", identifier)
        latency = _deepsynth_optional_measurement(row, "latency_s", identifier)
        if cost is not None:
            cost_values.append(cost)
        if latency is not None:
            latency_values.append(latency)
        case = {
            "case_id": f"deepsynth-{identifier}",
            "gold_keys": len(gold_flat),
            "prediction_keys": len(prediction_flat),
            "matched_keys": len(common),
            "exact_key_value_matches": exact_matches,
            "missing_keys": len(gold_keys - prediction_keys),
            "extra_keys": len(prediction_keys - gold_keys),
            "exact_task_match": exact_task,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "partial_similarity": _ratio(partial_similarity, len(gold_flat)),
            "cost_usd": cost,
            "latency_s": latency,
        }
        cases.append(case)
        totals.update(
            {
                "gold_keys": len(gold_flat),
                "prediction_keys": len(prediction_flat),
                "matched_keys": len(common),
                "exact_key_value_matches": exact_matches,
                "exact_task_matches": int(exact_task),
                "partial_similarity_sum": partial_similarity,
                "macro_precision_sum": precision,
                "macro_recall_sum": recall,
                "macro_f1_sum": f1,
            }
        )

    count = len(cases)
    micro_precision = _ratio(
        totals["exact_key_value_matches"], totals["prediction_keys"]
    )
    micro_recall = _ratio(totals["exact_key_value_matches"], totals["gold_keys"])
    return {
        "schema_version": DEEPSYNTH_SCORE_SCHEMA,
        "benchmark": "DeepSynth Bench compatible static evaluation",
        "system": system.strip(),
        "upstream_repository": "https://github.com/agentdeepsynthesis/deepsynth-bench",
        "upstream_commit": DEEPSYNTH_BENCH_COMMIT,
        "upstream_license": "Apache-2.0",
        "case_count": count,
        "case_ids": [case["case_id"] for case in cases],
        "metrics": {
            "exact_task_match_rate": _ratio(totals["exact_task_matches"], count),
            "exact_key_value_accuracy": micro_recall,
            "partial_similarity": _ratio(
                totals["partial_similarity_sum"], totals["gold_keys"]
            ),
            "micro_precision": micro_precision,
            "micro_recall": micro_recall,
            "micro_f1": _ratio(
                2 * micro_precision * micro_recall, micro_precision + micro_recall
            ),
            "macro_precision": _ratio(totals["macro_precision_sum"], count),
            "macro_recall": _ratio(totals["macro_recall_sum"], count),
            "macro_f1": _ratio(totals["macro_f1_sum"], count),
            "cost_reporting_coverage": _ratio(len(cost_values), count),
            "latency_reporting_coverage": _ratio(len(latency_values), count),
            "cost_usd_total": sum(cost_values) if len(cost_values) == count else None,
            "latency_s_mean": (
                sum(latency_values) / count if len(latency_values) == count else None
            ),
        },
        "counts": {
            key: value
            for key, value in sorted(totals.items())
            if not key.endswith("_sum")
        },
        "cases": cases,
        "artifacts": {
            "gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
            "predictions_sha256": hashlib.sha256(
                predictions_path.read_bytes()
            ).hexdigest(),
        },
        "dataset_identity_state": "user_supplied_artifact_not_officially_pinned",
        "execution_state": "deterministic_static_evaluation_complete",
        "claim_boundary": (
            "compatible static key/value evaluation with complete task-set binding; "
            "no LLM judge, retrieval, official hidden-test scoring or leaderboard submission"
        ),
    }


def _official_ids(rows: Sequence[Mapping[str, Any]], *, require_official_set: bool) -> list[int]:
    identifiers = [row.get("id") for row in rows]
    if not all(
        not isinstance(identifier, bool) and isinstance(identifier, int) and identifier >= 1
        for identifier in identifiers
    ):
        raise ResearchBenchmarkError("DeepResearch Bench result ids must be positive integers")
    typed = [int(identifier) for identifier in identifiers]
    if len(typed) != len(set(typed)):
        raise ResearchBenchmarkError("DeepResearch Bench result ids must be unique")
    if require_official_set and (len(typed) != 100 or set(typed) != set(range(1, 101))):
        raise ResearchBenchmarkError("official DeepResearch Bench results require ids 1-100")
    return typed


def _select_drb_result_rows(
    rows: Sequence[Mapping[str, Any]], case_ids: Sequence[str] | None
) -> list[Mapping[str, Any]]:
    if case_ids is None:
        return list(rows)
    if not case_ids:
        raise ResearchBenchmarkError("selected DeepResearch Bench case_ids cannot be empty")
    selected: list[int] = []
    for case_id in case_ids:
        if not isinstance(case_id, str) or not case_id.startswith("drb-") or not case_id[4:].isdigit():
            raise ResearchBenchmarkError("selected case_ids must use the drb-NNN form")
        selected.append(int(case_id[4:]))
    if len(selected) != len(set(selected)):
        raise ResearchBenchmarkError("selected DeepResearch Bench case_ids must be unique")
    by_id = {int(row["id"]): row for row in rows}
    missing = sorted(set(selected) - set(by_id))
    if missing:
        raise ResearchBenchmarkError(f"selected DeepResearch Bench result ids are missing: {missing}")
    return [by_id[identifier] for identifier in selected]


def import_deepresearch_bench_race_results(
    path: Path,
    *,
    require_official_set: bool = True,
    case_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Validate and aggregate official RACE JSONL without rerunning its model judge."""
    rows = _jsonl(path, "RACE result")
    _official_ids(rows, require_official_set=require_official_set)
    rows = _select_drb_result_rows(rows, case_ids)
    identifiers = _official_ids(rows, require_official_set=False)
    dimensions = (*_RACE_DIMENSIONS, "overall_score")
    totals = Counter({dimension: 0.0 for dimension in dimensions})
    for row in rows:
        if not isinstance(row.get("prompt"), str) or not row["prompt"].strip():
            raise ResearchBenchmarkError(f"RACE result {row.get('id')} lacks its prompt")
        for dimension in dimensions:
            value = row.get(dimension)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= float(value) <= 1
            ):
                raise ResearchBenchmarkError(
                    f"RACE result {row.get('id')} has an invalid {dimension} score"
                )
            totals[dimension] += float(value)
    means = {dimension: totals[dimension] / len(rows) for dimension in dimensions}
    return {
        "schema_version": "giga.deepresearch-bench-race-import.v1",
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "configured_judge_model_at_upstream_commit": DEEPRESEARCH_BENCH_RACE_MODEL,
        "artifact_judge_model": None,
        "artifact_judge_model_state": "not_embedded_in_result_rows",
        "case_ids": [f"drb-{identifier:03d}" for identifier in sorted(identifiers)],
        "case_count": len(rows),
        "means": means,
        "execution_state": "official_results_imported_not_rerun",
    }


def import_deepresearch_bench_fact_results(
    path: Path,
    *,
    require_official_set: bool = True,
    case_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Reproduce official FACT accounting and expose its report-coverage denominator."""
    rows = _jsonl(path, "FACT result")
    _official_ids(rows, require_official_set=require_official_set)
    rows = _select_drb_result_rows(rows, case_ids)
    identifiers = _official_ids(rows, require_official_set=False)
    reports_with_citations = 0
    known_citations = 0
    supported_citations = 0
    unknown_citations = 0
    validation_errors = 0
    for row in rows:
        citations = row.get("citations")
        deduplicated = row.get("citations_deduped")
        if not isinstance(citations, list) or not isinstance(deduplicated, Mapping):
            raise ResearchBenchmarkError(
                f"FACT result {row.get('id')} lacks citation arrays or deduplicated sources"
            )
        if not citations:
            continue
        reports_with_citations += 1
        for source in deduplicated.values():
            if not isinstance(source, Mapping):
                raise ResearchBenchmarkError("FACT deduplicated source must be an object")
            if source.get("validate_error") is not None:
                validation_errors += 1
                continue
            validations = source.get("validate_res")
            if not isinstance(validations, list):
                raise ResearchBenchmarkError("FACT source lacks validate_res array")
            for validation in validations:
                if not isinstance(validation, Mapping):
                    raise ResearchBenchmarkError("FACT validation must be an object")
                result = validation.get("result")
                if result not in {"supported", "unsupported", "unknown"}:
                    raise ResearchBenchmarkError("FACT validation has an unknown result")
                if result == "unknown":
                    unknown_citations += 1
                else:
                    known_citations += 1
                    supported_citations += result == "supported"
    return {
        "schema_version": "giga.deepresearch-bench-fact-import.v1",
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "configured_judge_model_at_upstream_commit": DEEPRESEARCH_BENCH_FACT_MODEL,
        "artifact_judge_model": None,
        "artifact_judge_model_state": "not_embedded_in_result_rows",
        "case_ids": [f"drb-{identifier:03d}" for identifier in sorted(identifiers)],
        "case_count": len(rows),
        "reports_with_citations": reports_with_citations,
        "report_coverage": _ratio(reports_with_citations, len(rows)),
        "effective_citations_per_evaluated_report": _ratio(known_citations, reports_with_citations),
        "supported_citations_per_evaluated_report": _ratio(
            supported_citations, reports_with_citations
        ),
        "citation_accuracy": _ratio(supported_citations, known_citations),
        "known_citations": known_citations,
        "supported_citations": supported_citations,
        "unknown_citations": unknown_citations,
        "source_validation_errors": validation_errors,
        "execution_state": "official_results_imported_not_rerun",
        "denominator_note": (
            "Official FACT averages exclude reports with no extracted citations; "
            "report_coverage is reported separately to prevent false comparability."
        ),
    }


def import_deepresearch_bench_competitor_cohort(
    race_path: Path,
    fact_path: Path,
    *,
    system: str,
    case_ids: Sequence[str],
) -> dict[str, Any]:
    """Predeclare one exact published competitor cohort using official artifacts."""
    if not isinstance(system, str) or not system.strip():
        raise ResearchBenchmarkError("competitor cohort system must be non-empty text")
    race = import_deepresearch_bench_race_results(race_path, case_ids=case_ids)
    fact = import_deepresearch_bench_fact_results(fact_path, case_ids=case_ids)
    if race["case_ids"] != fact["case_ids"]:
        raise ResearchBenchmarkError("RACE and FACT competitor cohort case sets differ")
    return {
        "schema_version": "giga.deepresearch-bench-competitor-cohort.v1",
        "system": system.strip(),
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "case_ids": race["case_ids"],
        "case_count": len(race["case_ids"]),
        "race": race,
        "fact": fact,
        "artifacts": {
            "race_sha256": hashlib.sha256(race_path.read_bytes()).hexdigest(),
            "fact_sha256": hashlib.sha256(fact_path.read_bytes()).hexdigest(),
        },
        "execution_state": "published_competitor_subset_imported_not_rerun",
        "claim_boundary": "published upstream artifacts for this exact predeclared case set",
    }


def build_deepresearch_bench_fact_benchmark_run(
    path: Path,
    *,
    case_id: str,
    measurement: Mapping[str, Any],
    upstream_commit: str = DEEPRESEARCH_BENCH_COMMIT,
) -> dict[str, Any]:
    """Adapt one official FACT artifact without inventing acquisition provenance."""
    if measurement.get("schema_version") != BENCHMARK_MEASUREMENT_SCHEMA:
        raise ResearchBenchmarkError(
            f"measurement schema_version must be {BENCHMARK_MEASUREMENT_SCHEMA}"
        )
    if measurement.get("case_id") != case_id:
        raise ResearchBenchmarkError("measurement case_id must match the requested FACT case")
    if "latency_ms" not in measurement:
        raise ResearchBenchmarkError(
            "FACT artifact measurement must state latency_ms explicitly, using null when unknown"
        )
    if not _git_commit(upstream_commit):
        raise ResearchBenchmarkError("upstream_commit must be a full lowercase Git commit")
    if not case_id.startswith("drb-") or not case_id[4:].isdigit():
        raise ResearchBenchmarkError("FACT case_id must use the drb-NNN form")
    upstream_id = int(case_id[4:])
    rows = _jsonl(path, "FACT result")
    matches = [row for row in rows if row.get("id") == upstream_id]
    if len(matches) != 1:
        raise ResearchBenchmarkError("FACT artifact must contain exactly one requested case")
    row = matches[0]
    prompt = row.get("prompt")
    citations = row.get("citations")
    deduplicated = row.get("citations_deduped")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ResearchBenchmarkError("FACT case lacks its prompt")
    if not isinstance(citations, list) or not isinstance(deduplicated, Mapping):
        raise ResearchBenchmarkError("FACT case lacks citation arrays or deduplicated sources")

    artifact_bytes = path.read_bytes()
    artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    record_bytes = json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    record_sha256 = hashlib.sha256(record_bytes).hexdigest()
    sources: list[dict[str, Any]] = []
    source_ids: dict[str, str] = {}
    validations_by_fact: dict[tuple[str, str], str] = {}
    for url, source in deduplicated.items():
        if not isinstance(url, str) or not url.strip() or not isinstance(source, Mapping):
            raise ResearchBenchmarkError("FACT deduplicated source must bind a URL to an object")
        facts = source.get("facts")
        validations = source.get("validate_res")
        if not isinstance(facts, list) or not all(isinstance(fact, str) for fact in facts):
            raise ResearchBenchmarkError("FACT source facts must be an array of text")
        if source.get("validate_error") is not None:
            validations = []
        if not isinstance(validations, list):
            raise ResearchBenchmarkError("FACT source lacks validate_res array")
        for validation in validations:
            if not isinstance(validation, Mapping):
                raise ResearchBenchmarkError("FACT validation must be an object")
            index = validation.get("idx")
            result = validation.get("result")
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(facts)
                or result not in {"supported", "unsupported", "unknown"}
            ):
                raise ResearchBenchmarkError("FACT validation has an invalid fact index or result")
            validations_by_fact[(url, facts[index])] = str(result)
        source_id = hashlib.sha256(url.encode("utf-8")).hexdigest()
        source_ids[url] = source_id
        content = source.get("url_content")
        content_sha256 = (
            hashlib.sha256(content.encode("utf-8")).hexdigest()
            if isinstance(content, str)
            else None
        )
        source_record_sha256 = hashlib.sha256(
            json.dumps(
                {"url": url, "source": source},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        sources.append(
            {
                "source_id": source_id,
                "url": url,
                "receipt_sha256": None,
                "content_sha256": content_sha256,
                "fetched_at": None,
                "provenance_state": "upstream_artifact_without_original_fetch_receipt",
                "upstream_source_record_sha256": source_record_sha256,
            }
        )

    claims: list[dict[str, Any]] = []
    for citation in citations:
        if not isinstance(citation, Mapping):
            raise ResearchBenchmarkError("FACT citation must be an object")
        fact = citation.get("fact")
        url = citation.get("url")
        if (
            not isinstance(fact, str)
            or not fact.strip()
            or not isinstance(url, str)
            or url not in source_ids
        ):
            raise ResearchBenchmarkError("FACT citation must bind text to a known source URL")
        claims.append(
            {
                "text": fact,
                "source_ids": [source_ids[str(url)]],
                "evidence": [{"source_id": source_ids[str(url)], "quote": fact}],
                "review_status": "pending",
                "position": "supports",
                "official_fact_validation": validations_by_fact.get(
                    (str(url), fact), "not_reported"
                ),
                "upstream_configured_fact_judge_model": DEEPRESEARCH_BENCH_FACT_MODEL,
                "artifact_judge_model_state": "not_embedded_in_result_rows",
            }
        )
    run = {
        "schema_version": BENCHMARK_RUN_SCHEMA,
        "system": measurement.get("system"),
        "case_id": case_id,
        "language": measurement.get("language"),
        "question": prompt.strip(),
        "started_at": measurement.get("started_at"),
        "finished_at": measurement.get("finished_at"),
        "latency_ms": measurement.get("latency_ms"),
        "latency_scope": measurement.get("latency_scope"),
        "cost_usd": measurement.get("cost_usd"),
        "cost_scope": measurement.get("cost_scope"),
        "minimum_sources": measurement.get("minimum_sources", 3),
        "expected_terms": measurement.get("expected_terms", []),
        "require_contradiction": measurement.get("require_contradiction", False),
        "sources": sources,
        "claims": claims,
        "upstream": {
            "repository": "https://github.com/Ayanami0730/deep_research_bench",
            "commit": upstream_commit,
            "license": "Apache-2.0",
            "artifact_sha256": artifact_sha256,
            "record_sha256": record_sha256,
            "record": row,
            "execution_state": "official_result_artifact_imported_not_rerun",
        },
    }
    _validated_run(run)
    return run


def prepare_deepresearch_bench_submission(
    case_manifest: Mapping[str, Any], article_manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """Build the official raw-article contract only when all imported cases are present."""
    cases = case_manifest.get("cases")
    articles = article_manifest.get("articles")
    system = article_manifest.get("system")
    if case_manifest.get(
        "schema_version"
    ) != "giga.research-benchmark-case-manifest.v1" or not isinstance(cases, list):
        raise ResearchBenchmarkError("submission requires an imported DRB case manifest")
    if not isinstance(system, str) or not system.strip() or not isinstance(articles, list):
        raise ResearchBenchmarkError("article manifest requires system and articles")
    by_case: dict[str, str] = {}
    for row in articles:
        if not isinstance(row, Mapping):
            raise ResearchBenchmarkError("every submission article must be an object")
        case_id = row.get("case_id")
        article = row.get("article")
        if not isinstance(case_id, str) or not isinstance(article, str) or not article.strip():
            raise ResearchBenchmarkError("submission articles require case_id and article text")
        if case_id in by_case:
            raise ResearchBenchmarkError("submission article case_ids must be unique")
        by_case[case_id] = article
    expected = {str(row["case_id"]) for row in cases}
    if set(by_case) != expected:
        missing = sorted(expected - set(by_case))
        extra = sorted(set(by_case) - expected)
        raise ResearchBenchmarkError(
            f"submission must cover the exact imported case set; missing={missing}, extra={extra}"
        )
    records = [
        {
            "id": int(row["upstream_id"]),
            "prompt": row["question"],
            "article": by_case[str(row["case_id"])],
        }
        for row in cases
    ]
    return {
        "schema_version": "giga.deepresearch-bench-submission.v1",
        "system": system.strip(),
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "case_count": len(records),
        "records": records,
        "execution_state": "raw_articles_ready_for_official_evaluator",
    }


def assemble_deepresearch_bench_cohort(
    case_manifest: Mapping[str, Any],
    *,
    system: str,
    record_sets: Sequence[tuple[str, Sequence[Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Combine independently produced records without overstating official readiness."""
    cases = case_manifest.get("cases")
    if (
        case_manifest.get("schema_version") != "giga.research-benchmark-case-manifest.v1"
        or case_manifest.get("upstream_commit") != DEEPRESEARCH_BENCH_COMMIT
        or not isinstance(cases, list)
    ):
        raise ResearchBenchmarkError("cohort assembly requires the pinned DRB case manifest")
    if not isinstance(system, str) or not system.strip():
        raise ResearchBenchmarkError("cohort system must be non-empty text")

    official: dict[int, Mapping[str, Any]] = {}
    for case in cases:
        if not isinstance(case, Mapping):
            raise ResearchBenchmarkError("every DRB manifest case must be an object")
        identifier = case.get("upstream_id")
        if isinstance(identifier, bool) or not isinstance(identifier, int):
            raise ResearchBenchmarkError("every DRB manifest case requires an integer upstream_id")
        if identifier in official:
            raise ResearchBenchmarkError("DRB manifest upstream ids must be unique")
        if (
            case.get("case_id") != f"drb-{identifier:03d}"
            or case.get("language") not in {"en", "zh"}
            or not isinstance(case.get("topic"), str)
            or not str(case["topic"]).strip()
            or not isinstance(case.get("question"), str)
            or not str(case["question"]).strip()
        ):
            raise ResearchBenchmarkError(f"DRB manifest case {identifier} is incomplete")
        official[identifier] = case
    official_languages = Counter(str(case["language"]) for case in official.values())
    if (
        case_manifest.get("case_count") != 100
        or set(official) != set(range(1, 101))
        or official_languages != Counter({"en": 50, "zh": 50})
    ):
        raise ResearchBenchmarkError(
            "cohort assembly requires official DRB ids 1-100 with 50 en and 50 zh cases"
        )

    records: dict[int, dict[str, Any]] = {}
    producers: dict[int, str] = {}
    for producer, rows in record_sets:
        if not isinstance(producer, str) or not producer.strip():
            raise ResearchBenchmarkError("every cohort record set requires a producer")
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
            raise ResearchBenchmarkError("every cohort record set must contain records")
        for row in rows:
            if not isinstance(row, Mapping):
                raise ResearchBenchmarkError("every cohort record must be an object")
            identifier = row.get("id")
            if isinstance(identifier, bool) or not isinstance(identifier, int):
                raise ResearchBenchmarkError("every cohort record requires an integer id")
            case = official.get(identifier)
            if case is None:
                raise ResearchBenchmarkError(f"cohort record id {identifier} is not official")
            if identifier in records:
                raise ResearchBenchmarkError(f"cohort record id {identifier} is duplicated")
            if row.get("prompt") != case["question"]:
                raise ResearchBenchmarkError(
                    f"cohort record {identifier} prompt differs from the official prompt"
                )
            article = row.get("article")
            if not isinstance(article, str) or not article.strip():
                raise ResearchBenchmarkError(f"cohort record {identifier} lacks article text")
            records[identifier] = {
                "id": identifier,
                "prompt": case["question"],
                "article": article,
            }
            producers[identifier] = producer.strip()

    ordered_ids = sorted(records)
    completed_languages = Counter(str(official[item]["language"]) for item in ordered_ids)
    total_languages = official_languages
    completed_topics = Counter(str(official[item]["topic"]) for item in ordered_ids)
    total_topics = Counter(str(case["topic"]) for case in official.values())

    def coverage(completed: Counter[str], totals: Counter[str]) -> dict[str, Any]:
        return {
            key: {
                "completed": completed[key],
                "total": totals[key],
                "ratio": _ratio(completed[key], totals[key]),
            }
            for key in sorted(totals)
        }

    ordered_records = [records[item] for item in ordered_ids]
    provenance = [
        {"id": item, "case_id": f"drb-{item:03d}", "producer": producers[item]}
        for item in ordered_ids
    ]
    cohort_identity = {
        "system": system.strip(),
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "records": ordered_records,
        "record_provenance": provenance,
    }
    return {
        "schema_version": DEEPRESEARCH_BENCH_COHORT_SCHEMA,
        **cohort_identity,
        "cohort_sha256": hashlib.sha256(
            json.dumps(cohort_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "case_count": len(ordered_records),
        "official_case_count": len(official),
        "coverage": _ratio(len(ordered_records), len(official)),
        "language_coverage": coverage(completed_languages, total_languages),
        "topic_coverage": coverage(completed_topics, total_topics),
        "generator_systems": sorted(set(producers.values())),
        "missing_case_ids": [
            f"drb-{identifier:03d}" for identifier in sorted(set(official) - set(records))
        ],
        "execution_state": (
            "complete_cohort_ready_for_official_evaluator"
            if len(ordered_records) == len(official)
            else "partial_cohort_not_officially_runnable"
        ),
    }


def plan_deepresearch_bench_campaign(
    case_manifest: Mapping[str, Any],
    *,
    system: str,
    record_sets: Sequence[tuple[str, Sequence[Mapping[str, Any]]]],
    limit: int,
    created_at: str,
) -> dict[str, Any]:
    """Select a deterministic, coverage-balancing batch of missing DRB cases."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ResearchBenchmarkError("campaign limit must be a positive integer")
    timestamp = _timestamp(created_at, "created_at").astimezone(UTC).isoformat()
    cohort = assemble_deepresearch_bench_cohort(
        case_manifest,
        system=system,
        record_sets=record_sets,
    )
    cases = case_manifest["cases"]
    by_id = {int(case["upstream_id"]): case for case in cases}
    completed_ids = {int(row["id"]) for row in cohort["records"]}
    remaining = [
        case for identifier, case in sorted(by_id.items()) if identifier not in completed_ids
    ]

    total_languages = Counter(str(case["language"]) for case in cases)
    total_topics = Counter(str(case["topic"]) for case in cases)
    completed_languages = Counter(str(by_id[item]["language"]) for item in completed_ids)
    completed_topics = Counter(str(by_id[item]["topic"]) for item in completed_ids)
    selected: list[Mapping[str, Any]] = []
    candidates = list(remaining)
    while candidates and len(selected) < limit:
        case = min(
            candidates,
            key=lambda item: (
                Fraction(completed_topics[str(item["topic"])], total_topics[str(item["topic"])]),
                Fraction(
                    completed_languages[str(item["language"])],
                    total_languages[str(item["language"])],
                ),
                int(item["upstream_id"]),
            ),
        )
        candidates.remove(case)
        selected.append(case)
        completed_topics[str(case["topic"])] += 1
        completed_languages[str(case["language"])] += 1

    campaign_identity = {
        "system": system.strip(),
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "baseline_cohort_sha256": cohort["cohort_sha256"],
        "selected_case_ids": [case["case_id"] for case in selected],
        "created_at": timestamp,
    }
    campaign_id = (
        "drb-campaign-"
        + hashlib.sha256(
            json.dumps(campaign_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
    )
    jobs = []
    for rank, case in enumerate(selected, start=1):
        case_id = str(case["case_id"])
        question = str(case["question"])
        language = str(case["language"])
        topic = str(case["topic"])
        if language == "zh":
            evidence_query = f"{question[:420]} 权威来源 数据 方法"
            challenge_query = f"{question[:420]} 局限 争议 反例 最新证据"
            evidence_question = "哪些权威一手来源、数据和方法能够支持对该问题的回答？"
            challenge_question = "现有证据有哪些局限、争议、反例或时效性风险？"
        else:
            evidence_query = f"{question[:420]} authoritative primary sources data methods"
            challenge_query = f"{question[:420]} limitations conflicting evidence counterexamples recent"
            evidence_question = (
                "Which authoritative primary sources, data and methods support the answer?"
            )
            challenge_question = (
                "Which limitations, conflicting evidence, counterexamples or recency risks matter?"
            )
        jobs.append(
            {
                "rank": rank,
                "case_id": case_id,
                "upstream_id": int(case["upstream_id"]),
                "language": language,
                "topic": topic,
                "selection_reason": (
                    "lowest completed topic ratio, then language ratio, then upstream id"
                ),
                "execution_state": "draft_plan_requires_campaign_admission_or_exact_approval",
                "plan": {
                    "schema_version": "giga.research-project.v1",
                    "project_id": f"{case_id}-{campaign_id}",
                    "question": question,
                    "created_at": timestamp,
                    "perspectives": [
                        {
                            "id": "answer-coverage",
                            "label": "Answer coverage",
                            "rationale": "Cover every material part of the exact benchmark prompt.",
                        },
                        {
                            "id": "primary-evidence",
                            "label": "Primary evidence",
                            "rationale": "Prefer authoritative data, methods and first-party sources.",
                        },
                        {
                            "id": "limitations",
                            "label": "Limitations and conflicts",
                            "rationale": "Search explicitly for uncertainty, disagreement and recency risk.",
                        },
                    ],
                    "subquestions": [
                        {
                            "id": "Q1",
                            "perspective_id": "answer-coverage",
                            "priority": 1,
                            "question": question,
                            "search_terms": [question[:500]],
                            "source_types": ["public_web", "scientific_api"],
                        },
                        {
                            "id": "Q2",
                            "perspective_id": "primary-evidence",
                            "priority": 2,
                            "question": evidence_question,
                            "search_terms": [evidence_query],
                            "source_types": ["public_web", "scientific_api"],
                        },
                        {
                            "id": "Q3",
                            "perspective_id": "limitations",
                            "priority": 3,
                            "question": challenge_question,
                            "search_terms": [challenge_query],
                            "source_types": ["public_web", "scientific_api"],
                        },
                    ],
                    "stopping_conditions": {
                        "maximum_depth": 2,
                        "maximum_sources": 12,
                        "minimum_source_diversity": 4,
                        "require_contradiction_search": True,
                    },
                },
            }
        )
    return {
        "schema_version": DEEPRESEARCH_BENCH_CAMPAIGN_SCHEMA,
        "campaign_id": campaign_id,
        **campaign_identity,
        "selection_algorithm": "lowest_topic_coverage_then_language_coverage_then_upstream_id",
        "baseline_case_count": cohort["case_count"],
        "remaining_case_count": len(remaining),
        "selected_case_count": len(jobs),
        "jobs": jobs,
        "operator_gate": (
            "Generated plans remain proposals. Admit the exact campaign under a bounded resource "
            "envelope, or approve an individual exact plan, before discovery or acquisition."
        ),
        "execution_state": (
            "benchmark_cohort_complete_no_jobs"
            if not remaining
            else "campaign_planned_not_admitted_or_run"
        ),
    }


def admit_deepresearch_bench_campaign(
    campaign: Mapping[str, Any],
    *,
    campaign_plan_sha256: str,
    authorized_by: str,
    authority_reference: str,
    authorized_at: str,
    maximum_network_requests: int,
    maximum_runtime_seconds: int,
) -> dict[str, Any]:
    """Bind one exact DRB campaign to a zero-spend, unauthenticated run envelope."""
    if campaign.get("schema_version") != DEEPRESEARCH_BENCH_CAMPAIGN_SCHEMA:
        raise ResearchBenchmarkError("campaign has an unsupported schema")
    if campaign.get("upstream_commit") != DEEPRESEARCH_BENCH_COMMIT:
        raise ResearchBenchmarkError("campaign is not bound to the pinned DRB commit")
    if not _digest(campaign_plan_sha256):
        raise ResearchBenchmarkError("campaign_plan_sha256 must be a lowercase SHA-256")
    if not isinstance(authorized_by, str) or not authorized_by.strip() or len(authorized_by) > 300:
        raise ResearchBenchmarkError("authorized_by must be non-empty text")
    if (
        not isinstance(authority_reference, str)
        or not authority_reference.strip()
        or len(authority_reference) > 500
    ):
        raise ResearchBenchmarkError("authority_reference must be non-empty text")
    if (
        isinstance(maximum_network_requests, bool)
        or not isinstance(maximum_network_requests, int)
        or maximum_network_requests < 1
    ):
        raise ResearchBenchmarkError("maximum_network_requests must be a positive integer")
    if (
        isinstance(maximum_runtime_seconds, bool)
        or not isinstance(maximum_runtime_seconds, int)
        or maximum_runtime_seconds < 1
    ):
        raise ResearchBenchmarkError("maximum_runtime_seconds must be a positive integer")

    selected_case_ids = campaign.get("selected_case_ids")
    jobs = campaign.get("jobs")
    if not isinstance(selected_case_ids, list) or not isinstance(jobs, list) or not jobs:
        raise ResearchBenchmarkError("campaign admission requires at least one selected job")
    if campaign.get("selected_case_count") != len(jobs) or len(selected_case_ids) != len(jobs):
        raise ResearchBenchmarkError("campaign selected-case accounting is inconsistent")
    if maximum_network_requests < len(jobs):
        raise ResearchBenchmarkError("network request envelope cannot be smaller than job count")

    clean_jobs: list[dict[str, Any]] = []
    seen_cases: set[str] = set()
    seen_projects: set[str] = set()
    for index, job in enumerate(jobs):
        if not isinstance(job, Mapping):
            raise ResearchBenchmarkError("every campaign job must be an object")
        case_id = job.get("case_id")
        if (
            not isinstance(case_id, str)
            or case_id in seen_cases
            or selected_case_ids[index] != case_id
        ):
            raise ResearchBenchmarkError("campaign case ordering or uniqueness is invalid")
        seen_cases.add(case_id)
        raw_plan = job.get("plan")
        if not isinstance(raw_plan, Mapping):
            raise ResearchBenchmarkError(f"campaign job {case_id} lacks a project plan")
        try:
            plan = validate_project_plan(raw_plan)
        except (TypeError, ValueError) as exc:
            raise ResearchBenchmarkError(f"campaign job {case_id} has an invalid plan") from exc
        expected_project_id = f"{case_id}-{campaign.get('campaign_id', '')}"
        if plan["project_id"] != expected_project_id or plan["project_id"] in seen_projects:
            raise ResearchBenchmarkError("campaign project identity is invalid or duplicated")
        if plan["question"] != job.get("plan", {}).get("question"):
            raise ResearchBenchmarkError("campaign plan question binding is invalid")
        if any(
            source_type not in {"public_web", "scientific_api"}
            for subquestion in plan["subquestions"]
            for source_type in subquestion["source_types"]
        ):
            raise ResearchBenchmarkError("campaign admission permits only public research sources")
        seen_projects.add(plan["project_id"])
        clean_jobs.append(
            {
                "rank": index + 1,
                "case_id": case_id,
                "project_id": plan["project_id"],
                "plan_sha256": project_plan_sha256(plan),
                "plan": plan,
            }
        )

    campaign_identity = {
        "system": str(campaign.get("system", "")).strip(),
        "upstream_commit": campaign["upstream_commit"],
        "baseline_cohort_sha256": campaign.get("baseline_cohort_sha256"),
        "selected_case_ids": selected_case_ids,
        "created_at": campaign.get("created_at"),
    }
    if not campaign_identity["system"] or not _digest(campaign_identity["baseline_cohort_sha256"]):
        raise ResearchBenchmarkError("campaign identity is incomplete")
    expected_campaign_id = (
        "drb-campaign-"
        + hashlib.sha256(
            json.dumps(campaign_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
    )
    if campaign.get("campaign_id") != expected_campaign_id:
        raise ResearchBenchmarkError("campaign_id does not match the pinned campaign identity")

    timestamp = _timestamp(authorized_at, "authorized_at").astimezone(UTC).isoformat()
    resource_envelope = {
        "maximum_external_cost_usd": 0,
        "maximum_network_requests": maximum_network_requests,
        "maximum_runtime_seconds": maximum_runtime_seconds,
        "public_unauthenticated_research": True,
        "authenticated_account_actions": False,
        "publication_or_benchmark_submission": False,
    }
    admission_identity = {
        "campaign_id": expected_campaign_id,
        "campaign_plan_sha256": campaign_plan_sha256,
        "authorized_by": authorized_by.strip(),
        "authority_reference": authority_reference.strip(),
        "authorized_at": timestamp,
        "resource_envelope": resource_envelope,
    }
    admission_id = "drb-admission-" + _canonical_artifact_sha256(admission_identity)[:16]
    admission = {
        "schema_version": DEEPRESEARCH_BENCH_ADMISSION_SCHEMA,
        "admission_id": admission_id,
        **admission_identity,
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "selected_case_ids": list(selected_case_ids),
        "jobs": clean_jobs,
        "execution_state": "admitted_for_zero_spend_public_research",
        "operator_gate": (
            "No per-case approval is required inside this exact envelope. Spending, authenticated "
            "actions, publication, submission, or scope expansion require a new authorization."
        ),
    }
    admission["admission_sha256"] = _canonical_artifact_sha256(admission)
    return admission


def prepare_deepresearch_bench_run_record(
    case_manifest: Mapping[str, Any],
    *,
    case_id: str,
    plan: Mapping[str, Any],
    run: Mapping[str, Any],
    system: str,
) -> dict[str, Any]:
    """Render one verified GIGA run into the exact official raw-article record shape."""
    cases = case_manifest.get("cases")
    if (
        case_manifest.get("schema_version") != "giga.research-benchmark-case-manifest.v1"
        or case_manifest.get("upstream_commit") != DEEPRESEARCH_BENCH_COMMIT
        or not isinstance(cases, list)
    ):
        raise ResearchBenchmarkError("run export requires the pinned DRB case manifest")
    matches = [row for row in cases if isinstance(row, Mapping) and row.get("case_id") == case_id]
    if len(matches) != 1:
        raise ResearchBenchmarkError("run export case_id must identify exactly one DRB case")
    case = matches[0]
    if plan.get("question") != case.get("question"):
        raise ResearchBenchmarkError("research plan question differs from the official DRB prompt")
    if run.get("schema_version") != "giga.research-run.v1":
        raise ResearchBenchmarkError("run export requires a GIGA research-run bundle")
    if run.get("project_id") != plan.get("project_id"):
        raise ResearchBenchmarkError("research plan and run project ids differ")
    if not isinstance(system, str) or not system.strip():
        raise ResearchBenchmarkError("run export system must be non-empty text")
    article = render_extractive_article(plan, run)
    if not article.strip() or "[Source " not in article:
        raise ResearchBenchmarkError("run export produced no citation-linked evidence")
    article_sha = hashlib.sha256(article.encode("utf-8")).hexdigest()
    return {
        "schema_version": "giga.deepresearch-bench-run-record.v1",
        "system": system.strip(),
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "case_id": case_id,
        "run_id": run.get("run_id"),
        "record": {
            "id": int(case["upstream_id"]),
            "prompt": case["question"],
            "article": article,
        },
        "article_sha256": article_sha,
        "execution_state": "single_raw_article_ready_not_officially_judged",
    }


def prepare_deepresearch_bench_synthesis_record(
    case_manifest: Mapping[str, Any],
    *,
    case_id: str,
    packet: Mapping[str, Any],
    proposal: Mapping[str, Any],
    system: str,
) -> dict[str, Any]:
    """Render one validated synthesis proposal into the official raw-article shape."""
    cases = case_manifest.get("cases")
    if (
        case_manifest.get("schema_version") != "giga.research-benchmark-case-manifest.v1"
        or case_manifest.get("upstream_commit") != DEEPRESEARCH_BENCH_COMMIT
        or not isinstance(cases, list)
    ):
        raise ResearchBenchmarkError("synthesis export requires the pinned DRB case manifest")
    matches = [row for row in cases if isinstance(row, Mapping) and row.get("case_id") == case_id]
    if len(matches) != 1:
        raise ResearchBenchmarkError("synthesis export case_id must identify exactly one DRB case")
    case = matches[0]
    if packet.get("question") != case.get("question"):
        raise ResearchBenchmarkError("synthesis packet question differs from the official prompt")
    if not isinstance(system, str) or not system.strip():
        raise ResearchBenchmarkError("synthesis export system must be non-empty text")
    article = render_synthesis_article(packet, proposal)
    return {
        "schema_version": "giga.deepresearch-bench-synthesis-record.v1",
        "system": system.strip(),
        "upstream_commit": DEEPRESEARCH_BENCH_COMMIT,
        "case_id": case_id,
        "run_id": packet.get("run_id"),
        "packet_sha256": packet.get("packet_sha256"),
        "record": {
            "id": int(case["upstream_id"]),
            "prompt": case["question"],
            "article": article,
        },
        "article_sha256": hashlib.sha256(article.encode("utf-8")).hexdigest(),
        "execution_state": "single_grounded_synthesis_ready_not_officially_judged",
    }
