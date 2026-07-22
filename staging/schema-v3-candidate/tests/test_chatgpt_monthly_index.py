from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import chatgpt_monthly_index


class ChatGPTMonthlyIndexTests(unittest.TestCase):
    def test_build_index_preserves_gaps_and_locators_without_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "transcript.jsonl"
            records = [
                {
                    "ts": "2023-03-26T01:00:00Z",
                    "text": "private first text",
                    "conversation": "First",
                    "conv_uuid": "a",
                    "sender": "human",
                    "export_namespace": "gpt2_2026",
                },
                {
                    "ts": "2023-03-26T01:01:00Z",
                    "text": "private reply",
                    "conversation": "First",
                    "conv_uuid": "a",
                    "sender": "assistant",
                    "export_namespace": "gpt2_2026",
                },
                {
                    "ts": "2023-05-01T00:00:00Z",
                    "text": "later private text",
                    "conversation": "Later",
                    "conv_uuid": "b",
                    "sender": "human",
                    "export_namespace": "gpt2_2026",
                },
            ]
            path.write_text("\n".join(json.dumps(item) for item in records) + "\n")

            index = chatgpt_monthly_index.build_index(path)
            self.assertEqual([item["month"] for item in index["months"]],
                             ["2023-03", "2023-04", "2023-05"])
            self.assertEqual(index["months"][1]["status"], "gap")
            first = index["months"][0]["conversations"][0]
            self.assertEqual((first["line_start"], first["line_end"]), (1, 2))
            rendered = chatgpt_monthly_index.markdown(index)
            self.assertNotIn("private first text", rendered)
            self.assertIn("No retained timestamped text turns", rendered)


if __name__ == "__main__":
    unittest.main()
