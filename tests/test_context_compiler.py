from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from twin_core.context_compiler import MAX_PACKET_CHARS, compile_context


class ContextCompilerTests(unittest.TestCase):
    def test_relevant_entry_and_one_hop_neighbour_are_selected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            memory = root / "memory"
            entries = memory / "entries"
            entries.mkdir(parents=True)
            (root / "CONTEXT.md").write_text("standing", encoding="utf-8")
            (memory / "MEMORY_PROTOCOL.md").write_text("policy", encoding="utf-8")
            (memory / "INDEX.md").write_text("index", encoding="utf-8")
            (entries / "2026-07-20-market-aligner.md").write_text(
                "Market Aligner commercial product links [[2026-07-20-career-goal]].",
                encoding="utf-8",
            )
            (entries / "2026-07-20-career-goal.md").write_text(
                "Career outcome by end of 2026.", encoding="utf-8"
            )
            (entries / "2026-07-20-unrelated.md").write_text("Dentist history.", encoding="utf-8")
            packet = compile_context(root, "What is the Market Aligner product boundary?")
            paths = {item["path"] for item in packet["documents"]}
            self.assertIn("memory/entries/2026-07-20-market-aligner.md", paths)
            self.assertIn("memory/entries/2026-07-20-career-goal.md", paths)
            self.assertNotIn("memory/entries/2026-07-20-unrelated.md", paths)
            self.assertLessEqual(len(str(packet)), MAX_PACKET_CHARS)
