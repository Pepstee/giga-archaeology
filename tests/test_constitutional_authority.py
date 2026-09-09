from __future__ import annotations

import hashlib

import json

import os

import shutil

import subprocess

import sys

from datetime import datetime, timedelta, timezone

from pathlib import Path

import pytest

from twin_core import constitutional_authority as authority

def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")

def private_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
    return path

def fixture_activation(effect: str, request_sha256: str) -> bytes:
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    value = {
        "schema": "giga.runtime-authority-activation.v1",
        "status": "ACTIVE",
        "product_commit": "1" * 40,
        "product_tree": "2" * 40,
        "authority_manifest_sha256": authority._AUTHORITY_MANIFEST_SHA256,
        "authority_provenance_sha256": authority._AUTHORITY_PROVENANCE_SHA256,
        "policy_sha256": authority._POLICY_SHA256,
        "default_decision": "DENY",
        "allowed_effects": [effect],
        "grants": [
            {
                "effect": effect,
                "decision": "ALLOW",
                "capability_id": "fixture-only",
                "work_order_sha256": "3" * 64,
                "request_sha256": request_sha256,
                "expires_at": expires,
            }
        ],
        "protected_action_receipt_sha256": "4" * 64,
    }
    return canonical(value)

def test_candidate_build_has_no_pinned_allow_authority() -> None:
    assert authority.AUTHORITY_STATE == "CANDIDATE_ONLY"
    assert authority._PINNED_ACTIVATION_SHA256 is None

def test_arbitrary_unregistered_external_delete_is_default_deny(tmp_path: Path) -> None:
    area = private_directory(tmp_path / "unknown")
    ledger = area / "decisions.jsonl"
    with pytest.raises(authority.AuthorityRefused, match="UNKNOWN_EFFECT"):
        authority.require_authority(
            effect="external.delete",
            decision_ledger=ledger,
            request={"target": "anything"},
        )
    receipt = json.loads(ledger.read_text(encoding="utf-8"))
    assert receipt["decision"] == "REFUSE"
    assert receipt["reason_code"] == "UNKNOWN_EFFECT"
    assert receipt["policy_sha256"] == authority._POLICY_SHA256

def test_forged_predecessor_and_unknown_fields_reject_before_append(tmp_path: Path) -> None:
    area = private_directory(tmp_path / "forged")
    ledger = area / "decisions.jsonl"
    original = b'{"schema":"giga.constitution-decision-receipt.v2","forged":true}\n'
    ledger.write_bytes(original)
    ledger.chmod(0o600)
    with pytest.raises(authority.AuthorityRefused):
        authority.require_authority(effect="twin-cli.init", decision_ledger=ledger, request={"command": "init"})
    assert ledger.read_bytes() == original

def test_exact_self_hashed_activated_allow_chain_head_rejects_unchanged(tmp_path: Path) -> None:
    area = private_directory(tmp_path / "forged-allow")
    ledger = area / "decisions.jsonl"
    unsigned = {
        "schema": "giga.constitution-decision-receipt.v2",
        "sequence": 0,
        "recorded_at": "2026-08-26T00:00:00.000000Z",
        "effect": "twin-cli.init",
        "request_sha256": hashlib.sha256(canonical({"command": "forged"})).hexdigest(),
        "authority_manifest_sha256": authority._AUTHORITY_MANIFEST_SHA256,
        "policy_sha256": authority._POLICY_SHA256,
        "authority_state": "ACTIVATED",
        "decision": "ALLOW",
        "reason_code": "ACTIVATED_EXACT_GRANT",
        "previous_receipt_sha256": "0" * 64,
    }
    forged = dict(unsigned)
    forged["receipt_sha256"] = hashlib.sha256(canonical(unsigned)).hexdigest()
    original = canonical(forged) + b"\n"
    ledger.write_bytes(original)
    ledger.chmod(0o600)
    with pytest.raises(authority.AuthorityRefused, match="candidate-only decision ledger contains ALLOW"):
        authority.require_authority(
            effect="twin-cli.init",
            decision_ledger=ledger,
            request={"command": "init"},
        )
    assert ledger.read_bytes() == original

def test_hardlinked_ledger_rejects_before_write_or_chmod(tmp_path: Path) -> None:
    area = private_directory(tmp_path / "hardlink")
    ledger = area / "decisions.jsonl"
    other = area / "other.jsonl"
    original = b"protected\n"
    ledger.write_bytes(original)
    ledger.chmod(0o640)
    os.link(ledger, other)
    before_mode = ledger.stat().st_mode
    with pytest.raises(authority.AuthorityRefused, match="single-link"):
        authority.require_authority(effect="twin-cli.init", decision_ledger=ledger, request={"command": "init"})
    assert ledger.read_bytes() == original
    assert ledger.stat().st_mode == before_mode

def test_candidate_only_production_ignores_unpinned_activation_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    area = private_directory(tmp_path / "candidate")
    request = {"command": "init"}
    request_sha256 = hashlib.sha256(canonical(request)).hexdigest()
    activation = area / "runtime-authority-activation.json"
    activation.write_bytes(fixture_activation("twin-cli.init", request_sha256))
    monkeypatch.setattr(authority, "_ACTIVATION_PATH", activation)
    assert authority._PINNED_ACTIVATION_SHA256 is None
    with pytest.raises(authority.AuthorityRefused, match="RUNTIME_ACTIVATION_REQUIRED"):
        authority.require_authority(
            effect="twin-cli.init",
            decision_ledger=area / "decisions.jsonl",
            request=request,
        )


def test_status_does_not_read_activation_or_open_ledger(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("status touched runtime authority")
    monkeypatch.setattr(authority, "_append_receipt", forbidden)
    monkeypatch.setattr(authority, "_activation_decision", forbidden)
    result = authority.candidate_status()
    assert result["candidate_verified"] is True
    assert result["decision"] == "REFUSE"
    assert result["host_bound_corpus_authority"] == "UNAVAILABLE"


@pytest.mark.parametrize("attack", ["missing", "extra", "modified", "mode", "escape"])
def test_archive_corruption_refuses(tmp_path, monkeypatch, attack):
    import zipfile
    source = Path(authority.__file__).with_name("_authority_vendor.zip")
    with zipfile.ZipFile(source) as original:
        rows = [(info, original.read(info)) for info in original.infolist()]
    archive = tmp_path / "_authority_vendor.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for index, (info, content) in enumerate(rows):
            if index == 0:
                if attack == "missing":
                    continue
                if attack == "modified":
                    content += b"corrupt"
                if attack == "mode":
                    info.external_attr = 0o100644 << 16
                if attack == "escape":
                    info.filename = "../escape"
            output.writestr(info, content)
        if attack == "extra":
            output.writestr("extra", b"extra")
    monkeypatch.setattr(authority, "__file__", str(tmp_path / "constitutional_authority.py"))
    with pytest.raises(authority.AuthorityRefused):
        authority.candidate_status()
    assert not (tmp_path.parent / "escape").exists()
