#!/usr/bin/env python3
"""Create the private runtime hierarchy for life-logging audio processing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SUBDIRECTORIES = (
    "recordings/inbox",
    "recordings/archive",
    "processing",
    "outputs/packages",
    "outbox/giga",
    "state",
)


def default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def bootstrap(root: Path) -> dict[str, object]:
    root = root.expanduser().resolve()
    created: list[str] = []
    for relative in SUBDIRECTORIES:
        target = root / relative
        if not target.exists():
            target.mkdir(parents=True)
            created.append(relative)
        elif not target.is_dir():
            raise NotADirectoryError(f"runtime path is not a directory: {target}")

    receipt = {
        "schema_version": "giga.life-logging.audio-bootstrap.v1",
        "root": str(root),
        "created": created,
        "paths": {relative: str(root / relative) for relative in SUBDIRECTORIES},
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create private life-logging audio runtime directories"
    )
    parser.add_argument("--root", type=Path, default=default_root())
    args = parser.parse_args()
    bootstrap(args.root)


if __name__ == "__main__":
    main()
