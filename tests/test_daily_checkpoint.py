from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from twin_core.daily_checkpoint import (
    DailyCheckpointError,
    begin_daily_checkpoint,
    complete_daily_checkpoint,
    report_daily_failure,
)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


class DailyCheckpointTests(unittest.TestCase):
    def repository(self, root: Path) -> None:
        git(root, "init", "-q")
        git(root, "config", "user.email", "gutu.artiom444@gmail.com")
        git(root, "config", "user.name", "Artiom Gutu")
        (root / "twin_core").mkdir()
        (root / "twin_core/example.py").write_text("# Index\n", encoding="utf-8")
        git(root, "add", "twin_core/example.py")
        git(root, "commit", "-qm", "baseline")

    def test_sanctioned_daily_changes_are_receipted_and_committed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.repository(root)
            baseline = begin_daily_checkpoint(
                root,
                run_id="run-1",
                write_set=("twin_core/example.py",),
                cleanup_lock=root / "absent.lock",
                require_upstream=False,
            )
            (root / "twin_core/example.py").write_text("# Updated\n", encoding="utf-8")
            result = complete_daily_checkpoint(
                baseline, day="2026-08-03", details={"provider": "test"}
            )
            self.assertEqual(result["result"], "committed")
            self.assertFalse(result["pushed"])
            self.assertEqual(git(root, "status", "--short"), "")
            self.assertEqual(
                git(root, "log", "-1", "--pretty=%s"),
                "daily: knowledge checkpoint 2026-08-03",
            )
            receipt = json.loads((root / result["receipt"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["parent_commit"], baseline.head)

    def test_dirty_baseline_and_out_of_scope_change_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.repository(root)
            (root / "README.md").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(DailyCheckpointError, "clean baseline"):
                begin_daily_checkpoint(root, run_id="dirty", write_set=("twin_core/example.py",), cleanup_lock=root / "absent.lock")
            (root / "README.md").unlink()
            baseline = begin_daily_checkpoint(
                root,
                run_id="run-2",
                write_set=("twin_core/example.py",),
                cleanup_lock=root / "absent.lock",
                require_upstream=False,
            )
            (root / "README.md").write_text("unexpected\n", encoding="utf-8")
            with self.assertRaisesRegex(DailyCheckpointError, "out-of-scope"):
                complete_daily_checkpoint(baseline, day="2026-08-03", details={}, push=False)
            self.assertEqual(git(root, "rev-parse", "HEAD"), baseline.head)

    def test_failure_report_is_external_and_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = report_daily_failure(
                run_id="failed-run",
                error=RuntimeError("injected"),
                destination=Path(folder),
            )
            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(report["result"], "failed")
            self.assertFalse(report["success_claim_allowed"])


class PortableCheckpointTests(unittest.TestCase):
    repository = DailyCheckpointTests.repository

    def begin(self, root, **kwargs):
        return begin_daily_checkpoint(root, run_id="synthetic", write_set=("twin_core/example.py",), cleanup_lock=root / "absent.lock", **kwargs)

    def test_private_and_broad_paths_are_rejected_before_hashing(self):
        from unittest.mock import patch
        for path in ("memory/INDEX.md", "runtime/generated/context/current.json", "twin_core/private/a.py", "twin_core/", ".", "../outside.py"):
            with tempfile.TemporaryDirectory() as folder, patch("twin_core.daily_checkpoint._sha256", side_effect=AssertionError("must not read")):
                root = Path(folder)
                with self.assertRaises(DailyCheckpointError):
                    begin_daily_checkpoint(root, run_id="denied", write_set=(path,))

    def test_symlink_parent_is_rejected_before_hashing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "elsewhere").mkdir()
            (root / "twin_core").symlink_to(root / "elsewhere", target_is_directory=True)
            with self.assertRaises(DailyCheckpointError):
                self.begin(root)

    def test_branch_change_at_same_head_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.repository(root)
            baseline = self.begin(root)
            git(root, "checkout", "-qb", "codex/other")
            with self.assertRaisesRegex(DailyCheckpointError, "branch changed"):
                complete_daily_checkpoint(baseline, day="2026-09-10", details={})

    def test_head_change_and_deletion_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.repository(root)
            baseline = self.begin(root)
            git(root, "commit", "--allow-empty", "-qm", "other")
            with self.assertRaisesRegex(DailyCheckpointError, "HEAD changed"):
                complete_daily_checkpoint(baseline, day="2026-09-10", details={})
            baseline = self.begin(root)
            (root / "twin_core/example.py").unlink()
            with self.assertRaisesRegex(DailyCheckpointError, "deletion"):
                complete_daily_checkpoint(baseline, day="2026-09-10", details={})

    def test_hash_drift_after_staging_refuses_commit(self):
        from unittest.mock import patch
        from twin_core import daily_checkpoint as checkpoint
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.repository(root)
            baseline = self.begin(root)
            (root / "twin_core/example.py").write_text("approved")
            original = checkpoint._git
            def changed(root, *args, **kwargs):
                result = original(root, *args, **kwargs)
                if args[0] == "add":
                    (root / "twin_core/example.py").write_text("changed after approval")
                    original(root, "add", "--", "twin_core/example.py")
                return result
            with patch.object(checkpoint, "_git", side_effect=changed):
                with self.assertRaisesRegex(DailyCheckpointError, "hash-approved"):
                    complete_daily_checkpoint(baseline, day="2026-09-10", details={})
            self.assertEqual(git(root, "rev-parse", "HEAD"), baseline.head)

    def test_opt_in_push_uses_exact_local_bare_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root, remote = base / "work", base / "remote.git"
            root.mkdir()
            self.repository(root)
            git(root, "checkout", "-qb", "codex/checkpoint")
            git(base, "init", "--bare", "-q", str(remote))
            git(root, "remote", "add", "origin", str(remote))
            git(root, "push", "-qu", "origin", "codex/checkpoint")
            baseline = self.begin(root, push_remote="origin", push_branch="codex/checkpoint")
            (root / "twin_core/example.py").write_text("approved technical change")
            result = complete_daily_checkpoint(baseline, day="2026-09-10", details={"synthetic": True}, push=True)
            self.assertTrue(result["pushed"])
            self.assertEqual(git(remote, "rev-parse", "refs/heads/codex/checkpoint"), result["commit"])
            self.assertEqual(git(root, "show", "-s", "--format=%an <%ae>"), "Artiom Gutu <gutu.artiom444@gmail.com>")

    def test_changed_push_binding_refuses_before_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root, remote = base / "work", base / "remote.git"
            root.mkdir()
            self.repository(root)
            git(root, "checkout", "-qb", "codex/checkpoint")
            git(base, "init", "--bare", "-q", str(remote))
            git(root, "remote", "add", "origin", str(remote))
            git(root, "push", "-qu", "origin", "codex/checkpoint")
            baseline = self.begin(root, push_remote="origin", push_branch="codex/checkpoint")
            git(root, "remote", "set-url", "origin", str(base / "different.git"))
            with self.assertRaisesRegex(DailyCheckpointError, "binding changed"):
                complete_daily_checkpoint(baseline, day="2026-09-10", details={}, push=True)
            self.assertEqual(git(root, "rev-parse", "HEAD"), baseline.head)


    def test_rename_status_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.repository(root)
            baseline = self.begin(root)
            git(root, "mv", "twin_core/example.py", "twin_core/renamed.py")
            with self.assertRaisesRegex(DailyCheckpointError, "rename/copy"):
                complete_daily_checkpoint(baseline, day="2026-09-10", details={})
            self.assertEqual(git(root, "rev-parse", "HEAD"), baseline.head)


if __name__ == "__main__":
    unittest.main()
