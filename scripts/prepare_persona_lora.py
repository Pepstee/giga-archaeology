#!/usr/bin/env python3
"""Prepare conservative local LoRA datasets from the unified memory database.

Two datasets are intentionally separate:

* ``speech`` uses genuine third-party -> operator exchanges from two-sided human platforms.
* ``reasoning`` uses genuine model -> operator transitions and therefore teaches critique,
  refinement and next-instruction behaviour, not independent hidden reasoning.

The script reads the SQLite authority in read-only mode and never changes provider exports.
Model-facing JSONL contains only chat messages; the provenance ledger retains exact record IDs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1
CREDENTIAL_PATTERNS = (
    re.compile(r"(?i)\b(?:password|passwd|api[_ -]?key|secret[_ -]?key|private[_ -]?key)\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\b(?:token|pin|pnr)\s*[:=]\s*[A-Za-z0-9._-]{4,}"),
)
INJECTED_PREFIXES = (
    "<system-reminder>", "<command-", "<local-command", "<recommended_plugins>",
    "<environment_context>", "<app-context>", "<permissions instructions>",
    "# agents.md instructions", "[[task:",
)
REASONING_MARKERS = re.compile(
    r"(?:\?|(?:^|\b)(?:no|but|because|actually|however|why|how|what|i think|i don['’]?t "
    r"(?:think|agree|understand)|you (?:missed|forgot|assumed)|that(?:'s| is) (?:wrong|not)|"
    r"prove|evidence|compare|analyse|analyze|explain|instead|нет|но|потому|поэтому|"
    r"думаю|считаю|почему|как|что|докаж|сравни|объясни|вместо)\b)",
    re.I,
)
CODE_LINE = re.compile(
    r"(?m)^\s*(?:def |class |import |from \S+ import |const |let |var |function |"
    r"SELECT |INSERT |UPDATE |CREATE TABLE|[A-Za-z_][A-Za-z0-9_]*\s*=\s*[\[{])"
)
LOG_LINE = re.compile(r"(?m)^(?:Traceback|Error:|Exception:|\[[0-9]{2}:[0-9]{2}:[0-9]{2}\])")


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalise(text: str) -> str:
    return " ".join(text.casefold().split())


def has_credential(text: str) -> bool:
    return any(pattern.search(text) for pattern in CREDENTIAL_PATTERNS)


def unsafe_text(text: str) -> str | None:
    lowered = text.casefold().lstrip()
    if any(lowered.startswith(prefix) for prefix in INJECTED_PREFIXES):
        return "injected_runtime_context"
    if has_credential(text):
        return "possible_credential"
    if text.count("```") >= 2 or len(CODE_LINE.findall(text)) >= 3:
        return "pasted_code"
    if len(LOG_LINE.findall(text)) >= 2:
        return "pasted_log"
    return None


def stable_split(group: str, seed: str) -> str:
    bucket = int(digest_text(group + "\0" + seed)[:12], 16) / float(16 ** 12)
    if bucket < 0.08:
        return "test"
    if bucket < 0.13:
        return "valid"
    return "train"


def ensure_new_directory(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"{path} is not empty; use a new dataset version")
    path.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_model_authored_hashes(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT normalised_sha256 FROM messages "
            "WHERE author_role='model' AND trim(text)<>''"
        )
    }


def rows_by_thread(
    connection: sqlite3.Connection,
    *,
    platforms: tuple[str, ...],
    since: str,
) -> dict[int, list[sqlite3.Row]]:
    placeholders = ",".join("?" for _ in platforms)
    rows = connection.execute(
        f"""
        SELECT m.message_pk,m.record_id,m.platform,m.namespace,m.thread_pk,t.title AS thread_title,
               t.coverage,m.author_name,m.author_role,m.direction,m.timestamp,m.timestamp_epoch,
               m.text,m.normalised_sha256,m.message_type
        FROM messages m JOIN threads t ON t.thread_pk=m.thread_pk
        WHERE m.platform IN ({placeholders}) AND m.timestamp>=?
          AND trim(m.text)<>'' AND m.author_role IN ('operator','third_party','model')
        ORDER BY m.thread_pk,m.timestamp,m.message_pk
        """,
        (*platforms, since),
    ).fetchall()
    output: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        output[row["thread_pk"]].append(row)
    return output


def build_speech(
    connection: sqlite3.Connection,
    ai_hashes: set[str],
    since: str,
) -> tuple[list[dict], list[dict], Counter]:
    examples: list[dict] = []
    quarantine: list[dict] = []
    stats = Counter()
    threads = rows_by_thread(
        connection,
        platforms=("instagram", "telegram"),
        since=since,
    )
    for thread_rows in threads.values():
        index = 0
        while index < len(thread_rows):
            if thread_rows[index]["author_role"] != "operator":
                index += 1
                continue
            start = index
            while index + 1 < len(thread_rows) and thread_rows[index + 1]["author_role"] == "operator":
                current_epoch = thread_rows[index]["timestamp_epoch"]
                next_epoch = thread_rows[index + 1]["timestamp_epoch"]
                if (
                    current_epoch is not None and next_epoch is not None
                    and next_epoch - current_epoch > 30 * 60
                ):
                    break
                index += 1
            target_rows = thread_rows[start:index + 1]
            previous = thread_rows[max(0, start - 8):start]
            if not previous or not any(row["author_role"] == "third_party" for row in previous):
                stats["no_incoming_context"] += 1
                index += 1
                continue

            target = "\n".join(row["text"].strip() for row in target_rows if row["text"].strip())
            if not (2 <= len(target) <= 1800):
                stats["target_length"] += 1
                index += 1
                continue
            reason = unsafe_text(target)
            if reason:
                quarantine.append({
                    "reason": reason,
                    "target_record_ids": [row["record_id"] for row in target_rows],
                })
                stats[f"quarantine_{reason}"] += 1
                index += 1
                continue
            if any(row["normalised_sha256"] in ai_hashes for row in target_rows):
                quarantine.append({
                    "reason": "exact_model_text_reuse",
                    "target_record_ids": [row["record_id"] for row in target_rows],
                })
                stats["quarantine_exact_model_text_reuse"] += 1
                index += 1
                continue

            # Collapse adjacent context messages by role. Author labels preserve group context.
            chat_context: list[dict] = []
            for row in previous:
                role = "assistant" if row["author_role"] == "operator" else "user"
                content = row["text"].strip()
                if row["author_role"] == "third_party" and row["coverage"] != "two_sided_direct":
                    content = f"[{row['author_name']}]: {content}"
                if chat_context and chat_context[-1]["role"] == role:
                    chat_context[-1]["content"] += "\n" + content
                else:
                    chat_context.append({"role": role, "content": content})
            while chat_context and chat_context[0]["role"] == "assistant":
                chat_context.pop(0)
            if not chat_context or chat_context[-1]["role"] != "user":
                # The burst must be a reply to a third party, not a self-initiated message.
                stats["not_direct_reply"] += 1
                index += 1
                continue
            context_chars = sum(len(item["content"]) for item in chat_context)
            if context_chars > 3500 or any(unsafe_text(item["content"]) for item in chat_context):
                stats["unsafe_or_long_context"] += 1
                index += 1
                continue

            timestamp = target_rows[-1]["timestamp"]
            example_id = digest_text(
                "\0".join(row["record_id"] for row in previous + target_rows)
            )
            examples.append({
                "example_id": example_id,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Reply as Artiom in his private conversational voice. "
                            "Match the language, relationship register, and natural brevity of the context."
                        ),
                    },
                    *chat_context,
                    {"role": "assistant", "content": target},
                ],
                "meta": {
                    "target_semantics": "direct_reply",
                    "mode": "mixed_private_experimental",
                    "platform": target_rows[-1]["platform"],
                    "namespace": target_rows[-1]["namespace"],
                    "thread_pk": target_rows[-1]["thread_pk"],
                    "thread_title": target_rows[-1]["thread_title"],
                    "timestamp": timestamp,
                    "context_record_ids": [row["record_id"] for row in previous],
                    "target_record_ids": [row["record_id"] for row in target_rows],
                },
            })
            stats["accepted"] += 1
            stats[f"accepted_{target_rows[-1]['platform']}"] += 1
            index += 1
    return examples, quarantine, stats


def build_reasoning(
    connection: sqlite3.Connection,
    ai_hashes: set[str],
    since: str,
) -> tuple[list[dict], list[dict], Counter]:
    examples: list[dict] = []
    quarantine: list[dict] = []
    stats = Counter()
    threads = rows_by_thread(
        connection,
        platforms=("chatgpt", "claude"),
        since=since,
    )
    for thread_rows in threads.values():
        for index, row in enumerate(thread_rows):
            if row["author_role"] != "operator" or index == 0:
                continue
            previous = thread_rows[index - 1]
            if previous["author_role"] != "model":
                stats["no_model_stimulus"] += 1
                continue
            target = row["text"].strip()
            stimulus = previous["text"].strip()
            if not (24 <= len(target) <= 1800 and 40 <= len(stimulus) <= 5000):
                stats["length_filter"] += 1
                continue
            if not REASONING_MARKERS.search(target):
                stats["no_reasoning_marker"] += 1
                continue
            reason = unsafe_text(target)
            context_reason = unsafe_text(stimulus)
            if reason or context_reason:
                quarantine.append({
                    "reason": reason or f"stimulus_{context_reason}",
                    "stimulus_record_id": previous["record_id"],
                    "target_record_id": row["record_id"],
                })
                stats[f"quarantine_{reason or context_reason}"] += 1
                continue
            if row["normalised_sha256"] in ai_hashes:
                quarantine.append({
                    "reason": "exact_model_text_reuse",
                    "stimulus_record_id": previous["record_id"],
                    "target_record_id": row["record_id"],
                })
                stats["quarantine_exact_model_text_reuse"] += 1
                continue
            example_id = digest_text(previous["record_id"] + "\0" + row["record_id"])
            examples.append({
                "example_id": example_id,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Respond to the preceding analysis as Artiom. Identify errors, "
                            "refine assumptions, state disagreements, or give the next precise instruction."
                        ),
                    },
                    {"role": "user", "content": stimulus},
                    {"role": "assistant", "content": target},
                ],
                "meta": {
                    "target_semantics": "operator_next_turn",
                    "semantic_limit": (
                        "teaches critique/refinement/steering, not independent task reasoning"
                    ),
                    "mode": "reasoning_steering_experimental",
                    "platform": row["platform"],
                    "namespace": row["namespace"],
                    "thread_pk": row["thread_pk"],
                    "thread_title": row["thread_title"],
                    "timestamp": row["timestamp"],
                    "stimulus_record_id": previous["record_id"],
                    "target_record_id": row["record_id"],
                },
            })
            stats["accepted"] += 1
            stats[f"accepted_{row['platform']}"] += 1
    return examples, quarantine, stats


def emit_dataset(
    examples: list[dict],
    quarantine: list[dict],
    stats: Counter,
    output: Path,
    *,
    dataset_kind: str,
    source_db: Path,
    seed: str,
    user_authorisation: str,
) -> None:
    ensure_new_directory(output)
    splits: dict[str, list[dict]] = {"train": [], "valid": [], "test": []}
    provenance: list[dict] = []
    seen = set()
    duplicates = 0
    for example in examples:
        if example["example_id"] in seen:
            duplicates += 1
            continue
        seen.add(example["example_id"])
        meta = example["meta"]
        group = f"{meta['platform']}\0{meta['thread_pk']}\0{meta['timestamp'][:7]}"
        split = stable_split(group, seed)
        splits[split].append({"messages": example["messages"]})
        provenance.append({
            "example_id": example["example_id"],
            "split": split,
            **meta,
        })
    for split, rows in splits.items():
        rows.sort(key=lambda row: digest_text(json.dumps(row, sort_keys=True, ensure_ascii=False)))
        write_jsonl(output / f"{split}.jsonl", rows)
    provenance.sort(key=lambda row: row["example_id"])
    write_jsonl(output / "provenance.jsonl", provenance)
    write_jsonl(output / "quarantine.jsonl", quarantine)
    test_hash = file_digest(output / "test.jsonl")
    lock = {
        "dataset_kind": dataset_kind,
        "test_sha256": test_hash,
        "records": len(splits["test"]),
        "rule": "Never add this file to training data for a later version.",
    }
    (output / "test.lock.json").write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_kind": dataset_kind,
        "source_database": str(source_db),
        "source_database_sha256_at_extraction": file_digest(source_db),
        "source_hash_note": (
            "Later Tier-3 claim insertion may change the SQLite file hash without changing "
            "the Tier-1 messages from which this dataset was extracted."
        ),
        "privacy_profile": "local_private_only",
        "split_contract": {
            "method": "stable hash of platform + thread + calendar month",
            "seed": seed,
            "fractions": {"train": 0.87, "valid": 0.05, "test": 0.08},
        },
        "counts": {split: len(rows) for split, rows in splits.items()},
        "duplicates_removed": duplicates,
        "quarantine_records": len(quarantine),
        "filter_counts": dict(stats),
        "test_sha256": test_hash,
        "training_authorised": True,
        "training_authorisation": user_authorisation,
        "promotion_authorised": False,
        "promotion_blocker": (
            "Experimental mixed-mode adapter; requires held-out behavioural, privacy, "
            "mode-isolation and memory-separation review before deployment."
        ),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for path in output.iterdir():
        path.chmod(0o600)
    print(json.dumps({
        "dataset": dataset_kind,
        "output": str(output),
        "counts": manifest["counts"],
        "quarantine": len(quarantine),
        "test_sha256": test_hash,
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--speech-since", default="2024-01-01")
    parser.add_argument("--reasoning-since", default="2024-01-01")
    parser.add_argument("--seed", default="giga-persona-20260726")
    args = parser.parse_args()

    db = args.db.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()
    connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    ai_hashes = load_model_authored_hashes(connection)

    speech, speech_quarantine, speech_stats = build_speech(
        connection, ai_hashes, args.speech_since
    )
    reasoning, reasoning_quarantine, reasoning_stats = build_reasoning(
        connection, ai_hashes, args.reasoning_since
    )
    authorisation = (
        "Operator directive on 2026-07-26: plan the LLM LoRA tuning on my data, "
        "then proceed with LoRA tuning. This authorises a local experimental run, "
        "not adapter promotion."
    )
    emit_dataset(
        speech, speech_quarantine, speech_stats,
        output_root / "speech-current-experimental-v1",
        dataset_kind="speech_direct_reply",
        source_db=db,
        seed=args.seed + "-speech",
        user_authorisation=authorisation,
    )
    emit_dataset(
        reasoning, reasoning_quarantine, reasoning_stats,
        output_root / "reasoning-steering-experimental-v1",
        dataset_kind="operator_next_turn",
        source_db=db,
        seed=args.seed + "-reasoning",
        user_authorisation=authorisation,
    )
    connection.close()


if __name__ == "__main__":
    main()
