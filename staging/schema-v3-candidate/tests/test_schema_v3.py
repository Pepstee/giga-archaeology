from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path

from twin_core.schema_v3 import TRIGGERS, entropy_report, migrate_v2_to_v3
from twin_core.store import SchemaMigrationRequired, TwinStore


def snapshot(path: Path) -> tuple[int, dict[str, int], str]:
    connection = sqlite3.connect(path)
    try:
        version = connection.execute("SELECT schema_version FROM schema_metadata").fetchone()[0]
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        counts = {table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                  for table in tables}
        schema = "\n".join(row[0] or "" for row in connection.execute(
            "SELECT sql FROM sqlite_schema WHERE sql IS NOT NULL ORDER BY type,name"
        ))
        return int(version), counts, hashlib.sha256(schema.encode()).hexdigest()
    finally:
        connection.close()


def core_digest(path: Path) -> str:
    connection = sqlite3.connect(path)
    try:
        digest = hashlib.sha256()
        for table in ("events", "processing_attempts", "receipts", "goals", "decisions",
                      "actions", "derived_artifacts", "derived_artifact_revisions"):
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            rows = connection.execute(
                f'SELECT * FROM "{table}" ORDER BY ' + ",".join(f'"{c}"' for c in columns)
            ).fetchall()
            digest.update(repr((table, columns, rows)).encode())
        return digest.hexdigest()
    finally:
        connection.close()


def make_v2(path: Path) -> None:
    # Reuse the production-v2 code in a subprocess-independent way by copying a known v2 DB.
    source = Path(os.environ.get("GIGA_V2_FIXTURE", "/Users/admin/.giga/twin.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    destination = sqlite3.connect(path)
    try:
        source_connection.backup(destination)
    finally:
        source_connection.close(); destination.close()


class SchemaV3Tests(unittest.TestCase):
    def test_fresh_store_has_exact_v3_contract(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = TwinStore(Path(folder) / "private" / "twin.sqlite3")
            connection = sqlite3.connect(store.database)
            try:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
                names = {row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_schema WHERE type='trigger'")}
                self.assertEqual(names, set(TRIGGERS))
            finally: connection.close()
            self.assertTrue(entropy_report(store.database)["ok"])

    def test_opening_v2_is_fail_closed_and_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "v2.sqlite3"; make_v2(database)
            before = database.read_bytes()
            with self.assertRaises(SchemaMigrationRequired): TwinStore(database)
            self.assertEqual(before, database.read_bytes())

    def test_migration_preserves_counts_and_backup_and_is_not_repeatable(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "v2.sqlite3"; backup = Path(folder) / "backup.sqlite3"
            make_v2(database); before = snapshot(database)
            logical_before = core_digest(database)
            result = migrate_v2_to_v3(database, backup)
            after = snapshot(database)
            self.assertEqual(before[1]["events"], after[1]["events"])
            self.assertEqual(before[1]["derived_artifact_revisions"], after[1]["derived_artifact_revisions"])
            self.assertEqual(snapshot(backup), before)
            self.assertEqual(core_digest(database), logical_before)
            self.assertEqual(core_digest(backup), logical_before)
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
            self.assertEqual(result["backup_sha256"], hashlib.sha256(backup.read_bytes()).hexdigest())
            self.assertTrue(entropy_report(database)["ok"])
            with self.assertRaises(RuntimeError):
                migrate_v2_to_v3(database, Path(folder) / "again.sqlite3")
            restored = Path(folder) / "restored.sqlite3"
            source = sqlite3.connect(backup); target = sqlite3.connect(restored)
            try: source.backup(target)
            finally: source.close(); target.close()
            self.assertEqual(snapshot(restored), before)
            self.assertEqual(core_digest(restored), logical_before)

    def test_faults_rollback_every_transaction_stage(self) -> None:
        for stage in ("after_lock", "after_backup", "after_ddl", "before_commit"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as folder:
                database = Path(folder) / "v2.sqlite3"; backup = Path(folder) / "backup.sqlite3"
                make_v2(database); before = snapshot(database)
                def fail(current: str) -> None:
                    if current == stage: raise RuntimeError("injected")
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    migrate_v2_to_v3(database, backup, fault_hook=fail)
                self.assertEqual(snapshot(database), before)
                self.assertEqual(backup.is_file(), stage != "after_lock")

    def test_database_triggers_block_revision_corruption_but_allow_normal_append(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = TwinStore(Path(folder) / "db.sqlite3")
            first = store.register_artifact(path="a", artifact_sha256="a"*64,
                source_refs=[{"path":"s","sha256":"b"*64}], build_command="build")
            connection = sqlite3.connect(store.database)
            try:
                for sql in (
                    "DELETE FROM derived_artifact_revisions WHERE id=?",
                    "UPDATE derived_artifact_revisions SET artifact_sha256=? WHERE id=?",
                    "UPDATE derived_artifact_revisions SET status='current' WHERE id=?",
                ):
                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(sql, (("c"*64, first) if "sha256" in sql else (first,)))
                connection.rollback()
            finally: connection.close()
            second = store.register_artifact(path="a", artifact_sha256="d"*64,
                source_refs=[{"path":"s","sha256":"b"*64}], build_command="build")
            self.assertNotEqual(first, second)
            self.assertTrue(entropy_report(store.database)["ok"])

    def test_entropy_detects_projection_and_trigger_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = TwinStore(Path(folder) / "db.sqlite3")
            store.register_artifact(path="a", artifact_sha256="a"*64,
                source_refs=[{"path":"s","sha256":"b"*64}], build_command="build")
            connection = sqlite3.connect(store.database)
            connection.execute("UPDATE derived_artifacts SET artifact_sha256=?", ("c"*64,))
            connection.execute("DROP TRIGGER trg_artifact_revision_no_delete")
            connection.commit(); connection.close()
            result = entropy_report(store.database)
            self.assertFalse(result["ok"])
            failed = {item["name"] for item in result["checks"] if not item["ok"]}
            self.assertEqual(failed, {"schema_contract", "projection_matches_current"})

    def test_user_version_mismatch_and_unknown_existing_database_fail(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = TwinStore(Path(folder) / "db.sqlite3")
            connection = sqlite3.connect(store.database); connection.execute("PRAGMA user_version=2")
            connection.commit(); connection.close()
            with self.assertRaisesRegex(RuntimeError, "entropy"): TwinStore(store.database)
            unknown = Path(folder) / "unknown.sqlite3"
            sqlite3.connect(unknown).close()
            with self.assertRaisesRegex(RuntimeError, "no schema metadata"): TwinStore(unknown)

    def test_writer_lock_causes_clean_timeout_without_partial_schema(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "v2.sqlite3"; backup = Path(folder) / "backup.sqlite3"
            make_v2(database); before = snapshot(database)
            lock = sqlite3.connect(database)
            lock.execute("BEGIN IMMEDIATE")
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    migrate_v2_to_v3(database, backup, timeout=0.05)
            finally:
                lock.rollback(); lock.close()
            self.assertEqual(snapshot(database), before)
            self.assertFalse(backup.exists())


if __name__ == "__main__": unittest.main()
