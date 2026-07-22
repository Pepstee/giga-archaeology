"""Explicit, fail-closed schema-v3 migration and entropy verification."""
from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path
from typing import Callable

from .store import utc_now

SCHEMA_VERSION = 3
MIGRATION_ID = "twin-schema-v2-to-v3-2026-07-22"
MIGRATION_SHA256 = hashlib.sha256(MIGRATION_ID.encode()).hexdigest()

TRIGGERS = {
    "trg_artifact_revision_no_delete": """
        CREATE TRIGGER trg_artifact_revision_no_delete
        BEFORE DELETE ON derived_artifact_revisions
        BEGIN SELECT RAISE(ABORT, 'artifact revisions are append-only'); END""",
    "trg_artifact_revision_immutable": """
        CREATE TRIGGER trg_artifact_revision_immutable
        BEFORE UPDATE OF path,artifact_sha256,source_refs_json,build_command,built_at,
          provenance_mode,supersedes_revision_id,authority_event_id,verification_json
        ON derived_artifact_revisions
        BEGIN SELECT RAISE(ABORT, 'artifact revision payload is immutable'); END""",
    "trg_artifact_revision_status": """
        CREATE TRIGGER trg_artifact_revision_status
        BEFORE UPDATE OF status ON derived_artifact_revisions
        WHEN NOT (OLD.status = 'current' AND NEW.status = 'superseded')
        BEGIN SELECT RAISE(ABORT, 'invalid artifact revision status transition'); END""",
    "trg_artifact_revision_insert_current": """
        CREATE TRIGGER trg_artifact_revision_insert_current
        BEFORE INSERT ON derived_artifact_revisions WHEN NEW.status <> 'current'
        BEGIN SELECT RAISE(ABORT, 'new artifact revision must be current'); END""",
}


def _normalise(sql: str | None) -> str:
    return " ".join((sql or "").split()).lower()


def install_v3_contract(connection: sqlite3.Connection) -> None:
    for sql in TRIGGERS.values():
        connection.execute(sql)


def verify_v3_contract(connection: sqlite3.Connection) -> None:
    metadata = connection.execute(
        "SELECT schema_version FROM schema_metadata WHERE singleton=1"
    ).fetchone()
    if metadata is None or int(metadata[0]) != SCHEMA_VERSION:
        raise RuntimeError("schema_metadata does not identify schema v3")
    user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if user_version != SCHEMA_VERSION:
        raise RuntimeError(f"schema entropy: metadata=3 but user_version={user_version}")
    rows = connection.execute(
        "SELECT name,sql FROM sqlite_schema WHERE type='trigger'"
    ).fetchall()
    actual = {str(row[0]): _normalise(row[1]) for row in rows}
    for name, expected in TRIGGERS.items():
        if actual.get(name) != _normalise(expected):
            raise RuntimeError(f"schema entropy: missing or altered trigger {name}")
    if connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='schema_migrations'"
    ).fetchone() is None:
        raise RuntimeError("schema entropy: schema_migrations ledger is missing")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def migrate_v2_to_v3(
    database: Path,
    backup: Path,
    *,
    fault_hook: Callable[[str], None] | None = None,
    timeout: float = 5.0,
) -> dict[str, object]:
    """Migrate only an exact v2 store, preserving a verified owner-only SQLite backup."""
    database, backup = database.expanduser().resolve(), backup.expanduser().resolve()
    if not database.is_file():
        raise FileNotFoundError(database)
    if database == backup or backup.exists():
        raise ValueError("backup must be a new path distinct from the database")
    backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    connection = sqlite3.connect(database, timeout=timeout)
    try:
        connection.execute(f"PRAGMA busy_timeout={int(timeout * 1000)}")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        version = connection.execute(
            "SELECT schema_version FROM schema_metadata WHERE singleton=1"
        ).fetchone()
        if version is None or int(version[0]) != 2:
            raise RuntimeError("migration requires an exact schema-v2 source")
        if int(connection.execute("PRAGMA user_version").fetchone()[0]) not in (0, 2):
            raise RuntimeError("v2 source has an unexpected user_version")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("source integrity_check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("source foreign_key_check failed")
        if fault_hook:
            fault_hook("after_lock")
        # The reserved writer lock stays held across backup and migration, so the
        # recovery image is the exact immediate pre-migration logical state.
        source = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=timeout)
        destination = sqlite3.connect(backup)
        try:
            source.backup(destination)
        finally:
            source.close()
            destination.close()
        os.chmod(backup, 0o600)
        backup_sha256 = _sha256(backup)
        if fault_hook:
            fault_hook("after_backup")
        connection.execute("""CREATE TABLE schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, from_version INTEGER NOT NULL,
            to_version INTEGER NOT NULL, applied_at TEXT NOT NULL,
            migration_sha256 TEXT NOT NULL, backup_sha256 TEXT NOT NULL)""")
        install_v3_contract(connection)
        if fault_hook:
            fault_hook("after_ddl")
        applied_at = utc_now()
        connection.execute(
            "UPDATE schema_metadata SET schema_version=3,migrated_at=? WHERE singleton=1",
            (applied_at,),
        )
        connection.execute("PRAGMA user_version=3")
        connection.execute(
            "INSERT INTO schema_migrations(from_version,to_version,applied_at,migration_sha256,backup_sha256) VALUES(2,3,?,?,?)",
            (applied_at, MIGRATION_SHA256, backup_sha256),
        )
        if fault_hook:
            fault_hook("before_commit")
        verify_v3_contract(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    check = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        verify_v3_contract(check)
        if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("post-migration integrity_check failed")
        if check.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("post-migration foreign_key_check failed")
    finally:
        check.close()
    return {"from_version": 2, "to_version": 3, "backup": str(backup),
            "backup_sha256": backup_sha256, "migration_sha256": MIGRATION_SHA256}


def entropy_report(database: Path) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    connection = sqlite3.connect(f"file:{database.expanduser().resolve()}?mode=ro", uri=True)
    try:
        def add(name: str, ok: bool, detail: object = None) -> None:
            checks.append({"name": name, "ok": bool(ok), "detail": detail})
        try:
            verify_v3_contract(connection)
            add("schema_contract", True)
        except Exception as exc:
            add("schema_contract", False, str(exc))
        duplicates = connection.execute("""SELECT path,COUNT(*) FROM derived_artifact_revisions
            WHERE status='current' GROUP BY path HAVING COUNT(*)<>1""").fetchall()
        add("one_current_revision", not duplicates, [tuple(row) for row in duplicates])
        mismatch = connection.execute("""SELECT a.path FROM derived_artifacts a
            LEFT JOIN derived_artifact_revisions r ON r.path=a.path AND r.status='current'
            WHERE r.id IS NULL OR a.artifact_sha256<>r.artifact_sha256
              OR a.source_refs_json<>r.source_refs_json OR a.build_command<>r.build_command
              OR a.built_at<>r.built_at""").fetchall()
        add("projection_matches_current", not mismatch, [row[0] for row in mismatch])
        missing_projection = connection.execute("""SELECT r.path FROM derived_artifact_revisions r
            LEFT JOIN derived_artifacts a ON a.path=r.path
            WHERE r.status='current' AND a.path IS NULL""").fetchall()
        add("current_has_projection", not missing_projection, [row[0] for row in missing_projection])
        orphans = connection.execute("""SELECT r.id FROM derived_artifact_revisions r
            LEFT JOIN derived_artifact_revisions p ON p.id=r.supersedes_revision_id
            WHERE r.supersedes_revision_id IS NOT NULL AND p.id IS NULL""").fetchall()
        add("no_orphan_revision_links", not orphans, [row[0] for row in orphans])
        rows = connection.execute("SELECT id,supersedes_revision_id FROM derived_artifact_revisions").fetchall()
        parent = {str(row[0]): (str(row[1]) if row[1] is not None else None) for row in rows}
        cycles: list[str] = []
        for start in parent:
            seen: set[str] = set()
            node: str | None = start
            while node is not None and node in parent:
                if node in seen:
                    cycles.append(start); break
                seen.add(node); node = parent[node]
        add("no_revision_cycles", not cycles, cycles)
    finally:
        connection.close()
    return {"ok": all(bool(item["ok"]) for item in checks), "checks": checks}
