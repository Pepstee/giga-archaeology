import hashlib
import json
from pathlib import Path

from gate_admission import decide


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_no_expansion_is_admitted(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {"findings": [{"id": "F-1", "classification": "DEFECT", "status": "open"}]},
    )
    assert decide(findings, None, None)[0] is True


def test_expansion_without_fable_is_refused(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {
            "findings": [
                {
                    "id": "F-2",
                    "classification": "ARCHITECTURE_EXPANSION",
                    "status": "open",
                }
            ]
        },
    )
    admitted, reason = decide(findings, None, None)
    assert admitted is False
    assert "Fable" in reason


def test_non_approving_fable_ruling_is_refused(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {
            "findings": [
                {
                    "id": "F-3",
                    "classification": "ARCHITECTURE_EXPANSION",
                    "status": "open",
                }
            ]
        },
    )
    ruling = write_json(
        tmp_path / "ruling.json",
        {"decision": "REDIRECT", "ratified_finding_ids": ["F-3"]},
    )
    receipt = write_json(
        tmp_path / "receipt.json",
        {
            "schema": "giga.fable-gate-receipt.v1",
            "ruling_sha256": hashlib.sha256(ruling.read_bytes()).hexdigest(),
        },
    )
    assert decide(findings, ruling, receipt)[0] is False


def test_exact_hash_bound_fable_ratification_is_admitted(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {
            "findings": [
                {
                    "id": "F-4",
                    "classification": "ARCHITECTURE_EXPANSION",
                    "status": "open",
                }
            ]
        },
    )
    ruling = write_json(
        tmp_path / "ruling.json",
        {
            "decision": "APPROVE_SCOPE_EXCEPTION",
            "ratified_finding_ids": ["F-4"],
        },
    )
    receipt = write_json(
        tmp_path / "receipt.json",
        {
            "schema": "giga.fable-gate-receipt.v1",
            "ruling_sha256": hashlib.sha256(ruling.read_bytes()).hexdigest(),
        },
    )
    assert decide(findings, ruling, receipt)[0] is True


def test_wrong_ruling_hash_is_refused(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {
            "findings": [
                {
                    "id": "F-5",
                    "classification": "ARCHITECTURE_EXPANSION",
                    "status": "open",
                }
            ]
        },
    )
    ruling = write_json(
        tmp_path / "ruling.json",
        {
            "decision": "APPROVE_SCOPE_EXCEPTION",
            "ratified_finding_ids": ["F-5"],
        },
    )
    receipt = write_json(
        tmp_path / "receipt.json",
        {
            "schema": "giga.fable-gate-receipt.v1",
            "ruling_sha256": "0" * 64,
        },
    )
    assert decide(findings, ruling, receipt)[0] is False
