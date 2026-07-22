#!/usr/bin/env python3
"""Build exhaustive, human- and machine-readable SkillTree inventories."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


EXPORT_ROOT = Path(
    "/Users/admin/Documents/giga-user/outputs/skilltree-export-2026-07-22"
)
GRAPH_PATH = EXPORT_ROOT / "data" / "graph.json"


def joined(values: list[str]) -> str:
    return "; ".join(sorted(set(values), key=str.casefold))


def md(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = graph["edges"]

    jobs_by_skill: dict[str, list[str]] = defaultdict(list)
    jobs_by_capability: dict[str, list[str]] = defaultdict(list)
    skill_ids_by_job: dict[str, list[str]] = defaultdict(list)
    capability_ids_by_job: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        if edge["relation"] == "documented_by":
            jobs_by_skill[edge["target"]].append(edge["source"])
            skill_ids_by_job[edge["source"]].append(edge["target"])
        elif edge["relation"] == "implemented_by_capability":
            jobs_by_capability[edge["target"]].append(edge["source"])
            capability_ids_by_job[edge["source"]].append(edge["target"])

    skill_rows: list[dict] = []
    for node in sorted(
        (n for n in nodes.values() if n["type"] == "skill_file"),
        key=lambda item: item["label"].casefold(),
    ):
        job_nodes = [nodes[job_id] for job_id in jobs_by_skill[node["id"]]]
        metadata = node.get("metadata") or {}
        explanation = metadata.get("what") or (
            "Referenced by the graph, but no public metadata or preview was exposed."
        )
        skill_rows.append(
            {
                "skill": node["label"],
                "path": node.get("path", ""),
                "public_metadata": bool(node.get("metadata")),
                "public_preview": bool(node.get("preview")),
                "departments": joined([job.get("department", "") for job in job_nodes]),
                "functions": joined([job.get("function", "") for job in job_nodes]),
                "mapped_jobs": joined([job["label"] for job in job_nodes]),
                "explanation": explanation,
                "requirements": metadata.get("needs", "Not publicly exposed"),
            }
        )

    capability_rows: list[dict] = []
    for node in sorted(
        (n for n in nodes.values() if n["type"] == "capability"),
        key=lambda item: item["label"].casefold(),
    ):
        job_nodes = [nodes[job_id] for job_id in jobs_by_capability[node["id"]]]
        capability_rows.append(
            {
                "capability": node["label"],
                "departments": joined([job.get("department", "") for job in job_nodes]),
                "functions": joined([job.get("function", "") for job in job_nodes]),
                "mapped_jobs": joined([job["label"] for job in job_nodes]),
            }
        )

    job_rows: list[dict] = []
    for node in sorted(
        (n for n in nodes.values() if n["type"] == "job"),
        key=lambda item: (
            item.get("department", "").casefold(),
            item.get("function", "").casefold(),
            item["label"].casefold(),
        ),
    ):
        skill_nodes = [nodes[item] for item in skill_ids_by_job[node["id"]]]
        capability_nodes = [nodes[item] for item in capability_ids_by_job[node["id"]]]
        playbook = node.get("playbook") or {}
        job_rows.append(
            {
                "department": node.get("department", ""),
                "function": node.get("function", ""),
                "job": node["label"],
                "level": node.get("level", ""),
                "description": node.get("description", ""),
                "named_skill_files": joined([item["label"] for item in skill_nodes]),
                "atomic_capabilities": joined([item["label"] for item in capability_nodes]),
                "prerequisites": joined(playbook.get("req", [])),
                "human_role": playbook.get("human", ""),
                "replaces": playbook.get("replaces", ""),
                "notes": playbook.get("notes", ""),
            }
        )

    inventory = {
        "definition": {
            "named_skill_files": "Deployable skill-file references in the graph.",
            "atomic_capabilities": "Small implementation capabilities attached to jobs.",
            "jobs": "AI-workforce jobs represented as the visible graph nodes.",
        },
        "counts": {
            "named_skill_files": len(skill_rows),
            "named_skill_files_with_public_preview": sum(
                row["public_preview"] for row in skill_rows
            ),
            "atomic_capabilities": len(capability_rows),
            "jobs": len(job_rows),
        },
        "named_skill_files": skill_rows,
        "atomic_capabilities": capability_rows,
        "jobs": job_rows,
    }
    (EXPORT_ROOT / "data" / "all_skills.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    write_csv(
        EXPORT_ROOT / "data" / "skills.csv",
        skill_rows,
        [
            "skill",
            "path",
            "public_metadata",
            "public_preview",
            "departments",
            "functions",
            "mapped_jobs",
            "explanation",
            "requirements",
        ],
    )
    write_csv(
        EXPORT_ROOT / "data" / "capabilities.csv",
        capability_rows,
        ["capability", "departments", "functions", "mapped_jobs"],
    )
    write_csv(
        EXPORT_ROOT / "data" / "jobs.csv",
        job_rows,
        [
            "department",
            "function",
            "job",
            "level",
            "description",
            "named_skill_files",
            "atomic_capabilities",
            "prerequisites",
            "human_role",
            "replaces",
            "notes",
        ],
    )

    lines = [
        "# Every skill in the SkillTree graph",
        "",
        "This is an exhaustive inventory of every skill-like object in the exported graph. "
        "The source uses three distinct concepts, so all three are listed rather than silently "
        "collapsing them:",
        "",
        f"- **{len(skill_rows)} named skill files** — deployable skill-file references; "
        f"{sum(row['public_preview'] for row in skill_rows)} have public preview text.",
        f"- **{len(capability_rows)} atomic capabilities** — implementation-level abilities attached to jobs.",
        f"- **{len(job_rows)} jobs** — the visible AI-workforce nodes in the map.",
        "",
        "The preview page does not expose the paid runnable skill-file contents. This inventory "
        "records every public title, path, explanation, requirement, mapping, and preview-availability "
        "flag without bypassing access controls.",
        "",
        "## 1. Named skill files",
        "",
        "| # | Skill | File reference | Preview | Department(s) | Mapped job(s) | Public explanation | Requirements |",
        "|---:|---|---|:---:|---|---|---|---|",
    ]
    for index, row in enumerate(skill_rows, 1):
        lines.append(
            f"| {index} | {md(row['skill'])} | `{md(row['path'])}` | "
            f"{'Yes' if row['public_preview'] else 'No'} | {md(row['departments'])} | "
            f"{md(row['mapped_jobs'])} | {md(row['explanation'])} | {md(row['requirements'])} |"
        )

    lines.extend(
        [
            "",
            "## 2. Atomic capabilities",
            "",
            "| # | Capability | Department(s) | Function(s) | Mapped job(s) |",
            "|---:|---|---|---|---|",
        ]
    )
    for index, row in enumerate(capability_rows, 1):
        lines.append(
            f"| {index} | `{md(row['capability'])}` | {md(row['departments'])} | "
            f"{md(row['functions'])} | {md(row['mapped_jobs'])} |"
        )

    lines.extend(
        [
            "",
            "## 3. Jobs / visible AI-workforce nodes",
            "",
            "| # | Department | Function | Job | Level | Description | Named skill file(s) | Atomic capabilities |",
            "|---:|---|---|---|---|---|---|---|",
        ]
    )
    for index, row in enumerate(job_rows, 1):
        lines.append(
            f"| {index} | {md(row['department'])} | {md(row['function'])} | "
            f"{md(row['job'])} | {md(row['level'])} | {md(row['description'])} | "
            f"{md(row['named_skill_files']) or '—'} | {md(row['atomic_capabilities']) or '—'} |"
        )

    lines.extend(
        [
            "",
            "## Machine-readable companions",
            "",
            "- `data/all_skills.json` — all three sets with mappings and explanations.",
            "- `data/skills.csv` — named skill files.",
            "- `data/capabilities.csv` — atomic capabilities.",
            "- `data/jobs.csv` — jobs, descriptions, playbook context, and mappings.",
            "",
            "Source: `data/graph.json` (570 nodes, 832 directed edges).",
            "",
        ]
    )
    (EXPORT_ROOT / "EVERY_SKILL.md").write_text("\n".join(lines), encoding="utf-8")

    print(
        f"Wrote {len(skill_rows)} skill files, {len(capability_rows)} capabilities, "
        f"and {len(job_rows)} jobs."
    )


if __name__ == "__main__":
    main()
