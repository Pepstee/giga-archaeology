from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from twin_core.store import TwinStore
from twin_core.telegram_pipeline import _process_event as process_event
# These are synthetic internal pipeline proofs, not production access grants.


ENTRY = """---
type: fact
tags: [telegram]
created: 2026-07-20
status: active
---
Artiom confirmed a test fact.

Source: authenticated Telegram event.
"""


class TelegramPipelineTests(unittest.TestCase):
    def setup(self, root: Path):
        memory = root / "memory"
        (memory / "entries").mkdir(parents=True)
        (root / "CONTEXT_PROTOCOL.md").write_text("synthetic protocol")
        (root / "CONTEXT.md").write_text("Standing context.", encoding="utf-8")
        (memory / "MEMORY_PROTOCOL.md").write_text("Memory policy.", encoding="utf-8")
        (memory / "INDEX.md").write_text("# Memory Index\n", encoding="utf-8")
        (memory / "tombstones.v1.json").write_text(
            '{"schema":"giga.memory.legacy-tombstones.v1","append_only":true,"deletion_performed":false,"entries":[]}\n'
        )
        store = TwinStore(root / "private" / "twin.sqlite3")
        event_id, _ = store.record_event(
            idempotency_key="telegram:update:1", kind="telegram.message.received",
            observed_at="2026-07-20T00:00:00Z", source="telegram", actor="operator",
            trust_class="operator_confirmed", sensitivity="sensitive",
            payload={"text": "remember a test fact"},
        )
        return memory, store, event_id

    def test_success_commits_once_and_replay_uses_receipt_without_worker(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory, store, event_id = self.setup(Path(folder).resolve() / "source")
            index_hash = hashlib.sha256((memory / "INDEX.md").read_bytes()).hexdigest()
            calls = 0

            def worker(_: str):
                nonlocal calls
                calls += 1
                return "fake", {
                    "schema_version": 1,
                    "reply": "Filed the test fact.",
                    "operations": [
                        {"operation": "create", "path": "entries/2026-07-20-test-fact.md",
                         "expected_sha256": None, "content": ENTRY},
                        {"operation": "replace", "path": "INDEX.md",
                         "expected_sha256": index_hash,
                         "content": "# Memory Index\n\n- [test fact](entries/2026-07-20-test-fact.md) — fact\n"},
                    ],
                }

            first = process_event(
                store=store, memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph, event_id=event_id,
                text="remember a test fact", worker=worker,
            )
            replay = process_event(
                store=store, memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph, event_id=event_id,
                text="remember a test fact", worker=worker,
            )
            self.assertTrue(first.success)
            self.assertTrue(replay.replayed)
            self.assertEqual(calls, 1)
            self.assertEqual(store.counts()["processing_attempts"], 1)

    def test_worker_or_validation_failure_remains_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory, store, event_id = self.setup(Path(folder).resolve() / "source")
            failed = process_event(
                store=store, memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph, event_id=event_id,
                text="remember", worker=lambda _: None,
            )
            self.assertFalse(failed.success)
            recovered = process_event(
                store=store, memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph, event_id=event_id, text="answer only",
                worker=lambda _: ("fake", {
                    "schema_version": 1, "reply": "Nothing durable to file.", "operations": [],
                }),
            )
            self.assertTrue(recovered.success)
            self.assertEqual(recovered.attempt_no, 2)
            self.assertEqual(store.counts()["processing_attempts"], 2)


def _synthetic_graph(root, generated):
    (generated / "graph.json").write_text(json.dumps({"nodes": [{"id": "synthetic-code"}], "links": []}))
