from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.counterevidence import write_counterevidence
from modules.operations.archaeology.evidence import (
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
)
from modules.operations.archaeology.history import (
    HistoryError,
    _path_changes,
    write_history,
)
from modules.operations.archaeology.hypotheses import HYPOTHESES_SCHEMA
from modules.operations.archaeology.inventory import write_inventory


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def _repository(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.name", "Fixture")
    _git(path, "config", "user.email", "<redacted-email>")
    return path


@pytest.fixture()
def evidence(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    primary = _repository(tmp_path / "primary")
    (primary / "src").mkdir()
    (primary / "src/app.py").write_text(
        "def candidate():\n    return 1\n", encoding="utf-8"
    )
    (primary / "src/orphan.py").write_text(
        "def orphan():\n    return 0\n", encoding="utf-8"
    )
    _git(primary, "add", ".")
    _git(primary, "commit", "-qm", "initial")
    (primary / "src/app.py").write_text(
        "def candidate():\n    return 2\n", encoding="utf-8"
    )
    _git(primary, "add", "src/app.py")
    _git(primary, "commit", "-qm", "change capability")

    comparison = _repository(tmp_path / "comparison")
    (comparison / "legacy").mkdir()
    (comparison / "legacy/app.py").write_text(
        "def candidate():\n    return 3\n", encoding="utf-8"
    )
    _git(comparison, "add", ".")
    _git(comparison, "commit", "-qm", "parallel version")

    inventory_dir = tmp_path / "inventory"
    inventory = write_inventory(primary, inventory_dir)
    inventory_path = inventory_dir / "inventory.json"
    inventory_raw = inventory_path.read_bytes()

    def finding(path: str, name: str) -> dict[str, object]:
        identity = {
            "tool": "vulture",
            "kind": "python-unused-observation",
            "paths": [path],
            "detail": {"line": 1, "message": f"unused function '{name}'"},
        }
        return {
            "id": sha256_bytes(canonical_bytes(identity)),
            **identity,
            "state": "OBSERVED",
            "authority_granted": False,
            "cleanup_permitted": False,
        }

    findings = [finding("src/app.py", "candidate"), finding("src/orphan.py", "orphan")]
    hypotheses = seal_document(
        {
            "schema": HYPOTHESES_SCHEMA,
            "authority": "read-only-observation",
            "authority_granted": False,
            "cleanup_permitted": False,
            "inventory": {
                "path": str(inventory_path),
                "file_sha256": sha256_bytes(inventory_raw),
                "receipt_sha256": inventory["receipt_sha256"],
                "repository_head": inventory["repository"]["head"],
                "repository_tree": inventory["repository"]["tree"],
            },
            "projection": {
                "files": 2,
                "path_list_sha256": "a" * 64,
                "persisted": False,
                "source_unchanged": True,
            },
            "tools": [],
            "findings": findings,
            "summary": {
                "observations": 2,
                "tools_passed": 0,
                "tools_not_passed": 0,
                "states": {"OBSERVED": 2},
            },
        }
    )
    hypotheses_path = tmp_path / "hypotheses.json"
    hypotheses_path.write_bytes(canonical_bytes(hypotheses))
    counter_dir = tmp_path / "counterevidence"
    write_counterevidence(inventory_path, hypotheses_path, counter_dir)
    return (
        primary,
        comparison,
        inventory_path,
        hypotheses_path,
        counter_dir / "counterevidence.json",
    )


def test_history_and_parallel_repo_are_preservation_evidence(
    evidence: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    primary, comparison, inventory_path, hypotheses_path, counter_path = evidence
    primary_before = _git(primary, "status", "--porcelain=v1", "--untracked-files=all")
    comparison_before = _git(
        comparison, "status", "--porcelain=v1", "--untracked-files=all"
    )
    output = tmp_path / "history"
    payload = write_history(
        inventory_path, hypotheses_path, counter_path, comparison, output
    )
    validate_self_hash(payload)
    paths = {item["path"]: item for item in payload["path_evidence"]}
    assert paths["src/app.py"]["state"] == "RELATED_VARIANT_OBSERVED"
    assert len(paths["src/app.py"]["historical_versions"]) == 2
    assert paths["src/app.py"]["comparison_matches"] == [
        {
            "path": "legacy/app.py",
            "blob_oid": paths["src/app.py"]["comparison_matches"][0]["blob_oid"],
            "relation": "RELATED_BASENAME_DIFFERENT_BLOB",
        }
    ]
    orphan_record = next(
        item
        for item in payload["records"]
        if item["paths"][0]["path"] == "src/orphan.py"
    )
    assert orphan_record["historical_state"] == "UNKNOWN"
    assert payload["authority_granted"] is False
    assert payload["cleanup_permitted"] is False
    assert (
        _git(primary, "status", "--porcelain=v1", "--untracked-files=all")
        == primary_before
    )
    assert (
        _git(comparison, "status", "--porcelain=v1", "--untracked-files=all")
        == comparison_before
    )


def test_history_output_is_private_create_once(
    evidence: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    _primary, comparison, inventory_path, hypotheses_path, counter_path = evidence
    output = tmp_path / "history"
    write_history(inventory_path, hypotheses_path, counter_path, comparison, output)
    for path in output.rglob("*"):
        if path.is_file():
            assert os.stat(path, follow_symlinks=False).st_mode & 0o777 == 0o600
    with pytest.raises(HistoryError, match="must not already exist"):
        write_history(inventory_path, hypotheses_path, counter_path, comparison, output)


def test_tampered_counterevidence_refuses(
    evidence: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    _primary, comparison, inventory_path, hypotheses_path, counter_path = evidence
    value = json.loads(counter_path.read_text())
    unsigned = dict(value)
    unsigned.pop("receipt_sha256")
    unsigned["hypotheses"]["receipt_sha256"] = "c" * 64
    counter_path.write_bytes(canonical_bytes(seal_document(unsigned)))
    with pytest.raises(HistoryError, match="hypothesis binding mismatch"):
        write_history(
            inventory_path,
            hypotheses_path,
            counter_path,
            comparison,
            tmp_path / "history",
        )


def test_git_rename_records_are_strict_variable_arity_data() -> None:
    assert _path_changes(b"R075\0old/path.py\0new/path.py\0M\0new/path.py\0") == [
        {
            "status": "R075",
            "old_path": "old/path.py",
            "new_path": "new/path.py",
        },
        {"status": "M", "path": "new/path.py"},
    ]
    with pytest.raises(HistoryError, match="unsupported Git path status"):
        _path_changes(b"C100\0old.py\0new.py\0")
    with pytest.raises(HistoryError, match="truncated rename"):
        _path_changes(b"R100\0old.py\0")
    with pytest.raises(HistoryError, match="safe relative path"):
        _path_changes(b"R100\0../old.py\0new.py\0")
