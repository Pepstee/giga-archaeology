"""Compatibility entrypoint for the renamed ``giga-archaeology`` command."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from modules.operations.scripts.archaeology import main as _main


def main(argv: list[str] | None = None) -> int:
    return _main(argv, prog="giga-archaeologist")


if __name__ == "__main__":
    raise SystemExit(main())
