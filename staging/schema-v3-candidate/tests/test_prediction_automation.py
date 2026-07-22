from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.prediction_automation import (
    OPERATOR_TZ,
    AutomationStore,
    load_recent_evidence,
    run_cycle,
)


def _record(timestamp: datetime, text: str) -> dict[str, str]:
    return {
        "ts": timestamp.isoformat().replace("+00:00", "Z"),
        "text": text,
        "source": "codex-desktop:test",
        "session": "test-session",
        "channel": "codex-desktop",
    }


def _write_snapshot(path: Path, records: list[dict[str, str]]) -> None:
    path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")


def _target(now: datetime, days: int) -> str:
    return str(now.astimezone(OPERATOR_TZ).date() + timedelta(days=days))


class PredictionAutomationTests(unittest.TestCase):
    def test_forecast_is_generated_then_resolved_only_by_later_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "prompts.jsonl"
            database = root / "predictions.sqlite3"
            now = datetime.now(timezone.utc).replace(microsecond=0)
            first = _record(now - timedelta(minutes=5), "I am beginning the SQLite project.")
            _write_snapshot(snapshot, [first])
            basis = load_recent_evidence(snapshot, now=now)[0].fingerprint

            def first_worker(prompt: str):
                self.assertIn("forecasting worker", prompt)
                return "GPT", json.dumps({
                    "predictions": [{
                        "event_key": "sqlite-project-follow-up",
                        "question": "Will Artiom mention the SQLite project again in captured AI prompts?",
                        "confidence": 75,
                        "target_date": _target(now, 3),
                        "domain": "projects",
                        "scope": "captured_ai_prompts",
                        "observable_rule": "Yes if a later captured prompt explicitly mentions SQLite.",
                        "match_terms": ["sqlite"],
                        "rationale": "He has just started discussing it.",
                        "basis_fingerprints": [basis],
                    }]
                })

            first_result = run_cycle(snapshot, first_worker, database=database, now=now)
            self.assertEqual(first_result["generated"], 1)
            self.assertEqual(first_result["resolved"], 0)

            later = _record(now + timedelta(days=1), "Continue with the SQLite project.")
            _write_snapshot(snapshot, [first, later])
            later_fingerprint = load_recent_evidence(
                snapshot, now=now + timedelta(days=2)
            )[-1].fingerprint

            def second_worker(prompt: str):
                if "blind adjudicator" in prompt:
                    store = AutomationStore(database)
                    prediction_id = store.open_predictions()[0]["id"]
                    return "Claude", json.dumps({
                        "decisions": [{
                            "prediction_id": prediction_id,
                            "outcome": "yes",
                            "resolution_confidence": 99,
                            "evidence_fingerprints": [later_fingerprint],
                            "coverage_complete": False,
                            "rationale": "A later prompt explicitly mentions SQLite.",
                        }]
                    })
                return "Claude", '{"predictions":[]}'

            second_result = run_cycle(
                snapshot, second_worker, database=database, now=now + timedelta(days=2)
            )
            self.assertEqual(second_result["resolved"], 1)
            self.assertEqual(second_result["statistics"]["resolved_count"], 1)
            self.assertEqual(second_result["statistics"]["mean_brier_score"], 0.0625)

    def test_model_cannot_resolve_with_pre_forecast_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "prompts.jsonl"
            database = root / "predictions.sqlite3"
            now = datetime.now(timezone.utc).replace(microsecond=0)
            old = _record(now - timedelta(hours=1), "Old evidence mentions travel.")
            _write_snapshot(snapshot, [old])
            old_fingerprint = load_recent_evidence(snapshot, now=now)[0].fingerprint
            store = AutomationStore(database)
            store.ingest_evidence(load_recent_evidence(snapshot, now=now), now)
            prediction_id = store.add_candidate({
                "event_key": "travel-again",
                "question": "Will Artiom mention travel again in captured AI prompts?",
                "confidence": 60,
                "target_date": _target(now, 2),
                "domain": "travel",
                "scope": "captured_ai_prompts",
                "observable_rule": "A later captured prompt contains a travel discussion.",
                "match_terms": ["travel"],
                "rationale": "Travel is recurrent.",
                "basis_fingerprints": [old_fingerprint],
            }, "GPT", now)
            self.assertIsNotNone(prediction_id)
            accepted = store.adjudicate({
                "prediction_id": prediction_id,
                "outcome": "yes",
                "resolution_confidence": 99,
                "evidence_fingerprints": [old_fingerprint],
                "coverage_complete": False,
                "rationale": "Uses old evidence and must be rejected.",
            }, "GPT", now)
            self.assertFalse(accepted)
            self.assertEqual(len(store.open_predictions()), 1)

    def test_expired_digital_forecast_gets_exhaustive_negative_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "prompts.jsonl"
            database = root / "predictions.sqlite3"
            now = datetime.now(timezone.utc).replace(microsecond=0)
            old = _record(now - timedelta(minutes=2), "We are discussing databases.")
            _write_snapshot(snapshot, [old])
            evidence = load_recent_evidence(snapshot, now=now)
            store = AutomationStore(database)
            store.ingest_evidence(evidence, now)
            prediction_id = store.add_candidate({
                "event_key": "mentions-volcano",
                "question": "Will a captured AI prompt literally mention volcano?",
                "confidence": 20,
                "target_date": _target(now, 1),
                "domain": "topic",
                "scope": "captured_ai_prompts",
                "observable_rule": "Yes iff a later captured prompt contains volcano.",
                "match_terms": ["volcano"],
                "rationale": "A deliberately unlikely test event.",
                "basis_fingerprints": [evidence[0].fingerprint],
            }, "GPT", now)
            self.assertIsNotNone(prediction_id)
            self.assertEqual(
                store.resolve_observable_predictions(now + timedelta(days=3)), 1
            )
            self.assertEqual(store.repository.fetch(prediction_id).resolution, "no")

    def test_cycle_is_idempotent_and_rejects_unknown_basis(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "prompts.jsonl"
            database = root / "predictions.sqlite3"
            now = datetime.now(timezone.utc).replace(microsecond=0)
            _write_snapshot(snapshot, [_record(now - timedelta(minutes=1), "One current prompt")])

            calls = 0
            def worker(_prompt: str):
                nonlocal calls
                calls += 1
                return "GPT", json.dumps({"predictions": [{
                    "event_key": "fabricated-basis",
                    "question": "Will this invalid candidate be accepted?",
                    "confidence": 50,
                    "target_date": _target(now, 1),
                    "domain": "test",
                    "scope": "captured_ai_prompts",
                    "observable_rule": "An exact later message appears.",
                    "match_terms": ["exact later message"],
                    "rationale": "Test",
                    "basis_fingerprints": ["not-in-evidence"],
                }]})

            first = run_cycle(snapshot, worker, database=database, now=now)
            second = run_cycle(snapshot, worker, database=database, now=now + timedelta(minutes=1))
            self.assertEqual(first["generated"], 0)
            self.assertEqual(second["evidence_added"], 0)
            self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
