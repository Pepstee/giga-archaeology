from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.evidence import validate_self_hash
from modules.operations.archaeology.inventory import (
    InventoryError,
    InventoryPolicy,
    build_inventory,
    write_inventory,
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
    (root / "src").mkdir()
    (root / "src/app.py").write_text(
        "class Service:\n    def run(self):\n        return 1\n\ndef main():\n    return Service().run()\n",
        encoding="utf-8",
    )
    (root / "src/copy.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "src/copy_two.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname="fixture"\nversion="1"\n[project.scripts]\nfixture="src.app:main"\n',
        encoding="utf-8",
    )
    (root / "memory").mkdir()
    (root / "memory/private.txt").write_text(
        "SECRET-MUST-NOT-APPEAR\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def test_inventory_is_deterministic_self_hashed_and_observation_only(
    repository: Path,
) -> None:
    first = build_inventory(repository)
    second = build_inventory(repository)
    assert first == second
    validate_self_hash(first)
    assert first["authority"] == "read-only-observation"
    assert first["authority_granted"] is False
    assert first["cleanup_permitted"] is False
    assert first["repository"]["status"]["clean"] is True
    assert any(symbol["qualified_name"] == "Service.run" for symbol in first["symbols"])
    assert any(
        entry["target"] == "fixture=src.app:main"
        for entry in first["declared_entrypoints"]
    )
    assert any(
        group["paths"] == ["src/copy.py", "src/copy_two.py"]
        for group in first["exact_duplicates"]
    )


def test_sensitive_paths_are_hashed_as_exclusions_but_never_recorded(
    repository: Path,
) -> None:
    inventory = build_inventory(repository)
    rendered = json.dumps(inventory, ensure_ascii=False)
    assert "memory/private.txt" not in rendered
    assert "SECRET-MUST-NOT-APPEAR" not in rendered
    assert inventory["privacy"]["excluded_count"] == 1
    assert inventory["privacy"]["excluded_paths_recorded"] is False


def test_untracked_is_not_read_unless_explicitly_admitted(repository: Path) -> None:
    (repository / "src/new.py").write_text(
        "def new():\n    return 2\n", encoding="utf-8"
    )
    default = build_inventory(repository)
    assert "src/new.py" not in {item["path"] for item in default["files"]}
    admitted = build_inventory(
        repository, InventoryPolicy(admitted_untracked=("src/new.py",))
    )
    assert "src/new.py" in {item["path"] for item in admitted["files"]}
    assert any(item["qualified_name"] == "new" for item in admitted["symbols"])


def test_symlink_is_hashed_without_following_target(
    repository: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("OUTSIDE-CONTENT\n", encoding="utf-8")
    (repository / "src/link").symlink_to(outside)
    _git(repository, "add", "src/link")
    inventory = build_inventory(repository)
    record = next(item for item in inventory["files"] if item["path"] == "src/link")
    assert record["kind"] == "symlink"
    assert "OUTSIDE-CONTENT" not in json.dumps(inventory)


def test_output_is_external_create_once_and_repository_unchanged(
    repository: Path, tmp_path: Path
) -> None:
    before = _git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    output = tmp_path / "evidence"
    payload = write_inventory(repository, output)
    assert (
        json.loads((output / "inventory.json").read_text(encoding="utf-8")) == payload
    )
    assert (output / "INVENTORY_REPORT.md").is_file()
    assert stat_mode(output / "inventory.json") == 0o600
    assert (
        _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == before
    )
    with pytest.raises(InventoryError, match="must not already exist"):
        write_inventory(repository, output)


def test_output_inside_repository_and_missing_admission_refuse(
    repository: Path,
) -> None:
    with pytest.raises(InventoryError, match="outside"):
        write_inventory(repository, repository / "evidence")
    with pytest.raises(InventoryError, match="absent or ignored"):
        build_inventory(repository, InventoryPolicy(admitted_untracked=("missing.py",)))


def stat_mode(path: Path) -> int:
    return os.stat(path, follow_symlinks=False).st_mode & 0o777
