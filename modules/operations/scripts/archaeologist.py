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
from modules.operations.archaeologist.counterevidence import (
    CounterevidenceError,
    write_counterevidence,
)


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
    except (CounterevidenceError, HypothesisError, InventoryError) as exc:
        print(
            json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr
        )
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
