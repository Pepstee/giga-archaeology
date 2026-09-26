"""Command surface for the read-only GIGA Archaeology pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Direct file launch must resolve this checkout without relying on the caller's cwd.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from modules.operations.archaeology.inventory import (
    InventoryError,
    InventoryPolicy,
    write_inventory,
)
from modules.operations.archaeology.hypotheses import (
    HypothesisError,
    ScannerPaths,
    write_hypotheses,
)
from modules.operations.archaeology.history import HistoryError, write_history
from modules.operations.archaeology.counterevidence import (
    CounterevidenceError,
    write_counterevidence,
)
from modules.operations.archaeology.judge import JudgeError, write_judgement
from modules.operations.archaeology.quarantine import (
    QuarantineError,
    write_quarantine_canary,
)
from modules.operations.archaeology.navigation_inventory import (
    NavigationInventoryError,
    current_navigation_run,
    locate_navigation_inventory,
    refresh_navigation_inventory,
    refresh_navigation_inventory_delta,
    search_navigation_inventory,
)
from modules.operations.archaeology.semantic_graph import (
    GraphifyConfig,
    SemanticGraphError,
    archive_legacy_graph,
    current_semantic_run,
    locate_semantic_graph,
    query_semantic_graph,
    refresh_semantic_graph,
)
from modules.operations.archaeology.navigation_maintenance import (
    NavigationMaintenanceError,
    run_navigation_maintenance,
)
from modules.operations.archaeology.map_catalog import (
    build_map_catalog,
    map_by_id,
    route_query_maps,
)
from modules.operations.archaeology.mapper import (
    MapperError,
    SUPPORTED_MAPS,
    audit_mapper,
    current_mapper_run,
    query_mapper,
    refresh_mapper,
)
from modules.operations.archaeology.dossier import (
    DossierError,
    build_context_projection,
    build_dossier,
)
from modules.operations.archaeology.benchmark import (
    BenchmarkError,
    run_context_benchmark,
    run_mapper_benchmark,
)
from modules.operations.archaeology.capability_feed import (
    CapabilityFeedError,
    DEFAULT_EVIDENCE_LEDGER,
    build_reviewed_archaeologist_v2_capability_feed,
    build_retrospective_capability_feed,
)
from modules.operations.archaeology.consultation import (
    ConsultationError,
    consult_before_decision,
)
from modules.operations.archaeology.scip_map import (
    ScipMapError,
    ScipRefreshConfig,
    build_scip_index,
    build_typescript_scip_index,
    current_scip_store,
    discover_scip_projects,
    refresh_scip_store,
)
from modules.operations.archaeology.retention import (
    RetentionError,
    assess_derived_family_retention,
    assess_cross_store_derived_map_lineage,
    compact_inactive_scip_generation,
    compact_inactive_semantic_generation,
    inspect_retention_receipt,
    read_active_consumer_registry,
    recover_current_compacted_mapper,
    render_cross_store_derived_map_lineage_report,
    render_retention_receipt_inspection,
    restore_compacted_scip_generation,
    restore_compacted_semantic_generation,
    run_scip_round_trip_canary,
    run_semantic_round_trip_canary,
    verify_compacted_generation_restore_stream,
    verify_scip_compacted_generation_restore_stream,
    verify_semantic_compacted_generation_restore_stream,
    write_compacted_generation_restore_verification,
    write_cross_store_derived_map_lineage_assessment,
    write_derived_family_retention_assessment,
    write_scip_restore_stream_verification,
    write_scip_round_trip_canary,
    write_semantic_restore_stream_verification,
    write_semantic_round_trip_canary,
)
from modules.operations.archaeology.divergence import (
    DivergenceError,
    write_cli_donor_superset_disposition,
    write_derived_payload_verifier_lineage,
    write_cross_worktree_behavior_map,
    write_cross_worktree_identity_map,
    write_cross_worktree_static_fact_map,
)


def _parse_generated_at(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError as exc:
        raise RetentionError("invalid generated-at timestamp") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="giga-archaeology")
    subcommands = parser.add_subparsers(dest="command", required=True)
    inventory = subcommands.add_parser(
        "inventory", help="produce a read-only immutable inventory"
    )
    inventory.add_argument("--repository", type=Path, required=True)
    inventory.add_argument("--output", type=Path, required=True)
    inventory.add_argument("--admit-untracked", action="append", default=[])
    divergence = subcommands.add_parser(
        "divergence-map",
        help="compare related worktrees without granting canonicality or retirement",
    )
    divergence.add_argument("--canonical", type=Path, required=True)
    divergence.add_argument("--donor", type=Path, action="append", required=True)
    divergence.add_argument("--runtime", type=Path, action="append", default=[])
    divergence.add_argument("--output", type=Path, required=True)
    static_divergence = subcommands.add_parser(
        "divergence-static-map",
        help="compare bounded static facts without granting runtime reachability",
    )
    static_divergence.add_argument("--canonical", type=Path, required=True)
    static_divergence.add_argument("--donor", type=Path, action="append", required=True)
    static_divergence.add_argument("--runtime", type=Path, action="append", default=[])
    static_divergence.add_argument("--predecessor", type=Path, required=True)
    static_divergence.add_argument("--output", type=Path, required=True)
    behavior_divergence = subcommands.add_parser(
        "divergence-behavior-map",
        help="bind M70 clusters to behavioral and test counterevidence",
    )
    behavior_divergence.add_argument("--canonical", type=Path, required=True)
    behavior_divergence.add_argument(
        "--donor", type=Path, action="append", required=True
    )
    behavior_divergence.add_argument(
        "--runtime", type=Path, action="append", default=[]
    )
    behavior_divergence.add_argument("--m69", type=Path, required=True)
    behavior_divergence.add_argument("--m70", type=Path, required=True)
    behavior_divergence.add_argument(
        "--allow-canonical-m70-drift", action="append", default=[]
    )
    behavior_divergence.add_argument("--output", type=Path, required=True)
    derived_payload_lineage = subcommands.add_parser(
        "derived-payload-lineage",
        help="inspect derived-agent-payload verifier lineage without retirement authority",
    )
    derived_payload_lineage.add_argument("--canonical", type=Path, required=True)
    derived_payload_lineage.add_argument(
        "--donor", type=Path, action="append", required=True
    )
    derived_payload_lineage.add_argument("--m69", type=Path, required=True)
    derived_payload_lineage.add_argument("--m70", type=Path, required=True)
    derived_payload_lineage.add_argument("--m71", type=Path, required=True)
    derived_payload_lineage.add_argument("--output", type=Path, required=True)
    cli_superset_disposition = subcommands.add_parser(
        "cli-superset-disposition",
        help=(
            "adjudicate the M69 old archaeologist.py CLI donor-superset "
            "family against canonical archaeology.py without donor execution"
        ),
    )
    cli_superset_disposition.add_argument("--canonical", type=Path, required=True)
    cli_superset_disposition.add_argument("--m69", type=Path, required=True)
    cli_superset_disposition.add_argument("--m70", type=Path, required=True)
    cli_superset_disposition.add_argument("--m71", type=Path, required=True)
    cli_superset_disposition.add_argument("--output", type=Path, required=True)
    hypotheses = subcommands.add_parser(
        "hypotheses", help="run isolated scanners and preserve OBSERVED hypotheses"
    )
    hypotheses.add_argument("--inventory", type=Path, required=True)
    hypotheses.add_argument("--output", type=Path, required=True)
    hypotheses.add_argument("--tools-root", type=Path, help="explicit scanner installation root")
    hypotheses.add_argument(
        "--no-sandbox", action="store_true",
        help="explicitly run scanners without the operating-system sandbox",
    )
    counterevidence = subcommands.add_parser(
        "counterevidence", help="model entrypoint and dynamic-use counterevidence"
    )
    counterevidence.add_argument("--inventory", type=Path, required=True)
    counterevidence.add_argument("--hypotheses", type=Path, required=True)
    counterevidence.add_argument("--output", type=Path, required=True)
    history = subcommands.add_parser(
        "history",
        help="compare Git history and a second repository without executing code",
    )
    history.add_argument("--inventory", type=Path, required=True)
    history.add_argument("--hypotheses", type=Path, required=True)
    history.add_argument("--counterevidence", type=Path, required=True)
    history.add_argument("--comparison-repository", type=Path, required=True)
    history.add_argument("--output", type=Path, required=True)
    judge = subcommands.add_parser(
        "judge",
        help="classify hypotheses with deterministic fail-closed evidence gates",
    )
    judge.add_argument("--inventory", type=Path, required=True)
    judge.add_argument("--hypotheses", type=Path, required=True)
    judge.add_argument("--counterevidence", type=Path, required=True)
    judge.add_argument("--history", type=Path, required=True)
    judge.add_argument("--output", type=Path, required=True)
    quarantine = subcommands.add_parser(
        "quarantine-canary",
        help="quarantine one verified candidate in a disposable fixture",
    )
    quarantine.add_argument("--repository", type=Path, required=True)
    quarantine.add_argument("--inventory", type=Path, required=True)
    quarantine.add_argument("--hypotheses", type=Path, required=True)
    quarantine.add_argument("--counterevidence", type=Path, required=True)
    quarantine.add_argument("--history", type=Path, required=True)
    quarantine.add_argument("--judge", type=Path, required=True)
    quarantine.add_argument("--hypothesis-id", required=True)
    quarantine.add_argument("--output", type=Path, required=True)
    navigation = subcommands.add_parser(
        "navigation-refresh",
        help="atomically refresh the complete local working-tree navigation inventory",
    )
    navigation.add_argument("--root", type=Path, required=True)
    navigation.add_argument("--store", type=Path, required=True)
    navigation.add_argument("--include-path", action="append", default=[], help="exact regular file to admit; repeatable; publishes PARTIAL and reads no other working-tree content")
    navigation_delta = subcommands.add_parser(
        "navigation-refresh-delta",
        help=(
            "refresh only committed and live Git-visible changes and publish "
            "an explicitly PARTIAL inventory"
        ),
    )
    navigation_delta.add_argument("--root", type=Path, required=True)
    navigation_delta.add_argument("--store", type=Path, required=True)
    navigation_delta.add_argument(
        "--path",
        action="append",
        default=[],
        help="refresh only this exact repository-relative path; repeatable",
    )
    navigation_status = subcommands.add_parser(
        "navigation-status", help="verify and report the current navigation inventory"
    )
    navigation_status.add_argument("--store", type=Path, required=True)
    navigation_search = subcommands.add_parser(
        "navigation-search",
        help="search the current authenticated navigation inventory",
    )
    navigation_search.add_argument("query")
    navigation_search.add_argument("--store", type=Path, required=True)
    navigation_search.add_argument("--limit", type=int, default=50)
    navigation_search.add_argument("--semantic-only", action="store_true")
    navigation_locate = subcommands.add_parser(
        "navigation-locate",
        help="return a closed path-role result from the authenticated inventory",
    )
    navigation_locate.add_argument("query")
    navigation_locate.add_argument("--store", type=Path, required=True)
    navigation_locate.add_argument("--limit", type=int, default=50)
    navigation_locate.add_argument("--semantic-only", action="store_true")
    semantic = subcommands.add_parser(
        "semantic-refresh",
        help="incrementally refresh the privacy-gated local Graphify navigation layer",
    )
    semantic.add_argument("--inventory-store", type=Path, required=True)
    semantic.add_argument("--semantic-store", type=Path, required=True)
    semantic.add_argument("--graphify-python", type=Path, default=GraphifyConfig.python)
    semantic.add_argument("--endpoint", default=GraphifyConfig.endpoint)
    semantic.add_argument("--model", default=GraphifyConfig.model)
    semantic.add_argument("--max-new-documents", type=int, default=1)
    semantic_status = subcommands.add_parser(
        "semantic-status", help="verify and report the current local semantic graph"
    )
    semantic_status.add_argument("--semantic-store", type=Path, required=True)
    semantic_query = subcommands.add_parser(
        "semantic-query",
        help="run a scoped query against the authenticated semantic graph",
    )
    semantic_query.add_argument("question")
    semantic_query.add_argument("--semantic-store", type=Path, required=True)
    semantic_query.add_argument("--budget", type=int, default=2000)
    semantic_locate = subcommands.add_parser(
        "semantic-locate",
        help="return closed source locations from the authenticated semantic graph",
    )
    semantic_locate.add_argument("query")
    semantic_locate.add_argument("--semantic-store", type=Path, required=True)
    semantic_locate.add_argument("--limit", type=int, default=100)
    semantic_archive = subcommands.add_parser(
        "semantic-archive-legacy",
        help="archive an obsolete ignored graph and link its path to the current local store",
    )
    semantic_archive.add_argument("--legacy-path", type=Path, required=True)
    semantic_archive.add_argument("--semantic-store", type=Path, required=True)
    maintenance = subcommands.add_parser(
        "navigation-maintenance",
        help="non-blocking inventory and local semantic refresh for daily or milestone use",
    )
    maintenance.add_argument("--root", type=Path, required=True)
    maintenance.add_argument("--inventory-store", type=Path, required=True)
    maintenance.add_argument("--semantic-store", type=Path, required=True)
    maintenance.add_argument("--mapper-store", type=Path)
    maintenance.add_argument("--scip-store", type=Path)
    maintenance.add_argument("--scip-node", type=Path)
    maintenance.add_argument("--scip-python-indexer-entrypoint", type=Path)
    maintenance.add_argument("--scip-python-package-json", type=Path)
    maintenance.add_argument("--scip-typescript-indexer-entrypoint", type=Path)
    maintenance.add_argument("--scip-typescript-package-json", type=Path)
    maintenance.add_argument("--scip-timeout", type=int, default=180)
    maintenance.add_argument(
        "--runtime-registry", type=Path, action="append", default=[]
    )
    maintenance.add_argument("--reason", required=True)
    maintenance.add_argument("--mode", choices=("full", "delta"), default="full")
    maintenance.add_argument(
        "--graphify-python", type=Path, default=GraphifyConfig.python
    )
    maintenance.add_argument("--endpoint", default=GraphifyConfig.endpoint)
    maintenance.add_argument("--model", default=GraphifyConfig.model)
    maintenance.add_argument("--max-new-documents", type=int, default=1)
    maintenance.add_argument(
        "--model-server-executable",
        type=Path,
        default=Path("/opt/homebrew/bin/mlx_lm.server"),
    )
    maintenance.add_argument("--model-path", type=Path, required=True)
    maintenance.add_argument("--strict", action="store_true")
    catalog = subcommands.add_parser(
        "map-catalog",
        help="print the deterministic Archaeology map implementation contract",
    )
    catalog.add_argument("--map", dest="map_id")
    mapper_refresh = subcommands.add_parser(
        "mapper-refresh",
        help="compile and atomically publish authenticated mapper facts",
    )
    mapper_refresh.add_argument("--inventory-store", type=Path, required=True)
    mapper_refresh.add_argument("--mapper-store", type=Path, required=True)
    mapper_refresh.add_argument(
        "--runtime-registry",
        type=Path,
        action="append",
        default=[],
        help="private external capability-adoption registry snapshot; repeatable",
    )
    mapper_refresh.add_argument(
        "--semantic-store",
        type=Path,
        help="existing private authenticated local Graphify store",
    )
    mapper_refresh.add_argument(
        "--scip-manifest",
        type=Path,
        action="append",
        default=[],
        help="private inventory-bound SCIP precision manifest; repeatable",
    )
    mapper_refresh.add_argument(
        "--scip-store",
        type=Path,
        help="current authenticated atomic SCIP store",
    )
    scip_build = subcommands.add_parser(
        "scip-build",
        help="compile one admitted language closure into a private SCIP index",
    )
    scip_build.add_argument("--inventory-store", type=Path, required=True)
    scip_build.add_argument("--output", type=Path, required=True)
    scip_build.add_argument("--node", type=Path, required=True)
    scip_build.add_argument("--indexer-entrypoint", type=Path, required=True)
    scip_build.add_argument("--package-json", type=Path, required=True)
    scip_build.add_argument(
        "--language", choices=("python", "typescript"), default="python"
    )
    scip_build.add_argument(
        "--project-root",
        default=".",
        help="repository-relative TypeScript project root; ignored for Python",
    )
    scip_build.add_argument("--timeout", type=int, default=180)
    scip_discover = subcommands.add_parser(
        "scip-discover",
        help="discover supported SCIP project closures from authenticated inventory",
    )
    scip_discover.add_argument("--inventory-store", type=Path, required=True)
    scip_refresh = subcommands.add_parser(
        "scip-refresh",
        help="atomically rebuild every supported discovered SCIP project",
    )
    scip_refresh.add_argument("--inventory-store", type=Path, required=True)
    scip_refresh.add_argument("--store", type=Path, required=True)
    scip_refresh.add_argument("--node", type=Path, required=True)
    scip_refresh.add_argument("--python-indexer-entrypoint", type=Path, required=True)
    scip_refresh.add_argument("--python-package-json", type=Path, required=True)
    scip_refresh.add_argument(
        "--typescript-indexer-entrypoint", type=Path, required=True
    )
    scip_refresh.add_argument("--typescript-package-json", type=Path, required=True)
    scip_refresh.add_argument("--timeout", type=int, default=180)
    scip_status = subcommands.add_parser(
        "scip-status", help="verify and report the current atomic SCIP store"
    )
    scip_status.add_argument("--store", type=Path, required=True)
    mapper_status = subcommands.add_parser(
        "mapper-status", help="verify and report the current mapper fact store"
    )
    mapper_status.add_argument("--mapper-store", type=Path, required=True)
    mapper_recover = subcommands.add_parser(
        "mapper-recover-compaction",
        help="restore an exactly authenticated externally-compacted CURRENT mapper DB",
    )
    mapper_recover.add_argument("--mapper-store", type=Path, required=True)
    retention_assess = subcommands.add_parser(
        "retention-assess-derived",
        help=(
            "classify navigation, semantic and SCIP retention as a sealed "
            "dry-run without granting mutation authority"
        ),
    )
    retention_assess.add_argument("--inventory-store", type=Path, required=True)
    retention_assess.add_argument("--semantic-store", type=Path, required=True)
    retention_assess.add_argument("--scip-store", type=Path)
    retention_assess.add_argument("--output", type=Path)
    retention_assess.add_argument(
        "--reference-root", type=Path, action="append", default=[]
    )
    lineage_assess = subcommands.add_parser(
        "retention-assess-derived-lineage",
        help=(
            "globally rank derived map payloads across runtime store families "
            "without granting payload-removal authority"
        ),
    )
    lineage_assess.add_argument(
        "--runtime-root", type=Path, action="append", required=True
    )
    lineage_assess.add_argument("--public-output", type=Path)
    lineage_assess.add_argument("--report-output", type=Path)
    lineage_assess.add_argument("--private-ledger-output", type=Path)
    lineage_assess.add_argument(
        "--reference-root", type=Path, action="append", default=[]
    )
    lineage_assess.add_argument("--active-consumer-registry", type=Path)
    lineage_assess.add_argument("--format", choices=("json", "human"), default="json")
    lineage_assess.add_argument("--generated-at")
    retention_verify = subcommands.add_parser(
        "retention-verify-restore-stream",
        help="verify an authenticated compressed generation without restoring it",
    )
    retention_verify.add_argument(
        "--kind", choices=("inventory", "mapper"), required=True
    )
    retention_verify.add_argument("--generation", type=Path, required=True)
    retention_verify.add_argument("--output", type=Path)
    retention_inspect = subcommands.add_parser(
        "retention-inspect-receipt",
        help="authenticate and safely inspect a current or historical retention receipt",
    )
    retention_inspect.add_argument("--receipt", type=Path, required=True)
    retention_inspect.add_argument("--expected-raw-sha256")
    retention_inspect.add_argument(
        "--format", choices=("json", "human"), default="json"
    )
    semantic_compact = subcommands.add_parser(
        "retention-compact-semantic-inactive",
        help="compact one semantic generation outside the newest-three raw window",
    )
    semantic_compact.add_argument("--semantic-store", type=Path, required=True)
    semantic_compact.add_argument("--run-id", required=True)
    semantic_compact.add_argument("--inactive-reason", required=True)
    semantic_restore = subcommands.add_parser(
        "retention-restore-semantic",
        help="restore exact semantic graph payloads while preserving archives",
    )
    semantic_restore.add_argument("--generation", type=Path, required=True)
    semantic_verify = subcommands.add_parser(
        "retention-verify-semantic-restore-stream",
        help="verify semantic archives without installing source payloads",
    )
    semantic_verify.add_argument("--generation", type=Path, required=True)
    semantic_verify.add_argument("--output", type=Path)
    semantic_canary = subcommands.add_parser(
        "retention-canary-semantic-round-trip",
        help="round-trip real semantic bytes in temporary storage only",
    )
    semantic_canary.add_argument("--generation", type=Path, required=True)
    semantic_canary.add_argument("--output", type=Path)
    scip_compact = subcommands.add_parser(
        "retention-compact-scip-inactive",
        help="compact one SCIP generation outside the newest-three raw window",
    )
    scip_compact.add_argument("--scip-store", type=Path, required=True)
    scip_compact.add_argument("--run-id", required=True)
    scip_compact.add_argument("--inactive-reason", required=True)
    scip_restore = subcommands.add_parser(
        "retention-restore-scip",
        help="restore exact SCIP indexes while preserving archives",
    )
    scip_restore.add_argument("--generation", type=Path, required=True)
    scip_verify = subcommands.add_parser(
        "retention-verify-scip-restore-stream",
        help="verify SCIP archives without installing source indexes",
    )
    scip_verify.add_argument("--generation", type=Path, required=True)
    scip_verify.add_argument("--output", type=Path)
    scip_canary = subcommands.add_parser(
        "retention-canary-scip-round-trip",
        help="round-trip real SCIP bytes in temporary storage only",
    )
    scip_canary.add_argument("--generation", type=Path, required=True)
    scip_canary.add_argument("--output", type=Path)
    mapper_query = subcommands.add_parser(
        "mapper-query", help="query authenticated deterministic map views"
    )
    mapper_query.add_argument("query")
    mapper_query.add_argument("--mapper-store", type=Path, required=True)
    mapper_query.add_argument(
        "--view", action="append", dest="views", choices=SUPPORTED_MAPS
    )
    mapper_query.add_argument("--limit", type=int, default=50)
    mapper_query.add_argument("--fact-limit", type=int, default=50)
    mapper_query.add_argument("--without-facts", action="store_true")
    mapper_dossier = subcommands.add_parser(
        "mapper-dossier",
        help="build a compact cross-map dossier for model or human navigation",
    )
    mapper_dossier.add_argument(
        "dossier",
        choices=(
            "architecture",
            "implementation",
            "debugging",
            "consolidation",
            "archaeology",
            "deletion_review",
            "security_review",
            "claim_review",
        ),
    )
    mapper_dossier.add_argument("term", nargs="+")
    mapper_dossier.add_argument("--mapper-store", type=Path, required=True)
    mapper_dossier.add_argument("--limit-per-term", type=int, default=100)
    mapper_dossier.add_argument("--overall-limit", type=int, default=500)
    mapper_dossier.add_argument("--fact-limit", type=int, default=20)
    mapper_dossier.add_argument("--without-semantic", action="store_true")
    mapper_dossier.add_argument("--include-facts", action="store_true")
    mapper_context = subcommands.add_parser(
        "mapper-context",
        help="render ranked source-linked mapper facts inside a deterministic budget",
    )
    mapper_context.add_argument(
        "dossier",
        choices=(
            "architecture",
            "implementation",
            "debugging",
            "consolidation",
            "archaeology",
            "deletion_review",
            "security_review",
            "claim_review",
        ),
    )
    mapper_context.add_argument("term", nargs="+")
    mapper_context.add_argument("--mapper-store", type=Path, required=True)
    mapper_context.add_argument("--token-budget", type=int, default=1000)
    mapper_context.add_argument("--limit-per-term", type=int, default=100)
    mapper_context.add_argument("--candidate-limit", type=int, default=2000)
    mapper_context.add_argument("--fact-limit", type=int, default=20)
    mapper_context.add_argument("--without-semantic", action="store_true")
    mapper_benchmark = subcommands.add_parser(
        "mapper-benchmark",
        help="measure retrieval quality and token reduction against a reviewed corpus",
    )
    mapper_benchmark.add_argument("--mapper-store", type=Path, required=True)
    mapper_benchmark.add_argument("--corpus", type=Path, required=True)
    context_benchmark = subcommands.add_parser(
        "mapper-context-benchmark",
        help="measure fixed-budget ranked context against reviewed symbol anchors",
    )
    context_benchmark.add_argument("--mapper-store", type=Path, required=True)
    context_benchmark.add_argument("--corpus", type=Path, required=True)
    mapper_feed = subcommands.add_parser(
        "mapper-capability-feed",
        help="emit the strict status-only retrospective capability feed",
    )
    mapper_feed.add_argument("--mapper-store", type=Path)
    mapper_feed.add_argument("--schema-version", choices=("v1", "v2"), default="v1")
    mapper_feed.add_argument("--repository-root", type=Path, default=Path("."))
    mapper_feed.add_argument(
        "--evidence-ledger", type=Path, default=DEFAULT_EVIDENCE_LEDGER
    )
    mapper_feed.add_argument("--generated-at", required=True)
    mapper_consult = subcommands.add_parser(
        "mapper-consult",
        help="compile relevant paths and seal the required pre-architecture consultation",
    )
    mapper_consult.add_argument(
        "task_class",
        choices=(
            "architecture",
            "ownership",
            "duplication",
            "consolidation",
            "feature-loss",
        ),
    )
    mapper_consult.add_argument("term", nargs="+")
    mapper_consult.add_argument("--task-id", required=True)
    mapper_consult.add_argument("--root", type=Path, required=True)
    mapper_consult.add_argument("--inventory-store", type=Path, required=True)
    mapper_consult.add_argument("--mapper-store", type=Path, required=True)
    mapper_consult.add_argument("--receipt", type=Path, required=True)
    mapper_consult.add_argument("--path", action="append", default=[])
    mapper_consult.add_argument("--exhaustive", action="store_true")
    mapper_audit = subcommands.add_parser(
        "mapper-audit",
        help="verify provenance, confidence, coverage and all 22 mapper views",
    )
    mapper_audit.add_argument("--mapper-store", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "inventory":
            payload = write_inventory(
                arguments.repository,
                arguments.output,
                InventoryPolicy(
                    admitted_untracked=tuple(sorted(arguments.admit_untracked))
                ),
            )
            print(
                json.dumps(
                    {"status": "PASS", "receipt_sha256": payload["receipt_sha256"]},
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "divergence-map":
            payload = write_cross_worktree_identity_map(
                arguments.canonical,
                arguments.donor,
                arguments.output,
                runtime_roots=arguments.runtime,
            )
            print(
                json.dumps(
                    {
                        "status": payload["status"],
                        "receipt_sha256": payload["receipt_sha256"],
                        "zero_mutation_receipt_sha256": payload["zero_mutation"][
                            "receipt_sha256"
                        ],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "divergence-static-map":
            payload = write_cross_worktree_static_fact_map(
                arguments.canonical,
                arguments.donor,
                arguments.predecessor,
                arguments.output,
                runtime_roots=arguments.runtime,
            )
            print(
                json.dumps(
                    {
                        "status": payload["status"],
                        "receipt_sha256": payload["receipt_sha256"],
                        "zero_mutation_receipt_sha256": payload["zero_mutation"][
                            "receipt_sha256"
                        ],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "divergence-behavior-map":
            payload = write_cross_worktree_behavior_map(
                arguments.canonical,
                arguments.donor,
                arguments.m69,
                arguments.m70,
                arguments.output,
                runtime_roots=arguments.runtime,
                allowed_canonical_m70_drift=arguments.allow_canonical_m70_drift,
            )
            print(
                json.dumps(
                    {
                        "status": payload["status"],
                        "receipt_sha256": payload["receipt_sha256"],
                        "zero_mutation_receipt_sha256": payload["zero_mutation"][
                            "receipt_sha256"
                        ],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "derived-payload-lineage":
            try:
                payload = write_derived_payload_verifier_lineage(
                    arguments.canonical,
                    arguments.donor,
                    arguments.m69,
                    arguments.m70,
                    arguments.m71,
                    arguments.output,
                )
            except (DivergenceError, OSError):
                print(
                    json.dumps(
                        {
                            "status": "REFUSED",
                            "reason": "DERIVED_PAYLOAD_LINEAGE_INPUT_UNAVAILABLE_OR_INVALID",
                        },
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
                return 2
            print(
                json.dumps(
                    {
                        "status": payload["status"],
                        "receipt_sha256": payload["receipt_sha256"],
                        "zero_mutation_receipt_sha256": payload["zero_mutation"][
                            "receipt_sha256"
                        ],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "cli-superset-disposition":
            try:
                payload = write_cli_donor_superset_disposition(
                    arguments.canonical,
                    arguments.m69,
                    arguments.m70,
                    arguments.m71,
                    arguments.output,
                )
            except (DivergenceError, OSError):
                print(
                    json.dumps(
                        {
                            "status": "REFUSED",
                            "reason": "CLI_DONOR_SUPERSET_INPUT_UNAVAILABLE_OR_INVALID",
                        },
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
                return 2
            print(
                json.dumps(
                    {
                        "status": payload["status"],
                        "receipt_sha256": payload["receipt_sha256"],
                        "zero_mutation_receipt_sha256": payload["zero_mutation"][
                            "receipt_sha256"
                        ],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "hypotheses":
            payload = write_hypotheses(
                arguments.inventory, arguments.output,
                ScannerPaths.from_tools_root(arguments.tools_root) if arguments.tools_root else None,
                use_sandbox=not arguments.no_sandbox,
            )
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "receipt_sha256": payload["receipt_sha256"],
                        "observations": payload["summary"]["observations"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "counterevidence":
            payload = write_counterevidence(
                arguments.inventory, arguments.hypotheses, arguments.output
            )
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "receipt_sha256": payload["receipt_sha256"],
                        "counterevidence_present": payload["summary"][
                            "counterevidence_present"
                        ],
                        "counterevidence_unknown": payload["summary"][
                            "counterevidence_unknown"
                        ],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "history":
            payload = write_history(
                arguments.inventory,
                arguments.hypotheses,
                arguments.counterevidence,
                arguments.comparison_repository,
                arguments.output,
            )
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "receipt_sha256": payload["receipt_sha256"],
                        "related_variant_observed": payload["summary"][
                            "related_variant_observed"
                        ],
                        "unknown": payload["summary"]["unknown"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "judge":
            payload = write_judgement(
                arguments.inventory,
                arguments.hypotheses,
                arguments.counterevidence,
                arguments.history,
                arguments.output,
            )
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "receipt_sha256": payload["receipt_sha256"],
                        **payload["summary"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "quarantine-canary":
            payload = write_quarantine_canary(
                arguments.repository,
                arguments.inventory,
                arguments.hypotheses,
                arguments.counterevidence,
                arguments.history,
                arguments.judge,
                arguments.hypothesis_id,
                arguments.output,
            )
            print(
                json.dumps(
                    {
                        "status": payload["status"],
                        "receipt_sha256": payload["receipt_sha256"],
                        "restored": payload["restored"],
                    },
                    sort_keys=True,
                )
            )
            return 0 if payload["status"] == "PASS" else 1
        if arguments.command == "navigation-refresh":
            run = refresh_navigation_inventory(arguments.root, arguments.store, include_paths=arguments.include_path)
            print(
                json.dumps(
                    {
                        "status": run.manifest["status"],
                        "run_id": run.manifest["run_id"],
                        "files": run.manifest["counts"]["files"],
                        "receipt_sha256": run.manifest["receipt_sha256"],
                    },
                    sort_keys=True,
                )
            )
            return 0 if run.manifest["status"] == "CURRENT" else 1
        if arguments.command == "navigation-refresh-delta":
            run = refresh_navigation_inventory_delta(
                arguments.root,
                arguments.store,
                include_paths=tuple(arguments.path),
            )
            print(
                json.dumps(
                    {
                        "status": run.manifest["status"],
                        "scope": run.manifest["scan"]["scope"],
                        "run_id": run.manifest["run_id"],
                        "files": run.manifest["counts"]["files"],
                        "refreshed_paths": run.manifest["counts"]["delta_refreshed"],
                        "deleted_paths": run.manifest["counts"]["delta_deleted"],
                        "receipt_sha256": run.manifest["receipt_sha256"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "navigation-status":
            run = current_navigation_run(arguments.store)
            print(json.dumps(run.manifest, sort_keys=True))
            return 0 if run.manifest["status"] == "CURRENT" else 1
        if arguments.command == "navigation-search":
            rows = search_navigation_inventory(
                arguments.store,
                arguments.query,
                limit=arguments.limit,
                semantic_only=arguments.semantic_only,
            )
            print(json.dumps({"status": "PASS", "results": rows}, sort_keys=True))
            return 0
        if arguments.command == "navigation-locate":
            print(
                json.dumps(
                    locate_navigation_inventory(
                        arguments.store,
                        arguments.query,
                        limit=arguments.limit,
                        semantic_only=arguments.semantic_only,
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "semantic-refresh":
            run = refresh_semantic_graph(
                arguments.inventory_store,
                arguments.semantic_store,
                GraphifyConfig(
                    python=arguments.graphify_python,
                    endpoint=arguments.endpoint,
                    model=arguments.model,
                    max_new_documents=arguments.max_new_documents,
                ),
            )
            print(
                json.dumps(
                    {
                        "status": run.manifest["status"],
                        "run_id": run.manifest["run_id"],
                        "selected": run.manifest["coverage"]["selected"],
                        "supported": run.manifest["coverage"]["supported"],
                        "nodes": run.manifest["graph"]["nodes"],
                        "edges": run.manifest["graph"]["edges"],
                        "receipt_sha256": run.manifest["receipt_sha256"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "semantic-status":
            run = current_semantic_run(arguments.semantic_store)
            print(
                json.dumps(
                    {
                        "status": run.manifest["status"],
                        "run_id": run.manifest["run_id"],
                        "inventory_run_id": run.manifest["inventory"]["run_id"],
                        "finished_at": run.manifest["scan"]["finished_at"],
                        "selected": run.manifest["coverage"]["selected"],
                        "supported": run.manifest["coverage"]["supported"],
                        "documents_selected": run.manifest["coverage"][
                            "documents_selected"
                        ],
                        "documents_total": run.manifest["coverage"]["documents_total"],
                        "nodes": run.manifest["graph"]["nodes"],
                        "edges": run.manifest["graph"]["edges"],
                        "receipt_sha256": run.manifest["receipt_sha256"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "semantic-query":
            print(
                query_semantic_graph(
                    arguments.semantic_store,
                    arguments.question,
                    budget=arguments.budget,
                ),
                end="",
            )
            return 0
        if arguments.command == "semantic-locate":
            print(
                json.dumps(
                    locate_semantic_graph(
                        arguments.semantic_store, arguments.query, limit=arguments.limit
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "semantic-archive-legacy":
            manifest = archive_legacy_graph(
                arguments.legacy_path, arguments.semantic_store
            )
            print(json.dumps(manifest, sort_keys=True))
            return 0
        if arguments.command == "navigation-maintenance":
            scip_values = (
                arguments.scip_store,
                arguments.scip_node,
                arguments.scip_python_indexer_entrypoint,
                arguments.scip_python_package_json,
                arguments.scip_typescript_indexer_entrypoint,
                arguments.scip_typescript_package_json,
            )
            if any(value is not None for value in scip_values) and not all(
                value is not None for value in scip_values
            ):
                raise ScipMapError(
                    "navigation maintenance SCIP configuration must be complete"
                )
            scip = (
                None
                if not all(value is not None for value in scip_values)
                else ScipRefreshConfig(
                    store=arguments.scip_store,
                    node=arguments.scip_node,
                    python_indexer_entrypoint=(
                        arguments.scip_python_indexer_entrypoint
                    ),
                    python_package_json=arguments.scip_python_package_json,
                    typescript_indexer_entrypoint=(
                        arguments.scip_typescript_indexer_entrypoint
                    ),
                    typescript_package_json=(arguments.scip_typescript_package_json),
                    timeout_seconds=arguments.scip_timeout,
                )
            )
            receipt = run_navigation_maintenance(
                arguments.root,
                arguments.inventory_store,
                arguments.semantic_store,
                reason=arguments.reason,
                graphify=GraphifyConfig(
                    python=arguments.graphify_python,
                    endpoint=arguments.endpoint,
                    model=arguments.model,
                    max_new_documents=arguments.max_new_documents,
                ),
                model_server_executable=arguments.model_server_executable,
                model_path=arguments.model_path,
                mapper_store=arguments.mapper_store,
                scip=scip,
                runtime_registries=tuple(arguments.runtime_registry),
                mode=arguments.mode,
            )
            print(json.dumps(receipt, sort_keys=True))
            if arguments.strict and receipt["status"] not in {
                "PASS",
                "SKIPPED_ALREADY_RUNNING",
            }:
                return 2
            return 0
        if arguments.command == "map-catalog":
            if arguments.map_id is None:
                print(json.dumps(build_map_catalog(), sort_keys=True))
                return 0
            try:
                selected = map_by_id(arguments.map_id)
            except KeyError:
                print(
                    json.dumps(
                        {
                            "status": "REFUSED",
                            "reason": f"unknown map: {arguments.map_id}",
                        },
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
                return 2
            print(json.dumps({"status": "PASS", "map": selected}, sort_keys=True))
            return 0
        if arguments.command == "mapper-refresh":
            if arguments.scip_store is not None and arguments.scip_manifest:
                raise ScipMapError(
                    "use either --scip-store or explicit --scip-manifest values"
                )
            scip_manifests = (
                current_scip_store(arguments.scip_store).manifest_paths
                if arguments.scip_store is not None
                else arguments.scip_manifest
            )
            run = refresh_mapper(
                arguments.inventory_store,
                arguments.mapper_store,
                runtime_registries=arguments.runtime_registry,
                semantic_store=arguments.semantic_store,
                scip_manifests=scip_manifests,
            )
            print(
                json.dumps(
                    {
                        "status": run.manifest["status"],
                        "run_id": run.manifest["run_id"],
                        "inventory_run_id": run.manifest["inventory"]["run_id"],
                        "entities": run.manifest["counts"]["entities"],
                        "relations": run.manifest["counts"]["relations"],
                        "receipt_sha256": run.manifest["receipt_sha256"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "scip-build":
            if arguments.language == "typescript":
                compiled = build_typescript_scip_index(
                    arguments.inventory_store,
                    arguments.output,
                    node=arguments.node,
                    indexer_entrypoint=arguments.indexer_entrypoint,
                    package_json=arguments.package_json,
                    project_root=arguments.project_root,
                    timeout_seconds=arguments.timeout,
                )
            else:
                compiled = build_scip_index(
                    arguments.inventory_store,
                    arguments.output,
                    node=arguments.node,
                    indexer_entrypoint=arguments.indexer_entrypoint,
                    package_json=arguments.package_json,
                    timeout_seconds=arguments.timeout,
                )
            print(
                json.dumps(
                    {
                        "status": compiled.manifest["status"],
                        "manifest": str(compiled.manifest_path),
                        "receipt_sha256": compiled.manifest["receipt_sha256"],
                        "index_sha256": compiled.manifest["index"]["sha256"],
                        "counts": compiled.manifest["counts"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "scip-discover":
            print(
                json.dumps(
                    discover_scip_projects(arguments.inventory_store), sort_keys=True
                )
            )
            return 0
        if arguments.command == "scip-refresh":
            run = refresh_scip_store(
                arguments.inventory_store,
                arguments.store,
                node=arguments.node,
                python_indexer_entrypoint=arguments.python_indexer_entrypoint,
                python_package_json=arguments.python_package_json,
                typescript_indexer_entrypoint=(arguments.typescript_indexer_entrypoint),
                typescript_package_json=arguments.typescript_package_json,
                timeout_seconds=arguments.timeout,
            )
            print(
                json.dumps(
                    {
                        "status": run.catalog["status"],
                        "run_id": run.catalog["run_id"],
                        "receipt_sha256": run.catalog["receipt_sha256"],
                        "counts": run.catalog["counts"],
                        "manifests": [str(path) for path in run.manifest_paths],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "scip-status":
            print(
                json.dumps(current_scip_store(arguments.store).catalog, sort_keys=True)
            )
            return 0
        if arguments.command == "mapper-status":
            print(
                json.dumps(
                    current_mapper_run(arguments.mapper_store).manifest, sort_keys=True
                )
            )
            return 0
        if arguments.command == "mapper-recover-compaction":
            print(
                json.dumps(
                    recover_current_compacted_mapper(arguments.mapper_store),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "retention-assess-derived":
            assessment = (
                assess_derived_family_retention(
                    arguments.inventory_store,
                    arguments.semantic_store,
                    scip_store=arguments.scip_store,
                    reference_roots=tuple(arguments.reference_root),
                )
                if arguments.output is None
                else write_derived_family_retention_assessment(
                    arguments.inventory_store,
                    arguments.semantic_store,
                    arguments.output,
                    scip_store=arguments.scip_store,
                    reference_roots=tuple(arguments.reference_root),
                )
            )
            print(
                json.dumps(
                    assessment,
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "retention-assess-derived-lineage":
            generated_at = _parse_generated_at(arguments.generated_at)
            active_registry = (
                None
                if arguments.active_consumer_registry is None
                else read_active_consumer_registry(arguments.active_consumer_registry)
            )
            if (
                arguments.public_output is None
                and arguments.report_output is None
                and arguments.private_ledger_output is None
            ):
                assessment = assess_cross_store_derived_map_lineage(
                    tuple(arguments.runtime_root),
                    reference_roots=tuple(arguments.reference_root),
                    active_consumer_registry=active_registry,
                    now=generated_at,
                )
            else:
                assessment = write_cross_store_derived_map_lineage_assessment(
                    tuple(arguments.runtime_root),
                    public_output=arguments.public_output,
                    report_output=arguments.report_output,
                    private_ledger_output=arguments.private_ledger_output,
                    reference_roots=tuple(arguments.reference_root),
                    active_consumer_registry=active_registry,
                    now=generated_at,
                )
            print(
                render_cross_store_derived_map_lineage_report(assessment)
                if arguments.format == "human"
                else json.dumps(assessment, sort_keys=True)
            )
            return 0
        if arguments.command == "retention-verify-restore-stream":
            verification = (
                verify_compacted_generation_restore_stream(
                    arguments.kind, arguments.generation
                )
                if arguments.output is None
                else write_compacted_generation_restore_verification(
                    arguments.kind, arguments.generation, arguments.output
                )
            )
            print(json.dumps(verification, sort_keys=True))
            return 0
        if arguments.command == "retention-inspect-receipt":
            inspection = inspect_retention_receipt(
                arguments.receipt,
                expected_raw_sha256=arguments.expected_raw_sha256,
            )
            print(
                render_retention_receipt_inspection(inspection)
                if arguments.format == "human"
                else json.dumps(inspection, sort_keys=True)
            )
            return 0
        if arguments.command == "retention-compact-semantic-inactive":
            print(
                json.dumps(
                    compact_inactive_semantic_generation(
                        arguments.semantic_store,
                        arguments.run_id,
                        inactive_reason=arguments.inactive_reason,
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "retention-restore-semantic":
            print(
                json.dumps(
                    restore_compacted_semantic_generation(arguments.generation),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "retention-verify-semantic-restore-stream":
            verification = (
                verify_semantic_compacted_generation_restore_stream(
                    arguments.generation
                )
                if arguments.output is None
                else write_semantic_restore_stream_verification(
                    arguments.generation, arguments.output
                )
            )
            print(json.dumps(verification, sort_keys=True))
            return 0
        if arguments.command == "retention-canary-semantic-round-trip":
            canary = (
                run_semantic_round_trip_canary(arguments.generation)
                if arguments.output is None
                else write_semantic_round_trip_canary(
                    arguments.generation, arguments.output
                )
            )
            print(json.dumps(canary, sort_keys=True))
            return 0
        if arguments.command == "retention-compact-scip-inactive":
            print(
                json.dumps(
                    compact_inactive_scip_generation(
                        arguments.scip_store,
                        arguments.run_id,
                        inactive_reason=arguments.inactive_reason,
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "retention-restore-scip":
            print(
                json.dumps(
                    restore_compacted_scip_generation(arguments.generation),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "retention-verify-scip-restore-stream":
            verification = (
                verify_scip_compacted_generation_restore_stream(arguments.generation)
                if arguments.output is None
                else write_scip_restore_stream_verification(
                    arguments.generation, arguments.output
                )
            )
            print(json.dumps(verification, sort_keys=True))
            return 0
        if arguments.command == "retention-canary-scip-round-trip":
            canary = (
                run_scip_round_trip_canary(arguments.generation)
                if arguments.output is None
                else write_scip_round_trip_canary(
                    arguments.generation, arguments.output
                )
            )
            print(json.dumps(canary, sort_keys=True))
            return 0
        if arguments.command == "mapper-query":
            route = route_query_maps(
                arguments.query,
                requested_maps=tuple(arguments.views) if arguments.views else None,
            )
            print(
                json.dumps(
                    query_mapper(
                        arguments.mapper_store,
                        arguments.query,
                        maps=route["selected_maps"],
                        search_query=route["search_query"],
                        limit=arguments.limit,
                        fact_limit=arguments.fact_limit,
                        include_facts=not arguments.without_facts,
                        routing=route,
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "mapper-dossier":
            print(
                json.dumps(
                    build_dossier(
                        arguments.mapper_store,
                        arguments.dossier,
                        arguments.term,
                        limit_per_term=arguments.limit_per_term,
                        overall_limit=arguments.overall_limit,
                        fact_limit=arguments.fact_limit,
                        include_semantic=not arguments.without_semantic,
                        include_facts=arguments.include_facts,
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "mapper-context":
            print(
                json.dumps(
                    build_context_projection(
                        arguments.mapper_store,
                        arguments.dossier,
                        arguments.term,
                        token_budget=arguments.token_budget,
                        limit_per_term=arguments.limit_per_term,
                        candidate_limit=arguments.candidate_limit,
                        fact_limit=arguments.fact_limit,
                        include_semantic=not arguments.without_semantic,
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "mapper-benchmark":
            result = run_mapper_benchmark(arguments.mapper_store, arguments.corpus)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "PASS" else 1
        if arguments.command == "mapper-context-benchmark":
            result = run_context_benchmark(arguments.mapper_store, arguments.corpus)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "PASS" else 1
        if arguments.command == "mapper-capability-feed":
            if arguments.schema_version == "v1":
                if arguments.mapper_store is None:
                    raise CapabilityFeedError(
                        "mapper-capability-feed v1 needs mapper-store"
                    )
                payload = build_retrospective_capability_feed(
                    arguments.mapper_store, generated_at=arguments.generated_at
                )
            else:
                payload = build_reviewed_archaeologist_v2_capability_feed(
                    arguments.repository_root,
                    generated_at=arguments.generated_at,
                    evidence_ledger=arguments.evidence_ledger,
                )
            print(
                json.dumps(
                    payload,
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "mapper-consult":
            receipt = consult_before_decision(
                arguments.root,
                arguments.inventory_store,
                arguments.mapper_store,
                task_id=arguments.task_id,
                task_class=arguments.task_class,
                terms=tuple(arguments.term),
                receipt_path=arguments.receipt,
                relevant_paths=tuple(arguments.path),
                exhaustive=arguments.exhaustive,
            )
            print(json.dumps(receipt, sort_keys=True))
            return 0 if receipt["status"] == "READY_FOR_BOUNDED_DECISION" else 1
        if arguments.command == "mapper-audit":
            audit = audit_mapper(arguments.mapper_store)
            print(json.dumps(audit, sort_keys=True))
            return 0 if audit["status"] == "PASS" else 1
    except (
        CounterevidenceError,
        DossierError,
        HistoryError,
        HypothesisError,
        InventoryError,
        NavigationInventoryError,
        NavigationMaintenanceError,
        MapperError,
        SemanticGraphError,
        JudgeError,
        QuarantineError,
        BenchmarkError,
        CapabilityFeedError,
        ConsultationError,
        ScipMapError,
        RetentionError,
        DivergenceError,
    ) as exc:
        print(
            json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
