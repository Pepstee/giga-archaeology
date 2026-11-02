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


def _summarize_scan_errors(values: list[object]) -> list[dict[str, object]]:
    counts: Counter[tuple[str, int | None, str | None]] = Counter()
    allowed_identity_fields = {"st_dev", "st_ino"}

    for value in values:
        if value == "identity-changed-before-read":
            counts[("identity-changed-before-read", None, None)] += 1
        elif isinstance(value, str) and value.startswith("identity-changed-before-read:"):
            fields = value.partition(":")[2].split(",")
            if fields and all(field in allowed_identity_fields for field in fields):
                for field in set(fields):
                    counts[("identity-changed-before-read", None, field)] += 1
            else:
                counts[("other", None, None)] += 1
        elif value == "root-identity-changed-during-scan":
            counts[("root-identity-change", None, None)] += 1
        elif value == "git-status-changed-during-scan":
            counts[("git-status-change", None, None)] += 1
        elif isinstance(value, str):
            match = re.fullmatch(r"(read|readlink|stat):([0-9]+)", value)
            if match:
                counts[(match.group(1), int(match.group(2)), None)] += 1
            else:
                stat_match = re.search(r":stat:([0-9]+)$", value)
                if stat_match:
                    counts[("stat", int(stat_match.group(1)), None)] += 1
                else:
                    counts[("other", None, None)] += 1
        else:
            counts[("other", None, None)] += 1

    return [
        {"category": category, "errno": errno, "field": field, "count": count}
        for (category, errno, field), count in sorted(
            counts.items(),
            key=lambda item: (
                item[0][0],
                item[0][1] if item[0][1] is not None else -1,
                item[0][2] or "",
            ),
        )
    ]


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

    failures = manifest.get("failures", [])
    if not isinstance(failures, list):
        failures = []
    diagnostic_errors = list(failures)
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
        diagnostic_errors = [scan_error for (scan_error,) in rows]
        diagnostic_errors.extend(
            failure
            for failure in failures
            if failure in {
                "root-identity-changed-during-scan",
                "git-status-changed-during-scan",
            }
        )
        scan_errors_available = True
    except (OSError, sqlite3.Error, TypeError, ValueError):
        pass

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
        "failure_reasons": _summarize_scan_errors(diagnostic_errors),
        "scan_errors_available": scan_errors_available,
        "git_stable_during_scan": stable,
    }


def test_scan_error_summary_exposes_only_identity_field_names() -> None:
    summary = _summarize_scan_errors(
        [
            "identity-changed-before-read:st_dev,st_ino",
            "C:\\Users\\private\\sample.py:read:13",
        ]
    )
    assert summary == [
        {
            "category": "identity-changed-before-read",
            "errno": None,
            "field": "st_dev",
            "count": 1,
        },
        {
            "category": "identity-changed-before-read",
            "errno": None,
            "field": "st_ino",
            "count": 1,
        },
        {"category": "other", "errno": None, "field": None, "count": 1},
    ]
    assert "C:\\Users\\private" not in json.dumps(summary)
    assert "13" not in json.dumps(summary)


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
