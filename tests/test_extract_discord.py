import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.extract_discord import extract


class DiscordExtractorTests(unittest.TestCase):
    def make_export(self, root: Path) -> Path:
        package = root / "package.zip"
        with ZipFile(package, "w") as archive:
            archive.writestr("README.txt", "Discord export")
            archive.writestr("Messages/index.json", json.dumps({"123": "Direct Message with X"}))
            archive.writestr("Messages/c123/channel.json", json.dumps({
                "id": "123", "type": "DM", "recipients": ["1", "2"]
            }))
            archive.writestr("Messages/c123/messages.json", json.dumps([
                {"ID": 2, "Timestamp": "2023-01-02 03:04:05", "Contents": "hello",
                 "Attachments": ""},
                {"ID": 1, "Timestamp": "2022-12-31 23:59:59", "Contents": "",
                 "Attachments": "https://cdn.example/x/private.png?token=secret"},
            ]))
            archive.writestr("Account/user.json", json.dumps({"email": "private@example.com"}))
        return package

    def test_extracts_messages_without_account_or_signed_urls(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = self.make_export(root)
            output = root / "messages.jsonl"
            manifest_path = root / "manifest.json"
            manifest = extract(package, output, manifest_path, "primary")
            rows = [json.loads(line) for line in output.read_text().splitlines()]

            self.assertEqual([row["message_id"] for row in rows], ["1", "2"])
            self.assertEqual(rows[0]["attachments"], [{"extension": ".png", "name": "private.png"}])
            self.assertNotIn("token=secret", output.read_text())
            self.assertNotIn("private@example.com", output.read_text())
            self.assertEqual(rows[0]["sender_scope"], "operator_account_outgoing")
            self.assertEqual(rows[0]["composition_status"], "unverified")
            self.assertEqual(manifest["records"], 2)
            self.assertEqual(manifest["empty_content_records"], 1)
            self.assertFalse(manifest["direct_sft_authorised"])

    def test_rejects_invalid_namespace(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError):
                extract(self.make_export(root), root / "out", root / "manifest", "Bad Namespace")


if __name__ == "__main__":
    unittest.main()
