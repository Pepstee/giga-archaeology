#!/usr/bin/env python3
"""Audit Artiom's canonical user-authored corpus for career-profile evidence.

The script reads every record in the three canonical textual views documented in
``corpus/MANIFEST.md``.  It de-duplicates overlapping AI prompt/transcript
records, counts track-specific evidence, and emits only short, secret-screened
examples.  It never writes raw corpus text to disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "prompts": sorted((ROOT / "corpus/raw").glob("prompts_*.jsonl"))[-1],
    "instagram": ROOT / "corpus/raw/instagram_20260717.jsonl",
    "transcripts": [
        ROOT / "corpus/transcripts/claude_conversations.jsonl",
        ROOT / "corpus/transcripts/chatgpt_conversations.jsonl",
    ],
}

TRACKS: dict[str, tuple[str, ...]] = {
    "agentic_ai": (
        "orchestrator", "agentic", "multi-agent", "multi agent", "llm", "claude",
        "codex", "model routing", "ai engineer", "ai engineering",
    ),
    "applied_ai": (
        "machine learning", "artificial intelligence", " ai ", "llm", "nlp",
        "prompt engineering", "rag", "fine-tun", "lora", "model-agnostic",
    ),
    "automation_solutions": (
        "automation", "automate", "workflow", "daemon", "pipeline", "scraper",
        "integration", "autonomous", "overnight",
    ),
    "cloud_platform": (
        "aws", "lambda", "serverless", "docker", "kubernetes", "terraform",
        "azure", "cloudwatch", "devops", "ci/cd", "infrastructure",
    ),
    "security_detection": (
        "scafad", "anomaly detection", "cybersecurity", "security engineer",
        "detection engineering", "attack detection", "privacy-preserving",
    ),
    "backend_software": (
        "backend", "api", "python", "database", "sql", "fastapi", "django",
        "server", "software architect", "software engineer",
    ),
    "full_stack": (
        "full-stack", "full stack", "frontend", "react", "next.js", "website",
        "web app", "client portal", "northern ray",
    ),
    "technical_product": (
        "product", "requirements", "architecture", "risk register", "calibration",
        "due diligence", "decision engine", "acceptance", "stakeholder",
    ),
}

SECRET_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"api[_ -]?key",
        r"secret[_ -]?access",
        r"bearer\s+[a-z0-9._-]+",
        r"token\s*[=:]",
        r"password\s*[=:]",
        r"-----begin [a-z ]+private key-----",
        r"\b\d{8,10}:[a-z0-9_-]{20,}\b",
    )
)


@dataclass(frozen=True)
class Record:
    source: str
    ts: str
    text: str
    locator: str


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            item["_line"] = line_no
            yield item


def records() -> Iterator[Record]:
    for item in read_jsonl(SOURCES["prompts"]):
        yield Record(
            "prompts",
            str(item.get("ts", "")),
            str(item.get("text", "")),
            f"{SOURCES['prompts'].relative_to(ROOT)}:{item['_line']}",
        )
    for item in read_jsonl(SOURCES["instagram"]):
        yield Record(
            "instagram",
            str(item.get("ts", "")),
            str(item.get("text", "")),
            f"corpus/raw/instagram_20260717.jsonl:{item['_line']}",
        )
    for path in SOURCES["transcripts"]:
        if not path.exists():
            continue
        for item in read_jsonl(path):
            if item.get("sender") != "human":
                continue
            yield Record(
                "transcripts",
                str(item.get("ts", "")),
                str(item.get("text", "")),
                f"{path.relative_to(ROOT)}:{item['_line']}",
            )


def text_key(text: str) -> str:
    normalised = re.sub(r"\s+", " ", text.strip()).casefold()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def safe(text: str) -> bool:
    return bool(text.strip()) and not any(pattern.search(text) for pattern in SECRET_PATTERNS)


def matches(text: str, terms: Iterable[str]) -> bool:
    haystack = f" {text.casefold()} "
    return any(term.casefold() in haystack for term in terms)


def compact(text: str, limit: int = 280) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def audit(example_limit: int) -> dict:
    raw_counts: Counter[str] = Counter()
    unique_counts: Counter[str] = Counter()
    track_counts: Counter[str] = Counter()
    track_sources: dict[str, Counter[str]] = {name: Counter() for name in TRACKS}
    examples: dict[str, list[dict[str, str]]] = {name: [] for name in TRACKS}
    seen: set[str] = set()
    secret_screened = 0

    for record in records():
        raw_counts[record.source] += 1
        key = text_key(record.text)
        if key in seen:
            continue
        seen.add(key)
        unique_counts[record.source] += 1
        if not safe(record.text):
            secret_screened += 1
            continue
        for track, terms in TRACKS.items():
            if not matches(record.text, terms):
                continue
            track_counts[track] += 1
            track_sources[track][record.source] += 1
            examples[track].append(
                {
                    "ts": record.ts,
                    "source": record.source,
                    "locator": record.locator,
                    "excerpt": compact(record.text),
                }
            )

    for track in TRACKS:
        examples[track] = sorted(examples[track], key=lambda e: e["ts"], reverse=True)[:example_limit]

    return {
        "scope": {
            "raw_user_authored_records": dict(raw_counts),
            "unique_records_after_exact_dedup": dict(unique_counts),
            "unique_total": len(seen),
            "secret_screened_records": secret_screened,
            "excluded": [
                "assistant turns",
                "other people's Instagram context",
                "binary attachments and raw export zip",
                "duplicate training-pair views",
            ],
        },
        "tracks": {
            track: {
                "matching_unique_records": track_counts[track],
                "by_source": dict(track_sources[track]),
                "recent_examples": examples[track],
            }
            for track in TRACKS
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(audit(max(0, args.examples)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
