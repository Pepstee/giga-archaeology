from __future__ import annotations

import json
import os
import sqlite3
import stat
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from twin_core.store import TwinStore


class TwinStoreTests(unittest.TestCase):
    def test_latest_operation_receipt_includes_failure_and_breaks_timestamp_ties(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(Path(folder))
            event_id, _ = store.record_event(
                idempotency_key="synthetic:tie", kind="test", observed_at="2026-07-20T00:00:00Z",
                source="test", actor="operator", trust_class="operator_confirmed",
                sensitivity="internal", payload={"synthetic": True},
            )
            self.assertIsNone(store.latest_operation_receipt(event_id, "test.compare"))
            committed = store.record_receipt(event_id=event_id, operation="test.compare", status="committed")
            failed = store.record_receipt(event_id=event_id, operation="test.compare", status="failed", details={"attempt_no": 2})
            with store.connect() as connection:
                connection.execute("UPDATE receipts SET recorded_at = ? WHERE event_id = ?", ("2026-07-20T00:00:00Z", event_id))
            latest = store.latest_operation_receipt(event_id, "test.compare")
            self.assertEqual(latest["id"], failed)
            self.assertEqual(latest["status"], "failed")
            self.assertEqual(latest, store.latest_operation_receipt(event_id, "test.compare"))
            self.assertEqual(store.latest_receipt(event_id, "test.compare")["id"], committed)

    def make_store(self, root: Path) -> TwinStore:
        return TwinStore(root / "private" / "twin.sqlite3")

    def test_event_replay_is_idempotent_and_payload_change_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(Path(folder))
            values = dict(
                idempotency_key="telegram:42",
                kind="message.received",
                observed_at=datetime.now(timezone.utc).isoformat(),
                source="telegram",
                actor="operator",
                trust_class="operator_confirmed",
                sensitivity="sensitive",
                payload={"text": "remember this"},
            )
            first, created = store.record_event(**values)
            replay, replay_created = store.record_event(**values)
            self.assertEqual(first, replay)
            self.assertTrue(created)
            self.assertFalse(replay_created)
            with self.assertRaises(ValueError):
                store.record_event(**{**values, "payload": {"text": "changed"}})
            self.assertEqual(store.counts()["events"], 1)

    def test_attempt_state_machine_and_receipt_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(Path(folder))
            event_id, _ = store.record_event(
                idempotency_key="test:1", kind="test", observed_at="2026-07-20T00:00:00Z",
                source="test", actor="operator", trust_class="operator_confirmed",
                sensitivity="internal", payload={"ok": True},
            )
            attempt, number = store.start_attempt(event_id, "memory-ingest")
            self.assertEqual(number, 1)
            store.transition_attempt(attempt, "staged")
            store.transition_attempt(attempt, "validated")
            store.transition_attempt(attempt, "committed")
            with self.assertRaises(ValueError):
                store.transition_attempt(attempt, "retry")
            receipt = store.record_receipt(
                event_id=event_id, operation="memory.commit", status="committed",
                artifacts=[{"path": "memory/example.md", "sha256": "abc"}],
            )
            self.assertTrue(receipt)
            latest = store.latest_receipt(event_id, "memory.commit")
            self.assertIsNotNone(latest)
            assert latest is not None
            self.assertEqual(latest["artifacts"][0]["path"], "memory/example.md")
            with self.assertRaises(KeyError):
                store.record_receipt(event_id="missing", operation="x", status="failed")

    def test_goal_and_decision_references_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(Path(folder))
            event_id, _ = store.record_event(
                idempotency_key="goal:source", kind="goal.ratified",
                observed_at="2026-07-20T00:00:00+00:00", source="operator",
                actor="operator", trust_class="operator_confirmed", sensitivity="internal",
                payload={"goal": "Build Virtual Artiom"},
            )
            goal_id = store.create_goal(
                title="Build Virtual Artiom", description="Measured faithful agency",
                priority=1.0, source_event_id=event_id,
                measures=[{"name": "accuracy", "direction": "increase"}],
            )
            decision_id = store.create_decision(
                trigger="Choose the first implementation slice", goal_ids=[goal_id],
                options=[{"id": "trust-kernel"}, {"id": "style-training"}],
                evidence_event_ids=[event_id], authority_level="A1",
                reversibility="reversible local code",
            )
            self.assertTrue(decision_id)
            with self.assertRaises(KeyError):
                store.create_decision(
                    trigger="bad", goal_ids=["missing"], options=[{"id": "x"}]
                )

    def test_derived_artifact_registry_requires_digest_and_sources(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(Path(folder))
            store.register_artifact(
                path="architecture/map.md",
                artifact_sha256="a" * 64,
                source_refs=[{"path": "00_MASTER.md", "sha256": "b" * 64}],
                build_command="python3 -m twin_core maturity",
                built_at="2026-07-20T00:00:00Z",
            )
            self.assertEqual(store.counts()["derived_artifacts"], 1)
            (Path(folder) / "architecture").mkdir()
            (Path(folder) / "architecture" / "map.md").write_text("map", encoding="utf-8")
            # Re-register the real digest so a complete lineage audit can pass.
            import hashlib
            digest = hashlib.sha256(b"map").hexdigest()
            source = Path(folder) / "source.md"
            source.write_text("source", encoding="utf-8")
            source_digest = hashlib.sha256(b"source").hexdigest()
            store.register_artifact(
                path="architecture/map.md", artifact_sha256=digest,
                source_refs=[{"path": "source.md", "sha256": source_digest}],
                build_command="build", built_at="2026-07-20T00:00:00Z",
            )
            self.assertTrue(store.audit_artifacts(Path(folder))["ok"])
            history = store.artifact_history("architecture/map.md")
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["status"], "current")
            self.assertEqual(history[0]["provenance_mode"], "built")
            self.assertEqual(history[1]["status"], "superseded")
            source.write_text("changed", encoding="utf-8")
            self.assertFalse(store.audit_artifacts(Path(folder))["ok"])
            store.mark_artifact_stale("architecture/map.md")
            with self.assertRaises(KeyError):
                store.mark_artifact_stale("missing")
            with self.assertRaises(ValueError):
                store.register_artifact(
                    path="bad", artifact_sha256="not-a-digest", source_refs=[{"id": "x"}],
                    build_command="build",
                )

    def test_schema_v1_artifacts_migrate_to_preserved_legacy_revisions(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "private" / "twin.sqlite3"
            database.parent.mkdir()
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE schema_metadata (
                    singleton INTEGER PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    migrated_at TEXT NOT NULL
                );
                CREATE TABLE derived_artifacts (
                    path TEXT PRIMARY KEY,
                    artifact_sha256 TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    build_command TEXT NOT NULL,
                    built_at TEXT NOT NULL,
                    stale INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            connection.execute(
                "INSERT INTO schema_metadata VALUES (1,1,'2026-07-20T00:00:00+00:00')"
            )
            connection.execute(
                "INSERT INTO derived_artifacts VALUES (?,?,?,?,?,0)",
                (
                    "architecture/map.md", "a" * 64,
                    json.dumps([{"path": "source.md", "sha256": "b" * 64}]),
                    "legacy build", "2026-07-20T00:00:00+00:00",
                ),
            )
            connection.commit()
            connection.close()

            store = TwinStore(database)
            history = store.artifact_history("architecture/map.md")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["provenance_mode"], "legacy")
            self.assertEqual(history[0]["artifact_sha256"], "a" * 64)
            with store.connect() as current:
                version = current.execute(
                    "SELECT schema_version FROM schema_metadata WHERE singleton = 1"
                ).fetchone()[0]
            self.assertEqual(version, 2)

    def test_reconciliation_requires_operator_authority_and_preserves_history(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(Path(folder))
            store.register_artifact(
                path="architecture/map.md", artifact_sha256="a" * 64,
                source_refs=[{"path": "old.md", "sha256": "b" * 64}],
                build_command="old build", built_at="2026-07-20T00:00:00Z",
            )
            inferred_event, _ = store.record_event(
                idempotency_key="lineage:inferred", kind="lineage.reconciliation.authorized",
                observed_at="2026-07-22T00:00:00Z", source="test", actor="model",
                trust_class="model_inference", sensitivity="internal", payload={"ok": True},
            )
            with self.assertRaises(ValueError):
                store.reconcile_artifact(
                    path="architecture/map.md", artifact_sha256="c" * 64,
                    source_refs=[{"path": "new.md", "sha256": "d" * 64}],
                    authority_event_id=inferred_event, verification={"ok": True},
                )
            authority_event, _ = store.record_event(
                idempotency_key="lineage:operator", kind="lineage.reconciliation.authorized",
                observed_at="2026-07-22T00:00:00Z", source="operator-request",
                actor="operator", trust_class="operator_confirmed", sensitivity="internal",
                payload={"scope": ["architecture/map.md"]},
            )
            with self.assertRaises(ValueError):
                store.reconcile_artifact(
                    path="architecture/map.md", artifact_sha256="c" * 64,
                    source_refs=[{"path": "new.md", "sha256": "d" * 64}],
                    authority_event_id=authority_event, verification={"ok": False},
                )
            revision = store.reconcile_artifact(
                path="architecture/map.md", artifact_sha256="c" * 64,
                source_refs=[{"path": "new.md", "sha256": "d" * 64}],
                authority_event_id=authority_event,
                verification={"ok": True, "method": "fixture"},
                built_at="2026-07-22T00:00:00Z",
            )
            replay = store.reconcile_artifact(
                path="architecture/map.md", artifact_sha256="c" * 64,
                source_refs=[{"path": "new.md", "sha256": "d" * 64}],
                authority_event_id=authority_event,
                verification={"ok": True, "method": "fixture"},
                built_at="2026-07-22T00:00:00Z",
            )
            self.assertEqual(revision, replay)
            history = store.artifact_history("architecture/map.md")
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["provenance_mode"], "reconciled")
            self.assertEqual(history[0]["authority_event_id"], authority_event)
            self.assertEqual(history[1]["status"], "superseded")

    def test_database_and_directory_are_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(Path(folder))
            self.assertEqual(stat.S_IMODE(store.database.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(store.database.parent.stat().st_mode), 0o700)
