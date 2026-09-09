from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from twin_core.operator_status import (
    OperatorStatusError,
    SECTION_NAMES,
    STATES,
    canonical_json,
    compile_status,
    render_summary,
    validate_status,
)
from twin_core.adapter_evidence import canonical_json as adapter_json
from twin_core.adapter_evidence import compile_registry as compile_adapter_registry


FIXED_TIME = "2026-07-22T16:00:00+00:00"


class OperatorStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "skilltree").mkdir()
        (self.root / "ecc-integration").mkdir()
        (self.root / "skilltree/implementation-registry.json").write_text(json.dumps({
            "jobs": [
                {"job": "Monitoring & Alerting", "status": "partial"},
                {"job": "Agent Evaluation", "status": "implemented"},
            ],
            "jobs_total": 2,
            "counts": {"partial": 1, "implemented": 1},
        }))
        (self.root / "ecc-integration/UPSTREAM.json").write_text(json.dumps({
            "schema": "giga.ecc-upstream.v1", "commit": "abc123"
        }))
        (self.root / "ecc-integration/IMPORT_LEDGER.json").write_text(json.dumps({
            "schema": "giga.ecc-import-ledger.v1", "deployed": False,
            "entries": [{"decision": "staged"}]
        }))
        (self.root / "00_MASTER.md").write_text(
            "| # | Session | Deliverables | Status | Session log |\n"
            "|---|---|---|---|---|\n"
            "| 01 | First | x | DONE (today) | log |\n"
            "| 02 | Second | y | IN PROGRESS | log |\n"
        )
        (self.root / "adapters/manifests").mkdir(parents=True)
        (self.root / "adapter.py").write_text("# adapter\n")
        (self.root / "adapter.md").write_text("adapter\n")
        (self.root / "adapter-proof.json").write_text("{}\n")
        (self.root / "adapters/manifests/test.json").write_text(json.dumps({
            "schema_version": "giga.adapter-evidence.v1",
            "id": "test-adapter",
            "state": "native",
            "authority": "read-only",
            "supported_assets": ["adapter.py"],
            "unsupported_surfaces": [],
            "onramp": "python3 adapter.py",
            "verification_commands": ["python3 -m pytest"],
            "risk_notes": ["test fixture"],
            "owner": "giga-user",
            "source_docs": ["adapter.md"],
            "evidence_paths": ["adapter-proof.json"],
            "verified_at": FIXED_TIME,
        }))
        (self.root / "outputs/adapter-evidence").mkdir(parents=True)
        adapter_registry = compile_adapter_registry(self.root, FIXED_TIME)
        (self.root / "outputs/adapter-evidence/registry.json").write_text(adapter_json(adapter_registry))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_fixed_clock_is_byte_deterministic(self) -> None:
        first = canonical_json(compile_status(self.root, FIXED_TIME))
        second = canonical_json(compile_status(self.root, FIXED_TIME))
        self.assertEqual(first, second)

    def test_canonical_json_round_trips_through_strict_validation(self) -> None:
        serialized = canonical_json(compile_status(self.root, FIXED_TIME))
        restored = json.loads(serialized)
        validate_status(restored)
        self.assertEqual(tuple(restored["sections"]), SECTION_NAMES)

    def test_published_schema_matches_compiler_contract(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "contracts/operator-status.v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "giga.operator-status.v1")
        self.assertEqual(schema["properties"]["authority"]["const"], "read-only-status")
        self.assertEqual(tuple(schema["properties"]["sections"]["required"]), SECTION_NAMES)
        self.assertEqual(tuple(schema["$defs"]["state"]["enum"]), STATES)
        self.assertEqual(set(schema["properties"]["summary"]["properties"]["state_counts"]["required"]), set(STATES))

    def test_missing_runtime_evidence_is_unknown_not_green(self) -> None:
        payload = compile_status(self.root, FIXED_TIME)
        for name in ("toolCalls", "activeAgents", "cost", "queueState"):
            self.assertEqual(payload["sections"][name]["state"], "unknown")
            self.assertIsNone(payload["sections"][name]["value"])
        self.assertEqual(tuple(payload["sections"]), SECTION_NAMES)

    def test_malformed_required_evidence_fails_closed(self) -> None:
        (self.root / "skilltree/implementation-registry.json").write_text("{")
        with self.assertRaisesRegex(OperatorStatusError, "malformed evidence"):
            compile_status(self.root, FIXED_TIME)

    def test_changed_adapter_evidence_fails_closed(self) -> None:
        (self.root / "adapter-proof.json").write_text('{"changed":true}\n')
        with self.assertRaisesRegex(OperatorStatusError, "adapter evidence changed"):
            compile_status(self.root, FIXED_TIME)

    def test_future_and_stale_adapter_registry_are_explicit(self) -> None:
        path = self.root / "outputs/adapter-evidence/registry.json"
        registry = json.loads(path.read_text())
        registry["observed_at"] = "2026-07-23T16:00:00+00:00"
        path.write_text(json.dumps(registry))
        with self.assertRaisesRegex(OperatorStatusError, "dated after"):
            compile_status(self.root, FIXED_TIME)
        registry["observed_at"] = "2026-07-20T16:00:00+00:00"
        path.write_text(json.dumps(registry))
        payload = compile_status(self.root, FIXED_TIME, stale_after_seconds=60)
        self.assertEqual(payload["sections"]["checks"]["value"]["adapters"]["registry_state"], "stale")
        self.assertEqual(payload["sections"]["risk"]["state"], "degraded")

    def test_missing_required_evidence_fails_closed(self) -> None:
        (self.root / "ecc-integration/UPSTREAM.json").unlink()
        with self.assertRaisesRegex(OperatorStatusError, "required evidence is missing"):
            compile_status(self.root, FIXED_TIME)

    def test_path_escape_and_absolute_input_fail_closed(self) -> None:
        with self.assertRaisesRegex(OperatorStatusError, "escapes repository"):
            compile_status(self.root, FIXED_TIME, registry_path="../outside.json")
        with self.assertRaisesRegex(OperatorStatusError, "absolute paths"):
            compile_status(self.root, FIXED_TIME, registry_path="/tmp/outside.json")

    def test_stale_runtime_evidence_is_never_green(self) -> None:
        packet = {
            "schema": "giga.operator-status-evidence.v1",
            "observed_at": "2026-07-20T16:00:00+00:00",
            "signals": {"cost": {"value": {"tokens": 10}, "state": "healthy"}},
        }
        (self.root / "runtime.json").write_text(json.dumps(packet))
        payload = compile_status(self.root, FIXED_TIME, runtime_evidence="runtime.json", stale_after_seconds=60)
        self.assertEqual(payload["sections"]["cost"]["state"], "stale")

    def test_future_runtime_evidence_fails_closed(self) -> None:
        packet = {
            "schema": "giga.operator-status-evidence.v1",
            "observed_at": "2026-07-23T16:00:00+00:00",
            "signals": {"cost": {"value": {"tokens": 10}, "state": "observed"}},
        }
        (self.root / "runtime.json").write_text(json.dumps(packet))
        with self.assertRaisesRegex(OperatorStatusError, "dated after"):
            compile_status(self.root, FIXED_TIME, runtime_evidence="runtime.json")

    def test_unknown_runtime_signal_and_empty_green_signal_fail_closed(self) -> None:
        for signals, message in (
            ({"secrets": {"value": 1, "state": "observed"}}, "unsupported runtime signals"),
            ({"cost": {"value": None, "state": "healthy"}}, "empty runtime signal"),
        ):
            packet = {"schema": "giga.operator-status-evidence.v1", "observed_at": FIXED_TIME, "signals": signals}
            (self.root / "runtime.json").write_text(json.dumps(packet))
            with self.assertRaisesRegex(OperatorStatusError, message):
                compile_status(self.root, FIXED_TIME, runtime_evidence="runtime.json")

    def test_summary_and_machine_states_agree(self) -> None:
        payload = compile_status(self.root, FIXED_TIME)
        summary = render_summary(payload)
        for name, section in payload["sections"].items():
            self.assertIn(f"- {name}: {section['state']}", summary)
        validate_status(payload)

    def test_validator_rejects_mutation_claim_and_summary_tamper(self) -> None:
        payload = compile_status(self.root, FIXED_TIME)
        payload["sections"]["sessionControls"]["value"]["mutation_performed"] = True
        with self.assertRaisesRegex(OperatorStatusError, "must not perform mutations"):
            validate_status(payload)
        payload = compile_status(self.root, FIXED_TIME)
        payload["summary"]["overall_state"] = "healthy"
        with self.assertRaisesRegex(OperatorStatusError, "summary disagrees"):
            validate_status(payload)


if __name__ == "__main__":
    unittest.main()
