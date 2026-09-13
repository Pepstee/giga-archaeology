"""Command surface for the read-only GIGA Archaeologist pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from modules.operations.archaeologist.inventory import (
    InventoryError,
    InventoryPolicy,
    write_inventory,
)
from modules.operations.archaeologist.hypotheses import (
    HypothesisError,
    write_hypotheses,
)
from modules.operations.archaeologist.history import HistoryError, write_history
from modules.operations.archaeologist.counterevidence import (
    CounterevidenceError,
    write_counterevidence,
)
from modules.operations.archaeologist.judge import JudgeError, write_judgement
from modules.operations.archaeologist.quarantine import (
    QuarantineError,
    write_quarantine_canary,
)
from modules.operations.archaeologist.navigation_inventory import (
    NavigationInventoryError,
    current_navigation_run,
    locate_navigation_inventory,
    refresh_navigation_inventory,
    search_navigation_inventory,
)
from modules.operations.archaeologist.semantic_graph import (
    GraphifyConfig,
    SemanticGraphError,
    archive_legacy_graph,
    current_semantic_run,
    locate_semantic_graph,
    query_semantic_graph,
    refresh_semantic_graph,
)
from modules.operations.archaeologist.navigation_maintenance import (
    NavigationMaintenanceError,
    run_navigation_maintenance,
)
from modules.operations.archaeologist.retention import (
    RetentionError,
    RetentionPolicy,
    run_navigation_retention,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="giga-archaeologist")
    subcommands = parser.add_subparsers(dest="command", required=True)
    inventory = subcommands.add_parser(
        "inventory", help="produce a read-only immutable inventory"
    )
    inventory.add_argument("--repository", type=Path, required=True)
    inventory.add_argument("--output", type=Path, required=True)
    inventory.add_argument("--admit-untracked", action="append", default=[])
    hypotheses = subcommands.add_parser(
        "hypotheses", help="run isolated scanners and preserve OBSERVED hypotheses"
    )
    hypotheses.add_argument("--inventory", type=Path, required=True)
    hypotheses.add_argument("--output", type=Path, required=True)
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
    maintenance.add_argument("--reason", required=True)
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
    retention = subcommands.add_parser(
        "navigation-retention",
        help="plan or safely apply retention to stale navigation-map generations",
    )
    retention.add_argument("--inventory-store", type=Path, required=True)
    retention.add_argument("--semantic-store", type=Path, required=True)
    retention.add_argument("--mapper-store", type=Path)
    retention.add_argument("--reference-root", type=Path, action="append", default=[])
    retention.add_argument("--apply", action="store_true")
    retention.add_argument("--keep-successes", type=int, default=3)
    retention.add_argument("--keep-failures", type=int, default=2)
    retention.add_argument("--min-age-seconds", type=int, default=24 * 60 * 60)
    retention.add_argument(
        "--quarantine-grace-seconds", type=int, default=7 * 24 * 60 * 60
    )
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
        if arguments.command == "hypotheses":
            payload = write_hypotheses(arguments.inventory, arguments.output)
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
            run = refresh_navigation_inventory(arguments.root, arguments.store)
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
            )
            print(json.dumps(receipt, sort_keys=True))
            if arguments.strict and receipt["status"] not in {
                "PASS",
                "SKIPPED_ALREADY_RUNNING",
            }:
                return 2
            return 0
        if arguments.command == "navigation-retention":
            receipt = run_navigation_retention(
                arguments.inventory_store,
                arguments.mapper_store,
                arguments.semantic_store,
                reference_roots=tuple(arguments.reference_root),
                policy=RetentionPolicy(
                    keep_successes=arguments.keep_successes,
                    keep_failures=arguments.keep_failures,
                    min_age_seconds=arguments.min_age_seconds,
                    quarantine_grace_seconds=arguments.quarantine_grace_seconds,
                ),
                apply=arguments.apply,
            )
            print(json.dumps(receipt, sort_keys=True))
            return 0
    except (
        CounterevidenceError,
        HistoryError,
        HypothesisError,
        InventoryError,
        NavigationInventoryError,
        NavigationMaintenanceError,
        RetentionError,
        SemanticGraphError,
        JudgeError,
        QuarantineError,
    ) as exc:
        print(
            json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
