"""Command line interface for the deterministic scientific-review pipeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .passage_retrieval import (
    DEFAULT_DENSE_MODEL,
    PassageRetrievalError,
    fastembed_dense_ranking,
    index_archived_receipts,
    retrieve_passages,
)
from .research_benchmark import (
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
from .research_benchmark import (
    load_json as load_benchmark_json,
)
from .scientific_evidence import ScientificEvidenceError
from .scientific_fulltext import (
    extract_pmc_xml,
    fetch_europe_pmc_xml,
    plan_full_text,
    write_fulltext_plan,
)
from .scientific_query_compiler import (
    compile_manifest,
    embed_compiled_queries,
    load_ontology,
    load_search_spec,
)
from .scientific_readiness import assess_screening_readiness_files
from .scientific_review_state import (
    DEFAULT_REVIEW_DATABASE,
    ScientificReviewStore,
    ingest_screening_snapshot,
)
from .scientific_review_funnel import (
    apply_abstract_enrichments_files,
    build_review_funnel_files,
    write_pubmed_abstracts,
    write_pubmed_abstract_queue,
)
from .scientific_saturation import evaluate_saturation
from .scientific_screening import (
    compile_screening,
    inspect_historical_rds_performance,
    prepare_historical_ris_corpus,
    write_historical_ris_corpus,
    simulate_active_learning,
    validate_exclusion_audit,
    write_screening,
)


from .research_project import (
    DEFAULT_PROJECT_DATABASE,
    ResearchProjectError,
    ResearchProjectStore,
    build_frontier_proposal_request,
    build_research_frontier,
    propose_frontier_extension,
    propose_provider_frontier_extension,
)
from .research_run import (
    DEFAULT_RUN_ROOT,
    execute_parallel_research_runs,
    execute_research_run,
)
from .research_export import (
    CITATION_TRACE_VIEW_RECEIPT_SCHEMA,
    OUTLINE_PROPOSAL_SCHEMA,
    PLAN_MIND_MAP_RECEIPT_SCHEMA,
    ResearchExportError,
    apply_reviewed_outline,
    build_synthesis_packet,
    citation_trace_view_receipt,
    plan_mind_map_receipt,
    render_citation_trace_view,
    render_markdown_report,
    render_plan_mind_map,
    render_synthesis_article,
    report_receipt,
    validate_outline_proposal,
    validate_synthesis_proposal,
)
from .web_acquisition import (
    DEFAULT_ARCHIVE,
    LocalDocumentAcquirer,
    PublicWebAcquirer,
    ScraplingTransport,
    WebAcquisitionError,
    archived_source_json,
)
from .web_discovery import (
    DuckDuckGoSearchProvider,
    OpenAlexSearchProvider,
    WikipediaSearchProvider,
)

def _visual_table_options(args: argparse.Namespace) -> dict[str, Path | str | None]:
    return {
        "visual_table_model": getattr(args, "visual_table_model", None),
        "visual_table_model_sha256": getattr(args, "visual_table_model_sha256", None),
    }


def _run_acquirer(args: argparse.Namespace) -> PublicWebAcquirer:
    return PublicWebAcquirer(
        repository_root=args.repository_root,
        archive_root=args.archive_root,
        transport=ScraplingTransport(args.transport),
        timeout_seconds=args.timeout,
        maximum_bytes=args.maximum_bytes,
        **_visual_table_options(args),
    )


def _run_providers(acquirer: PublicWebAcquirer) -> dict[str, object]:
    return {
        "duckduckgo": DuckDuckGoSearchProvider(acquirer),
        "openalex": OpenAlexSearchProvider(acquirer),
        "wikipedia": WikipediaSearchProvider(acquirer),
    }


def _execute_project_run(
    store: ResearchProjectStore,
    args: argparse.Namespace,
    project_id: str,
    pinned_sources: Mapping[str, list[str]],
    local_sources: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    local_receipts: dict[str, list[Path]] = {}
    if local_sources:
        state = store.export_state(project_id)
        if not state["status"]["approved"]:
            raise ResearchProjectError(
                "project plan requires human approval before local acquisition"
            )
        selected_questions = state["plan"]["subquestions"][: args.maximum_subquestions]
        selected_by_id = {str(row["id"]): row for row in selected_questions}
        for subquestion_id, source_paths in local_sources.items():
            selected = selected_by_id.get(subquestion_id)
            if selected is None:
                raise ResearchProjectError(
                    f"local source references unselected subquestion {subquestion_id!r}"
                )
            if "local_document" not in selected["source_types"]:
                raise ResearchProjectError(
                    f"subquestion {subquestion_id!r} does not permit local_document sources"
                )
            if len(source_paths) > args.sources_per_subquestion:
                raise ResearchProjectError(
                    f"local sources for {subquestion_id} exceed sources_per_subquestion"
                )
        local_acquirer = LocalDocumentAcquirer(
            repository_root=args.repository_root,
            archive_root=args.archive_root,
            maximum_bytes=args.maximum_bytes,
            **_visual_table_options(args),
        )
        for subquestion_id, source_paths in local_sources.items():
            local_receipts[subquestion_id] = [
                local_acquirer.acquire(
                    Path(source_path),
                    archived_at=getattr(args, "local_archived_at", None),
                ).receipt_path
                for source_path in source_paths
            ]
    acquirer = _run_acquirer(args)
    return execute_research_run(
        store,
        project_id,
        acquirer=acquirer,
        providers={} if getattr(args, "local_only", False) else _run_providers(acquirer),
        repository_root=args.repository_root,
        run_root=args.run_root,
        language=args.language,
        maximum_subquestions=args.maximum_subquestions,
        discovery_limit=args.discovery_limit,
        sources_per_subquestion=args.sources_per_subquestion,
        passages_per_subquestion=args.passages_per_subquestion,
        per_domain=args.per_domain,
        pinned_sources=pinned_sources,
        local_receipts=local_receipts,
        local_only=getattr(args, "local_only", False),
    )


def _acquire_local(args: argparse.Namespace) -> dict[str, object]:
    acquirer = LocalDocumentAcquirer(
        repository_root=args.repository_root,
        archive_root=args.archive_root,
        maximum_bytes=args.maximum_bytes,
        **_visual_table_options(args),
    )
    result = archived_source_json(
        acquirer.acquire(args.file, archived_at=args.archived_at)
    )
    if args.output:
        _write_json(args.output.expanduser().resolve(), result)
    return result


def _add_project_run_arguments(
    parser: argparse.ArgumentParser,
    *,
    parallel: bool,
) -> None:
    parser.add_argument("--language", choices=("en", "zh"), default="en")
    parser.add_argument("--maximum-subquestions", type=int, default=1)
    parser.add_argument("--discovery-limit", type=int, default=4)
    parser.add_argument("--sources-per-subquestion", type=int, default=2)
    parser.add_argument("--passages-per-subquestion", type=int, default=4)
    parser.add_argument("--per-domain", type=int, default=1)
    parser.add_argument(
        "--pinned-source",
        action="append",
        nargs=3 if parallel else 2,
        metavar=("PROJECT_ID", "SUBQUESTION_ID", "HTTPS_URL")
        if parallel
        else ("SUBQUESTION_ID", "HTTPS_URL"),
        default=[],
        help=(
            "acquire an approved exact source for one named project and subquestion "
            "before ranked discoveries (repeatable)"
            if parallel
            else "acquire an approved exact source before ranked discoveries (repeatable)"
        ),
    )
    if not parallel:
        parser.add_argument(
            "--local-source",
            action="append",
            nargs=2,
            metavar=("SUBQUESTION_ID", "DOCUMENT"),
            default=[],
            type=str,
            help=(
                "archive and research an operator-selected local document for one "
                "subquestion (repeatable)"
            ),
        )
        parser.add_argument(
            "--local-only",
            action="store_true",
            help="run entirely from --local-source documents without web discovery",
        )
        parser.add_argument(
            "--local-archived-at",
            help="fixed RFC 3339 archive time for reproducible local-source runs",
        )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument(
        "--transport", choices=("static", "dynamic", "stealth"), default="static"
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--maximum-bytes", type=int, default=10 * 1024 * 1024)
    _add_visual_table_arguments(parser)


def _add_visual_table_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--visual-table-model",
        type=Path,
        help=(
            "explicit local RapidTable SLANet-plus ONNX model for scanned-PDF "
            "table candidates; requires --visual-table-model-sha256 and never downloads"
        ),
    )
    parser.add_argument(
        "--visual-table-model-sha256",
        help=(
            "exact SHA-256 for --visual-table-model; required when the model path is set"
        ),
    )


def _project(args: argparse.Namespace) -> dict[str, object]:
    store = ResearchProjectStore(args.project_database)
    if args.project_command == "create":
        return store.create(_json(args.plan))
    if args.project_command == "approve":
        return store.approve(
            args.project_id,
            plan_sha256=args.plan_sha256,
            approved_by=args.approved_by,
            approved_at=args.approved_at,
        )
    if args.project_command == "attach-web-source":
        return store.attach_web_source(args.project_id, args.receipt, args.archive_root)
    if args.project_command == "attach-local-document":
        return store.attach_local_document(
            args.project_id,
            args.receipt,
            args.archive_root,
            recorded_at=args.recorded_at,
        )
    if args.project_command == "add-evidence":
        return store.add_evidence_span(
            args.project_id,
            receipt_sha256=args.receipt_sha256,
            archive_root=args.archive_root,
            quote=args.quote.read_text(encoding="utf-8"),
            locator=args.locator,
            subquestion_ids=args.subquestions,
            recorded_at=args.recorded_at,
        )
    if args.project_command == "propose-claim":
        return store.propose_claim(
            args.project_id,
            claim=args.claim.read_text(encoding="utf-8"),
            evidence_span_ids=args.evidence_spans,
            position=args.position,
            confidence=args.confidence,
            proposed_by=args.proposed_by,
            recorded_at=args.recorded_at,
        )
    if args.project_command == "review-claim":
        return store.review_claim(
            args.project_id,
            claim_id=args.claim_id,
            decision=args.decision,
            reviewed_by=args.reviewed_by,
            notes=args.notes,
            reviewed_at=args.reviewed_at,
        )
    if args.project_command == "propose-claim-relation":
        return store.propose_claim_relation(
            args.project_id,
            source_claim_id=args.source_claim_id,
            target_claim_id=args.target_claim_id,
            relation=args.relation,
            rationale=args.rationale,
            proposed_by=args.proposed_by,
            recorded_at=args.recorded_at,
        )
    if args.project_command == "review-claim-relation":
        return store.review_claim_relation(
            args.project_id,
            relation_id=args.relation_id,
            decision=args.decision,
            reviewed_by=args.reviewed_by,
            notes=args.notes,
            reviewed_at=args.reviewed_at,
        )
    if args.project_command == "matrix":
        return store.evidence_matrix(args.project_id)
    if args.project_command == "citation-graph":
        return store.citation_graph(args.project_id)
    if args.project_command == "plan-map":
        return store.plan_map(args.project_id)
    if args.project_command == "trace-view":
        graph = store.citation_graph(args.project_id)
        document = render_citation_trace_view(graph)
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(document, encoding="utf-8")
        return {
            **citation_trace_view_receipt(graph, document),
            "schema_version": CITATION_TRACE_VIEW_RECEIPT_SCHEMA,
            "output": str(output),
        }
    if args.project_command == "mind-map":
        plan_map = store.plan_map(args.project_id)
        document = render_plan_mind_map(plan_map)
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(document, encoding="utf-8")
        return {
            **plan_mind_map_receipt(plan_map, document),
            "schema_version": PLAN_MIND_MAP_RECEIPT_SCHEMA,
            "output": str(output),
        }
    if args.project_command == "frontier":
        state = store.export_state(args.project_id)
        if not state["status"]["approved"]:
            raise ResearchProjectError("project plan requires human approval before evaluation")
        frontier = build_research_frontier(
            state["plan"],
            [_json(path) for path in args.run],
            evidence_matrix=state["matrix"],
            evaluated_at=args.evaluated_at,
            minimum_evidence_spans=args.minimum_evidence_spans,
            minimum_distinct_domains=args.minimum_distinct_domains,
            maximum_age_days=args.maximum_age_days,
        )
        output = args.output.expanduser().resolve()
        _write_private_json_once(output, frontier)
        return {
            "schema_version": frontier["schema_version"],
            "project_id": args.project_id,
            "frontier_sha256": frontier["frontier_sha256"],
            "synthesis_ready": frontier["synthesis_ready"],
            "next_subquestion_ids": frontier["next_subquestion_ids"],
            "project_gap_types": frontier["project_gap_types"],
            "output": str(output),
            "execution_state": frontier["execution_state"],
            "claim_authority": False,
        }
    if args.project_command == "frontier-request":
        state = store.export_state(args.project_id)
        if not state["status"]["approved"]:
            raise ResearchProjectError(
                "project plan requires human approval before provider request"
            )
        request = build_frontier_proposal_request(
            state["plan"],
            _json(args.frontier),
            requested_at=args.requested_at,
            maximum_followups=args.maximum_followups,
        )
        output = args.output.expanduser().resolve()
        _write_private_json_once(output, request)
        return {
            "schema_version": request["schema_version"],
            "project_id": args.project_id,
            "request_sha256": request["request_sha256"],
            "maximum_followups": request["maximum_followups"],
            "output": str(output),
            "execution_state": "awaiting_provider_response",
            "claim_authority": False,
        }
    if args.project_command == "extend-frontier":
        state = store.export_state(args.project_id)
        if not state["status"]["approved"]:
            raise ResearchProjectError("project plan requires human approval before extension")
        followup_document = _json(args.followups)
        followups = followup_document.get("followups")
        extension = propose_frontier_extension(
            state["plan"],
            _json(args.frontier),
            followups,
            extension_project_id=args.extension_project_id,
            created_at=args.created_at,
        )
        output = args.output.expanduser().resolve()
        plan_output = args.plan_output.expanduser().resolve()
        _write_private_json_once(output, extension)
        _write_private_json_once(plan_output, extension["project_plan"])
        return {
            "schema_version": extension["schema_version"],
            "base_project_id": args.project_id,
            "extension_project_id": args.extension_project_id,
            "extension_sha256": extension["extension_sha256"],
            "project_plan_sha256": extension["project_plan_sha256"],
            "output": str(output),
            "plan_output": str(plan_output),
            "execution_state": extension["execution_state"],
            "approval_required": True,
            "claim_authority": False,
        }
    if args.project_command == "extend-frontier-provider":
        state = store.export_state(args.project_id)
        if not state["status"]["approved"]:
            raise ResearchProjectError(
                "project plan requires human approval before provider extension"
            )
        provider_extension = propose_provider_frontier_extension(
            state["plan"],
            _json(args.frontier),
            _json(args.request),
            _json(args.response),
            extension_project_id=args.extension_project_id,
            created_at=args.created_at,
        )
        output = args.output.expanduser().resolve()
        plan_output = args.plan_output.expanduser().resolve()
        _write_private_json_once(output, provider_extension)
        _write_private_json_once(
            plan_output,
            provider_extension["extension"]["project_plan"],
        )
        proposal = provider_extension["provider_proposal"]
        return {
            "schema_version": provider_extension["schema_version"],
            "base_project_id": args.project_id,
            "extension_project_id": args.extension_project_id,
            "provider_extension_sha256": provider_extension[
                "provider_extension_sha256"
            ],
            "project_plan_sha256": provider_extension["extension"][
                "project_plan_sha256"
            ],
            "provider": proposal["provider"],
            "output": str(output),
            "plan_output": str(plan_output),
            "execution_state": "awaiting_human_approval",
            "approval_required": True,
            "claim_authority": False,
        }
    if args.project_command == "propose-outline":
        packet = _build_project_synthesis_packet(
            store, args, include_reviewed_outline=False
        )
        proposal = validate_outline_proposal(packet, _json(args.proposal))
        result = store.propose_outline(
            args.project_id,
            proposal=proposal,
            proposed_by=args.proposed_by,
            recorded_at=args.recorded_at,
        )
        return {
            **result,
            "schema_version": OUTLINE_PROPOSAL_SCHEMA,
            "packet_sha256": packet["packet_sha256"],
            "run_id": packet["run_id"],
            "claim_authority": False,
        }
    if args.project_command == "review-outline":
        return store.review_outline(
            args.project_id,
            outline_id=args.outline_id,
            decision=args.decision,
            reviewed_by=args.reviewed_by,
            notes=args.notes,
            reviewer_kind=args.reviewer_kind,
            reviewed_at=args.reviewed_at,
        )
    if args.project_command == "synthesis-packet":
        packet = _build_project_synthesis_packet(
            store, args, include_reviewed_outline=True
        )
        _write_json(args.output.expanduser().resolve(), packet)
        return {
            "schema_version": packet["schema_version"],
            "project_id": args.project_id,
            "run_id": packet["run_id"],
            "packet_sha256": packet["packet_sha256"],
            "evidence_count": len(packet["evidence"]),
            "component_count": len(packet["component_runs"]),
            "outline_review_state": packet["outline_review"]["state"],
            "output": str(args.output.expanduser().resolve()),
            "execution_state": "synthesis_packet_ready_for_external_model",
            "claim_authority": False,
        }
    if args.project_command == "render-synthesis":
        packet = _build_project_synthesis_packet(
            store, args, include_reviewed_outline=True
        )
        proposal = _json(args.proposal)
        validated = validate_synthesis_proposal(packet, proposal)
        article = render_synthesis_article(packet, proposal)
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(article, encoding="utf-8")
        if args.validation:
            _write_json(args.validation.expanduser().resolve(), validated)
        return {
            "schema_version": "giga.research-synthesis-article-receipt.v1",
            "project_id": args.project_id,
            "run_id": packet["run_id"],
            "packet_sha256": packet["packet_sha256"],
            "article_sha256": hashlib.sha256(article.encode("utf-8")).hexdigest(),
            "paragraph_count": validated["validation"]["paragraph_count"],
            "citation_coverage": validated["validation"]["citation_coverage"],
            "mean_lexical_support": validated["validation"]["mean_lexical_support"],
            "outline_review_state": packet["outline_review"]["state"],
            "output": str(output),
            "execution_state": "grounded_synthesis_proposal_not_human_reviewed",
            "claim_authority": False,
        }
    if args.project_command == "report":
        state = store.export_state(args.project_id)
        report = render_markdown_report(state["plan"], state["status"], state["matrix"])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        return {**report_receipt(report), "output": str(args.output.resolve())}
    if args.project_command == "run":
        pinned_sources: dict[str, list[str]] = {}
        for subquestion_id, source_url in args.pinned_source:
            pinned_sources.setdefault(subquestion_id, []).append(source_url)
        local_sources: dict[str, list[str]] = {}
        for subquestion_id, source_path in args.local_source:
            local_sources.setdefault(subquestion_id, []).append(source_path)
        return _execute_project_run(
            store,
            args,
            args.project_id,
            pinned_sources,
            local_sources,
        )
    if args.project_command == "run-parallel":
        project_pins: dict[str, dict[str, list[str]]] = {}
        known = set(args.project_ids)
        for project_id, subquestion_id, source_url in args.pinned_source:
            if project_id not in known:
                raise ResearchProjectError(
                    f"parallel pinned source references unknown project {project_id!r}"
                )
            project_pins.setdefault(project_id, {}).setdefault(
                subquestion_id, []
            ).append(source_url)
        batch = execute_parallel_research_runs(
            store,
            args.project_ids,
            runner=lambda project_id: _execute_project_run(
                store,
                args,
                project_id,
                project_pins.get(project_id, {}),
            ),
            configuration=_run_configuration(args, project_pins),
            maximum_workers=args.maximum_workers,
        )
        output = args.output.expanduser().resolve()
        _write_private_json_once(output, batch)
        if batch["failed_projects"]:
            raise ResearchProjectError(
                f"parallel research batch preserved {batch['failed_projects']} failure(s) at {output}"
            )
        return {
            "schema_version": batch["schema_version"],
            "batch_id": batch["batch_id"],
            "batch_sha256": batch["batch_sha256"],
            "completed_projects": batch["completed_projects"],
            "failed_projects": 0,
            "output": str(output),
            "execution_state": batch["execution_state"],
            "claim_authority": False,
        }
    return store.status(args.project_id)


def _run_configuration(
    args: argparse.Namespace,
    pinned_sources: Mapping[str, Mapping[str, list[str]]],
) -> dict[str, Any]:
    return {
        "language": args.language,
        "maximum_subquestions": args.maximum_subquestions,
        "discovery_limit": args.discovery_limit,
        "sources_per_subquestion": args.sources_per_subquestion,
        "passages_per_subquestion": args.passages_per_subquestion,
        "per_domain": args.per_domain,
        "transport": args.transport,
        "timeout": args.timeout,
        "maximum_bytes": args.maximum_bytes,
        "repository_root": str(args.repository_root.expanduser().resolve()),
        "archive_root": str(args.archive_root.expanduser().resolve()),
        "run_root": str(args.run_root.expanduser().resolve()),
        "visual_table": {
            "enabled": bool(getattr(args, "visual_table_model", None)),
            "model_sha256": getattr(args, "visual_table_model_sha256", None),
        },
        "pinned_sources": {
            project_id: dict(sorted(question_pins.items()))
            for project_id, question_pins in sorted(pinned_sources.items())
        },
    }

def _build_project_synthesis_packet(
    store: ResearchProjectStore,
    args: argparse.Namespace,
    *,
    include_reviewed_outline: bool,
) -> dict[str, Any]:
    state = store.export_state(args.project_id)
    supplements = [
        (store.export_state(project_id)["plan"], _json(Path(run_path)))
        for project_id, run_path in args.supplement
    ]
    packet = build_synthesis_packet(
        state["plan"], _json(args.run), supplements=supplements
    )
    if not include_reviewed_outline:
        return packet
    reviewed = store.accepted_outline(
        args.project_id, packet_sha256=packet["packet_sha256"]
    )
    return apply_reviewed_outline(packet, reviewed) if reviewed else packet

def _write_private_json_once(path: Path, value: Any) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise ResearchProjectError(f"research artifact path is not a regular file: {path}")
        if path.read_bytes() != payload:
            raise ResearchProjectError(
                f"refusing to overwrite different research artifact: {path}"
            )
        os.chmod(path, 0o600)
        return
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise ResearchProjectError(f"research artifact appeared concurrently: {path}") from exc
    os.chmod(path, 0o600)

def _retrieve_passages(args: argparse.Namespace) -> dict[str, Any]:
    dense = _json(args.dense_ranking).get("passage_ids") if args.dense_ranking else None
    metadata_scope = _json(args.metadata_scope) if args.metadata_scope else None
    if dense is not None and (
        not isinstance(dense, list) or not all(isinstance(item, str) for item in dense)
    ):
        raise PassageRetrievalError("dense ranking passage_ids must be an array of strings")
    passages = index_archived_receipts(
        args.archive_root,
        args.receipts,
        maximum_characters=args.maximum_characters,
        overlap_characters=args.overlap_characters,
    )
    dense_provider = None
    if args.dense:
        dense_provider = fastembed_dense_ranking(
            args.query,
            passages,
            model_name=args.dense_model,
            cache_root=args.dense_cache_root,
            batch_size=args.dense_batch_size,
            threads=args.dense_threads,
        )
        dense = dense_provider["passage_ids"]
    if dense is None and args.dense_weight != 1.0:
        raise PassageRetrievalError("--dense-weight requires a dense ranking")
    ranker_weights = {"bm25": args.bm25_weight}
    if dense is not None:
        ranker_weights["dense"] = args.dense_weight
    result = retrieve_passages(
        args.query,
        passages,
        dense_ranking=dense,
        metadata_scope=metadata_scope,
        ranker_weights=ranker_weights,
        rank_constant=args.rank_constant,
        limit=args.limit,
        per_source=args.per_source,
    )
    if dense_provider is not None:
        result["dense_provider"] = dense_provider
    if args.output:
        _write_json(args.output.expanduser().resolve(), result)
    return result

def _benchmark(args: argparse.Namespace) -> dict[str, Any]:
    if args.benchmark_command == "score":
        result = score_benchmark_run(load_benchmark_json(args.run))
    elif args.benchmark_command == "score-synthesis":
        run = build_synthesis_benchmark_run(
            load_benchmark_json(args.packet),
            load_benchmark_json(args.proposal),
            load_benchmark_json(args.measurement),
        )
        run_output = args.run_output.expanduser().resolve()
        _write_json(run_output, run)
        result = {
            **score_benchmark_run(run),
            "benchmark_run": str(run_output),
            "benchmark_run_sha256": hashlib.sha256(run_output.read_bytes()).hexdigest(),
        }
    elif args.benchmark_command == "score-extractive":
        run = build_extractive_benchmark_run(
            load_benchmark_json(args.plan),
            load_benchmark_json(args.run),
            load_benchmark_json(args.measurement),
        )
        run_output = args.run_output.expanduser().resolve()
        _write_json(run_output, run)
        result = {
            **score_benchmark_run(run),
            "benchmark_run": str(run_output),
            "benchmark_run_sha256": hashlib.sha256(run_output.read_bytes()).hexdigest(),
        }
    elif args.benchmark_command == "score-retrieval":
        result = score_retrieval_ablation(
            load_benchmark_json(args.specification),
            load_benchmark_json(args.bm25),
            load_benchmark_json(args.hybrid),
        )
    elif args.benchmark_command == "score-retrieval-cohort":
        result = score_retrieval_cohort(
            load_benchmark_json(args.manifest),
            [load_benchmark_json(path) for path in args.scores],
        )
    elif args.benchmark_command == "import-drb":
        result = import_deepresearch_bench_cases(args.query_jsonl)
    elif args.benchmark_command == "import-drb-race":
        result = import_deepresearch_bench_race_results(args.result_jsonl)
    elif args.benchmark_command == "import-drb-fact":
        result = import_deepresearch_bench_fact_results(args.result_jsonl)
    elif args.benchmark_command == "import-drb-competitor-cohort":
        result = import_deepresearch_bench_competitor_cohort(
            args.race_jsonl,
            args.fact_jsonl,
            system=args.system,
            case_ids=args.case_ids,
        )
    elif args.benchmark_command == "import-reportbench":
        result = import_reportbench_cases(args.case_jsonl)
    elif args.benchmark_command == "import-reportbench-results":
        result = import_reportbench_results(
            args.case_jsonl,
            args.related_work_csv,
            args.statement_metrics_csv,
            system=args.system,
        )
    elif args.benchmark_command == "import-pdrbench":
        result = import_pdrbench_cases(args.case_jsonl)
    elif args.benchmark_command == "import-pdrbench-results":
        result = import_pdrbench_results(
            args.case_jsonl,
            args.personalization_jsonl,
            args.quality_jsonl,
            args.reliability_jsonl,
            system=args.system,
        )
    elif args.benchmark_command == "score-deepsynth":
        result = score_deepsynth_static(
            args.gold_json,
            args.predictions_json,
            system=args.system,
        )
    elif args.benchmark_command == "adapt-drb-fact-run":
        run = build_deepresearch_bench_fact_benchmark_run(
            args.result_jsonl,
            case_id=args.case_id,
            measurement=load_benchmark_json(args.measurement),
        )
        run_output = args.run_output.expanduser().resolve()
        _write_json(run_output, run)
        result = {
            **score_benchmark_run(run),
            "benchmark_run": str(run_output),
            "benchmark_run_sha256": hashlib.sha256(run_output.read_bytes()).hexdigest(),
        }
    elif args.benchmark_command == "prepare-drb":
        prepared = prepare_deepresearch_bench_submission(
            load_benchmark_json(args.cases), load_benchmark_json(args.articles)
        )
        submission = args.jsonl.expanduser().resolve()
        _write_jsonl(submission, prepared["records"])
        result = {
            **{key: value for key, value in prepared.items() if key != "records"},
            "submission_jsonl": str(submission),
            "submission_sha256": hashlib.sha256(submission.read_bytes()).hexdigest(),
        }
    elif args.benchmark_command == "prepare-drb-run":
        prepared = prepare_deepresearch_bench_run_record(
            load_benchmark_json(args.cases),
            case_id=args.case_id,
            plan=load_benchmark_json(args.plan),
            run=load_benchmark_json(args.run),
            system=args.system,
        )
        submission = args.jsonl.expanduser().resolve()
        _write_jsonl(submission, [prepared["record"]])
        result = {
            **{key: value for key, value in prepared.items() if key != "record"},
            "submission_jsonl": str(submission),
            "submission_sha256": hashlib.sha256(submission.read_bytes()).hexdigest(),
        }
    elif args.benchmark_command == "prepare-drb-synthesis":
        prepared = prepare_deepresearch_bench_synthesis_record(
            load_benchmark_json(args.cases),
            case_id=args.case_id,
            packet=load_benchmark_json(args.packet),
            proposal=load_benchmark_json(args.proposal),
            system=args.system,
        )
        submission = args.jsonl.expanduser().resolve()
        _write_jsonl(submission, [prepared["record"]])
        result = {
            **{key: value for key, value in prepared.items() if key != "record"},
            "submission_jsonl": str(submission),
            "submission_sha256": hashlib.sha256(submission.read_bytes()).hexdigest(),
        }
    elif args.benchmark_command == "cohort-drb":
        prepared = assemble_deepresearch_bench_cohort(
            load_benchmark_json(args.cases),
            system=args.system,
            record_sets=_benchmark_record_sets(args.record),
        )
        submission = args.jsonl.expanduser().resolve()
        _write_jsonl(submission, prepared["records"])
        result = {
            **{key: value for key, value in prepared.items() if key != "records"},
            "submission_jsonl": str(submission),
            "submission_sha256": hashlib.sha256(submission.read_bytes()).hexdigest(),
        }
    elif args.benchmark_command == "plan-drb-campaign":
        planned = plan_deepresearch_bench_campaign(
            load_benchmark_json(args.cases),
            system=args.system,
            record_sets=_benchmark_record_sets(args.record),
            limit=args.limit,
            created_at=args.created_at,
        )
        campaign_directory = args.campaign_directory.expanduser().resolve()
        job_exports = []
        for job in planned["jobs"]:
            plan_path = campaign_directory / str(job["case_id"]) / "PLAN.json"
            _write_private_json_once(plan_path, job["plan"])
            job_exports.append(
                {
                    "case_id": job["case_id"],
                    "plan": str(plan_path),
                    "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                    "execution_state": job["execution_state"],
                }
            )
        campaign_path = campaign_directory / "CAMPAIGN.json"
        _write_private_json_once(campaign_path, planned)
        result = {
            **{key: value for key, value in planned.items() if key != "jobs"},
            "campaign_plan": str(campaign_path),
            "campaign_plan_sha256": hashlib.sha256(campaign_path.read_bytes()).hexdigest(),
            "job_exports": job_exports,
        }
    elif args.benchmark_command == "admit-drb-campaign":
        campaign_path = args.campaign.expanduser().resolve()
        campaign_bytes = campaign_path.read_bytes()
        actual_campaign_sha256 = hashlib.sha256(campaign_bytes).hexdigest()
        if actual_campaign_sha256 != args.campaign_plan_sha256:
            raise ResearchBenchmarkError(
                "campaign_plan_sha256 differs from the exact campaign artifact"
            )
        admission = admit_deepresearch_bench_campaign(
            load_benchmark_json(campaign_path),
            campaign_plan_sha256=actual_campaign_sha256,
            authorized_by=args.authorized_by,
            authority_reference=args.authority_reference,
            authorized_at=args.authorized_at,
            maximum_network_requests=args.maximum_network_requests,
            maximum_runtime_seconds=args.maximum_runtime_seconds,
        )
        store = ResearchProjectStore(args.project_database)
        preflight: dict[str, Mapping[str, Any] | None] = {}
        for job in admission["jobs"]:
            project_id = str(job["project_id"])
            try:
                state = store.status(project_id)
            except ResearchProjectError as exc:
                if str(exc) != "unknown project_id":
                    raise
                state = None
            if state is not None and state["plan_sha256"] != job["plan_sha256"]:
                raise ResearchBenchmarkError(
                    f"existing project {project_id} differs from the admitted campaign plan"
                )
            preflight[project_id] = state
        approval_context = {
            key: admission[key]
            for key in (
                "schema_version",
                "admission_id",
                "admission_sha256",
                "campaign_id",
                "campaign_plan_sha256",
                "authority_reference",
                "resource_envelope",
            )
        }
        admitted_jobs = []
        for job in admission["jobs"]:
            project_id = str(job["project_id"])
            state = preflight[project_id]
            if state is None:
                created = store.create(job["plan"])
                state = store.status(project_id)
                transition = "created_and_admitted"
            else:
                created = None
                transition = "existing_plan_admitted"
            approved = None
            if not state["approved"]:
                approved = store.approve(
                    project_id,
                    plan_sha256=str(job["plan_sha256"]),
                    approved_by=args.authorized_by,
                    approved_at=args.authorized_at,
                    approval_context=approval_context,
                )
            else:
                transition = "already_approved_exact_plan"
            final_state = store.status(project_id)
            admitted_jobs.append(
                {
                    "case_id": job["case_id"],
                    "project_id": project_id,
                    "plan_sha256": job["plan_sha256"],
                    "transition": transition,
                    "create_event_sha256": created["event_sha256"] if created else None,
                    "approval_event_sha256": approved["event_sha256"] if approved else None,
                    "status": final_state["status"],
                }
            )
        result = {
            **{key: value for key, value in admission.items() if key != "jobs"},
            "project_database": str(store.database.resolve()),
            "jobs": admitted_jobs,
        }
    else:
        result = compare_scores(
            [load_benchmark_json(path) for path in args.scores],
            system_aliases=dict(args.system_alias),
        )
    if args.output:
        output = args.output.expanduser().resolve()
        if args.benchmark_command in {"plan-drb-campaign", "admit-drb-campaign"}:
            _write_private_json_once(output, result)
        else:
            _write_json(output, result)
    return result


def _benchmark_record_sets(
    values: list[list[str]],
) -> list[tuple[str, list[Mapping[str, Any]]]]:
    record_sets = []
    for producer, path_text in values:
        path = Path(path_text).expanduser().resolve()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            rows = [json.loads(line) for line in lines]
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchBenchmarkError(f"cannot read cohort JSONL from {path}") from exc
        if not all(isinstance(row, Mapping) for row in rows):
            raise ResearchBenchmarkError(f"cohort JSONL from {path} must contain objects")
        record_sets.append((producer, rows))
    return record_sets


def _write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )

DEFAULT_PROVIDERS = ("europe_pmc", "pubmed")


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScientificEvidenceError(f"cannot read JSON object from {path}") from exc
    if not isinstance(value, dict):
        raise ScientificEvidenceError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _negative_control_campaign(
    campaign: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    controls = [
        query for query in manifest["queries"] if query["negative_control"]
    ]
    return {
        "schema_version": "giga.scientific-search-campaign.v1",
        "campaign_id": f"{campaign['campaign_id']}-negative-controls",
        "protocol": campaign["protocol"],
        "created_at": campaign["created_at"],
        "execution_state": "compiled_negative_controls_not_executed",
        "defaults": {
            "endpoint": "search/papers",
            "corpus": "pubmed",
            "search_mode": "semantic",
            "max_results": 10,
            "filters": {"retracted": "exclude_retracted"},
        },
        "queries": [
            {
                "id": control["id"],
                "phase": 99,
                "question": control["human_question"],
                "provider_queries": {
                    provider: expression
                    for provider, expression in control["provider_queries"].items()
                    if provider != "clinical_trials"
                },
            }
            for control in controls
        ],
        "completion_rule": (
            "Every retrieved negative-control record must be proposed for exclusion; "
            "any failure blocks search promotion."
        ),
    }


def _simulate_active_learning(args: argparse.Namespace) -> dict[str, Any]:
    try:
        rows = [
            json.loads(line)
            for line in args.groups.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, json.JSONDecodeError) as exc:
        raise ScientificEvidenceError(
            f"cannot read active-learning group JSONL from {args.groups}"
        ) from exc
    if not all(isinstance(row, Mapping) for row in rows):
        raise ScientificEvidenceError(
            "active-learning group JSONL must contain only JSON objects"
        )
    result = simulate_active_learning(
        rows,
        _json(args.oracle),
        seed_group_ids=args.seed_group_id,
        maximum_labels=args.maximum_labels,
        target_recall=args.target_recall,
    )
    _write_json(args.output.expanduser().resolve(), result)
    return result


def _prepare_historical_ris(args: argparse.Namespace) -> dict[str, Any]:
    corpus = prepare_historical_ris_corpus(
        args.included_ris.expanduser().resolve(),
        args.excluded_ris.expanduser().resolve(),
        simulation_id=args.simulation_id,
        source_id=args.source_id,
    )
    return write_historical_ris_corpus(corpus, args.output.expanduser().resolve())


def _inspect_historical_rds_performance(args: argparse.Namespace) -> dict[str, Any]:
    result = inspect_historical_rds_performance(
        args.rds.expanduser().resolve(),
        expected_review=args.expected_review,
        expected_review_authors=args.expected_review_authors,
    )
    _write_json(args.output.expanduser().resolve(), result)
    return result


def _compile_search(args: argparse.Namespace) -> dict[str, Any]:
    campaign = _json(args.campaign)
    ontology = load_ontology(args.ontology)
    specification = load_search_spec(args.specification, ontology=ontology)
    manifest = compile_manifest(
        campaign,
        ontology,
        specification,
        providers=args.provider or DEFAULT_PROVIDERS,
    )
    compiled_campaign = embed_compiled_queries(campaign, manifest)
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "COMPILED_SEARCH_MANIFEST.json", manifest)
    _write_json(output / "COMPILED_CAMPAIGN.json", compiled_campaign)
    _write_json(
        output / "NEGATIVE_CONTROL_CAMPAIGN.json",
        _negative_control_campaign(campaign, manifest),
    )
    return {
        "mode": "compile_search",
        "campaign_id": campaign["campaign_id"],
        "compiled_queries": sum(
            not item["negative_control"] for item in manifest["queries"]
        ),
        "negative_controls": sum(
            item["negative_control"] for item in manifest["queries"]
        ),
        "providers": manifest["providers"],
        "manifest_sha256": manifest["manifest_sha256"],
        "output": str(output),
        "api_calls_made": 0,
        "scientific_conclusion_authority": False,
    }


def _screen(args: argparse.Namespace) -> dict[str, Any]:
    campaign = _json(args.campaign)
    manifest = _json(args.manifest)
    ontology = load_ontology(args.ontology)
    specification = load_search_spec(args.specification, ontology=ontology)
    duplicate_document = (
        _json(args.duplicate_decisions) if args.duplicate_decisions else None
    )
    build = compile_screening(
        args.database.expanduser().resolve(),
        campaign,
        manifest,
        ontology,
        specification,
        duplicate_document,
    )
    output = args.output.expanduser().resolve()
    summary = write_screening(build, output)
    fulltext = plan_full_text(build.groups, build.proposals)
    fulltext_artifact = write_fulltext_plan(
        fulltext,
        output / "FULLTEXT_PLAN.jsonl",
    )
    summary["artifacts"]["fulltext_plan"] = fulltext_artifact
    summary["full_text_plans"] = len(fulltext)
    _write_json(output / "SCREENING_SUMMARY.json", summary)
    state_result = None
    if not args.no_state_ledger:
        store = ScientificReviewStore(args.review_database)
        if duplicate_document:
            for decision in duplicate_document["decisions"]:
                store.record_duplicate_decision(
                    campaign_id=campaign["campaign_id"],
                    pair_sha256=decision["pair_sha256"],
                    decision=decision["decision"],
                    decided_by=decision["decided_by"],
                    evidence=decision["evidence"],
                    decided_at=decision["decided_at"],
                )
        state_result = ingest_screening_snapshot(
            store,
            campaign_id=campaign["campaign_id"],
            groups=build.groups,
            proposals=build.proposals,
            snapshot_sha256=summary["snapshot_payload_sha256"],
            recorded_at=args.recorded_at or campaign["created_at"],
        )
    return {
        "mode": "screen",
        **summary,
        "state_ledger": state_result,
        "api_calls_made": 0,
    }


def _fetch_pmc(args: argparse.Namespace) -> dict[str, Any]:
    receipt = fetch_europe_pmc_xml(
        args.pmcid,
        args.destination,
        timeout=args.timeout,
    )
    if args.receipt:
        _write_json(args.receipt, receipt)
    return receipt


def _extract_pmc(args: argparse.Namespace) -> dict[str, Any]:
    extraction = extract_pmc_xml(args.xml)
    if args.output:
        _write_json(args.output, extraction)
    return extraction


def _validate_exclusion_audit(args: argparse.Namespace) -> dict[str, Any]:
    summary = _json(args.screening_summary)
    artifact = summary.get("artifacts", {}).get("exclusion_audit")
    if not isinstance(artifact, dict):
        raise ScientificEvidenceError(
            "screening summary has no exclusion_audit artifact"
        )
    expected_path = (
        args.screening_summary.expanduser().resolve().parent / artifact["path"]
    )
    if hashlib.sha256(expected_path.read_bytes()).hexdigest() != artifact["sha256"]:
        raise ScientificEvidenceError(
            "deterministic exclusion-audit sample hash mismatch"
        )
    with expected_path.open(encoding="utf-8", newline="") as handle:
        expected = list(csv.DictReader(handle))
    report = validate_exclusion_audit(
        args.completed_audit,
        expected,
        maximum_false_exclusion_rate=args.maximum_false_exclusion_rate,
    )
    if args.output:
        _write_json(args.output, report)
    return report


def _saturation(args: argparse.Namespace) -> dict[str, Any]:
    report = evaluate_saturation(
        args.screening_summary,
        maximum_new_candidate_rate=args.maximum_new_candidate_rate,
    )
    if args.output:
        _write_json(args.output, report)
    return report


def _readiness(args: argparse.Namespace) -> dict[str, Any]:
    report = assess_screening_readiness_files(
        main_summary=args.main_summary,
        negative_control_summary=args.negative_control_summary,
        review_database=args.review_database,
        exclusion_audit_report=args.exclusion_audit_report,
        saturation_report=args.saturation_report,
    )
    if args.output:
        _write_json(args.output, report)
    return report


def _review_funnel(args: argparse.Namespace) -> dict[str, Any]:
    return build_review_funnel_files(
        groups=args.groups,
        proposals=args.proposals,
        features=args.features,
        output=args.output,
        eligibility_decisions=args.eligibility_decisions,
        extractions=args.extractions,
        duplicate_decision_report=args.duplicate_decision_report,
        synthesis_signoff=args.synthesis_signoff,
    )


def _fetch_abstracts(args: argparse.Namespace) -> dict[str, Any]:
    identifiers: list[str] = []
    for value in args.pmid:
        identifiers.extend(part.strip() for part in value.split(",") if part.strip())
    return write_pubmed_abstracts(
        identifiers,
        args.destination,
        timeout=args.timeout,
    )


def _merge_abstracts(args: argparse.Namespace) -> dict[str, Any]:
    return apply_abstract_enrichments_files(
        groups=args.groups,
        retrievals=args.retrievals,
        ontology=args.ontology,
        specification=args.specification,
        output=args.output,
    )


def _fetch_abstract_queue(args: argparse.Namespace) -> dict[str, Any]:
    return write_pubmed_abstract_queue(
        args.queue,
        args.destination,
        timeout=args.timeout,
    )


def _state(args: argparse.Namespace) -> dict[str, Any]:
    store = ScientificReviewStore(args.review_database)
    if args.state_command == "audit":
        return store.audit()
    if args.state_command == "status":
        return store.counts(args.campaign_id)
    if args.state_command == "decide":
        current = store.current_states(args.campaign_id).get(args.group_id)
        if current not in {
            "awaiting_review",
            "proposed_include",
            "proposed_exclude",
        }:
            raise ScientificEvidenceError(
                "human eligibility decisions require an awaiting/proposed state"
            )
        evidence = _json(args.evidence)
        event_id, created = store.transition(
            campaign_id=args.campaign_id,
            group_id=args.group_id,
            from_state=current,
            to_state="included" if args.decision == "include" else "excluded",
            actor_kind="human",
            reason_codes=[args.reason_code],
            evidence=evidence,
            recorded_at=args.recorded_at,
        )
        return {
            "event_id": event_id,
            "created": created,
            "from_state": current,
            "to_state": "included"
            if args.decision == "include"
            else "excluded",
            "authority": "eligibility_only_not_scientific_conclusion",
        }
    if args.state_command == "llm-proposal":
        proposal = _json(args.proposal)
        metadata = _json(args.source_metadata)
        proposal_id, created = store.record_llm_proposal(
            proposal,
            source_metadata=metadata,
        )
        return {
            "proposal_id": proposal_id,
            "created": created,
            "state_changed": False,
            "human_confirmation_required": True,
        }
    if args.state_command == "fulltext-plan":
        evidence = _json(args.evidence)
        event_id, created = store.transition(
            campaign_id=args.campaign_id,
            group_id=args.group_id,
            from_state="included",
            to_state="fulltext_planned",
            actor_kind="system",
            reason_codes=["FULLTEXT_ROUTE_SELECTED"],
            evidence=evidence,
            recorded_at=args.recorded_at,
        )
        return {
            "event_id": event_id,
            "created": created,
            "to_state": "fulltext_planned",
        }
    if args.state_command == "fulltext-result":
        evidence = _json(args.evidence)
        target = (
            "fulltext_obtained"
            if args.result == "obtained"
            else "fulltext_unavailable"
        )
        event_id, created = store.transition(
            campaign_id=args.campaign_id,
            group_id=args.group_id,
            from_state="fulltext_planned",
            to_state=target,
            actor_kind="system",
            reason_codes=[
                "FULLTEXT_OBTAINED_LAWFULLY"
                if args.result == "obtained"
                else "FULLTEXT_UNAVAILABLE_AFTER_LAWFUL_ROUTES"
            ],
            evidence=evidence,
            recorded_at=args.recorded_at,
        )
        return {"event_id": event_id, "created": created, "to_state": target}
    if args.state_command == "appraised":
        evidence = _json(args.evidence)
        event_id, created = store.transition(
            campaign_id=args.campaign_id,
            group_id=args.group_id,
            from_state="fulltext_obtained",
            to_state="appraised",
            actor_kind="human",
            reason_codes=["HUMAN_FULLTEXT_APPRAISAL_RECORDED"],
            evidence=evidence,
            recorded_at=args.recorded_at,
        )
        return {
            "event_id": event_id,
            "created": created,
            "to_state": "appraised",
            "scientific_conclusion_authority": False,
        }
    if args.state_command == "duplicate-decision":
        evidence = _json(args.evidence)
        decision_id, created = store.record_duplicate_decision(
            campaign_id=args.campaign_id,
            pair_sha256=args.pair_sha256,
            decision=args.decision,
            decided_by=args.decided_by,
            evidence=evidence,
            decided_at=args.decided_at,
        )
        return {
            "decision_id": decision_id,
            "created": created,
            "decision": args.decision,
            "screening_snapshot_recompile_required": True,
        }
    raise ScientificEvidenceError("unknown state command")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser(
        "compile-search",
        help="compile human questions into provider-specific queries without network",
    )
    compile_parser.add_argument("campaign", type=Path)
    compile_parser.add_argument("ontology", type=Path)
    compile_parser.add_argument("specification", type=Path)
    compile_parser.add_argument("output", type=Path)
    compile_parser.add_argument(
        "--provider",
        action="append",
        choices=[
            "clinical_trials",
            "europe_pmc",
            "openalex",
            "pubmed",
            "semantic_scholar",
        ],
    )

    screen = subparsers.add_parser(
        "screen",
        help="normalise, deduplicate, triage and queue an acquisition ledger",
    )
    screen.add_argument("database", type=Path)
    screen.add_argument("campaign", type=Path)
    screen.add_argument("manifest", type=Path)
    screen.add_argument("ontology", type=Path)
    screen.add_argument("specification", type=Path)
    screen.add_argument("output", type=Path)
    screen.add_argument(
        "--review-database",
        type=Path,
        default=DEFAULT_REVIEW_DATABASE,
    )
    screen.add_argument("--recorded-at")
    screen.add_argument("--no-state-ledger", action="store_true")
    screen.add_argument("--duplicate-decisions", type=Path)

    fetch = subparsers.add_parser(
        "fetch-pmc",
        help="explicitly fetch one full-text XML file from official Europe PMC",
    )
    fetch.add_argument("pmcid")
    fetch.add_argument("destination", type=Path)
    fetch.add_argument("--receipt", type=Path)
    fetch.add_argument("--timeout", type=int, default=60)

    extract = subparsers.add_parser(
        "extract-pmc",
        help="deterministically extract source-located text from PMC XML",
    )
    extract.add_argument("xml", type=Path)
    extract.add_argument("--output", type=Path)

    audit_exclusions = subparsers.add_parser(
        "validate-exclusion-audit",
        help="validate a human-completed copy of the deterministic exclusion sample",
    )
    audit_exclusions.add_argument("screening_summary", type=Path)
    audit_exclusions.add_argument("completed_audit", type=Path)
    audit_exclusions.add_argument(
        "--maximum-false-exclusion-rate",
        type=float,
        default=0.0,
    )
    audit_exclusions.add_argument("--output", type=Path)

    saturation = subparsers.add_parser(
        "saturation",
        help="evaluate two consecutive search amendments across three snapshots",
    )
    saturation.add_argument(
        "screening_summary",
        type=Path,
        nargs="+",
    )
    saturation.add_argument(
        "--maximum-new-candidate-rate",
        type=float,
        default=0.01,
    )
    saturation.add_argument("--output", type=Path)

    readiness = subparsers.add_parser(
        "readiness",
        help="evaluate fail-closed deterministic screening promotion gates",
    )
    readiness.add_argument("main_summary", type=Path)
    readiness.add_argument("negative_control_summary", type=Path)
    readiness.add_argument(
        "--review-database",
        type=Path,
        default=DEFAULT_REVIEW_DATABASE,
    )
    readiness.add_argument("--exclusion-audit-report", type=Path)
    readiness.add_argument("--saturation-report", type=Path)
    readiness.add_argument("--output", type=Path)

    funnel = subparsers.add_parser(
        "review-funnel",
        help=(
            "build metadata, abstract, priority, full-text, grouping and synthesis "
            "review artifacts without LLM calls"
        ),
    )
    funnel.add_argument("groups", type=Path)
    funnel.add_argument("proposals", type=Path)
    funnel.add_argument("features", type=Path)
    funnel.add_argument("output", type=Path)
    funnel.add_argument("--eligibility-decisions", type=Path)
    funnel.add_argument("--extractions", type=Path)
    funnel.add_argument("--duplicate-decision-report", type=Path)
    funnel.add_argument("--synthesis-signoff", type=Path)

    abstracts = subparsers.add_parser(
        "fetch-pubmed-abstracts",
        help="explicitly retrieve one official PubMed abstract batch (maximum 200)",
    )
    abstracts.add_argument("pmid", nargs="+")
    abstracts.add_argument("destination", type=Path)
    abstracts.add_argument("--timeout", type=int, default=60)

    merge_abstracts = subparsers.add_parser(
        "merge-abstracts",
        help=(
            "identifier-match retrieved abstracts, preserve conflicts, and recompute "
            "features and eligibility proposals"
        ),
    )
    merge_abstracts.add_argument("groups", type=Path)
    merge_abstracts.add_argument("retrievals", type=Path)
    merge_abstracts.add_argument("ontology", type=Path)
    merge_abstracts.add_argument("specification", type=Path)
    merge_abstracts.add_argument("output", type=Path)

    fetch_queue = subparsers.add_parser(
        "fetch-abstract-queue",
        help="explicitly fetch all PubMed routes in a review queue in batches of 200",
    )
    fetch_queue.add_argument("queue", type=Path)
    fetch_queue.add_argument("destination", type=Path)
    fetch_queue.add_argument("--timeout", type=int, default=60)

    state = subparsers.add_parser(
        "state",
        help="inspect or append authorised review-state records",
    )
    state.add_argument(
        "--review-database",
        type=Path,
        default=DEFAULT_REVIEW_DATABASE,
    )
    state_sub = state.add_subparsers(dest="state_command", required=True)
    audit = state_sub.add_parser("audit")
    audit.set_defaults()
    status = state_sub.add_parser("status")
    status.add_argument("campaign_id")
    decide = state_sub.add_parser("decide")
    decide.add_argument("campaign_id")
    decide.add_argument("group_id")
    decide.add_argument("decision", choices=["include", "exclude"])
    decide.add_argument("reason_code")
    decide.add_argument("evidence", type=Path)
    decide.add_argument("--recorded-at")
    llm = state_sub.add_parser("llm-proposal")
    llm.add_argument("proposal", type=Path)
    llm.add_argument("source_metadata", type=Path)
    fulltext_plan = state_sub.add_parser("fulltext-plan")
    fulltext_plan.add_argument("campaign_id")
    fulltext_plan.add_argument("group_id")
    fulltext_plan.add_argument("evidence", type=Path)
    fulltext_plan.add_argument("--recorded-at")
    fulltext_result = state_sub.add_parser("fulltext-result")
    fulltext_result.add_argument("campaign_id")
    fulltext_result.add_argument("group_id")
    fulltext_result.add_argument("result", choices=["obtained", "unavailable"])
    fulltext_result.add_argument("evidence", type=Path)
    fulltext_result.add_argument("--recorded-at")
    appraised = state_sub.add_parser("appraised")
    appraised.add_argument("campaign_id")
    appraised.add_argument("group_id")
    appraised.add_argument("evidence", type=Path)
    appraised.add_argument("--recorded-at")
    duplicate = state_sub.add_parser("duplicate-decision")
    duplicate.add_argument("campaign_id")
    duplicate.add_argument("pair_sha256")
    duplicate.add_argument(
        "decision",
        choices=["same_study", "different_study", "uncertain"],
    )
    duplicate.add_argument("decided_by")
    duplicate.add_argument("evidence", type=Path)
    duplicate.add_argument("--decided-at")
    acquire_local = subparsers.add_parser(
        "acquire-local",
        help="content-address one operator-selected local document without leaking its path",
    )
    acquire_local.add_argument("file", type=Path)
    acquire_local.add_argument("--repository-root", type=Path, default=Path.cwd())
    acquire_local.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE)
    acquire_local.add_argument("--maximum-bytes", type=int, default=10 * 1024 * 1024)
    _add_visual_table_arguments(acquire_local)
    acquire_local.add_argument("--archived-at")
    acquire_local.add_argument("--output", type=Path)

    project = subparsers.add_parser(
        "project",
        help="create, approve and resume a reviewed personal-research project",
    )
    project.add_argument(
        "--project-database",
        type=Path,
        default=DEFAULT_PROJECT_DATABASE,
    )
    project_sub = project.add_subparsers(dest="project_command", required=True)
    project_create = project_sub.add_parser("create", help="record a plan proposal")
    project_create.add_argument("plan", type=Path)
    project_approve = project_sub.add_parser("approve", help="approve the exact proposed plan")
    project_approve.add_argument("project_id")
    project_approve.add_argument("plan_sha256")
    project_approve.add_argument("approved_by")
    project_approve.add_argument("--approved-at")
    project_attach = project_sub.add_parser(
        "attach-web-source",
        help="attach and verify one archived web-source receipt",
    )
    project_attach.add_argument("project_id")
    project_attach.add_argument("receipt", type=Path)
    project_attach.add_argument("archive_root", type=Path)
    project_attach_local = project_sub.add_parser(
        "attach-local-document",
        help="attach and verify one archived local-document receipt",
    )
    project_attach_local.add_argument("project_id")
    project_attach_local.add_argument("receipt", type=Path)
    project_attach_local.add_argument("archive_root", type=Path)
    project_attach_local.add_argument("--recorded-at")
    project_evidence = project_sub.add_parser(
        "add-evidence",
        help="verify and attach a verbatim evidence span from an archived source",
    )
    project_evidence.add_argument("project_id")
    project_evidence.add_argument("receipt_sha256")
    project_evidence.add_argument("archive_root", type=Path)
    project_evidence.add_argument("quote", type=Path)
    project_evidence.add_argument("locator")
    project_evidence.add_argument(
        "--subquestion", action="append", required=True, dest="subquestions"
    )
    project_evidence.add_argument("--recorded-at")
    project_claim = project_sub.add_parser(
        "propose-claim",
        help="record a citation-bound claim proposal without accepting it",
    )
    project_claim.add_argument("project_id")
    project_claim.add_argument("claim", type=Path)
    project_claim.add_argument("position", choices=("supports", "contradicts", "context", "mixed"))
    project_claim.add_argument("confidence", type=float)
    project_claim.add_argument("proposed_by")
    project_claim.add_argument(
        "--evidence-span", action="append", required=True, dest="evidence_spans"
    )
    project_claim.add_argument("--recorded-at")
    project_review = project_sub.add_parser(
        "review-claim", help="accept or reject one exact claim proposal"
    )
    project_review.add_argument("project_id")
    project_review.add_argument("claim_id")
    project_review.add_argument("decision", choices=("accept", "reject"))
    project_review.add_argument("reviewed_by")
    project_review.add_argument("notes")
    project_review.add_argument("--reviewed-at")
    project_relation = project_sub.add_parser(
        "propose-claim-relation",
        help="record a claim-to-claim relationship proposal without accepting it",
    )
    project_relation.add_argument("project_id")
    project_relation.add_argument("source_claim_id")
    project_relation.add_argument("target_claim_id")
    project_relation.add_argument(
        "relation", choices=("supports", "contradicts", "qualifies", "duplicates")
    )
    project_relation.add_argument("proposed_by")
    project_relation.add_argument("rationale")
    project_relation.add_argument("--recorded-at")
    project_relation_review = project_sub.add_parser(
        "review-claim-relation",
        help="accept or reject one exact claim relationship proposal",
    )
    project_relation_review.add_argument("project_id")
    project_relation_review.add_argument("relation_id")
    project_relation_review.add_argument("decision", choices=("accept", "reject"))
    project_relation_review.add_argument("reviewed_by")
    project_relation_review.add_argument("notes")
    project_relation_review.add_argument("--reviewed-at")
    project_matrix = project_sub.add_parser(
        "matrix",
        help="render claims, citations, contradiction positions and review states",
    )
    project_matrix.add_argument("project_id")
    project_citation_graph = project_sub.add_parser(
        "citation-graph",
        help="project the append-only ledger as a deterministic claim/evidence graph",
    )
    project_citation_graph.add_argument("project_id")
    project_plan_map = project_sub.add_parser(
        "plan-map",
        help="project the exact reviewed plan as a deterministic navigation map",
    )
    project_plan_map.add_argument("project_id")
    project_trace_view = project_sub.add_parser(
        "trace-view",
        help="render the deterministic claim/evidence graph as offline inspectable HTML",
    )
    project_trace_view.add_argument("project_id")
    project_trace_view.add_argument("output", type=Path)
    project_mind_map = project_sub.add_parser(
        "mind-map",
        help="render the exact project plan as offline inspectable HTML",
    )
    project_mind_map.add_argument("project_id")
    project_mind_map.add_argument("output", type=Path)
    project_frontier = project_sub.add_parser(
        "frontier",
        help="cross-evaluate completed runs and export the bounded next research frontier",
    )
    project_frontier.add_argument("project_id")
    project_frontier.add_argument("--run", action="append", type=Path, required=True)
    project_frontier.add_argument("--evaluated-at", required=True)
    project_frontier.add_argument("--minimum-evidence-spans", type=int, default=1)
    project_frontier.add_argument("--minimum-distinct-domains", type=int, default=1)
    project_frontier.add_argument("--maximum-age-days", type=int)
    project_frontier.add_argument("--output", type=Path, required=True)
    project_frontier_request = project_sub.add_parser(
        "frontier-request",
        help="export a minimal content-hashed request for any model provider",
    )
    project_frontier_request.add_argument("project_id")
    project_frontier_request.add_argument("frontier", type=Path)
    project_frontier_request.add_argument("--requested-at", required=True)
    project_frontier_request.add_argument("--maximum-followups", type=int, default=3)
    project_frontier_request.add_argument("--output", type=Path, required=True)
    project_extension = project_sub.add_parser(
        "extend-frontier",
        help="validate up to three gap-filling questions as a new approval-gated project",
    )
    project_extension.add_argument("project_id")
    project_extension.add_argument("frontier", type=Path)
    project_extension.add_argument("followups", type=Path)
    project_extension.add_argument("extension_project_id")
    project_extension.add_argument("--created-at", required=True)
    project_extension.add_argument("--output", type=Path, required=True)
    project_extension.add_argument("--plan-output", type=Path, required=True)
    project_provider_extension = project_sub.add_parser(
        "extend-frontier-provider",
        help=(
            "validate an exact provider response, preserve its cost provenance and "
            "export a separately approvable project"
        ),
    )
    project_provider_extension.add_argument("project_id")
    project_provider_extension.add_argument("frontier", type=Path)
    project_provider_extension.add_argument("request", type=Path)
    project_provider_extension.add_argument("response", type=Path)
    project_provider_extension.add_argument("extension_project_id")
    project_provider_extension.add_argument("--created-at", required=True)
    project_provider_extension.add_argument("--output", type=Path, required=True)
    project_provider_extension.add_argument("--plan-output", type=Path, required=True)
    project_outline = project_sub.add_parser(
        "propose-outline",
        help="validate and ledger a complete outline proposal against exact run evidence",
    )
    project_outline.add_argument("project_id")
    project_outline.add_argument("run", type=Path)
    project_outline.add_argument("proposal", type=Path)
    project_outline.add_argument("proposed_by")
    project_outline.add_argument("--recorded-at")
    project_outline.add_argument(
        "--supplement",
        action="append",
        nargs=2,
        metavar=("PROJECT_ID", "RUN_PATH"),
        default=[],
        help="bind the outline to the same composite evidence packet (repeatable)",
    )
    project_outline_review = project_sub.add_parser(
        "review-outline",
        help="accept or reject one exact packet-bound outline proposal",
    )
    project_outline_review.add_argument("project_id")
    project_outline_review.add_argument("outline_id")
    project_outline_review.add_argument("decision", choices=("accept", "reject"))
    project_outline_review.add_argument("reviewed_by")
    project_outline_review.add_argument("notes")
    project_outline_review.add_argument(
        "--reviewer-kind",
        choices=("human", "controlled_canary"),
        default="human",
        help="label controlled test acceptance without claiming human review",
    )
    project_outline_review.add_argument("--reviewed-at")
    project_packet = project_sub.add_parser(
        "synthesis-packet",
        help="export exact run evidence and a provider-neutral synthesis contract",
    )
    project_packet.add_argument("project_id")
    project_packet.add_argument("run", type=Path)
    project_packet.add_argument("output", type=Path)
    project_packet.add_argument(
        "--supplement",
        action="append",
        nargs=2,
        metavar=("PROJECT_ID", "RUN_PATH"),
        default=[],
        help="merge a ledgered supplement project and run into the packet (repeatable)",
    )
    project_synthesis = project_sub.add_parser(
        "render-synthesis",
        help="validate and render a citation-bound external synthesis proposal",
    )
    project_synthesis.add_argument("project_id")
    project_synthesis.add_argument("run", type=Path)
    project_synthesis.add_argument("proposal", type=Path)
    project_synthesis.add_argument("output", type=Path)
    project_synthesis.add_argument("--validation", type=Path)
    project_synthesis.add_argument(
        "--supplement",
        action="append",
        nargs=2,
        metavar=("PROJECT_ID", "RUN_PATH"),
        default=[],
        help="rebuild the same composite packet used by the proposal (repeatable)",
    )
    project_report = project_sub.add_parser(
        "report", help="export reviewed project state as traceable Markdown"
    )
    project_report.add_argument("project_id")
    project_report.add_argument("output", type=Path)
    project_run = project_sub.add_parser(
        "run",
        help="resume an approved discovery, acquisition and evidence-retrieval run",
    )
    project_run.add_argument("project_id")
    _add_project_run_arguments(project_run, parallel=False)
    project_parallel = project_sub.add_parser(
        "run-parallel",
        help=(
            "run independent approved projects concurrently after an all-project "
            "approval preflight"
        ),
    )
    project_parallel.add_argument("project_ids", nargs="+")
    project_parallel.add_argument("--maximum-workers", type=int, default=3)
    project_parallel.add_argument("--output", type=Path, required=True)
    _add_project_run_arguments(project_parallel, parallel=True)
    project_status = project_sub.add_parser("status", help="audit and resume project state")
    project_status.add_argument("project_id")

    retrieve = subparsers.add_parser(
        "retrieve-passages",
        help="verify archived sources and rank exact-offset evidence passages",
    )
    retrieve.add_argument("archive_root", type=Path)
    retrieve.add_argument("query")
    retrieve.add_argument("receipts", type=Path, nargs="+")
    dense_group = retrieve.add_mutually_exclusive_group()
    dense_group.add_argument("--dense-ranking", type=Path)
    dense_group.add_argument(
        "--dense",
        action="store_true",
        help="generate a local FastEmbed dense ranking and fuse it with BM25",
    )
    retrieve.add_argument("--dense-model", default=DEFAULT_DENSE_MODEL)
    retrieve.add_argument(
        "--dense-cache-root",
        type=Path,
        default=Path("~/.giga/research-models/fastembed"),
    )
    retrieve.add_argument("--dense-batch-size", type=int, default=64)
    retrieve.add_argument("--dense-threads", type=int)
    retrieve.add_argument(
        "--metadata-scope",
        type=Path,
        help="JSON receipt-bound metadata scope applied before BM25, dense ranking and fusion",
    )
    retrieve.add_argument("--bm25-weight", type=float, default=1.0)
    retrieve.add_argument("--dense-weight", type=float, default=1.0)
    retrieve.add_argument("--rank-constant", type=int, default=60)
    retrieve.add_argument("--maximum-characters", type=int, default=1200)
    retrieve.add_argument("--overlap-characters", type=int, default=180)
    retrieve.add_argument("--limit", type=int, default=10)
    retrieve.add_argument("--per-source", type=int, default=3)
    retrieve.add_argument("--output", type=Path)

    active_learning = subparsers.add_parser(
        "simulate-active-learning",
        help=(
            "measure deterministic human-oracle queue prioritisation on a fully "
            "labelled, deduplicated historical corpus without writing live review state"
        ),
    )
    active_learning.add_argument(
        "groups",
        type=Path,
        help="canonical DEDUP_GROUPS.jsonl-style records",
    )
    active_learning.add_argument(
        "oracle",
        type=Path,
        help="fully labelled simulation-only oracle JSON",
    )
    active_learning.add_argument("output", type=Path)
    active_learning.add_argument(
        "--seed-group-id",
        action="append",
        required=True,
        help="historical human label used to seed the simulation (repeatable)",
    )
    active_learning.add_argument("--maximum-labels", type=int)
    active_learning.add_argument("--target-recall", type=float, default=1.0)

    historical_ris = subparsers.add_parser(
        "prepare-historical-ris",
        help=(
            "prepare a label-blind canonical corpus and simulation-only oracle "
            "from final historical RIS include/exclude exports"
        ),
    )
    historical_ris.add_argument("included_ris", type=Path)
    historical_ris.add_argument("excluded_ris", type=Path)
    historical_ris.add_argument("output", type=Path)
    historical_ris.add_argument("--simulation-id", required=True)
    historical_ris.add_argument("--source-id", required=True)

    historical_rds = subparsers.add_parser(
        "inspect-historical-rds-performance",
        help=(
            "validate and safely summarise a historical human-screener RDS performance "
            "table without emitting raw rows or writing live review state"
        ),
    )
    historical_rds.add_argument("rds", type=Path)
    historical_rds.add_argument("output", type=Path)
    historical_rds.add_argument("--expected-review")
    historical_rds.add_argument("--expected-review-authors")

    benchmark = subparsers.add_parser(
        "benchmark",
        help="score and compare research runs with deterministic bilingual metrics",
    )
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_command", required=True)
    benchmark_score = benchmark_sub.add_parser("score", help="score one benchmark run")
    benchmark_score.add_argument("run", type=Path)
    benchmark_score.add_argument("--output", type=Path)
    benchmark_score_synthesis = benchmark_sub.add_parser(
        "score-synthesis",
        help="convert and score one validated synthesis with an explicit measurement envelope",
    )
    benchmark_score_synthesis.add_argument("packet", type=Path)
    benchmark_score_synthesis.add_argument("proposal", type=Path)
    benchmark_score_synthesis.add_argument("measurement", type=Path)
    benchmark_score_synthesis.add_argument("--run-output", type=Path, required=True)
    benchmark_score_synthesis.add_argument("--output", type=Path)
    benchmark_score_extractive = benchmark_sub.add_parser(
        "score-extractive",
        help="convert and score one verified extractive research run",
    )
    benchmark_score_extractive.add_argument("plan", type=Path)
    benchmark_score_extractive.add_argument("run", type=Path)
    benchmark_score_extractive.add_argument("measurement", type=Path)
    benchmark_score_extractive.add_argument("--run-output", type=Path, required=True)
    benchmark_score_extractive.add_argument("--output", type=Path)
    benchmark_score_retrieval = benchmark_sub.add_parser(
        "score-retrieval",
        help="score BM25, owned dense and hybrid rankings on one exact gold corpus",
    )
    benchmark_score_retrieval.add_argument("specification", type=Path)
    benchmark_score_retrieval.add_argument("bm25", type=Path)
    benchmark_score_retrieval.add_argument("hybrid", type=Path)
    benchmark_score_retrieval.add_argument("--output", type=Path)
    benchmark_score_retrieval_cohort = benchmark_sub.add_parser(
        "score-retrieval-cohort",
        help="aggregate a provenance-bound external multilingual retrieval cohort",
    )
    benchmark_score_retrieval_cohort.add_argument("manifest", type=Path)
    benchmark_score_retrieval_cohort.add_argument("scores", type=Path, nargs="+")
    benchmark_score_retrieval_cohort.add_argument("--output", type=Path)
    benchmark_compare = benchmark_sub.add_parser(
        "compare", help="compare score documents over identical case sets"
    )
    benchmark_compare.add_argument("scores", type=Path, nargs="+")
    benchmark_compare.add_argument(
        "--system-alias",
        action="append",
        nargs=2,
        metavar=("PRODUCER", "COHORT_SYSTEM"),
        default=[],
        help="group versioned producer names without mutating source scores (repeatable)",
    )
    benchmark_compare.add_argument("--output", type=Path)
    benchmark_import = benchmark_sub.add_parser(
        "import-drb", help="validate and import the official bilingual DeepResearch Bench cases"
    )
    benchmark_import.add_argument("query_jsonl", type=Path)
    benchmark_import.add_argument("--output", type=Path, required=True)
    benchmark_race = benchmark_sub.add_parser(
        "import-drb-race", help="validate and aggregate official 100-case RACE results"
    )
    benchmark_race.add_argument("result_jsonl", type=Path)
    benchmark_race.add_argument("--output", type=Path, required=True)
    benchmark_fact = benchmark_sub.add_parser(
        "import-drb-fact", help="validate and aggregate official 100-case FACT results"
    )
    benchmark_fact.add_argument("result_jsonl", type=Path)
    benchmark_fact.add_argument("--output", type=Path, required=True)
    benchmark_competitor_cohort = benchmark_sub.add_parser(
        "import-drb-competitor-cohort",
        help="import published RACE and FACT results for one predeclared case cohort",
    )
    benchmark_competitor_cohort.add_argument("system")
    benchmark_competitor_cohort.add_argument("race_jsonl", type=Path)
    benchmark_competitor_cohort.add_argument("fact_jsonl", type=Path)
    benchmark_competitor_cohort.add_argument("case_ids", nargs="+")
    benchmark_competitor_cohort.add_argument("--output", type=Path, required=True)
    benchmark_reportbench = benchmark_sub.add_parser(
        "import-reportbench",
        help="validate and import the official 100-case ReportBench v1.1 manifest",
    )
    benchmark_reportbench.add_argument("case_jsonl", type=Path)
    benchmark_reportbench.add_argument("--output", type=Path, required=True)
    benchmark_reportbench_results = benchmark_sub.add_parser(
        "import-reportbench-results",
        help="reproduce ReportBench aggregates from official-shape result CSVs",
    )
    benchmark_reportbench_results.add_argument("system")
    benchmark_reportbench_results.add_argument("case_jsonl", type=Path)
    benchmark_reportbench_results.add_argument("related_work_csv", type=Path)
    benchmark_reportbench_results.add_argument("statement_metrics_csv", type=Path)
    benchmark_reportbench_results.add_argument("--output", type=Path, required=True)
    benchmark_pdrbench = benchmark_sub.add_parser(
        "import-pdrbench",
        help="validate and import a pinned PDR-Bench query cohort",
    )
    benchmark_pdrbench.add_argument("case_jsonl", type=Path)
    benchmark_pdrbench.add_argument("--output", type=Path, required=True)
    benchmark_pdrbench_results = benchmark_sub.add_parser(
        "import-pdrbench-results",
        help="reproduce PDR-Bench P/Q/R aggregates from complete result artifacts",
    )
    benchmark_pdrbench_results.add_argument("system")
    benchmark_pdrbench_results.add_argument("case_jsonl", type=Path)
    benchmark_pdrbench_results.add_argument("personalization_jsonl", type=Path)
    benchmark_pdrbench_results.add_argument("quality_jsonl", type=Path)
    benchmark_pdrbench_results.add_argument("reliability_jsonl", type=Path)
    benchmark_pdrbench_results.add_argument("--output", type=Path, required=True)
    benchmark_deepsynth = benchmark_sub.add_parser(
        "score-deepsynth",
        help="score a complete DeepSynth-shaped structured-answer cohort",
    )
    benchmark_deepsynth.add_argument("system")
    benchmark_deepsynth.add_argument("gold_json", type=Path)
    benchmark_deepsynth.add_argument("predictions_json", type=Path)
    benchmark_deepsynth.add_argument("--output", type=Path, required=True)
    benchmark_fact_run = benchmark_sub.add_parser(
        "adapt-drb-fact-run",
        help=(
            "adapt one official FACT artifact into the deterministic run contract "
            "without inventing fetch provenance or latency"
        ),
    )
    benchmark_fact_run.add_argument("result_jsonl", type=Path)
    benchmark_fact_run.add_argument("case_id")
    benchmark_fact_run.add_argument("measurement", type=Path)
    benchmark_fact_run.add_argument("--run-output", type=Path, required=True)
    benchmark_fact_run.add_argument("--output", type=Path)
    benchmark_prepare = benchmark_sub.add_parser(
        "prepare-drb", help="write the exact official raw-article JSONL contract"
    )
    benchmark_prepare.add_argument("cases", type=Path)
    benchmark_prepare.add_argument("articles", type=Path)
    benchmark_prepare.add_argument("--jsonl", type=Path, required=True)
    benchmark_prepare.add_argument("--output", type=Path)
    benchmark_run = benchmark_sub.add_parser(
        "prepare-drb-run",
        help="render one verified GIGA run as an official-shape raw article record",
    )
    benchmark_run.add_argument("cases", type=Path)
    benchmark_run.add_argument("case_id")
    benchmark_run.add_argument("plan", type=Path)
    benchmark_run.add_argument("run", type=Path)
    benchmark_run.add_argument("system")
    benchmark_run.add_argument("--jsonl", type=Path, required=True)
    benchmark_run.add_argument("--output", type=Path)
    benchmark_synthesis = benchmark_sub.add_parser(
        "prepare-drb-synthesis",
        help="render one validated synthesis proposal as an official-shape raw article record",
    )
    benchmark_synthesis.add_argument("cases", type=Path)
    benchmark_synthesis.add_argument("case_id")
    benchmark_synthesis.add_argument("packet", type=Path)
    benchmark_synthesis.add_argument("proposal", type=Path)
    benchmark_synthesis.add_argument("system")
    benchmark_synthesis.add_argument("--jsonl", type=Path, required=True)
    benchmark_synthesis.add_argument("--output", type=Path)
    benchmark_cohort = benchmark_sub.add_parser(
        "cohort-drb",
        help="assemble verified records and report exact official-cohort coverage",
    )
    benchmark_cohort.add_argument("cases", type=Path)
    benchmark_cohort.add_argument("system")
    benchmark_cohort.add_argument(
        "--record",
        nargs=2,
        action="append",
        required=True,
        metavar=("PRODUCER", "JSONL"),
    )
    benchmark_cohort.add_argument("--jsonl", type=Path, required=True)
    benchmark_cohort.add_argument("--output", type=Path)
    benchmark_campaign = benchmark_sub.add_parser(
        "plan-drb-campaign",
        help="plan a resumable, coverage-balancing batch of missing official cases",
    )
    benchmark_campaign.add_argument("cases", type=Path)
    benchmark_campaign.add_argument("system")
    benchmark_campaign.add_argument(
        "--record",
        nargs=2,
        action="append",
        default=[],
        metavar=("PRODUCER", "JSONL"),
    )
    benchmark_campaign.add_argument("--limit", type=int, default=10)
    benchmark_campaign.add_argument("--created-at", required=True)
    benchmark_campaign.add_argument("--campaign-directory", type=Path, required=True)
    benchmark_campaign.add_argument("--output", type=Path)
    benchmark_admission = benchmark_sub.add_parser(
        "admit-drb-campaign",
        help="admit one exact DRB campaign under a zero-spend public-research envelope",
    )
    benchmark_admission.add_argument("campaign", type=Path)
    benchmark_admission.add_argument("campaign_plan_sha256")
    benchmark_admission.add_argument("authorized_by")
    benchmark_admission.add_argument("authority_reference")
    benchmark_admission.add_argument("--authorized-at", required=True)
    benchmark_admission.add_argument("--maximum-network-requests", type=int, required=True)
    benchmark_admission.add_argument("--maximum-runtime-seconds", type=int, required=True)
    benchmark_admission.add_argument(
        "--project-database", type=Path, default=DEFAULT_PROJECT_DATABASE
    )
    benchmark_admission.add_argument("--output", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "acquire-local":
            result = _acquire_local(args)
        elif args.command == "project":
            result = _project(args)
        elif args.command == "benchmark":
            result = _benchmark(args)
        elif args.command == "retrieve-passages":
            result = _retrieve_passages(args)
        elif args.command == "compile-search":
            result = _compile_search(args)
        elif args.command == "simulate-active-learning":
            result = _simulate_active_learning(args)
        elif args.command == "prepare-historical-ris":
            result = _prepare_historical_ris(args)
        elif args.command == "inspect-historical-rds-performance":
            result = _inspect_historical_rds_performance(args)
        elif args.command == "screen":
            result = _screen(args)
        elif args.command == "fetch-pmc":
            result = _fetch_pmc(args)
        elif args.command == "extract-pmc":
            result = _extract_pmc(args)
        elif args.command == "validate-exclusion-audit":
            result = _validate_exclusion_audit(args)
        elif args.command == "saturation":
            result = _saturation(args)
        elif args.command == "readiness":
            result = _readiness(args)
        elif args.command == "review-funnel":
            result = _review_funnel(args)
        elif args.command == "fetch-pubmed-abstracts":
            result = _fetch_abstracts(args)
        elif args.command == "merge-abstracts":
            result = _merge_abstracts(args)
        elif args.command == "fetch-abstract-queue":
            result = _fetch_abstract_queue(args)
        else:
            result = _state(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (KeyError, OSError, ScientificEvidenceError, ResearchBenchmarkError, PassageRetrievalError, ResearchProjectError, ResearchExportError, WebAcquisitionError) as exc:
        print(f"scientific-pipeline: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
