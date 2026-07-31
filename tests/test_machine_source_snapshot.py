from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.capture_machine_source_snapshot import (
    SnapshotError,
    _write_immutable,
    bind_pair,
    capture,
    capture_tree,
    manifest_digest,
    verify_snapshot,
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def _registry(path: Path, mac_root: Path, gutua_root: Path) -> Path:
    document = {
        "schema": "giga.machine-authority.v1",
        "policy_id": "test.policy.v1",
        "authority": {"canonical_host": "mac"},
        "hosts": {
            "mac": {
                "role": "canonical",
                "roots": [
                    {
                        "id": "repo",
                        "path": str(mac_root),
                        "kind": "git",
                        "purpose": "test",
                    }
                ],
            },
            "gutua": {
                "role": "candidate_source",
                "roots": [
                    {
                        "id": "tree",
                        "path": str(gutua_root),
                        "kind": "tree",
                        "purpose": "test",
                        "excludes": ["cache"],
                    }
                ],
            },
        },
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_git_snapshot_binds_refs_and_dirty_content(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "base")
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("candidate\n", encoding="utf-8")

    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "source.txt").write_text("source\n", encoding="utf-8")
    registry = _registry(tmp_path / "registry.json", repo, tree)
    document = capture(registry, "mac")

    root = document["roots"][0]
    assert root["git"]["head"] == _git(repo, "rev-parse", "HEAD")
    assert root["git"]["refs"]
    assert root["git"]["dirty_worktree_count"] == 1
    paths = {
        item["path"]
        for item in root["git"]["worktrees"][0]["dirty_entries"]
    }
    assert paths == {"tracked.txt", "untracked.txt"}
    assert document["manifest_digest"] == manifest_digest(document)


def test_tree_snapshot_declares_and_applies_exclusions(tmp_path: Path) -> None:
    (tmp_path / "keep").mkdir()
    (tmp_path / "keep" / "source.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "ignored.bin").write_bytes(b"x")

    result = capture_tree(tmp_path, ["cache"])

    assert result["excludes"] == ["cache"]
    assert {item["path"] for item in result["entries"]} == {
        "keep",
        "keep/source.py",
    }


def test_immutable_snapshot_refuses_different_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    first = {"schema": "test", "manifest_digest": "a"}
    _write_immutable(path, first)
    path.chmod(0o644)

    with pytest.raises(SnapshotError, match="immutable snapshot already exists"):
        _write_immutable(path, {"schema": "test", "manifest_digest": "b"})


def test_verify_detects_tampering(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "file.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "base")
    tree = tmp_path / "tree"
    tree.mkdir()
    registry = _registry(tmp_path / "registry.json", repo, tree)
    document = capture(registry, "mac")
    output = tmp_path / "snapshot.json"
    _write_immutable(output, document)
    assert verify_snapshot(output)["ok"] is True

    output.chmod(0o644)
    changed = json.loads(output.read_text(encoding="utf-8"))
    changed["host"]["role"] = "candidate_source"
    output.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(SnapshotError, match="seal mismatch"):
        verify_snapshot(output)


def test_pair_grants_no_promotion_or_deletion_authority(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "file.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "base")
    tree = tmp_path / "tree"
    tree.mkdir()
    registry = _registry(tmp_path / "registry.json", repo, tree)

    mac_path = tmp_path / "mac.json"
    gutua_path = tmp_path / "gutua.json"
    _write_immutable(mac_path, capture(registry, "mac"))
    _write_immutable(gutua_path, capture(registry, "gutua"))
    pair = bind_pair(registry, mac_path, gutua_path)

    assert pair["canonical_host"] == "mac"
    assert pair["promotion_authority_granted"] is False
    assert pair["deletion_authority_granted"] is False
    assert pair["comparison_performed"] is False
