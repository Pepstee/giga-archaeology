from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from twin_core.integrity import verify_hash_baseline


class IntegrityTests(unittest.TestCase):
    def test_baseline_verifies_and_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            export = root / "export.zip"
            export.write_bytes(b"immutable source")
            digest = hashlib.sha256(export.read_bytes()).hexdigest()
            baseline = root / "baseline.sha256"
            baseline.write_text(f"{digest}  export.zip\n", encoding="utf-8")
            self.assertTrue(verify_hash_baseline(root, baseline)["ok"])
            export.write_bytes(b"changed")
            result = verify_hash_baseline(root, baseline)
            self.assertFalse(result["ok"])
            self.assertFalse(result["files"][0]["ok"])

    def test_baseline_rejects_paths_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            baseline = root / "baseline.sha256"
            baseline.write_text(f"{'a' * 64}  ../escape.zip\n", encoding="utf-8")
            result = verify_hash_baseline(root, baseline)
            self.assertFalse(result["ok"])
            self.assertIn("escapes", result["errors"][0])
