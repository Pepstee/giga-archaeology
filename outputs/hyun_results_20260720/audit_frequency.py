#!/usr/bin/env python3
"""Build an auditable, non-destructive frequency dataset for Hyun's handoff."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path("/Users/admin/Documents/giga-user")
SCORED = ROOT / "market-aligner/skeleton/data/bulk_500/jobs_scored_terra.jsonl"
OUT = ROOT / "outputs/hyun_results_20260720/frequency_audit.json"

# Packaging-only corrections for model drift observed in this completed run.
# The source JSONL and source workbooks remain untouched.
ALIASES = {
    "adobexd": "adobe_xd",
    "adobe_xd": "adobe_xd",
    "adobe_after_effects": "aftereffects",
    "after_effects": "aftereffects",
    "aftereffects": "aftereffects",
    "adobe_premiere_pro": "premiere",
    "premiere_pro": "premiere",
    "premierepro": "premiere",
    "premiere": "premiere",
    "substancepainter": "substance_painter",
    "substance_painter": "substance_painter",
    "stablediffusion": "stable_diffusion",
    "stable_diffusion": "stable_diffusion",
    "davinciresolve": "davinci_resolve",
    "finalcutpro": "final_cut_pro",
    "hancomoffice": "hancom_office",
    "veo3": "veo",
}

OWNED_TOOLS = {"rhino", "max3ds", "revit", "photoshop", "illustrator", "lumion"}


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return ALIASES.get(text, text)


def ranked_counts(rows: list[dict], field: str, eligible_only: bool = True) -> list[dict]:
    freq: Counter[str] = Counter()
    fields: dict[str, Counter[str]] = defaultdict(Counter)
    raw_forms: dict[str, Counter[str]] = defaultdict(Counter)
    population = [r for r in rows if r.get("entry_level") is True] if eligible_only else rows
    for row in population:
        career = row.get("mapped_career") or "other"
        per_job: dict[str, set[str]] = defaultdict(set)
        for raw in row.get(field) or []:
            canonical = norm(raw)
            if canonical:
                per_job[canonical].add(str(raw))
        for canonical, surfaces in per_job.items():
            freq[canonical] += 1
            fields[canonical][career] += 1
            raw_forms[canonical].update(surfaces)
    result = []
    for item, count in freq.most_common():
        result.append({
            "requirement": item,
            "frequency": count,
            "pct_of_eligible_jobs": round(100 * count / len(population), 1) if population else 0.0,
            "top_fields": ", ".join(f"{k} ({v})" for k, v in fields[item].most_common(3)),
            "owned_or_reported": item in OWNED_TOOLS,
            "raw_forms": ", ".join(sorted(raw_forms[item])),
        })
    return result


def main() -> None:
    rows = [json.loads(line) for line in SCORED.read_text(encoding="utf-8").splitlines() if line.strip()]
    eligible = [r for r in rows if r.get("entry_level") is True]
    tool_rows = ranked_counts(rows, "required_software")
    broad_rows = ranked_counts(rows, "skills_to_learn")
    field_counts = Counter(r.get("mapped_career") or "other" for r in rows)
    eligible_field_counts = Counter(r.get("mapped_career") or "other" for r in eligible)
    boards = Counter(r.get("board") or "unknown" for r in rows)
    payload = {
        "methodology": {
            "denominator": "291 postings explicitly classified entry_level=true",
            "counting_rule": "one count per normalized requirement per posting",
            "tool_source": "required_software",
            "broader_requirement_source": "skills_to_learn",
            "source_data_changed": False,
            "owned_tools_source": "profiler/data/hyun_profile.yaml tools_self_reported",
        },
        "summary": {
            "scored_jobs": len(rows),
            "eligible_entry_level_jobs": len(eligible),
            "non_entry_jobs": sum(r.get("entry_level") is False for r in rows),
            "unclear_entry_status": sum(r.get("entry_level") is None for r in rows),
            "boards": dict(boards),
            "field_counts": dict(field_counts),
            "eligible_field_counts": dict(eligible_field_counts),
            "eligible_with_structured_tools": sum(bool(r.get("required_software")) for r in eligible),
            "eligible_with_broader_requirements": sum(bool(r.get("skills_to_learn")) for r in eligible),
        },
        "tool_prevalence": tool_rows,
        "requirement_prevalence": broad_rows,
        "learning_gap_prevalence": [r for r in broad_rows if not r["owned_or_reported"]],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print("top_tools", [(r["requirement"], r["frequency"]) for r in tool_rows[:15]])
    print("top_gaps", [(r["requirement"], r["frequency"]) for r in payload["learning_gap_prevalence"][:20]])


if __name__ == "__main__":
    main()
