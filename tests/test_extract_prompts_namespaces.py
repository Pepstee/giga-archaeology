from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import extract_prompts


class PromptNamespaceTests(unittest.TestCase):
    def test_newest_snapshot_from_each_namespace_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = {
                "chatgpt_prompts_20260718.jsonl": [{"text": "old default"}],
                "chatgpt_prompts_20260719.jsonl": [{"text": "new default"}],
                "chatgpt_prompts_gpt2_2026_20260718.jsonl": [{"text": "old second"}],
                "chatgpt_prompts_gpt2_2026_20260720.jsonl": [{"text": "new second"}],
            }
            for name, values in records.items():
                (root / name).write_text("\n".join(json.dumps(v) for v in values) + "\n")
            output: list[dict] = []
            with patch.object(extract_prompts, "OUT", root):
                count = extract_prompts._extract_chatgpt_snapshot(
                    output, {"default", "gpt2_2026"})
            self.assertEqual(count, 2)
            self.assertEqual({item["text"] for item in output}, {"new default", "new second"})
            self.assertEqual({item["export_namespace"] for item in output},
                             {"default", "gpt2_2026"})

    def test_unapproved_namespace_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "chatgpt_prompts_20260720.jsonl").write_text(
                json.dumps({"text": "operator"}) + "\n")
            (root / "chatgpt_prompts_gpt2_2026_20260720.jsonl").write_text(
                json.dumps({"text": "mixed account"}) + "\n")
            output: list[dict] = []
            with patch.object(extract_prompts, "OUT", root), patch.object(
                    extract_prompts, "CHATGPT_NAMESPACE_POLICY", root / "missing.json"):
                count = extract_prompts._extract_chatgpt_snapshot(output)
            self.assertEqual(count, 1)
            self.assertEqual(output[0]["text"], "operator")
            self.assertEqual(output[0]["export_namespace"], "default")

    def test_deduplication_preserves_identical_cross_account_records(self) -> None:
        common = {
            "ts": "2026-01-01T00:00:00Z",
            "text": "same retained message",
            "channel": "chatgpt-web",
        }
        records = [
            {**common, "export_namespace": "default", "session": "first"},
            {**common, "export_namespace": "gpt2_2026", "session": "second"},
            {**common, "export_namespace": "gpt2_2026", "session": "second"},
        ]
        output = extract_prompts._deduplicate_records(records)
        self.assertEqual(len(output), 2)
        self.assertEqual({item["export_namespace"] for item in output},
                         {"default", "gpt2_2026"})

    def test_deduplication_preserves_distinct_chatgpt_conversations(self) -> None:
        common = {
            "ts": "2026-01-01T00:00:00Z",
            "text": "same shared message",
            "channel": "chatgpt-web",
            "export_namespace": "gpt2_2026",
        }
        records = [
            {**common, "session": "conversation-a"},
            {**common, "session": "conversation-b"},
            {**common, "session": "conversation-b"},
        ]
        output = extract_prompts._deduplicate_records(records)
        self.assertEqual(len(output), 2)
        self.assertEqual({item["session"] for item in output},
                         {"conversation-a", "conversation-b"})


if __name__ == "__main__":
    unittest.main()
