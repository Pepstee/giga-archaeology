from __future__ import annotations

import json
import os
import sqlite3
import stat
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.evidence import validate_self_hash
from modules.operations.archaeology.navigation_inventory import (
    NavigationInventoryError,
    current_navigation_run,
    locate_navigation_inventory,
    refresh_navigation_inventory,
    refresh_navigation_inventory_delta,
    search_navigation_inventory,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


@pytest.fixture()
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src/main.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (root / "src/copy.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "src/copy-two.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "ignored").mkdir()
    (root / "ignored/cache.txt").write_text("cache\n", encoding="utf-8")
    (root / "memory").mkdir()
    (root / "memory/private.md").write_text("private fact\n", encoding="utf-8")
    _git(root, "add", ".gitignore", "src")
    _git(root, "commit", "-qm", "fixture")
    (root / "notes.md").write_text("untracked but useful\n", encoding="utf-8")
    return root


def _rows(run, query: str = "SELECT * FROM files ORDER BY path"):
    connection = sqlite3.connect(run.run_directory / "inventory.sqlite3")
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(query)]
    finally:
        connection.close()


def test_complete_inventory_covers_tracked_untracked_ignored_and_private_metadata(
    repository: Path, tmp_path: Path
) -> None:
    run = refresh_navigation_inventory(repository, tmp_path / "store")
    validate_self_hash(run.manifest)
    rows = {item["path"]: item for item in _rows(run)}
    assert set(rows) == {
        ".gitignore",
        "ignored/cache.txt",
        "memory/private.md",
        "notes.md",
        "src/copy-two.py",
        "src/copy.py",
        "src/main.py",
    }
    assert rows["src/main.py"]["git_status"] == "  "
    assert rows["notes.md"]["git_status"] == "??"
    assert rows["ignored/cache.txt"]["git_status"] == "!!"
    assert rows["memory/private.md"]["content_sha256"]
    assert rows["memory/private.md"]["semantic_eligible"] == 0
    assert rows["memory/private.md"]["semantic_reason"] == "sensitive-path"
    assert rows["notes.md"]["semantic_eligible"] == 1
    assert run.manifest["scan"]["control_exclusions"] == [
        {"path": ".git", "reason": "mutable Git control internals"}
    ]
    assert run.manifest["status"] == "CURRENT"


def test_commonjs_source_is_semantically_eligible_for_the_javascript_mapper(
    repository: Path, tmp_path: Path
) -> None:
    path = repository / "src/worker.cjs"
    path.write_text("module.exports = { answer: 42 };\n", encoding="utf-8")
    _git(repository, "add", "src/worker.cjs")
    _git(repository, "commit", "-qm", "add commonjs source")

    run = refresh_navigation_inventory(repository, tmp_path / "store")
    row = {item["path"]: item for item in _rows(run)}["src/worker.cjs"]
    assert row["semantic_eligible"] == 1
    assert row["semantic_reason"] == "eligible-local-only"


def test_symlink_is_hashed_without_following_and_special_file_is_recorded(
    repository: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.write_text("outside secret", encoding="utf-8")
    (repository / "link").symlink_to(outside)
    os.mkfifo(repository / "pipe")
    run = refresh_navigation_inventory(repository, tmp_path / "store")
    rows = {item["path"]: item for item in _rows(run)}
    assert rows["link"]["kind"] == "symlink"
    assert rows["link"]["content_sha256"]
    assert rows["pipe"]["kind"] == "fifo"
    assert rows["pipe"]["hash_status"] == "not_applicable"
    assert "outside secret" not in json.dumps(run.manifest)


def test_incremental_refresh_reuses_only_unchanged_hashes(
    repository: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    first = refresh_navigation_inventory(repository, store)
    (repository / "notes.md").write_text("changed\n", encoding="utf-8")
    second = refresh_navigation_inventory(repository, store)
    assert second.manifest["scan"]["incremental_from"] == first.manifest["run_id"]
    assert second.manifest["counts"]["reused"] == first.manifest["counts"]["files"] - 1
    assert second.manifest["counts"]["hashed"] == 1
    assert current_navigation_run(store).manifest["run_id"] == second.manifest["run_id"]


def test_commit_delta_refresh_is_fast_truthful_and_never_claims_full_currency(
    repository: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    first = refresh_navigation_inventory(repository, store)
    old_ignored_hash = {item["path"]: item["content_sha256"] for item in _rows(first)}[
        "ignored/cache.txt"
    ]

    (repository / "src/main.py").write_text(
        "def main():\n    return 2\n", encoding="utf-8"
    )
    (repository / "src/new.py").write_text("NEW = True\n", encoding="utf-8")
    (repository / "src/copy-two.py").unlink()
    _git(repository, "add", "src")
    _git(repository, "commit", "-qm", "material milestone")
    (repository / "notes.md").write_text("live dirty change\n", encoding="utf-8")
    (repository / "ignored/cache.txt").write_text(
        "uncovered ignored change\n", encoding="utf-8"
    )

    delta = refresh_navigation_inventory_delta(repository, store)
    validate_self_hash(delta.manifest)
    assert delta.manifest["status"] == "PARTIAL"
    assert delta.manifest["scan"]["scope"] == "commit-delta-and-live-git-status"
    assert delta.manifest["scan"]["incremental_from"] == first.manifest["run_id"]
    assert set(delta.manifest["scan"]["commit_paths"]) == {
        "src/copy-two.py",
        "src/main.py",
        "src/new.py",
    }
    assert delta.manifest["scan"]["unverified_surfaces"] == [
        "ignored-file-content-outside-refreshed-paths",
        "directory-membership-outside-git-visible-paths",
    ]
    rows = {item["path"]: item for item in _rows(delta)}
    assert "src/copy-two.py" not in rows
    assert (
        rows["src/main.py"]["content_sha256"]
        != {item["path"]: item["content_sha256"] for item in _rows(first)}[
            "src/main.py"
        ]
    )
    assert rows["src/new.py"]["git_tracked"] == 1
    assert rows["notes.md"]["git_status"] == "??"
    # The ignored file was deliberately outside the Git-visible delta.  Its old
    # row is preserved, and PARTIAL makes that uncovered surface explicit.
    assert rows["ignored/cache.txt"]["content_sha256"] == old_ignored_hash
    assert current_navigation_run(store).manifest["status"] == "PARTIAL"


def test_delta_refresh_reuses_current_when_commit_and_status_are_unchanged(
    repository: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    first = refresh_navigation_inventory(repository, store)
    second = refresh_navigation_inventory_delta(repository, store)
    assert second.manifest["run_id"] == first.manifest["run_id"]
    assert second.manifest["status"] == "CURRENT"


def test_delta_refresh_detects_new_bytes_when_dirty_status_text_is_unchanged(
    repository: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    refresh_navigation_inventory(repository, store)
    target = repository / "src/main.py"
    target.write_text("def main():\n    return 2\n", encoding="utf-8")
    first_dirty = refresh_navigation_inventory_delta(repository, store)
    first_row = {item["path"]: item for item in _rows(first_dirty)}["src/main.py"]

    target.write_text("def main():\n    return 3\n", encoding="utf-8")
    second_dirty = refresh_navigation_inventory_delta(repository, store)
    second_row = {item["path"]: item for item in _rows(second_dirty)}["src/main.py"]

    assert second_dirty.reused_current is False
    assert second_dirty.manifest["run_id"] != first_dirty.manifest["run_id"]
    assert second_row["content_sha256"] != first_row["content_sha256"]


def test_scoped_delta_reuses_only_after_exact_live_path_verification(
    repository: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    first = refresh_navigation_inventory(repository, store)
    second = refresh_navigation_inventory_delta(
        repository, store, include_paths=("src/main.py",)
    )
    assert second.manifest["run_id"] == first.manifest["run_id"]
    assert second.reused_current is True
    assert second.verified_live_paths == ("src/main.py",)

    (repository / "src/main.py").chmod(0o600)
    changed = refresh_navigation_inventory_delta(
        repository, store, include_paths=("src/main.py",)
    )
    assert changed.manifest["run_id"] != first.manifest["run_id"]
    assert changed.reused_current is False
    assert changed.verified_live_paths == ()
    row = {item["path"]: item for item in _rows(changed)}["src/main.py"]
    assert row["mode"] == 0o600


def test_scoped_delta_content_drift_never_reuses_authenticated_inventory(
    repository: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    first = refresh_navigation_inventory(repository, store)
    (repository / "ignored/cache.txt").write_text(
        "new ignored bytes\n", encoding="utf-8"
    )
    changed = refresh_navigation_inventory_delta(
        repository, store, include_paths=("ignored/cache.txt",)
    )
    assert changed.manifest["run_id"] != first.manifest["run_id"]
    assert changed.reused_current is False
    row = {item["path"]: item for item in _rows(changed)}["ignored/cache.txt"]
    assert (
        row["content_sha256"]
        != {item["path"]: item["content_sha256"] for item in _rows(first)}[
            "ignored/cache.txt"
        ]
    )


def test_logical_row_digest_is_stable_across_full_and_incremental_refresh(
    repository: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    first = refresh_navigation_inventory(repository, store)
    second = refresh_navigation_inventory(repository, store)
    assert (
        first.manifest["database"]["row_digest_sha256"]
        == second.manifest["database"]["row_digest_sha256"]
    )
    assert second.manifest["counts"]["hashed"] == 0
    assert second.manifest["counts"]["reused"] == first.manifest["counts"]["files"]


def test_duplicate_groups_and_path_search_are_queryable(
    repository: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    run = refresh_navigation_inventory(repository, store)
    groups = _rows(run, "SELECT * FROM duplicate_groups")
    assert any(item["copies"] == 2 for item in groups)
    results = search_navigation_inventory(store, "main.py")
    assert results[0]["path"] == "src/main.py"
    assert search_navigation_inventory(store, "memory", semantic_only=True) == []


def test_inventory_publishes_exact_ordered_git_status_entries(
    repository: Path, tmp_path: Path
) -> None:
    _git(repository, "mv", "src/main.py", "src/renamed.py")
    run = refresh_navigation_inventory(repository, tmp_path / "store")
    rows = _rows(
        run,
        """SELECT phase,ordinal,code,path,secondary_path
           FROM git_status_entries ORDER BY phase,ordinal""",
    )
    before = [item for item in rows if item["phase"] == "before"]
    after = [item for item in rows if item["phase"] == "after"]
    assert before == [dict(item, phase="before") for item in after]
    rename = next(item for item in before if "R" in item["code"])
    assert {rename["path"], rename["secondary_path"]} == {
        "src/main.py",
        "src/renamed.py",
    }
    assert run.manifest["git"]["before"]["entries"] == len(before)
    assert run.manifest["git"]["before"]["entries_sha256"]
    assert run.manifest["database"]["git_status_row_digest_sha256"]


def test_locator_distinguishes_tracked_source_from_history_and_binds_repository(
    repository: Path, tmp_path: Path
) -> None:
    nested = repository / "jaa-runtime"
    nested.mkdir()
    _git(nested, "init", "-q")
    _git(nested, "config", "user.name", "Fixture")
    _git(nested, "config", "user.email", "<redacted-email>")
    (nested / "src").mkdir()
    (nested / "src/application_compiler.py").write_text(
        "class ApplicationCompiler:\n    pass\n", encoding="utf-8"
    )
    _git(nested, "add", ".")
    _git(nested, "commit", "-qm", "nested fixture")
    archive = repository / "archive"
    archive.mkdir()
    (archive / "application_compiler.py").write_text("old = True\n", encoding="utf-8")
    store = tmp_path / "store"
    refresh_navigation_inventory(repository, store)
    result = locate_navigation_inventory(store, "application_compiler.py")
    validate_self_hash(result)
    by_path = {item["path"]: item for item in result["results"]}
    active = by_path["jaa-runtime/src/application_compiler.py"]
    assert active["role"] == "CANONICAL_SOURCE_CANDIDATE"
    assert active["canonicality_claimed"] is False
    assert active["repository"]["root"] == "jaa-runtime"
    assert active["repository"]["tracked"] is True
    assert active["source"]["live_matches_inventory"] is True
    assert by_path["archive/application_compiler.py"]["role"] == (
        "HISTORICAL_OR_ARCHIVED_COPY"
    )


def test_locator_ignores_unborn_nested_repository_candidate(
    repository: Path, tmp_path: Path
) -> None:
    abandoned = repository / "abandoned"
    abandoned.mkdir()
    _git(abandoned, "init", "-q")
    (abandoned / "application_notes.md").write_text("notes\n", encoding="utf-8")
    store = tmp_path / "store"
    refresh_navigation_inventory(repository, store)
    result = locate_navigation_inventory(store, "application")
    row = next(
        item for item in result["results"] if item["path"].startswith("abandoned/")
    )
    assert row["repository"]["root"] == "."
    assert row["role"] == "UNTRACKED_WORKING_COPY"


def test_publication_is_external_private_atomic_and_current_is_authenticated(
    repository: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    before = _git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    run = refresh_navigation_inventory(repository, store)
    assert stat.S_IMODE(store.stat().st_mode) == 0o700
    assert stat.S_IMODE((store / "CURRENT.json").stat().st_mode) == 0o600
    assert (
        stat.S_IMODE((run.run_directory / "inventory.sqlite3").stat().st_mode) == 0o600
    )
    assert (
        _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == before
    )
    pointer = json.loads((store / "CURRENT.json").read_text(encoding="utf-8"))
    validate_self_hash(pointer)
    assert current_navigation_run(store).manifest == run.manifest
    database = run.run_directory / "inventory.sqlite3"
    raw = database.read_bytes()
    database.write_bytes(raw + b"tamper")
    with pytest.raises(NavigationInventoryError, match="database hash mismatch"):
        current_navigation_run(store)


def test_failed_refresh_preserves_previous_current(
    repository: Path, tmp_path: Path, monkeypatch
) -> None:
    store = tmp_path / "store"
    first = refresh_navigation_inventory(repository, store)

    def fail(*_args, **_kwargs):
        raise NavigationInventoryError("injected scan failure")

    monkeypatch.setattr(
        "modules.operations.archaeology.navigation_inventory._tracked_files", fail
    )
    with pytest.raises(NavigationInventoryError, match="injected"):
        refresh_navigation_inventory(repository, store)
    assert current_navigation_run(store).manifest["run_id"] == first.manifest["run_id"]
    assert not list(store.glob(".staging-*"))


def test_store_inside_root_and_unsafe_store_refuse(
    repository: Path, tmp_path: Path
) -> None:
    with pytest.raises(NavigationInventoryError, match="outside"):
        refresh_navigation_inventory(repository, repository / "generated")
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir(mode=0o755)
    with pytest.raises(NavigationInventoryError, match="mode 0700"):
        refresh_navigation_inventory(repository, unsafe)


def test_invalid_search_parameters_refuse(repository: Path, tmp_path: Path) -> None:
    store = tmp_path / "store"
    refresh_navigation_inventory(repository, store)
    with pytest.raises(NavigationInventoryError, match="query"):
        search_navigation_inventory(store, "")
    with pytest.raises(NavigationInventoryError, match="limit"):
        search_navigation_inventory(store, "src", limit=0)


def test_explicit_scope_never_opens_excluded_dirty_or_untracked_content(
    repository: Path, tmp_path: Path, monkeypatch
) -> None:
    from modules.operations.archaeology import navigation_inventory as module
    _git(repository, "add", "memory/private.md")
    _git(repository, "commit", "-qm", "private fixture")
    (repository / "memory/private.md").write_text("changed private fixture")
    original_open = os.open
    opened = []

    def guarded_open(path, flags, *args, **kwargs):
        opened.append(str(path))
        assert "private.md" not in str(path)
        assert "notes.md" not in str(path)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", guarded_open)
    monkeypatch.setattr(module, "_status_snapshot", lambda *a: pytest.fail("unscoped Git status"))
    monkeypatch.setattr(module, "_walk_files", lambda *a: pytest.fail("whole-root walk"))
    run = refresh_navigation_inventory(repository, tmp_path / "scoped", include_paths=["src/main.py"])
    assert [row["path"] for row in _rows(run)] == ["src/main.py"]
    assert run.manifest["status"] == "PARTIAL"
    assert run.manifest["scan"]["scope"] == "explicit-file-allowlist"
    assert run.manifest["scan"]["included_paths"] == ["src/main.py"]
    assert "all-content-outside-included-paths" in run.manifest["scan"]["unverified_surfaces"]
    with pytest.raises(NavigationInventoryError, match="delta is unsupported"):
        refresh_navigation_inventory_delta(repository, tmp_path / "scoped", include_paths=["src/main.py"])
    assert opened


@pytest.mark.parametrize("scope", [["src"], ["alias/main.py"], ["src/link.py"], ["../outside"]])
def test_explicit_scope_refuses_directories_and_symlink_components(repository, tmp_path, scope):
    (repository / "alias").symlink_to(repository / "src", target_is_directory=True)
    (repository / "src/link.py").symlink_to(repository / "memory/private.md")
    with pytest.raises((NavigationInventoryError, OSError)):
        refresh_navigation_inventory(repository, tmp_path / "scoped", include_paths=scope)
    assert not (tmp_path / "scoped/CURRENT.json").exists()


def test_scoped_mapper_never_collects_historical_blobs(repository, tmp_path, monkeypatch):
    from modules.operations.archaeology import mapper
    refresh_navigation_inventory(repository, tmp_path / "scoped", include_paths=["src/main.py"])
    monkeypatch.setattr(mapper, "collect_recent_lineage", lambda *a, **k: pytest.fail("historical blob expansion"))
    run = mapper.refresh_mapper(tmp_path / "scoped", tmp_path / "mapper")
    assert run.manifest["status"] == "PARTIAL"
    connection = sqlite3.connect(run.run_directory / "facts.sqlite3")
    try:
        rows = connection.execute("SELECT * FROM coverage WHERE map_id='git_lineage'").fetchall()
        assert "historical-content-excluded-by-explicit-file-scope" in str(rows)
    finally:
        connection.close()
