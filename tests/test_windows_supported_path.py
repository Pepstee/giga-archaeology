"""End-to-end portability coverage for the supported local mapping path."""
from __future__ import annotations

from collections import Counter
import json
import os
import re
import sqlite3
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
    installed_cli = os.environ.get("GIGA_ARCHAEOLOGY_CLI")
    command = (
        [installed_cli, *arguments]
        if installed_cli
        else [sys.executable, "-m", "modules.operations.scripts.archaeology", *arguments]
    )
    result = subprocess.run(
        command,
        cwd=SOURCE_ROOT,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _navigation_diagnostic(store: Path) -> dict[str, object]:
    """Return pathless scan diagnostics suitable for hosted CI logs."""
    try:
        pointer = json.loads((store / "CURRENT.json").read_text(encoding="utf-8"))
        run_id = pointer.get("run_id")
        if not isinstance(run_id, str) or not run_id or "/" in run_id or "\\" in run_id:
            return {"available": False}
        manifest = json.loads(
            (store / "runs" / run_id / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, TypeError, ValueError):
        return {"available": False}

    reason_counts: Counter[tuple[str, int | None]] = Counter()
    fallback_reason_counts: Counter[tuple[str, int | None]] = Counter()

    def record_error(
        target: Counter[tuple[str, int | None]], value: object
    ) -> None:
        if value == "identity-changed-before-read":
            target[("identity-changed-before-read", None)] += 1
        elif value == "changed-during-read":
            target[("changed-during-read", None)] += 1
        elif isinstance(value, str):
            match = re.fullmatch(r"(read|readlink|stat):([0-9]+)", value)
            if match:
                target[(match.group(1), int(match.group(2)))] += 1
            else:
                stat_match = re.search(r":stat:([0-9]+)$", value)
                if stat_match:
                    target[("stat", int(stat_match.group(1)))] += 1
                else:
                    target[("other", None)] += 1
        else:
            target[("other", None)] += 1

    failures = manifest.get("failures", [])
    if isinstance(failures, list):
        for failure in failures:
            record_error(fallback_reason_counts, failure)

    scan_errors_available = False
    database = store / "runs" / run_id / "inventory.sqlite3"
    try:
        connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "SELECT scan_error FROM files WHERE scan_error IS NOT NULL"
            ).fetchall()
        finally:
            connection.close()
        for (scan_error,) in rows:
            record_error(reason_counts, scan_error)
        scan_errors_available = True
    except (OSError, sqlite3.Error, TypeError, ValueError):
        pass
    if not scan_errors_available:
        reason_counts = fallback_reason_counts

    scan = manifest.get("scan", {})
    scope = scan.get("scope") if isinstance(scan, dict) else None
    if not isinstance(scope, str) or scope not in {
        "all-working-tree-files",
        "explicit-file-allowlist",
    }:
        scope = "unknown"
    counts = manifest.get("counts", {})
    errors = counts.get("errors") if isinstance(counts, dict) else None
    git = manifest.get("git", {})
    stable = git.get("stable_during_scan") if isinstance(git, dict) else None
    if stable not in (True, False, None):
        stable = "unknown"
    status = manifest.get("status")
    if status not in {"CURRENT", "PARTIAL"}:
        status = "unknown"
    return {
        "available": True,
        "status": status,
        "scope": scope,
        "errors": errors if isinstance(errors, int) and not isinstance(errors, bool) else "unknown",
        "failure_reasons": [
            {"category": category, "errno": errno, "count": count}
            for (category, errno), count in sorted(
                reason_counts.items(), key=lambda item: (item[0][0], item[0][1] or -1)
            )
        ],
        "scan_errors_available": scan_errors_available,
        "git_stable_during_scan": stable,
    }


def test_supported_scan_maps_and_queries_a_committed_python_repository(tmp_path: Path) -> None:
    repository = tmp_path / "source repository"
    repository.mkdir()
    (repository / "sample.py").write_text(
        "def parse_record(value):\n    return value.strip()\n",
        encoding="utf-8",
    )
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "Archaeology test")
    _git(repository, "config", "user.email", "archaeology-test@example.invalid")
    _git(repository, "add", "sample.py")
    _git(repository, "commit", "--quiet", "-m", "fixture")

    inventory_store = tmp_path / "private inventory"
    mapper_store = tmp_path / "private maps"
    try:
        inventory = _cli(
            "navigation-refresh",
            "--root",
            str(repository),
            "--store",
            str(inventory_store),
        )
    except AssertionError as exc:
        diagnostic = json.dumps(_navigation_diagnostic(inventory_store), sort_keys=True)
        raise AssertionError(f"{exc}\nNavigation scan diagnostic: {diagnostic}") from None
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
