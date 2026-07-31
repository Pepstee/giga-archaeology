#!/usr/bin/env python3
"""Audit the giga-user top level against its ownership-zone contract."""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = DEFAULT_ROOT / "architecture" / "root-layout.v1.json"


def load_contract(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def audit(root: Path, contract: dict) -> tuple[list[str], list[str], list[str]]:
    classified: set[str] = set()
    for zone in contract["zones"].values():
        classified.update(zone.get("paths", []))

    legacy = set(contract.get("legacy_root_exceptions", []))
    ignored_patterns = contract.get("ignored_root_patterns", [])
    entries = sorted(path.name for path in root.iterdir())

    unknown = [
        name
        for name in entries
        if name not in classified
        and name not in legacy
        and not any(fnmatch.fnmatch(name, pattern) for pattern in ignored_patterns)
    ]
    present_legacy = sorted(name for name in legacy if (root / name).exists())
    missing_registry_paths: list[str] = []

    registry_path = root / contract["zones"]["projects"]["registry"]
    if registry_path.exists():
        registry = load_contract(registry_path)
        missing_registry_paths = sorted(
            project["path"]
            for project in registry["projects"]
            if not (root / project["path"]).exists()
        )
    else:
        missing_registry_paths.append(str(registry_path.relative_to(root)))

    return unknown, present_legacy, missing_registry_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--strict-legacy",
        action="store_true",
        help="also fail while legacy root exceptions remain",
    )
    args = parser.parse_args()

    contract = load_contract(args.contract)
    unknown, legacy, missing = audit(args.root.resolve(), contract)

    print(f"root: {args.root.resolve()}")
    print(f"unclassified: {len(unknown)}")
    for name in unknown:
        print(f"  UNKNOWN {name}")
    print(f"legacy exceptions: {len(legacy)}")
    for name in legacy:
        print(f"  LEGACY  {name}")
    print(f"missing project paths: {len(missing)}")
    for name in missing:
        print(f"  MISSING {name}")

    return int(bool(unknown or missing or (args.strict_legacy and legacy)))


if __name__ == "__main__":
    raise SystemExit(main())
