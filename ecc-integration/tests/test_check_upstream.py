import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_upstream.py"


class UpstreamCheckTests(unittest.TestCase):
    def test_script_never_contains_merge_or_pull_execution(self):
        text = SCRIPT.read_text()
        self.assertNotIn('"merge"', text)
        self.assertNotIn('"pull"', text)
        self.assertIn('"safe_to_auto_deploy": False', text)
        self.assertIn('"fetch"', text)

    def test_import_ledger_is_pinned_and_only_explicitly_implemented_entries_advance(self):
        ledger = json.loads((SCRIPT.parents[1] / "IMPORT_LEDGER.json").read_text())
        self.assertRegex(ledger["commit"], r"^[0-9a-f]{40}$")
        self.assertFalse(ledger["deployed"])
        self.assertTrue(ledger["entries"])
        decisions = {}
        for entry in ledger["entries"]:
            self.assertRegex(entry["source_sha256"], r"^[0-9a-f]{64}$")
            decisions[entry["id"]] = entry["decision"]
            self.assertIn(entry["decision"], {"staged", "implemented-read-only"})
            self.assertTrue(entry["tests"])
            if entry["decision"] == "implemented-read-only":
                self.assertTrue(entry.get("implementation"))
                for relative in entry["implementation"]:
                    self.assertTrue((SCRIPT.parents[2] / relative).exists(), relative)
        self.assertEqual("implemented-read-only", decisions.pop("status-field-map"))
        self.assertEqual("implemented-read-only", decisions.pop("adapter-evidence-contract"))
        self.assertEqual({"staged"}, set(decisions.values()))


if __name__ == "__main__":
    unittest.main()
