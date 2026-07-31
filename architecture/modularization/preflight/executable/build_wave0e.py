#!/usr/bin/env python3
"""Build the Wave 0E worktree-promotion and live-writer manifests.

This inventory is metadata-only.  It never opens a candidate repository file:
classification uses Git path/status metadata, file size, process command lines,
and launchd labels.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ALLOWLIST = HERE / "WORKTREE_PROMOTION_ALLOWLIST.json"
WRITER_GATE = HERE / "LIVE_WRITER_GATE.json"

ALLOWED_CATEGORIES = {
    "source_authority",
    "generated",
    "runtime",
    "private_raw",
    "credential_secret",
    "cache",
    "external",
    "historical",
    "unresolved",
}
PROMOTABLE = {"source_authority", "historical"}

GENERATED_SEGMENTS = {
    "compiled-full-results-2026-07-28",
    "compiled-full-results-2026-07-28-v2",
    "compiled-full-results-2026-07-28-v3",
    "compiled-full-results-2026-07-28-v4",
    "compiled-pilot-results",
    "compiled-pilot-results-final",
    "compiled-search",
    "deterministic-screening",
    "deterministic-screening-v2",
    "deterministic-screening-v3",
    "deterministic-screening-final",
    "negative-control-results",
    "negative-control-results-final",
    "rapid-verdict-2026-07-29",
    "review-funnel-2026-07-29-v1",
    "evidence-map",
    "rendered",
    "applications",
    "interview-preparation",
}


def run(*args: str) -> str:
    return subprocess.check_output(
        args, cwd=ROOT, text=True, encoding="utf-8", errors="surrogateescape"
    )


def nul_paths(*args: str) -> list[str]:
    raw = subprocess.check_output(args, cwd=ROOT)
    return sorted(
        item.decode("utf-8", "surrogateescape")
        for item in raw.split(b"\0")
        if item
    )


def sha256_lines(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def changed_path_sets() -> tuple[list[str], list[str], list[str]]:
    unstaged = nul_paths("git", "diff", "--name-only", "-z")
    staged = nul_paths("git", "diff", "--cached", "--name-only", "-z")
    untracked = nul_paths("git", "ls-files", "--others", "--exclude-standard", "-z")
    return unstaged, staged, untracked


def changed_paths() -> tuple[list[str], list[str]]:
    unstaged, staged, untracked = changed_path_sets()
    tracked = sorted(set(unstaged) | set(staged))
    return tracked, untracked


def git_state(
    path: str, tracked: set[str], unstaged: set[str], staged: set[str]
) -> str:
    if path not in tracked:
        return "untracked"
    if path in staged and path in unstaged:
        return "staged-and-unstaged"
    if path in staged:
        return "staged"
    return "modified"


def classify(path: str) -> tuple[str, str]:
    pure = PurePosixPath(path)
    parts = set(pure.parts)
    lower = path.lower()
    suffix = pure.suffix.lower()
    name = pure.name.lower()

    if (
        any(part in {"secrets", "secret", "credentials", "credential", "private"} for part in parts)
        or (name.startswith(".env") and name != ".env.example")
        or suffix in {".pem", ".key", ".p12"}
        or any(token in name for token in ("credential", "api-key", "private-key"))
    ):
        return "credential_secret", "Credential-like path; requires explicit secret review."

    if path == "result.json" or suffix in {".zip", ".sqlite", ".sqlite3", ".db"}:
        return "private_raw", "Raw export/archive/database authority is not source-promotable."

    if (
        "__pycache__" in parts
        or ".pytest_cache" in parts
        or ".mypy_cache" in parts
        or ".ruff_cache" in parts
        or ".venv" in parts
        or "node_modules" in parts
        or suffix in {".pyc", ".pyo"}
    ):
        return "cache", "Rebuildable dependency or interpreter/test cache."

    if pure.parts and pure.parts[0] in {"upstreams", "audit-work", "market-aligner", "market-aligner-artiom"}:
        return "external", "Independent or upstream workspace; never absorb into root history."

    if pure.parts and pure.parts[0] == "tmp":
        return "cache", "Temporary render/work product."

    if pure.parts[:2] == ("job-application-automation", "tmp"):
        return "cache", "Project-local render scratch output."

    if (
        any(segment in parts for segment in GENERATED_SEGMENTS)
        or pure.parts and pure.parts[0] in {"output"}
        or lower.endswith(".inspect.ndjson")
        or name.startswith("preview-")
        or name.startswith("qa-")
    ):
        return "generated", "Derived output; preserve by receipt or regenerate, not source promotion."

    if (
        suffix in {".png", ".jpg", ".jpeg", ".webp", ".xlsx"}
        or (
            suffix == ".pdf"
            and "evidence" not in parts
            and pure.parts[:2] != ("company-admin", "excellence-exalted")
        )
    ):
        return "generated", "Rendered/binary deliverable; not canonical programme source."

    if suffix == ".pdf" and "evidence" in parts:
        return "private_raw", "Binary source evidence may contain personal identifiers."

    if pure.parts and pure.parts[0] in {"SESSION_LOGS", "reports", "retrospectives"}:
        return "historical", "Programme evidence, receipt, analysis, or historical ledger."

    if suffix in {
        ".md",
        ".json",
        ".jsonl",
        ".csv",
        ".py",
        ".sh",
        ".mjs",
        ".toml",
        ".yaml",
        ".yml",
        ".plist",
        ".service",
        ".timer",
        ".conf",
        ".cron",
        ".txt",
        ".patch",
    } or name in {".gitignore", ".gitkeep", ".env.example"}:
        return "source_authority", "Authored source, configuration, contract, or authority document."

    return "unresolved", "No deterministic metadata-only rule classifies this path safely."


def build_allowlist() -> dict[str, Any]:
    unstaged, staged, untracked = changed_path_sets()
    tracked = sorted(set(unstaged) | set(staged))
    tracked_set = set(tracked)
    unstaged_set = set(unstaged)
    staged_set = set(staged)
    records: list[dict[str, Any]] = []
    for path in sorted(tracked_set | set(untracked)):
        category, reason = classify(path)
        absolute = ROOT / path
        records.append(
            {
                "path": path,
                "git_state": git_state(
                    path, tracked_set, unstaged_set, staged_set
                ),
                "category": category,
                "promotable": category in PROMOTABLE,
                "size_bytes": absolute.stat().st_size if absolute.is_file() else None,
                "reason": reason,
            }
        )
    allow = [item["path"] for item in records if item["promotable"]]
    deny = [item["path"] for item in records if not item["promotable"]]
    counts = Counter(item["category"] for item in records)
    return {
        "schema": "giga.modularization.worktree-promotion-allowlist.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(ROOT),
        "policy": {
            "promotable_categories": sorted(PROMOTABLE),
            "deny_by_default": True,
            "raw_payload_contents_read": False,
            "staging_authority": "none; this manifest does not stage or commit",
        },
        "counts": {
            "records": len(records),
            "tracked_changed": len(tracked),
            "untracked": len(untracked),
            "by_category": dict(sorted(counts.items())),
            "safe_to_promote": len(allow),
            "denied": len(deny),
        },
        "tracked_changed_paths_sha256": sha256_lines(tracked),
        "untracked_paths_sha256": sha256_lines(untracked),
        "safe_to_promote_sha256": sha256_lines(allow),
        "denied_sha256": sha256_lines(deny),
        "safe_to_promote": allow,
        "deny": deny,
        "records": records,
    }


def live_repo_processes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current_pid = os.getpid()
    parent_pid = os.getppid()
    for line in run("ps", "-axo", "pid=,ppid=,etime=,command=").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        fields = stripped.split(None, 3)
        if len(fields) != 4:
            continue
        pid, ppid, elapsed, command = fields
        if int(pid) in {current_pid, parent_pid}:
            continue
        if str(ROOT) in command:
            rows.append(
                {
                    "pid": int(pid),
                    "ppid": int(ppid),
                    "elapsed": elapsed,
                    "command": command,
                }
            )
    return rows


def launchd_matches() -> list[dict[str, Any]]:
    output = run("launchctl", "list")
    matches: list[dict[str, Any]] = []
    for line in output.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in ("giga", "jarvis", "memory", "market", "dubbing", "orchestr")):
            fields = line.split(maxsplit=2)
            matches.append(
                {
                    "pid": fields[0] if fields else "-",
                    "last_exit": fields[1] if len(fields) > 1 else "-",
                    "label": fields[2] if len(fields) > 2 else line,
                }
            )
    return matches


def build_writer_gate(allowlist: dict[str, Any]) -> dict[str, Any]:
    processes = live_repo_processes()
    launchd = launchd_matches()
    return {
        "schema": "giga.modularization.live-writer-gate.v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(ROOT),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "root_inode": ROOT.stat().st_ino,
        "git_head": run("git", "rev-parse", "HEAD").strip(),
        "git_branch": run("git", "branch", "--show-current").strip(),
        "worktree_allowlist_sha256": hashlib.sha256(
            json.dumps(allowlist, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "repo_bound_processes": processes,
        "possibly_related_launchd_jobs": launchd,
        "ready_for_root_move": not processes,
        "decision": (
            "pass-no-repository-bound-writers-observed"
            if not processes
            else "fail-repository-bound-writers-observed"
        ),
        "limitations": [
            "This is a point-in-time observation, not a persistent filesystem fence.",
            "Possibly related launchd labels are not treated as writers without a repository-bound command.",
            "The root-move lock and an immediate second process check remain mandatory.",
        ],
    }


def main() -> int:
    allowlist = build_allowlist()
    ALLOWLIST.write_text(
        json.dumps(allowlist, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    gate = build_writer_gate(allowlist)
    WRITER_GATE.write_text(
        json.dumps(gate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "allowlist": str(ALLOWLIST),
                "writer_gate": str(WRITER_GATE),
                "counts": allowlist["counts"],
                "writer_gate_decision": gate["decision"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
