from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.counterevidence import (
    CounterevidenceError,
    write_counterevidence,
)
from modules.operations.archaeology.evidence import (
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
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


@pytest.fixture()
def inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "src").mkdir()
    (root / "src/app.py").write_text(
        "def main():\n    return 1\n\ndef plugin():\n    return 2\n",
        encoding="utf-8",
    )
    (root / "src/orphan.py").write_text(
        "def orphan():\n    return 3\n", encoding="utf-8"
    )
    (root / "src/runner.py").write_text(
        "import src.app\n\ndef dispatch(module):\n    return getattr(module, 'plugin')()\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname="fixture"\nversion="1"\n[project.scripts]\nfixture="src.app:main"\n',
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    inventory_dir = tmp_path / "inventory"
    inventory = write_inventory(root, inventory_dir)
    inventory_path = inventory_dir / "inventory.json"
    inventory_raw = inventory_path.read_bytes()

    def finding(name: str, line: int, path: str = "src/app.py") -> dict[str, object]:
        identity = {
            "tool": "vulture",
            "kind": "python-unused-observation",
            "paths": [path],
            "detail": {"line": line, "message": f"unused function '{name}'"},
        }
        return {
            "id": sha256_bytes(canonical_bytes(identity)),
            **identity,
            "state": "OBSERVED",
            "authority_granted": False,
            "cleanup_permitted": False,
        }

    findings = [
        finding("main", 1),
        finding("plugin", 4),
        finding("orphan", 1, "src/orphan.py"),
    ]
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
                "files": 3,
                "path_list_sha256": "a" * 64,
                "persisted": False,
                "source_unchanged": True,
            },
            "tools": [],
            "findings": findings,
            "summary": {
                "observations": 3,
                "tools_passed": 0,
                "tools_not_passed": 0,
                "states": {"OBSERVED": 3},
            },
        }
    )
    hypotheses_path = tmp_path / "hypotheses.json"
    hypotheses_path.write_bytes(canonical_bytes(hypotheses))
    return root, inventory_path, hypotheses_path


def test_entrypoint_and_dynamic_signals_block_false_absence(
    inputs: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    root, inventory_path, hypotheses_path = inputs
    before = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    output = tmp_path / "counterevidence"
    payload = write_counterevidence(inventory_path, hypotheses_path, output)
    validate_self_hash(payload)
    by_id = {item["hypothesis_id"]: item for item in payload["records"]}
    hypotheses = json.loads(hypotheses_path.read_text())
    main, plugin, orphan = [by_id[item["id"]] for item in hypotheses["findings"]]
    assert main["counterevidence_state"] == "PRESENT"
    assert any(
        item["kind"] == "declared-entrypoint-symbol" for item in main["evidence"]
    )
    assert plugin["counterevidence_state"] == "PRESENT"
    assert any(
        item["kind"] == "dynamic-string-reference" for item in plugin["evidence"]
    )
    assert orphan["counterevidence_state"] == "UNKNOWN"
    assert orphan["runtime_trace_available"] is False
    assert payload["authority_granted"] is False
    assert payload["cleanup_permitted"] is False
    assert _git(root, "status", "--porcelain=v1", "--untracked-files=all") == before


def test_output_is_private_create_once_and_no_unknown_becomes_absent(
    inputs: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    _root, inventory_path, hypotheses_path = inputs
    output = tmp_path / "counterevidence"
    payload = write_counterevidence(inventory_path, hypotheses_path, output)
    assert all(
        item["counterevidence_state"] in {"PRESENT", "UNKNOWN"}
        for item in payload["records"]
    )
    for path in output.rglob("*"):
        if path.is_file():
            assert os.stat(path, follow_symlinks=False).st_mode & 0o777 == 0o600
    with pytest.raises(CounterevidenceError, match="must not already exist"):
        write_counterevidence(inventory_path, hypotheses_path, output)


def test_cross_document_hash_drift_refuses(
    inputs: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    _root, inventory_path, hypotheses_path = inputs
    value = json.loads(hypotheses_path.read_text())
    unsigned = dict(value)
    unsigned.pop("receipt_sha256")
    unsigned["inventory"]["file_sha256"] = "b" * 64
    hypotheses_path.write_bytes(canonical_bytes(seal_document(unsigned)))
    with pytest.raises(CounterevidenceError, match="inventory file hash mismatch"):
        write_counterevidence(inventory_path, hypotheses_path, tmp_path / "out")
