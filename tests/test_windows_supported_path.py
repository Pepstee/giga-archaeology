"""End-to-end portability coverage for the supported local mapping path."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _cli(*arguments: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "modules.operations.scripts.archaeology", *arguments],
        cwd=SOURCE_ROOT,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_supported_scan_maps_and_queries_a_committed_python_repository(tmp_path: Path) -> None:
    repository = tmp_path / "source repository"
    repository.mkdir()
    (repository / "sample.py").write_text(
        "def parse_record(value):\n    return value.strip()\n",
        encoding="utf-8",
    )
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "Archaeology test")
    _git(repository, "config", "user.email", "<redacted-email>")
    _git(repository, "add", "sample.py")
    _git(repository, "commit", "--quiet", "-m", "fixture")

    inventory_store = tmp_path / "private inventory"
    mapper_store = tmp_path / "private maps"
    inventory = _cli(
        "navigation-refresh",
        "--root",
        str(repository),
        "--store",
        str(inventory_store),
    )
    assert json.loads(inventory)["status"] == "CURRENT"

    mapped = _cli(
        "mapper-refresh",
        "--inventory-store",
        str(inventory_store),
        "--mapper-store",
        str(mapper_store),
    )
    assert json.loads(mapped)["status"] == "CURRENT"

    query = _cli(
        "mapper-query",
        "--mapper-store",
        str(mapper_store),
        "--view",
        "symbols",
        "--limit",
        "10",
        "--without-facts",
        "parse_record",
    )
    query_result = json.loads(query)
    assert query_result["status"] == "PASS"
    assert "parse_record" in query
