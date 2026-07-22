#!/usr/bin/env python3
"""Build a deterministic month/review index for a ChatGPT transcript JSONL.

The index deliberately contains metadata and source locators, not message text.  It gives a
reviewer a complete chronological queue while keeping the transcript itself as the evidence
source.  Missing calendar months are emitted explicitly so absence is not mistaken for a quiet
period supported by evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "corpus/transcripts/chatgpt_conversations_gpt2_2026.jsonl"
DEFAULT_JSON = ROOT / "retrospectives/gpt2_2026-month-index.json"
DEFAULT_MARKDOWN = ROOT / "retrospectives/gpt2_2026-month-index.md"


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def month_after(value: str) -> str:
    year, month = map(int, value.split("-"))
    return f"{year + (month == 12):04d}-{1 if month == 12 else month + 1:02d}"


def month_range(first: str, last: str) -> list[str]:
    values: list[str] = []
    current = first
    while current <= last:
        values.append(current)
        current = month_after(current)
    return values


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_index(path: Path) -> dict:
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    month_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    namespaces: set[str] = set()
    total_records = 0
    untimestamped = 0

    with path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"non-object record at {path}:{line_no}")
            sender = record.get("sender")
            if sender not in {"human", "assistant"}:
                raise ValueError(f"invalid sender at {path}:{line_no}: {sender!r}")
            text = record.get("text")
            if not isinstance(text, str):
                raise ValueError(f"non-text record at {path}:{line_no}")
            namespace = record.get("export_namespace")
            if isinstance(namespace, str) and namespace:
                namespaces.add(namespace)
            timestamp = parse_timestamp(record.get("ts"))
            total_records += 1
            if timestamp is None:
                untimestamped += 1
                continue

            month = timestamp.strftime("%Y-%m")
            conv_uuid = str(record.get("conv_uuid") or "missing-conversation-id")
            title = str(record.get("conversation") or "Untitled ChatGPT conversation")
            conversations = grouped[month]
            conversation = conversations.setdefault(
                conv_uuid,
                {
                    "conv_uuid": conv_uuid,
                    "title": title,
                    "first_ts": record["ts"],
                    "last_ts": record["ts"],
                    "line_start": line_no,
                    "line_end": line_no,
                    "human_turns": 0,
                    "assistant_turns": 0,
                    "human_characters": 0,
                    "assistant_characters": 0,
                },
            )
            conversation["first_ts"] = min(conversation["first_ts"], record["ts"])
            conversation["last_ts"] = max(conversation["last_ts"], record["ts"])
            conversation["line_start"] = min(conversation["line_start"], line_no)
            conversation["line_end"] = max(conversation["line_end"], line_no)
            conversation[f"{sender}_turns"] += 1
            conversation[f"{sender}_characters"] += len(text)
            month_totals[month][f"{sender}_turns"] += 1
            month_totals[month][f"{sender}_characters"] += len(text)

    populated = sorted(grouped)
    if not populated:
        raise ValueError(f"no timestamped transcript records in {path}")

    months: list[dict] = []
    for month in month_range(populated[0], populated[-1]):
        conversations = sorted(
            grouped.get(month, {}).values(),
            key=lambda item: (item["first_ts"], item["conv_uuid"]),
        )
        totals = month_totals.get(month, {})
        months.append(
            {
                "month": month,
                "status": "present" if conversations else "gap",
                "conversation_count": len(conversations),
                "human_turns": totals.get("human_turns", 0),
                "assistant_turns": totals.get("assistant_turns", 0),
                "human_characters": totals.get("human_characters", 0),
                "assistant_characters": totals.get("assistant_characters", 0),
                "conversations": conversations,
            }
        )

    return {
        "schema_version": 1,
        "source": str(path.resolve()),
        "source_sha256": sha256(path),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "export_namespaces": sorted(namespaces),
        "total_records": total_records,
        "untimestamped_records": untimestamped,
        "first_month": populated[0],
        "last_month": populated[-1],
        "months": months,
    }


def markdown(index: dict) -> str:
    lines = [
        "# Second ChatGPT Account — Month Review Index",
        "",
        "This is a deterministic review queue. It reproduces no message text; every claim in",
        "the qualitative ledger must resolve to the namespaced transcript line locators listed",
        "for its source conversations. A `gap` means the export contains no timestamped text",
        "turns for that calendar month—not that nothing happened in the operator's life.",
        "",
        f"- Source: `{index['source']}`",
        f"- Source SHA-256: `{index['source_sha256']}`",
        f"- Namespace(s): `{', '.join(index['export_namespaces']) or 'none'}`",
        f"- Retained text turns: {index['total_records']:,}",
        f"- Review span: {index['first_month']} through {index['last_month']}",
        "",
        "| Month | Evidence | Conversations | Human turns | Assistant turns | Human characters |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in index["months"]:
        lines.append(
            f"| {item['month']} | {item['status']} | {item['conversation_count']:,} | "
            f"{item['human_turns']:,} | {item['assistant_turns']:,} | "
            f"{item['human_characters']:,} |"
        )
    lines.extend(["", "## Conversation queues", ""])
    for item in index["months"]:
        lines.append(f"### {item['month']}")
        lines.append("")
        if item["status"] == "gap":
            lines.extend(["No retained timestamped text turns.", ""])
            continue
        lines.extend(
            [
                "| First timestamp | Conversation | H/A turns | Transcript lines |",
                "|---|---|---:|---:|",
            ]
        )
        for conversation in item["conversations"]:
            title = conversation["title"].replace("|", "/").replace("\n", " ")
            lines.append(
                f"| {conversation['first_ts']} | {title} | "
                f"{conversation['human_turns']}/{conversation['assistant_turns']} | "
                f"{conversation['line_start']}–{conversation['line_end']} |"
            )
        lines.append("")
    return "\n".join(lines)


def write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    index = build_index(args.input.expanduser().resolve())
    write_private(args.output_json, json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    write_private(args.output_markdown, markdown(index) + "\n")
    print(json.dumps({
        "json": str(args.output_json.resolve()),
        "markdown": str(args.output_markdown.resolve()),
        "months": len(index["months"]),
        "present_months": sum(item["status"] == "present" for item in index["months"]),
        "gaps": sum(item["status"] == "gap" for item in index["months"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
