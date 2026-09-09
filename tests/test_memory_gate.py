"""Synthetic internal algorithm evidence; production corpus activation is unavailable."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from twin_core.memory_gate import MemoryGateError, _require_memory_gate as require_memory_gate

class MemoryGateTests(unittest.TestCase):

    def test_missing_tombstone_ledger_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            memory = root / 'memory'
            (memory / 'entries').mkdir(parents=True)
            (memory / 'INDEX.md').write_text('# Index\n', encoding='utf-8')
            with self.assertRaisesRegex(MemoryGateError, 'tombstone-ledger'):
                require_memory_gate(root, 'pre-context')

    def test_empty_valid_store_emits_content_addressed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            memory = root / 'memory'
            (memory / 'entries').mkdir(parents=True)
            (memory / 'INDEX.md').write_text('# Index\n', encoding='utf-8')
            (memory / 'MEMORY_PROTOCOL.md').write_text('policy\n', encoding='utf-8')
            ledger = {'schema': 'giga.memory.legacy-tombstones.v1', 'append_only': True, 'deletion_performed': False, 'entries': []}
            (memory / 'tombstones.v1.json').write_text(json.dumps(ledger) + '\n', encoding='utf-8')
            receipt = require_memory_gate(root, 'pre-context')
            self.assertEqual(receipt['result'], 'passed')
            matches = list((memory / 'validation/receipts').glob(f"pre-context-{receipt['receipt_sha256']}.json"))
            self.assertEqual(len(matches), 1)
if __name__ == '__main__':
    unittest.main()



def test_public_corpus_entrypoints_refuse_before_filesystem_access():
    from unittest.mock import patch
    import pytest
    from twin_core import memory_gate, memory_proposals, context_compiler, telegram_pipeline
    from twin_core.constitutional_authority import AuthorityRefused
    root = Path("/synthetic-not-opened")
    calls = [
        lambda: memory_gate.validate_memory_gate(root, "pre-context"),
        lambda: memory_gate.require_memory_gate(root, "pre-context"),
        lambda: memory_gate.write_rollback_receipt(root),
        lambda: memory_proposals.validate_proposal(root, {}),
        lambda: memory_proposals.commit_proposal(root, None),
        lambda: context_compiler.compile_context(root, "synthetic"),
        lambda: telegram_pipeline.memory_inventory(root),
        lambda: telegram_pipeline.provider_prompt(root, "synthetic", "event"),
        lambda: telegram_pipeline.process_event(),
    ]
    with patch.object(Path, "open", side_effect=AssertionError("must refuse before I/O")), patch.object(Path, "resolve", side_effect=AssertionError("must refuse before resolution")):
        for call in calls:
            with pytest.raises(AuthorityRefused, match="HOST_BOUND_CORPUS_ACTIVATION_REQUIRED"):
                call()


def test_internal_gate_refuses_symlink_before_reading_target(tmp_path):
    from unittest.mock import patch
    import pytest
    from twin_core import memory_gate
    root = tmp_path.resolve()
    (root / "memory").mkdir()
    outside = root / "synthetic-excluded.txt"
    outside.write_text("synthetic must not be read")
    (root / "memory" / "linked.txt").symlink_to(outside)
    with patch.object(memory_gate, "_sha256", side_effect=AssertionError("must not hash target")):
        with pytest.raises(MemoryGateError, match="memory-symlink"):
            memory_gate._require_memory_gate(root, "pre-context")


def test_memory_cli_refuses_without_opening_selected_root(capsys):
    from twin_core.cli import main
    assert main(["--root", "/synthetic-not-opened", "validate-memory", "--json"]) == 1
    assert "HOST_BOUND_CORPUS_ACTIVATION_REQUIRED" in capsys.readouterr().out
