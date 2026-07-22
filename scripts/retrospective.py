#!/usr/bin/env python3
"""Create a reproducible evidence census for Session 04's human-authored corpus.

This is an audit aid, not a personality classifier.  Its quantitative signals are
proxies and are labelled as such in the resulting report.  It never prints message
contents, which keeps the report shareable and avoids copying credentials from raw
conversation history.

Usage:
  python3 scripts/retrospective.py
  python3 scripts/retrospective.py --start 2026-01-01 --end 2026-07-19
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parent.parent
PROMPTS = sorted((ROOT / "corpus/raw").glob("prompts_*.jsonl"))[-1]
TRANSCRIPTS = [
    ROOT / "corpus/transcripts/claude_conversations.jsonl",
    ROOT / "corpus/transcripts/chatgpt_conversations.jsonl",
]
INSTAGRAM = ROOT / "corpus/raw/instagram_20260717.jsonl"
DEFAULT_OUTPUT = ROOT / "retrospectives/2026-07-evaluator.md"

EVIDENCE_TERMS = re.compile(r"\b(?:evidence|cite|citation|verify|verified|source|audit|test|prove)\b", re.I)
CHALLENGE_TERMS = re.compile(r"\b(?:challenge|push ?back|critique|adversarial|what am i wrong|where am i wrong)\b", re.I)
RECONSIDER_TERMS = re.compile(r"\b(?:you(?:'| a)re right|i agree|fair point|i was wrong|changed my mind)\b", re.I)
SECRET_TERMS = re.compile(r"\b(?:password|api[_ -]?key|secret[_ -]?key|private key|token)\b", re.I)


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)
    return records


def in_window(record: dict, start: datetime | None, end: datetime | None) -> bool:
    timestamp = parse_timestamp(record.get("ts"))
    if timestamp is None:
        return start is None and end is None
    return (start is None or timestamp >= start) and (end is None or timestamp < end)


def month(value: object) -> str:
    timestamp = parse_timestamp(value)
    return timestamp.strftime("%Y-%m") if timestamp else "undated"


def percentage(numerator: int, denominator: int) -> str:
    return "n/a" if not denominator else f"{numerator / denominator:.1%}"


def largest_conversations(records: list[dict]) -> list[tuple[str, int, int, int]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record.get("sender") != "human" or not isinstance(record.get("text"), str):
            continue
        grouped[record.get("conversation") or "Untitled"].append(record["text"])
    return sorted(((title, len(texts), sum(map(len, texts)),
                    sum(len(text) >= 5_000 for text in texts))
                   for title, texts in grouped.items()),
                  key=lambda row: row[1], reverse=True)[:12]


def report(start: datetime | None, end: datetime | None) -> str:
    prompts = [record for record in read_jsonl(PROMPTS) if in_window(record, start, end)]
    turns = [record for path in TRANSCRIPTS if path.exists()
             for record in read_jsonl(path) if in_window(record, start, end)]
    humans = [record for record in turns if record.get("sender") == "human" and isinstance(record.get("text"), str)]
    claude_turns = [record for record in turns if record.get("source") != "chatgpt-web"]
    chatgpt_turns = [record for record in turns if record.get("source") == "chatgpt-web"]
    instagram = [record for record in read_jsonl(INSTAGRAM) if in_window(record, start, end)]

    texts = [record["text"] for record in humans]
    prompt_texts = [record.get("text", "") for record in prompts if isinstance(record.get("text"), str)]
    human_lengths = [len(text) for text in texts]
    by_month = Counter(month(record.get("ts")) for record in humans)
    repeated = Counter(re.sub(r"\s+", " ", text.strip().lower()) for text in texts)
    exact_repeats = sum(count - 1 for text, count in repeated.items() if len(text) >= 40 and count > 1)
    evidence = sum(bool(EVIDENCE_TERMS.search(text)) for text in texts)
    challenge = sum(bool(CHALLENGE_TERMS.search(text)) for text in texts)
    reconsider = sum(bool(RECONSIDER_TERMS.search(text)) for text in texts)
    secret_hits = sum(bool(SECRET_TERMS.search(record.get("text", ""))) for record in prompts + humans + instagram)
    short = sum(len(text.strip()) < 80 for text in texts)

    period = f"{start.date().isoformat() if start else 'corpus start'} to {end.date().isoformat() if end else 'corpus end'}"
    lines = [
        "# Retrospective Evaluator Output",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Window: {period}",
        "",
        "## Method and limits",
        "",
        "- Counts all eligible records in the three landed, human-authored views. The prompt and transcript views overlap; they are reported separately and never summed.",
        "- ChatGPT follows each conversation's exported canonical branch; abandoned response branches are excluded. Binary/image-only turns remain in the raw export but are absent from text counts.",
        "- Keyword signals and message length are review queues, not behavioural findings. They cannot establish intent, outcome quality, or causal change.",
        "- The evaluator never emits raw message text. Qualitative findings require a human reviewer to return to the source conversation and quote it with context.",
        "",
        "## Census",
        "",
        "| View | Eligible records |",
        "|---|---:|",
        f"| Canonical prompt corpus | {len(prompts):,} |",
        f"| Claude transcript human turns | {sum(record.get('sender') == 'human' for record in claude_turns):,} |",
        f"| Claude transcript total text turns | {len(claude_turns):,} |",
        f"| ChatGPT transcript human text turns | {sum(record.get('sender') == 'human' for record in chatgpt_turns):,} |",
        f"| ChatGPT transcript total text turns | {len(chatgpt_turns):,} |",
        f"| Instagram operator messages | {len(instagram):,} |",
        "",
        "## Review signals",
        "",
        "| Signal | Result | Interpretation boundary |",
        "|---|---:|---|",
        f"| Median human-turn length | {median(human_lengths):.0f} characters | Register-dependent; not a quality score. |",
        f"| Human turns under 80 characters | {percentage(short, len(texts))} | A proxy for prompts likely to need context, not proof of under-specification. |",
        f"| Evidence/verification vocabulary | {percentage(evidence, len(texts))} | A review queue for epistemic standards, not evidence of correctness. |",
        f"| Challenge-seeking vocabulary | {percentage(challenge, len(texts))} | Does not measure whether challenge changed a decision. |",
        f"| Reconsideration vocabulary | {percentage(reconsider, len(texts))} | English-only lower bound; does not prove a decision reversal. |",
        f"| Exact repeated substantive turns | {exact_repeats:,} | Duplicate/retry signal only; semantic repetition needs review. |",
        f"| Possible secret-bearing records | {secret_hits:,} | Security review required; this count does not disclose content. |",
        "",
        "## Human-turn volume by month",
        "",
        "| Month | Turns |",
        "|---|---:|",
    ]
    lines.extend(f"| {label} | {count:,} |" for label, count in sorted(by_month.items()))
    lines.extend(["", "## Most iterative reasoning conversations", "", "| Conversation | Human turns | Human characters | Turns at least 5,000 characters |", "|---|---:|---:|---:|"])
    lines.extend(f"| {title.replace('|', '/')} | {turn_count:,} | {characters:,} | {large_turns:,} |"
                 for title, turn_count, characters, large_turns in largest_conversations(turns))
    lines.extend([
        "",
        "## Required manual checks",
        "",
        "1. Sample high-signal conversations from different months before stating any longitudinal claim. Do not use long pasted material as evidence of a personal preoccupation.",
        "2. Separate private/casual register from work/reasoning register; neither predicts the other reliably.",
        "3. Inspect every possible-secret hit locally; rotate exposed credentials and redact only derived artefacts, preserving raw provenance under access control.",
        "4. Record each report hypothesis as confirmed, refined, or discarded by the operator before changing standing context.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", help="inclusive UTC date/time (for example 2026-01-01)")
    parser.add_argument("--end", help="exclusive UTC date/time (for example 2026-08-01)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    start = parse_timestamp(args.start + "T00:00:00Z") if args.start and len(args.start) == 10 else parse_timestamp(args.start)
    end = parse_timestamp(args.end + "T00:00:00Z") if args.end and len(args.end) == 10 else parse_timestamp(args.end)
    if args.start and start is None or args.end and end is None:
        parser.error("--start and --end must be ISO dates or timestamps")
    if start and end and end <= start:
        parser.error("--end must be later than --start")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report(start, end), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
