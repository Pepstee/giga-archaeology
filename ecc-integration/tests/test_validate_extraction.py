from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ecc-integration/scripts/validate_extraction.py"
FINDINGS = ROOT / "ecc-integration/PORTABLE_FINDINGS.json"
AUDIT_SCRIPT = ROOT / "deploy/skills/skilltree-operator/scripts/audit_tree.py"
LIVE_EVIDENCE_ROOT = Path("/Users/admin/Documents/giga-user")

PINNED_COUNTS = {
    "implemented": 7,
    "external": 2,
    "partial": 1,
    "available": 5,
    "blocked": 2,
    "documented": 120,
}

_SPEC = importlib.util.spec_from_file_location("ecc_validate_extraction", SCRIPT)
ecc_validate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ecc_validate)


def _run(*extra: str, findings: Path = FINDINGS) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ROOT),
            "--upstream",
            str(ROOT / "upstreams/ECC"),
            "--findings",
            str(findings),
            *extra,
        ],
        text=True,
        capture_output=True,
        timeout=120,
    )


def _fail_envelope(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode == 2, result.stdout + result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "fail"
    assert set(envelope["error"]) == {"code", "message"}
    return envelope


def test_real_extraction_has_complete_pinned_coverage() -> None:
    result = _run("--evidence-root", str(LIVE_EVIDENCE_ROOT))
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report == {
        "adaptation_candidates": 11,
        "canonical_skills": 278,
        "commit": "96789caaf90501ff9b55bf1b00f1c28cf3fccbeb",
        "inventory_hashes_verified": 3330,
        "ledger_entries": 12,
        "portable_findings": 15,
        "source_files": 3330,
        "staged_specifications": 10,
        "status": "pass",
        "skilltree": {
            "status": "pass",
            "jobs_total": 137,
            "counts": PINNED_COUNTS,
            "authority_sha256": {
                "audit": ecc_validate._sha256(AUDIT_SCRIPT),
                "evidence_map": ecc_validate._sha256(
                    ROOT
                    / "deploy/skills/skilltree-operator/references/evidence-map.json"
                ),
                "tree": (
                    "d6516de61738a1dcebd462ff255328d77d69c47e34c508b37a1eb131f9017dfc"
                ),
                "playbook": (
                    "13d4ed4caad6a5cdb5162e18803202edecf1846ac3c8d039a7f441a6761fd7fe"
                ),
            },
            "registry_sha256": (
                "cd39dfe4167c34a0b0a6fb986d9e9e0144e088575505e8c017aa4dd63c32773a"
            ),
            "status_sha256": (
                "f12a6f82ef180477964bdf44da919583e00705b3a5ac6c97de5012abd8ebcd6c"
            ),
            "compatibility_target": "IMPLEMENTATION_STATUS.md",
        },
    }


def test_extraction_drift_is_reported_before_capability_replay(tmp_path: Path) -> None:
    document = json.loads(FINDINGS.read_text(encoding="utf-8"))
    document["portable_findings"][0]["sources"][0]["sha256"] = "0" * 64
    path = tmp_path / "hash.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = _run("--findings", str(path))
    envelope = _fail_envelope(result)
    assert envelope["error"]["code"] == "extraction-invalid"
    assert "source hash mismatch" in envelope["error"]["message"]


def test_missing_candidate_coverage_fails_closed(tmp_path: Path) -> None:
    document = json.loads(FINDINGS.read_text(encoding="utf-8"))
    del document["candidate_skill_coverage"]["agent-eval"]
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = _run("--findings", str(path))
    envelope = _fail_envelope(result)
    assert envelope["error"]["code"] == "extraction-invalid"
    assert "coverage mismatch" in envelope["error"]["message"]


def test_source_hash_tamper_and_destination_escape_fail_closed(tmp_path: Path) -> None:
    document = json.loads(FINDINGS.read_text(encoding="utf-8"))
    document["portable_findings"][0]["destination"] = "../outside.md"
    path = tmp_path / "escape.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = _run("--findings", str(path))
    envelope = _fail_envelope(result)
    assert "escapes its root" in envelope["error"]["message"]


# ---------------------------------------------------------------------------
# Controlled fixtures: complete miniature SkillTree environments so the gate's
# positive path and every refusal reason are provable in a clean clone.
# ---------------------------------------------------------------------------


JOBS = ["Alpha Capability", "Beta Missing Proof", "Gamma Skill Thing"]


def make_skilltree_fixture(base: Path) -> tuple[Path, Path]:
    source = base / "source"
    evidence = base / "evidence"
    audit_home = source / "deploy" / "skills" / "skilltree-operator" / "scripts"
    audit_home.mkdir(parents=True)
    references = audit_home.parent / "references"
    references.mkdir()
    export = source / "outputs" / "skilltree-export-2026-07-22" / "data"
    export.mkdir(parents=True)
    (source / "deploy" / "skills" / "gamma-skill-thing").mkdir(parents=True)
    (source / "skilltree").mkdir(parents=True)
    (evidence / "proof").mkdir(parents=True)
    shutil.copy2(AUDIT_SCRIPT, audit_home / "audit_tree.py")

    tree = [
        {
            "name": "Operations",
            "functions": [
                {
                    "name": "Build",
                    "jobs": [
                        {
                            "name": name,
                            "desc": "",
                            "level": "autonomous",
                            "skills": [],
                            "tools": [],
                        }
                        for name in JOBS
                    ],
                }
            ],
        }
    ]
    playbook = {
        name: {
            "req": [],
            "human": "",
            "replaces": "",
            "files": [{"path": f"{name.lower().replace(' ', '-')}.py"}],
        }
        for name in JOBS
    }
    (export / "tree.json").write_text(json.dumps(tree), encoding="utf-8")
    (export / "playbook.json").write_text(json.dumps(playbook), encoding="utf-8")
    (references / "evidence-map.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "hub": {"evidence": ["proof/hub-note.md"], "note": "fixture hub"},
                "jobs": {
                    "Alpha Capability": {
                        "status": "implemented",
                        "evidence": ["proof/alpha-proof.txt"],
                    },
                    "Beta Missing Proof": {
                        "status": "implemented",
                        "evidence": ["proof/absent.txt"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (source / "deploy" / "skills" / "gamma-skill-thing" / "SKILL.md").write_text(
        "---\nname: Gamma Skill Thing\ndescription: fixture\n---\n", encoding="utf-8"
    )
    (evidence / "proof" / "alpha-proof.txt").write_text(
        "alpha durable proof\n", encoding="utf-8"
    )
    (evidence / "proof" / "hub-note.md").write_text("hub note\n", encoding="utf-8")

    generated = subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--root",
            str(source),
            "--export",
            str(source / "outputs" / "skilltree-export-2026-07-22"),
            "--evidence-map",
            str(references / "evidence-map.json"),
            "--evidence-root",
            str(evidence),
            "--skill-root",
            str(source / "deploy" / "skills"),
            "--output",
            str(source / "skilltree" / "implementation-registry.json"),
            "--report",
            str(source / "skilltree" / "IMPLEMENTATION_STATUS.md"),
        ],
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert generated.returncode == 0, generated.stderr
    compat = source / "skilltree" / "IMPLEMENTATION_REPORT.md"
    compat.symlink_to("IMPLEMENTATION_STATUS.md")
    return source, evidence


def test_fixture_replay_passes_with_explicit_read_only_evidence_root(
    tmp_path: Path,
) -> None:
    source, evidence = make_skilltree_fixture(tmp_path)
    verdict = ecc_validate.validate_skilltree_truth(source, evidence)
    assert verdict == {
        "status": "pass",
        "jobs_total": 3,
        "counts": {"available": 1, "documented": 1, "implemented": 1},
        "authority_sha256": {
            "audit": ecc_validate._sha256(
                source / "deploy/skills/skilltree-operator/scripts/audit_tree.py"
            ),
            "evidence_map": ecc_validate._sha256(
                source / "deploy/skills/skilltree-operator/references/evidence-map.json"
            ),
            "tree": ecc_validate._sha256(
                source / "outputs/skilltree-export-2026-07-22/data/tree.json"
            ),
            "playbook": ecc_validate._sha256(
                source / "outputs/skilltree-export-2026-07-22/data/playbook.json"
            ),
        },
        "registry_sha256": ecc_validate._sha256(
            source / "skilltree" / "implementation-registry.json"
        ),
        "status_sha256": ecc_validate._sha256(
            source / "skilltree" / "IMPLEMENTATION_STATUS.md"
        ),
        "compatibility_target": "IMPLEMENTATION_STATUS.md",
    }


def test_fixture_replay_rejects_missing_drifted_or_unsafe_states(
    tmp_path: Path,
) -> None:
    source, evidence = make_skilltree_fixture(tmp_path)

    (evidence / "proof" / "alpha-proof.txt").unlink()
    with pytest.raises(ecc_validate.CodedExtractionError) as missing:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert missing.value.code == "skilltree-replay-failed"
    assert "tracked registry differs from canonical generation" in str(missing.value)
    (evidence / "proof" / "alpha-proof.txt").write_text(
        "alpha durable proof\n", encoding="utf-8"
    )

    registry = source / "skilltree" / "implementation-registry.json"
    original_registry = registry.read_bytes()
    registry.write_bytes(original_registry + b"\n")
    with pytest.raises(ecc_validate.CodedExtractionError) as drifted:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert drifted.value.code == "skilltree-replay-failed"
    assert "tracked registry differs" in str(drifted.value)
    registry.write_bytes(original_registry)

    compat = source / "skilltree" / "IMPLEMENTATION_REPORT.md"
    compat.unlink()
    compat.write_bytes((source / "skilltree" / "IMPLEMENTATION_STATUS.md").read_bytes())
    with pytest.raises(ecc_validate.CodedExtractionError) as compat_error:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert compat_error.value.code == "skilltree-replay-failed"
    assert "compatibility surface must be a symlink" in str(compat_error.value)
    compat.unlink()
    compat.symlink_to("IMPLEMENTATION_STATUS.md")

    status = source / "skilltree" / "IMPLEMENTATION_STATUS.md"
    status.write_bytes(status.read_bytes() + b"stale tail\n")
    with pytest.raises(ecc_validate.CodedExtractionError) as status_error:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert status_error.value.code == "skilltree-replay-failed"
    assert "tracked report differs" in str(status_error.value)
    status.write_bytes(status.read_bytes()[: -len(b"stale tail\n")])

    assert ecc_validate.validate_skilltree_truth(source, evidence)["status"] == "pass"

    compat.unlink()
    compat.symlink_to(source / "skilltree" / "IMPLEMENTATION_STATUS.md")
    with pytest.raises(ecc_validate.CodedExtractionError) as absolute_compat:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert absolute_compat.value.code == "skilltree-replay-failed"
    assert "canonical relative target" in str(absolute_compat.value)


def test_replay_refuses_unsafe_inputs(tmp_path: Path) -> None:
    with pytest.raises(ecc_validate.CodedExtractionError) as bad_root:
        ecc_validate.validate_skilltree_truth(ROOT, tmp_path / "absent-evidence")
    assert bad_root.value.code == "skilltree-invalid-input"

    empty = tmp_path / "empty-source"
    empty.mkdir()
    with pytest.raises(ecc_validate.CodedExtractionError) as bare:
        ecc_validate.validate_skilltree_truth(empty, tmp_path)
    assert bare.value.code == "skilltree-invalid-input"
    assert "skilltree audit is missing" in str(bare.value)


def test_child_failure_modes_fail_closed(tmp_path: Path, monkeypatch) -> None:
    source, evidence = make_skilltree_fixture(tmp_path)

    def unreadable(command):
        return subprocess.CompletedProcess(
            command, returncode=0, stdout="not-json", stderr=""
        )

    monkeypatch.setattr(ecc_validate, "_run_child", unreadable)
    with pytest.raises(ecc_validate.CodedExtractionError) as malformed:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert malformed.value.code == "skilltree-child-unreadable"

    def refused(command):
        return subprocess.CompletedProcess(
            command, returncode=0, stdout=json.dumps({"check": "unexpected"}), stderr=""
        )

    monkeypatch.setattr(ecc_validate, "_run_child", refused)
    with pytest.raises(ecc_validate.CodedExtractionError) as wrong_verdict:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert wrong_verdict.value.code == "skilltree-child-unreadable"

    def slow(command):
        raise subprocess.TimeoutExpired(cmd="audit_tree.py", timeout=120)

    monkeypatch.setattr(ecc_validate, "_run_child", slow)
    with pytest.raises(ecc_validate.CodedExtractionError) as timed_out:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert timed_out.value.code == "skilltree-timeout"

    def broken_spawn(command):
        raise OSError("spawn blocked")

    monkeypatch.setattr(ecc_validate, "_run_child", broken_spawn)
    with pytest.raises(ecc_validate.CodedExtractionError) as spawn_error:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert spawn_error.value.code == "skilltree-spawn-error"

    def drifting_child(command):
        return subprocess.CompletedProcess(
            command, returncode=1, stdout="", stderr="DRIFT: tracked registry differs\n"
        )

    monkeypatch.setattr(ecc_validate, "_run_child", drifting_child)
    with pytest.raises(ecc_validate.CodedExtractionError) as child_drift:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert child_drift.value.code == "skilltree-replay-failed"
    assert "DRIFT: tracked registry differs" in str(child_drift.value)


def test_replay_detects_tracked_surface_race(tmp_path: Path, monkeypatch) -> None:
    source, evidence = make_skilltree_fixture(tmp_path)
    registry = source / "skilltree" / "implementation-registry.json"

    def racing_child(command):
        registry.write_bytes(registry.read_bytes() + b"\n")
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout=json.dumps(
                {
                    "check": "ok",
                    "counts": {
                        "available": 1,
                        "documented": 1,
                        "implemented": 1,
                    },
                    "output": str(registry),
                    "report": str(source / "skilltree" / "IMPLEMENTATION_STATUS.md"),
                    "compat_report": str(
                        source / "skilltree" / "IMPLEMENTATION_REPORT.md"
                    ),
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(ecc_validate, "_run_child", racing_child)
    with pytest.raises(ecc_validate.CodedExtractionError) as raced:
        ecc_validate.validate_skilltree_truth(source, evidence)
    assert raced.value.code == "skilltree-replay-raced"
