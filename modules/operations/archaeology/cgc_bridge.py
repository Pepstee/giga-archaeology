"""Isolated CodeGraphContext adapter used only inside a scanner sandbox.

CodeGraphContext normally bootstraps ``~/.codegraphcontext``.  Archaeology
must not create global state, so this bridge rebinds every configuration path
to the caller's private scratch directory before importing the indexing
helpers.  It indexes only the already-filtered external source projection.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def _rebind_config(config_root: Path) -> None:
    from codegraphcontext.cli import config_manager

    old_root = config_manager.CONFIG_DIR
    for name, value in tuple(vars(config_manager).items()):
        if isinstance(value, Path):
            try:
                relative = value.relative_to(old_root)
            except ValueError:
                continue
            setattr(config_manager, name, config_root / relative)
    defaults = dict(config_manager.DEFAULT_CONFIG)
    for key, value in defaults.items():
        if isinstance(value, str) and value.startswith(str(old_root)):
            defaults[key] = str(config_root) + value[len(str(old_root)) :]
    config_manager.DEFAULT_CONFIG = defaults
    if config_manager.CONFIG_DIR != config_root:
        raise RuntimeError("CodeGraphContext configuration root was not isolated")


def run(projection: Path, config_root: Path, database: Path, output: Path) -> None:
    projection = projection.resolve(strict=True)
    config_root = config_root.resolve(strict=False)
    database = database.resolve(strict=False)
    output = output.resolve(strict=False)
    _rebind_config(config_root)
    os.environ["CGC_RUNTIME_DB_TYPE"] = "kuzudb"
    os.environ["CGC_RUNTIME_DB_PATH"] = str(database)
    os.environ["CGC_IGNORE_PROJECT_ENV"] = "1"
    os.environ["ENABLE_AUTO_WATCH"] = "false"

    from codegraphcontext.cli.cli_helpers import _initialize_services, index_helper

    index_helper(str(projection), no_progress=True)
    services = _initialize_services(None, cwd=projection)
    database_manager, _builder, finder = services[:3]
    try:
        result: dict[str, Any] = finder.find_dead_code(
            repo_path=projection.as_posix(), limit=None, include_low_confidence=True
        )
    finally:
        database_manager.close_driver()
    output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--config-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.projection, args.config_root, args.database, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
