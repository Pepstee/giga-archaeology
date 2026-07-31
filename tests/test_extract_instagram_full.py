import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.extract_instagram_full import extract


class InstagramFullExtractorTests(unittest.TestCase):
    def test_preserves_both_directions_without_extracting_media(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = root / "instagram.zip"
            member = "your_instagram_activity/messages/inbox/friend_123/message_1.json"
            with ZipFile(package, "w") as archive:
                archive.writestr(member, json.dumps({
                    "title": "Friend",
                    "thread_path": "inbox/friend_123",
                    "participants": [{"name": "Artiom"}, {"name": "Friend"}],
                    "messages": [
                        {"sender_name": "Friend", "timestamp_ms": 1000, "content": "hi"},
                        {"sender_name": "Artiom", "timestamp_ms": 2000,
                         "content": "hello", "photos": [{"uri": "photos/x.jpg"}]},
                    ],
                }))
            output = root / "out.jsonl"
            manifest_path = root / "manifest.json"
            manifest = extract(
                package, output, manifest_path, "Artiom", "instagram_test"
            )
            rows = [json.loads(line) for line in output.read_text().splitlines()]

            self.assertEqual([row["direction"] for row in rows], ["incoming", "outgoing"])
            self.assertEqual(rows[1]["media"]["photos"][0]["uri"], "photos/x.jpg")
            self.assertEqual(manifest["records"], 2)
            self.assertEqual(manifest["direction_counts"], {"incoming": 1, "outgoing": 1})
            self.assertFalse(manifest["direct_sft_authorised"])


if __name__ == "__main__":
    unittest.main()
