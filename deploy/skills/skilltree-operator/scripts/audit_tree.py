#!/usr/bin/env python3
"""Build an evidence-backed implementation registry from the immutable SkillTree export."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


STATUSES = {"implemented", "partial", "available", "external", "blocked", "documented"}
PRECEDENCE = {name: rank for rank, name in enumerate(
    ("documented", "available", "blocked", "partial", "external", "implemented")
)}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe_evidence(root: Path, relative: str) -> tuple[bool, str]:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"evidence escapes giga-user root: {relative}") from exc
    if any(char in relative for char in "*?["):
        raise ValueError(f"evidence paths must be exact, not globs: {relative}")
    if not candidate.exists():
        return False, relative
    if candidate.is_dir() and not any(item.name[0] != "." for item in candidate.iterdir()):
        return False, relative
    return True, relative


def external_evidence(path_text: str) -> tuple[bool, str]:
    path = Path(path_text)
    if not path.is_absolute() or any(char in path_text for char in "*?["):
        raise ValueError(f"external evidence must be an exact absolute path: {path_text}")
    return path.exists(), path_text


def skill_names(roots: list[Path]) -> set[str]:
    names: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("*/SKILL.md"):
            head = path.read_text(encoding="utf-8", errors="replace")[:2000]
            match = re.search(r"(?m)^name:\s*['\"]?([^'\"\n]+)", head)
            if match:
                names.add(match.group(1).strip().casefold())
    return names


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--evidence-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--skill-root", action="append", type=Path, default=[])
    args = parser.parse_args()

    root = args.root.resolve()
    export = args.export.resolve()
    if export.is_relative_to(root) is False:
        raise SystemExit("export must be inside giga-user")
    tree = load_json(export / "data" / "tree.json")
    playbook = load_json(export / "data" / "playbook.json")
    evidence_map = load_json(args.evidence_map)
    declarations = evidence_map["jobs"]
    hub_declaration = evidence_map.get("hub", {})
    installed = skill_names([*args.skill_root, root / "deploy" / "skills"])

    locations: dict[str, dict] = {}
    for department in tree:
        for function in department.get("functions", []):
            for job in function.get("jobs", []):
                locations[job["name"]] = {
                    "department": department["name"],
                    "function": function["name"],
                    "description": job.get("desc", ""),
                    "target_level": job.get("level", "autonomous"),
                    "capabilities": job.get("skills", []),
                    "tools": job.get("tools", []),
                }

    unknown = sorted(set(declarations) - set(playbook))
    if unknown:
        raise SystemExit(f"evidence map contains unknown jobs: {unknown}")

    rows = []
    for name, entry in playbook.items():
        declaration = declarations.get(name, {})
        declared = declaration.get("status", "documented")
        if declared not in STATUSES:
            raise SystemExit(f"invalid status for {name}: {declared}")
        checks = [safe_evidence(root, item) for item in declaration.get("evidence", [])]
        external_checks = [external_evidence(item) for item in declaration.get("external_evidence", [])]
        found = [item for ok, item in checks if ok]
        missing = [item for ok, item in checks if not ok]
        external_found = [item for ok, item in external_checks if ok]
        external_missing = [item for ok, item in external_checks if not ok]
        if declared == "implemented":
            status = "implemented" if checks and not missing else ("partial" if found else "documented")
        elif declared == "external":
            complete = checks and not missing and external_checks and not external_missing
            status = "external" if complete else ("partial" if found or external_found else "documented")
        elif declared == "partial":
            status = "partial" if found else "documented"
        else:
            status = declared

        files = entry.get("files", [])
        advertised = {normalized(Path(item.get("path", "")).stem) for item in files}
        matches = sorted(advertised & {normalized(item) for item in installed})
        if status == "documented" and matches:
            status = "available"
        location = locations.get(name, {})
        row = {
            "job": name,
            **location,
            "status": status,
            "prerequisites": entry.get("req", []),
            "human_control": entry.get("human"),
            "replacement_claim": entry.get("replaces"),
            "evidence_found": found,
            "evidence_missing": missing,
            "external_evidence_found": external_found,
            "external_evidence_missing": external_missing,
            "matching_skills": matches,
            "note": declaration.get("note", ""),
            "blocker": declaration.get("blocker"),
        }
        rows.append(row)

    hub_checks = [safe_evidence(root, item) for item in hub_declaration.get("evidence", [])]
    hub_found = [item for ok, item in hub_checks if ok]
    hub_missing = [item for ok, item in hub_checks if not ok]
    hub_status = "implemented" if hub_checks and not hub_missing else ("partial" if hub_found else "documented")
    by_name = {row["job"]: row for row in rows}
    for row in rows:
        prereq_states = []
        for prerequisite in row["prerequisites"]:
            if prerequisite == "Company Knowledge Base":
                prerequisite = "Company Knowledge Base"
            target = by_name.get(prerequisite)
            status = hub_status if prerequisite == "Company Knowledge Base" else (
                target["status"] if target else "missing"
            )
            prereq_states.append({"job": prerequisite, "status": status})
        row["prerequisite_states"] = prereq_states
        row["eligible_to_advance"] = all(
            item["status"] in {"implemented", "external"} for item in prereq_states
        )

    counts = Counter(row["status"] for row in rows)
    registry = {
        "schema_version": "1.0",
        "source_export": str(export.relative_to(root)),
        "hub": {
            "job": "Company Knowledge Base",
            "status": hub_status,
            "evidence_found": hub_found,
            "evidence_missing": hub_missing,
            "note": hub_declaration.get("note", ""),
        },
        "jobs_total": len(rows),
        "counts": dict(sorted(counts.items())),
        "jobs": sorted(rows, key=lambda row: (-PRECEDENCE[row["status"]], row["job"])),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = ["# GIGA SkillTree implementation audit", "", f"Jobs audited: **{len(rows)}**", ""]
    lines.append("| Status | Count |")
    lines.append("|---|---:|")
    for status in ("implemented", "external", "partial", "available", "blocked", "documented"):
        lines.append(f"| {status} | {counts.get(status, 0)} |")
    lines.extend(["", "## Evidence-backed capabilities", ""])
    for row in registry["jobs"]:
        if row["status"] == "documented":
            continue
        evidence = ", ".join(f"`{item}`" for item in row["evidence_found"]) or "none"
        lines.append(f"- **{row['job']}** — `{row['status']}` — {row['note'] or 'No note.'} Evidence: {evidence}")
    lines.extend(["", "## Eligible undocumented nodes", ""])
    eligible = [row for row in rows if row["status"] == "documented" and row["eligible_to_advance"]]
    for row in sorted(eligible, key=lambda item: item["job"]):
        lines.append(f"- {row['job']} ({row.get('department', 'unknown')} / {row.get('function', 'unknown')})")
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "report": str(args.report), "counts": registry["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
