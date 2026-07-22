#!/usr/bin/env python3
"""Build auditable, provider-neutral fine-tuning datasets from canonical GIGA views.

This script does not train a model. It creates versioned candidate/split artefacts with
provenance, deterministic leakage-resistant splits, sensitive-record quarantine and a
manifest. Raw corpus files are never modified.

Commands:
  transcript-candidates  Invert AI-chat transcripts so the model learns Artiom's next turn.
  prepare-pairs          Validate, deduplicate, screen and split chat-format pairs.
  audit-style            Audit one-sided style text (for example Discord); never fabricates
                         missing conversation context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = 1
SPLITS = ("train", "valid", "test")
SPLIT_PRIORITY = {"train": 0, "valid": 1, "test": 2}

CREDENTIAL_PATTERNS = (
    re.compile(r"(?i)\b(?:password|passwd|api[_ -]?key|secret[_ -]?key|private[_ -]?key)\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\b(?:token|pin|pnr)\s*[:=]\s*[A-Za-z0-9._-]{4,}"),
)
EMAIL_RE = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
URL_RE = re.compile(r"(?i)\bhttps?://\S+")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
HANDLE_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_.]{2,30}\b")

INJECTED_PREFIXES = (
    "<system-reminder>", "<command-", "<local-command", "<recommended_plugins>",
    "<environment_context>", "<app-context>", "<permissions instructions>",
    "# AGENTS.md instructions", "[[task:",
)


def normalise(text: str) -> str:
    return " ".join(text.casefold().split())


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_jsonl(path: Path) -> Iterable[tuple[int, dict]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: record is not an object")
            yield line_number, value


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def pair_messages(record: dict) -> tuple[str, str]:
    messages = record.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError("messages must contain at least one user turn and one assistant turn")
    if messages[-1].get("role") != "assistant":
        raise ValueError("last message must be the Artiom/assistant target")
    if any(not isinstance(item, dict) or item.get("role") not in {"system", "user", "assistant"}
           or not isinstance(item.get("content"), str) or not item["content"].strip()
           for item in messages):
        raise ValueError("every message needs role system|user|assistant and non-empty content")
    user_turns = [item["content"] for item in messages[:-1] if item["role"] == "user"]
    if not user_turns:
        raise ValueError("example has no user/context turn")
    return "\n".join(user_turns), messages[-1]["content"]


def pair_hash(record: dict) -> str:
    context, target = pair_messages(record)
    return digest_text(normalise(context) + "\0" + normalise(target))


def context_hash(record: dict) -> str:
    context, _ = pair_messages(record)
    return digest_text(normalise(context))


def has_credential(text: str) -> bool:
    return any(pattern.search(text) for pattern in CREDENTIAL_PATTERNS)


def privacy_flags(text: str) -> list[str]:
    flags = []
    if EMAIL_RE.search(text):
        flags.append("email")
    if PHONE_RE.search(text):
        flags.append("phone")
    if URL_RE.search(text):
        flags.append("url")
    if HANDLE_RE.search(text):
        flags.append("handle")
    return flags


def redact_cloud(text: str) -> str:
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    text = URL_RE.sub("<URL>", text)
    return HANDLE_RE.sub("<HANDLE>", text)


def redact_record(record: dict) -> dict:
    clone = json.loads(json.dumps(record, ensure_ascii=False))
    for message in clone["messages"]:
        message["content"] = redact_cloud(message["content"])
    return clone


def month_key(timestamp: object) -> str:
    value = str(timestamp or "undated")
    match = re.match(r"(\d{4})-(\d{2})", value)
    return f"{match.group(1)}-{match.group(2)}" if match else "undated"


def stable_split(record: dict, seed: str, valid_fraction: float, test_fraction: float) -> str:
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    thread = str(meta.get("thread") or meta.get("conversation") or meta.get("source") or "unknown")
    group = f"{thread}\0{month_key(meta.get('ts'))}\0{seed}"
    bucket = int(digest_text(group)[:12], 16) / float(16 ** 12)
    if bucket < test_fraction:
        return "test"
    if bucket < test_fraction + valid_fraction:
        return "valid"
    return "train"


def ensure_output(output: Path, force: bool) -> None:
    if output.exists() and any(output.iterdir()) and not force:
        raise FileExistsError(f"{output} is not empty; use a new version or --force")
    output.mkdir(parents=True, exist_ok=True)


def load_mode_map(path: Path | None) -> tuple[dict, str | None]:
    if path is None:
        return {"default_mode": "unassigned", "threads": {}}, None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("threads", {}), dict):
        raise ValueError("mode map must be an object with a threads object")
    value.setdefault("default_mode", "unassigned")
    return value, file_digest(path)


def quality_flags(context: str, target: str) -> list[str]:
    flags = []
    target_norm = normalise(target)
    if len(target_norm) < 4:
        flags.append("low_information")
    if len(context) > 8_000 or len(target) > 4_000:
        flags.append("very_long")
    if "```" in target or re.search(r"(?m)^\s*(?:def |class |import |from \S+ import )", target):
        flags.append("pasted_code")
    if re.search(r"(?i)\b(?:you missed|you forgot|that's wrong|that is wrong|i disagree|not what i|no,)\b", target):
        flags.append("correction")
    if target_norm in {"yes", "correct", "exactly", "good", "perfect", "that's right", "that is right"}:
        flags.append("acceptance")
    return flags


def prepare_pairs(args: argparse.Namespace) -> int:
    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    ensure_output(output, args.force)
    mode_map, mode_map_hash = load_mode_map(args.mode_map)

    valid: list[dict] = []
    invalid: list[dict] = []
    quarantine: list[dict] = []
    seen_pairs: set[str] = set()
    duplicate_count = 0
    privacy_counter: Counter[str] = Counter()
    quality_counter: Counter[str] = Counter()
    mode_counter: Counter[str] = Counter()
    excluded_mode = 0

    for line_number, record in read_jsonl(source):
        try:
            context, target = pair_messages(record)
        except ValueError as exc:
            invalid.append({"line": line_number, "error": str(exc)})
            continue
        identity = pair_hash(record)
        if identity in seen_pairs:
            duplicate_count += 1
            continue
        seen_pairs.add(identity)
        joined = context + "\n" + target
        if has_credential(joined):
            quarantine.append({"reason": "possible_credential", "source_line": line_number,
                               "record": record})
            continue
        flags = privacy_flags(joined)
        privacy_counter.update(flags)
        qflags = quality_flags(context, target)
        quality_counter.update(qflags)
        prepared = redact_record(record) if args.privacy == "cloud" else record
        prepared.setdefault("meta", {})
        thread = str(prepared["meta"].get("thread") or "")
        mode = str(mode_map.get("threads", {}).get(thread) or prepared["meta"].get("mode")
                   or mode_map.get("default_mode") or "unassigned")
        if mode == "exclude" or (args.only_mode and mode != args.only_mode):
            excluded_mode += 1
            continue
        mode_counter[mode] += 1
        prepared["meta"].update({
            "example_id": identity,
            "source_file": str(source),
            "source_line": line_number,
            "privacy_flags": flags,
            "quality_flags": qflags,
            "mode": mode,
        })
        valid.append(prepared)

    assigned: dict[str, list[dict]] = {split: [] for split in SPLITS}
    initial: dict[str, str] = {}
    by_context: defaultdict[str, list[str]] = defaultdict(list)
    by_id = {}
    for record in valid:
        identity = record["meta"]["example_id"]
        split = stable_split(record, args.seed, args.valid_fraction, args.test_fraction)
        initial[identity] = split
        by_context[context_hash(record)].append(identity)
        by_id[identity] = record

    # Identical prompts must never appear on both sides of an evaluation boundary. If a
    # context occurs in several relationship/month groups, assign all copies to the most
    # protected split selected for any copy (test > valid > train).
    final = dict(initial)
    for identities in by_context.values():
        protected = max((initial[item] for item in identities), key=SPLIT_PRIORITY.get)
        for identity in identities:
            final[identity] = protected
    for identity, split in final.items():
        assigned[split].append(by_id[identity])

    provenance = []
    for split in SPLITS:
        assigned[split].sort(key=lambda record: record["meta"]["example_id"])
        model_records = []
        for record in assigned[split]:
            provenance.append({"example_id": record["meta"]["example_id"], "split": split,
                               "meta": record.get("meta", {})})
            model_records.append({"messages": record["messages"]})
        write_jsonl(output / f"{split}.jsonl", model_records)

    write_jsonl(output / "provenance.jsonl", provenance)
    write_jsonl(output / "quarantine.jsonl", quarantine)
    (output / "invalid.json").write_text(json.dumps(invalid, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "source_sha256": file_digest(source),
        "privacy_profile": args.privacy,
        "mode_map": str(args.mode_map.resolve()) if args.mode_map else None,
        "mode_map_sha256": mode_map_hash,
        "only_mode": args.only_mode,
        "split_contract": {
            "method": "stable hash of relationship/conversation plus calendar month",
            "seed": args.seed,
            "valid_fraction": args.valid_fraction,
            "test_fraction": args.test_fraction,
            "identical_contexts_coalesced": True,
        },
        "counts": {split: len(assigned[split]) for split in SPLITS},
        "input_records": len(valid) + len(invalid) + len(quarantine) + duplicate_count,
        "exact_duplicates_removed": duplicate_count,
        "invalid_records": len(invalid),
        "quarantined_possible_credentials": len(quarantine),
        "privacy_flag_counts": dict(privacy_counter),
        "quality_flag_counts": dict(quality_counter),
        "mode_counts": dict(mode_counter),
        "excluded_by_mode_policy": excluded_mode,
        "unassigned_mode_records": mode_counter.get("unassigned", 0),
        "third_party_context_review_required": True,
        "training_authorised": False,
        "authorisation_note": "Set only after manual privacy review and locked evaluation creation.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


def looks_injected(text: str) -> bool:
    return text.lstrip().startswith(INJECTED_PREFIXES)


def merge_adjacent(messages: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for message in messages:
        if merged and merged[-1]["role"] == message["role"]:
            merged[-1]["content"] += "\n" + message["content"]
        else:
            merged.append(dict(message))
    return merged


def transcript_candidates(args: argparse.Namespace) -> int:
    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists() and not args.force:
        raise FileExistsError(f"{output} exists; choose a versioned path or use --force")
    conversations: defaultdict[str, list[dict]] = defaultdict(list)
    for line_number, record in read_jsonl(source):
        sender = record.get("sender")
        text = record.get("text")
        if sender not in {"human", "assistant"} or not isinstance(text, str) or not text.strip():
            continue
        if looks_injected(text):
            continue
        key = str(record.get("conv_uuid") or record.get("conversation") or f"line:{line_number}")
        item = dict(record)
        item["_line"] = line_number
        conversations[key].append(item)

    candidates = []
    skipped_no_stimulus = 0
    for conversation_id, turns in conversations.items():
        turns.sort(key=lambda record: (str(record.get("ts") or ""), record["_line"]))
        for index, turn in enumerate(turns):
            if turn["sender"] != "human" or index == 0:
                continue
            prior = turns[max(0, index - args.context_turns):index]
            mapped = [
                {"role": "assistant" if item["sender"] == "human" else "user",
                 "content": item["text"].strip()}
                for item in prior
            ]
            mapped = merge_adjacent(mapped)
            while mapped and mapped[0]["role"] != "user":
                mapped.pop(0)
            if not mapped or mapped[-1]["role"] != "user":
                skipped_no_stimulus += 1
                continue
            target = turn["text"].strip()
            mapped.append({"role": "assistant", "content": target})
            context = "\n".join(item["content"] for item in mapped[:-1] if item["role"] == "user")
            flags = quality_flags(context, target)
            candidates.append({
                "messages": mapped,
                "meta": {
                    "mode": args.mode,
                    "source": turn.get("source"),
                    "conversation": turn.get("conversation"),
                    "conversation_id": conversation_id,
                    "ts": turn.get("ts"),
                    "source_line": turn["_line"],
                    "quality_flags": flags,
                    "semantic_scope": "operator reaction/critique, not independent task solution",
                },
            })
    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, candidates)
    print(json.dumps({
        "source": str(source),
        "source_sha256": file_digest(source),
        "candidates": len(candidates),
        "conversations": len(conversations),
        "skipped_without_assistant_stimulus": skipped_no_stimulus,
        "output": str(output),
    }, indent=2, ensure_ascii=False))
    return 0


def audit_style(args: argparse.Namespace) -> int:
    source = args.input.expanduser().resolve()
    counts: Counter[str] = Counter()
    lengths = []
    exact = set()
    possible_credentials = 0
    privacy: Counter[str] = Counter()
    invalid = 0
    for _, record in read_jsonl(source):
        text = record.get("text")
        if not isinstance(text, str) or not text.strip():
            invalid += 1
            continue
        counts[str(record.get("era") or "unknown")] += 1
        lengths.append(len(text))
        exact.add(digest_text(normalise(text)))
        possible_credentials += int(has_credential(text))
        privacy.update(privacy_flags(text))
    report = {
        "schema_version": SCHEMA_VERSION,
        "source": str(source),
        "source_sha256": file_digest(source),
        "records": sum(counts.values()),
        "invalid": invalid,
        "exact_duplicates": sum(counts.values()) - len(exact),
        "by_era": dict(sorted(counts.items())),
        "length_chars": {
            "min": min(lengths) if lengths else 0,
            "median": sorted(lengths)[len(lengths) // 2] if lengths else 0,
            "max": max(lengths) if lengths else 0,
        },
        "possible_credentials": possible_credentials,
        "privacy_flag_counts": dict(privacy),
        "training_role": "style-only auxiliary corpus; no reply context exists",
        "direct_sft_authorised": False,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    pairs = commands.add_parser("prepare-pairs", help="validate and split chat-format pairs")
    pairs.add_argument("--input", type=Path, required=True)
    pairs.add_argument("--output", type=Path, required=True)
    pairs.add_argument("--privacy", choices=("local", "cloud"), default="local")
    pairs.add_argument("--mode-map", type=Path,
                       help="private JSON mapping exact thread names to modes")
    pairs.add_argument("--only-mode", help="emit only this mapped mode")
    pairs.add_argument("--seed", default="giga-v1")
    pairs.add_argument("--valid-fraction", type=float, default=0.05)
    pairs.add_argument("--test-fraction", type=float, default=0.10)
    pairs.add_argument("--force", action="store_true")
    pairs.set_defaults(function=prepare_pairs)

    transcript = commands.add_parser(
        "transcript-candidates", help="turn AI transcripts into operator-next-turn candidates")
    transcript.add_argument("--input", type=Path, required=True)
    transcript.add_argument("--output", type=Path, required=True)
    transcript.add_argument("--mode", default="reasoning-steering")
    transcript.add_argument("--context-turns", type=int, default=6)
    transcript.add_argument("--force", action="store_true")
    transcript.set_defaults(function=transcript_candidates)

    style = commands.add_parser("audit-style", help="audit one-sided style-only messages")
    style.add_argument("--input", type=Path, required=True)
    style.add_argument("--report", type=Path)
    style.set_defaults(function=audit_style)
    return root


def main() -> int:
    args = parser().parse_args()
    if getattr(args, "valid_fraction", 0) < 0 or getattr(args, "test_fraction", 0) < 0:
        raise ValueError("split fractions cannot be negative")
    if getattr(args, "valid_fraction", 0) + getattr(args, "test_fraction", 0) >= 1:
        raise ValueError("valid + test fractions must be below 1")
    return args.function(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
