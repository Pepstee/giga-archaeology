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
from modules.operations.archaeologist.hypotheses import HypothesisError, write_hypotheses
from modules.operations.archaeologist.history import HistoryError, write_history
from modules.operations.archaeologist.counterevidence import (
    CounterevidenceError,
    write_counterevidence,
)
from modules.operations.archaeologist.judge import JudgeError, write_judgement
from modules.operations.archaeologist.quarantine import QuarantineError, write_quarantine_canary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="giga-archaeologist")
    subcommands = parser.add_subparsers(dest="command", required=True)
    inventory = subcommands.add_parser("inventory", help="produce a read-only immutable inventory")
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
        "history", help="compare Git history and a second repository without executing code"
    )
    history.add_argument("--inventory", type=Path, required=True)
    history.add_argument("--hypotheses", type=Path, required=True)
    history.add_argument("--counterevidence", type=Path, required=True)
    history.add_argument("--comparison-repository", type=Path, required=True)
    history.add_argument("--output", type=Path, required=True)
    judge = subcommands.add_parser(
        "judge", help="classify hypotheses with deterministic fail-closed evidence gates"
    )
    judge.add_argument("--inventory", type=Path, required=True)
    judge.add_argument("--hypotheses", type=Path, required=True)
    judge.add_argument("--counterevidence", type=Path, required=True)
    judge.add_argument("--history", type=Path, required=True)
    judge.add_argument("--output", type=Path, required=True)
    quarantine = subcommands.add_parser(
        "quarantine-canary", help="quarantine one verified candidate in a disposable fixture"
    )
    quarantine.add_argument("--repository", type=Path, required=True)
    quarantine.add_argument("--inventory", type=Path, required=True)
    quarantine.add_argument("--hypotheses", type=Path, required=True)
    quarantine.add_argument("--counterevidence", type=Path, required=True)
    quarantine.add_argument("--history", type=Path, required=True)
    quarantine.add_argument("--judge", type=Path, required=True)
    quarantine.add_argument("--hypothesis-id", required=True)
    quarantine.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "inventory":
            payload = write_inventory(
                arguments.repository,
                arguments.output,
                InventoryPolicy(admitted_untracked=tuple(sorted(arguments.admit_untracked))),
            )
            print(
                json.dumps(
                    {"status": "PASS", "receipt_sha256": payload["receipt_sha256"]}, sort_keys=True
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
                        "counterevidence_present": payload["summary"]["counterevidence_present"],
                        "counterevidence_unknown": payload["summary"]["counterevidence_unknown"],
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
                        "related_variant_observed": payload["summary"]["related_variant_observed"],
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
    except (
        CounterevidenceError,
        HistoryError,
        HypothesisError,
        InventoryError,
        JudgeError,
        QuarantineError,
    ) as exc:
        print(
            json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr
        )
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
