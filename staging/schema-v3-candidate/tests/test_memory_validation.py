from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from twin_core.memory_validation import validate_memory


class MemoryValidationTests(unittest.TestCase):
    def test_valid_memory_passes_and_broken_links_fail(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entries = root / "entries"
            entries.mkdir()
            (entries / "2026-01-01-one.md").write_text(
                "---\ntype: fact\ntags: [test]\ncreated: 2026-01-01\nstatus: active\n---\n"
                "Fact.\nSource: operator.\nSee [[2026-01-01-two]].\n"
            )
            (entries / "2026-01-01-two.md").write_text(
                "---\ntype: decision\ntags: [test]\ncreated: 2026-01-01\nstatus: active\n---\n"
                "Decision.\nSource: operator.\n"
            )
            (root / "INDEX.md").write_text(
                "- [one](entries/2026-01-01-one.md)\n- [two](entries/2026-01-01-two.md)\n"
            )
            self.assertTrue(validate_memory(root)["ok"])
            (entries / "2026-01-01-two.md").unlink()
            result = validate_memory(root)
            self.assertFalse(result["ok"])
            self.assertIn("broken-entry-link", {item["code"] for item in result["findings"]})

    def test_unreviewed_marker_is_required_for_auto_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entries = root / "entries"
            entries.mkdir()
            (entries / "2026-01-01-one.md").write_text(
                "---\ntype: fact\ntags: [auto-ingest]\ncreated: 2026-01-01\nstatus: active\n---\n"
                "Fact.\nSource: corpus.\n"
            )
            (root / "INDEX.md").write_text("- [one](entries/2026-01-01-one.md)\n")
            result = validate_memory(root)
            self.assertFalse(result["ok"])
            self.assertIn("auto-review", {item["code"] for item in result["findings"]})

