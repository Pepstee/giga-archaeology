#!/usr/bin/env python3
"""Check ECC drift without merging or deploying upstream changes."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true", help="Fetch upstream/main; never merges")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    manifest = json.loads(args.manifest.read_text())
    if args.fetch:
        subprocess.check_call(["git", "-C", str(repo), "fetch", "--filter=blob:none", "upstream", "main"])
    pinned = manifest["commit"]
    candidate = run(repo, "rev-parse", "upstream/main")
    changed = []
    if pinned != candidate:
        for line in run(repo, "diff", "--name-status", pinned, candidate).splitlines():
            if line:
                status, *paths = line.split("\t")
                changed.append({"status": status, "paths": paths})
    affected_skill_ids = sorted({
        item["paths"][-1].split("/")[1]
        for item in changed
        if item["paths"] and item["paths"][-1].startswith("skills/") and len(item["paths"][-1].split("/")) > 2
    })
    result = {
        "schema": "giga.ecc-upstream-check.v1", "pinned": pinned, "candidate": candidate,
        "update_available": pinned != candidate, "changed_paths": changed,
        "affected_canonical_skills": affected_skill_ids,
        "safe_to_auto_deploy": False,
        "next_action": "rerun full audit and review changed hashes" if changed else "none",
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Pinned:    {pinned}")
        print(f"Candidate: {candidate}")
        print(f"Changed paths: {len(changed)}")
        print("Auto-deploy: prohibited")


if __name__ == "__main__":
    main()
