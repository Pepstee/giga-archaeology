from __future__ import annotations

import plistlib
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_daily_launcher_targets_canonical_non_worktree_owner() -> None:
    path = ROOT / "deploy/launchd/com.artiom.giga-navigation-maintenance.plist"
    payload = plistlib.loads(path.read_bytes())
    arguments = payload["ProgramArguments"]
    assert payload["Label"] == "com.artiom.giga-navigation-maintenance"
    assert (
        "/Users/admin/Documents/giga-user/modules/operations/scripts/archaeologist.py" in arguments
    )
    assert "navigation-maintenance" in arguments
    assert arguments[arguments.index("--max-new-documents") + 1] == "1"
    assert all("worktrees" not in value for value in arguments)


def test_post_commit_launcher_hands_off_to_loaded_daily_service() -> None:
    path = ROOT / "deploy/git-hooks/post-commit.navigation"
    text = path.read_text(encoding="utf-8")
    assert stat.S_IMODE(path.stat().st_mode) == 0o755
    assert "/usr/bin/git rev-parse --show-toplevel" in text
    assert '[ "$GIGA_NAV_ROOT" = "/Users/admin/Documents/giga-user" ] || exit 0' in text
    assert "/bin/launchctl kickstart" in text
    assert "gui/$(/usr/bin/id -u)/com.artiom.giga-navigation-maintenance" in text
    assert "nohup " not in text
    assert "navigation-maintenance" in text
    assert "worktrees" not in text
    assert text.rstrip().endswith("exit 0")
