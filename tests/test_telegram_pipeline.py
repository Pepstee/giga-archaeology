from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from twin_core.store import TwinStore
from twin_core.telegram_pipeline import (
    _process_event as process_event, _compare_shadow_execution as compare_shadow_execution,
    ShadowComparisonError,
)
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
    def test_public_shadow_comparison_refuses_before_reading_store(self) -> None:
        from twin_core.telegram_pipeline import compare_shadow_execution as public_compare
        from twin_core.constitutional_authority import AuthorityRefused
        with self.assertRaises(AuthorityRefused):
            public_compare(None, "synthetic-event")

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

    def test_observe_only_route_is_receipted_but_does_not_govern_provider(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory, store, event_id = self.setup(Path(folder).resolve() / "source")
            worker_calls = 0
            route_calls = 0

            def observer(_: str):
                nonlocal route_calls
                route_calls += 1
                return {
                    "mode": "observe-only",
                    "decision": "refuse",
                    "reason_codes": ["CALLER_NOT_APPROVED"],
                    "execution_authorized": False,
                    "authority_granted": False,
                    "command_execution": False,
                }

            def worker(_: str):
                nonlocal worker_calls
                worker_calls += 1
                return "fake", {
                    "schema_version": 1,
                    "reply": "No durable change.",
                    "operations": [],
                }

            first = process_event(
                store=store,
                memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph,
                event_id=event_id,
                text="answer only",
                worker=worker,
                route_observer=observer,
            )
            replay = process_event(
                store=store,
                memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph,
                event_id=event_id,
                text="answer only",
                worker=worker,
                route_observer=observer,
            )
            self.assertTrue(first.success)
            self.assertTrue(replay.replayed)
            self.assertEqual(worker_calls, 1)
            self.assertEqual(route_calls, 1)
            receipt = store.latest_receipt(
                event_id, "telegram.memory.proposal.route.shadow"
            )
            self.assertIsNotNone(receipt)
            details = receipt["details"]
            self.assertEqual(details["mode"], "observe-only")
            self.assertIs(details["provider_execution_governed"], False)
            self.assertEqual(details["shadow_decision"]["decision"], "refuse")
            comparison = compare_shadow_execution(store, event_id)
            self.assertEqual(comparison["status"], "complete")
            self.assertEqual(comparison["alignment"], "mismatch")
            self.assertIn(
                "SHADOW_REFUSAL_LEGACY_BOUNDARY_REACHED",
                comparison["reason_codes"],
            )
            self.assertFalse(comparison["provider_execution_governed"])
            self.assertFalse(comparison["enforcement_ready"])

    def test_shadow_route_operation_cannot_collide_with_commit_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory, store, event_id = self.setup(Path(folder).resolve() / "source")
            calls = 0

            def worker(_: str):
                nonlocal calls
                calls += 1
                return None

            with self.assertRaisesRegex(ValueError, "non-empty and distinct"):
                process_event(
                    store=store,
                    memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph,
                    event_id=event_id,
                    text="answer",
                    worker=worker,
                    route_observer=lambda _: {},
                    route_operation="telegram.memory.commit",
                )
            self.assertEqual(calls, 0)
            self.assertEqual(store.counts()["processing_attempts"], 0)

    def test_shadow_comparison_matches_success_and_replays_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory, store, event_id = self.setup(Path(folder).resolve() / "source")

            def observer(_: str):
                return {
                    "mode": "observe-only",
                    "decision": "proposal-only",
                    "reason_codes": [],
                    "execution_authorized": False,
                    "authority_granted": False,
                    "command_execution": False,
                }

            def worker(_: str):
                boundary = store.latest_receipt(
                    event_id, "telegram.memory.proposal.provider.boundary"
                )
                self.assertIsNotNone(boundary)
                return "fake", {
                    "schema_version": 1,
                    "reply": "No durable change.",
                    "operations": [],
                }

            process_event(
                store=store, memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph, event_id=event_id,
                text="answer only", worker=worker, route_observer=observer,
            )
            first = compare_shadow_execution(store, event_id)
            second = compare_shadow_execution(store, event_id)
            self.assertEqual(first, second)
            self.assertEqual(first["alignment"], "match")
            self.assertEqual(first["reason_codes"], [])
            self.assertEqual(first["completion"]["status"], "committed")
            self.assertEqual(first["provider_boundary"]["attempt_no"], 1)

    def test_missing_telemetry_is_incomplete_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            _, store, event_id = self.setup(Path(folder).resolve() / "source")
            comparison = compare_shadow_execution(store, event_id)
            self.assertEqual(comparison["status"], "incomplete")
            self.assertEqual(comparison["alignment"], "incomplete")
            self.assertEqual(
                comparison["reason_codes"],
                [
                    "COMPLETION_RECEIPT_MISSING",
                    "PROVIDER_BOUNDARY_RECEIPT_MISSING",
                    "SHADOW_RECEIPT_MISSING",
                ],
            )
            self.assertFalse(comparison["enforcement_ready"])

    def test_failed_provider_attempt_is_compared_without_false_success(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory, store, event_id = self.setup(Path(folder).resolve() / "source")
            outcome = process_event(
                store=store, memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph, event_id=event_id,
                text="answer only", worker=lambda _: None,
                route_observer=lambda _: {
                    "mode": "observe-only",
                    "decision": "proposal-only",
                    "reason_codes": [],
                    "execution_authorized": False,
                    "authority_granted": False,
                    "command_execution": False,
                },
            )
            self.assertFalse(outcome.success)
            comparison = compare_shadow_execution(store, event_id)
            self.assertEqual(comparison["status"], "complete")
            self.assertEqual(comparison["alignment"], "match")
            self.assertIn(
                "LEGACY_COMPLETION_NOT_COMMITTED", comparison["reason_codes"]
            )
            self.assertEqual(comparison["completion"]["status"], "failed")

    def test_comparison_rejects_boundary_bound_to_another_decision(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory, store, event_id = self.setup(Path(folder).resolve() / "source")
            process_event(
                store=store, memory_root=memory, private_output=memory.parent.parent / "projection", graphify_runner=_synthetic_graph, event_id=event_id,
                text="answer only",
                worker=lambda _: ("fake", {
                    "schema_version": 1, "reply": "No change.", "operations": [],
                }),
                route_observer=lambda _: {
                    "mode": "observe-only", "decision": "proposal-only",
                    "reason_codes": [], "execution_authorized": False,
                    "authority_granted": False, "command_execution": False,
                },
            )
            store.record_receipt(
                event_id=event_id,
                operation="telegram.memory.proposal.provider.boundary",
                status="committed",
                details={
                    "attempt_no": 1,
                    "mode": "observe-only",
                    "provider_boundary_reached": True,
                    "provider_execution_governed": False,
                    "shadow_decision_sha256": "0" * 64,
                },
            )
            with self.assertRaises(ShadowComparisonError) as raised:
                compare_shadow_execution(store, event_id)
            self.assertEqual(
                raised.exception.reason, "COMPARISON_SHADOW_BINDING_MISMATCH"
            )

    def test_comparison_rejects_receipt_race(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            _, store, event_id = self.setup(Path(folder).resolve() / "source")
            with (
                patch.object(
                    store,
                    "latest_receipt",
                    side_effect=[None, None, {"id": "late"}, None],
                ),
                patch.object(
                    store, "latest_operation_receipt", side_effect=[None, None]
                ),
            ):
                with self.assertRaises(ShadowComparisonError) as raised:
                    compare_shadow_execution(store, event_id)
            self.assertEqual(
                raised.exception.reason, "COMPARISON_TELEMETRY_RACE"
            )


def _synthetic_graph(root, generated):
    (generated / "graph.json").write_text(json.dumps({"nodes": [{"id": "synthetic-code"}], "links": []}))
