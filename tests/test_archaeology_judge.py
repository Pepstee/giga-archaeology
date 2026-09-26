from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.counterevidence import COUNTEREVIDENCE_SCHEMA
from modules.operations.archaeology.evidence import (
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
)
from modules.operations.archaeology.history import HISTORY_SCHEMA
from modules.operations.archaeology.hypotheses import HYPOTHESES_SCHEMA
from modules.operations.archaeology.inventory import write_inventory
from modules.operations.archaeology.judge import (
    JudgeError,
    build_judgement,
    write_judgement,
)


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["/usr/bin/git", *arguments], cwd=root, check=True, capture_output=True
    )


def _write(path: Path, value: dict[str, object]) -> Path:
    path.write_bytes(canonical_bytes(value))
    return path


def _finding(tool: str, kind: str, detail: dict[str, object]) -> dict[str, object]:
    identity = {
        "tool": tool,
        "kind": kind,
        "paths": ["src/candidate.py"],
        "detail": detail,
    }
    return {
        "id": sha256_bytes(canonical_bytes(identity)),
        **identity,
        "state": "OBSERVED",
        "authority_granted": False,
        "cleanup_permitted": False,
    }


def _candidate_evidence(
    tmp_path: Path,
    *,
    probe_argv: list[str] | None = None,
    probe_should_pass: bool = True,
) -> dict[str, Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "Fixture")
    _git(repository, "config", "user.email", "<redacted-email>")
    (repository / "src").mkdir()
    (repository / "src/candidate.py").write_text("def candidate():\n    return 1\n")
    if probe_argv is not None:
        (repository / "src/app.py").write_text("def answer():\n    return 42\n")
        (repository / "tests").mkdir()
        (repository / "tests/test_app.py").write_text(
            "import unittest\nfrom src.app import answer\n\n"
            "class AppTests(unittest.TestCase):\n"
            "    def test_answer(self):\n"
            f"        self.assertEqual(answer(), {42 if probe_should_pass else 41})\n"
        )
        marker = seal_document(
            {
                "schema": "giga.archaeologist.disposable-fixture.v1",
                "disposable": True,
                "target_path": "src/candidate.py",
                "probe_argv": probe_argv,
                "cleanup_permitted": False,
                "deletion_permitted": False,
            }
        )
        (repository / ".giga-archaeologist-disposable.json").write_bytes(
            canonical_bytes(marker)
        )
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "fixture")

    inventory_dir = tmp_path / "inventory"
    inventory = write_inventory(repository, inventory_dir)
    inventory_path = inventory_dir / "inventory.json"
    inventory_raw = inventory_path.read_bytes()
    findings = [
        _finding(
            "vulture",
            "python-unused-observation",
            {"line": 1, "message": "unused function 'candidate'"},
        ),
        _finding(
            "codegraphcontext",
            "graph-unreferenced-function-observation",
            {"line": 1, "symbol": "candidate"},
        ),
    ]
    hypotheses = seal_document(
        {
            "schema": HYPOTHESES_SCHEMA,
            "authority": "read-only-observation",
            "authority_granted": False,
            "cleanup_permitted": False,
            "inventory": {
                "file_sha256": sha256_bytes(inventory_raw),
                "receipt_sha256": inventory["receipt_sha256"],
            },
            "findings": findings,
        }
    )
    hypotheses_path = _write(tmp_path / "hypotheses.json", hypotheses)
    hypotheses_raw = hypotheses_path.read_bytes()
    counter_records = [
        {
            "hypothesis_id": item["id"],
            "hypothesis_state": "OBSERVED",
            "counterevidence_state": "CLEARED_WITH_COMPLETE_RUNTIME_TRACE",
            "runtime_trace_available": True,
            "entrypoint_scope_complete": True,
            "evidence": [],
            "trace_receipt_sha256": "a" * 64,
            "authority_granted": False,
            "cleanup_permitted": False,
        }
        for item in findings
    ]
    counter = seal_document(
        {
            "schema": COUNTEREVIDENCE_SCHEMA,
            "authority": "read-only-counterevidence",
            "authority_granted": False,
            "cleanup_permitted": False,
            "inventory": {
                "file_sha256": sha256_bytes(inventory_raw),
                "receipt_sha256": inventory["receipt_sha256"],
            },
            "hypotheses": {
                "file_sha256": sha256_bytes(hypotheses_raw),
                "receipt_sha256": hypotheses["receipt_sha256"],
            },
            "records": counter_records,
        }
    )
    counter_path = _write(tmp_path / "counter.json", counter)
    counter_raw = counter_path.read_bytes()
    history_records = [
        {
            "hypothesis_id": item["id"],
            "hypothesis_state": "OBSERVED",
            "historical_state": "NO_RELATED_VARIANT_VERIFIED",
            "absence_proof": {
                "all_refs_checked": True,
                "rename_history_checked": True,
                "comparison_repository_receipts": ["b" * 64],
            },
            "authority_granted": False,
            "cleanup_permitted": False,
        }
        for item in findings
    ]
    history = seal_document(
        {
            "schema": HISTORY_SCHEMA,
            "authority": "read-only-historical-evidence",
            "authority_granted": False,
            "cleanup_permitted": False,
            "inputs": {
                "inventory": {
                    "file_sha256": sha256_bytes(inventory_raw),
                    "receipt_sha256": inventory["receipt_sha256"],
                },
                "hypotheses": {
                    "file_sha256": sha256_bytes(hypotheses_raw),
                    "receipt_sha256": hypotheses["receipt_sha256"],
                },
                "counterevidence": {
                    "file_sha256": sha256_bytes(counter_raw),
                    "receipt_sha256": counter["receipt_sha256"],
                },
            },
            "records": history_records,
        }
    )
    history_path = _write(tmp_path / "history.json", history)
    return {
        "repository": repository,
        "inventory": inventory_path,
        "hypotheses": hypotheses_path,
        "counter": counter_path,
        "history": history_path,
    }


@pytest.fixture()
def evidence(tmp_path: Path) -> dict[str, Path]:
    return _candidate_evidence(tmp_path)


def _reseal(path: Path, mutate) -> None:
    value = json.loads(path.read_text())
    value.pop("receipt_sha256")
    mutate(value)
    path.write_bytes(canonical_bytes(seal_document(value)))


def _judge(paths: dict[str, Path]) -> dict[str, object]:
    return build_judgement(
        paths["inventory"], paths["hypotheses"], paths["counter"], paths["history"]
    )


def test_two_tools_and_complete_negative_evidence_mint_candidate(
    evidence: dict[str, Path],
) -> None:
    payload = _judge(evidence)
    validate_self_hash(payload)
    assert payload["summary"] == {
        "hypotheses": 2,
        "CONFLICT": 0,
        "UNKNOWN": 0,
        "VERIFIED_CANDIDATE": 2,
    }
    assert {tuple(item["lifecycle"]) for item in payload["decisions"]} == {
        ("OBSERVED", "CORROBORATED", "COUNTEREVIDENCE_CHECKED", "VERIFIED_CANDIDATE")
    }
    assert all(item["quarantine_candidate"] for item in payload["decisions"])
    assert all(
        not item["cleanup_permitted"] and not item["deletion_permitted"]
        for item in payload["decisions"]
    )


def test_positive_counterevidence_is_conflict(evidence: dict[str, Path]) -> None:
    _reseal(
        evidence["counter"],
        lambda value: value["records"][0].update(counterevidence_state="PRESENT"),
    )
    counter = json.loads(evidence["counter"].read_text())
    _reseal(
        evidence["history"],
        lambda value: value["inputs"]["counterevidence"].update(
            file_sha256=sha256_bytes(evidence["counter"].read_bytes()),
            receipt_sha256=counter["receipt_sha256"],
        ),
    )
    payload = _judge(evidence)
    assert payload["summary"]["CONFLICT"] == 1
    assert payload["summary"]["VERIFIED_CANDIDATE"] == 1


def test_positive_history_is_conflict(evidence: dict[str, Path]) -> None:
    _reseal(
        evidence["history"],
        lambda value: value["records"][0].update(
            historical_state="RELATED_VARIANT_OBSERVED"
        ),
    )
    assert _judge(evidence)["summary"]["CONFLICT"] == 1


def test_missing_record_is_unknown(evidence: dict[str, Path]) -> None:
    _reseal(evidence["counter"], lambda value: value["records"].pop())
    counter = json.loads(evidence["counter"].read_text())
    _reseal(
        evidence["history"],
        lambda value: value["inputs"]["counterevidence"].update(
            file_sha256=sha256_bytes(evidence["counter"].read_bytes()),
            receipt_sha256=counter["receipt_sha256"],
        ),
    )
    assert _judge(evidence)["summary"]["UNKNOWN"] == 1


def test_duplicate_and_tampered_evidence_refuse(evidence: dict[str, Path]) -> None:
    _reseal(
        evidence["counter"], lambda value: value["records"].append(value["records"][0])
    )
    counter = json.loads(evidence["counter"].read_text())
    _reseal(
        evidence["history"],
        lambda value: value["inputs"]["counterevidence"].update(
            file_sha256=sha256_bytes(evidence["counter"].read_bytes()),
            receipt_sha256=counter["receipt_sha256"],
        ),
    )
    with pytest.raises(JudgeError, match="unique"):
        _judge(evidence)


def test_output_is_private_and_create_once(
    evidence: dict[str, Path], tmp_path: Path
) -> None:
    output = tmp_path / "judge"
    write_judgement(
        evidence["inventory"],
        evidence["hypotheses"],
        evidence["counter"],
        evidence["history"],
        output,
    )
    assert all(
        os.stat(path, follow_symlinks=False).st_mode & 0o777 == 0o600
        for path in output.iterdir()
    )
    with pytest.raises(JudgeError, match="must not already exist"):
        write_judgement(
            evidence["inventory"],
            evidence["hypotheses"],
            evidence["counter"],
            evidence["history"],
            output,
        )
