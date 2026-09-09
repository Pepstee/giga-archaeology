from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest
import scripts.staged_privacy_admission as privacy

from scripts.staged_privacy_admission import (
    _HOOK_BYTES,
    PrivacyAdmissionError,
    activate_hook,
    audit_index,
    audit_range,
    hook_status,
    main,
)


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _repo(root: Path) -> str:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Artiom Gutu")
    _git(root, "config", "user.email", "gutu.artiom444@gmail.com")
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-qm", "base")
    return _git(root, "rev-parse", "HEAD")


def _stage(
    root: Path, relative: str, body: bytes = b"safe\n", *, force: bool = False
) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    _git(root, "add", "-f" if force else "--", relative)


def _install_and_activate(root: Path) -> str:
    source_root = Path(__file__).resolve().parents[1]
    controller = root / "scripts/staged_privacy_admission.py"
    hook = root / ".githooks/pre-commit"
    controller.parent.mkdir()
    hook.parent.mkdir()
    controller.write_bytes(
        (source_root / "scripts/staged_privacy_admission.py").read_bytes()
    )
    hook.write_bytes(_HOOK_BYTES)
    controller.chmod(0o755)
    hook.chmod(0o755)
    _git(root, "add", "scripts/staged_privacy_admission.py", ".githooks/pre-commit")
    _git(root, "commit", "-qm", "install privacy admission")
    commit = _git(root, "rev-parse", "HEAD")
    assert activate_hook(root)["status"] == "ACTIVE"
    return commit


def test_exact_staged_bytes_pass_and_unstaged_private_bytes_do_not_leak(
    tmp_path: Path,
) -> None:
    _repo(tmp_path)
    _stage(tmp_path, "src/owner.py", b"print('safe')\n")
    (tmp_path / "src/owner.py").write_bytes(b"sk-" + b"x" * 40 + b"\n")
    result = audit_index(tmp_path)
    assert result["status"] == "PASS"
    assert result["scanned_blob_count"] == 1
    assert result["private_payload_admitted"] is False


@pytest.mark.parametrize(
    "relative",
    [
        "candidate-evidence/raw.json",
        "runtime_evidence/canary/dom.html",
        "personal-vault/export.json",
        "live-canary/attempt/network.har",
        "applications/Synthetic_resume.pdf",
        "applications/acme/answers.json",
        "documents/Synthetic_CV_NewRole.pdf",
    ],
)
def test_private_evidence_and_identity_paths_refuse(
    tmp_path: Path, relative: str
) -> None:
    _repo(tmp_path)
    _stage(tmp_path, relative)
    with pytest.raises(PrivacyAdmissionError, match="private"):
        audit_index(tmp_path)


def test_force_added_ignored_private_payload_still_refuses(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / ".gitignore").write_text("candidate-evidence/\n", encoding="utf-8")
    _git(tmp_path, "add", ".gitignore")
    _git(tmp_path, "commit", "-qm", "ignore private evidence")
    _stage(tmp_path, "candidate-evidence/raw.json", force=True)
    with pytest.raises(PrivacyAdmissionError, match="private evidence"):
        audit_index(tmp_path)


def test_alternate_committing_index_is_the_one_admitted(
    tmp_path: Path, monkeypatch
) -> None:
    _repo(tmp_path)
    alternate = tmp_path / "alternate.index"
    environment = {**os.environ, "GIT_INDEX_FILE": str(alternate)}
    subprocess.run(
        ["git", "read-tree", "HEAD"], cwd=tmp_path, env=environment, check=True
    )
    private = tmp_path / "candidate-evidence/raw.json"
    private.parent.mkdir(parents=True)
    private.write_text("{}\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-f", "candidate-evidence/raw.json"],
        cwd=tmp_path,
        env=environment,
        check=True,
    )
    monkeypatch.setenv("GIT_INDEX_FILE", str(alternate))
    with pytest.raises(PrivacyAdmissionError, match="private evidence"):
        audit_index(tmp_path)


def test_private_key_and_credential_shapes_refuse_without_echoing_bytes(
    tmp_path: Path,
) -> None:
    _repo(tmp_path)
    private_key = (
        b"-----BEGIN "
        + b"PRIVATE KEY-----\n"
        + b"A" * 80
        + b"\n-----END PRIVATE KEY-----\n"
    )
    _stage(tmp_path, "config/material.txt", private_key)
    with pytest.raises(
        PrivacyAdmissionError, match="private key material"
    ) as key_error:
        audit_index(tmp_path)
    assert "AAAA" not in str(key_error.value)

    _stage(tmp_path, "config/material.txt", b"sk-" + b"a" * 40 + b"\n")
    with pytest.raises(PrivacyAdmissionError, match="credential-shaped"):
        audit_index(tmp_path)


@pytest.mark.parametrize(
    "body",
    [
        b"api_key: abcdefghijklmnopqrstuvwxyz123456\n",
        b"PASSWORD=correcthorsebatterystaple\n",
        b"aws_secret_access_key = 'abcdefghijklmnopqrstuvwxyz123456'\n",
        b'"api_' + b'key": "abcdefghijklmnopqrstuvwxyz123456"\n',
        b"{" + b'"password":"correcthorsebatterystaple"}\n',
    ],
)
def test_unquoted_and_compound_credential_assignments_refuse(
    tmp_path: Path, body: bytes
) -> None:
    _repo(tmp_path)
    _stage(tmp_path, "config/settings.txt", body)
    with pytest.raises(PrivacyAdmissionError, match="credential-shaped"):
        audit_index(tmp_path)


@pytest.mark.parametrize(
    "body",
    [
        b"API_KEY=${GIGA_API_KEY}\n",
        b"PASSWORD=<from-operator-environment>\n",
        b"aws_secret_access_key: REDACTED_PLACEHOLDER\n",
        b"{" + b'"api_' + b'key": "${GIGA_API_KEY}"}\n',
    ],
)
def test_explicit_credential_placeholders_are_not_false_positives(
    tmp_path: Path, body: bytes
) -> None:
    _repo(tmp_path)
    _stage(tmp_path, "config/settings.example", body)
    assert audit_index(tmp_path)["status"] == "PASS"


def test_secret_filename_and_symlink_refuse(tmp_path: Path) -> None:
    _repo(tmp_path)
    _stage(tmp_path, ".env", b"SAFE_PLACEHOLDER=1\n", force=True)
    with pytest.raises(PrivacyAdmissionError, match="secret-bearing filename"):
        audit_index(tmp_path)

    _git(tmp_path, "reset", "-q", "HEAD", "--", ".env")
    (tmp_path / ".env").unlink()
    os.symlink("README.md", tmp_path / "linked")
    _git(tmp_path, "add", "linked")
    with pytest.raises(PrivacyAdmissionError, match="symlink"):
        audit_index(tmp_path)


def test_commit_range_rejects_private_payload_and_accepts_safe_change(
    tmp_path: Path,
) -> None:
    base = _repo(tmp_path)
    _stage(tmp_path, "src/owner.py", b"print('safe')\n")
    _git(tmp_path, "commit", "-qm", "safe")
    safe = _git(tmp_path, "rev-parse", "HEAD")
    assert audit_range(tmp_path, base, safe)["status"] == "PASS"

    _stage(tmp_path, "live-canary/attempt/dom.json", b"{}\n")
    _git(tmp_path, "commit", "-qm", "unsafe")
    unsafe = _git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(PrivacyAdmissionError, match="private evidence"):
        audit_range(tmp_path, safe, unsafe)


def test_commit_range_rejects_private_payload_deleted_at_tip(tmp_path: Path) -> None:
    base = _repo(tmp_path)
    _stage(tmp_path, "live-canary/attempt/dom.json", b"{}\n")
    _git(tmp_path, "commit", "-qm", "unsafe intermediate")
    (tmp_path / "live-canary/attempt/dom.json").unlink()
    _git(tmp_path, "add", "-u")
    _git(tmp_path, "commit", "-qm", "hide unsafe intermediate")
    tip = _git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(PrivacyAdmissionError, match="private evidence"):
        audit_range(tmp_path, base, tip)


def test_application_source_module_and_env_example_are_not_false_positives(
    tmp_path: Path,
) -> None:
    _repo(tmp_path)
    _stage(tmp_path, "src/market_aligner/applications/jaa.py", b"OWNER = True\n")
    _stage(tmp_path, ".env.example", b"TOKEN_FROM_ENV=\n")
    assert audit_index(tmp_path)["status"] == "PASS"


def test_cli_refuses_without_printing_private_content(tmp_path: Path, capsys) -> None:
    _repo(tmp_path)
    _stage(tmp_path, "config/token.txt", b"sk-" + b"z" * 40 + b"\n")
    assert main(["index", "--root", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "credential-shaped" in captured.err
    assert "zzzz" not in captured.err


def test_activated_hook_rejects_an_actual_forced_private_commit(tmp_path: Path) -> None:
    _repo(tmp_path)
    with pytest.raises(PrivacyAdmissionError, match="not activated"):
        hook_status(tmp_path)
    installed_commit = _install_and_activate(tmp_path)
    assert hook_status(tmp_path)["status"] == "ACTIVE"

    _stage(tmp_path, "candidate-evidence/raw.json", force=True)
    result = subprocess.run(
        ["git", "commit", "-m", "attempt private evidence"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "private evidence" in result.stderr
    assert _git(tmp_path, "rev-parse", "HEAD") == installed_commit
    assert "candidate-evidence/raw.json" not in _git(
        tmp_path, "ls-tree", "-r", "--name-only", "HEAD"
    )


@pytest.mark.parametrize(
    ("relative", "body", "message"),
    [
        (
            "scripts/staged_privacy_admission.py",
            b"print('disabled')\n",
            "controller update requires explicit activation",
        ),
        (
            ".githooks/pre-commit",
            b"#!/bin/sh\nexit 0\n",
            "hook update requires exact reviewed bytes",
        ),
    ],
)
def test_active_installed_boundary_refuses_unactivated_control_weakening(
    tmp_path: Path, relative: str, body: bytes, message: str
) -> None:
    _repo(tmp_path)
    installed_commit = _install_and_activate(tmp_path)
    path = tmp_path / relative
    path.write_bytes(body)
    path.chmod(0o755)
    _git(tmp_path, "add", relative)
    result = subprocess.run(
        ["git", "commit", "-m", "weaken privacy admission"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert message in result.stderr
    assert _git(tmp_path, "rev-parse", "HEAD") == installed_commit


def test_activation_installs_the_retained_reviewed_controller_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    _repo(tmp_path)
    source_root = Path(__file__).resolve().parents[1]
    controller = tmp_path / "scripts/staged_privacy_admission.py"
    hook = tmp_path / ".githooks/pre-commit"
    controller.parent.mkdir()
    hook.parent.mkdir()
    reviewed = (source_root / "scripts/staged_privacy_admission.py").read_bytes()
    controller.write_bytes(reviewed)
    hook.write_bytes(_HOOK_BYTES)
    controller.chmod(0o755)
    hook.chmod(0o755)
    _git(tmp_path, "add", "scripts/staged_privacy_admission.py", ".githooks/pre-commit")

    original = privacy._validate_admission_files
    swapped = b"raise SystemExit(0)\n"

    def swap_after_validation(*args, **kwargs):
        retained = original(*args, **kwargs)
        controller.write_bytes(swapped)
        controller.chmod(0o755)
        return retained

    monkeypatch.setattr(privacy, "_validate_admission_files", swap_after_validation)
    assert privacy.activate_hook(tmp_path)["status"] == "ACTIVE"
    installed = Path(_git(tmp_path, "config", "--local", "--get", "core.hooksPath"))
    assert (installed / "controller.py").read_bytes() == reviewed
    assert (installed / "controller.py").read_bytes() != swapped

    _stage(tmp_path, "candidate-evidence/raw.json", force=True)
    result = subprocess.run(
        ["git", "commit", "-m", "attempt private evidence after swap"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "private evidence" in result.stderr


def test_config_drift_is_detected_and_protected_range_still_refuses(
    tmp_path: Path,
) -> None:
    _repo(tmp_path)
    protected_base = _install_and_activate(tmp_path)
    disabled = tmp_path / ".disabled-hooks"
    disabled.mkdir()
    _git(tmp_path, "config", "core.hooksPath", str(disabled))
    with pytest.raises(PrivacyAdmissionError, match="not activated"):
        hook_status(tmp_path)

    _stage(tmp_path, "candidate-evidence/raw.json", force=True)
    _git(tmp_path, "commit", "-qm", "local bypass remains remotely inadmissible")
    bypass_commit = _git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(PrivacyAdmissionError, match="private evidence"):
        audit_range(tmp_path, protected_base, bypass_commit)


def test_path_fingerprint_preserves_exact_denial_without_embedded_label(tmp_path, monkeypatch):
    import hashlib
    _repo(tmp_path)
    relative = 'synthetic/exact-denial.txt'
    monkeypatch.setattr(privacy, '_KNOWN_PRIVATE_PATH_SHA256', frozenset({hashlib.sha256(relative.encode()).hexdigest()}))
    _stage(tmp_path, relative)
    with pytest.raises(PrivacyAdmissionError, match='known private identity artifact') as error:
        audit_index(tmp_path)
    assert relative not in str(error.value)
