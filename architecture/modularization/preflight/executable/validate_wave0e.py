#!/usr/bin/env python3
"""Validate Wave 0E path classification and live-writer evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from build_wave0e import (
    ALLOWED_CATEGORIES,
    ALLOWLIST,
    PROMOTABLE,
    ROOT,
    WRITER_GATE,
    changed_paths,
    sha256_lines,
)


def validate(
    allowlist: dict[str, Any], gate: dict[str, Any], *, check_live: bool = True
) -> list[str]:
    errors: list[str] = []
    if allowlist.get("schema") != "giga.modularization.worktree-promotion-allowlist.v1":
        errors.append("unexpected allowlist schema")
    records = allowlist.get("records", [])
    paths = [item.get("path") for item in records if isinstance(item, dict)]
    if len(paths) != len(set(paths)):
        errors.append("duplicate classified paths")
    if any(item.get("category") not in ALLOWED_CATEGORIES for item in records):
        errors.append("unknown classification category")
    if any(
        item.get("promotable") != (item.get("category") in PROMOTABLE)
        for item in records
    ):
        errors.append("promotability does not match fail-closed category policy")
    allow = sorted(item["path"] for item in records if item["promotable"])
    deny = sorted(item["path"] for item in records if not item["promotable"])
    if allow != sorted(allowlist.get("safe_to_promote", [])):
        errors.append("safe-to-promote projection mismatch")
    if deny != sorted(allowlist.get("deny", [])):
        errors.append("deny projection mismatch")
    if set(allow) & set(deny):
        errors.append("allow and deny lists overlap")
    if sha256_lines(allow) != allowlist.get("safe_to_promote_sha256"):
        errors.append("safe-to-promote digest mismatch")
    if sha256_lines(deny) != allowlist.get("denied_sha256"):
        errors.append("deny digest mismatch")

    if check_live:
        tracked, untracked = changed_paths()
        live = sorted(set(tracked) | set(untracked))
        if sorted(paths) != live:
            errors.append(
                "worktree classification drift; regenerate before promotion or migration"
            )
        if sha256_lines(tracked) != allowlist.get("tracked_changed_paths_sha256"):
            errors.append("tracked-change digest drift")
        if sha256_lines(untracked) != allowlist.get("untracked_paths_sha256"):
            errors.append("untracked-path digest drift")

    if gate.get("schema") != "giga.modularization.live-writer-gate.v1":
        errors.append("unexpected live-writer gate schema")
    processes = gate.get("repo_bound_processes")
    if not isinstance(processes, list):
        errors.append("repo-bound process list is missing")
    elif gate.get("ready_for_root_move") != (not processes):
        errors.append("live-writer decision does not match observed processes")
    if gate.get("root_inode") != ROOT.stat().st_ino:
        errors.append("repository root inode drift")
    return errors


def main() -> int:
    allowlist = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    gate = json.loads(WRITER_GATE.read_text(encoding="utf-8"))
    errors = validate(allowlist, gate)
    print(
        json.dumps(
            {
                "schema": "giga.modularization.wave0e-validation.v1",
                "ok": not errors,
                "allowlist_sha256": hashlib.sha256(ALLOWLIST.read_bytes()).hexdigest(),
                "writer_gate_sha256": hashlib.sha256(WRITER_GATE.read_bytes()).hexdigest(),
                "errors": errors,
            },
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
