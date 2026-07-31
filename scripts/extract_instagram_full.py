#!/usr/bin/env python3
"""Extract a complete two-sided Instagram message view from an immutable Meta ZIP.

The established ``extract_instagram.py`` intentionally keeps only operator-authored text for
style analysis. This extractor serves the evidence/memory layer instead: it preserves both
sides, media/action metadata and exact archive positions without extracting or altering the
provider archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit
from zipfile import BadZipFile, ZipFile


SCHEMA_VERSION = 1
INBOX_PREFIX = "your_instagram_activity/messages/inbox/"


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def fix_text(value: object) -> object:
    if isinstance(value, str):
        try:
            return value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
    if isinstance(value, list):
        return [fix_text(item) for item in value]
    if isinstance(value, dict):
        return {key: fix_text(item) for key, item in value.items()}
    return value


def safe_uri(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if value.startswith(("http://", "https://")):
        parsed = urlsplit(value)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return PurePosixPath(value).as_posix()


def media_metadata(message: dict) -> dict:
    output: dict[str, object] = {}
    for key in ("photos", "videos", "audio_files", "files", "gifs"):
        values = message.get(key)
        if not isinstance(values, list):
            continue
        cleaned = []
        for value in values:
            if not isinstance(value, dict):
                continue
            item = {
                field: safe_uri(value.get(field)) if field in {"uri", "link"} else value.get(field)
                for field in ("uri", "link", "creation_timestamp")
                if value.get(field) is not None
            }
            cleaned.append(item)
        if cleaned:
            output[key] = cleaned
    share = message.get("share")
    if isinstance(share, dict):
        output["share"] = {
            key: safe_uri(value) if key == "link" else fix_text(value)
            for key, value in share.items()
            if key in {"link", "share_text", "original_content_owner"} and value is not None
        }
    for key in ("call_duration", "reactions", "sticker", "story_share"):
        if message.get(key) is not None:
            output[key] = fix_text(message[key])
    return output


def stable_message_id(archive_hash: str, member: str, position: int, message: dict) -> str:
    canonical = json.dumps(message, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    raw = f"{archive_hash}\0{member}\0{position}\0{canonical}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def extract(source: Path, output: Path, manifest_path: Path, operator_name: str,
            namespace: str, force: bool = False) -> dict:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    if (output.exists() or manifest_path.exists()) and not force:
        raise FileExistsError("output already exists; choose a new versioned output path")

    source_hash = file_digest(source)
    rows: list[dict] = []
    invalid: list[dict] = []
    direction_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    thread_ids: set[str] = set()

    try:
        with ZipFile(source) as archive:
            archive.testzip()
            members = sorted(
                name for name in archive.namelist()
                if name.startswith(INBOX_PREFIX) and PurePosixPath(name).name.startswith("message_")
                and name.endswith(".json")
            )
            for member in members:
                try:
                    thread = fix_text(json.loads(archive.read(member)))
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    invalid.append({"member": member, "error": str(exc)})
                    continue
                if not isinstance(thread, dict) or not isinstance(thread.get("messages"), list):
                    invalid.append({"member": member, "error": "invalid thread schema"})
                    continue
                thread_id = PurePosixPath(member).parent.name
                thread_ids.add(thread_id)
                participants = [
                    str(item.get("name")) for item in thread.get("participants", [])
                    if isinstance(item, dict) and item.get("name")
                ]
                for position, message in enumerate(thread["messages"]):
                    if not isinstance(message, dict):
                        invalid.append({"member": member, "position": position,
                                        "error": "message is not an object"})
                        continue
                    sender = str(message.get("sender_name") or "unknown")
                    timestamp_ms = message.get("timestamp_ms")
                    if not isinstance(timestamp_ms, int):
                        invalid.append({"member": member, "position": position,
                                        "error": "missing integer timestamp_ms"})
                        continue
                    timestamp = datetime.fromtimestamp(
                        timestamp_ms / 1000, tz=timezone.utc
                    ).isoformat()
                    text = str(message.get("content") or "")
                    media = media_metadata(message)
                    event_type = "text" if text else "media_or_action"
                    if text and media:
                        event_type = "text_with_media"
                    direction = "outgoing" if sender == operator_name else "incoming"
                    direction_counts[direction] += 1
                    type_counts[event_type] += 1
                    rows.append({
                        "schema_version": SCHEMA_VERSION,
                        "source": "instagram_account_export",
                        "export_namespace": namespace,
                        "message_id": stable_message_id(source_hash, member, position, message),
                        "ts_utc": timestamp,
                        "timestamp_ms": timestamp_ms,
                        "thread_id": thread_id,
                        "thread_title": str(thread.get("title") or thread_id),
                        "thread_path": thread.get("thread_path"),
                        "participants": participants,
                        "sender_name": sender,
                        "direction": direction,
                        "text": text,
                        "event_type": event_type,
                        "media": media,
                        "archive_member": member,
                        "archive_position": position,
                        "sender_scope": (
                            "operator_account_outgoing" if direction == "outgoing"
                            else "conversation_context"
                        ),
                        "composition_status": "unverified",
                        "context_available": True,
                        "training_role": (
                            "candidate_target" if direction == "outgoing"
                            else "third_party_context_only"
                        ),
                    })
    except BadZipFile as exc:
        raise ValueError(f"not a valid ZIP archive: {source}") from exc

    rows.sort(key=lambda row: (row["ts_utc"], row["thread_id"], row["message_id"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "source_sha256": source_hash,
        "export_namespace": namespace,
        "operator_name": operator_name,
        "output": str(output),
        "output_sha256": file_digest(output),
        "records": len(rows),
        "invalid_records": len(invalid),
        "invalid": invalid,
        "threads_with_messages": len(thread_ids),
        "direction_counts": dict(direction_counts),
        "event_type_counts": dict(type_counts),
        "date_range": {
            "first": rows[0]["ts_utc"] if rows else None,
            "last": rows[-1]["ts_utc"] if rows else None,
        },
        "source_limitations": [
            "Direction proves which account transmitted a message, not independent authorship.",
            "Unsent/deleted messages may be absent.",
            "Media binaries remain in the immutable source archive and are referenced only.",
            "Third-party messages are local-private context and never training targets.",
        ],
        "direct_sft_authorised": False,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--operator-name", default="Artiom")
    parser.add_argument("--namespace", default="instagram_primary")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifest = extract(
        args.input, args.output, args.manifest, args.operator_name, args.namespace, args.force
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}")
        raise SystemExit(2)
