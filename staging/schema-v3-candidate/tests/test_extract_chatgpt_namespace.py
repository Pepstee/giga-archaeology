from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import extract_chatgpt


class ChatGPTNamespaceTests(unittest.TestCase):
    def test_namespace_produces_separate_views_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "export.zip"
            conversation = {
                "id": "conversation-1",
                "title": "Test",
                "current_node": "a",
                "mapping": {
                    "a": {"parent": None, "message": {
                        "author": {"role": "user"}, "create_time": 1_700_000_000,
                        "content": {"parts": ["hello"]}}},
                },
            }
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("conversations-000.json", json.dumps([conversation]))
            raw, transcripts = root / "raw", root / "transcripts"
            with patch.object(extract_chatgpt, "RAW", raw), patch.object(
                    extract_chatgpt, "TRANSCRIPTS", transcripts):
                prompt_path, transcript_path, _ = extract_chatgpt.extract(
                    archive, "20260719", "account2")
            self.assertEqual(prompt_path.name, "chatgpt_prompts_account2_20260719.jsonl")
            self.assertEqual(transcript_path.name, "chatgpt_conversations_account2.jsonl")
            record = json.loads(transcript_path.read_text().strip())
            self.assertEqual(record["export_namespace"], "account2")


if __name__ == "__main__":
    unittest.main()
