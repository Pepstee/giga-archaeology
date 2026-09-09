from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from twin_core.execution_policy import (
    LIVE_SHADOW_REQUIRED_GRANT_FIELDS,
    LIVE_SHADOW_REQUIRED_RECEIPTS,
    LIVE_SHADOW_STOP_CONDITIONS,
    LIVE_SHADOW_TELEMETRY_FIELDS,
    REQUEST_SCHEMA,
    ExecutionPolicyError,
    decide_route,
    load_registry,
)


def _record(path: Path, root: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def _live_shadow_policy() -> dict[str, object]:
    return {
        "schema_version": "giga.live-shadow-policy.v1",
        "status": "operator-grant-required",
        "sample_size_max": 20,
        "provider_attempts_max": 20,
        "provider_cost_usd_max": 1.0,
        "provider_tokens_max": 81920,
        "max_samples_per_minute": 2,
        "collection_window_seconds_max": 3600,
        "grant_validity_seconds_max": 86400,
        "retention_seconds_max": 86400,
        "target_binding": "operator-issued-opaque-target-selector-sha256",
        "sampling_rule": "first-eligible-operator-events-no-synthetic-provider-calls",
        "data_scope": "existing-receipt-metadata-and-hashes-only",
        "storage_boundary": "local-twinstore-receipts-only",
        "telemetry_field_allowlist": LIVE_SHADOW_TELEMETRY_FIELDS,
        "required_grant_fields": LIVE_SHADOW_REQUIRED_GRANT_FIELDS,
        "required_receipts": LIVE_SHADOW_REQUIRED_RECEIPTS,
        "stop_conditions": LIVE_SHADOW_STOP_CONDITIONS,
        "telemetry_collection_authorized": False,
        "raw_message_capture_authorized": False,
        "secret_material_capture_authorized": False,
        "external_export_authorized": False,
        "new_provider_execution_authorized": False,
        "enforcement_promotion_authorized": False,
    }


class ExecutionPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "execution").mkdir()
        evidence = self.root / "handler.py"
        evidence.write_text("# deterministic evidence\n", encoding="utf-8")
        self.registry_path = self.root / "execution/capabilities.v1.json"
        self.registry = {
            "schema_version": "giga.execution-capability-registry.v1",
            "registry_version": 1,
            "mode": "observe-only",
            "authority": "routing-evidence-only",
            "authority_granted": False,
            "command_execution": False,
            "capabilities": [
                {
                    "capability_id": "telegram-memory-proposal",
                    "operation_id": "telegram.memory.proposal",
                    "approved_callers": ["scripts.jarvis_telegram:_process_update"],
                    "route": "proposal-only",
                    "maximum_authority": "A0",
                    "target": "memory-proposal",
                    "max_cost_usd": 1.0,
                    "max_tokens": 4096,
                    "timeout_seconds": 180,
                    "reversibility": "not-applicable-proposal-only",
                    "expected_receipt_type": "telegram.memory.commit",
                    "proposal_contract": "twin.memory-proposal.v1",
                    "live_shadow_policy": _live_shadow_policy(),
                    "evidence": [_record(evidence, self.root)],
                }
            ],
        }
        self._write_registry()
        self.request = {
            "schema_version": REQUEST_SCHEMA,
            "registry_version": 1,
            "capability_id": "telegram-memory-proposal",
            "operation_id": "telegram.memory.proposal",
            "caller_id": "scripts.jarvis_telegram:_process_update",
            "idempotency_key": "event-1",
            "input_sha256": hashlib.sha256(b"prompt").hexdigest(),
            "requested_authority": "A0",
            "target": "memory-proposal",
            "max_cost_usd": 1.0,
            "max_tokens": 4096,
            "timeout_seconds": 180,
            "reversibility": "not-applicable-proposal-only",
            "expected_receipt_type": "telegram.memory.commit",
        }

    def _write_registry(self) -> None:
        self.registry_path.write_text(
            json.dumps(self.registry, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_matching_route_is_deterministic_but_never_authorises_execution(
        self,
    ) -> None:
        first = decide_route(self.root, self.request)
        second = decide_route(self.root, self.request)
        self.assertEqual(first, second)
        self.assertEqual(first["decision"], "proposal-only")
        self.assertEqual(first["reason_codes"], [])
        self.assertIs(first["execution_authorized"], False)
        self.assertIs(first["authority_granted"], False)
        self.assertIs(first["command_execution"], False)

    def test_unknown_or_out_of_bounds_request_refuses_with_stable_reasons(self) -> None:
        unknown = dict(self.request, capability_id="unknown")
        self.assertEqual(
            decide_route(self.root, unknown)["reason_codes"], ["CAPABILITY_UNKNOWN"]
        )
        rejected = dict(
            self.request,
            caller_id="scripts.unregistered:main",
            max_cost_usd=2.0,
            max_tokens=5000,
            timeout_seconds=181,
        )
        decision = decide_route(self.root, rejected)
        self.assertEqual(decision["decision"], "refuse")
        self.assertEqual(
            decision["reason_codes"],
            [
                "CALLER_NOT_APPROVED",
                "COST_LIMIT_EXCEEDED",
                "TIMEOUT_LIMIT_EXCEEDED",
                "TOKEN_LIMIT_EXCEEDED",
            ],
        )

    def test_request_and_registry_shapes_fail_closed(self) -> None:
        with self.assertRaises(ExecutionPolicyError) as extra:
            decide_route(self.root, dict(self.request, unexpected=True))
        self.assertEqual(extra.exception.reason, "POLICY_REQUEST_INVALID")

        self.registry["authority_granted"] = True
        self._write_registry()
        with self.assertRaises(ExecutionPolicyError) as identity:
            decide_route(self.root, self.request)
        self.assertEqual(identity.exception.reason, "POLICY_REGISTRY_IDENTITY")

    def test_live_shadow_policy_is_closed_and_never_pre_authorizes(self) -> None:
        registry, _ = load_registry(self.root)
        policy = registry["capabilities"][0]["live_shadow_policy"]
        self.assertEqual(policy["status"], "operator-grant-required")
        self.assertIs(policy["telemetry_collection_authorized"], False)
        self.assertIs(policy["raw_message_capture_authorized"], False)
        self.assertIs(policy["secret_material_capture_authorized"], False)
        self.assertIs(policy["external_export_authorized"], False)
        self.assertIs(policy["new_provider_execution_authorized"], False)
        self.assertIs(policy["enforcement_promotion_authorized"], False)

        policy["telemetry_collection_authorized"] = True
        self.registry["capabilities"][0]["live_shadow_policy"] = policy
        self._write_registry()
        with self.assertRaises(ExecutionPolicyError) as raised:
            load_registry(self.root)
        self.assertEqual(raised.exception.reason, "POLICY_REGISTRY_INVALID")

    def test_live_shadow_policy_rejects_widened_or_underspecified_bounds(self) -> None:
        policy = self.registry["capabilities"][0]["live_shadow_policy"]
        policy["sample_size_max"] = 1_000_000
        policy["provider_attempts_max"] = 1_000_000
        policy["collection_window_seconds_max"] = 31_536_000
        policy["grant_validity_seconds_max"] = 31_536_000
        self._write_registry()
        with self.assertRaises(ExecutionPolicyError) as widened:
            load_registry(self.root)
        self.assertEqual(widened.exception.reason, "POLICY_REGISTRY_INVALID")

        for field, value in (
            ("provider_cost_usd_max", True),
            ("sample_size_max", 20.0),
            ("collection_window_seconds_max", 3600.0),
        ):
            policy = _live_shadow_policy()
            policy[field] = value
            self.registry["capabilities"][0]["live_shadow_policy"] = policy
            self._write_registry()
            with self.assertRaises(ExecutionPolicyError) as type_drift:
                load_registry(self.root)
            self.assertEqual(type_drift.exception.reason, "POLICY_REGISTRY_INVALID")

        policy = _live_shadow_policy()
        policy["required_receipts"] = policy["required_receipts"][:-1]
        self.registry["capabilities"][0]["live_shadow_policy"] = policy
        self._write_registry()
        with self.assertRaises(ExecutionPolicyError) as receipts:
            load_registry(self.root)
        self.assertEqual(receipts.exception.reason, "POLICY_REGISTRY_INVALID")

    def test_nonfinite_request_and_duplicate_registry_keys_fail_closed(self) -> None:
        with self.assertRaises(ExecutionPolicyError) as nonfinite:
            decide_route(self.root, dict(self.request, max_cost_usd=float("nan")))
        self.assertEqual(nonfinite.exception.reason, "POLICY_REQUEST_INVALID")
        with self.assertRaises(ExecutionPolicyError) as huge:
            decide_route(self.root, dict(self.request, max_cost_usd=10**10_000))
        self.assertEqual(huge.exception.reason, "POLICY_REQUEST_INVALID")

        raw = self.registry_path.read_text(encoding="utf-8")
        self.registry_path.write_text(
            raw.replace(
                '"registry_version": 1,',
                '"registry_version": 1,\n  "registry_version": 1,',
            ),
            encoding="utf-8",
        )
        with self.assertRaises(ExecutionPolicyError) as duplicate:
            decide_route(self.root, self.request)
        self.assertEqual(duplicate.exception.reason, "POLICY_REGISTRY_INVALID")

    def test_evidence_drift_and_symlink_fail_closed(self) -> None:
        (self.root / "handler.py").write_text("# drift\n", encoding="utf-8")
        with self.assertRaises(ExecutionPolicyError) as drift:
            decide_route(self.root, self.request)
        self.assertEqual(drift.exception.reason, "POLICY_EVIDENCE_DRIFT")

        target = self.root / "real-handler.py"
        target.write_text("# deterministic evidence\n", encoding="utf-8")
        (self.root / "handler.py").unlink()
        (self.root / "handler.py").symlink_to(target)
        with self.assertRaises(ExecutionPolicyError) as symlink:
            decide_route(self.root, self.request)
        self.assertEqual(symlink.exception.reason, "POLICY_PATH_SYMLINK")

    def test_registry_path_escape_and_symlink_fail_closed(self) -> None:
        with self.assertRaises(ExecutionPolicyError) as escape:
            decide_route(self.root, self.request, registry_path="../registry.json")
        self.assertEqual(escape.exception.reason, "POLICY_PATH_ESCAPE")
        with self.assertRaises(ExecutionPolicyError) as noncanonical:
            decide_route(
                self.root,
                self.request,
                registry_path="execution/../execution/capabilities.v1.json",
            )
        self.assertEqual(noncanonical.exception.reason, "POLICY_PATH_INVALID")

        link = self.root / "execution/link.json"
        link.symlink_to(self.registry_path)
        with self.assertRaises(ExecutionPolicyError) as symlink:
            decide_route(self.root, self.request, registry_path="execution/link.json")
        self.assertEqual(symlink.exception.reason, "POLICY_PATH_SYMLINK")


    def test_generated_registry_replays_byte_identically_without_authority(self) -> None:
        root = self.root
        request = dict(self.request, idempotency_key="fixture-event")
        first = decide_route(root, request)
        second = decide_route(root, request)
        self.assertEqual(first, second)
        self.assertEqual(first["decision"], "proposal-only")
        self.assertIs(first["execution_authorized"], False)
        policy = load_registry(root)[0]["capabilities"][0]["live_shadow_policy"]
        self.assertEqual(policy["sample_size_max"], 20)
        self.assertEqual(policy["max_samples_per_minute"], 2)
        self.assertEqual(
            policy["data_scope"], "existing-receipt-metadata-and-hashes-only"
        )
        self.assertIs(policy["telemetry_collection_authorized"], False)


if __name__ == "__main__":
    unittest.main()
