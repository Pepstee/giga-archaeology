from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import jarvis_telegram as jarvis
from twin_core import provider_adapters
from twin_core.store import TwinStore


class JarvisTelegramTests(unittest.TestCase):
    def test_shadow_route_builds_bounded_request_without_authority(self) -> None:
        captured = {}

        def fake(root, request):
            captured["root"] = root
            captured["request"] = request
            return {"decision": "proposal-only", "execution_authorized": False}

        with patch("scripts.jarvis_telegram.decide_route", side_effect=fake):
            decision = jarvis._shadow_route("event-1", "bounded prompt")
        self.assertEqual(decision["decision"], "proposal-only")
        request = captured["request"]
        self.assertEqual(request["caller_id"], jarvis.ROUTE_CALLER)
        self.assertEqual(request["requested_authority"], "A0")
        self.assertEqual(request["max_tokens"], 4096)
        self.assertEqual(request["timeout_seconds"], jarvis.CLAUDE_TIMEOUT_S)

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


def test_public_update_refuses_before_provider(tmp_path):
    import pytest
    from twin_core.constitutional_authority import AuthorityRefused
    store = TwinStore(tmp_path / "private" / "twin.sqlite3")
    update = {"update_id": 43, "message": {"message_id": 8, "date": 1784510000, "text": "synthetic technical fixture"}}
    with patch("scripts.jarvis_telegram._worker") as worker:
        with pytest.raises(AuthorityRefused, match="HOST_BOUND_CORPUS_ACTIVATION_REQUIRED"):
            jarvis._process_update(store, update)
        worker.assert_not_called()
    # Capture precedes public processing refusal. Do not claim all effects blocked.
    assert store.counts()["events"] == 1
