from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path


def test_legacy_package_resolves_to_canonical_module_objects() -> None:
    canonical = importlib.import_module("modules.operations.archaeology.mapper")
    legacy = importlib.import_module("modules.operations.archaeologist.mapper")

    assert legacy is canonical
    assert legacy.__name__ == "modules.operations.archaeology.mapper"


def test_canonical_and_compatibility_entrypoints_are_equivalent(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    commands = (
        root / "modules/operations/scripts/archaeology.py",
        root / "modules/operations/scripts/archaeologist.py",
    )
    outputs = []
    for command in commands:
        result = subprocess.run(
            [sys.executable, str(command), "map-catalog", "--map", "symbols"],
            cwd=tmp_path,
            env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        outputs.append(json.loads(result.stdout))

    assert outputs[0] == outputs[1]
