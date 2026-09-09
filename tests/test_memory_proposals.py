"""Synthetic internal algorithm evidence; production corpus activation is unavailable."""
from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from twin_core.memory_proposals import _commit_proposal as commit_proposal, _validate_proposal as validate_proposal
ENTRY = '---\ntype: fact\ntags: [test]\ncreated: 2026-07-20\nstatus: active\n---\nThe trust kernel exists.\n\nSource: operator-confirmed test.\n'

class MemoryProposalTests(unittest.TestCase):

    def memory(self, root: Path) -> Path:
        memory = root / 'memory'
        (memory / 'entries').mkdir(parents=True)
        (memory / 'INDEX.md').write_text('# Memory Index\n', encoding='utf-8')
        (memory / 'MEMORY_PROTOCOL.md').write_text('policy\n', encoding='utf-8')
        (memory / 'tombstones.v1.json').write_text('{"schema":"giga.memory.legacy-tombstones.v1","append_only":true,"deletion_performed":false,"entries":[]}\n', encoding='utf-8')
        return memory

    def test_create_and_index_replace_are_validated_then_idempotently_committed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory = self.memory(Path(folder).resolve())
            index = memory / 'INDEX.md'
            index_hash = hashlib.sha256(index.read_bytes()).hexdigest()
            proposal = validate_proposal(memory, {'schema_version': 1, 'reply': 'Filed and linked.', 'operations': [{'operation': 'create', 'path': 'entries/2026-07-20-trust-kernel.md', 'expected_sha256': None, 'content': ENTRY}, {'operation': 'replace', 'path': 'INDEX.md', 'expected_sha256': index_hash, 'content': '# Memory Index\n\n- [trust kernel](entries/2026-07-20-trust-kernel.md) — fact\n'}]})
            first = commit_proposal(memory, proposal)
            replay = commit_proposal(memory, proposal)
            self.assertEqual(first, replay)
            self.assertTrue((memory / 'entries' / '2026-07-20-trust-kernel.md').exists())

    def test_delete_escape_and_stale_replace_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory = self.memory(Path(folder).resolve())
            base = {'schema_version': 1, 'reply': 'No change.'}
            with self.assertRaises(ValueError):
                validate_proposal(memory, {**base, 'operations': [{'operation': 'delete', 'path': 'INDEX.md', 'expected_sha256': None, 'content': ''}]})
            with self.assertRaises(ValueError):
                validate_proposal(memory, {**base, 'operations': [{'operation': 'create', 'path': '../escape.md', 'expected_sha256': None, 'content': ENTRY}]})
            with self.assertRaises(ValueError):
                validate_proposal(memory, {**base, 'operations': [{'operation': 'replace', 'path': 'INDEX.md', 'expected_sha256': '0' * 64, 'content': '# Changed\n'}]})

    def test_projected_memory_must_be_internally_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory = self.memory(Path(folder).resolve())
            with self.assertRaisesRegex(ValueError, 'missing from index'):
                validate_proposal(memory, {'schema_version': 1, 'reply': 'Filed.', 'operations': [{'operation': 'create', 'path': 'entries/2026-07-20-unindexed.md', 'expected_sha256': None, 'content': ENTRY}]})

    def test_partial_commit_failure_restores_the_exact_source_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            memory = self.memory(Path(folder).resolve())
            index = memory / 'INDEX.md'
            before = index.read_bytes()
            index_hash = hashlib.sha256(before).hexdigest()
            proposal = validate_proposal(memory, {'schema_version': 1, 'reply': 'Filed.', 'operations': [{'operation': 'create', 'path': 'entries/2026-07-20-trust-kernel.md', 'expected_sha256': None, 'content': ENTRY}, {'operation': 'replace', 'path': 'INDEX.md', 'expected_sha256': index_hash, 'content': '# Memory Index\n\n- [trust kernel](entries/2026-07-20-trust-kernel.md) — fact\n'}]})
            from twin_core import memory_proposals
            real_write = memory_proposals._atomic_write
            calls = 0

            def fail_second(target: Path, content: bytes) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError('injected failure')
                real_write(target, content)
            with patch('twin_core.memory_proposals._atomic_write', side_effect=fail_second):
                with self.assertRaisesRegex(OSError, 'injected failure'):
                    commit_proposal(memory, proposal)
            self.assertEqual(index.read_bytes(), before)
            self.assertFalse((memory / 'entries/2026-07-20-trust-kernel.md').exists())
            rollback_receipts = list((memory / 'validation/receipts').glob('post-commit-rollback-*.json'))
            self.assertEqual(len(rollback_receipts), 1)



def test_internal_commit_rejects_stale_validated_snapshot(tmp_path):
    import pytest
    root = tmp_path.resolve()
    memory = MemoryProposalTests().memory(root)
    index = memory / "INDEX.md"
    proposal = validate_proposal(memory, {
        "schema_version": 1, "reply": "synthetic update", "operations": [{
            "operation": "replace", "path": "INDEX.md",
            "expected_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
            "content": "# Memory Index\n\nProposed synthetic commentary.\n",
        }],
    })
    index.write_text("# Memory Index\n\nConcurrent synthetic commentary.\n")
    with pytest.raises(ValueError, match="snapshot changed"):
        commit_proposal(memory, proposal)
