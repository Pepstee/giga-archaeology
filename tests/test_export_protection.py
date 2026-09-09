from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
import pytest
from unittest.mock import patch
from twin_core.export_protection import ExportProtectionError
from twin_core.cli import main
from pathlib import Path

from twin_core.export_protection import verify_export_set


def _fixture(root: Path) -> tuple[Path, Path]:
    workspace = root / "workspace"
    evidence = root / "evidence"
    policy_dir = workspace / "modules/digital-twin/evidence"
    ledger_dir = workspace / "architecture/evidence"
    policy_dir.mkdir(parents=True)
    ledger_dir.mkdir(parents=True)
    (workspace / "architecture").mkdir(exist_ok=True)
    evidence.mkdir()
    archive = evidence / "export.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("data.json", "{}")
    os.chmod(archive, 0o600)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (workspace / "architecture/baseline.sha256").write_text(f"{digest}  export.zip\n")
    (ledger_dir / "ledger.json").write_text(json.dumps({
        "assets": [{
            "relative_path": "export.zip", "sha256": digest,
            "authority_role": "immutable_original", "format": "zip",
        }]
    }))
    (policy_dir / "export-protection.v1.json").write_text(json.dumps({
        "authority_count": 1,
        "baseline": "architecture/baseline.sha256",
        "ledger": "architecture/evidence/ledger.json",
        "required_source_mode": "0600",
        "encrypted_content_addressed_vault_required": True,
    }))
    return workspace, evidence


def test_complete_export_set_passes_integrity_but_not_unproven_vault() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        workspace, evidence = _fixture(Path(temporary))
        result = verify_export_set(workspace, evidence, policy_path=Path("modules/digital-twin/evidence/export-protection.v1.json"), full_crc=True)
        assert result["integrity_ok"]
        assert result["baseline_complete"]
        assert not result["operational_acceptance"]
        assert "encrypted-two-copy-vault-and-restore-drill" in result["operational_blockers"]


def test_baseline_ledger_disagreement_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        workspace, evidence = _fixture(Path(temporary))
        ledger_path = workspace / "architecture/evidence/ledger.json"
        ledger = json.loads(ledger_path.read_text())
        ledger["assets"][0]["sha256"] = "0" * 64
        ledger_path.write_text(json.dumps(ledger))
        with pytest.raises(ExportProtectionError):
            verify_export_set(workspace, evidence, policy_path=Path("modules/digital-twin/evidence/export-protection.v1.json"))


@pytest.mark.parametrize("relative", ["../outside.zip", "/outside.zip", "linked/export.zip"])
def test_invalid_authority_never_opens_export(tmp_path, relative):
    workspace, evidence = _fixture(tmp_path)
    (evidence / "linked").symlink_to(workspace, target_is_directory=True)
    ledger = workspace / "architecture/evidence/ledger.json"
    value = json.loads(ledger.read_text())
    value["assets"][0]["relative_path"] = relative
    ledger.write_text(json.dumps(value))
    (workspace / "architecture/baseline.sha256").write_text(value["assets"][0]["sha256"] + "  " + relative + "\n")
    with patch("twin_core.export_protection.verify_hash_baseline", side_effect=AssertionError("source read")):
        with pytest.raises(ExportProtectionError):
            verify_export_set(workspace, evidence, policy_path=Path("modules/digital-twin/evidence/export-protection.v1.json"))


def test_policy_escape_fails_before_load(tmp_path):
    with patch("twin_core.export_protection._load", side_effect=AssertionError("outside policy read")):
        with pytest.raises(ExportProtectionError):
            verify_export_set(tmp_path, tmp_path, policy_path=Path("../policy.json"))


def test_explicit_cli_and_baseline_compatibility(tmp_path, capsys):
    workspace, evidence = _fixture(tmp_path)
    args = ["--root", str(workspace), "verify-exports", "--policy", "modules/digital-twin/evidence/export-protection.v1.json", "--evidence-root", str(evidence), "--full-crc"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["archive_checks"]["export.zip"]["crc"] == "pass"
    assert main(args + ["--require-hardened"]) == 2
    capsys.readouterr()
    assert main(["--root", str(evidence), "verify-exports", "--baseline", str(workspace / "architecture/baseline.sha256")]) == 0
    capsys.readouterr()
    with pytest.raises(SystemExit):
        main(["--root", str(workspace), "verify-exports", "--policy", "policy.json"])


@pytest.mark.parametrize("field", ["ledger", "baseline"])
def test_policy_dependency_escape_rejected_before_read(tmp_path, field):
    workspace, evidence = _fixture(tmp_path)
    policy_path = Path("modules/digital-twin/evidence/export-protection.v1.json")
    policy = json.loads((workspace / policy_path).read_text())
    policy[field] = "../outside.json"
    (workspace / policy_path).write_text(json.dumps(policy))
    with patch("twin_core.export_protection._baseline_entries", side_effect=AssertionError("baseline read")):
        with pytest.raises(ExportProtectionError):
            verify_export_set(workspace, evidence, policy_path=policy_path)


def test_hash_valid_malformed_zip_has_inspectable_cli_failure(tmp_path, capsys):
    workspace, evidence = _fixture(tmp_path)
    (evidence / "export.zip").write_bytes(b"not a ZIP")
    digest = hashlib.sha256(b"not a ZIP").hexdigest()
    ledger_file = workspace / "architecture/evidence/ledger.json"
    ledger = json.loads(ledger_file.read_text())
    ledger["assets"][0]["sha256"] = digest
    ledger_file.write_text(json.dumps(ledger))
    (workspace / "architecture/baseline.sha256").write_text(digest + "  export.zip\n")
    assert main(["--root", str(workspace), "verify-exports", "--policy", "modules/digital-twin/evidence/export-protection.v1.json", "--evidence-root", str(evidence)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert not result["integrity_ok"]
    assert "ZIP authority" in result["errors"][0]
