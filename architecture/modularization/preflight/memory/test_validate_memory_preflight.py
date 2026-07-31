from __future__ import annotations

import copy
import unittest
from pathlib import Path

from architecture.modularization.preflight.memory.validate_memory_preflight import (
    ROOT,
    active_truth_digest,
    deterministic_id,
    sha256_text,
    snapshot_digest,
    validate_contracts,
    validate_legacy,
    validate_snapshot,
)


UNKNOWN = {"state": "unknown", "reason": "not-recorded"}


def snapshot_fixture() -> dict:
    statement = "The operator confirmed a synthetic test preference."
    content = "Synthetic immutable revision content."
    legacy_path = "memory/entries/2026-07-31-test.md"
    legacy_sha256 = "1" * 64
    entry_id = deterministic_id(
        "mem", {"legacy_path": legacy_path, "legacy_sha256": legacy_sha256}
    )
    revision_id = deterministic_id(
        "rev",
        {
            "entry_id": entry_id,
            "parent_revision_id": None,
            "content_sha256": sha256_text(content),
            "created_at": "2026-07-31",
        },
    )
    claim_id = deterministic_id(
        "clm",
        {
            "revision_id": revision_id,
            "ordinal": 0,
            "statement_sha256": sha256_text(statement),
        },
    )
    payload = {
        "schema_version": "giga.memory.snapshot.v2",
        "snapshot_sha256": "0" * 64,
        "active_truth_sha256": "0" * 64,
        "evaluated_at": "2026-07-31T00:00:00Z",
        "source_manifest": {
            "history_complete": True,
            "sources": [
                {
                    "path": legacy_path,
                    "sha256": legacy_sha256,
                    "role": "legacy-entry",
                }
            ],
        },
        "entries": [
            {
                "entry_id": entry_id,
                "slug": "2026-07-31-test",
                "legacy_path": legacy_path,
                "legacy_sha256": legacy_sha256,
                "head_revision_id": revision_id,
                "revisions": [
                    {
                        "revision_id": revision_id,
                        "parent_revision_id": None,
                        "created_at": "2026-07-31",
                        "lifecycle": "active",
                        "content": content,
                        "content_sha256": sha256_text(content),
                        "original_metadata": {
                            "type": "fact",
                            "status": "active",
                        },
                        "claims": [
                            {
                                "claim_id": claim_id,
                                "kind": "fact",
                                "statement": statement,
                                "statement_sha256": sha256_text(statement),
                                "lifecycle": "active",
                                "epistemic": {
                                    "status": "operator-confirmed",
                                    "confidence": 1.0,
                                    "reviewed_by": "operator",
                                },
                                "temporal": {
                                    "observed_at": "2026-07-31",
                                    "valid_from": "2026-07-31",
                                    "valid_until": UNKNOWN,
                                },
                                "evidence": [
                                    {
                                        "source_id": "src:test-operator",
                                        "source_sha256": "5" * 64,
                                        "locator": "synthetic fixture",
                                        "authority": "operator-confirmed",
                                    }
                                ],
                                "derived_from_claim_ids": [],
                                "contradicts_claim_ids": [],
                            }
                        ],
                    }
                ],
            }
        ],
        "tombstones": [],
        "derived_artifacts": [],
        "migration": {
            "rules_version": "giga.memory.migration-rules.v2",
            "status": "accepted",
            "blockers": [],
            "unknown_values_preserved": True,
        },
    }
    payload["active_truth_sha256"] = active_truth_digest(
        [
            {
                "claim_id": claim_id,
                "revision_id": revision_id,
                "statement_sha256": sha256_text(statement),
            }
        ]
    )
    payload["snapshot_sha256"] = snapshot_digest(payload)
    return payload


def codes(result: dict) -> set[str]:
    return {code for code, _ in result["error_codes"]}


class MemoryPreflightTests(unittest.TestCase):
    def test_contract_bundle_is_internally_consistent(self) -> None:
        result = validate_contracts(ROOT)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["counts"]["contracts"], 4)

    def test_valid_snapshot_passes_inventory_and_acceptance(self) -> None:
        payload = snapshot_fixture()
        self.assertTrue(validate_snapshot(payload)["ok"])
        self.assertTrue(validate_snapshot(payload, acceptance=True)["ok"])

    def test_archived_claim_is_preserved_but_excluded_from_active_truth(self) -> None:
        payload = snapshot_fixture()
        claim = payload["entries"][0]["revisions"][0]["claims"][0]
        original_statement = claim["statement"]
        claim["lifecycle"] = "archived"
        payload["active_truth_sha256"] = active_truth_digest([])
        payload["snapshot_sha256"] = snapshot_digest(payload)
        result = validate_snapshot(payload)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["counts"]["active_truth_claims"], 0)
        self.assertEqual(claim["statement"], original_statement)

    def test_tombstone_excludes_claim_without_erasing_it(self) -> None:
        payload = snapshot_fixture()
        claim = payload["entries"][0]["revisions"][0]["claims"][0]
        tombstone_id = deterministic_id(
            "tmb",
            {
                "target_type": "claim",
                "target_id": claim["claim_id"],
                "target_sha256": claim["statement_sha256"],
                "reason_code": "false",
                "effective_at": "2026-07-31",
                "authorized_by": "operator",
            },
        )
        payload["tombstones"].append(
            {
                "tombstone_id": tombstone_id,
                "target_type": "claim",
                "target_id": claim["claim_id"],
                "target_sha256": claim["statement_sha256"],
                "reason_code": "false",
                "rationale": "Synthetic correction.",
                "effective_at": "2026-07-31",
                "authorized_by": "operator",
                "evidence": [
                    {
                        "source_id": "src:test-correction",
                        "source_sha256": "3" * 64,
                        "locator": "synthetic fixture",
                        "authority": "operator-confirmed",
                    }
                ],
                "invalidates_derivatives": True,
            }
        )
        payload["active_truth_sha256"] = active_truth_digest([])
        payload["snapshot_sha256"] = snapshot_digest(payload)
        result = validate_snapshot(payload)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["counts"]["active_truth_claims"], 0)
        self.assertIn("Synthetic", payload["tombstones"][0]["rationale"])
        self.assertIn("operator confirmed", claim["statement"].lower())

    def test_contradictions_must_be_symmetric(self) -> None:
        payload = snapshot_fixture()
        first = payload["entries"][0]["revisions"][0]["claims"][0]
        second = copy.deepcopy(first)
        second["statement"] = "A contradictory synthetic claim."
        second["statement_sha256"] = sha256_text(second["statement"])
        second["claim_id"] = deterministic_id(
            "clm",
            {
                "revision_id": payload["entries"][0]["head_revision_id"],
                "ordinal": 1,
                "statement_sha256": second["statement_sha256"],
            },
        )
        first["contradicts_claim_ids"] = [second["claim_id"]]
        payload["entries"][0]["revisions"][0]["claims"].append(second)
        payload["active_truth_sha256"] = active_truth_digest([])
        payload["snapshot_sha256"] = snapshot_digest(payload)
        result = validate_snapshot(payload)
        self.assertFalse(result["ok"])
        self.assertIn("contradiction-asymmetry", codes(result))

    def test_current_derivative_cannot_depend_on_tombstoned_claim(self) -> None:
        payload = snapshot_fixture()
        claim = payload["entries"][0]["revisions"][0]["claims"][0]
        tombstone_id = deterministic_id(
            "tmb",
            {
                "target_type": "claim",
                "target_id": claim["claim_id"],
                "target_sha256": claim["statement_sha256"],
                "reason_code": "policy",
                "effective_at": "2026-07-31",
                "authorized_by": "deterministic-policy",
            },
        )
        payload["tombstones"].append(
            {
                "tombstone_id": tombstone_id,
                "target_type": "claim",
                "target_id": claim["claim_id"],
                "target_sha256": claim["statement_sha256"],
                "reason_code": "policy",
                "rationale": "Synthetic policy test.",
                "effective_at": "2026-07-31",
                "authorized_by": "deterministic-policy",
                "evidence": [
                    {
                        "source_id": "src:test-policy",
                        "source_sha256": "4" * 64,
                        "locator": "synthetic fixture",
                        "authority": "source-observation",
                    }
                ],
                "invalidates_derivatives": True,
            }
        )
        payload["active_truth_sha256"] = active_truth_digest([])
        payload["snapshot_sha256"] = snapshot_digest(payload)
        payload["derived_artifacts"] = [
            {
                "artifact_id": "ctx:test-artifact",
                "stage": "context",
                "artifact_sha256": "2" * 64,
                "memory_snapshot_sha256": payload["snapshot_sha256"],
                "active_truth_sha256": payload["active_truth_sha256"],
                "claim_dependencies": [claim["claim_id"]],
                "revision_dependencies": [],
                "state": "current",
                "invalidated_by": [],
            }
        ]
        result = validate_snapshot(payload)
        self.assertFalse(result["ok"])
        self.assertIn("derived-current-invalid", codes(result))
        self.assertIn("derived-invalidation-receipt", codes(result))

    def test_snapshot_hash_drift_fails_closed(self) -> None:
        payload = snapshot_fixture()
        payload["entries"][0]["revisions"][0]["content"] += " drift"
        result = validate_snapshot(payload)
        self.assertFalse(result["ok"])
        self.assertIn("revision-content-hash", codes(result))
        self.assertIn("snapshot-hash", codes(result))

    def test_legacy_inventory_matches_but_acceptance_is_blocked(self) -> None:
        repo = Path(__file__).resolve().parents[4]
        inventory = validate_legacy(repo)
        self.assertTrue(inventory["ok"], inventory)
        acceptance = validate_legacy(repo, acceptance=True)
        self.assertFalse(acceptance["ok"])
        self.assertIn("acceptance-live-validator-red", codes(acceptance))
        self.assertIn("acceptance-declared-blocker", codes(acceptance))


if __name__ == "__main__":
    unittest.main()
