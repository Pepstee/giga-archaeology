#!/usr/bin/env python3
"""Build the local, provenance-bearing unified memory database.

The database combines canonical derived views from Discord, Telegram, Instagram, Claude and
ChatGPT. Provider exports remain immutable. Every stored message points back to a source file
and source position. Three tiers are exposed:

1. ``tier1_evidence``: exact message observations and provenance.
2. ``tier2_episodes``: deterministic conversation sessions and monthly structure.
3. ``tier3_memory_map``: evidence-linked interpretive claims populated by later analysis.

The SQLite database is the requested one-file authority. A chronological gzip JSONL export is
also emitted for systems that cannot query SQLite.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Iterator


SCHEMA_VERSION = 1
SESSION_GAP_SECONDS = 12 * 60 * 60
TOKEN_RE = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
STOPWORDS = {
    "that", "this", "with", "have", "what", "when", "your", "from", "just", "like",
    "there", "they", "will", "would", "could", "about", "then", "were", "been", "because",
    "если", "тебя", "меня", "только", "просто", "чтобы", "когда", "потому", "очень", "есть",
    "тебе", "будет", "можно", "этого", "того", "тоже", "было", "него", "себя", "сейчас",
}


@dataclass(frozen=True)
class SourceSpec:
    path: Path
    platform: str
    namespace: str
    coverage: str
    adapter: Callable[[dict, int, "SourceSpec"], dict | None]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def normalise_text(text: str) -> str:
    return " ".join(text.casefold().split())


def content_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_id(*parts: object) -> str:
    raw = "\0".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_timestamp(value: str, *, naive: bool = False) -> tuple[str, float | None, str]:
    raw = str(value)
    if naive:
        parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        # Discord exports omit timezone. Keep the original wall-clock value and do not claim UTC.
        return parsed.isoformat(), None, "provider_naive_unknown_timezone"
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.isoformat(), None, "provider_naive_unknown_timezone"
    normal = parsed.astimezone(timezone.utc)
    return normal.isoformat(), normal.timestamp(), "provider_utc"


def json_lines(path: Path) -> Iterator[tuple[int, dict]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: record is not an object")
            yield line_number, value


def discord_adapter(row: dict, line: int, spec: SourceSpec) -> dict:
    ts, epoch, basis = parse_timestamp(row["ts"], naive=True)
    account = {
        "primary_20260719": ("account:discord:qstee", "Λstee"),
        "teen_vstee": ("account:discord:vstee", "B L Λ D E"),
    }.get(spec.namespace, (f"account:discord:{spec.namespace}", spec.namespace))
    return {
        "record_id": f"message:discord:{spec.namespace}:{row['channel_id']}:{row['message_id']}",
        "native_message_id": str(row["message_id"]),
        "thread_id": str(row["channel_id"]),
        "thread_title": str(row.get("channel_label") or row["channel_id"]),
        "author_id": account[0],
        "author_name": account[1],
        "author_role": "operator",
        "direction": "outgoing",
        "timestamp": ts,
        "timestamp_epoch": epoch,
        "timezone_basis": basis,
        "text": str(row.get("text") or ""),
        "message_type": "message",
        "composition_status": str(row.get("composition_status") or "unverified"),
        "context_available": bool(row.get("context_available")),
        "source_member": row.get("archive_member"),
        "source_position": row.get("archive_position", line),
        "native_reply_to": None,
        "metadata": {
            "attachments": row.get("attachments", []),
            "channel_type": row.get("channel_type"),
            "guild_id": row.get("guild_id"),
            "guild_name": row.get("guild_name"),
            "training_role": row.get("training_role"),
        },
    }


def telegram_adapter(row: dict, line: int, spec: SourceSpec) -> dict:
    timestamp_raw = row.get("ts_utc") or row.get("ts_export_local")
    ts, epoch, basis = parse_timestamp(timestamp_raw)
    direction = str(row.get("direction") or "unknown")
    role = "operator" if direction == "outgoing" else (
        "system" if direction == "service" else "third_party"
    )
    source_position = row.get("source_position")
    return {
        "record_id": f"message:telegram:{spec.namespace}:{row['chat_id']}:{row['message_id']}",
        "native_message_id": str(row["message_id"]),
        "thread_id": str(row["chat_id"]),
        "thread_title": str(row.get("chat_name") or row["chat_id"]),
        "author_id": str(row.get("sender_id") or f"telegram:{role}"),
        "author_name": str(row.get("sender_name") or role),
        "author_role": role,
        "direction": direction,
        "timestamp": ts,
        "timestamp_epoch": epoch,
        "timezone_basis": basis,
        "text": str(row.get("text") or ""),
        "message_type": str(row.get("message_type") or "message"),
        "composition_status": str(row.get("composition_status") or "unverified"),
        "context_available": bool(row.get("context_available")),
        "source_member": "result.json",
        "source_position": (
            json.dumps(source_position, sort_keys=True) if source_position is not None else str(line)
        ),
        "native_reply_to": (
            str(row["reply_to_message_id"]) if row.get("reply_to_message_id") is not None else None
        ),
        "metadata": {
            "chat_type": row.get("chat_type"),
            "forwarded_from": row.get("forwarded_from"),
            "forwarded_from_id": row.get("forwarded_from_id"),
            "edited": row.get("edited"),
            "media": row.get("media", {}),
            "reactions": row.get("reactions", []),
            "action": row.get("action"),
            "training_role": row.get("training_role"),
        },
    }


def instagram_adapter(row: dict, line: int, spec: SourceSpec) -> dict:
    ts, epoch, basis = parse_timestamp(row["ts_utc"])
    direction = str(row.get("direction") or "unknown")
    role = "operator" if direction == "outgoing" else "third_party"
    return {
        "record_id": f"message:instagram:{spec.namespace}:{row['message_id']}",
        "native_message_id": str(row["message_id"]),
        "thread_id": str(row["thread_id"]),
        "thread_title": str(row.get("thread_title") or row["thread_id"]),
        "author_id": f"account:instagram:{normalise_text(str(row.get('sender_name') or role))}",
        "author_name": str(row.get("sender_name") or role),
        "author_role": role,
        "direction": direction,
        "timestamp": ts,
        "timestamp_epoch": epoch,
        "timezone_basis": basis,
        "text": str(row.get("text") or ""),
        "message_type": str(row.get("event_type") or "message"),
        "composition_status": str(row.get("composition_status") or "unverified"),
        "context_available": True,
        "source_member": row.get("archive_member"),
        "source_position": row.get("archive_position", line),
        "native_reply_to": None,
        "metadata": {
            "participants": row.get("participants", []),
            "thread_path": row.get("thread_path"),
            "media": row.get("media", {}),
            "training_role": row.get("training_role"),
        },
    }


def instagram_comment_adapter(row: dict, line: int, spec: SourceSpec) -> dict | None:
    if row.get("source") != "instagram_comment":
        return None
    ts, epoch, basis = parse_timestamp(row["ts"])
    return {
        "record_id": f"message:instagram:{spec.namespace}:comment:{line}",
        "native_message_id": None,
        "thread_id": "post_comment",
        "thread_title": "Instagram post comments",
        "author_id": "account:instagram:artiom",
        "author_name": "Artiom",
        "author_role": "operator",
        "direction": "outgoing",
        "timestamp": ts,
        "timestamp_epoch": epoch,
        "timezone_basis": basis,
        "text": str(row.get("text") or ""),
        "message_type": "comment",
        "composition_status": "unverified",
        "context_available": False,
        "source_member": None,
        "source_position": line,
        "native_reply_to": None,
        "metadata": {"register": row.get("register")},
    }


def ai_adapter(row: dict, line: int, spec: SourceSpec) -> dict:
    ts, epoch, basis = parse_timestamp(row["ts"])
    sender = str(row.get("sender") or "unknown")
    role = "operator" if sender == "human" else "model"
    direction = "outgoing" if role == "operator" else "incoming"
    conversation_id = str(row.get("conv_uuid") or row.get("conversation") or "unknown")
    return {
        "record_id": f"message:{spec.platform}:{spec.namespace}:{conversation_id}:{line}",
        "native_message_id": None,
        "thread_id": conversation_id,
        "thread_title": str(row.get("conversation") or conversation_id),
        "author_id": (
            "person:artiom" if role == "operator"
            else f"model:{spec.platform}:{spec.namespace}"
        ),
        "author_name": "Artiom" if role == "operator" else spec.platform,
        "author_role": role,
        "direction": direction,
        "timestamp": ts,
        "timestamp_epoch": epoch,
        "timezone_basis": basis,
        "text": str(row.get("text") or ""),
        "message_type": "conversation_turn",
        "composition_status": "unverified" if role == "operator" else "model_output",
        "context_available": True,
        "source_member": None,
        "source_position": line,
        "native_reply_to": None,
        "metadata": {"sender": sender, "source": row.get("source")},
    }


def default_sources(root: Path) -> list[SourceSpec]:
    return [
        SourceSpec(root / "corpus/raw/discord_messages_teen_vstee_20260726.jsonl",
                   "discord", "teen_vstee", "one_sided_account_sent", discord_adapter),
        SourceSpec(root / "corpus/raw/discord_messages_primary_20260719.jsonl",
                   "discord", "primary_20260719", "one_sided_account_sent", discord_adapter),
        SourceSpec(root / "corpus/raw/telegram_messages_primary_20260722.jsonl",
                   "telegram", "telegram_primary_20260722", "complete_two_sided_export",
                   telegram_adapter),
        SourceSpec(root / "corpus/raw/instagram_messages_full_20260726.jsonl",
                   "instagram", "instagram_primary_20260716", "complete_two_sided_export",
                   instagram_adapter),
        SourceSpec(root / "corpus/raw/instagram_20260717.jsonl",
                   "instagram", "instagram_comments_20260717", "operator_comments_only",
                   instagram_comment_adapter),
        SourceSpec(root / "corpus/transcripts/claude_conversations.jsonl",
                   "claude", "claude_primary", "complete_two_sided_text_view", ai_adapter),
        SourceSpec(root / "corpus/transcripts/chatgpt_conversations.jsonl",
                   "chatgpt", "chatgpt_pre2026", "complete_two_sided_text_view", ai_adapter),
        SourceSpec(root / "corpus/transcripts/chatgpt_conversations_gpt2_2026.jsonl",
                   "chatgpt", "gpt2_2026", "complete_two_sided_text_view", ai_adapter),
    ]


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE source_files (
    source_id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    platform TEXT NOT NULL,
    namespace TEXT NOT NULL,
    coverage TEXT NOT NULL,
    records_seen INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE threads (
    thread_pk INTEGER PRIMARY KEY,
    platform TEXT NOT NULL,
    namespace TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    title TEXT NOT NULL,
    coverage TEXT NOT NULL,
    UNIQUE(platform, namespace, thread_id)
);
CREATE TABLE messages (
    message_pk INTEGER PRIMARY KEY,
    record_id TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL,
    namespace TEXT NOT NULL,
    native_message_id TEXT,
    thread_pk INTEGER NOT NULL REFERENCES threads(thread_pk),
    author_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_role TEXT NOT NULL,
    direction TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    timestamp_epoch REAL,
    timezone_basis TEXT NOT NULL,
    text TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    normalised_sha256 TEXT NOT NULL,
    message_type TEXT NOT NULL,
    composition_status TEXT NOT NULL,
    context_available INTEGER NOT NULL CHECK(context_available IN (0,1)),
    source_id INTEGER NOT NULL REFERENCES source_files(source_id),
    source_member TEXT,
    source_position TEXT NOT NULL,
    native_reply_to TEXT,
    metadata_json TEXT NOT NULL
);
CREATE INDEX idx_messages_thread_time ON messages(thread_pk, timestamp, message_pk);
CREATE INDEX idx_messages_time ON messages(timestamp, message_pk);
CREATE INDEX idx_messages_author_time ON messages(author_role, timestamp);
CREATE INDEX idx_messages_hash ON messages(normalised_sha256);
CREATE VIRTUAL TABLE message_fts USING fts5(
    record_id UNINDEXED, text, tokenize='unicode61 remove_diacritics 2'
);
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    thread_pk INTEGER NOT NULL REFERENCES threads(thread_pk),
    start_timestamp TEXT NOT NULL,
    end_timestamp TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    operator_count INTEGER NOT NULL,
    other_count INTEGER NOT NULL,
    text_chars INTEGER NOT NULL,
    keywords_json TEXT NOT NULL,
    boundary_seconds INTEGER NOT NULL,
    coverage TEXT NOT NULL
);
CREATE TABLE session_messages (
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    message_pk INTEGER NOT NULL REFERENCES messages(message_pk),
    ordinal INTEGER NOT NULL,
    PRIMARY KEY(session_id, message_pk)
);
CREATE INDEX idx_session_messages_message ON session_messages(message_pk);
CREATE TABLE monthly_map (
    month TEXT NOT NULL,
    platform TEXT NOT NULL,
    namespace TEXT NOT NULL,
    messages INTEGER NOT NULL,
    operator_messages INTEGER NOT NULL,
    other_messages INTEGER NOT NULL,
    text_chars INTEGER NOT NULL,
    threads INTEGER NOT NULL,
    PRIMARY KEY(month, platform, namespace)
);
CREATE TABLE memory_claims (
    claim_id TEXT PRIMARY KEY,
    claim_type TEXT NOT NULL,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    status TEXT NOT NULL,
    method TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE claim_evidence (
    claim_id TEXT NOT NULL REFERENCES memory_claims(claim_id),
    message_pk INTEGER NOT NULL REFERENCES messages(message_pk),
    evidence_role TEXT NOT NULL,
    PRIMARY KEY(claim_id, message_pk, evidence_role)
);
CREATE VIEW tier1_evidence AS
SELECT m.record_id,m.platform,m.namespace,t.thread_id,t.title AS thread_title,
       m.author_id,m.author_name,m.author_role,m.direction,m.timestamp,m.timezone_basis,
       m.text,m.composition_status,m.context_available,s.path AS source_path,
       m.source_member,m.source_position,m.native_reply_to
FROM messages m JOIN threads t ON t.thread_pk=m.thread_pk
JOIN source_files s ON s.source_id=m.source_id;
CREATE VIEW tier2_episodes AS
SELECT s.session_id,t.platform,t.namespace,t.thread_id,t.title,s.start_timestamp,
       s.end_timestamp,s.message_count,s.operator_count,s.other_count,s.text_chars,
       s.keywords_json,s.boundary_seconds,s.coverage
FROM sessions s JOIN threads t ON t.thread_pk=s.thread_pk;
CREATE VIEW tier3_memory_map AS
SELECT c.*,COUNT(e.message_pk) AS evidence_count
FROM memory_claims c LEFT JOIN claim_evidence e ON e.claim_id=c.claim_id
GROUP BY c.claim_id;
"""


def top_keywords(counter: Counter[str], limit: int = 12) -> list[tuple[str, int]]:
    return [
        (token, count) for token, count in counter.most_common()
        if token not in STOPWORDS
    ][:limit]


def text_tokens(text: str) -> Iterator[str]:
    for token in TOKEN_RE.findall(text.casefold()):
        if token not in STOPWORDS:
            yield token


def build_sessions(connection: sqlite3.Connection) -> None:
    cursor = connection.execute(
        """SELECT m.message_pk,m.thread_pk,m.timestamp,m.timestamp_epoch,m.author_role,m.text,
                  t.platform,t.namespace,t.coverage
           FROM messages m JOIN threads t ON t.thread_pk=m.thread_pk
           ORDER BY m.thread_pk,m.timestamp,m.message_pk"""
    )
    current_thread = None
    session_rows: list[dict] = []
    session_number = 0

    def flush() -> None:
        nonlocal session_rows, session_number
        if not session_rows:
            return
        first, last = session_rows[0], session_rows[-1]
        session_number += 1
        session_id = "session:" + stable_id(
            first["thread_pk"], first["message_pk"], SESSION_GAP_SECONDS
        )
        keyword_counter: Counter[str] = Counter()
        for item in session_rows:
            keyword_counter.update(text_tokens(item["text"]))
        operator_count = sum(item["author_role"] == "operator" for item in session_rows)
        connection.execute(
            """INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                session_id, first["thread_pk"], first["timestamp"], last["timestamp"],
                len(session_rows), operator_count, len(session_rows) - operator_count,
                sum(len(item["text"]) for item in session_rows),
                json.dumps(top_keywords(keyword_counter), ensure_ascii=False),
                SESSION_GAP_SECONDS, first["coverage"],
            ),
        )
        connection.executemany(
            "INSERT INTO session_messages VALUES (?,?,?)",
            [(session_id, item["message_pk"], index)
             for index, item in enumerate(session_rows)],
        )
        session_rows = []

    previous_epoch = None
    previous_timestamp = None
    for row in cursor:
        item = dict(row)
        if current_thread != item["thread_pk"]:
            flush()
            current_thread = item["thread_pk"]
            previous_epoch = None
            previous_timestamp = None
        new_session = False
        if session_rows:
            if item["timestamp_epoch"] is not None and previous_epoch is not None:
                new_session = item["timestamp_epoch"] - previous_epoch > SESSION_GAP_SECONDS
            else:
                # Naive Discord timestamps are internally comparable within one account/thread.
                now = datetime.fromisoformat(item["timestamp"])
                prior = datetime.fromisoformat(str(previous_timestamp))
                new_session = (now - prior).total_seconds() > SESSION_GAP_SECONDS
        if new_session:
            flush()
        session_rows.append(item)
        previous_epoch = item["timestamp_epoch"]
        previous_timestamp = item["timestamp"]
    flush()


def build_monthly_map(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT INTO monthly_map
        SELECT substr(m.timestamp,1,7),m.platform,m.namespace,COUNT(*),
               SUM(CASE WHEN m.author_role='operator' THEN 1 ELSE 0 END),
               SUM(CASE WHEN m.author_role='operator' THEN 0 ELSE 1 END),
               SUM(length(m.text)),COUNT(DISTINCT m.thread_pk)
        FROM messages m GROUP BY 1,2,3"""
    )


def build(root: Path, output: Path, export_path: Path, manifest_path: Path) -> dict:
    root = root.resolve()
    output = output.resolve()
    export_path = export_path.resolve()
    manifest_path = manifest_path.resolve()
    for path in (output, export_path, manifest_path):
        if path.exists():
            raise FileExistsError(f"{path} already exists; use a new versioned path")
        path.parent.mkdir(parents=True, exist_ok=True)

    temp = output.with_suffix(output.suffix + ".building")
    if temp.exists():
        temp.unlink()
    connection = sqlite3.connect(temp)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO metadata VALUES (?,?)",
                           ("schema_version", str(SCHEMA_VERSION)))
        connection.execute("INSERT INTO metadata VALUES (?,?)", ("built_at", utc_now()))
        connection.execute("INSERT INTO metadata VALUES (?,?)",
                           ("session_gap_seconds", str(SESSION_GAP_SECONDS)))
        sources = default_sources(root)
        thread_cache: dict[tuple[str, str, str], int] = {}
        total = 0
        for spec in sources:
            if not spec.path.exists():
                raise FileNotFoundError(spec.path)
            digest = file_digest(spec.path)
            cursor = connection.execute(
                """INSERT INTO source_files
                   (path,sha256,byte_size,platform,namespace,coverage)
                   VALUES (?,?,?,?,?,?)""",
                (str(spec.path), digest, spec.path.stat().st_size, spec.platform,
                 spec.namespace, spec.coverage),
            )
            source_id = int(cursor.lastrowid)
            seen = inserted = 0
            batch = []
            fts_batch = []
            for line_number, raw in json_lines(spec.path):
                seen += 1
                item = spec.adapter(raw, line_number, spec)
                if item is None:
                    continue
                key = (spec.platform, spec.namespace, item["thread_id"])
                thread_pk = thread_cache.get(key)
                if thread_pk is None:
                    connection.execute(
                        """INSERT OR IGNORE INTO threads
                           (platform,namespace,thread_id,title,coverage) VALUES (?,?,?,?,?)""",
                        (*key, item["thread_title"], spec.coverage),
                    )
                    thread_pk = int(connection.execute(
                        """SELECT thread_pk FROM threads
                           WHERE platform=? AND namespace=? AND thread_id=?""", key
                    ).fetchone()[0])
                    thread_cache[key] = thread_pk
                text = item["text"]
                batch.append((
                    item["record_id"], spec.platform, spec.namespace,
                    item["native_message_id"], thread_pk, item["author_id"],
                    item["author_name"], item["author_role"], item["direction"],
                    item["timestamp"], item["timestamp_epoch"], item["timezone_basis"], text,
                    content_digest(text), content_digest(normalise_text(text)),
                    item["message_type"], item["composition_status"],
                    int(item["context_available"]), source_id, item["source_member"],
                    str(item["source_position"]), item["native_reply_to"],
                    json.dumps(item["metadata"], ensure_ascii=False, sort_keys=True),
                ))
                fts_batch.append((item["record_id"], text))
                inserted += 1
                if len(batch) >= 2000:
                    connection.executemany(
                        """INSERT INTO messages
                        (record_id,platform,namespace,native_message_id,thread_pk,author_id,
                         author_name,author_role,direction,timestamp,timestamp_epoch,
                         timezone_basis,text,content_sha256,normalised_sha256,message_type,
                         composition_status,context_available,source_id,source_member,
                         source_position,native_reply_to,metadata_json)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", batch
                    )
                    connection.executemany(
                        "INSERT INTO message_fts(record_id,text) VALUES (?,?)", fts_batch
                    )
                    batch.clear()
                    fts_batch.clear()
            if batch:
                connection.executemany(
                    """INSERT INTO messages
                    (record_id,platform,namespace,native_message_id,thread_pk,author_id,
                     author_name,author_role,direction,timestamp,timestamp_epoch,
                     timezone_basis,text,content_sha256,normalised_sha256,message_type,
                     composition_status,context_available,source_id,source_member,
                     source_position,native_reply_to,metadata_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", batch
                )
                connection.executemany(
                    "INSERT INTO message_fts(record_id,text) VALUES (?,?)", fts_batch
                )
            connection.execute(
                "UPDATE source_files SET records_seen=?,records_inserted=? WHERE source_id=?",
                (seen, inserted, source_id),
            )
            total += inserted
            connection.commit()

        build_sessions(connection)
        build_monthly_map(connection)
        connection.commit()

        message_count = int(connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0])
        fts_count = int(connection.execute("SELECT COUNT(*) FROM message_fts").fetchone()[0])
        membership_count = int(
            connection.execute("SELECT COUNT(*) FROM session_messages").fetchone()[0]
        )
        if not (message_count == total == fts_count == membership_count):
            raise RuntimeError(
                f"reconciliation failed messages={message_count} inserted={total} "
                f"fts={fts_count} memberships={membership_count}"
            )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        counts = {
            "messages": message_count,
            "text_bearing": int(connection.execute(
                "SELECT COUNT(*) FROM messages WHERE text<>''"
            ).fetchone()[0]),
            "operator_messages": int(connection.execute(
                "SELECT COUNT(*) FROM messages WHERE author_role='operator'"
            ).fetchone()[0]),
            "threads": int(connection.execute("SELECT COUNT(*) FROM threads").fetchone()[0]),
            "sessions": int(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]),
            "months": int(connection.execute(
                "SELECT COUNT(DISTINCT month) FROM monthly_map"
            ).fetchone()[0]),
            "sources": int(connection.execute("SELECT COUNT(*) FROM source_files").fetchone()[0]),
        }
        by_source = [
            dict(row) for row in connection.execute(
                """SELECT platform,namespace,records_seen,records_inserted
                   FROM source_files ORDER BY platform,namespace"""
            )
        ]
    finally:
        connection.close()

    os.replace(temp, output)
    os.chmod(output, 0o600)

    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        with gzip.open(export_path, "wt", encoding="utf-8", compresslevel=6) as handle:
            for row in connection.execute(
                """SELECT e.* FROM tier1_evidence e
                   ORDER BY e.timestamp,e.platform,e.namespace,e.record_id"""
            ):
                handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
    finally:
        connection.close()
    os.chmod(export_path, 0o600)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "database": str(output),
        "database_sha256": file_digest(output),
        "chronological_export": str(export_path),
        "chronological_export_sha256": file_digest(export_path),
        "counts": counts,
        "by_source": by_source,
        "tiers": {
            "tier1": "tier1_evidence — exact source observations",
            "tier2": "tier2_episodes — deterministic 12-hour conversation sessions",
            "tier3": "tier3_memory_map — evidence-linked interpretations",
        },
        "immutability": "All inputs are read-only canonical derivatives of preserved exports.",
        "training_authorised": False,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.root, args.output, args.export, args.manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as exc:
        print(f"error: {exc}")
        raise SystemExit(2)
