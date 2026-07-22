import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_contracts import validate_adapter, validate_evaluator, validate_provenance


class ContractTests(unittest.TestCase):
    def test_adapter_requires_honest_evidence(self):
        valid = {
            "id": "codex", "state": "instruction-backed", "supported_assets": ["AGENTS.md"],
            "unsupported_surfaces": ["native hooks"], "onramp": "project instructions",
            "verification_commands": ["python3 verify.py"], "risk_notes": ["policy is not enforcement"],
            "owner": "giga-user", "source_docs": ["adapter.md"], "verified_at": "2026-07-22T00:00:00Z"
        }
        self.assertEqual([], validate_adapter(valid))
        invalid = {**valid, "state": "native", "verification_commands": []}
        self.assertEqual(["empty:verification_commands"], validate_adapter(invalid))

    def test_evaluator_requires_rejected_negative_control(self):
        base = {
            "scenario": "safe import", "trace": "trace.json", "report": "report.json",
            "verifier": "independent", "rollback": "remove staged candidate", "promoted": False
        }
        only_accept = {**base, "candidates": [{"id": "a", "decision": "accepted", "evidence": ["test"]}]}
        self.assertIn("missing:rejected_negative_control", validate_evaluator(only_accept))
        complete = {**base, "candidates": [
            {"id": "a", "decision": "accepted", "evidence": ["test"]},
            {"id": "b", "decision": "rejected", "evidence": ["unsafe mutation"]}
        ]}
        self.assertEqual([], validate_evaluator(complete))

    def test_provenance_is_pinned_and_tested(self):
        valid = {
            "upstream": "https://github.com/affaan-m/ECC", "commit": "a" * 40,
            "source_path": "docs/example.md", "source_sha256": "b" * 64,
            "destination": "candidate/example.md", "adaptation": "concept only",
            "tests": ["python3 -m unittest"], "decision": "staged"
        }
        self.assertEqual([], validate_provenance(valid))
        invalid = {**valid, "commit": "main", "tests": []}
        self.assertEqual(["empty:tests", "invalid:commit"], validate_provenance(invalid))


if __name__ == "__main__":
    unittest.main()
