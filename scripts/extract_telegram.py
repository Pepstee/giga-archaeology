#!/usr/bin/env python3
"""Normalize a Telegram Desktop JSON export without altering the source file.

The derived JSONL retains both sides of each conversation, service events, reply and
forward provenance, and media metadata.  Account ownership proves message direction,
not independent authorship: copied, forwarded, quoted, generated, or pasted text remains
composition-unverified until separately classified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def flatten_text(value: object) -> str:
    """Return Telegram's rich-text representation as visible text."""
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""
    parts: list[str] = []
    for part in value:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict) and isinstance(part.get("text"), str):
            parts.append(part["text"])
    return "".join(parts)


def media_metadata(message: dict) -> dict:
    keys = (
        "media_type", "file", "file_name", "file_size", "mime_type", "photo",
        "photo_file_size", "thumbnail", "thumbnail_file_size", "width", "height",
        "duration_seconds", "sticker_emoji", "media_spoiler", "self_destruct_period_seconds",
        "location_information", "live_location_period_seconds", "contact_information",
        "contact_vcard", "contact_vcard_file_size", "poll", "title", "performer",
    )
    return {key: message[key] for key in keys if key in message}


def extract(source: Path, output: Path, manifest_path: Path, namespace: str,
            force: bool = False) -> dict:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    if (output.exists() or manifest_path.exists()) and not force:
        raise FileExistsError("output already exists; choose a new versioned output path")

    try:
        export = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Telegram JSON export: {source}") from exc
    if not isinstance(export, dict) or not isinstance(export.get("personal_information"), dict):
        raise ValueError("not a recognised Telegram Desktop JSON export")

    personal = export["personal_information"]
    self_id = f"user{personal.get('user_id')}"
    rows: list[dict] = []
    invalid: list[dict] = []
    by_year: Counter[str] = Counter()
    by_month: Counter[str] = Counter()
    by_direction: Counter[str] = Counter()
    by_chat_type: Counter[str] = Counter()
    by_message_type: Counter[str] = Counter()
    by_media_type: Counter[str] = Counter()
    chats_with_messages: set[str] = set()
    text_bearing = 0

    for section in ("chats", "left_chats"):
        container = export.get(section, {})
        chat_list = container.get("list", []) if isinstance(container, dict) else []
        if not isinstance(chat_list, list):
            invalid.append({"section": section, "error": "chat list is not a list"})
            continue
        for chat_position, chat in enumerate(chat_list):
            if not isinstance(chat, dict) or not isinstance(chat.get("messages"), list):
                invalid.append({"section": section, "chat_position": chat_position,
                                "error": "invalid chat object"})
                continue
            chat_id = str(chat.get("id"))
            chat_type = str(chat.get("type") or "unknown")
            chat_name = chat.get("name")
            for message_position, message in enumerate(chat["messages"]):
                if not isinstance(message, dict):
                    invalid.append({"section": section, "chat_id": chat_id,
                                    "message_position": message_position,
                                    "error": "message is not an object"})
                    continue
                required = (message.get("id"), message.get("date"),
                            message.get("date_unixtime"), message.get("type"))
                if any(value is None for value in required):
                    invalid.append({"section": section, "chat_id": chat_id,
                                    "message_position": message_position,
                                    "error": "missing id, date, date_unixtime, or type"})
                    continue

                sender_id = message.get("from_id") or message.get("actor_id")
                if message.get("type") == "service":
                    direction = "service"
                elif sender_id == self_id:
                    direction = "outgoing"
                elif sender_id:
                    direction = "incoming"
                else:
                    direction = "unknown"
                text = flatten_text(message.get("text"))
                text_bearing += int(bool(text.strip()))
                timestamp = datetime.fromtimestamp(int(message["date_unixtime"]), tz=timezone.utc)
                media = media_metadata(message)
                record = {
                    "schema_version": SCHEMA_VERSION,
                    "source": "telegram_desktop_export",
                    "export_namespace": namespace,
                    "section": section,
                    "chat_id": chat_id,
                    "chat_name": chat_name,
                    "chat_type": chat_type,
                    "message_id": str(message["id"]),
                    "message_type": message["type"],
                    "ts_export_local": message["date"],
                    "ts_unix": int(message["date_unixtime"]),
                    "ts_utc": timestamp.isoformat().replace("+00:00", "Z"),
                    "sender_name": message.get("from") or message.get("actor"),
                    "sender_id": sender_id,
                    "direction": direction,
                    "text": text,
                    "text_entities": message.get("text_entities", []),
                    "reply_to_message_id": (str(message["reply_to_message_id"])
                                            if message.get("reply_to_message_id") is not None else None),
                    "forwarded_from": message.get("forwarded_from"),
                    "forwarded_from_id": message.get("forwarded_from_id"),
                    "saved_from": message.get("saved_from"),
                    "via_bot": message.get("via_bot"),
                    "edited": message.get("edited"),
                    "edited_unixtime": message.get("edited_unixtime"),
                    "action": message.get("action"),
                    "discard_reason": message.get("discard_reason"),
                    "reactions": message.get("reactions", []),
                    "inline_bot_buttons": message.get("inline_bot_buttons"),
                    "media": media,
                    "source_position": {"chat": chat_position, "message": message_position},
                    "sender_scope": ("operator_account_outgoing" if direction == "outgoing"
                                     else "conversation_context"),
                    "composition_status": "unverified",
                    "context_available": True,
                    "training_role": "unreviewed_two_sided",
                }
                rows.append(record)
                chats_with_messages.add(chat_id)
                by_year[str(timestamp.year)] += 1
                by_month[timestamp.strftime("%Y-%m")] += 1
                by_direction[direction] += 1
                by_chat_type[chat_type] += 1
                by_message_type[str(message["type"])] += 1
                if media.get("media_type"):
                    by_media_type[str(media["media_type"])] += 1

    rows.sort(key=lambda row: (row["ts_unix"], row["chat_id"], int(row["message_id"])))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "source_sha256": file_digest(source),
        "export_namespace": namespace,
        "account": {
            "user_id": str(personal.get("user_id")),
            "first_name": personal.get("first_name"),
            "last_name": personal.get("last_name"),
            "username": personal.get("username"),
            "phone_number_stored": bool(personal.get("phone_number")),
        },
        "output": str(output),
        "output_sha256": file_digest(output),
        "records": len(rows),
        "text_bearing_records": text_bearing,
        "invalid_records": len(invalid),
        "invalid": invalid,
        "chats_with_messages": len(chats_with_messages),
        "date_range_utc": {
            "first": rows[0]["ts_utc"] if rows else None,
            "last": rows[-1]["ts_utc"] if rows else None,
        },
        "by_year": dict(sorted(by_year.items())),
        "by_month": dict(sorted(by_month.items())),
        "by_direction": dict(sorted(by_direction.items())),
        "by_chat_type": dict(sorted(by_chat_type.items())),
        "by_message_type": dict(sorted(by_message_type.items())),
        "by_media_type": dict(sorted(by_media_type.items())),
        "source_limitations": [
            "Deleted messages and deleted chats may be absent.",
            "Secret chats are device-local and may be absent from a cloud export.",
            "The export's human-readable date has no explicit timezone; ts_unix is canonical.",
            "Message direction proves account transmission, not independent composition.",
            "Media paths are retained as metadata, but missing exported media cannot be reconstructed.",
        ],
        "privacy_note": "Names, usernames, contact metadata, and conversation text identify third parties.",
        "direct_sft_authorised": False,
        "training_role": "unreviewed two-sided corpus; pairs require privacy and composition review",
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
