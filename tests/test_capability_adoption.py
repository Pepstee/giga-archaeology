from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from twin_core.capability_adoption import (
    CANDIDATE_FEED_SCHEMA,
    LEGACY_CANDIDATE_FEED_SCHEMA,
    CapabilityAdoptionError,
    compile_adoption_registry,
    inspect_capability_manifest,
    observe_liveness,
    require_active,
    require_declared_active,
    verify_declared_active,
)
from scripts.capability_adoption_gate import (
    main as capability_gate_main,
)


CANONICAL_RETROSPECTIVE_FEED = "fixtures/retrospective.json"

OBSERVED = "2026-08-29T08:00:00Z"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _self_hash(value: dict) -> dict:
    material = dict(value)
    material.pop("self_sha256", None)
    value["self_sha256"] = _sha(
        json.dumps(
            material, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    )
    return value


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _record(root: Path, relative: str) -> dict:
    raw = (root / relative).read_bytes()
    return {"path": relative, "sha256": _sha(raw), "bytes": len(raw)}


def _canonical_candidate_feed(root: Path) -> None:
    feed = {
        "schema": LEGACY_CANDIDATE_FEED_SCHEMA,
        "producer": "giga.archaeologist.fixture",
        "inventory_manifest_sha256": "a" * 64,
        "generated_at": "2026-08-29T07:30:00Z",
        "candidates": [],
        "self_sha256": "",
    }
    _write_json(root / CANONICAL_RETROSPECTIVE_FEED, _self_hash(feed))


def _git_value(root: Path, *arguments: str) -> str:
    return (
        subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=True,
            stdout=subprocess.PIPE,
        )
        .stdout.decode("ascii", "strict")
        .strip()
    )


def _git_object_record(root: Path, relative: str) -> dict:
    commit = _git_value(root, "rev-parse", "HEAD")
    tree = _git_value(root, "rev-parse", "HEAD^{tree}")
    blob = _git_value(root, "rev-parse", f"HEAD:{relative}")
    raw = subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", blob],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "update-ref",
            "refs/remotes/origin/reviewed-module",
            commit,
        ],
        check=True,
    )
    return {
        "kind": "git-object-file",
        "repo_alias": "giga-user",
        "commit": commit,
        "tree": tree,
        "path": relative,
        "git_blob_oid": blob,
        "sha256": _sha(raw),
        "bytes": len(raw),
        "source_status": "TRACKED_CLEAN_HEAD",
    }


def _v2_candidate_feed(source: dict, **candidate_changes: object) -> dict:
    candidate = {
        "candidate_id": "archaeologist-mapper-disconnected",
        "capability_id": "archaeologist-mapper",
        "disposition": "DISCONNECTED",
        "owner_hint": "reviewed-producer-owner",
        "source_refs": [source],
        "entrypoint_hints": ["giga-archaeologist mapper-capability-feed"],
        "reason": "Accepted implementation has no adopted consumer manifest.",
    }
    candidate.update(candidate_changes)
    return _self_hash(
        {
            "schema": CANDIDATE_FEED_SCHEMA,
            "producer": "giga.archaeologist.fixture-v2",
            "inventory_manifest_sha256": "b" * 64,
            "generated_at": "2026-08-29T07:30:00Z",
            "candidates": [candidate],
            "self_sha256": "",
        }
    )


def _fixture(
    root: Path, *, status: str = "PASS", next_check: str = "2026-08-30T08:00:00Z"
) -> None:
    _canonical_candidate_feed(root)
    for relative, content in (
        ("src/owner.py", "print('ok')\n"),
        ("config/settings.json", "{}\n"),
        ("proofs/proof.json", '{"status":"PASS"}\n'),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest = {
        "schema": "giga.capability-adoption-manifest.v2",
        "id": "fixture-capability",
        "owner": "fixture/owner",
        "responsibility": "Prove the adoption boundary.",
        "claim": "ACTIVE",
        "implementation_paths": ["src/owner.py"],
        "configuration_paths": ["config/settings.json"],
        "proof_paths": ["proofs/proof.json"],
        "entrypoint": {"argv": ["python3", "src/owner.py"], "working_directory": "."},
        "consumer": {
            "id": "fixture-consumer",
            "entrypoint": {
                "argv": ["python3", "src/owner.py"],
                "working_directory": ".",
            },
        },
        "runtime": {
            "kind": "local",
            "deployment_id": "fixture-runtime",
            "availability_argv": ["python3", "src/owner.py"],
        },
        "affected_evidence": [{"kind": "test", "path": "proofs/proof.json"}],
        "trigger": {"kind": "manual", "identity": "fixture-trigger"},
        "authority": {
            "capabilities": ["fixture.read"],
            "privacy": "faceless",
            "external_effects": False,
            "vault_required": False,
        },
        "recovery": {
            "status_argv": ["python3", "src/owner.py"],
            "reconcile_argv": [],
            "disable_argv": [],
        },
        "liveness_receipt": "capabilities/receipts/fixture-capability.json",
    }
    manifest_path = root / "capabilities/manifests/fixture-capability.json"
    _write_json(manifest_path, manifest)
    receipt = {
        "schema": "giga.capability-liveness-receipt.v2",
        "capability_id": "fixture-capability",
        "manifest_sha256": _sha(manifest_path.read_bytes()),
        "observed_at": "2026-08-29T07:00:00Z",
        "status": status,
        "implementation": [_record(root, "src/owner.py")],
        "configuration": [_record(root, "config/settings.json")],
        "proofs": [_record(root, "proofs/proof.json")],
        "entrypoint": manifest["entrypoint"],
        "consumer": manifest["consumer"],
        "runtime": manifest["runtime"],
        "affected_evidence": manifest["affected_evidence"],
        "trigger": manifest["trigger"],
        "authority": manifest["authority"],
        "recovery": manifest["recovery"],
        "last_success_at": "2026-08-29T07:00:00Z" if status == "PASS" else None,
        "last_successful_use_at": "2026-08-29T06:59:00Z",
        "last_failure_at": "2026-08-29T07:00:00Z" if status == "FAIL" else None,
        "next_check_at": next_check,
        "verification": {
            "argv": ["python3", "src/owner.py"],
            "exit_code": 0 if status == "PASS" else 1,
            "stdout_sha256": _sha(b"ok\n"),
            "stdout_bytes": 3,
        },
        "self_sha256": "",
    }
    _write_json(root / manifest["liveness_receipt"], _self_hash(receipt))


def _registry(root: Path, **kwargs) -> dict:
    kwargs.setdefault("require_git_head", False)
    return compile_adoption_registry(root, OBSERVED, **kwargs)


def _commit(root: Path) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Artiom Gutu",
        "GIT_AUTHOR_EMAIL": "gutu.artiom444@gmail.com",
        "GIT_COMMITTER_NAME": "Artiom Gutu",
        "GIT_COMMITTER_EMAIL": "gutu.artiom444@gmail.com",
    }
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q", str(root)], check=True, env=env)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, env=env)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-qm", "fixture"], check=True, env=env
    )


def test_active_requires_current_exact_owner_evidence(tmp_path: Path) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    registry = _registry(tmp_path, require_git_head=True)
    capability = require_active(registry, "fixture-capability")
    assert capability["state"] == "ACTIVE"
    assert capability["execution_authority_granted"] is False
    assert registry["execution_authority_granted"] is False


def test_active_requires_a_distinct_last_successful_use(tmp_path: Path) -> None:
    _fixture(tmp_path)
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["last_successful_use_at"] = None
    _write_json(receipt_path, _self_hash(receipt))
    registry = _registry(tmp_path)
    capability = registry["capabilities"][0]
    assert capability["state"] == "BROKEN"
    assert "last_successful_use_at" in capability["reason"]


def test_missing_receipt_is_adopted_unproven_and_refuses(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / "capabilities/receipts/fixture-capability.json").unlink()
    registry = _registry(tmp_path)
    assert registry["capabilities"][0]["state"] == "ADOPTED_UNPROVEN"
    with pytest.raises(CapabilityAdoptionError, match="current-HEAD"):
        require_active(registry, "fixture-capability")


def test_source_or_configuration_drift_is_stale(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / "config/settings.json").write_text('{"drift":true}\n', encoding="utf-8")
    registry = _registry(tmp_path)
    assert registry["capabilities"][0]["state"] == "STALE"
    assert "configuration differs" in registry["capabilities"][0]["reason"]


def test_expired_and_failed_liveness_never_become_active(tmp_path: Path) -> None:
    _fixture(tmp_path, next_check="2026-08-29T07:59:59Z")
    assert _registry(tmp_path)["capabilities"][0]["state"] == "STALE"
    _fixture(tmp_path, status="FAIL")
    assert _registry(tmp_path)["capabilities"][0]["state"] == "DEGRADED"


@pytest.mark.parametrize(
    ("status", "next_check", "expected_state"),
    [
        ("FAIL", "2026-08-30T08:00:00Z", "DEGRADED"),
        ("PASS", "2026-08-29T07:59:59Z", "STALE"),
    ],
)
def test_liveness_report_preserves_nonactive_state(
    tmp_path: Path, status: str, next_check: str, expected_state: str
) -> None:
    _fixture(tmp_path, status=status, next_check=next_check)
    _commit(tmp_path)
    report = observe_liveness(tmp_path, _registry(tmp_path, require_git_head=True))
    assert report["capabilities"][0]["state"] == expected_state
    assert report["capabilities"][0]["live_check"]["performed"] is False
    assert report["summary"]["states"][expected_state] == 1
    material = dict(report)
    recorded = material.pop("report_sha256")
    assert recorded == _sha(
        json.dumps(
            material, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    )


def test_operator_markdown_report_exposes_degraded_state(
    tmp_path: Path, capsys
) -> None:
    _fixture(tmp_path, status="FAIL")
    _commit(tmp_path)
    result = capability_gate_main(
        [
            "report",
            "--format",
            "markdown",
            "--root",
            str(tmp_path),
            "--observed-at",
            OBSERVED,
        ]
    )
    assert result == 2
    output = capsys.readouterr().out
    assert "# GIGA capability liveness" in output
    assert "| `DEGRADED` | 1 |" in output
    assert (
        "| fixture-capability | fixture-consumer | fixture-runtime | `ACTIVE` | `DEGRADED` |"
        in output
    )
    assert "Execution authority granted: `false`" in output


def test_report_failure_cannot_be_masked_by_a_later_healthy_observation(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    observations = iter(((1, b"failed\n"), (0, b"ok\n")))

    def observe_once(*_args, **_kwargs):
        return next(observations)

    monkeypatch.setattr(
        "twin_core.capability_adoption._run_read_only_status", observe_once
    )
    argv = ["--root", str(tmp_path), "--observed-at", OBSERVED]
    assert capability_gate_main(["report", "--format", "markdown", *argv]) == 2
    report = capsys.readouterr().out
    assert "| `DEGRADED` | 1 |" in report
    assert capability_gate_main(["enforce-claims", *argv]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_registry_tampering_cannot_turn_a_refusal_active(tmp_path: Path) -> None:
    _fixture(tmp_path, status="FAIL")
    _commit(tmp_path)
    registry = _registry(tmp_path, require_git_head=True)
    registry["capabilities"][0]["state"] = "ACTIVE"
    with pytest.raises(CapabilityAdoptionError, match="self hash differs"):
        require_active(registry, "fixture-capability")


@pytest.mark.parametrize(
    ("status", "next_check", "state"),
    [
        ("FAIL", "2026-08-30T08:00:00Z", "DEGRADED"),
        ("PASS", "2026-08-29T07:59:59Z", "STALE"),
    ],
)
def test_declared_active_enforcement_rejects_noncurrent_claims(
    tmp_path: Path, status: str, next_check: str, state: str
) -> None:
    _fixture(tmp_path, status=status, next_check=next_check)
    _commit(tmp_path)
    registry = _registry(tmp_path, require_git_head=True)
    assert registry["capabilities"][0]["state"] == state
    with pytest.raises(
        CapabilityAdoptionError,
        match=rf"declared ACTIVE capability is not current: fixture-capability \({state}\)",
    ):
        require_declared_active(registry)


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS sandbox-exec")
def test_declared_active_enforcement_passes_all_current_claims(tmp_path: Path) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    registry = _registry(tmp_path, require_git_head=True)
    declared = require_declared_active(registry)
    assert [item["id"] for item in declared] == ["fixture-capability"]
    verified = verify_declared_active(tmp_path, registry)
    assert [item["id"] for item in verified] == ["fixture-capability"]


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS sandbox-exec")
def test_declared_active_enforcement_rejects_fabricated_owner_output(
    tmp_path: Path,
) -> None:
    _fixture(tmp_path)
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["verification"]["stdout_sha256"] = "a" * 64
    receipt["verification"]["stdout_bytes"] = 2
    _write_json(receipt_path, _self_hash(receipt))
    _commit(tmp_path)
    registry = _registry(tmp_path, require_git_head=True)
    assert require_declared_active(registry)[0]["state"] == "ACTIVE"
    with pytest.raises(
        CapabilityAdoptionError, match="owner status differs from its receipt"
    ):
        verify_declared_active(tmp_path, registry)


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS sandbox-exec")
def test_live_report_marks_fabricated_owner_output_broken(tmp_path: Path) -> None:
    _fixture(tmp_path)
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["verification"]["stdout_sha256"] = "a" * 64
    _write_json(receipt_path, _self_hash(receipt))
    _commit(tmp_path)
    report = observe_liveness(tmp_path, _registry(tmp_path, require_git_head=True))
    capability = report["capabilities"][0]
    assert capability["state"] == "BROKEN"
    assert capability["live_check"]["status"] == "FAIL"
    assert capability["reason"] == "live owner status differs from its receipt"


def test_enforce_claims_cli_is_fail_closed(tmp_path: Path, capsys) -> None:
    _fixture(tmp_path, status="FAIL")
    _commit(tmp_path)
    result = capability_gate_main(
        ["enforce-claims", "--root", str(tmp_path), "--observed-at", OBSERVED]
    )
    assert result == 2
    assert "declared ACTIVE capability is not current" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS sandbox-exec")
def test_enforce_claims_cli_blocks_owner_status_filesystem_effects(
    tmp_path: Path, capsys
) -> None:
    _fixture(tmp_path)
    owner = tmp_path / "src/owner.py"
    owner.write_text(
        "from pathlib import Path\n"
        "Path('config/settings.json').write_text('{\"drift\":true}\\n')\n"
        "print('ok')\n",
        encoding="utf-8",
    )
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["implementation"] = [_record(tmp_path, "src/owner.py")]
    _write_json(receipt_path, _self_hash(receipt))
    _commit(tmp_path)
    result = capability_gate_main(
        ["enforce-claims", "--root", str(tmp_path), "--observed-at", OBSERVED]
    )
    assert result == 2
    assert "owner status differs from its receipt" in capsys.readouterr().err
    assert (tmp_path / "config/settings.json").read_text(encoding="utf-8") == "{}\n"


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS sandbox-exec")
def test_enforce_claims_cli_blocks_unrelated_owner_write(
    tmp_path: Path, capsys
) -> None:
    _fixture(tmp_path)
    owner = tmp_path / "src/owner.py"
    owner.write_text(
        "from pathlib import Path\n"
        "Path('UNAUTHORIZED_EFFECT.txt').write_text('effect')\n"
        "print('ok')\n",
        encoding="utf-8",
    )
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["implementation"] = [_record(tmp_path, "src/owner.py")]
    _write_json(receipt_path, _self_hash(receipt))
    _commit(tmp_path)
    result = capability_gate_main(
        ["enforce-claims", "--root", str(tmp_path), "--observed-at", OBSERVED]
    )
    assert result == 2
    assert "owner status differs from its receipt" in capsys.readouterr().err
    assert not (tmp_path / "UNAUTHORIZED_EFFECT.txt").exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS sandbox-exec")
def test_enforce_claims_cli_blocks_owner_network(tmp_path: Path, capsys) -> None:
    _fixture(tmp_path)
    owner = tmp_path / "src/owner.py"
    owner.write_text(
        "import socket\n"
        "socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'x', ('127.0.0.1', 9))\n"
        "print('ok')\n",
        encoding="utf-8",
    )
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["implementation"] = [_record(tmp_path, "src/owner.py")]
    _write_json(receipt_path, _self_hash(receipt))
    _commit(tmp_path)
    result = capability_gate_main(
        ["enforce-claims", "--root", str(tmp_path), "--observed-at", OBSERVED]
    )
    assert result == 2
    assert "owner status differs from its receipt" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS sandbox-exec")
def test_enforce_claims_cli_terminates_oversized_output(tmp_path: Path, capsys) -> None:
    _fixture(tmp_path)
    owner = tmp_path / "src/owner.py"
    owner.write_text(
        "import os\nchunk = b'x' * 65536\nfor _ in range(82): os.write(1, chunk)\n",
        encoding="utf-8",
    )
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["implementation"] = [_record(tmp_path, "src/owner.py")]
    _write_json(receipt_path, _self_hash(receipt))
    _commit(tmp_path)
    result = capability_gate_main(
        ["enforce-claims", "--root", str(tmp_path), "--observed-at", OBSERVED]
    )
    assert result == 2
    assert "owner status output is too large" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS sandbox-exec")
def test_owner_status_runtime_may_be_exactly_allowed_under_home(
    tmp_path: Path, monkeypatch
) -> None:
    _fixture(tmp_path)
    with tempfile.TemporaryDirectory(
        dir=Path.home(), prefix=".giga-status-runtime-"
    ) as runtime_dir:
        real_python = sys.executable
        runtime = Path(runtime_dir)
        runtime.chmod(0o770)
        home_python = runtime / "bin/python3"
        home_python.parent.mkdir(mode=0o770)
        home_python.write_text(
            f'#!/bin/sh\nexec {shlex.quote(real_python)} "$@"\n', encoding="utf-8"
        )
        home_python.chmod(0o770)
        monkeypatch.setattr(
            "twin_core.capability_adoption.sys.executable", str(home_python)
        )
        monkeypatch.setattr(
            "twin_core.capability_adoption.sys.base_prefix", str(runtime)
        )
        argv = [str(home_python), "src/owner.py"]
        manifest_path = tmp_path / "capabilities/manifests/fixture-capability.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["recovery"]["status_argv"] = argv
        manifest["runtime"]["availability_argv"] = argv
        _write_json(manifest_path, manifest)
        receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["manifest_sha256"] = _sha(manifest_path.read_bytes())
        receipt["recovery"] = manifest["recovery"]
        receipt["runtime"] = manifest["runtime"]
        receipt["verification"]["argv"] = argv
        _write_json(receipt_path, _self_hash(receipt))
        _commit(tmp_path)
        registry = _registry(tmp_path, require_git_head=True)
        assert verify_declared_active(tmp_path, registry)[0]["state"] == "ACTIVE"


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS sandbox-exec")
def test_owner_status_timeout_survives_closed_output_pipes(
    tmp_path: Path, monkeypatch
) -> None:
    _fixture(tmp_path)
    owner = tmp_path / "src/owner.py"
    owner.write_text(
        "import os, time\nos.close(1)\nos.close(2)\ntime.sleep(60)\n",
        encoding="utf-8",
    )
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["implementation"] = [_record(tmp_path, "src/owner.py")]
    receipt["verification"]["stdout_sha256"] = _sha(b"")
    receipt["verification"]["stdout_bytes"] = 0
    _write_json(receipt_path, _self_hash(receipt))
    _commit(tmp_path)
    registry = _registry(tmp_path, require_git_head=True)
    monkeypatch.setattr("twin_core.capability_adoption.STATUS_TIMEOUT_SECONDS", 0.3)
    started = __import__("time").monotonic()
    with pytest.raises(CapabilityAdoptionError, match="owner status timed out"):
        verify_declared_active(tmp_path, registry)
    assert __import__("time").monotonic() - started < 2





def test_retrospective_socket_is_status_only(tmp_path: Path) -> None:
    _fixture(tmp_path)
    feed_path = tmp_path / "inventory/candidates.json"
    feed = {
        "schema": LEGACY_CANDIDATE_FEED_SCHEMA,
        "producer": "giga.archaeologist",
        "inventory_manifest_sha256": "b" * 64,
        "generated_at": "2026-08-29T07:30:00Z",
        "candidates": [
            {
                "candidate_id": "legacy-mail-reader-v1",
                "capability_id": "market-employer-response-tracking",
                "disposition": "DORMANT_ADOPTABLE",
                "owner_hint": "market-aligner/JAA",
                "source_refs": [_record(tmp_path, "src/owner.py")],
                "entrypoint_hints": ["legacy.mail:poll"],
                "reason": "Useful source exists but no adopted entrypoint or liveness proof exists.",
            }
        ],
        "self_sha256": "",
    }
    _write_json(feed_path, _self_hash(feed))
    _commit(tmp_path)
    registry = _registry(
        tmp_path,
        candidate_feeds=("inventory/candidates.json",),
        require_git_head=True,
    )
    candidate = registry["retrospective_socket"]["candidates"][0]
    assert candidate["state"] == "DORMANT_ADOPTABLE"
    assert candidate["execution_authority_granted"] is False
    assert registry["retrospective_socket"]["promotion_authority"] is False
    with pytest.raises(CapabilityAdoptionError, match="not uniquely registered"):
        require_active(registry, "market-employer-response-tracking")


def test_liveness_report_exposes_only_pathless_disconnected_summary(
    tmp_path: Path,
) -> None:
    _fixture(tmp_path)
    feed_path = tmp_path / "inventory/candidates.json"
    feed = {
        "schema": LEGACY_CANDIDATE_FEED_SCHEMA,
        "producer": "giga.archaeologist",
        "inventory_manifest_sha256": "b" * 64,
        "generated_at": "2026-08-29T07:30:00Z",
        "candidates": [
            {
                "candidate_id": "implemented-disconnected-v1",
                "capability_id": "implemented-disconnected",
                "disposition": "DISCONNECTED",
                "owner_hint": "private-owner-hint-not-for-report",
                "source_refs": [_record(tmp_path, "src/owner.py")],
                "entrypoint_hints": ["private/path/entrypoint.py"],
                "reason": "Private path details must stay out of the public report.",
            }
        ],
        "self_sha256": "",
    }
    _write_json(feed_path, _self_hash(feed))
    _commit(tmp_path)
    registry = _registry(
        tmp_path,
        candidate_feeds=("inventory/candidates.json",),
        require_git_head=True,
    )
    report = observe_liveness(tmp_path, registry)
    assert report["implemented_but_disconnected"] == [
        {
            "candidate_id": "implemented-disconnected-v1",
            "capability_id": "implemented-disconnected",
            "state": "DISCONNECTED",
            "has_entrypoint_hint": True,
            "evidence_source_count": 1,
            "evidence_source_kinds": ["consumer-head-file"],
        }
    ]
    serialized = json.dumps(report["implemented_but_disconnected"])
    assert "private-owner-hint" not in serialized
    assert "private/path" not in serialized


def test_v2_feed_verifies_cross_branch_git_object_evidence(tmp_path: Path) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    source = _git_object_record(tmp_path, "src/owner.py")
    feed_path = tmp_path / "inventory/candidates-v2.json"
    _write_json(feed_path, _v2_candidate_feed(source))
    _commit(tmp_path)

    registry = _registry(
        tmp_path,
        candidate_feeds=("inventory/candidates-v2.json",),
        require_git_head=True,
    )
    candidate = registry["retrospective_socket"]["candidates"][0]
    assert candidate["capability_id"] == "archaeologist-mapper"
    assert candidate["source_refs"] == [source]
    assert registry["retrospective_socket"]["promotion_authority"] is False
    report = observe_liveness(tmp_path, registry)
    assert report["implemented_but_disconnected"] == [
        {
            "candidate_id": "archaeologist-mapper-disconnected",
            "capability_id": "archaeologist-mapper",
            "state": "DISCONNECTED",
            "has_entrypoint_hint": True,
            "evidence_source_count": 1,
            "evidence_source_kinds": ["git-object-file"],
        }
    ]
    serialized = json.dumps(report["implemented_but_disconnected"])
    assert "reviewed-producer-owner" not in serialized
    assert "src/owner.py" not in serialized


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("repo_alias", "untrusted-repository", "repository is not trusted"),
        ("tree", "0" * 40, "tree differs"),
        ("git_blob_oid", "0" * 40, "blob identity differs"),
        ("sha256", "0" * 64, "source bytes differ"),
        ("bytes", 999, "source bytes differ"),
        ("source_status", "UNKNOWN", "source status is invalid"),
    ),
)
def test_v2_git_object_evidence_fails_closed(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    source = _git_object_record(tmp_path, "src/owner.py")
    source[field] = value
    _write_json(tmp_path / "inventory/candidates-v2.json", _v2_candidate_feed(source))
    with pytest.raises(CapabilityAdoptionError, match=message):
        _registry(
            tmp_path,
            candidate_feeds=("inventory/candidates-v2.json",),
            require_git_head=False,
        )


def test_v2_clean_head_source_requires_remote_tip(tmp_path: Path) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    source = _git_object_record(tmp_path, "src/owner.py")
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "update-ref",
            "-d",
            "refs/remotes/origin/reviewed-module",
        ],
        check=True,
    )
    _write_json(tmp_path / "inventory/candidates-v2.json", _v2_candidate_feed(source))
    with pytest.raises(CapabilityAdoptionError, match="not retained by a remote"):
        _registry(
            tmp_path,
            candidate_feeds=("inventory/candidates-v2.json",),
            require_git_head=False,
        )


def test_v2_source_refs_reject_duplicate_git_object_identity(tmp_path: Path) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    source = _git_object_record(tmp_path, "src/owner.py")
    feed = _v2_candidate_feed(source)
    feed["candidates"][0]["source_refs"] = [source, dict(source)]
    _write_json(tmp_path / "inventory/candidates-v2.json", _self_hash(feed))
    with pytest.raises(CapabilityAdoptionError, match="duplicate identities"):
        _registry(
            tmp_path,
            candidate_feeds=("inventory/candidates-v2.json",),
            require_git_head=False,
        )


def test_v2_unknown_disposition_is_not_a_candidate(tmp_path: Path) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    source = _git_object_record(tmp_path, "src/owner.py")
    feed = _v2_candidate_feed(source, disposition="UNKNOWN")
    _write_json(tmp_path / "inventory/candidates-v2.json", feed)
    with pytest.raises(CapabilityAdoptionError, match="disposition is invalid"):
        _registry(
            tmp_path,
            candidate_feeds=("inventory/candidates-v2.json",),
            require_git_head=False,
        )


def test_retrospective_candidate_cannot_duplicate_adopted_capability(
    tmp_path: Path,
) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    source = _git_object_record(tmp_path, "src/owner.py")
    feed = _v2_candidate_feed(source, capability_id="fixture-capability")
    _write_json(tmp_path / "inventory/candidates-v2.json", feed)
    with pytest.raises(
        CapabilityAdoptionError, match="cannot remain retrospective candidates"
    ):
        _registry(
            tmp_path,
            candidate_feeds=("inventory/candidates-v2.json",),
            require_git_head=False,
        )











def test_feed_source_drift_and_future_feed_refuse(tmp_path: Path) -> None:
    _fixture(tmp_path)
    feed = {
        "schema": LEGACY_CANDIDATE_FEED_SCHEMA,
        "producer": "giga.archaeologist",
        "inventory_manifest_sha256": "b" * 64,
        "generated_at": "2026-08-30T07:30:00Z",
        "candidates": [],
        "self_sha256": "",
    }
    _write_json(tmp_path / "inventory/candidates.json", _self_hash(feed))
    with pytest.raises(CapabilityAdoptionError, match="dated after"):
        _registry(tmp_path, candidate_feeds=("inventory/candidates.json",))


def test_retrospective_sources_must_also_match_current_head(tmp_path: Path) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    source = tmp_path / "legacy/untracked.py"
    source.parent.mkdir(parents=True)
    source.write_text("def dormant(): return True\n", encoding="utf-8")
    feed = {
        "schema": LEGACY_CANDIDATE_FEED_SCHEMA,
        "producer": "giga.archaeologist",
        "inventory_manifest_sha256": "b" * 64,
        "generated_at": "2026-08-29T07:30:00Z",
        "candidates": [
            {
                "candidate_id": "legacy-untracked-v1",
                "capability_id": "legacy-untracked",
                "disposition": "DORMANT_ADOPTABLE",
                "owner_hint": "legacy",
                "source_refs": [_record(tmp_path, "legacy/untracked.py")],
                "entrypoint_hints": [],
                "reason": "Inventory observation awaiting adoption.",
            }
        ],
        "self_sha256": "",
    }
    feed_path = tmp_path / "inventory/candidates.json"
    _write_json(feed_path, _self_hash(feed))
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "inventory/candidates.json"], check=True
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Artiom Gutu",
            "-c",
            "user.email=gutu.artiom444@gmail.com",
            "commit",
            "-qm",
            "feed",
        ],
        check=True,
    )
    with pytest.raises(CapabilityAdoptionError, match="missing from HEAD"):
        _registry(
            tmp_path,
            candidate_feeds=("inventory/candidates.json",),
            require_git_head=True,
        )


def test_current_head_provenance_rejects_self_rehashed_worktree_mutation(
    tmp_path: Path,
) -> None:
    _fixture(tmp_path)
    _commit(tmp_path)
    assert (
        _registry(tmp_path, require_git_head=True)["capabilities"][0]["state"]
        == "ACTIVE"
    )

    proof = tmp_path / "proofs/proof.json"
    proof.write_text('{"status":"PASS","changed":true}\n', encoding="utf-8")
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["proofs"] = [_record(tmp_path, "proofs/proof.json")]
    _write_json(receipt_path, _self_hash(receipt))
    with pytest.raises(CapabilityAdoptionError, match="working tree differs from HEAD"):
        _registry(tmp_path, require_git_head=True)





def test_public_default_refuses_uncommitted_authority(tmp_path: Path) -> None:
    _fixture(tmp_path)
    with pytest.raises(CapabilityAdoptionError, match="missing from HEAD"):
        compile_adoption_registry(tmp_path, OBSERVED)


def test_pass_cannot_hide_later_failure_or_different_verifier(tmp_path: Path) -> None:
    _fixture(tmp_path)
    receipt_path = tmp_path / "capabilities/receipts/fixture-capability.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["observed_at"] = "2026-08-29T07:45:00Z"
    receipt["last_failure_at"] = "2026-08-29T07:30:00Z"
    _write_json(receipt_path, _self_hash(receipt))
    result = _registry(tmp_path)["capabilities"][0]
    assert result["state"] == "BROKEN"
    assert "later failure" in result["reason"]

    _fixture(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["verification"]["argv"] = ["true"]
    _write_json(receipt_path, _self_hash(receipt))
    result = _registry(tmp_path)["capabilities"][0]
    assert result["state"] == "BROKEN"
    assert "owner status command" in result["reason"]

    _fixture(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["verification"]["exit_code"] = False
    _write_json(receipt_path, _self_hash(receipt))
    result = _registry(tmp_path)["capabilities"][0]
    assert result["state"] == "BROKEN"
    assert "exit code" in result["reason"]





def test_cli_only_reads_explicit_feeds(tmp_path, capsys):
    _fixture(tmp_path)
    _commit(tmp_path)
    args = ["status", "--root", str(tmp_path), "--observed-at", OBSERVED]
    assert capability_gate_main(args) == 0
    assert json.loads(capsys.readouterr().out)["retrospective_socket"]["feeds"] == []
    explicit = args + ["--candidate-feed", CANONICAL_RETROSPECTIVE_FEED]
    assert capability_gate_main(explicit) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["retrospective_socket"]["feeds"]) == 1
    assert result["execution_authority_granted"] is False
    assert capability_gate_main(explicit + ["--candidate-feed", CANONICAL_RETROSPECTIVE_FEED]) == 2
    capsys.readouterr()
    (tmp_path / CANONICAL_RETROSPECTIVE_FEED).unlink()
    assert capability_gate_main(args) == 0
    capsys.readouterr()
    assert capability_gate_main(explicit) == 2


def test_linux_owner_execution_refuses_before_launch(tmp_path, monkeypatch):
    import twin_core.capability_adoption as module
    monkeypatch.setattr(module.sys, "platform", "linux")
    def forbidden(*args, **kwargs):
        raise AssertionError("unrestricted launch")
    monkeypatch.setattr(module.subprocess, "Popen", forbidden)
    with pytest.raises(CapabilityAdoptionError, match="macOS read-only sandbox"):
        module._run_read_only_status(tmp_path, tmp_path, ["true"], {}, "fixture")


def test_shipped_contracts_match_synthetic_documents(tmp_path):
    _fixture(tmp_path)
    root = Path(__file__).resolve().parents[1]
    for contract, document in [
        ('capability-adoption-manifest', 'capabilities/manifests/fixture-capability.json'),
        ('capability-liveness-receipt', 'capabilities/receipts/fixture-capability.json'),
    ]:
        schema = json.loads((root / f'contracts/{contract}.v2.schema.json').read_text())
        value = json.loads((tmp_path / document).read_text())
        assert set(schema['required']) == set(value)
        assert schema['properties']['schema']['const'] == value['schema']
    for family in ['capability-adoption-manifest', 'capability-liveness-receipt', 'retrospective-capability-candidates']:
        for version in [1, 2]:
            schema = json.loads((root / f'contracts/{family}.v{version}.schema.json').read_text())
            assert schema['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
            assert schema['additionalProperties'] is False


@pytest.mark.parametrize("version", [1, 2])
def test_manifest_inspection_is_strict_and_non_authorizing(tmp_path: Path, version: int) -> None:
    _fixture(tmp_path)
    relative = "capabilities/manifests/fixture-capability.json"
    path = tmp_path / relative
    manifest = json.loads(path.read_text())
    if version == 1:
        manifest["schema"] = "giga.capability-adoption-manifest.v1"
        for field in ("consumer", "runtime", "affected_evidence"):
            del manifest[field]
        _write_json(path, manifest)
    inspected = inspect_capability_manifest(tmp_path, relative)
    assert inspected["id"] == "fixture-capability"
    assert inspected["owner"] == "fixture/owner"
    assert inspected["implementation_paths"] == ["src/owner.py"]
    assert inspected["manifest_sha256"] == _sha(path.read_bytes())
    assert inspected["declaration_only"] is True
    assert inspected["canonicality_claimed"] is False
    assert inspected["execution_authority_granted"] is False
    if version == 1:
        with pytest.raises(CapabilityAdoptionError, match="wrong schema"):
            _registry(tmp_path)
    manifest["unexpected"] = True
    _write_json(path, manifest)
    with pytest.raises(CapabilityAdoptionError, match="wrong schema"):
        inspect_capability_manifest(tmp_path, relative)


def test_manifest_inspection_rejects_invalid_legacy_authority_and_paths(tmp_path: Path) -> None:
    _fixture(tmp_path)
    relative = "capabilities/manifests/fixture-capability.json"
    path = tmp_path / relative
    manifest = json.loads(path.read_text())
    manifest["schema"] = "giga.capability-adoption-manifest.v1"
    for field in ("consumer", "runtime", "affected_evidence"):
        del manifest[field]
    manifest["implementation_paths"] = ["../outside.py"]
    _write_json(path, manifest)
    with pytest.raises(CapabilityAdoptionError):
        inspect_capability_manifest(tmp_path, relative)
    manifest["implementation_paths"] = ["src/owner.py"]
    manifest["authority"]["unexpected"] = True
    _write_json(path, manifest)
    with pytest.raises(CapabilityAdoptionError):
        inspect_capability_manifest(tmp_path, relative)
