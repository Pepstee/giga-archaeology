from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from twin_core import research_benchmark as research_benchmark_module
from twin_core.passage_retrieval import dense_ranking_identity_sha256
from twin_core.research_benchmark import (
    BENCHMARK_MEASUREMENT_SCHEMA,
    BENCHMARK_RUN_SCHEMA,
    ResearchBenchmarkError,
    admit_deepresearch_bench_campaign,
    assemble_deepresearch_bench_cohort,
    build_deepresearch_bench_fact_benchmark_run,
    build_extractive_benchmark_run,
    build_synthesis_benchmark_run,
    compare_scores,
    import_deepresearch_bench_cases,
    import_deepresearch_bench_competitor_cohort,
    import_deepresearch_bench_fact_results,
    import_deepresearch_bench_race_results,
    import_pdrbench_cases,
    import_pdrbench_results,
    import_reportbench_cases,
    import_reportbench_results,
    plan_deepresearch_bench_campaign,
    prepare_deepresearch_bench_run_record,
    prepare_deepresearch_bench_submission,
    prepare_deepresearch_bench_synthesis_record,
    score_benchmark_run,
    score_deepsynth_static,
    score_retrieval_ablation,
    score_retrieval_cohort,
)
from twin_core.research_export import (
    SYNTHESIS_PROPOSAL_SCHEMA,
    build_synthesis_packet,
)
from twin_core.research_project import ResearchProjectStore, validate_project_plan
from twin_core.scientific_pipeline_cli import main


def _run(*, system: str = "giga", case_id: str = "zh-en-1") -> dict:
    return {
        "schema_version": BENCHMARK_RUN_SCHEMA,
        "system": system,
        "case_id": case_id,
        "language": "mixed",
        "question": "How should research systems verify citations? 研究系统如何验证引用？",
        "started_at": "2026-08-30T08:00:00+00:00",
        "finished_at": "2026-08-30T08:00:02+00:00",
        "cost_usd": 0.02,
        "cost_scope": "provider_api_charges",
        "minimum_sources": 2,
        "expected_terms": ["verify citations", "验证引用"],
        "require_contradiction": True,
        "sources": [
            {
                "source_id": "s1",
                "url": "https://example.edu/research",
                "receipt_sha256": "a" * 64,
                "content_sha256": "b" * 64,
                "fetched_at": "2026-08-30T07:59:00+00:00",
            },
            {
                "source_id": "s2",
                "url": "https://gitee.com/team/research",
                "receipt_sha256": "c" * 64,
                "content_sha256": "d" * 64,
                "fetched_at": "2026-08-30T07:59:30+00:00",
            },
        ],
        "claims": [
            {
                "text": "Research systems should verify citations. 研究系统应验证引用。",
                "source_ids": ["s1"],
                "evidence": [
                    {
                        "source_id": "s1",
                        "quote": "Research systems verify citations. 研究系统验证引用。",
                    }
                ],
                "review_status": "accept",
                "position": "supports",
            },
            {
                "text": "Some workflows do not verify citations.",
                "source_ids": ["s2"],
                "evidence": [
                    {"source_id": "s2", "quote": "Some workflows do not verify citations."}
                ],
                "review_status": "accept",
                "position": "contradicts",
            },
        ],
    }


def _retrieval_ablation_artifacts() -> tuple[dict, dict, dict]:
    query = "How should research systems verify claims and preserve provenance?"
    receipts = [character * 64 for character in "abcd"]
    passages = [f"passage-{index}" for index in range(4)]
    specification = {
        "schema_version": "giga.research-retrieval-microbenchmark.v1",
        "query": query,
        "corpus_receipt_sha256s": receipts,
        "relevant_receipt_sha256s": receipts[:2],
        "cutoff": 2,
    }
    bm25 = {
        "query": query,
        "indexed_passages": 4,
        "results": [{"passage_id": passages[2]}],
    }
    hybrid = {
        "query": query,
        "indexed_passages": 4,
        "results": [
            {"passage_id": passage_id, "receipt_sha256": receipt}
            for passage_id, receipt in zip(
                [passages[2], passages[1], passages[0], passages[3]],
                [receipts[2], receipts[1], receipts[0], receipts[3]],
                strict=True,
            )
        ],
        "dense_provider": {
            "schema_version": "giga.research-dense-ranking.v1",
            "engine": "fastembed",
            "engine_version": "0.8.0",
            "model": "multilingual-test-model",
            "model_source": "https://example.org/model",
            "model_license": "apache-2.0",
            "dimension": 384,
            "passage_count": 4,
            "model_cache": {
                "manifest_sha256": "f" * 64,
                "snapshot_revisions": ["1" * 40],
            },
            "passage_ids": [passages[1], passages[0], passages[2], passages[3]],
            "scores": [
                {"passage_id": passage_id, "cosine_similarity": score}
                for passage_id, score in zip(
                    [passages[1], passages[0], passages[2], passages[3]],
                    [0.9, 0.8, 0.7, 0.6],
                    strict=True,
                )
            ],
            "query": query,
            "claim_authority": False,
        },
    }
    hybrid["dense_provider"]["ranking_sha256"] = dense_ranking_identity_sha256(
        hybrid["dense_provider"]
    )
    return specification, bm25, hybrid


def test_scores_owned_dense_retrieval_against_exact_bm25_corpus() -> None:
    specification, bm25, hybrid = _retrieval_ablation_artifacts()
    score = score_retrieval_ablation(specification, bm25, hybrid)
    assert score["rankings"]["bm25"]["recall_at_k"] == 0.0
    assert score["rankings"]["dense"]["recall_at_k"] == 1.0
    assert score["rankings"]["hybrid_rrf"]["recall_at_k"] == 0.5
    assert score["deltas"]["dense_recall_at_k_minus_bm25"] == 1.0
    assert score["deltas"]["hybrid_recall_at_k_minus_bm25"] == 0.5
    assert score["dense_provider"]["engine_version"] == "0.8.0"
    assert len(score["result_identity_sha256"]) == 64
    assert score["claim_authority"] is False

    hybrid["dense_provider"]["elapsed_ms"] = 9999
    repeated = score_retrieval_ablation(specification, bm25, hybrid)
    assert repeated["result_identity_sha256"] == score["result_identity_sha256"]
    assert repeated["artifacts"]["hybrid_sha256"] != score["artifacts"]["hybrid_sha256"]


def test_retrieval_ablation_supports_graded_external_relevance() -> None:
    specification, bm25, hybrid = _retrieval_ablation_artifacts()
    specification["relevance_grade_by_receipt"] = {
        "a" * 64: 2,
        "b" * 64: 1,
    }
    score = score_retrieval_ablation(specification, bm25, hybrid)
    assert score["relevance_mode"] == "graded"
    assert score["rankings"]["dense"]["ndcg_at_k"] < 1.0
    assert score["rankings"]["dense"]["ndcg_at_k"] > score["rankings"]["bm25"]["ndcg_at_k"]

    specification["relevance_grade_by_receipt"].pop("b" * 64)
    with pytest.raises(ResearchBenchmarkError, match="cover every relevant receipt"):
        score_retrieval_ablation(specification, bm25, hybrid)


def _retrieval_cohort_fixture(source_cases: int = 20) -> tuple[dict, list[dict]]:
    datasets = [
        {
            "dataset_id": "capretrieval-zh",
            "language": "zh",
            "source_url": "https://huggingface.co/datasets/lxucs/CapRetrieval",
            "revision": "c311ae680fdf621a38a4abd4704ad92f822d6897",
            "license": "Apache-2.0",
            "artifacts": [
                {"name": "passages/test.jsonl", "sha256": "2" * 64, "bytes": 367403},
                {"name": "queries/test.jsonl", "sha256": "3" * 64, "bytes": 176654},
            ],
        },
        {
            "dataset_id": "capretrieval-en",
            "language": "en",
            "source_url": "https://huggingface.co/datasets/lxucs/CapRetrievalEn",
            "revision": "a64b947bc33a38ce77dff90a3d5a5bff6ead8fec",
            "license": "Apache-2.0",
            "artifacts": [
                {"name": "passages/test.jsonl", "sha256": "4" * 64, "bytes": 446880},
                {"name": "queries/test.jsonl", "sha256": "5" * 64, "bytes": 157837},
            ],
        },
    ]
    cases = []
    scores = []
    selected_ids = [f"source-{index:03d}" for index in range(source_cases)]
    for dataset in datasets:
        for source_id in selected_ids:
            specification, bm25, hybrid = _retrieval_ablation_artifacts()
            query = f"{dataset['language']} external query {source_id}"
            specification["query"] = query
            specification["relevance_grade_by_receipt"] = {
                "a" * 64: 2,
                "b" * 64: 1,
            }
            bm25["query"] = query
            hybrid["query"] = query
            hybrid["dense_provider"]["query"] = query
            score = score_retrieval_ablation(specification, bm25, hybrid)
            score_sha = hashlib.sha256(
                json.dumps(score, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            cases.append(
                {
                    "case_id": f"{dataset['language']}-{source_id}",
                    "dataset_id": dataset["dataset_id"],
                    "source_query_id": source_id,
                    "language": dataset["language"],
                    "query": query,
                    "score_sha256": score_sha,
                }
            )
            scores.append(score)
    selection_digest = hashlib.sha256(
        json.dumps(selected_ids, separators=(",", ":")).encode()
    ).hexdigest()
    manifest = {
        "schema_version": "giga.research-retrieval-cohort-manifest.v1",
        "cohort_id": "capretrieval-paired-r1",
        "selection": {
            "method": "lowest SHA-256 of shared source query IDs",
            "seed_sha256": "6" * 64,
            "source_universe_cases": 100,
            "selected_source_cases": source_cases,
            "selected_source_ids_sha256": selection_digest,
        },
        "datasets": datasets,
        "cases": cases,
    }
    return manifest, scores


def test_scores_paired_external_multilingual_retrieval_cohort() -> None:
    manifest, scores = _retrieval_cohort_fixture()
    cohort = score_retrieval_cohort(manifest, scores)
    assert cohort["case_count"] == 40
    assert cohort["languages"] == ["en", "zh"]
    assert cohort["eligibility"]["enough_cases_per_language"] is True
    assert cohort["groups"]["zh"]["aggregate"]["dense"]["ndcg_at_k"]["mean"] > 0
    dense_ndcg = next(
        row
        for row in cohort["groups"]["overall"]["comparisons"]
        if row["metric"] == "ndcg_at_k" and row["left_system"] == "dense"
    )
    assert dense_ndcg["superiority_state"] == "left_superior"
    assert cohort["hybrid_ndcg_superiority_over_bm25"]["overall"]["state"] == (
        "left_superior"
    )
    assert cohort["competitive_superiority_established"] is False
    assert cohort["claim_authority"] is False

    manifest["datasets"][0]["license"] = "unknown"
    with pytest.raises(ResearchBenchmarkError, match="license must be explicit"):
        score_retrieval_cohort(manifest, scores)

    manifest, scores = _retrieval_cohort_fixture()
    manifest["selection"]["selected_source_ids_sha256"] = "0" * 64
    with pytest.raises(ResearchBenchmarkError, match="declared paired selection"):
        score_retrieval_cohort(manifest, scores)


def test_retrieval_ablation_rejects_incomplete_or_unbound_rankings() -> None:
    specification, bm25, hybrid = _retrieval_ablation_artifacts()
    hybrid["dense_provider"]["passage_ids"].pop()
    with pytest.raises(ResearchBenchmarkError, match="exact passage corpus"):
        score_retrieval_ablation(specification, bm25, hybrid)

    specification, bm25, hybrid = _retrieval_ablation_artifacts()
    hybrid["results"][0]["receipt_sha256"] = "f" * 64
    with pytest.raises(ResearchBenchmarkError, match="provenance"):
        score_retrieval_ablation(specification, bm25, hybrid)

    specification, bm25, hybrid = _retrieval_ablation_artifacts()
    hybrid["results"][0], hybrid["results"][1] = hybrid["results"][1], hybrid["results"][0]
    with pytest.raises(ResearchBenchmarkError, match="declared fusion policy"):
        score_retrieval_ablation(specification, bm25, hybrid)

    specification, bm25, hybrid = _retrieval_ablation_artifacts()
    hybrid["dense_provider"]["scores"][0]["cosine_similarity"] = -0.25
    with pytest.raises(ResearchBenchmarkError, match="hash differs"):
        score_retrieval_ablation(specification, bm25, hybrid)

    specification, bm25, hybrid = _retrieval_ablation_artifacts()
    hybrid["dense_provider"]["query"] = "a different query"
    with pytest.raises(ResearchBenchmarkError, match="query differs"):
        score_retrieval_ablation(specification, bm25, hybrid)


def test_cli_scores_retrieval_ablation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    specification, bm25, hybrid = _retrieval_ablation_artifacts()
    paths = [tmp_path / name for name in ("specification.json", "bm25.json", "hybrid.json")]
    for path, value in zip(paths, (specification, bm25, hybrid), strict=True):
        path.write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "score.json"
    assert main(["benchmark", "score-retrieval", *(str(path) for path in paths), "--output", str(output)]) == 0
    score = json.loads(capsys.readouterr().out)
    assert score["rankings"]["dense"]["recall_at_k"] == 1.0
    assert json.loads(output.read_text(encoding="utf-8")) == score


def test_cli_scores_external_retrieval_cohort(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest, scores = _retrieval_cohort_fixture(source_cases=1)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    score_paths = []
    for index, score in enumerate(scores):
        path = tmp_path / f"score-{index}.json"
        path.write_text(json.dumps(score), encoding="utf-8")
        score_paths.append(path)
    output = tmp_path / "cohort.json"
    assert (
        main(
            [
                "benchmark",
                "score-retrieval-cohort",
                str(manifest_path),
                *(str(path) for path in score_paths),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["case_count"] == 2
    assert result["eligibility"]["enough_cases_per_language"] is False
    assert json.loads(output.read_text(encoding="utf-8")) == result


def test_scores_grounded_bilingual_run_and_keeps_efficiency_separate() -> None:
    score = score_benchmark_run(_run())
    assert score["quality_score"] > 0.90
    assert score["metrics"]["citation_existence_accuracy"] == 1.0
    assert score["metrics"]["provenance_completeness"] == 1.0
    assert score["metrics"]["expected_term_coverage"] == 1.0
    assert score["metrics"]["latency_ms"] == 2000
    assert score["metrics"]["cost_usd"] == 0.02
    assert score["metrics"]["cost_state"] == "measured"


def test_missing_citation_unsupported_claim_and_provenance_are_penalised() -> None:
    run = _run()
    run["sources"][0]["receipt_sha256"] = "missing"
    run["claims"][0]["source_ids"] = ["ghost"]
    run["claims"][0]["evidence"] = [{"quote": "Unrelated weather report"}]
    score = score_benchmark_run(run)
    assert score["metrics"]["citation_existence_accuracy"] == 0.5
    assert score["metrics"]["citation_lexical_support_pass_rate"] == 0.5
    assert score["metrics"]["provenance_completeness"] == 0.5


def test_empty_or_non_object_evidence_is_fail_closed() -> None:
    run = _run()
    run["claims"][0]["evidence"] = ["not-an-object"]
    score = score_benchmark_run(run)
    assert score["metrics"]["citation_lexical_support_pass_rate"] == 0.5


def test_quote_from_an_uncited_or_unknown_source_cannot_support_claim() -> None:
    run = _run()
    run["claims"][0]["evidence"][0]["source_id"] = "ghost"
    score = score_benchmark_run(run)
    assert score["metrics"]["citation_lexical_support_pass_rate"] == 0.5


def test_multiple_cited_spans_collectively_support_one_synthesis_claim() -> None:
    run = _run()
    run["claims"][0] = {
        "text": "Research systems verify citations with archived evidence.",
        "source_ids": ["s1", "s2"],
        "evidence": [
            {"source_id": "s1", "quote": "Research systems verify citations."},
            {"source_id": "s2", "quote": "Archived evidence is retained."},
        ],
        "review_status": "accept",
        "position": "supports",
    }
    score = score_benchmark_run(run)
    assert score["metrics"]["citation_lexical_support_mean"] > 0.5
    assert score["metrics"]["citation_lexical_support_pass_rate"] == 1.0


def test_expected_concepts_accept_auditable_bilingual_aliases() -> None:
    run = _run()
    run["expected_terms"] = [["验证引用", "verify citations"], ["存档", "archived"]]
    score = score_benchmark_run(run)
    assert score["metrics"]["expected_concept_count"] == 2
    assert score["metrics"]["expected_term_coverage"] == 0.5


def test_duplicate_source_ids_and_comparison_rows_are_rejected() -> None:
    run = _run()
    run["sources"][1]["source_id"] = "s1"
    with pytest.raises(ResearchBenchmarkError, match="unique"):
        score_benchmark_run(run)

    score = score_benchmark_run(_run())
    with pytest.raises(ResearchBenchmarkError, match="duplicate"):
        compare_scores([score, score])


def test_comparison_requires_identical_case_sets_and_reports_bounded_leader() -> None:
    giga = score_benchmark_run(_run())
    competitor_run = _run(system="competitor")
    competitor_run["claims"][0]["evidence"] = []
    competitor = score_benchmark_run(competitor_run)
    comparison = compare_scores([competitor, giga])
    assert comparison["leader"] == "giga"
    assert comparison["leader_statistically_superior"] is False
    assert comparison["cost_comparable"] is True
    assert "exact case set" in comparison["claim_boundary"]

    different = score_benchmark_run(_run(system="competitor", case_id="other"))
    with pytest.raises(ResearchBenchmarkError, match="identical case sets"):
        compare_scores([giga, different])


def test_paired_comparison_establishes_reproducible_cohort_superiority() -> None:
    scores = []
    for index in range(10):
        case_id = f"case-{index:02d}"
        giga = score_benchmark_run(_run(case_id=case_id))
        rival_run = _run(system="rival", case_id=case_id)
        rival_run["claims"][0]["evidence"] = []
        scores.extend([giga, score_benchmark_run(rival_run)])

    comparison = compare_scores(scores)
    repeated = compare_scores(scores)
    pair = comparison["pairwise_quality"][0]
    stats = pair["statistics"]
    assert comparison == repeated
    assert comparison["schema_version"] == "giga.research-benchmark-comparison.v3"
    assert comparison["leader"] == "giga"
    assert comparison["leader_statistically_superior"] is True
    assert pair["left_system"] == "giga"
    assert pair["right_system"] == "rival"
    assert pair["superiority_state"] == "left_superior"
    assert pair["superior_system"] == "giga"
    assert stats["wins"] == 10
    assert stats["losses"] == 0
    assert stats["randomisation_method"] == "exact_paired_sign_flip"
    assert stats["randomisation_p_value_two_sided"] == pytest.approx(2 / 1024)
    assert stats["holm_adjusted_p_value"] == pytest.approx(2 / 1024)
    assert stats["bootstrap_confidence_interval_95"]["lower"] > 0
    assert pair["metric_mean_deltas"]["citation_lexical_support_pass_rate"] > 0


def test_paired_comparison_refuses_superiority_claim_for_tiny_cohort() -> None:
    scores = []
    for index in range(4):
        case_id = f"case-{index:02d}"
        giga = score_benchmark_run(_run(case_id=case_id))
        rival_run = _run(system="rival", case_id=case_id)
        rival_run["claims"][0]["evidence"] = []
        scores.extend([giga, score_benchmark_run(rival_run)])
    comparison = compare_scores(scores)
    assert comparison["leader"] == "giga"
    assert comparison["leader_statistically_superior"] is False
    assert comparison["pairwise_quality"][0]["superiority_state"] == "insufficient_cases"


def test_comparison_rejects_tampered_quality_score() -> None:
    score = score_benchmark_run(_run())
    score["quality_score"] += 0.01
    with pytest.raises(ResearchBenchmarkError, match="does not match"):
        compare_scores([score])


def test_comparison_aliases_versioned_producers_without_mutating_scores() -> None:
    first = score_benchmark_run(_run(system="giga-v1", case_id="case-1"))
    second = score_benchmark_run(_run(system="giga-v2", case_id="case-2"))
    rival_first = score_benchmark_run(_run(system="rival", case_id="case-1"))
    rival_second = score_benchmark_run(_run(system="rival", case_id="case-2"))
    comparison = compare_scores(
        [first, second, rival_first, rival_second],
        system_aliases={"giga-v1": "giga", "giga-v2": "giga"},
    )
    by_system = {row["system"]: row for row in comparison["systems"]}
    assert by_system["giga"]["case_count"] == 2
    assert by_system["giga"]["system_members"] == ["giga-v1", "giga-v2"]
    assert comparison["system_aliases"] == {"giga-v1": "giga", "giga-v2": "giga"}
    assert first["system"] == "giga-v1"


def test_unknown_cost_is_not_coerced_to_zero_or_used_for_ranking() -> None:
    giga_run = _run()
    giga_run["cost_usd"] = None
    giga_run["cost_scope"] = None
    competitor_run = _run(system="competitor")
    giga = score_benchmark_run(giga_run)
    competitor = score_benchmark_run(competitor_run)
    comparison = compare_scores([giga, competitor])
    assert giga["metrics"]["cost_usd"] is None
    assert giga["metrics"]["cost_state"] == "unknown"
    assert comparison["cost_comparable"] is False
    by_system = {row["system"]: row for row in comparison["systems"]}
    assert by_system["giga"]["cost_usd_total"] is None
    assert by_system["competitor"]["cost_usd_total"] == 0.02
    assert "excluded from ranking" in comparison["cost_comparison_note"]


def test_measured_cost_requires_scope_and_unknown_cost_rejects_scope() -> None:
    run = _run()
    run.pop("cost_scope")
    with pytest.raises(ResearchBenchmarkError, match="cost_scope"):
        score_benchmark_run(run)
    run["cost_usd"] = None
    run["cost_scope"] = "provider_api_charges"
    with pytest.raises(ResearchBenchmarkError, match="unknown cost_usd"):
        score_benchmark_run(run)


def test_unknown_latency_is_not_coerced_to_zero_or_used_for_ranking() -> None:
    imported_run = _run(system="imported")
    imported_run.update(
        {
            "started_at": None,
            "finished_at": None,
            "latency_ms": None,
            "latency_scope": None,
        }
    )
    imported = score_benchmark_run(imported_run)
    measured = score_benchmark_run(_run())
    comparison = compare_scores([imported, measured])
    assert imported["metrics"]["latency_ms"] is None
    assert imported["metrics"]["latency_state"] == "unknown"
    assert comparison["latency_comparable"] is False
    by_system = {row["system"]: row for row in comparison["systems"]}
    assert by_system["imported"]["latency_ms_mean"] is None
    assert by_system["giga"]["latency_ms_mean"] == 2000
    assert "excluded from ranking" in comparison["latency_comparison_note"]


def test_measured_latency_requires_scope_and_unknown_latency_rejects_scope() -> None:
    run = _run()
    run["latency_ms"] = 1500
    with pytest.raises(ResearchBenchmarkError, match="latency_scope"):
        score_benchmark_run(run)
    run["latency_ms"] = None
    run["latency_scope"] = "end_to_end_wall_clock"
    with pytest.raises(ResearchBenchmarkError, match="unknown latency_ms"):
        score_benchmark_run(run)


def test_legacy_numeric_efficiency_without_scope_is_not_comparable() -> None:
    legacy = score_benchmark_run(_run(system="legacy"))
    legacy["metrics"].pop("latency_scope")
    legacy["metrics"].pop("cost_scope")
    current = score_benchmark_run(_run(system="current"))
    comparison = compare_scores([legacy, current])
    by_system = {row["system"]: row for row in comparison["systems"]}
    assert by_system["legacy"]["latency_comparable"] is False
    assert by_system["legacy"]["cost_comparable"] is False
    assert comparison["latency_comparable"] is False
    assert comparison["cost_comparable"] is False


def test_validated_synthesis_converts_to_score_input_and_cli_preserves_it(tmp_path, capsys) -> None:
    plan = {
        "project_id": "synthesis-project",
        "question": "Which evidence verifies citations?",
        "subquestions": [{"id": "Q1", "perspective_id": "evidence", "question": "Which evidence?"}],
    }
    run = {
        "schema_version": "giga.research-run.v1",
        "run_id": "synthesis-run",
        "project_id": "synthesis-project",
        "acquisitions": [
            {
                "status": "acquired",
                "receipt_sha256": "a" * 64,
                "final_url": "https://example.edu/citations",
                "content_sha256": "b" * 64,
                "fetched_at": "2026-08-30T08:00:01+00:00",
                "transport": "fixture",
            }
        ],
        "retrievals": [
            {
                "subquestion_id": "Q1",
                "result": {
                    "results": [
                        {
                            "receipt_sha256": "a" * 64,
                            "passage_id": "p1",
                            "text_sha256": "c" * 64,
                            "start": 0,
                            "end": 34,
                            "text": "Evidence verifies research citations.",
                        }
                    ]
                },
            }
        ],
    }
    packet = build_synthesis_packet(plan, run)
    proposal = {
        "schema_version": SYNTHESIS_PROPOSAL_SCHEMA,
        "packet_sha256": packet["packet_sha256"],
        "run_id": packet["run_id"],
        "sections": [
            {
                "section_id": packet["outline"][0]["section_id"],
                "heading": packet["outline"][0]["heading"],
                "paragraphs": [
                    {
                        "text": "Evidence verifies research citations.",
                        "evidence_ids": ["E1"],
                    }
                ],
            }
        ],
    }
    measurement = {
        "schema_version": BENCHMARK_MEASUREMENT_SCHEMA,
        "system": "giga-synthesis",
        "case_id": "case-1",
        "language": "en",
        "started_at": "2026-08-30T08:00:00+00:00",
        "finished_at": "2026-08-30T08:00:02+00:00",
        "cost_usd": None,
        "cost_scope": None,
        "minimum_sources": 1,
        "expected_terms": ["verify citations"],
        "require_contradiction": False,
    }
    benchmark_run = build_synthesis_benchmark_run(packet, proposal, measurement)
    assert benchmark_run["sources"][0]["content_sha256"] == "b" * 64
    assert benchmark_run["claims"][0]["review_status"] == "pending"
    score = score_benchmark_run(benchmark_run)
    assert score["metrics"]["provenance_completeness"] == 1.0
    assert score["metrics"]["human_review_rate"] == 0.0
    assert score["metrics"]["cost_state"] == "unknown"

    extractive_run = build_extractive_benchmark_run(plan, run, measurement)
    assert extractive_run["generation_mode"] == "deterministic-extractive"
    assert extractive_run["source_project_id"] == "synthesis-project"
    assert extractive_run["claims"][0]["text"] == "Evidence verifies research citations."
    assert score_benchmark_run(extractive_run)["metrics"]["citation_lexical_support_pass_rate"] == 1

    packet_path = tmp_path / "packet.json"
    proposal_path = tmp_path / "proposal.json"
    measurement_path = tmp_path / "measurement.json"
    run_path = tmp_path / "benchmark-run.json"
    score_path = tmp_path / "score.json"
    for path, value in (
        (packet_path, packet),
        (proposal_path, proposal),
        (measurement_path, measurement),
    ):
        path.write_text(json.dumps(value), encoding="utf-8")
    assert (
        main(
            [
                "benchmark",
                "score-synthesis",
                str(packet_path),
                str(proposal_path),
                str(measurement_path),
                "--run-output",
                str(run_path),
                "--output",
                str(score_path),
            ]
        )
        == 0
    )
    cli_score = json.loads(capsys.readouterr().out)
    assert cli_score["benchmark_run_sha256"]
    assert json.loads(run_path.read_text(encoding="utf-8")) == benchmark_run
    assert json.loads(score_path.read_text(encoding="utf-8")) == cli_score

    extractive_run_path = tmp_path / "extractive-run.json"
    extractive_score_path = tmp_path / "extractive-score.json"
    plan_path = tmp_path / "plan.json"
    research_run_path = tmp_path / "research-run.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    research_run_path.write_text(json.dumps(run), encoding="utf-8")
    assert (
        main(
            [
                "benchmark",
                "score-extractive",
                str(plan_path),
                str(research_run_path),
                str(measurement_path),
                "--run-output",
                str(extractive_run_path),
                "--output",
                str(extractive_score_path),
            ]
        )
        == 0
    )
    cli_extractive_score = json.loads(capsys.readouterr().out)
    assert json.loads(extractive_run_path.read_text(encoding="utf-8")) == extractive_run
    assert json.loads(extractive_score_path.read_text(encoding="utf-8")) == cli_extractive_score


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("started_at", "2026-08-30", "timezone"),
        ("finished_at", "not-a-date", "ISO-8601"),
    ],
)
def test_malformed_timestamps_fail(field: str, value: str, message: str) -> None:
    run = _run()
    run[field] = value
    with pytest.raises(ResearchBenchmarkError, match=message):
        score_benchmark_run(run)


def test_existing_cli_scores_a_run(tmp_path, capsys) -> None:
    path = tmp_path / "run.json"
    output = tmp_path / "score.json"
    path.write_text(json.dumps(_run()), encoding="utf-8")
    assert main(["benchmark", "score", str(path), "--output", str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["system"] == "giga"
    assert result["quality_score"] > 0.90
    assert json.loads(output.read_text(encoding="utf-8")) == result


def test_imports_exact_official_deepresearch_bench_shape(tmp_path) -> None:
    path = tmp_path / "query.jsonl"
    rows = [
        {
            "id": identifier,
            "topic": "Science" if identifier % 2 else "Finance",
            "language": "zh" if identifier <= 50 else "en",
            "prompt": f"Research question {identifier}",
        }
        for identifier in range(1, 101)
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    manifest = import_deepresearch_bench_cases(path)
    assert manifest["case_count"] == 100
    assert manifest["languages"] == {"en": 50, "zh": 50}
    assert manifest["cases"][0]["case_id"] == "drb-001"
    assert manifest["execution_state"] == "cases_imported_not_run"

    rows.pop()
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    with pytest.raises(ResearchBenchmarkError, match="official DRB set"):
        import_deepresearch_bench_cases(path)


def test_imports_official_race_shape_and_rejects_unbounded_scores(tmp_path) -> None:
    path = tmp_path / "race.jsonl"
    rows = [
        {
            "id": identifier,
            "prompt": f"Question {identifier}",
            "comprehensiveness": 0.4,
            "insight": 0.5,
            "instruction_following": 0.6,
            "readability": 0.7,
            "overall_score": 0.55,
        }
        for identifier in (1, 2)
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    result = import_deepresearch_bench_race_results(path, require_official_set=False)
    assert result["means"]["overall_score"] == pytest.approx(0.55)
    assert result["artifact_judge_model"] is None
    assert result["artifact_judge_model_state"] == "not_embedded_in_result_rows"
    assert result["execution_state"] == "official_results_imported_not_rerun"
    rows[0]["insight"] = 1.1
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    with pytest.raises(ResearchBenchmarkError, match="invalid insight"):
        import_deepresearch_bench_race_results(path, require_official_set=False)


def test_fact_import_reproduces_official_denominator_and_reports_coverage(tmp_path) -> None:
    path = tmp_path / "fact.jsonl"
    rows = [
        {
            "id": 1,
            "citations": [{"fact": "A", "url": "https://example.com"}],
            "citations_deduped": {
                "https://example.com": {
                    "validate_error": None,
                    "validate_res": [
                        {"result": "supported"},
                        {"result": "unsupported"},
                        {"result": "unknown"},
                    ],
                }
            },
        },
        {"id": 2, "citations": [], "citations_deduped": {}},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    result = import_deepresearch_bench_fact_results(path, require_official_set=False)
    assert result["report_coverage"] == 0.5
    assert result["effective_citations_per_evaluated_report"] == 2.0
    assert result["citation_accuracy"] == 0.5
    assert result["unknown_citations"] == 1
    assert result["artifact_judge_model"] is None


def test_imports_predeclared_published_competitor_cohort(tmp_path, capsys) -> None:
    race_path = tmp_path / "race.jsonl"
    fact_path = tmp_path / "fact.jsonl"
    race_rows = [
        {
            "id": identifier,
            "prompt": f"Question {identifier}",
            "comprehensiveness": identifier / 200,
            "insight": 0.5,
            "instruction_following": 0.6,
            "readability": 0.7,
            "overall_score": 0.55,
        }
        for identifier in range(1, 101)
    ]
    fact_rows = [
        {
            "id": identifier,
            "citations": [{"fact": "A", "url": "https://example.com"}],
            "citations_deduped": {
                "https://example.com": {
                    "validate_error": None,
                    "validate_res": [{"result": "supported"}],
                }
            },
        }
        for identifier in range(1, 101)
    ]
    race_path.write_text("\n".join(json.dumps(row) for row in race_rows), encoding="utf-8")
    fact_path.write_text("\n".join(json.dumps(row) for row in fact_rows), encoding="utf-8")
    result = import_deepresearch_bench_competitor_cohort(
        race_path,
        fact_path,
        system="published-rival",
        case_ids=["drb-001", "drb-059"],
    )
    assert result["case_ids"] == ["drb-001", "drb-059"]
    assert result["case_count"] == 2
    assert result["race"]["means"]["comprehensiveness"] == pytest.approx(0.15)
    assert result["fact"]["report_coverage"] == 1.0
    assert result["artifacts"]["race_sha256"]

    output = tmp_path / "cohort.json"
    assert (
        main(
            [
                "benchmark",
                "import-drb-competitor-cohort",
                "published-rival",
                str(race_path),
                str(fact_path),
                "drb-001",
                "drb-059",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    cli_result = json.loads(capsys.readouterr().out)
    assert cli_result == result
    assert json.loads(output.read_text(encoding="utf-8")) == result


def test_imports_reportbench_manifest_and_count_based_results(
    tmp_path, capsys, monkeypatch
) -> None:
    cases_path = tmp_path / "reportbench.jsonl"
    cases = [
        {
            "arxiv_id": f"2401.{identifier:05d}",
            "prompt": f"Review topic {identifier}",
            "application_domain": "Computing",
            "update_date": "2025-01-01",
        }
        for identifier in range(100)
    ]
    cases_path.write_text("\n".join(json.dumps(row) for row in cases), encoding="utf-8")
    related_path = tmp_path / "related.csv"
    statement_path = tmp_path / "statement.csv"
    with related_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "arxiv_id",
                "predicted_count",
                "ground_truth_count",
                "intersection_count",
            ],
        )
        writer.writeheader()
        for row in cases:
            writer.writerow(
                {
                    "arxiv_id": row["arxiv_id"],
                    "predicted_count": 10,
                    "ground_truth_count": 20,
                    "intersection_count": 5,
                }
            )
    with statement_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "arxiv_id",
                "total_citations",
                "total_no_citations",
                "matched_statements",
                "aligned_statements",
                "no_citations_correct",
                "no_citations_incorrect",
                "no_citations_tie",
            ],
        )
        writer.writeheader()
        for row in cases:
            writer.writerow(
                {
                    "arxiv_id": row["arxiv_id"],
                    "total_citations": 8,
                    "total_no_citations": 4,
                    "matched_statements": 6,
                    "aligned_statements": 3,
                    "no_citations_correct": 2,
                    "no_citations_incorrect": 1,
                    "no_citations_tie": 1,
                }
            )

    manifest = import_reportbench_cases(cases_path, require_official_set=False)
    assert manifest["case_count"] == 100
    assert manifest["application_domains"] == {"Computing": 100}
    monkeypatch.setattr(
        research_benchmark_module,
        "REPORTBENCH_V1_1_SHA256",
        manifest["artifact_sha256"],
    )
    result = import_reportbench_results(
        cases_path,
        related_path,
        statement_path,
        system="published-system",
    )
    metrics = result["metrics"]
    assert metrics["reference_precision"] == 0.5
    assert metrics["reference_recall"] == 0.25
    assert metrics["reference_f1"] == pytest.approx(1 / 3)
    assert metrics["citation_source_match_rate"] == 0.75
    assert metrics["citation_statement_alignment_rate"] == 0.5
    assert metrics["non_cited_factual_accuracy"] == pytest.approx(2 / 3)
    assert metrics["non_cited_verdict_coverage"] == 1.0
    assert result["artifact_judge_models"] is None
    assert result["artifacts"]["cases_sha256"] == manifest["artifact_sha256"]

    output = tmp_path / "reportbench-result.json"
    assert (
        main(
            [
                "benchmark",
                "import-reportbench-results",
                "published-system",
                str(cases_path),
                str(related_path),
                str(statement_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == result
    assert json.loads(output.read_text(encoding="utf-8")) == result

    related_rows = related_path.read_text(encoding="utf-8").splitlines()
    related_rows[1] = related_rows[1].replace(",10,20,5", ",10,20,11")
    related_path.write_text("\n".join(related_rows) + "\n", encoding="utf-8")
    with pytest.raises(ResearchBenchmarkError, match="intersection"):
        import_reportbench_results(
            cases_path,
            related_path,
            statement_path,
            system="invalid",
        )


def test_imports_pdrbench_manifest_and_complete_pqr_results(
    tmp_path, capsys, monkeypatch
) -> None:
    cases_path = tmp_path / "pdrbench.jsonl"
    cases = [
        {
            "id": identifier,
            "domain": "Education",
            "language": "en",
            "taskid": identifier,
            "userid": f"User{identifier}",
            "task": f"Research task {identifier}",
            "query": f"Research task {identifier}\n\nUser profile: Profile {identifier}",
        }
        for identifier in (1, 3, 5)
    ]
    cases_path.write_text("\n".join(json.dumps(row) for row in cases), encoding="utf-8")
    manifest = import_pdrbench_cases(cases_path, require_official_set=False)
    assert manifest["case_count"] == 3
    assert manifest["task_persona_pair_count"] == 3
    assert manifest["domains"] == {"Education": 3}
    assert [row["benchmark_id"] for row in manifest["cases"]] == [1, 3, 5]
    with pytest.raises(ResearchBenchmarkError, match="exact pinned"):
        import_pdrbench_cases(cases_path)
    monkeypatch.setitem(
        research_benchmark_module.PDRBENCH_OFFICIAL_ARTIFACTS,
        manifest["artifact_sha256"],
        {"language": "en", "case_count": 3, "cohort": "contract_test"},
    )

    personalization_path = tmp_path / "personalization.jsonl"
    quality_path = tmp_path / "quality.jsonl"
    reliability_path = tmp_path / "reliability.jsonl"
    personalization_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": row["id"],
                    "goal_alignment": 8,
                    "content_alignment": 8,
                    "presentation_fit": 8,
                    "actionability_practicality": 8,
                    "p_overall_score": 8,
                }
            )
            for row in cases
        ),
        encoding="utf-8",
    )
    quality_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": row["id"],
                    "depth_insight": 7,
                    "logical_coherence": 7,
                    "clarity_readability": 7,
                    "q_overall_score": 7,
                }
            )
            for row in cases
        ),
        encoding="utf-8",
    )
    reliability_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": row["id"],
                    "factual_claims": ["supported", "unsupported", "uncited"],
                    "factual_claims_deduped": {
                        "https://example.test/source": {
                            "facts": ["supported", "unsupported"],
                            "validate_error": None,
                            "validate_res": [
                                {"idx": 0, "result": "supported"},
                                {"idx": 1, "result": "unsupported"},
                            ],
                        },
                        "no_url": {"facts": ["uncited"]},
                    },
                }
            )
            for row in cases
        ),
        encoding="utf-8",
    )

    result = import_pdrbench_results(
        cases_path,
        personalization_path,
        quality_path,
        reliability_path,
        system="personalized-system",
    )
    assert result["case_count"] == 3
    assert result["cohort"] == "contract_test"
    assert result["metrics"]["p_overall_score"] == 8
    assert result["metrics"]["q_overall_score"] == 7
    assert result["metrics"]["factual_accuracy"] == 5
    assert result["metrics"]["citation_coverage"] == pytest.approx(20 / 3)
    assert result["metrics"]["r_overall_score"] == pytest.approx(35 / 6)
    assert result["artifact_judge_models"] is None
    assert result["reliability_counts"]["uncited_claims"] == 3

    output = tmp_path / "pdrbench-result.json"
    assert (
        main(
            [
                "benchmark",
                "import-pdrbench-results",
                "personalized-system",
                str(cases_path),
                str(personalization_path),
                str(quality_path),
                str(reliability_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == result
    assert json.loads(output.read_text(encoding="utf-8")) == result

    reliability_rows = reliability_path.read_text(encoding="utf-8").splitlines()
    invalid = json.loads(reliability_rows[0])
    invalid["factual_claims_deduped"]["https://example.test/source"]["validate_res"].pop()
    reliability_rows[0] = json.dumps(invalid)
    reliability_path.write_text("\n".join(reliability_rows), encoding="utf-8")
    with pytest.raises(ResearchBenchmarkError, match="validation count"):
        import_pdrbench_results(
            cases_path,
            personalization_path,
            quality_path,
            reliability_path,
            system="invalid",
        )


def test_scores_complete_deepsynth_contract_with_micro_macro_and_measurements(
    tmp_path, capsys
) -> None:
    gold_path = tmp_path / "deepsynth-gold.json"
    predictions_path = tmp_path / "deepsynth-predictions.json"
    gold_path.write_text(
        json.dumps(
            [
                {"Question Number": "001", "Answers": {"a": 1, "b": 2}},
                {"Question Number": 2, "Answers": {"x": ["yes", "no"]}},
            ]
        ),
        encoding="utf-8",
    )
    predictions = [
        {
            "Question Number": 1,
            "answer": '<Answer>: {"a": 1, "b": 3, "extra": 4}',
            "cost_usd": 0.1,
            "latency_s": 2,
        },
        {
            "Question Number": "002",
            "answer": {"x": ["yes", "no"]},
            "cost_usd": 0.2,
            "latency_s": 4,
        },
    ]
    predictions_path.write_text(json.dumps(predictions), encoding="utf-8")

    score = score_deepsynth_static(
        gold_path, predictions_path, system="structured-system"
    )
    metrics = score["metrics"]
    assert score["case_ids"] == ["deepsynth-001", "deepsynth-002"]
    assert metrics["exact_task_match_rate"] == 0.5
    assert metrics["exact_key_value_accuracy"] == 0.75
    assert metrics["partial_similarity"] == 0.75
    assert metrics["micro_precision"] == 0.6
    assert metrics["micro_recall"] == 0.75
    assert metrics["micro_f1"] == pytest.approx(2 / 3)
    assert metrics["macro_f1"] == 0.7
    assert metrics["cost_reporting_coverage"] == 1
    assert metrics["latency_reporting_coverage"] == 1
    assert metrics["cost_usd_total"] == pytest.approx(0.3)
    assert metrics["latency_s_mean"] == 3
    assert score["dataset_identity_state"] == "user_supplied_artifact_not_officially_pinned"

    output = tmp_path / "deepsynth-score.json"
    assert (
        main(
            [
                "benchmark",
                "score-deepsynth",
                "structured-system",
                str(gold_path),
                str(predictions_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == score
    assert json.loads(output.read_text(encoding="utf-8")) == score

    predictions_path.write_text(json.dumps(predictions[:1]), encoding="utf-8")
    with pytest.raises(ResearchBenchmarkError, match="cover exactly"):
        score_deepsynth_static(gold_path, predictions_path, system="partial")


def test_adapts_fact_case_without_inventing_provenance_latency_or_review(tmp_path, capsys) -> None:
    result_path = tmp_path / "validated.jsonl"
    result_path.write_text(
        json.dumps(
            {
                "id": 11,
                "prompt": "Which inhibitor is supported?",
                "article": "Nitrite is an inhibitor [1].",
                "citations": [
                    {
                        "fact": "Nitrite is an inhibitor.",
                        "ref_idx": 1,
                        "url": "https://example.edu/inhibitors",
                    }
                ],
                "citations_deduped": {
                    "https://example.edu/inhibitors": {
                        "facts": ["Nitrite is an inhibitor."],
                        "url_content": "Nitrite is an inhibitor in this experiment.",
                        "article_id": 11,
                        "validate_res": [{"idx": 0, "result": "supported"}],
                        "validate_error": None,
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    measurement = {
        "schema_version": BENCHMARK_MEASUREMENT_SCHEMA,
        "system": "claude-3-7-sonnet-latest-official-artifact",
        "case_id": "drb-011",
        "language": "en",
        "started_at": None,
        "finished_at": None,
        "latency_ms": None,
        "latency_scope": None,
        "cost_usd": None,
        "cost_scope": None,
        "minimum_sources": 1,
        "expected_terms": [["nitrite", "亚硝酸盐"]],
        "require_contradiction": False,
    }
    run = build_deepresearch_bench_fact_benchmark_run(
        result_path, case_id="drb-011", measurement=measurement
    )
    score = score_benchmark_run(run)
    assert run["upstream"]["artifact_sha256"]
    assert run["upstream"]["record"]["id"] == 11
    assert run["sources"][0]["receipt_sha256"] is None
    assert run["sources"][0]["provenance_state"].startswith("upstream_artifact")
    assert run["claims"][0]["official_fact_validation"] == "supported"
    assert run["claims"][0]["review_status"] == "pending"
    assert score["metrics"]["provenance_completeness"] == 0.0
    assert score["metrics"]["human_review_rate"] == 0.0
    assert score["metrics"]["latency_state"] == "unknown"

    measurement_path = tmp_path / "measurement.json"
    run_path = tmp_path / "run.json"
    score_path = tmp_path / "score.json"
    measurement_path.write_text(json.dumps(measurement), encoding="utf-8")
    assert (
        main(
            [
                "benchmark",
                "adapt-drb-fact-run",
                str(result_path),
                "drb-011",
                str(measurement_path),
                "--run-output",
                str(run_path),
                "--output",
                str(score_path),
            ]
        )
        == 0
    )
    cli_score = json.loads(capsys.readouterr().out)
    assert cli_score["benchmark_run_sha256"]
    assert json.loads(run_path.read_text(encoding="utf-8")) == run
    assert json.loads(score_path.read_text(encoding="utf-8")) == cli_score


def test_prepares_exact_official_raw_article_contract() -> None:
    cases = {
        "schema_version": "giga.research-benchmark-case-manifest.v1",
        "cases": [
            {
                "case_id": "drb-001",
                "upstream_id": 1,
                "question": "Question one",
            },
            {
                "case_id": "drb-002",
                "upstream_id": 2,
                "question": "Question two",
            },
        ],
    }
    prepared = prepare_deepresearch_bench_submission(
        cases,
        {
            "system": "giga",
            "articles": [
                {"case_id": "drb-002", "article": "Answer two [1]."},
                {"case_id": "drb-001", "article": "Answer one [1]."},
            ],
        },
    )
    assert prepared["records"] == [
        {"id": 1, "prompt": "Question one", "article": "Answer one [1]."},
        {"id": 2, "prompt": "Question two", "article": "Answer two [1]."},
    ]
    with pytest.raises(ResearchBenchmarkError, match="exact imported case set"):
        prepare_deepresearch_bench_submission(
            cases,
            {"system": "giga", "articles": [{"case_id": "drb-001", "article": "Only one"}]},
        )


def _official_manifest() -> dict:
    cases = [
        {
            "case_id": f"drb-{identifier:03d}",
            "upstream_id": identifier,
            "language": "en" if identifier <= 50 else "zh",
            "topic": "science" if identifier % 2 else "finance",
            "question": f"Official question {identifier}",
        }
        for identifier in range(1, 101)
    ]
    return {
        "schema_version": "giga.research-benchmark-case-manifest.v1",
        "upstream_commit": "469cce54ea7f6a63c163d3d9fec879cf289ec484",
        "case_count": 100,
        "cases": cases,
    }


def test_assembles_partial_drb_cohort_with_exact_coverage_and_provenance() -> None:
    manifest = _official_manifest()
    first = {"id": 1, "prompt": "Official question 1", "article": "First answer"}
    second = {"id": 52, "prompt": "Official question 52", "article": "Second answer"}
    assembled = assemble_deepresearch_bench_cohort(
        manifest,
        system="giga-cohort",
        record_sets=[("synthesis-v8", [second]), ("extractive-v1", [first])],
    )
    assert [record["id"] for record in assembled["records"]] == [1, 52]
    assert assembled["case_count"] == 2
    assert assembled["coverage"] == 0.02
    assert assembled["language_coverage"]["en"]["completed"] == 1
    assert assembled["language_coverage"]["zh"]["completed"] == 1
    assert assembled["topic_coverage"]["science"]["completed"] == 1
    assert assembled["topic_coverage"]["finance"]["completed"] == 1
    assert assembled["record_provenance"] == [
        {"id": 1, "case_id": "drb-001", "producer": "extractive-v1"},
        {"id": 52, "case_id": "drb-052", "producer": "synthesis-v8"},
    ]
    assert len(assembled["missing_case_ids"]) == 98
    assert assembled["execution_state"] == "partial_cohort_not_officially_runnable"
    assert assembled == assemble_deepresearch_bench_cohort(
        manifest,
        system="giga-cohort",
        record_sets=[("synthesis-v8", [second]), ("extractive-v1", [first])],
    )


def test_drb_cohort_rejects_duplicate_unknown_and_prompt_drift() -> None:
    manifest = _official_manifest()
    record = {"id": 1, "prompt": "Official question 1", "article": "Answer"}
    with pytest.raises(ResearchBenchmarkError, match="duplicated"):
        assemble_deepresearch_bench_cohort(
            manifest, system="giga", record_sets=[("one", [record]), ("two", [record])]
        )
    with pytest.raises(ResearchBenchmarkError, match="not official"):
        assemble_deepresearch_bench_cohort(
            manifest,
            system="giga",
            record_sets=[("one", [{"id": 101, "prompt": "x", "article": "x"}])],
        )
    with pytest.raises(ResearchBenchmarkError, match="official prompt"):
        assemble_deepresearch_bench_cohort(
            manifest,
            system="giga",
            record_sets=[("one", [{**record, "prompt": "drift"}])],
        )


def test_only_complete_official_drb_cohort_is_evaluator_ready() -> None:
    manifest = _official_manifest()
    records = [
        {"id": item, "prompt": f"Official question {item}", "article": f"Answer {item}"}
        for item in range(1, 101)
    ]
    assembled = assemble_deepresearch_bench_cohort(
        manifest, system="giga", record_sets=[("generator", records)]
    )
    assert assembled["coverage"] == 1.0
    assert assembled["missing_case_ids"] == []
    assert assembled["execution_state"] == "complete_cohort_ready_for_official_evaluator"


def test_drb_cohort_cli_writes_deterministic_official_shape_jsonl(tmp_path, capsys) -> None:
    manifest_path = tmp_path / "cases.json"
    second_path = tmp_path / "second.jsonl"
    first_path = tmp_path / "first.jsonl"
    jsonl_path = tmp_path / "cohort.jsonl"
    receipt_path = tmp_path / "receipt.json"
    manifest_path.write_text(json.dumps(_official_manifest()), encoding="utf-8")
    second_path.write_text(
        json.dumps({"id": 52, "prompt": "Official question 52", "article": "Second"}),
        encoding="utf-8",
    )
    first_path.write_text(
        json.dumps({"id": 1, "prompt": "Official question 1", "article": "First"}),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "benchmark",
                "cohort-drb",
                str(manifest_path),
                "giga-cohort",
                "--record",
                "synthesis",
                str(second_path),
                "--record",
                "extractive",
                str(first_path),
                "--jsonl",
                str(jsonl_path),
                "--output",
                str(receipt_path),
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert [row["id"] for row in rows] == [1, 52]
    assert receipt["coverage"] == 0.02
    assert receipt["execution_state"] == "partial_cohort_not_officially_runnable"
    assert len(receipt["submission_sha256"]) == 64
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt


def test_plans_balanced_resumable_drb_campaign_with_valid_project_proposals() -> None:
    manifest = _official_manifest()
    existing = [
        {"id": 1, "prompt": "Official question 1", "article": "First"},
        {"id": 52, "prompt": "Official question 52", "article": "Second"},
    ]
    campaign = plan_deepresearch_bench_campaign(
        manifest,
        system="giga-campaign",
        record_sets=[("existing", existing)],
        limit=3,
        created_at="2026-08-31T01:00:00+09:00",
    )
    assert campaign["baseline_case_count"] == 2
    assert campaign["remaining_case_count"] == 98
    assert [job["case_id"] for job in campaign["jobs"]] == [
        "drb-002",
        "drb-051",
        "drb-003",
    ]
    assert all(validate_project_plan(job["plan"]) == job["plan"] for job in campaign["jobs"])
    assert all(len(job["plan"]["subquestions"]) == 3 for job in campaign["jobs"])
    assert all(
        job["plan"]["stopping_conditions"]
        == {
            "maximum_depth": 2,
            "maximum_sources": 12,
            "minimum_source_diversity": 4,
            "require_contradiction_search": True,
        }
        for job in campaign["jobs"]
    )
    assert campaign["execution_state"] == "campaign_planned_not_admitted_or_run"
    assert campaign == plan_deepresearch_bench_campaign(
        manifest,
        system="giga-campaign",
        record_sets=[("existing", existing)],
        limit=3,
        created_at="2026-08-31T01:00:00+09:00",
    )


def test_drb_campaign_resume_skips_newly_completed_case() -> None:
    manifest = _official_manifest()
    first = plan_deepresearch_bench_campaign(
        manifest,
        system="giga",
        record_sets=[],
        limit=1,
        created_at="2026-08-31T01:00:00+09:00",
    )
    selected = first["jobs"][0]
    resumed = plan_deepresearch_bench_campaign(
        manifest,
        system="giga",
        record_sets=[
            (
                "completed",
                [
                    {
                        "id": selected["upstream_id"],
                        "prompt": selected["plan"]["question"],
                        "article": "Completed article",
                    }
                ],
            )
        ],
        limit=1,
        created_at="2026-08-31T01:00:00+09:00",
    )
    assert resumed["jobs"][0]["case_id"] != selected["case_id"]
    assert resumed["baseline_case_count"] == 1


def test_drb_campaign_cli_writes_campaign_and_individual_plans(tmp_path, capsys) -> None:
    manifest_path = tmp_path / "cases.json"
    campaign_directory = tmp_path / "campaign"
    receipt_path = tmp_path / "receipt.json"
    manifest_path.write_text(json.dumps(_official_manifest()), encoding="utf-8")
    command = [
        "benchmark",
        "plan-drb-campaign",
        str(manifest_path),
        "giga",
        "--limit",
        "2",
        "--created-at",
        "2026-08-31T01:00:00+09:00",
        "--campaign-directory",
        str(campaign_directory),
        "--output",
        str(receipt_path),
    ]
    assert main(command) == 0
    receipt = json.loads(capsys.readouterr().out)
    campaign = json.loads((campaign_directory / "CAMPAIGN.json").read_text(encoding="utf-8"))
    assert receipt["selected_case_count"] == 2
    assert len(receipt["job_exports"]) == 2
    assert campaign["campaign_id"] == receipt["campaign_id"]
    assert all(Path(row["plan"]).is_file() for row in receipt["job_exports"])
    original = (campaign_directory / "CAMPAIGN.json").read_bytes()
    assert main(command) == 0
    capsys.readouterr()
    changed = list(command)
    changed[changed.index("2026-08-31T01:00:00+09:00")] = "2026-09-01T01:00:00Z"
    assert main(changed) == 2
    assert "refusing to overwrite different research artifact" in capsys.readouterr().err
    assert (campaign_directory / "CAMPAIGN.json").read_bytes() == original
    assert (campaign_directory.stat().st_mode & 0o777) == 0o700
    assert all(
        (Path(row["plan"]).stat().st_mode & 0o777) == 0o600 for row in receipt["job_exports"]
    )


def test_drb_campaign_admission_replaces_per_case_approval_with_exact_zero_spend_envelope(
    tmp_path, capsys
) -> None:
    campaign = plan_deepresearch_bench_campaign(
        _official_manifest(),
        system="giga",
        record_sets=[],
        limit=2,
        created_at="2026-08-31T01:00:00Z",
    )
    campaign_path = tmp_path / "CAMPAIGN.json"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    campaign_sha256 = hashlib.sha256(campaign_path.read_bytes()).hexdigest()
    admission = admit_deepresearch_bench_campaign(
        campaign,
        campaign_plan_sha256=campaign_sha256,
        authorized_by="operator",
        authority_reference="active-goal-public-web-canary",
        authorized_at="2026-08-31T01:05:00Z",
        maximum_network_requests=40,
        maximum_runtime_seconds=3600,
    )
    assert admission["execution_state"] == "admitted_for_zero_spend_public_research"
    assert admission["resource_envelope"] == {
        "maximum_external_cost_usd": 0,
        "maximum_network_requests": 40,
        "maximum_runtime_seconds": 3600,
        "public_unauthenticated_research": True,
        "authenticated_account_actions": False,
        "publication_or_benchmark_submission": False,
    }
    database = tmp_path / "projects.sqlite3"
    receipt_path = tmp_path / "ADMISSION.json"
    command = [
        "benchmark",
        "admit-drb-campaign",
        str(campaign_path),
        campaign_sha256,
        "operator",
        "active-goal-public-web-canary",
        "--authorized-at",
        "2026-08-31T01:05:00Z",
        "--maximum-network-requests",
        "40",
        "--maximum-runtime-seconds",
        "3600",
        "--project-database",
        str(database),
        "--output",
        str(receipt_path),
    ]
    assert main(command) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["admission_id"] == admission["admission_id"]
    assert {job["transition"] for job in receipt["jobs"]} == {"created_and_admitted"}
    assert {job["status"] for job in receipt["jobs"]} == {"ready"}
    store = ResearchProjectStore(database)
    for job in admission["jobs"]:
        state = store.status(job["project_id"])
        assert state["approved"] is True
        assert state["approval_context"]["admission_id"] == admission["admission_id"]
        assert state["approval_context"]["resource_envelope"]["maximum_external_cost_usd"] == 0
    rerun = [value for value in command if value != "--output" and value != str(receipt_path)]
    assert main(rerun) == 0
    resumed = json.loads(capsys.readouterr().out)
    assert {job["transition"] for job in resumed["jobs"]} == {
        "already_approved_exact_plan"
    }
    with pytest.raises(ResearchBenchmarkError, match="network request envelope"):
        admit_deepresearch_bench_campaign(
            campaign,
            campaign_plan_sha256=campaign_sha256,
            authorized_by="operator",
            authority_reference="active-goal-public-web-canary",
            authorized_at="2026-08-31T01:05:00Z",
            maximum_network_requests=1,
            maximum_runtime_seconds=3600,
        )


def test_prepares_one_verified_run_as_official_shape_record(tmp_path, capsys) -> None:
    cases = {
        "schema_version": "giga.research-benchmark-case-manifest.v1",
        "upstream_commit": "469cce54ea7f6a63c163d3d9fec879cf289ec484",
        "cases": [
            {
                "case_id": "drb-059",
                "upstream_id": 59,
                "question": "How do birds navigate?",
            }
        ],
    }
    plan = {
        "project_id": "project-59",
        "question": "How do birds navigate?",
        "subquestions": [
            {
                "id": "Q1",
                "perspective_id": "navigation",
                "question": "Which cues are used?",
            }
        ],
    }
    run = {
        "schema_version": "giga.research-run.v1",
        "run_id": "run-59",
        "project_id": "project-59",
        "acquisitions": [
            {
                "status": "acquired",
                "receipt_sha256": "a" * 64,
                "final_url": "https://nature.com/example",
                "content_sha256": "b" * 64,
            }
        ],
        "retrievals": [
            {
                "subquestion_id": "Q1",
                "result": {
                    "results": [
                        {
                            "receipt_sha256": "a" * 64,
                            "text": "Birds use magnetic cues.",
                        }
                    ]
                },
            }
        ],
    }

    prepared = prepare_deepresearch_bench_run_record(
        cases, case_id="drb-059", plan=plan, run=run, system="giga-extractive"
    )

    assert prepared["record"]["id"] == 59
    assert prepared["record"]["prompt"] == "How do birds navigate?"
    assert "[Source 1](https://nature.com/example)" in prepared["record"]["article"]
    assert len(prepared["article_sha256"]) == 64

    cases_path = tmp_path / "cases.json"
    plan_path = tmp_path / "plan.json"
    run_path = tmp_path / "run.json"
    jsonl_path = tmp_path / "record.jsonl"
    receipt_path = tmp_path / "receipt.json"
    for path, value in ((cases_path, cases), (plan_path, plan), (run_path, run)):
        path.write_text(json.dumps(value), encoding="utf-8")
    assert (
        main(
            [
                "benchmark",
                "prepare-drb-run",
                str(cases_path),
                "drb-059",
                str(plan_path),
                str(run_path),
                "giga-extractive",
                "--jsonl",
                str(jsonl_path),
                "--output",
                str(receipt_path),
            ]
        )
        == 0
    )
    cli_receipt = json.loads(capsys.readouterr().out)
    assert cli_receipt["execution_state"] == "single_raw_article_ready_not_officially_judged"
    assert json.loads(jsonl_path.read_text(encoding="utf-8"))["id"] == 59
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == cli_receipt

    packet = build_synthesis_packet(plan, run)
    proposal = {
        "schema_version": SYNTHESIS_PROPOSAL_SCHEMA,
        "packet_sha256": packet["packet_sha256"],
        "run_id": packet["run_id"],
        "sections": [
            {
                "section_id": packet["outline"][0]["section_id"],
                "heading": packet["outline"][0]["heading"],
                "paragraphs": [{"text": "Birds use magnetic cues.", "evidence_ids": ["E1"]}],
            }
        ],
    }
    synthesis = prepare_deepresearch_bench_synthesis_record(
        cases,
        case_id="drb-059",
        packet=packet,
        proposal=proposal,
        system="giga-synthesis",
    )
    assert synthesis["record"]["id"] == 59
    assert "[E1](https://nature.com/example)" in synthesis["record"]["article"]
