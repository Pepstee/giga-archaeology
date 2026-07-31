#!/usr/bin/env python3
"""Inventory every accessible SKILL.md/skill.md beneath the user's home directory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import yaml


HOME = Path("/Users/admin")
GIGA_ROOT = HOME / "Documents" / "giga-user"
ACTIVE_REGISTRY = (
    HOME
    / ".codex"
    / "skills"
    / "skill-router"
    / "references"
    / "installed-skills.json"
)

CATEGORY_PRIORITY = {
    "active-codex-personal-or-system": 0,
    "active-shared-agent": 1,
    "active-claude-personal": 2,
    "installed-codex-plugin-cache": 3,
    "giga-owned-deploy": 4,
    "giga-staging": 5,
    "claude-marketplace-checkout": 6,
    "codex-marketplace-temporary-mirror": 7,
    "codex-runtime-cache": 8,
    "claude-app-session-or-runtime": 9,
    "claude-scheduled-automation": 10,
    "claude-user-project-runtime": 11,
    "orchestrator-v3-skill-corpus": 12,
    "giga-ecc-upstream": 13,
    "giga-corpus-snapshot": 14,
    "giga-vendored-runtime": 15,
    "other-project-local": 16,
    "kimi-runtime": 17,
    "graphify-repository-cache": 18,
    "package-manager-or-model-runtime": 19,
    "other-accessible-home-path": 20,
}


def is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def category_for(path: Path) -> str:
    rules = (
        ("active-codex-personal-or-system", HOME / ".codex" / "skills"),
        ("active-shared-agent", HOME / ".agents" / "skills"),
        ("active-claude-personal", HOME / ".claude" / "skills"),
        ("installed-codex-plugin-cache", HOME / ".codex" / "plugins" / "cache"),
        ("giga-owned-deploy", GIGA_ROOT / "deploy" / "skills"),
        ("giga-staging", GIGA_ROOT / "staging"),
        (
            "claude-marketplace-checkout",
            HOME / ".claude" / "plugins" / "marketplaces",
        ),
        ("codex-marketplace-temporary-mirror", HOME / ".codex" / ".tmp"),
        ("codex-runtime-cache", HOME / ".cache" / "codex-runtimes"),
        (
            "claude-app-session-or-runtime",
            HOME / "Library" / "Application Support" / "Claude",
        ),
        ("claude-scheduled-automation", HOME / "Claude" / "Scheduled"),
        ("claude-scheduled-automation", HOME / "Claude" / "DisabledScheduled"),
        ("claude-user-project-runtime", HOME / "Claude"),
        (
            "orchestrator-v3-skill-corpus",
            HOME / "Documents" / "agentic-orchestrator" / "projects" / "orchestrator-v3",
        ),
        ("giga-ecc-upstream", GIGA_ROOT / "upstreams" / "ECC"),
        ("giga-corpus-snapshot", GIGA_ROOT / "corpus"),
        ("giga-vendored-runtime", GIGA_ROOT),
        ("other-project-local", HOME / "Documents"),
        (
            "kimi-runtime",
            HOME / "Library" / "Application Support" / "kimi-desktop",
        ),
        ("graphify-repository-cache", HOME / ".graphify"),
    )
    for category, root in rules:
        if is_below(path, root):
            return category
    if any(
        is_below(path, root)
        for root in (HOME / ".cache", HOME / ".npm", HOME / ".local", HOME / ".lmstudio")
    ):
        return "package-manager-or-model-runtime"
    return "other-accessible-home-path"


def discover_manifests() -> tuple[list[Path], int]:
    command = [
        "rg",
        "--files",
        "--hidden",
        "--no-ignore",
        "-g",
        "SKILL.md",
        "-g",
        "skill.md",
        str(HOME),
    ]
    process = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    paths = sorted(
        {Path(line) for line in process.stdout.splitlines() if line.strip()},
        key=lambda item: str(item).casefold(),
    )
    denied_count = sum(
        "Operation not permitted" in line for line in process.stderr.splitlines()
    )
    return paths, denied_count


def normalized(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fallback_frontmatter(text: str, key: str) -> str:
    if not text.startswith("---"):
        return ""
    frontmatter = text.split("---", 2)[1]
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", frontmatter)
    return normalized(match.group(1).strip("'\"")) if match else ""


def fallback_description(text: str) -> str:
    body = text.split("---", 2)[-1] if text.startswith("---") else text
    for block in re.split(r"\n\s*\n", body):
        candidate = normalized(block)
        if not candidate or candidate.startswith(("#", "```", "<")):
            continue
        return candidate
    return "No description was declared; purpose requires manual inspection."


def short_description(description: str, limit: int = 240) -> str:
    description = normalized(description)
    if len(description) <= limit:
        return description
    sentence = re.match(r"^(.+?[.!?])(?:\s|$)", description)
    if sentence and len(sentence.group(1)) <= limit:
        return sentence.group(1)
    return description[: limit - 1].rstrip(" ,;:-") + "…"


def parse_manifest(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    metadata: dict[str, object] = {}
    parse_error = ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            try:
                loaded = yaml.safe_load(parts[1])
                if isinstance(loaded, dict):
                    metadata = loaded
            except Exception as exc:  # malformed third-party frontmatter
                parse_error = f"{type(exc).__name__}: {exc}"
    name = normalized(metadata.get("name")) or fallback_frontmatter(text, "name")
    if not name:
        name = path.parent.name
    description = normalized(metadata.get("description")) or fallback_frontmatter(
        text, "description"
    )
    declared_description = bool(description)
    if not description:
        description = fallback_description(text)
    return {
        "path": str(path),
        "name": name,
        "description": description,
        "short_description": short_description(description),
        "declared_description": declared_description,
        "category": category_for(path),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "frontmatter_parse_error": parse_error,
    }


def markdown_cell(value: object) -> str:
    return normalized(value).replace("|", "\\|")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=GIGA_ROOT / "outputs" / f"skill-filesystem-inventory-{date.today()}",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    active = json.loads(ACTIVE_REGISTRY.read_text(encoding="utf-8"))
    active_paths = {str(Path(item["path"]).resolve()) for item in active}
    manifests, denied_count = discover_manifests()
    physical_rows = [parse_manifest(path) for path in manifests]
    for row in physical_rows:
        row["catalogued_by_skill_router"] = (
            str(Path(str(row["path"])).resolve()) in active_paths
        )

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in physical_rows:
        key = (str(row["name"]).casefold(), str(row["description"]))
        grouped[key].append(row)

    capability_rows: list[dict[str, object]] = []
    for (_, _), instances in grouped.items():
        ordered = sorted(
            instances,
            key=lambda row: (
                CATEGORY_PRIORITY[str(row["category"])],
                str(row["path"]).casefold(),
            ),
        )
        categories = sorted(
            {str(row["category"]) for row in instances},
            key=lambda item: CATEGORY_PRIORITY[item],
        )
        hashes = {str(row["sha256"]) for row in instances}
        capability_rows.append(
            {
                "name": ordered[0]["name"],
                "short_description": ordered[0]["short_description"],
                "description": ordered[0]["description"],
                "categories": categories,
                "copy_count": len(instances),
                "content_variant_count": len(hashes),
                "catalogued_by_skill_router": any(
                    bool(row["catalogued_by_skill_router"]) for row in instances
                ),
                "canonical_path": ordered[0]["path"],
                "paths": [str(row["path"]) for row in ordered],
            }
        )
    capability_rows.sort(
        key=lambda row: (
            0 if row["catalogued_by_skill_router"] else 1,
            min(CATEGORY_PRIORITY[item] for item in row["categories"]),
            str(row["name"]).casefold(),
            str(row["description"]).casefold(),
        )
    )

    category_counts = Counter(str(row["category"]) for row in physical_rows)
    unique_names = {str(row["name"]).casefold() for row in physical_rows}
    content_hashes = {str(row["sha256"]) for row in physical_rows}
    parse_errors = [row for row in physical_rows if row["frontmatter_parse_error"]]

    summary = {
        "generated_on": date.today().isoformat(),
        "scan_root": str(HOME),
        "scope": "Every accessible SKILL.md or skill.md under the user home directory.",
        "macos_protected_directories_reported_by_scanner": denied_count,
        "counts": {
            "skill_router_catalog_entries": len(active),
            "physical_manifests": len(physical_rows),
            "unique_content_hashes": len(content_hashes),
            "unique_name_description_capabilities": len(capability_rows),
            "unique_names": len(unique_names),
            "manifests_without_declared_description": sum(
                not bool(row["declared_description"]) for row in physical_rows
            ),
            "frontmatter_parse_errors": len(parse_errors),
        },
        "physical_manifests_by_category": dict(
            sorted(
                category_counts.items(),
                key=lambda item: (CATEGORY_PRIORITY[item[0]], item[0]),
            )
        ),
    }
    payload = {
        "summary": summary,
        "skill_router_catalog": active,
        "deduplicated_capabilities": capability_rows,
        "physical_manifests": physical_rows,
    }
    (output / "inventory.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(
        output / "deduplicated-capabilities.csv",
        [
            {
                **row,
                "categories": "; ".join(row["categories"]),
                "paths": "; ".join(row["paths"]),
            }
            for row in capability_rows
        ],
        [
            "name",
            "short_description",
            "description",
            "categories",
            "copy_count",
            "content_variant_count",
            "catalogued_by_skill_router",
            "canonical_path",
            "paths",
        ],
    )
    write_csv(
        output / "physical-manifests.csv",
        physical_rows,
        [
            "path",
            "name",
            "short_description",
            "description",
            "declared_description",
            "category",
            "sha256",
            "catalogued_by_skill_router",
            "frontmatter_parse_error",
        ],
    )

    lines = [
        "# Exhaustive local agent-skill inventory",
        "",
        f"Generated {summary['generated_on']}. This scans every accessible `SKILL.md` "
        f"and `skill.md` beneath `{HOME}`. It separates the local skill-router catalog from "
        "downloaded caches, upstream libraries, generated corpora, session copies, and "
        "historical snapshots.",
        "",
        "## What “all” means here",
        "",
        f"- **{len(active):,} manifest entries are in the local skill-router catalog.**",
        f"- **{len(physical_rows):,} physical manifests** were found on disk.",
        f"- Those collapse to **{len(capability_rows):,} distinct name+description records**, "
        f"**{len(unique_names):,} names**, and **{len(content_hashes):,} distinct file contents**.",
        "- A file being present—or even appearing in the filesystem-generated router "
        "catalog—does not prove it is enabled, trusted, or callable in a particular session.",
        f"- macOS denied traversal into {denied_count:,} protected operating-system/private-data "
        "directories. All user-controlled Codex, Claude, shared-agent, GIGA, project, and "
        "accessible cache roots were scanned.",
        "",
        "## Physical copies by source",
        "",
        "| Source class | Manifests | Meaning |",
        "|---|---:|---|",
    ]
    meanings = {
        "active-codex-personal-or-system": "Personal and built-in Codex skill roots.",
        "active-shared-agent": "Shared `~/.agents/skills` root.",
        "active-claude-personal": "Personal Claude skill root.",
        "installed-codex-plugin-cache": "Downloaded Codex plugin packages currently cached.",
        "giga-owned-deploy": "GIGA-owned deployable skills.",
        "giga-staging": "Staged GIGA copies; not authoritative by presence alone.",
        "claude-marketplace-checkout": "Claude marketplace repository checkout.",
        "codex-marketplace-temporary-mirror": "Temporary Codex marketplace/catalog mirror.",
        "codex-runtime-cache": "Bundled Codex runtime dependency copies.",
        "claude-app-session-or-runtime": "Claude app session, upload, or runtime copies.",
        "claude-scheduled-automation": "User-created Claude scheduled or disabled automations.",
        "claude-user-project-runtime": "Skills or dependency copies inside user Claude project workspaces.",
        "orchestrator-v3-skill-corpus": "Large orchestrator-v3 skill corpus/generation workspace.",
        "giga-ecc-upstream": "Vendored ECC upstream, including translated/duplicated skills.",
        "giga-corpus-snapshot": "Historical evidence snapshots in the GIGA corpus.",
        "giga-vendored-runtime": "Dependencies or other non-owned manifests inside GIGA.",
        "other-project-local": "Skills embedded in other local projects.",
        "kimi-runtime": "Kimi desktop runtime skills.",
        "graphify-repository-cache": "Skills inside repositories cached by Graphify.",
        "package-manager-or-model-runtime": "npm, pipx, model, or other dependency copies.",
        "other-accessible-home-path": "Other accessible locations under the home directory.",
    }
    for category, count in sorted(
        category_counts.items(),
        key=lambda item: (CATEGORY_PRIORITY[item[0]], item[0]),
    ):
        lines.append(
            f"| `{category}` | {count:,} | {meanings[category]} |"
        )

    lines.extend(
        [
            "",
            "## Local skill-router catalog",
            "",
            "| # | Skill | Short purpose | Source | Manifest |",
            "|---:|---|---|---|---|",
        ]
    )
    for index, row in enumerate(active, 1):
        lines.append(
            f"| {index} | `{markdown_cell(row['name'])}` | "
            f"{markdown_cell(short_description(str(row['description'])))} | "
            f"{markdown_cell(row['source'])} | `{markdown_cell(row['path'])}` |"
        )

    lines.extend(
        [
            "",
            "## Every distinct discovered capability record",
            "",
            "A record is deduplicated by normalized skill name plus full declared description. "
            "Same-name variants remain separate because they can implement different behavior. "
            "The full JSON and CSV retain every physical path.",
            "",
            "| # | Skill | Short purpose | In router catalog | Source class(es) | Copies | Canonical manifest |",
            "|---:|---|---|:---:|---|---:|---|",
        ]
    )
    for index, row in enumerate(capability_rows, 1):
        lines.append(
            f"| {index} | `{markdown_cell(row['name'])}` | "
            f"{markdown_cell(row['short_description'])} | "
            f"{'Yes' if row['catalogued_by_skill_router'] else 'No'} | "
            f"{markdown_cell('; '.join(row['categories']))} | "
            f"{row['copy_count']} | `{markdown_cell(row['canonical_path'])}` |"
        )

    lines.extend(
        [
            "",
            "## Machine-readable companions",
            "",
            "- `inventory.json` — summary, skill-router catalog, every deduplicated record, and every physical manifest.",
            "- `deduplicated-capabilities.csv` — one row per name+description record, with all paths.",
            "- `physical-manifests.csv` — one row per on-disk manifest, including hash and source class.",
            "",
        ]
    )
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
