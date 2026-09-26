"""Local operational ledger for observations, decisions, actions and receipts.

The Markdown memory remains the human-auditable personal canon.  This SQLite store supplies
transactionality, idempotency and lifecycle evidence; it must not become a second biography.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


SCHEMA_VERSION = 2
DEFAULT_DATABASE = Path.home() / ".giga" / "twin.sqlite3"
TRUST_CLASSES = {
    "operator_confirmed",
    "source_observation",
    "third_party_claim",
    "model_inference",
    "model_output",
}
SENSITIVITY_CLASSES = {"internal", "sensitive", "restricted"}
AUTHORITY_LEVELS = {"A0", "A1", "A2", "A3", "A4", "AX"}
GOAL_STATUSES = {"proposed", "active", "paused", "achieved", "abandoned"}
DECISION_STATUSES = {"open", "recommended", "decided", "observing", "resolved", "abandoned"}
ACTION_STATUSES = {"proposed", "approved", "running", "committed", "failed", "rolled_back", "cancelled"}
RECEIPT_STATUSES = {"committed", "rejected", "failed", "rolled_back"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_REVISION_STATUSES = {"current", "superseded"}
ARTIFACT_PROVENANCE_MODES = {"built", "reconciled", "legacy"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


def _json(value: Any) -> str:
    """Canonical JSON; reject NaN and non-serialisable data."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _json_hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _timestamp(value: str | None, *, field: str) -> str:
    candidate = value or utc_now()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _enum(value: str, allowed: set[str], field: str) -> str:
    if value not in allowed:
        raise ValueError(f"{field} must be one of {sorted(allowed)}")
    return value


def _text(value: str, field: str, *, maximum: int = 20_000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    return cleaned


class TwinStore:
    """SQLite-backed trust kernel with secure local defaults."""

    def __init__(self, database: Path = DEFAULT_DATABASE):
        self.database = database.expanduser().resolve()
        parent_existed = self.database.parent.exists()
        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Never chmod a caller-supplied shared parent such as /tmp.  Enforce 0700 on the
        # kernel's own default directory and on directories created by this constructor.
        if not parent_existed or self.database.parent == DEFAULT_DATABASE.parent.resolve():
            os.chmod(self.database.parent, 0o700)
        self._initialise()
        os.chmod(self.database, 0o600)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialise(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    schema_version INTEGER NOT NULL,
                    migrated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    trust_class TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    content_ref TEXT,
                    CHECK(trust_class IN ('operator_confirmed','source_observation',
                          'third_party_claim','model_inference','model_output')),
                    CHECK(sensitivity IN ('internal','sensitive','restricted'))
                );

                CREATE TABLE IF NOT EXISTS processing_attempts (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL REFERENCES events(id),
                    processor TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN
                        ('claimed','staged','validated','committed','retry','dead_letter')),
                    attempt_no INTEGER NOT NULL CHECK(attempt_no > 0),
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    error_class TEXT,
                    error_detail TEXT,
                    UNIQUE(event_id, processor, attempt_no)
                );

                CREATE TABLE IF NOT EXISTS receipts (
                    id TEXT PRIMARY KEY,
                    event_id TEXT REFERENCES events(id),
                    action_id TEXT,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN
                        ('committed','rejected','failed','rolled_back')),
                    artifacts_json TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    CHECK(event_id IS NOT NULL OR action_id IS NOT NULL)
                );

                CREATE TABLE IF NOT EXISTS goals (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN
                        ('proposed','active','paused','achieved','abandoned')),
                    priority REAL NOT NULL CHECK(priority >= 0 AND priority <= 1),
                    deadline TEXT,
                    measures_json TEXT NOT NULL,
                    constraints_json TEXT NOT NULL,
                    source_event_id TEXT REFERENCES events(id),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    trigger TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN
                        ('open','recommended','decided','observing','resolved','abandoned')),
                    goal_ids_json TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    evidence_event_ids_json TEXT NOT NULL,
                    recommendation_json TEXT,
                    selected_option_json TEXT,
                    confidence REAL CHECK(confidence IS NULL OR
                        (confidence >= 0 AND confidence <= 1)),
                    authority_level TEXT NOT NULL CHECK(authority_level IN
                        ('A0','A1','A2','A3','A4','AX')),
                    reversibility TEXT NOT NULL,
                    deadline TEXT,
                    created_at TEXT NOT NULL,
                    decided_at TEXT,
                    outcome_json TEXT,
                    resolved_at TEXT
                );

                CREATE TABLE IF NOT EXISTS actions (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL REFERENCES decisions(id),
                    capability TEXT NOT NULL,
                    target TEXT NOT NULL,
                    authority_level TEXT NOT NULL CHECK(authority_level IN
                        ('A0','A1','A2','A3','A4','AX')),
                    max_cost REAL NOT NULL CHECK(max_cost >= 0),
                    reversible INTEGER NOT NULL CHECK(reversible IN (0,1)),
                    status TEXT NOT NULL CHECK(status IN
                        ('proposed','approved','running','committed','failed','rolled_back','cancelled')),
                    expected_receipt TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS derived_artifacts (
                    path TEXT PRIMARY KEY,
                    artifact_sha256 TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    build_command TEXT NOT NULL,
                    built_at TEXT NOT NULL,
                    stale INTEGER NOT NULL DEFAULT 0 CHECK(stale IN (0,1))
                );

                CREATE TABLE IF NOT EXISTS derived_artifact_revisions (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    build_command TEXT NOT NULL,
                    built_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('current','superseded')),
                    provenance_mode TEXT NOT NULL CHECK(provenance_mode IN
                        ('built','reconciled','legacy')),
                    supersedes_revision_id TEXT REFERENCES derived_artifact_revisions(id),
                    authority_event_id TEXT REFERENCES events(id),
                    verification_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_kind_time ON events(kind, observed_at);
                CREATE INDEX IF NOT EXISTS idx_attempts_event_state ON processing_attempts(event_id, state);
                CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_artifact_revisions_path_time
                    ON derived_artifact_revisions(path, built_at);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_artifact_revisions_current
                    ON derived_artifact_revisions(path) WHERE status = 'current';
                """
            )
            current = connection.execute(
                "SELECT schema_version FROM schema_metadata WHERE singleton = 1"
            ).fetchone()
            if current is None:
                connection.execute(
                    "INSERT INTO schema_metadata VALUES (1, ?, ?)",
                    (SCHEMA_VERSION, utc_now()),
                )
            elif current["schema_version"] == 1:
                self._migrate_v1_to_v2(connection)
            elif current["schema_version"] != SCHEMA_VERSION:
                raise RuntimeError(
                    f"unsupported twin schema {current['schema_version']}; expected {SCHEMA_VERSION}"
                )

    def _migrate_v1_to_v2(self, connection: sqlite3.Connection) -> None:
        """Preserve every v1 projection row as a first-class legacy revision."""
        revision_count = int(
            connection.execute("SELECT COUNT(*) FROM derived_artifact_revisions").fetchone()[0]
        )
        if revision_count:
            raise RuntimeError("schema v1 migration found unexpected artifact revision rows")
        rows = connection.execute(
            """SELECT path,artifact_sha256,source_refs_json,build_command,built_at,stale
               FROM derived_artifacts ORDER BY path"""
        ).fetchall()
        for row in rows:
            connection.execute(
                """INSERT INTO derived_artifact_revisions
                (id,path,artifact_sha256,source_refs_json,build_command,built_at,status,
                 provenance_mode,supersedes_revision_id,authority_event_id,verification_json)
                VALUES (?,?,?,?,?,?,'current','legacy',NULL,NULL,?)""",
                (
                    _uuid(), row["path"], row["artifact_sha256"], row["source_refs_json"],
                    row["build_command"], row["built_at"],
                    _json({"migrated_from_schema": 1, "legacy_stale": bool(row["stale"])}),
                ),
            )
        connection.execute(
            "UPDATE schema_metadata SET schema_version = ?, migrated_at = ? WHERE singleton = 1",
            (SCHEMA_VERSION, utc_now()),
        )

    def record_event(
        self,
        *,
        idempotency_key: str,
        kind: str,
        observed_at: str,
        source: str,
        actor: str,
        trust_class: str,
        sensitivity: str,
        payload: Mapping[str, Any],
        content_ref: str | None = None,
        captured_at: str | None = None,
    ) -> tuple[str, bool]:
        """Append an event, returning ``(id, created)`` for idempotent replays."""
        key = _text(idempotency_key, "idempotency_key", maximum=500)
        event_kind = _text(kind, "kind", maximum=120)
        source_value = _text(source, "source", maximum=500)
        actor_value = _text(actor, "actor", maximum=200)
        trust = _enum(trust_class, TRUST_CLASSES, "trust_class")
        sensitivity_value = _enum(sensitivity, SENSITIVITY_CLASSES, "sensitivity")
        observed = _timestamp(observed_at, field="observed_at")
        captured = _timestamp(captured_at, field="captured_at")
        payload_text = _json(dict(payload))
        payload_digest = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        event_id = _uuid()
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id, payload_sha256 FROM events WHERE idempotency_key = ?", (key,)
            ).fetchone()
            if existing is not None:
                if existing["payload_sha256"] != payload_digest:
                    raise ValueError("idempotency_key replay changed the event payload")
                return str(existing["id"]), False
            connection.execute(
                """INSERT INTO events
                (id,idempotency_key,kind,observed_at,captured_at,source,actor,trust_class,
                 sensitivity,payload_json,payload_sha256,content_ref)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event_id, key, event_kind, observed, captured, source_value, actor_value,
                 trust, sensitivity_value, payload_text, payload_digest, content_ref),
            )
        return event_id, True

    def start_attempt(self, event_id: str, processor: str) -> tuple[str, int]:
        processor_value = _text(processor, "processor", maximum=200)
        attempt_id = _uuid()
        with self.connect() as connection:
            if connection.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone() is None:
                raise KeyError(f"unknown event {event_id}")
            number = connection.execute(
                "SELECT COALESCE(MAX(attempt_no), 0) + 1 FROM processing_attempts "
                "WHERE event_id = ? AND processor = ?",
                (event_id, processor_value),
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO processing_attempts
                (id,event_id,processor,state,attempt_no,started_at)
                VALUES (?,?,?,?,?,?)""",
                (attempt_id, event_id, processor_value, "claimed", number, utc_now()),
            )
        return attempt_id, int(number)

    def transition_attempt(
        self,
        attempt_id: str,
        state: str,
        *,
        error_class: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        allowed = {
            "claimed": {"staged", "retry", "dead_letter"},
            "staged": {"validated", "retry", "dead_letter"},
            "validated": {"committed", "retry", "dead_letter"},
            "committed": set(),
            "retry": set(),
            "dead_letter": set(),
        }
        if state not in allowed:
            raise ValueError(f"invalid attempt state {state}")
        with self.connect() as connection:
            current = connection.execute(
                "SELECT state FROM processing_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"unknown processing attempt {attempt_id}")
            if state not in allowed[current["state"]]:
                raise ValueError(f"invalid attempt transition {current['state']} -> {state}")
            connection.execute(
                """UPDATE processing_attempts SET state = ?, finished_at = ?,
                   error_class = ?, error_detail = ? WHERE id = ?""",
                (state, utc_now(), error_class, error_detail, attempt_id),
            )

    def record_receipt(
        self,
        *,
        operation: str,
        status: str,
        event_id: str | None = None,
        action_id: str | None = None,
        artifacts: Sequence[Mapping[str, Any]] = (),
        details: Mapping[str, Any] | None = None,
    ) -> str:
        receipt_status = _enum(status, RECEIPT_STATUSES, "status")
        if (event_id is None) == (action_id is None):
            raise ValueError("receipt must reference exactly one event or action")
        receipt_id = _uuid()
        with self.connect() as connection:
            if event_id is not None and connection.execute(
                "SELECT 1 FROM events WHERE id = ?", (event_id,)
            ).fetchone() is None:
                raise KeyError(f"unknown event {event_id}")
            if action_id is not None and connection.execute(
                "SELECT 1 FROM actions WHERE id = ?", (action_id,)
            ).fetchone() is None:
                raise KeyError(f"unknown action {action_id}")
            connection.execute(
                """INSERT INTO receipts
                (id,event_id,action_id,operation,status,artifacts_json,details_json,recorded_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (receipt_id, event_id, action_id, _text(operation, "operation", maximum=200),
                 receipt_status, _json(list(artifacts)), _json(dict(details or {})), utc_now()),
            )
        return receipt_id

    def latest_receipt(self, event_id: str, operation: str) -> dict[str, Any] | None:
        """Return the latest committed receipt for replay without re-invoking a provider."""
        with self.connect() as connection:
            row = connection.execute(
                """SELECT id, status, artifacts_json, details_json, recorded_at
                   FROM receipts WHERE event_id = ? AND operation = ? AND status = 'committed'
                   ORDER BY recorded_at DESC, id DESC LIMIT 1""",
                (event_id, _text(operation, "operation", maximum=200)),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "status": row["status"],
            "artifacts": json.loads(row["artifacts_json"]),
            "details": json.loads(row["details_json"]),
            "recorded_at": row["recorded_at"],
        }

    def create_goal(
        self,
        *,
        title: str,
        description: str,
        priority: float,
        deadline: str | None = None,
        measures: Sequence[Mapping[str, Any]] = (),
        constraints: Sequence[Mapping[str, Any]] = (),
        source_event_id: str | None = None,
        status: str = "proposed",
    ) -> str:
        _enum(status, GOAL_STATUSES, "status")
        if isinstance(priority, bool) or not 0 <= float(priority) <= 1:
            raise ValueError("priority must be between 0 and 1")
        goal_id, now = _uuid(), utc_now()
        with self.connect() as connection:
            if source_event_id is not None and connection.execute(
                "SELECT 1 FROM events WHERE id = ?", (source_event_id,)
            ).fetchone() is None:
                raise KeyError(f"unknown source event {source_event_id}")
            connection.execute(
                """INSERT INTO goals
                (id,title,description,status,priority,deadline,measures_json,constraints_json,
                 source_event_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (goal_id, _text(title, "title", maximum=500),
                 _text(description, "description"), status, float(priority), deadline,
                 _json(list(measures)), _json(list(constraints)), source_event_id, now, now),
            )
        return goal_id

    def create_decision(
        self,
        *,
        trigger: str,
        goal_ids: Sequence[str],
        options: Sequence[Mapping[str, Any]],
        evidence_event_ids: Sequence[str] = (),
        authority_level: str = "A1",
        reversibility: str = "unknown",
        deadline: str | None = None,
    ) -> str:
        _enum(authority_level, AUTHORITY_LEVELS, "authority_level")
        if not options:
            raise ValueError("a decision needs at least one option")
        decision_id = _uuid()
        with self.connect() as connection:
            known_goals = {
                row[0] for row in connection.execute(
                    f"SELECT id FROM goals WHERE id IN ({','.join('?' for _ in goal_ids)})",
                    tuple(goal_ids),
                )
            } if goal_ids else set()
            if set(goal_ids) != known_goals:
                raise KeyError("decision references an unknown goal")
            known_events = {
                row[0] for row in connection.execute(
                    f"SELECT id FROM events WHERE id IN ({','.join('?' for _ in evidence_event_ids)})",
                    tuple(evidence_event_ids),
                )
            } if evidence_event_ids else set()
            if set(evidence_event_ids) != known_events:
                raise KeyError("decision references unknown evidence")
            connection.execute(
                """INSERT INTO decisions
                (id,trigger,status,goal_ids_json,options_json,evidence_event_ids_json,
                 authority_level,reversibility,deadline,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (decision_id, _text(trigger, "trigger"), "open", _json(list(goal_ids)),
                 _json(list(options)), _json(list(evidence_event_ids)), authority_level,
                 _text(reversibility, "reversibility", maximum=120), deadline, utc_now()),
            )
        return decision_id

    def register_artifact(
        self,
        *,
        path: str,
        artifact_sha256: str,
        source_refs: Sequence[Mapping[str, Any]],
        build_command: str,
        built_at: str | None = None,
    ) -> str:
        """Register a built artefact revision without erasing its previous lineage."""
        return self._register_artifact_revision(
            path=path,
            artifact_sha256=artifact_sha256,
            source_refs=source_refs,
            build_command=build_command,
            built_at=built_at,
            provenance_mode="built",
            authority_event_id=None,
            verification={"registration": "build"},
        )

    def reconcile_artifact(
        self,
        *,
        path: str,
        artifact_sha256: str,
        source_refs: Sequence[Mapping[str, Any]],
        authority_event_id: str,
        verification: Mapping[str, Any],
        build_command: str = "operator-authorized current-state lineage reconciliation",
        built_at: str | None = None,
    ) -> str:
        """Adopt a verified current state while retaining the historical registration."""
        if verification.get("ok") is not True:
            raise ValueError("reconciliation verification must explicitly pass")
        return self._register_artifact_revision(
            path=path,
            artifact_sha256=artifact_sha256,
            source_refs=source_refs,
            build_command=build_command,
            built_at=built_at,
            provenance_mode="reconciled",
            authority_event_id=_text(authority_event_id, "authority_event_id", maximum=200),
            verification=verification,
        )

    def _register_artifact_revision(
        self,
        *,
        path: str,
        artifact_sha256: str,
        source_refs: Sequence[Mapping[str, Any]],
        build_command: str,
        built_at: str | None,
        provenance_mode: str,
        authority_event_id: str | None,
        verification: Mapping[str, Any],
    ) -> str:
        artifact_path = _text(path, "path", maximum=2_000)
        if not SHA256.fullmatch(artifact_sha256):
            raise ValueError("artifact_sha256 must be 64 lowercase hexadecimal characters")
        if not source_refs:
            raise ValueError("a derived artifact needs at least one source reference")
        normalised_refs: list[dict[str, str]] = []
        for ref in source_refs:
            relative = ref.get("path") if isinstance(ref, Mapping) else None
            digest = ref.get("sha256") if isinstance(ref, Mapping) else None
            if not isinstance(relative, str) or not relative.strip():
                raise ValueError("source reference path must be non-empty text")
            if not isinstance(digest, str) or not SHA256.fullmatch(digest):
                raise ValueError("source reference sha256 must be 64 lowercase hexadecimal characters")
            normalised_refs.append({"path": relative.strip(), "sha256": digest})
        mode = _enum(provenance_mode, ARTIFACT_PROVENANCE_MODES, "provenance_mode")
        built = _timestamp(built_at, field="built_at")
        command = _text(build_command, "build_command", maximum=10_000)
        refs_json = _json(normalised_refs)
        verification_json = _json(dict(verification))
        with self.connect() as connection:
            if authority_event_id is not None:
                authority = connection.execute(
                    "SELECT trust_class FROM events WHERE id = ?", (authority_event_id,)
                ).fetchone()
                if authority is None:
                    raise KeyError(f"unknown authority event {authority_event_id}")
                if authority["trust_class"] != "operator_confirmed":
                    raise ValueError("artifact reconciliation requires an operator-confirmed event")
            current = connection.execute(
                """SELECT id,artifact_sha256,source_refs_json,build_command,provenance_mode,
                          authority_event_id,verification_json
                   FROM derived_artifact_revisions
                   WHERE path = ? AND status = 'current'""",
                (artifact_path,),
            ).fetchone()
            if current is not None and all((
                current["artifact_sha256"] == artifact_sha256,
                current["source_refs_json"] == refs_json,
                current["build_command"] == command,
                current["provenance_mode"] == mode,
                current["authority_event_id"] == authority_event_id,
                current["verification_json"] == verification_json,
            )):
                connection.execute(
                    "UPDATE derived_artifacts SET stale = 0 WHERE path = ?", (artifact_path,)
                )
                return str(current["id"])
            prior_revision_id = str(current["id"]) if current is not None else None
            if current is not None:
                connection.execute(
                    "UPDATE derived_artifact_revisions SET status = 'superseded' WHERE id = ?",
                    (prior_revision_id,),
                )
            revision_id = _uuid()
            connection.execute(
                """INSERT INTO derived_artifact_revisions
                (id,path,artifact_sha256,source_refs_json,build_command,built_at,status,
                 provenance_mode,supersedes_revision_id,authority_event_id,verification_json)
                VALUES (?,?,?,?,?,?,'current',?,?,?,?)""",
                (
                    revision_id, artifact_path, artifact_sha256, refs_json, command, built,
                    mode, prior_revision_id, authority_event_id, verification_json,
                ),
            )
            connection.execute(
                """INSERT INTO derived_artifacts
                (path,artifact_sha256,source_refs_json,build_command,built_at,stale)
                VALUES (?,?,?,?,?,0)
                ON CONFLICT(path) DO UPDATE SET
                    artifact_sha256=excluded.artifact_sha256,
                    source_refs_json=excluded.source_refs_json,
                    build_command=excluded.build_command,
                    built_at=excluded.built_at,
                    stale=0""",
                (artifact_path, artifact_sha256, refs_json, command, built),
            )
        return revision_id

    def artifact_history(self, path: str | None = None) -> list[dict[str, Any]]:
        """Return current and superseded lineage revisions, newest first."""
        parameters: tuple[str, ...] = ()
        where = ""
        if path is not None:
            where = "WHERE path = ?"
            parameters = (_text(path, "path", maximum=2_000),)
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT id,path,artifact_sha256,source_refs_json,build_command,built_at,
                           status,provenance_mode,supersedes_revision_id,authority_event_id,
                           verification_json
                    FROM derived_artifact_revisions {where}
                    ORDER BY CASE status WHEN 'current' THEN 0 ELSE 1 END,
                             built_at DESC, id DESC""",
                parameters,
            ).fetchall()
        return [
            {
                "id": row["id"],
                "path": row["path"],
                "artifact_sha256": row["artifact_sha256"],
                "source_refs": json.loads(row["source_refs_json"]),
                "build_command": row["build_command"],
                "built_at": row["built_at"],
                "status": row["status"],
                "provenance_mode": row["provenance_mode"],
                "supersedes_revision_id": row["supersedes_revision_id"],
                "authority_event_id": row["authority_event_id"],
                "verification": json.loads(row["verification_json"]),
            }
            for row in rows
        ]

    def mark_artifact_stale(self, path: str) -> None:
        artifact_path = _text(path, "path", maximum=2_000)
        with self.connect() as connection:
            changed = connection.execute(
                "UPDATE derived_artifacts SET stale = 1 WHERE path = ?", (artifact_path,)
            ).rowcount
            if not changed:
                raise KeyError(f"unknown derived artifact {artifact_path}")

    def audit_artifacts(self, root: Path) -> dict[str, Any]:
        """Re-hash registered artefacts and sources without mutating either."""
        root = root.resolve()
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT a.path, a.artifact_sha256, a.source_refs_json, a.build_command,
                          a.built_at, a.stale, r.id AS current_revision_id,
                          r.provenance_mode, r.authority_event_id
                   FROM derived_artifacts a
                   LEFT JOIN derived_artifact_revisions r
                     ON r.path = a.path AND r.status = 'current'
                   ORDER BY a.path"""
            ).fetchall()
            revision_counts = {
                str(row["status"]): int(row["amount"])
                for row in connection.execute(
                    """SELECT status, COUNT(*) AS amount FROM derived_artifact_revisions
                       GROUP BY status"""
                ).fetchall()
            }
        results: list[dict[str, Any]] = []
        for row in rows:
            reasons: list[str] = []
            artifact_path = (root / row["path"]).resolve()
            try:
                artifact_path.relative_to(root)
            except ValueError:
                reasons.append("artifact path escapes GIGA root")
            actual_artifact = None
            if not reasons and artifact_path.is_file():
                digest = hashlib.sha256()
                with artifact_path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                actual_artifact = digest.hexdigest()
                if actual_artifact != row["artifact_sha256"]:
                    reasons.append("artifact content changed")
            elif not reasons:
                reasons.append("artifact is missing")

            try:
                refs = json.loads(row["source_refs_json"])
            except json.JSONDecodeError:
                refs = []
                reasons.append("source reference JSON is invalid")
            source_results: list[dict[str, Any]] = []
            for ref in refs if isinstance(refs, list) else []:
                relative = ref.get("path") if isinstance(ref, dict) else None
                expected = ref.get("sha256") if isinstance(ref, dict) else None
                source_result = {"path": relative, "expected_sha256": expected, "ok": False}
                if not isinstance(relative, str) or not isinstance(expected, str):
                    reasons.append("source reference lacks path or sha256")
                    source_results.append(source_result)
                    continue
                source_path = (root / relative).resolve()
                try:
                    source_path.relative_to(root)
                except ValueError:
                    reasons.append(f"source path escapes GIGA root: {relative}")
                    source_results.append(source_result)
                    continue
                if not source_path.is_file():
                    reasons.append(f"source is missing: {relative}")
                    source_results.append(source_result)
                    continue
                digest = hashlib.sha256()
                with source_path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                actual = digest.hexdigest()
                source_result.update({"actual_sha256": actual, "ok": actual == expected})
                if actual != expected:
                    reasons.append(f"source changed: {relative}")
                source_results.append(source_result)
            if row["stale"]:
                reasons.append("explicitly marked stale")
            results.append({
                "path": row["path"],
                "expected_sha256": row["artifact_sha256"],
                "actual_sha256": actual_artifact,
                "built_at": row["built_at"],
                "build_command": row["build_command"],
                "current_revision_id": row["current_revision_id"],
                "provenance_mode": row["provenance_mode"],
                "authority_event_id": row["authority_event_id"],
                "sources": source_results,
                "ok": not reasons,
                "reasons": reasons,
            })
        return {
            "ok": bool(results) and all(item["ok"] for item in results),
            "artifacts": results,
            "lineage": {
                "active": len(results),
                "revisions": sum(revision_counts.values()),
                "current": revision_counts.get("current", 0),
                "superseded": revision_counts.get("superseded", 0),
            },
        }

    def counts(self) -> dict[str, int]:
        tables = (
            "events", "processing_attempts", "receipts", "goals", "decisions", "actions",
            "derived_artifacts", "derived_artifact_revisions",
        )
        with self.connect() as connection:
            return {table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                    for table in tables}
