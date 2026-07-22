from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from twin_core.memory_proposals import commit_proposal, validate_proposal


ENTRY = """---
type: fact
tags: [test]
created: 2026-07-20
status: active
---
The trust kernel exists.

Source: operator-confirmed test.
"""


class MemoryProposalTests(unittest.TestCase):
    def memory(self, root: Path) -> Path:
        memory = root / "memory"
        (memory / "entries").mkdir(parents=True)
        (memory / "INDEX.md").write_text("# Memory Index\n", encoding="utf-8")
        return memory

    def test_create_and_index_replace_are_validated_then_idempotently_committed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory = self.memory(Path(folder))
            index = memory / "INDEX.md"
            index_hash = hashlib.sha256(index.read_bytes()).hexdigest()
            proposal = validate_proposal(memory, {
                "schema_version": 1,
                "reply": "Filed and linked.",
                "operations": [
                    {
                        "operation": "create",
                        "path": "entries/2026-07-20-trust-kernel.md",
                        "expected_sha256": None,
                        "content": ENTRY,
                    },
                    {
                        "operation": "replace",
                        "path": "INDEX.md",
                        "expected_sha256": index_hash,
                        "content": (
                            "# Memory Index\n\n- [trust kernel]"
                            "(entries/2026-07-20-trust-kernel.md) — fact\n"
                        ),
                    },
                ],
            })
            first = commit_proposal(memory, proposal)
            replay = commit_proposal(memory, proposal)
            self.assertEqual(first, replay)
            self.assertTrue((memory / "entries" / "2026-07-20-trust-kernel.md").exists())

    def test_delete_escape_and_stale_replace_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory = self.memory(Path(folder))
            base = {"schema_version": 1, "reply": "No change."}
            with self.assertRaises(ValueError):
                validate_proposal(memory, {**base, "operations": [{
                    "operation": "delete", "path": "INDEX.md", "expected_sha256": None,
                    "content": "",
                }]})
            with self.assertRaises(ValueError):
                validate_proposal(memory, {**base, "operations": [{
                    "operation": "create", "path": "../escape.md", "expected_sha256": None,
                    "content": ENTRY,
                }]})
            with self.assertRaises(ValueError):
                validate_proposal(memory, {**base, "operations": [{
                    "operation": "replace", "path": "INDEX.md",
                    "expected_sha256": "0" * 64, "content": "# Changed\n",
                }]})

    def test_projected_memory_must_be_internally_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory = self.memory(Path(folder))
            with self.assertRaisesRegex(ValueError, "missing from index"):
                validate_proposal(memory, {
                    "schema_version": 1,
                    "reply": "Filed.",
                    "operations": [{
                        "operation": "create",
                        "path": "entries/2026-07-20-unindexed.md",
                        "expected_sha256": None,
                        "content": ENTRY,
                    }],
                })
