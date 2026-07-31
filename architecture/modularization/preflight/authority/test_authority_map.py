#!/usr/bin/env python3
"""Focused tests for the Wave 0A authority map and validator."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_authority_map as validator


class AuthorityMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(
            validator.MANIFEST.read_text(encoding="utf-8")
        )
        cls.batches = json.loads(
            validator.BATCH_MANIFEST.read_text(encoding="utf-8")
        )

    def test_structural_validation_passes(self) -> None:
        errors, blockers = validator.validate_payload(self.payload)
        self.assertEqual(errors, [])
        self.assertGreater(len(blockers), 0)

    def test_every_live_root_path_is_mapped_once(self) -> None:
        live = validator.current_top_level()
        mapped = sorted(entry["source"] for entry in self.payload["entries"])
        self.assertEqual(mapped, live)
        self.assertEqual(len(mapped), len(set(mapped)))
        digest = hashlib.sha256("\n".join(mapped).encode("utf-8")).hexdigest()
        self.assertEqual(
            digest, self.payload["scope"]["top_level_name_set_sha256"]
        )

    def test_wave_zero_cannot_move_any_entry(self) -> None:
        self.assertFalse(self.payload["scope"]["wave0_moves_authorized"])
        self.assertTrue(
            all(
                entry["wave0_move_authorized"] is False
                for entry in self.payload["entries"]
            )
        )

    def test_specialised_skill_module_has_owned_and_external_boundaries(self) -> None:
        module = self.payload["target_architecture"]["modules"]["skills"]
        self.assertEqual(module["owner"], "giga-user platform")
        self.assertEqual(
            module["canonical_owned_source"], "modules/skills/owned"
        )
        source_classes = {
            item["target_class"]
            for item in self.payload["skills"]["source_classes"]
        }
        self.assertTrue(
            validator.REQUIRED_SKILL_TARGET_CLASSES.issubset(source_classes)
        )
        owned = {
            item["name"] for item in self.payload["skills"]["giga_owned_skills"]
        }
        self.assertEqual(owned, {"librarian", "skilltree-operator"})

    def test_blocked_ambiguity_prevents_acceptance_readiness(self) -> None:
        errors, blockers = validator.validate_payload(self.payload)
        self.assertFalse(errors)
        self.assertTrue(blockers)
        blocked_sources = {item.split(":", 1)[0] for item in blockers}
        self.assertEqual(
            blocked_sources, {"life-admin", "market-aligner-artiom"}
        )

    def test_concurrent_life_admin_workspace_is_fail_closed(self) -> None:
        entry = next(
            item for item in self.payload["entries"]
            if item["source"] == "life-admin"
        )
        self.assertEqual(entry["disposition"], "protected/no-touch")
        self.assertEqual(entry["lifecycle_status"], "active-concurrent-workspace")
        self.assertEqual(entry["destination"], "projects/life-admin")
        self.assertEqual(entry["ambiguity"]["state"], "blocked")
        deferred = {
            item["source"]: item
            for item in self.batches["deferred"]
        }
        self.assertIn("life-admin", deferred)
        self.assertEqual(
            deferred["life-admin"]["required_decision"],
            "identify originating task, seal tree, register project, then migrate in a later isolated batch",
        )
        self.assertEqual(len(self.batches["batches"]), 13)
        self.assertNotIn(
            "life-admin",
            {
                source
                for batch in self.batches["batches"]
                for source in batch["source_paths"]
            },
        )

    def test_migration_batches_validate(self) -> None:
        errors = validator.validate_batches(self.batches, self.payload)
        self.assertEqual(errors, [])

    def test_script_and_test_routes_are_exhaustive(self) -> None:
        actual_scripts = {
            str(path.relative_to(validator.ROOT))
            for path in (validator.ROOT / "scripts").iterdir()
            if path.is_file()
        }
        actual_tests = {
            str(path.relative_to(validator.ROOT))
            for path in (validator.ROOT / "tests").iterdir()
            if path.is_file()
        }
        self.assertEqual(set(self.batches["script_routes"]), actual_scripts)
        self.assertEqual(set(self.batches["test_routes"]), actual_tests)

    def test_batches_never_include_protected_sources(self) -> None:
        protected = {
            entry["source"]
            for entry in self.payload["entries"]
            if entry["disposition"] == "protected/no-touch"
        }
        sources = [
            source
            for batch in self.batches["batches"]
            for source in batch["source_paths"]
        ]
        self.assertFalse(
            {
                source
                for source in sources
                if any(
                    source == root or source.startswith(f"{root}/")
                    for root in protected
                )
            }
        )

    def test_validator_rejects_batch_source_overlap(self) -> None:
        corrupted = copy.deepcopy(self.batches)
        first = corrupted["batches"][0]["moves"][0]["source"]
        duplicate = {
            "source": first,
            "destination": "quarantine/test-overlap",
            "action": "move",
        }
        target = corrupted["batches"][1]
        target["moves"].append(duplicate)
        target["source_paths"].append(first)
        target["expected_post_move_paths"].append(duplicate["destination"])
        target["source_path_set_sha256"] = hashlib.sha256(
            "\n".join(sorted(target["source_paths"])).encode("utf-8")
        ).hexdigest()
        errors = validator.validate_batches(
            corrupted, self.payload, check_live_sources=False
        )
        self.assertTrue(any("source-path overlap" in error for error in errors))

    def test_validator_rejects_duplicate_source(self) -> None:
        corrupted = copy.deepcopy(self.payload)
        corrupted["entries"].append(copy.deepcopy(corrupted["entries"][0]))
        corrupted["scope"]["top_level_path_count"] += 1
        errors, _ = validator.validate_payload(
            corrupted, check_live_root=False
        )
        self.assertTrue(any("duplicate source" in error for error in errors))

    def test_validator_rejects_unowned_skill_module(self) -> None:
        corrupted = copy.deepcopy(self.payload)
        corrupted["target_architecture"]["modules"]["skills"]["owner"] = ""
        errors, _ = validator.validate_payload(
            corrupted, check_live_root=False
        )
        self.assertTrue(
            any("modules/skills lacks explicit GIGA ownership" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
