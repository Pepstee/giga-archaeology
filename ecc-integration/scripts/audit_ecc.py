#!/usr/bin/env python3
"""Produce a deterministic, read-only inventory and triage of a pinned ECC checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


RISK_PATTERNS = {
    "destructive_shell": re.compile(r"\b(?:rm\s+-rf|git\s+reset\s+--hard|sudo\b)", re.I),
    "credential_or_secret": re.compile(r"\b(?:api[_-]?key|access[_-]?token|password|secret)\b", re.I),
    "network_execution": re.compile(r"(?:curl|wget)[^\n|]*(?:\||-o\s+[^\s]+)|\bnpx\b", re.I),
    "home_mutation": re.compile(r"(?:~/|\$HOME/|\.claude/|\.codex/)", re.I),
    "autonomous_mutation": re.compile(r"\b(?:auto(?:matic)?-?update|self-?modify|continuous learning)\b", re.I),
}

PRIORITY_CONCEPTS = {
    "harness-adapter-compliance", "eval-harness", "agent-eval", "verification-loop",
    "skill-comply", "production-audit", "repo-scan", "security-scan", "safety-guard",
    "recursive-decision-ledger", "token-budget-advisor", "workspace-surface-audit",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def tracked_files(root: Path) -> list[Path]:
    """Return the pinned Git tree only, excluding ignored/generated local artifacts."""
    raw = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"])
    relatives = [item.decode("utf-8") for item in raw.split(b"\0") if item]
    return sorted(root / relative for relative in relatives)


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip("'\"")
    return result


def tokens(value: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", value.lower()) if len(t) > 2}


def similarity(a: str, b: str) -> float:
    left, right = tokens(a), tokens(b)
    return len(left & right) / len(left | right) if left and right else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ecc", type=Path, required=True)
    parser.add_argument("--installed", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.ecc.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    installed = json.loads(args.installed.read_text())
    installed_by_name = {item["name"]: item for item in installed}

    files = []
    risk_totals = Counter()
    for path in tracked_files(root):
        if not path.is_file():
            raise SystemExit(f"tracked source is missing: {path.relative_to(root)}")
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        text = data.decode("utf-8", errors="ignore") if b"\0" not in data[:4096] else ""
        risks = [name for name, pattern in RISK_PATTERNS.items() if text and pattern.search(text)]
        risk_totals.update(risks)
        files.append({"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "risks": risks})

    skills = []
    for skill_file in sorted((root / "skills").glob("*/SKILL.md")):
        text = skill_file.read_text(errors="replace")
        meta = frontmatter(text)
        name = meta.get("name") or skill_file.parent.name
        description = meta.get("description", "")
        exact = installed_by_name.get(name)
        closest = max(installed, key=lambda item: similarity(description, item.get("description", "")))
        score = round(similarity(description, closest.get("description", "")), 3)
        subtree = [item for item in files if item["path"].startswith(f"skills/{skill_file.parent.name}/")]
        risks = sorted({risk for item in subtree for risk in item["risks"]})
        if exact:
            disposition, reason = "reject_duplicate", f"Installed capability has the same name ({exact['source']})."
        elif name in PRIORITY_CONCEPTS:
            disposition, reason = "adapt_candidate", "Potentially strengthens giga-user governance, verification, or evidence handling."
        elif risks:
            disposition, reason = "reference_only", "Contains mutation, credential, network, or autonomous-operation indicators requiring manual isolation."
        elif score >= 0.62:
            disposition, reason = "reject_overlap", f"High semantic overlap with installed {closest['name']} ({score})."
        else:
            disposition, reason = "defer_on_demand", "No current giga-user requirement justifies increasing the active trigger surface."
        skills.append({
            "name": name, "path": skill_file.relative_to(root).as_posix(), "description": description,
            "files": len(subtree), "bytes": sum(item["bytes"] for item in subtree), "risks": risks,
            "closest_installed": closest["name"], "similarity": score,
            "disposition": disposition, "reason": reason,
        })

    commit = git(root, "rev-parse", "HEAD")
    provenance = {
        "schema": "giga.ecc-upstream.v1", "upstream": "https://github.com/affaan-m/ECC.git",
        "fork": "https://github.com/Pepstee/ECC.git", "commit": commit,
        "commit_date": git(root, "show", "-s", "--format=%cI", commit),
        "tree": git(root, "rev-parse", f"{commit}^{{tree}}"),
        "license_sha256": sha256(root / "LICENSE"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    inventory = {
        "schema": "giga.ecc-inventory.v1", "commit": commit,
        "counts": {"files": len(files), "skills": len(skills), "bytes": sum(x["bytes"] for x in files)},
        "risk_file_counts": dict(sorted(risk_totals.items())), "files": files,
    }
    classification = {
        "schema": "giga.ecc-classification.v1", "commit": commit,
        "policy": "No item is deployed by this classification; adapt_candidate requires isolated tests and explicit promotion.",
        "counts": dict(sorted(Counter(item["disposition"] for item in skills).items())), "skills": skills,
    }
    for name, payload in (("UPSTREAM.json", provenance), ("COMPONENT_INVENTORY.json", inventory), ("SKILL_CLASSIFICATION.json", classification)):
        (out / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"provenance": provenance, "inventory": inventory["counts"], "classification": classification["counts"]}, indent=2))


if __name__ == "__main__":
    main()
