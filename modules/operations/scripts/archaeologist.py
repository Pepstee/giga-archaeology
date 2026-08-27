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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="giga-archaeologist")
    subcommands = parser.add_subparsers(dest="command", required=True)
    inventory = subcommands.add_parser("inventory", help="produce a read-only immutable inventory")
    inventory.add_argument("--repository", type=Path, required=True)
    inventory.add_argument("--output", type=Path, required=True)
    inventory.add_argument("--admit-untracked", action="append", default=[])
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
    except InventoryError as exc:
        print(
            json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr
        )
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
