#!/usr/bin/env python3
"""Extract canonical text turns from a sharded ChatGPT account export.

The export's ``mapping`` contains abandoned branches as well as the branch visible when
the export was created.  This extractor follows ``current_node`` back to the root and
reverses that chain, so retries and superseded answers are not silently counted as if they
were separate conversations.

Outputs:
  corpus/raw/chatgpt_prompts_<date>.jsonl
  corpus/transcripts/chatgpt_conversations.jsonl

For a second account/export, pass ``--namespace <stable-id>``. This writes separate
namespaced views and prevents the established canonical transcript from being overwritten.

Binary attachments remain only in the immutable export.  Multimodal messages contribute
their string text parts; image-only messages are counted as skipped, not fabricated.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "corpus" / "raw"
TRANSCRIPTS = ROOT / "corpus" / "transcripts"


def _find_archive() -> Path:
    candidates = sorted(
        list(ROOT.glob("*chatgpt*.zip"))
        + list((ROOT / "corpus" / "chatgpt-export").glob("*.zip"))
    )
    if not candidates:
        raise FileNotFoundError("no ChatGPT export zip found in the project root or corpus/chatgpt-export")
    if len(candidates) > 1:
        raise RuntimeError("multiple ChatGPT export zips found; pass --archive explicitly")
    return candidates[0]


def _iso_timestamp(value: object) -> str | None:
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    # Some export variants use milliseconds rather than seconds.
    if value > 10_000_000_000:
        value /= 1_000
    try:
        return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
    except (OSError, OverflowError, ValueError):
        return None


def _text(content: object) -> str | None:
    if not isinstance(content, dict):
        return None
    parts = content.get("parts")
    if not isinstance(parts, list):
        return None
    text_parts: list[str] = []
    for part in parts:
        if isinstance(part, str) and part.strip():
            text_parts.append(part.strip())
        elif isinstance(part, dict) and part.get("content_type") in {"text", "input_text"}:
            value = part.get("text")
            if isinstance(value, str) and value.strip():
                text_parts.append(value.strip())
    value = "\n".join(text_parts).strip()
    return value or None


def _canonical_messages(conversation: dict) -> list[dict]:
    mapping = conversation.get("mapping") or {}
    node_id = conversation.get("current_node")
    messages: list[dict] = []
    seen: set[str] = set()
    while isinstance(node_id, str) and node_id not in seen and node_id in mapping:
        seen.add(node_id)
        node = mapping[node_id]
        message = node.get("message") if isinstance(node, dict) else None
        if isinstance(message, dict):
            messages.append(message)
        node_id = node.get("parent") if isinstance(node, dict) else None
    messages.reverse()
    return messages


def extract(archive: Path, stamp: str, namespace: str | None = None) -> tuple[Path, Path, Counter]:
    prompt_records: list[dict] = []
    transcript_records: list[dict] = []
    stats: Counter = Counter()
    dates: list[str] = []

    with zipfile.ZipFile(archive) as export:
        shards = sorted(
            name for name in export.namelist()
            if name.startswith("conversations-") and name.endswith(".json")
        )
        if not shards:
            raise RuntimeError("export contains no conversations-*.json shards")
        stats["shards"] = len(shards)
        for shard in shards:
            conversations = json.loads(export.read(shard))
            if not isinstance(conversations, list):
                raise RuntimeError(f"{shard} is not a JSON array")
            for conversation in conversations:
                if not isinstance(conversation, dict):
                    continue
                stats["conversations"] += 1
                conversation_id = conversation.get("id") or conversation.get("conversation_id")
                title = str(conversation.get("title") or "Untitled ChatGPT conversation")
                fallback_ts = _iso_timestamp(conversation.get("create_time"))
                text_turns_before = len(transcript_records)
                for message in _canonical_messages(conversation):
                    role = (message.get("author") or {}).get("role")
                    if role not in {"user", "assistant"}:
                        stats[f"skipped_role:{role}"] += 1
                        continue
                    text = _text(message.get("content"))
                    if not text:
                        stats[f"skipped_nontext:{role}"] += 1
                        continue
                    ts = _iso_timestamp(message.get("create_time")) or fallback_ts
                    if ts:
                        dates.append(ts)
                    sender = "human" if role == "user" else "assistant"
                    transcript_records.append({
                        "ts": ts,
                        "text": text,
                        "conversation": title,
                        "conv_uuid": conversation_id,
                        "sender": sender,
                        "source": "chatgpt-web",
                        **({"export_namespace": namespace} if namespace else {}),
                    })
                    stats[f"text_turns:{role}"] += 1
                    if role == "user":
                        prompt_records.append({
                            "ts": ts,
                            "text": text,
                            "source": f"chatgpt-web:{title[:50]}",
                            "session": conversation_id,
                            "channel": "chatgpt-web",
                            **({"export_namespace": namespace} if namespace else {}),
                        })
                if len(transcript_records) > text_turns_before:
                    stats["text_conversations"] += 1
                else:
                    stats["conversations_without_text"] += 1

    RAW.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    suffix = f"_{namespace}" if namespace else ""
    prompt_path = RAW / f"chatgpt_prompts{suffix}_{stamp}.jsonl"
    transcript_path = TRANSCRIPTS / f"chatgpt_conversations{suffix}.jsonl"
    prompt_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in prompt_records) + "\n",
        encoding="utf-8",
    )
    transcript_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in transcript_records) + "\n",
        encoding="utf-8",
    )
    if dates:
        stats["first_text_turn"] = min(dates)
        stats["last_text_turn"] = max(dates)
    return prompt_path, transcript_path, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="ChatGPT export zip; auto-detected if omitted")
    parser.add_argument("--stamp", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    parser.add_argument(
        "--namespace",
        help="stable account/export label; writes separate outputs instead of replacing canon",
    )
    args = parser.parse_args()
    if args.namespace and not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", args.namespace):
        parser.error("--namespace must match [a-z0-9][a-z0-9_-]{0,39}")
    archive = (args.archive or _find_archive()).expanduser().resolve()
    if not archive.is_file():
        parser.error(f"archive does not exist: {archive}")
    prompt_path, transcript_path, stats = extract(archive, args.stamp, args.namespace)
    print(json.dumps({
        "archive": str(archive),
        "prompts": str(prompt_path),
        "transcripts": str(transcript_path),
        "stats": dict(stats),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
