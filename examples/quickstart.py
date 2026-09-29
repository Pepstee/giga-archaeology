#!/usr/bin/env python3
"""Run the documented local inventory, map, query, and context workflow."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a local Archaeology map and print source-linked context."
    )
    parser.add_argument("repository", type=Path, help="root of a committed Git repository")
    parser.add_argument(
        "store", type=Path, help="new or empty output directory outside the repository"
    )
    parser.add_argument(
        "terms", nargs="+", help="terms; first is symbol query, all are used for context"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if shutil.which("git") is None:
        parser.error("Git must be installed and available on PATH")

    repository = args.repository.expanduser().resolve()
    store = args.store.expanduser().resolve()
    if not repository.is_dir():
        parser.error(f"repository directory does not exist: {repository}")
    try:
        git_root = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        parser.error(f"not a Git repository: {repository}")
    if Path(git_root).resolve() != repository:
        parser.error(f"use the Git root, not a subdirectory: {git_root}")

    if store == repository or store.is_relative_to(repository):
        parser.error("store must be outside the repository to keep generated evidence separate")
    if repository.is_relative_to(store):
        parser.error("store must not contain the repository")
    if store.exists() and (not store.is_dir() or any(store.iterdir())):
        parser.error("store must be a new or empty directory; existing data is never overwritten")
    store.mkdir(parents=True, exist_ok=True)

    inventory_store = store / "inventory"
    mapper_store = store / "maps"
    query = args.terms[0]
    commands = (
        ("Inventory the repository", "navigation.json", [
            "navigation-refresh", "--root", str(repository), "--store", str(inventory_store),
        ]),
        ("Build the structural maps", "mapper.json", [
            "mapper-refresh", "--inventory-store", str(inventory_store),
            "--mapper-store", str(mapper_store),
        ]),
        ("Query symbols", "query.json", [
            "mapper-query", query, "--mapper-store", str(mapper_store),
            "--view", "symbols", "--limit", "10", "--without-facts",
        ]),
        ("Render bounded context", "context.json", [
            "mapper-context", "implementation", *args.terms,
            "--mapper-store", str(mapper_store), "--token-budget", "1200",
            "--without-semantic",
        ]),
    )
    example_dir = Path(__file__).resolve().parent
    for label, filename, command_args in commands:
        print(f"\n== {label} ==", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "modules.operations.scripts.archaeology", *command_args],
                cwd=example_dir,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as error:
            print(f"Could not start Archaeology: {error}", file=sys.stderr)
            return 1
        if result.returncode:
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            print(f"Stopped after {label}; command exited {result.returncode}.", file=sys.stderr)
            return result.returncode
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            print(f"{label} returned invalid JSON: {error}", file=sys.stderr)
            return 1
        (store / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        status = payload.get("status", "UNKNOWN") if isinstance(payload, dict) else "UNKNOWN"
        if filename == "navigation.json" and isinstance(payload, dict):
            print(f"Status: {status}; files admitted: {payload.get('files', 'unknown')}")
        elif filename == "mapper.json" and isinstance(payload, dict):
            print(
                f"Status: {status}; entities: {payload.get('entities', 'unknown')}; "
                f"relations: {payload.get('relations', 'unknown')}"
            )
        elif filename == "query.json" and isinstance(payload, dict):
            rows = payload.get("results", [])
            count = len(rows) if isinstance(rows, list) else "unknown"
            print(f"Status: {status}; symbol results: {count}; query: {query}")
        elif filename == "context.json" and isinstance(payload, dict):
            context = payload.get("context", "")
            if isinstance(context, str) and context:
                print(context)
            else:
                print(f"Status: {status}; no context matched those terms.")
        print(f"Full evidence: {store / filename}")

    print(f"\nEvidence stores: {store}")
    print("Map receipts and context can contain source code and absolute paths; keep the output private.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
