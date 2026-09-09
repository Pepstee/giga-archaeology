from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from twin_core import operator_status as operator_status_module
from twin_core.operator_status import (
    ADMISSION_ONRAMP,
    ADMITTED_ADAPTER_ID,
    AdapterAdmissionError,
    OperatorStatusError,
    SECTION_NAMES,
    STATES,
    admit_no_write_adapter,
    canonical_json,
    compile_status,
    render_summary,
    validate_status,
)
from twin_core.adapter_evidence import canonical_json as adapter_json
from twin_core.adapter_evidence import compile_registry as compile_adapter_registry


FIXED_TIME = "2026-07-22T16:00:00+00:00"

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "scripts/operator_status.py"

_scripts_spec = importlib.util.spec_from_file_location("scripts_operator_status", CLI)
scripts_operator_status = importlib.util.module_from_spec(_scripts_spec)
_scripts_spec.loader.exec_module(scripts_operator_status)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def build_admission_root(
    *,
    adapter_id: str = ADMITTED_ADAPTER_ID,
    onramp: str = ADMISSION_ONRAMP,
    authority: str = "read-only",
    state: str = "native",
    verified_at: str = FIXED_TIME,
    verification_commands: list[str] | None = None,
) -> tuple[tempfile.TemporaryDirectory, Path]:
    """Complete minimal root whose compiled registry carries one admission candidate."""
    holder = tempfile.TemporaryDirectory()
    root = Path(holder.name)
    (root / "adapters/manifests").mkdir(parents=True)
    (root / "outputs/adapter-evidence").mkdir(parents=True)
    (root / "core.py").write_text("# core\n", encoding="utf-8")
    (root / "cli.py").write_text("# cli\n", encoding="utf-8")
    (root / "contract.json").write_text("{}\n", encoding="utf-8")
    (root / "source-doc.md").write_text("source\n", encoding="utf-8")
    (root / "proof.json").write_text("{}\n", encoding="utf-8")
    manifest = {
        "schema_version": "giga.adapter-evidence.v1",
        "id": adapter_id,
        "state": state,
        "authority": authority,
        "supported_assets": ["core.py", "cli.py", "contract.json"],
        "unsupported_surfaces": ["session mutation"],
        "onramp": onramp,
        "verification_commands": verification_commands
        or ["python3 -m pytest -q tests/"],
        "risk_notes": ["fixture adapter"],
        "owner": "giga-user",
        "source_docs": ["source-doc.md"],
        "evidence_paths": ["proof.json"],
        "verified_at": verified_at,
    }
    (root / "adapters/manifests/operator-status-local.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    registry = compile_adapter_registry(root, FIXED_TIME)
    (root / "outputs/adapter-evidence/registry.json").write_text(
        adapter_json(registry), encoding="utf-8"
    )
    return holder, root

def build_status_root(**overrides) -> tuple[tempfile.TemporaryDirectory, Path]:
    """Complete isolated status root for exercising the public CLI."""
    holder, root = build_admission_root(**overrides)
    (root / "skilltree").mkdir()
    (root / "ecc-integration").mkdir()
    (root / "skilltree/implementation-registry.json").write_text(
        json.dumps(
            {
                "jobs": [
                    {"job": "Monitoring & Alerting", "status": "partial"},
                    {"job": "Agent Evaluation", "status": "implemented"},
                ],
                "jobs_total": 2,
                "counts": {"partial": 1, "implemented": 1},
            }
        )
    )
    (root / "ecc-integration/UPSTREAM.json").write_text(
        json.dumps({"schema": "giga.ecc-upstream.v1", "commit": "abc123"})
    )
    (root / "ecc-integration/IMPORT_LEDGER.json").write_text(
        json.dumps(
            {
                "schema": "giga.ecc-import-ledger.v1",
                "deployed": False,
                "entries": [{"decision": "staged"}],
            }
        )
    )
    (root / "00_MASTER.md").write_text(
        "| # | Session | Deliverables | Status | Session log |\n"
        "|---|---|---|---|---|\n"
        "| 01 | First | x | DONE (today) | log |\n"
    )
    return holder, root

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

class NoWriteAdmissionTests(unittest.TestCase):
    """Evidence-backed admission of operator-status-local on the official no-write onramp."""

    def admit(self, **overrides) -> tuple[dict, Path]:
        holder, root = build_admission_root(**overrides)
        self.addCleanup(holder.cleanup)
        return admit_no_write_adapter(root), root

    def status_root(self, **overrides) -> Path:
        """Admission fixture extended with the full status evidence set."""
        holder, root = build_status_root(**overrides)
        self.addCleanup(holder.cleanup)
        return root

    def expect_refusal(self, expected_reason: str, **overrides) -> None:
        with self.assertRaises(AdapterAdmissionError) as raised:
            receipt, _ = self.admit(**overrides)
            self.fail(f"admission unexpectedly succeeded: {receipt}")
        self.assertEqual(raised.exception.reason, expected_reason)

    def test_admission_binds_identity_and_currently_rehashed_files(self) -> None:
        receipt, root = self.admit()
        registry_bytes = (root / "outputs/adapter-evidence/registry.json").read_bytes()
        registry = json.loads(registry_bytes)
        record = next(
            item for item in registry["adapters"] if item["id"] == ADMITTED_ADAPTER_ID
        )
        canonical_record = json.dumps(
            record, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

        self.assertEqual(receipt["adapter_id"], ADMITTED_ADAPTER_ID)
        self.assertEqual(receipt["declared_state"], "native")
        self.assertEqual(receipt["effective_state"], "native")
        self.assertEqual(receipt["verification_state"], "verified")
        self.assertEqual(receipt["authority"], "read-only")
        self.assertEqual(receipt["onramp"], ADMISSION_ONRAMP)
        self.assertEqual(receipt["registry_schema_version"], "giga.adapter-registry.v1")
        self.assertEqual(receipt["registry_authority"], "read-only-evidence")
        self.assertIs(receipt["authority_granted"], False)
        self.assertIs(receipt["command_execution"], False)
        self.assertIs(receipt["commands_executed"], False)
        self.assertEqual(
            receipt["registry_path"], "outputs/adapter-evidence/registry.json"
        )
        self.assertEqual(receipt["registry_sha256"], _sha256_bytes(registry_bytes))
        self.assertEqual(
            receipt["adapter_record_sha256"], _sha256_bytes(canonical_record)
        )
        for field in ("supported_assets", "source_docs", "evidence"):
            self.assertEqual(receipt[field], record[field])

    def test_admission_is_deterministic_and_never_executes_commands(self) -> None:
        marker = "touch ./must-not-exist-from-manifest"
        receipt_one, root_one = self.admit(verification_commands=[marker])
        receipt_two, root_two = self.admit(verification_commands=[marker])
        self.assertEqual(receipt_one, receipt_two)
        self.assertFalse((root_one / "must-not-exist-from-manifest").exists())
        self.assertFalse((root_two / "must-not-exist-from-manifest").exists())

    def test_compile_status_embeds_receipt_and_stays_byte_deterministic(self) -> None:
        root = self.status_root()
        receipt = admit_no_write_adapter(root)

        without = compile_status(root, FIXED_TIME)
        self.assertNotIn("adapter_admission", without["sections"]["checks"]["value"])

        first = canonical_json(compile_status(root, FIXED_TIME, admission=receipt))
        second = canonical_json(compile_status(root, FIXED_TIME, admission=receipt))
        self.assertEqual(first, second)
        embedded = json.loads(first)["sections"]["checks"]["value"]["adapter_admission"]
        self.assertEqual(embedded, receipt)

    def test_forged_or_misused_receipt_fails_closed(self) -> None:
        root = self.status_root()
        receipt = admit_no_write_adapter(root)
        with self.assertRaisesRegex(AdapterAdmissionError, "missing or unexpected"):
            compile_status(root, FIXED_TIME, admission={})
        extra = dict(receipt, unexpected="not-authorised")
        with self.assertRaisesRegex(AdapterAdmissionError, "missing or unexpected"):
            compile_status(root, FIXED_TIME, admission=extra)
        mutated = dict(receipt, commands_executed=True)
        with self.assertRaisesRegex(
            AdapterAdmissionError, "claims a different adapter"
        ):
            compile_status(root, FIXED_TIME, admission=mutated)
        other_adapter = dict(receipt, adapter_id="some-other-adapter")
        with self.assertRaisesRegex(
            AdapterAdmissionError, "claims a different adapter"
        ):
            compile_status(root, FIXED_TIME, admission=other_adapter)
        wrong_onramp = dict(receipt, onramp="python3 evil.py --write-everything")
        with self.assertRaisesRegex(
            AdapterAdmissionError, "claims a different adapter"
        ):
            compile_status(root, FIXED_TIME, admission=wrong_onramp)
        wrong_hash = dict(receipt, registry_sha256="0" * 64)
        with self.assertRaisesRegex(AdapterAdmissionError, "does not match current"):
            compile_status(root, FIXED_TIME, admission=wrong_hash)

    def test_registry_change_between_status_load_and_receipt_binding_fails_closed(
        self,
    ) -> None:
        root = self.status_root()
        receipt = admit_no_write_adapter(root)
        original = operator_status_module._validate_adapters

        def mutate_after_validation(*args, **kwargs):
            result = original(*args, **kwargs)
            registry_path = root / "outputs/adapter-evidence/registry.json"
            registry_path.write_bytes(registry_path.read_bytes() + b"\n")
            return result

        with patch(
            "twin_core.operator_status._validate_adapters",
            side_effect=mutate_after_validation,
        ):
            with self.assertRaisesRegex(
                AdapterAdmissionError, "does not match current"
            ):
                compile_status(root, FIXED_TIME, admission=receipt)

    def test_missing_duplicate_wrong_id_fail_closed(self) -> None:
        self.expect_refusal("adapter-missing", adapter_id="some-other-adapter")

        holder, root = build_admission_root()
        self.addCleanup(holder.cleanup)
        path = root / "outputs/adapter-evidence/registry.json"
        registry = json.loads(path.read_text(encoding="utf-8"))
        registry["adapters"].append(json.loads(json.dumps(registry["adapters"][0])))
        path.write_text(json.dumps(registry), encoding="utf-8")
        with self.assertRaises(AdapterAdmissionError) as raised:
            admit_no_write_adapter(root)
        self.assertEqual(raised.exception.reason, "adapter-duplicate")

    def test_wrong_onramp_and_authority_fail_closed(self) -> None:
        self.expect_refusal(
            "adapter-onramp-mismatch", onramp="python3 scripts/operator_status.py"
        )
        self.expect_refusal("adapter-authority-mismatch", authority="proposal-only")

    def test_stale_manifest_degrades_and_fails_closed(self) -> None:
        self.expect_refusal("adapter-stale", verified_at="2026-06-01T00:00:00+00:00")

    def test_registry_identity_tamper_fails_closed(self) -> None:
        holder, root = build_admission_root()
        self.addCleanup(holder.cleanup)
        path = root / "outputs/adapter-evidence/registry.json"
        registry = json.loads(path.read_text(encoding="utf-8"))
        registry["command_execution"] = True
        path.write_text(json.dumps(registry), encoding="utf-8")
        with self.assertRaises(AdapterAdmissionError) as raised:
            admit_no_write_adapter(root)
        self.assertEqual(raised.exception.reason, "adapter-registry-identity")

    def test_evidence_drift_after_compilation_fails_closed(self) -> None:
        holder, root = build_admission_root()
        self.addCleanup(holder.cleanup)
        (root / "core.py").write_text("# core changed\n", encoding="utf-8")
        with self.assertRaises(AdapterAdmissionError) as raised:
            admit_no_write_adapter(root)
        self.assertEqual(raised.exception.reason, "adapter-evidence-drift")
        self.assertIn("core.py", str(raised.exception))

    def test_non_native_and_symlinked_bound_evidence_fail_closed(self) -> None:
        self.expect_refusal("adapter-state-mismatch", state="adapter-backed")

        holder, root = build_admission_root()
        self.addCleanup(holder.cleanup)
        target = root / "actual-core.py"
        target.write_bytes((root / "core.py").read_bytes())
        (root / "core.py").unlink()
        (root / "core.py").symlink_to(target)
        with self.assertRaises(AdapterAdmissionError) as symlinked:
            admit_no_write_adapter(root)
        self.assertEqual(symlinked.exception.reason, "adapter-evidence-drift")
        self.assertIn("symlink", str(symlinked.exception))

    def test_malformed_record_and_evidence_race_fail_closed(self) -> None:
        holder, root = build_admission_root()
        self.addCleanup(holder.cleanup)
        registry_path = root / "outputs/adapter-evidence/registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["adapters"][0]["supported_assets"][0]["unexpected"] = True
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        with self.assertRaises(AdapterAdmissionError) as malformed:
            admit_no_write_adapter(root)
        self.assertEqual(malformed.exception.reason, "adapter-registry-invalid")

        holder_two, root_two = build_admission_root()
        self.addCleanup(holder_two.cleanup)
        real_records = admit_no_write_adapter(root_two)
        raced_records = {
            field: [dict(record) for record in real_records[field]]
            for field in ("supported_assets", "source_docs", "evidence")
        }
        raced_records["supported_assets"][0]["sha256"] = "0" * 64
        with patch(
            "twin_core.operator_status.current_adapter_file_records",
            return_value=raced_records,
        ):
            with self.assertRaises(AdapterAdmissionError) as raced:
                admit_no_write_adapter(root_two)
        self.assertEqual(raced.exception.reason, "adapter-evidence-race")

    def test_symlinked_unreadable_and_missing_registry_fail_closed(self) -> None:
        holder, root = build_admission_root()
        self.addCleanup(holder.cleanup)
        registry_path = root / "outputs/adapter-evidence/registry.json"
        outside_copy = root / "registry-copy.json"
        outside_copy.write_bytes(registry_path.read_bytes())
        registry_path.unlink()
        registry_path.symlink_to(outside_copy)
        with self.assertRaises(AdapterAdmissionError) as symlinked:
            admit_no_write_adapter(root)
        self.assertEqual(symlinked.exception.reason, "adapter-registry-path-uncertain")

        registry_path.unlink()
        registry_path.write_text("{", encoding="utf-8")
        with self.assertRaises(AdapterAdmissionError) as malformed:
            admit_no_write_adapter(root)
        self.assertEqual(malformed.exception.reason, "adapter-registry-unreadable")

        registry_path.unlink()
        with self.assertRaises(AdapterAdmissionError) as absent:
            admit_no_write_adapter(root)
        self.assertEqual(absent.exception.reason, "adapter-registry-path-uncertain")

    def test_no_write_authority_cannot_justify_a_mutating_output_path(self) -> None:
        receipt, root = self.admit()
        with self.assertRaises(AdapterAdmissionError) as conflict:
            scripts_operator_status._reject_mutation_with_admission(
                receipt, no_write=False
            )
        self.assertEqual(conflict.exception.reason, "adapter-admission-write-conflict")
        self.assertIsNone(
            scripts_operator_status._admission_for_run(root, no_write=False)
        )
        self.assertIsNotNone(
            scripts_operator_status._admission_for_run(root, no_write=True)
        )

class CliNoWriteOnrampTests(unittest.TestCase):
    """The public CLI admits, replays deterministically and touches no output."""

    def setUp(self) -> None:
        self.holder, self.root = build_status_root()
        self.addCleanup(self.holder.cleanup)

    def _run_cli(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--root",
                str(self.root),
                "--no-write",
                "--json",
                *extra,
            ],
            text=True,
            capture_output=True,
            timeout=60,
        )

    def test_public_onramp_admits_bound_adapter_without_touching_files(self) -> None:
        default_output = self.root / "outputs/operator-status/latest.json"
        default_output.parent.mkdir(parents=True, exist_ok=True)
        default_output.write_text("preserve me\n", encoding="utf-8")
        default_before = (
            default_output.read_bytes(),
            default_output.stat().st_mtime_ns,
        )
        scratch = self.root / "audit-work" / "slice-scratch"
        scratch.mkdir(parents=True)
        forbidden_output = scratch / "no-write-must-not-exist.json"
        result = self._run_cli("--output", str(forbidden_output.relative_to(self.root)))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        receipt = payload["sections"]["checks"]["value"]["adapter_admission"]
        self.assertEqual(receipt["adapter_id"], ADMITTED_ADAPTER_ID)
        self.assertEqual(receipt["onramp"], ADMISSION_ONRAMP)
        self.assertIs(receipt["commands_executed"], False)
        registry_path = self.root / "outputs/adapter-evidence/registry.json"
        registry_bytes = registry_path.read_bytes()
        self.assertEqual(receipt["registry_sha256"], _sha256_bytes(registry_bytes))
        registry = json.loads(registry_bytes)
        record = next(
            item for item in registry["adapters"] if item["id"] == ADMITTED_ADAPTER_ID
        )
        canonical_record = json.dumps(
            record, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(
            receipt["adapter_record_sha256"], _sha256_bytes(canonical_record)
        )
        self.assertEqual(receipt["supported_assets"], record["supported_assets"])
        self.assertEqual(receipt["evidence"], record["evidence"])
        self.assertFalse(forbidden_output.exists())
        self.assertEqual(default_output.read_bytes(), default_before[0])
        self.assertEqual(default_output.stat().st_mtime_ns, default_before[1])

    def test_public_onramp_replay_is_byte_identical(self) -> None:
        first = self._run_cli("--observed-at", FIXED_TIME)
        second = self._run_cli("--observed-at", FIXED_TIME)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_write_capable_run_stays_available_and_claims_no_admission(self) -> None:
        scratch = self.root / "audit-work" / "slice-scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        destination = scratch / "write-path-check.json"
        self.addCleanup(lambda: destination.unlink(missing_ok=True))
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--root",
                str(self.root),
                "--observed-at",
                FIXED_TIME,
                "--output",
                str(destination.relative_to(self.root)),
                "--json",
            ],
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(destination.exists())
        written = json.loads(destination.read_text(encoding="utf-8"))
        self.assertNotIn("adapter_admission", written["sections"]["checks"]["value"])

if __name__ == "__main__":
    unittest.main()
