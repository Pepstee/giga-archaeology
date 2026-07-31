#!/usr/bin/env python3
"""Extract the messages section of a Discord account export into canonical JSONL.

The Discord package contains sensitive account, billing and behavioural-analytics data that
is not needed for language analysis. This extractor reads only the provider's messages
section (for example ``Messages/`` or the Russian-localised ``Сообщения/``) plus the package
README, preserves message provenance, and never fabricates the missing side of a conversation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile


SCHEMA_VERSION = 1
NAMESPACE_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}")
URL_RE = re.compile(r"https?://[^\s,]+")


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def attachment_metadata(value: object) -> list[dict[str, str]]:
    """Retain useful attachment evidence without copying signed CDN query strings."""
    if not isinstance(value, str) or not value.strip():
        return []
    output = []
    for url in URL_RE.findall(value):
        path = PurePosixPath(url.split("?", 1)[0])
        output.append({"name": path.name, "extension": path.suffix.lower()})
    return output


def load_json(archive: ZipFile, member: str) -> object:
    try:
        return json.loads(archive.read(member))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"invalid or missing Discord export member: {member}") from exc


def find_messages_root(names: set[str]) -> str:
    """Find a Discord messages section without assuming the export language."""
    candidates = []
    for name in names:
        path = PurePosixPath(name)
        if path.name != "index.json" or len(path.parts) != 2:
            continue
        root = path.parent.as_posix()
        channel_json = any(
            value.startswith(root + "/c") and value.endswith("/channel.json")
            for value in names
        )
        messages_json = any(
            value.startswith(root + "/c") and value.endswith("/messages.json")
            for value in names
        )
        if channel_json and messages_json:
            candidates.append(root)
    if len(candidates) != 1:
        raise ValueError(
            "archive is not a recognised Discord account export: "
            f"expected one messages section, found {len(candidates)}"
        )
    return candidates[0]


def extract(source: Path, output: Path, manifest_path: Path, namespace: str,
            force: bool = False) -> dict:
    if not NAMESPACE_RE.fullmatch(namespace):
        raise ValueError("namespace must match [a-z0-9][a-z0-9_-]{0,39}")
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    if (output.exists() or manifest_path.exists()) and not force:
        raise FileExistsError("output already exists; choose a new versioned output path")

    rows = []
    invalid = []
    by_year: Counter[str] = Counter()
    by_month: Counter[str] = Counter()
    by_type: Counter[str] = Counter()
    empty_content = 0
    attachment_messages = 0
    channel_ids = set()

    try:
        with ZipFile(source) as archive:
            names = set(archive.namelist())
            if "README.txt" not in names:
                raise ValueError("archive is not a recognised Discord account export")
            messages_root = find_messages_root(names)
            index = load_json(archive, f"{messages_root}/index.json")
            if not isinstance(index, dict):
                raise ValueError(f"{messages_root}/index.json must be an object")

            channel_members = sorted(n for n in names if n.startswith(messages_root + "/")
                                     and n.endswith("/channel.json"))
            channels = {}
            for member in channel_members:
                channel = load_json(archive, member)
                if isinstance(channel, dict) and channel.get("id") is not None:
                    channels[str(channel["id"])] = channel

            message_members = sorted(n for n in names if n.startswith(messages_root + "/")
                                     and n.endswith("/messages.json"))
            for member in message_members:
                channel_id = PurePosixPath(member).parent.name.removeprefix("c")
                channel = channels.get(channel_id, {})
                channel_type = str(channel.get("type") or "UNKNOWN")
                channel_label = str(index.get(channel_id) or channel.get("name") or
                                    "Unknown channel")
                messages = load_json(archive, member)
                if not isinstance(messages, list):
                    invalid.append({"member": member, "error": "messages root is not a list"})
                    continue
                for position, message in enumerate(messages):
                    if not isinstance(message, dict):
                        invalid.append({"member": member, "position": position,
                                        "error": "message is not an object"})
                        continue
                    message_id = message.get("ID")
                    timestamp = message.get("Timestamp")
                    text = message.get("Contents")
                    if message_id is None or not isinstance(timestamp, str) or not isinstance(text, str):
                        invalid.append({"member": member, "position": position,
                                        "error": "missing ID, Timestamp or Contents"})
                        continue
                    try:
                        parsed = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        invalid.append({"member": member, "position": position,
                                        "error": "invalid timestamp"})
                        continue
                    attachments = attachment_metadata(message.get("Attachments"))
                    empty_content += int(not text.strip())
                    attachment_messages += int(bool(attachments))
                    channel_ids.add(channel_id)
                    by_year[str(parsed.year)] += 1
                    by_month[parsed.strftime("%Y-%m")] += 1
                    by_type[channel_type] += 1
                    guild = channel.get("guild") if isinstance(channel.get("guild"), dict) else {}
                    rows.append({
                        "schema_version": SCHEMA_VERSION,
                        "source": "discord_account_export",
                        "export_namespace": namespace,
                        "message_id": str(message_id),
                        "ts": timestamp,
                        "era": str(parsed.year),
                        "text": text,
                        "attachments": attachments,
                        "channel_id": channel_id,
                        "channel_type": channel_type,
                        "channel_label": channel_label,
                        "guild_id": str(guild.get("id")) if guild.get("id") is not None else None,
                        "guild_name": guild.get("name"),
                        "archive_member": member,
                        "archive_position": position,
                        # Discord proves which account sent a message, not who composed the
                        # words. Copypasta, quotations, bot output and pasted documents are
                        # all common in this package and must not be silently relabelled as
                        # original operator prose.
                        "sender_scope": "operator_account_outgoing",
                        "composition_status": "unverified",
                        "context_available": False,
                        "training_role": "style_only",
                    })
    except BadZipFile as exc:
        raise ValueError(f"not a valid zip archive: {source}") from exc

    rows.sort(key=lambda row: (row["ts"], row["channel_id"], row["message_id"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    digest = file_digest(source)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "source_sha256": digest,
        "export_namespace": namespace,
        "output": str(output),
        "output_sha256": file_digest(output),
        "records": len(rows),
        "invalid_records": len(invalid),
        "invalid": invalid,
        "channels_with_messages": len(channel_ids),
        "empty_content_records": empty_content,
        "attachment_messages": attachment_messages,
        "date_range": {
            "first": rows[0]["ts"] if rows else None,
            "last": rows[-1]["ts"] if rows else None,
        },
        "by_year": dict(sorted(by_year.items())),
        "by_month": dict(sorted(by_month.items())),
        "by_channel_type": dict(sorted(by_type.items())),
        "messages_root": messages_root,
        "excluded_sections": "all archive sections outside README.txt and the detected messages root",
        "source_limitations": [
            "Discord exports only messages sent by the account owner.",
            "Deleted messages are absent.",
            "The package timestamp has no timezone marker.",
            "Other participants' messages and reply context are unavailable.",
            "A sent message may be copied, quoted, translated, generated or pasted rather than composed by the operator.",
        ],
        "privacy_note": "Channel labels and guild names may identify third parties.",
        "direct_sft_authorised": False,
        "training_role": "style-only auxiliary corpus; never fabricate reply context",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--input", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--manifest", type=Path, required=True)
    result.add_argument("--namespace", required=True)
    result.add_argument("--force", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    manifest = extract(args.input, args.output, args.manifest, args.namespace, args.force)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}")
        raise SystemExit(2)
