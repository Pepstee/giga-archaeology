from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate_evidence_ledger.py")
SPEC = importlib.util.spec_from_file_location("evidence_validator", MODULE_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class EvidenceValidatorTests(unittest.TestCase):
    def test_tree_hash_is_path_sensitive_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "b").mkdir()
            (root / "b" / "two.txt").write_bytes(b"two")
            (root / "one.txt").write_bytes(b"one")
            first = validator.tree_observation(root)
            second = validator.tree_observation(root)
            self.assertEqual(first, second)
            (root / "one.txt").write_bytes(b"changed")
            third = validator.tree_observation(root)
            self.assertNotEqual(first["tree_sha256"], third["tree_sha256"])

    def test_zip_observation_detects_unsafe_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escape.txt", b"no")
            observed = validator.zip_observation(archive_path, full_crc=True)
            self.assertEqual(observed["unsafe_paths"], 1)
            self.assertEqual(observed["crc_test"], "pass")

    def test_inventory_validation_detects_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            payload = repo / "source.bin"
            payload.write_bytes(b"original")
            ledger_path = repo / "ledger.json"
            ledger = {
                "schema": "giga.immutable-evidence-ledger.v1",
                "repository_root": ".",
                "archive_discovery": {
                    "extensions": [".zip"],
                    "excluded_directory_names": [".git"],
                    "excluded_path_fragments_casefold": ["dubbing-studio"],
                    "inventory": []
                },
                "assets": [
                    {
                        "id": "source",
                        "relative_path": "source.bin",
                        "kind": "file",
                        "format": "opaque",
                        "size_bytes": 8,
                        "sha256": validator.sha256_file(payload),
                        "permissions": {
                            "mode": validator.file_mode(payload)
                        },
                        "consumer_references": [],
                        "baseline_coverage": [],
                        "protection_gaps": []
                    }
                ],
                "migration_readiness": {
                    "ready": True,
                    "blocking_findings": []
                }
            }
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            clean = validator.validate(
                ledger_path, repo_override=repo, mode="inventory"
            )
            self.assertTrue(clean["ok"], clean["errors"])
            payload.write_bytes(b"tampered")
            drifted = validator.validate(
                ledger_path, repo_override=repo, mode="inventory"
            )
            self.assertFalse(drifted["ok"])
            self.assertTrue(
                any(".sha256" in error for error in drifted["errors"])
            )

    def test_acceptance_mode_fails_closed_on_declared_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            ledger_path = repo / "ledger.json"
            ledger = {
                "schema": "giga.immutable-evidence-ledger.v1",
                "repository_root": ".",
                "archive_discovery": {
                    "extensions": [".zip"],
                    "excluded_directory_names": [".git"],
                    "excluded_path_fragments_casefold": ["dubbing-studio"],
                    "inventory": []
                },
                "assets": [],
                "migration_readiness": {
                    "ready": False,
                    "blocking_findings": [
                        {
                            "id": "TEST-P0",
                            "severity": "P0",
                            "finding": "restore drill absent"
                        }
                    ]
                }
            }
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            inventory = validator.validate(
                ledger_path, repo_override=repo, mode="inventory"
            )
            acceptance = validator.validate(
                ledger_path, repo_override=repo, mode="acceptance"
            )
            self.assertTrue(inventory["ok"])
            self.assertFalse(acceptance["ok"])
            self.assertIn("TEST-P0", acceptance["errors"][0])


if __name__ == "__main__":
    unittest.main()
