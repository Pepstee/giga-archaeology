from __future__ import annotations

import subprocess
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import daily_personal_knowledge


class ReadonlyWorkerTests(unittest.TestCase):
    @patch("scripts.daily_personal_knowledge.shutil.which")
    @patch("scripts.daily_personal_knowledge.subprocess.run")
    def test_claude_worker_disables_tools_without_swallowing_prompt(self, run, which) -> None:
        which.side_effect = lambda name: "/usr/local/bin/claude" if name == "claude" else None
        run.return_value = subprocess.CompletedProcess([], 0, stdout='{"predictions":[]}', stderr="")
        result = daily_personal_knowledge.run_readonly_worker("UNTRUSTED PROMPT BODY")
        self.assertEqual(result, ("Claude", '{"predictions":[]}'))
        command = run.call_args.args[0]
        self.assertIn("--tools=", command)
        self.assertEqual(command[-2:], ["--", "UNTRUSTED PROMPT BODY"])
        self.assertNotIn("--dangerously-skip-permissions", command)

    @patch("scripts.daily_personal_knowledge.shutil.which")
    @patch("scripts.daily_personal_knowledge.subprocess.run")
    def test_codex_fallback_is_read_only_and_allows_non_git_root(self, run, which) -> None:
        which.side_effect = lambda name: "/usr/local/bin/codex" if name == "codex" else None
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="unavailable")
        with patch("pathlib.Path.read_text", return_value='{"predictions":[]}'):
            daily_personal_knowledge.run_readonly_worker("prompt")
        command = run.call_args.args[0]
        self.assertIn("read-only", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_delta_prioritises_fresh_records_and_is_run_addressed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            snapshot = root / "prompts.jsonl"
            old = {"ts": "2023-01-01T00:00:00Z", "text": "old backfill", "source": "chatgpt"}
            fresh = {"ts": "2026-07-20T08:00:00Z", "text": "fresh event", "source": "codex"}
            snapshot.write_text(
                json.dumps(old) + "\n" + json.dumps(fresh) + "\n", encoding="utf-8"
            )
            inbox = root / "inbox"
            with patch.object(daily_personal_knowledge, "INBOX", inbox):
                path, fingerprints, backlog = daily_personal_knowledge.make_delta(
                    snapshot, set(), last_success="2026-07-20"
                )
            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(records[0]["text"], "fresh event")
            self.assertEqual(backlog, 2)
            self.assertEqual(len(fingerprints), 2)
            self.assertRegex(path.name, r"daily_delta_\d{4}-\d{2}-\d{2}_[0-9a-f]{12}\.jsonl")
