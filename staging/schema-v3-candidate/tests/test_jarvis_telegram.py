from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import jarvis_telegram as jarvis
from twin_core import provider_adapters
from twin_core.store import TwinStore


class JarvisTelegramTests(unittest.TestCase):
    def test_claude_worker_has_no_tools_write_or_bypass(self) -> None:
        commands = []
        original = provider_adapters._run

        def fake(cmd, *, cwd, timeout):
            commands.append(cmd)
            return '{"schema_version":1,"reply":"ok","operations":[]}'

        provider_adapters._run = fake
        try:
            proposal = provider_adapters.claude_proposal("instructions", cwd=Path("."))
        finally:
            provider_adapters._run = original
        self.assertIsNotNone(proposal)
        command = commands[0]
        self.assertIn("--tools=", command)
        self.assertIn("--json-schema", command)
        self.assertNotIn("--dangerously-skip-permissions", command)

    def test_capture_is_idempotent_and_keeps_message_in_secure_store(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = TwinStore(Path(folder) / "private" / "twin.sqlite3")
            update = {
                "update_id": 42,
                "message": {"message_id": 7, "date": 1784510000, "text": "remember this"},
            }
            first = jarvis._capture_update(store, update)
            replay = jarvis._capture_update(store, update)
            self.assertTrue(first[1])
            self.assertFalse(replay[1])
            self.assertEqual(first[0], replay[0])
            self.assertEqual(store.counts()["events"], 1)
            self.assertEqual(store.counts()["receipts"], 1)

    def test_offset_write_is_atomic_shape_and_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "private" / "offset.json"
            jarvis._save_offset(path, 99)
            self.assertEqual(json.loads(path.read_text()), {"offset": 99})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
