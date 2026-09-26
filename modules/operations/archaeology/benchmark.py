"""Versioned, receipt-bound retrieval benchmarks for the Archaeology mapper."""

from __future__ import annotations

from fnmatch import fnmatchcase
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from typing import Any

from .dossier import DossierError, build_context_projection, build_dossier
from .evidence import canonical_bytes, seal_document
from .mapper import current_mapper_run
from .navigation_inventory import current_navigation_run


CORPUS_SCHEMA = "giga.archaeologist.mapper-benchmark-corpus.v1"
RESULT_SCHEMA = "giga.archaeologist.mapper-benchmark-result.v1"
CONTEXT_CORPUS_SCHEMA = "giga.archaeologist.context-benchmark-corpus.v1"
CONTEXT_RESULT_SCHEMA = "giga.archaeologist.context-benchmark-result.v1"
_DOSSIERS = {
    "architecture",
    "implementation",
    "debugging",
    "consolidation",
    "archaeology",
    "deletion_review",
    "security_review",
    "claim_review",
}


class BenchmarkError(ValueError):
    """A benchmark cannot be evaluated without overstating its evidence."""


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BenchmarkError(f"duplicate benchmark key: {key}")
        result[key] = value
    return result


def _load_corpus(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        corpus = json.loads(
            raw.decode("utf-8", "strict"), object_pairs_hook=_strict_pairs
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkError("benchmark corpus is not strict UTF-8 JSON") from exc
    if not isinstance(corpus, dict) or set(corpus) != {
        "schema",
        "corpus_id",
        "reviewed_at",
        "review_scope",
        "cases",
    }:
        raise BenchmarkError("benchmark corpus root is not closed")
    if corpus["schema"] != CORPUS_SCHEMA:
        raise BenchmarkError("unsupported benchmark corpus schema")
    if corpus["review_scope"] not in {"FULL_PATH_SET", "PATH_RULE_ANCHORS"}:
        raise BenchmarkError("unsupported benchmark review scope")
    if not isinstance(corpus["cases"], list) or not corpus["cases"]:
        raise BenchmarkError("benchmark corpus has no cases")
    identifiers: set[str] = set()
    for case in corpus["cases"]:
        if not isinstance(case, dict) or set(case) != {
            "id",
            "question",
            "dossier",
            "terms",
            "expected_path_globs",
            "relevant_path_globs",
            "min_precision_basis_points",
            "min_recall_basis_points",
            "limit_per_term",
            "overall_limit",
            "include_semantic",
        }:
            raise BenchmarkError("benchmark case is not closed")
        identifier = case["id"]
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in identifiers
        ):
            raise BenchmarkError("benchmark case id is invalid or duplicated")
        identifiers.add(identifier)
        if case["dossier"] not in _DOSSIERS:
            raise BenchmarkError("benchmark case has an unsupported dossier")
        for field in ("question",):
            if not isinstance(case[field], str) or not case[field].strip():
                raise BenchmarkError(f"benchmark case {field} is invalid")
        for field in ("terms", "expected_path_globs", "relevant_path_globs"):
            values = case[field]
            if (
                not isinstance(values, list)
                or not values
                or any(not isinstance(value, str) or not value for value in values)
            ):
                raise BenchmarkError(f"benchmark case {field} is invalid")
        for field in ("min_precision_basis_points", "min_recall_basis_points"):
            value = case[field]
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 10000
            ):
                raise BenchmarkError(f"benchmark case {field} is invalid")
        for field, ceiling in (("limit_per_term", 500), ("overall_limit", 2000)):
            value = case[field]
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= ceiling
            ):
                raise BenchmarkError(f"benchmark case {field} is invalid")
        if not isinstance(case["include_semantic"], bool):
            raise BenchmarkError("benchmark include_semantic is invalid")
    return corpus, hashlib.sha256(raw).hexdigest()


def _load_context_corpus(path: Path) -> tuple[dict[str, Any], str]:
    """Load a reviewed fixed-budget ranking corpus with a closed schema."""

    raw = path.read_bytes()
    try:
        corpus = json.loads(
            raw.decode("utf-8", "strict"), object_pairs_hook=_strict_pairs
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkError(
            "context benchmark corpus is not strict UTF-8 JSON"
        ) from exc
    if not isinstance(corpus, dict) or set(corpus) != {
        "schema",
        "corpus_id",
        "reviewed_at",
        "donor",
        "cases",
    }:
        raise BenchmarkError("context benchmark corpus root is not closed")
    if corpus["schema"] != CONTEXT_CORPUS_SCHEMA:
        raise BenchmarkError("unsupported context benchmark corpus schema")
    donor = corpus["donor"]
    if not isinstance(donor, dict) or set(donor) != {
        "name",
        "url",
        "commit",
        "reviewed_mechanisms",
    }:
        raise BenchmarkError("context benchmark donor is not closed")
    if any(
        not isinstance(donor[field], str) or not donor[field]
        for field in ("name", "url", "commit")
    ):
        raise BenchmarkError("context benchmark donor identity is invalid")
    if (
        not isinstance(donor["reviewed_mechanisms"], list)
        or not donor["reviewed_mechanisms"]
        or any(
            not isinstance(value, str) or not value
            for value in donor["reviewed_mechanisms"]
        )
    ):
        raise BenchmarkError("context benchmark donor mechanisms are invalid")
    if not isinstance(corpus["cases"], list) or not corpus["cases"]:
        raise BenchmarkError("context benchmark corpus has no cases")
    identifiers: set[str] = set()
    for case in corpus["cases"]:
        if not isinstance(case, dict) or set(case) != {
            "id",
            "question",
            "dossier",
            "terms",
            "token_budget",
            "include_semantic",
            "expected_anchors",
            "relevant_path_globs",
            "min_anchor_recall_basis_points",
            "min_precision_basis_points",
            "min_relationship_anchor_count",
            "min_budget_utilization_basis_points",
        }:
            raise BenchmarkError("context benchmark case is not closed")
        identifier = case["id"]
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in identifiers
        ):
            raise BenchmarkError("context benchmark case id is invalid or duplicated")
        identifiers.add(identifier)
        if case["dossier"] not in _DOSSIERS:
            raise BenchmarkError("context benchmark case has an unsupported dossier")
        if not isinstance(case["question"], str) or not case["question"].strip():
            raise BenchmarkError("context benchmark question is invalid")
        if (
            not isinstance(case["terms"], list)
            or not case["terms"]
            or any(not isinstance(value, str) or not value for value in case["terms"])
        ):
            raise BenchmarkError("context benchmark terms are invalid")
        if (
            isinstance(case["token_budget"], bool)
            or not isinstance(case["token_budget"], int)
            or not 32 <= case["token_budget"] <= 65_536
        ):
            raise BenchmarkError("context benchmark token budget is invalid")
        if not isinstance(case["include_semantic"], bool):
            raise BenchmarkError("context benchmark include_semantic is invalid")
        if (
            not isinstance(case["relevant_path_globs"], list)
            or not case["relevant_path_globs"]
            or any(
                not isinstance(value, str) or not value
                for value in case["relevant_path_globs"]
            )
        ):
            raise BenchmarkError("context benchmark relevant paths are invalid")
        anchors = case["expected_anchors"]
        if not isinstance(anchors, list) or not anchors:
            raise BenchmarkError("context benchmark has no expected anchors")
        anchor_ids: set[str] = set()
        for anchor in anchors:
            if not isinstance(anchor, dict) or set(anchor) != {
                "id",
                "path",
                "kind",
                "qualified_name",
                "max_rank",
                "relationship_expanded",
            }:
                raise BenchmarkError("context benchmark anchor is not closed")
            anchor_id = anchor["id"]
            if (
                not isinstance(anchor_id, str)
                or not anchor_id
                or anchor_id in anchor_ids
            ):
                raise BenchmarkError(
                    "context benchmark anchor id is invalid or duplicated"
                )
            anchor_ids.add(anchor_id)
            for field in ("path", "kind", "qualified_name"):
                if not isinstance(anchor[field], str) or not anchor[field]:
                    raise BenchmarkError(f"context benchmark anchor {field} is invalid")
            if (
                anchor["path"].startswith("/")
                or ".." in Path(anchor["path"]).parts
                or "\\" in anchor["path"]
            ):
                raise BenchmarkError("context benchmark anchor path is unsafe")
            if (
                isinstance(anchor["max_rank"], bool)
                or not isinstance(anchor["max_rank"], int)
                or not 1 <= anchor["max_rank"] <= 1000
            ):
                raise BenchmarkError("context benchmark anchor rank is invalid")
            if not isinstance(anchor["relationship_expanded"], bool):
                raise BenchmarkError(
                    "context benchmark relationship-expanded flag is invalid"
                )
        for field in (
            "min_anchor_recall_basis_points",
            "min_precision_basis_points",
            "min_budget_utilization_basis_points",
        ):
            value = case[field]
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 10_000
            ):
                raise BenchmarkError(f"context benchmark {field} is invalid")
        relationship_minimum = case["min_relationship_anchor_count"]
        if (
            isinstance(relationship_minimum, bool)
            or not isinstance(relationship_minimum, int)
            or not 0 <= relationship_minimum <= len(anchors)
        ):
            raise BenchmarkError(
                "context benchmark relationship anchor minimum is invalid"
            )
    return corpus, hashlib.sha256(raw).hexdigest()


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatchcase(path, pattern) for pattern in patterns)


def _basis_points(numerator: int, denominator: int) -> int:
    return (
        10000
        if denominator == 0 and numerator == 0
        else (0 if denominator == 0 else round(10000 * numerator / denominator))
    )


def _whole_scope_bytes(mapper_store: Path) -> tuple[int, int, int, int]:
    mapper = current_mapper_run(mapper_store)
    inventory = current_navigation_run(Path(mapper.manifest["inventory"]["store"]))
    if (
        inventory.manifest["run_id"] != mapper.manifest["inventory"]["run_id"]
        or inventory.manifest["receipt_sha256"]
        != mapper.manifest["inventory"]["receipt_sha256"]
    ):
        raise BenchmarkError("mapper benchmark inventory binding advanced")
    connection = sqlite3.connect(
        f"file:{inventory.run_directory / 'inventory.sqlite3'}?mode=ro", uri=True
    )
    try:
        whole = connection.execute(
            """SELECT COUNT(*),COALESCE(SUM(size_bytes),0) FROM files
               WHERE kind='regular' AND content_sha256 IS NOT NULL"""
        ).fetchone()
        supported = connection.execute(
            """SELECT COUNT(*),COALESCE(SUM(size_bytes),0) FROM files
               WHERE kind='regular' AND content_sha256 IS NOT NULL
                 AND semantic_eligible=1"""
        ).fetchone()
    finally:
        connection.close()
    return int(whole[0]), int(whole[1]), int(supported[0]), int(supported[1])


def run_mapper_benchmark(mapper_store: Path, corpus_path: Path) -> dict[str, Any]:
    """Run reviewed path-rule cases without reading the repository source tree."""

    corpus, corpus_sha256 = _load_corpus(corpus_path)
    mapper = current_mapper_run(mapper_store)
    scope_files, scope_bytes, supported_files, supported_bytes = _whole_scope_bytes(
        mapper_store
    )
    baseline_tokens = math.ceil(supported_bytes / 4)
    case_results: list[dict[str, Any]] = []
    for case in corpus["cases"]:
        started = time.monotonic()
        try:
            dossier = build_dossier(
                mapper_store,
                case["dossier"],
                case["terms"],
                limit_per_term=case["limit_per_term"],
                overall_limit=case["overall_limit"],
                include_semantic=case["include_semantic"],
                include_facts=False,
            )
        except DossierError as exc:
            raise BenchmarkError(
                f"benchmark dossier refused for {case['id']}: {exc}"
            ) from exc
        duration = round(time.monotonic() - started, 6)
        paths = sorted({item["path"] for item in dossier["consulted_sources"]})
        expected_hits = {
            pattern: sorted(path for path in paths if fnmatchcase(path, pattern))
            for pattern in case["expected_path_globs"]
        }
        relevant = [
            path for path in paths if _matches(path, case["relevant_path_globs"])
        ]
        unmatched = [path for path in paths if path not in relevant]
        recall = _basis_points(
            sum(bool(values) for values in expected_hits.values()), len(expected_hits)
        )
        precision = _basis_points(len(relevant), len(paths))
        dossier_bytes = len(canonical_bytes(dossier))
        dossier_tokens = math.ceil(dossier_bytes / 4)
        token_reduction = (
            0
            if baseline_tokens == 0
            else max(0, 10000 - round(10000 * dossier_tokens / baseline_tokens))
        )
        passed = (
            recall >= case["min_recall_basis_points"]
            and precision >= case["min_precision_basis_points"]
        )
        case_results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "status": "PASS" if passed else "FAILED_REVIEWED_THRESHOLD",
                "dossier": case["dossier"],
                "terms": case["terms"],
                "dossier_receipt_sha256": dossier["receipt_sha256"],
                "mapper_run_id": dossier["mapper"]["run_id"],
                "duration_seconds": duration,
                "retrieved_source_count": len(paths),
                "relevant_source_count": len(relevant),
                "expected_anchor_count": len(expected_hits),
                "matched_anchor_count": sum(
                    bool(values) for values in expected_hits.values()
                ),
                "expected_path_hits": expected_hits,
                "precision_basis_points": precision,
                "recall_basis_points": recall,
                "thresholds": {
                    "precision_basis_points": case["min_precision_basis_points"],
                    "recall_basis_points": case["min_recall_basis_points"],
                },
                "unmatched_to_reviewed_path_rules": unmatched[:100],
                "unmatched_paths_omitted": max(0, len(unmatched) - 100),
                "dossier_bytes": dossier_bytes,
                "estimated_dossier_tokens": dossier_tokens,
                "estimated_whole_scope_tokens": baseline_tokens,
                "estimated_token_reduction_basis_points": token_reduction,
                "dossier_completeness": dossier["completeness"],
                "authority_granted": False,
            }
        )
    passing = sum(item["status"] == "PASS" for item in case_results)
    return seal_document(
        {
            "schema": RESULT_SCHEMA,
            "status": "PASS" if passing == len(case_results) else "PARTIAL",
            "authority": "non-authoritative-retrieval-quality-measurement",
            "authority_granted": False,
            "corpus": {
                "path": str(corpus_path.resolve(strict=True)),
                "sha256": corpus_sha256,
                "id": corpus["corpus_id"],
                "reviewed_at": corpus["reviewed_at"],
                "review_scope": corpus["review_scope"],
            },
            "mapper": {
                "run_id": mapper.manifest["run_id"],
                "manifest_receipt_sha256": mapper.manifest["receipt_sha256"],
                "inventory_run_id": mapper.manifest["inventory"]["run_id"],
                "inventory_receipt_sha256": mapper.manifest["inventory"][
                    "receipt_sha256"
                ],
            },
            "whole_scope": {
                "hashed_regular_files": scope_files,
                "bytes": scope_bytes,
                "supported_text_files": supported_files,
                "supported_text_bytes": supported_bytes,
                "estimated_supported_text_tokens": baseline_tokens,
                "token_estimate": "ceil(semantic-eligible-file-bytes/4); deterministic comparison only",
            },
            "summary": {
                "cases": len(case_results),
                "passing": passing,
                "failed": len(case_results) - passing,
                "minimum_precision_basis_points": min(
                    item["precision_basis_points"] for item in case_results
                ),
                "minimum_recall_basis_points": min(
                    item["recall_basis_points"] for item in case_results
                ),
                "minimum_token_reduction_basis_points": min(
                    item["estimated_token_reduction_basis_points"]
                    for item in case_results
                ),
                "broad_completeness_claimed": False,
            },
            "cases": case_results,
            "limitations": [
                "Path-rule review measures retrieval against declared anchors and relevance globs; it is not semantic truth or exhaustive source review.",
                "Token counts are deterministic byte-based estimates, not provider-tokenizer counts.",
                "A passing benchmark grants no ownership, deletion, deployment, or milestone authority.",
            ],
        }
    )


def run_context_benchmark(mapper_store: Path, corpus_path: Path) -> dict[str, Any]:
    """Measure ranked fixed-budget context against reviewed symbol anchors.

    The benchmark reads only authenticated mapper facts.  It does not read or
    execute repository sources and it never promotes a ranking score to fact.
    """

    corpus, corpus_sha256 = _load_context_corpus(corpus_path)
    mapper = current_mapper_run(mapper_store)
    case_results: list[dict[str, Any]] = []
    for case in corpus["cases"]:
        started = time.monotonic()
        try:
            projection = build_context_projection(
                mapper_store,
                case["dossier"],
                case["terms"],
                token_budget=case["token_budget"],
                include_semantic=case["include_semantic"],
            )
            replay = build_context_projection(
                mapper_store,
                case["dossier"],
                case["terms"],
                token_budget=case["token_budget"],
                include_semantic=case["include_semantic"],
            )
        except DossierError as exc:
            raise BenchmarkError(
                f"context benchmark projection refused for {case['id']}: {exc}"
            ) from exc
        duration = round(time.monotonic() - started, 6)
        deterministic_replay = canonical_bytes(projection) == canonical_bytes(replay)
        entries = projection["entries"]
        entry_index: dict[tuple[str, str, str], tuple[int, dict[str, Any]]] = {}
        all_source_bound = True
        for rank, entry in enumerate(entries, 1):
            source = entry.get("source")
            path = source.get("path") if isinstance(source, dict) else None
            identity = (
                source.get("identity_sha256") if isinstance(source, dict) else None
            )
            if not isinstance(path, str) or not isinstance(identity, str):
                all_source_bound = False
                continue
            entry_index[(path, entry["kind"], entry["qualified_name"])] = (
                rank,
                entry,
            )

        anchor_results: list[dict[str, Any]] = []
        matched = relationship_matched = 0
        for anchor in case["expected_anchors"]:
            located = entry_index.get(
                (anchor["path"], anchor["kind"], anchor["qualified_name"])
            )
            rank = located[0] if located else None
            entry = located[1] if located else None
            relationship_expanded = bool(
                entry is not None
                and not entry["matched_terms"]
                and entry["relation_context"]
            )
            rank_satisfied = rank is not None and rank <= anchor["max_rank"]
            relationship_satisfied = bool(
                rank_satisfied
                and relationship_expanded == anchor["relationship_expanded"]
            )
            satisfied = rank_satisfied and relationship_satisfied
            matched += int(satisfied)
            relationship_matched += int(satisfied and anchor["relationship_expanded"])
            anchor_results.append(
                {
                    **anchor,
                    "observed_rank": rank,
                    "observed_relationship_expanded": relationship_expanded,
                    "status": "PASS" if satisfied else "MISSING_OR_MISRANKED",
                }
            )

        sourced_entries = [
            item
            for item in entries
            if isinstance(item.get("source"), dict)
            and isinstance(item["source"].get("path"), str)
        ]
        relevant_entries = [
            item
            for item in sourced_entries
            if _matches(item["source"]["path"], case["relevant_path_globs"])
        ]
        recall = _basis_points(matched, len(case["expected_anchors"]))
        precision = _basis_points(len(relevant_entries), len(sourced_entries))
        utilization = _basis_points(
            projection["budget"]["used"], projection["budget"]["requested"]
        )
        context_matches_entries = projection["context"].splitlines() == [
            item["context_line"] for item in entries
        ]
        passed = bool(
            deterministic_replay
            and all_source_bound
            and context_matches_entries
            and projection["budget"]["used"] <= projection["budget"]["requested"]
            and recall >= case["min_anchor_recall_basis_points"]
            and precision >= case["min_precision_basis_points"]
            and relationship_matched >= case["min_relationship_anchor_count"]
            and utilization >= case["min_budget_utilization_basis_points"]
        )
        case_results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "status": "PASS" if passed else "FAILED_REVIEWED_THRESHOLD",
                "dossier": case["dossier"],
                "terms": case["terms"],
                "projection_receipt_sha256": projection["receipt_sha256"],
                "ranking_algorithm": projection["ranking"]["algorithm"],
                "mapper_run_id": projection["mapper"]["run_id"],
                "duration_seconds_including_replay": duration,
                "token_budget": projection["budget"],
                "budget_utilization_basis_points": utilization,
                "entry_count": len(entries),
                "candidate_count": projection["candidate_count"],
                "projectable_candidate_count": projection[
                    "projectable_candidate_count"
                ],
                "relationship_expanded_entry_count": sum(
                    not item["matched_terms"] and bool(item["relation_context"])
                    for item in entries
                ),
                "expected_anchor_count": len(case["expected_anchors"]),
                "matched_anchor_count": matched,
                "matched_relationship_anchor_count": relationship_matched,
                "anchor_recall_basis_points": recall,
                "relevant_entry_precision_basis_points": precision,
                "thresholds": {
                    "anchor_recall_basis_points": case[
                        "min_anchor_recall_basis_points"
                    ],
                    "relevant_entry_precision_basis_points": case[
                        "min_precision_basis_points"
                    ],
                    "relationship_anchor_count": case["min_relationship_anchor_count"],
                    "budget_utilization_basis_points": case[
                        "min_budget_utilization_basis_points"
                    ],
                },
                "anchors": anchor_results,
                "deterministic_replay": deterministic_replay,
                "all_selected_entries_source_bound": all_source_bound,
                "context_lines_match_entries": context_matches_entries,
                "authority_granted": False,
            }
        )

    passing = sum(item["status"] == "PASS" for item in case_results)
    return seal_document(
        {
            "schema": CONTEXT_RESULT_SCHEMA,
            "status": "PASS" if passing == len(case_results) else "PARTIAL",
            "authority": "non-authoritative-ranked-context-quality-measurement",
            "authority_granted": False,
            "corpus": {
                "path": str(corpus_path.resolve(strict=True)),
                "sha256": corpus_sha256,
                "id": corpus["corpus_id"],
                "reviewed_at": corpus["reviewed_at"],
            },
            "donor": corpus["donor"],
            "mapper": {
                "run_id": mapper.manifest["run_id"],
                "manifest_receipt_sha256": mapper.manifest["receipt_sha256"],
                "inventory_run_id": mapper.manifest["inventory"]["run_id"],
                "inventory_receipt_sha256": mapper.manifest["inventory"][
                    "receipt_sha256"
                ],
            },
            "summary": {
                "cases": len(case_results),
                "passing": passing,
                "failed": len(case_results) - passing,
                "minimum_anchor_recall_basis_points": min(
                    item["anchor_recall_basis_points"] for item in case_results
                ),
                "minimum_relevant_entry_precision_basis_points": min(
                    item["relevant_entry_precision_basis_points"]
                    for item in case_results
                ),
                "minimum_budget_utilization_basis_points": min(
                    item["budget_utilization_basis_points"] for item in case_results
                ),
                "relationship_anchors_proved": sum(
                    item["matched_relationship_anchor_count"] for item in case_results
                ),
                "deterministic_replays": sum(
                    item["deterministic_replay"] for item in case_results
                ),
                "broad_completeness_claimed": False,
            },
            "cases": case_results,
            "limitations": [
                "Reviewed anchors measure fixed-budget retrieval for named tasks; they are not exhaustive semantic truth.",
                "The lexical budget is deterministic and intentionally makes no provider-tokenizer equivalence claim.",
                "Relationship expansion is derived ranking evidence, not an authority or source fact.",
                "A passing benchmark grants no ownership, deletion, deployment, or milestone authority.",
            ],
        }
    )
