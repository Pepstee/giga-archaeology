"""Synthetic internal algorithm evidence; production corpus activation is unavailable."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from twin_core.context_compiler import MAX_PACKET_CHARS, _compile_context as compile_context

def entry(body: str, *, status: str='active') -> str:
    return f'---\ntype: fact\ntags: [test]\ncreated: 2026-07-20\nstatus: {status}\n---\n{body}\n\nSource: test fixture.\n'

class ContextCompilerTests(unittest.TestCase):

    def test_relevant_entry_and_one_hop_neighbour_are_selected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            memory = root / 'memory'
            entries = memory / 'entries'
            entries.mkdir(parents=True)
            (root / 'CONTEXT.md').write_text('standing', encoding='utf-8')
            (memory / 'MEMORY_PROTOCOL.md').write_text('policy', encoding='utf-8')
            (memory / 'tombstones.v1.json').write_text('{"schema":"giga.memory.legacy-tombstones.v1","append_only":true,"deletion_performed":false,"entries":[]}\n', encoding='utf-8')
            (memory / 'INDEX.md').write_text('# Index\n\n- [market](entries/2026-07-20-market-aligner.md)\n- [career](entries/2026-07-20-career-goal.md)\n- [unrelated](entries/2026-07-20-unrelated.md)\n', encoding='utf-8')
            (entries / '2026-07-20-market-aligner.md').write_text(entry('Market Aligner commercial product links [[2026-07-20-career-goal]].'), encoding='utf-8')
            (entries / '2026-07-20-career-goal.md').write_text(entry('Career outcome by end of 2026.'), encoding='utf-8')
            (entries / '2026-07-20-unrelated.md').write_text(entry('Dentist history.'), encoding='utf-8')
            packet = compile_context(root, 'What is the Market Aligner product boundary?')
            paths = {item['path'] for item in packet['documents']}
            self.assertIn('memory/entries/2026-07-20-market-aligner.md', paths)
            self.assertIn('memory/entries/2026-07-20-career-goal.md', paths)
            self.assertNotIn('memory/entries/2026-07-20-unrelated.md', paths)
            self.assertLessEqual(len(str(packet)), MAX_PACKET_CHARS)

    def test_inactive_entry_is_excluded_from_index_and_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            memory = root / 'memory'
            entries = memory / 'entries'
            entries.mkdir(parents=True)
            (root / 'CONTEXT.md').write_text('standing', encoding='utf-8')
            (memory / 'MEMORY_PROTOCOL.md').write_text('policy', encoding='utf-8')
            (memory / 'tombstones.v1.json').write_text('{"schema":"giga.memory.legacy-tombstones.v1","append_only":true,"deletion_performed":false,"entries":[]}\n', encoding='utf-8')
            (memory / 'INDEX.md').write_text('# Index\n\n- [obsolete](entries/2026-07-20-obsolete.md)\n', encoding='utf-8')
            (entries / '2026-07-20-obsolete.md').write_text(entry('Obsolete certainty.', status='archived'), encoding='utf-8')
            packet = compile_context(root, 'obsolete certainty')
            paths = {item['path'] for item in packet['documents']}
            self.assertNotIn('memory/entries/2026-07-20-obsolete.md', paths)
            index = next((item['content'] for item in packet['documents'] if item['path'] == 'memory/INDEX.md'))
            self.assertNotIn('obsolete', index)
