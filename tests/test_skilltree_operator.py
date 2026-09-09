"""Black-box assurance for the evidence-backed SkillTree registry."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/skills/skilltree-operator/scripts/audit_tree.py"
EXPORT = ROOT / "outputs/skilltree-export-2026-07-22"
EVIDENCE = ROOT / "deploy/skills/skilltree-operator/references/evidence-map.json"

SPEC = importlib.util.spec_from_file_location("skilltree_audit_tree", SCRIPT)
audit_tree = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_tree)


@pytest.fixture
def lane_scratch(request) -> Path:
    """Unique scratch dir inside the source root (gitignored audit-work/)."""
    scratch = Path(tempfile.mkdtemp(prefix="slice1-", dir=ROOT / "audit-work"))
    request.addfinalizer(lambda: shutil.rmtree(scratch, ignore_errors=True))
    return scratch


def export_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(EXPORT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(EXPORT.rglob("*"))
        if path.is_file()
    }


def run_audit(
    lane_scratch: Path, evidence: Path = EVIDENCE
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ROOT),
            "--export",
            str(EXPORT),
            "--evidence-map",
            str(evidence),
            "--output",
            str(lane_scratch / "registry.json"),
            "--report",
            str(lane_scratch / "report.md"),
            "--skill-root",
            str(ROOT / "deploy/skills"),
        ],
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_real_audit_covers_every_job_without_modifying_export(
    lane_scratch: Path,
) -> None:
    before = export_hashes()
    result = run_audit(lane_scratch)
    assert result.returncode == 0, result.stderr
    registry = json.loads((lane_scratch / "registry.json").read_text(encoding="utf-8"))
    assert registry["jobs_total"] == 137
    assert len(registry["jobs"]) == 137
    assert registry["hub"]["status"] == "implemented"
    assert sum(registry["counts"].values()) == 137
    deck = next(item for item in registry["jobs"] if item["job"] == "Deck Production")
    assert deck["status"] == "implemented"
    assert deck["evidence_missing"] == []
    assert export_hashes() == before


def test_missing_evidence_cannot_claim_implemented(lane_scratch: Path) -> None:
    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    document["jobs"]["Agent Evaluation"]["evidence"] = ["missing-proof.json"]
    evidence = lane_scratch / "evidence.json"
    evidence.write_text(json.dumps(document), encoding="utf-8")
    result = run_audit(lane_scratch, evidence)
    assert result.returncode == 0, result.stderr
    registry = json.loads((lane_scratch / "registry.json").read_text(encoding="utf-8"))
    row = next(item for item in registry["jobs"] if item["job"] == "Agent Evaluation")
    assert row["status"] == "documented"
    assert row["evidence_missing"] == ["missing-proof.json"]


def test_unknown_job_and_path_escape_fail_closed(lane_scratch: Path) -> None:
    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    document["jobs"]["Invented Capability"] = {
        "status": "implemented",
        "evidence": ["00_MASTER.md"],
    }
    unknown = lane_scratch / "unknown.json"
    unknown.write_text(json.dumps(document), encoding="utf-8")
    assert run_audit(lane_scratch, unknown).returncode != 0

    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    document["jobs"]["Agent Evaluation"]["evidence"] = ["../outside"]
    escaped = lane_scratch / "escaped.json"
    escaped.write_text(json.dumps(document), encoding="utf-8")
    result = run_audit(lane_scratch, escaped)
    assert result.returncode != 0
    assert "escapes evidence root" in result.stderr


# ---------------------------------------------------------------------------
# Controlled fixtures: complete miniature source/evidence environments so the
# slice semantics are provable in a clean clone without private corpus bytes.
# ---------------------------------------------------------------------------


JOBS = ["Alpha Capability", "Beta Missing Proof", "Gamma Skill Thing", "Delta External"]


def make_fixture(base: Path) -> tuple[Path, Path]:
    """Return (source_root, evidence_root) for a complete controlled replay."""
    source = base / "source"
    evidence = base / "evidence"
    (source / "export" / "data").mkdir(parents=True)
    (source / "references").mkdir(parents=True)
    (source / "deploy" / "skills" / "gamma-skill-thing").mkdir(parents=True)
    (source / "skilltree").mkdir(parents=True)
    (evidence / "proof").mkdir(parents=True)
    (evidence / "seam").mkdir(parents=True)
    (evidence / "outside").mkdir(parents=True)

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
            "files": [{"path": f"{audit_tree.normalized(name)}.py"}],
        }
        for name in JOBS
    }
    (source / "export" / "data" / "tree.json").write_text(
        json.dumps(tree), encoding="utf-8"
    )
    (source / "export" / "data" / "playbook.json").write_text(
        json.dumps(playbook), encoding="utf-8"
    )

    evidence_map = {
        "schema_version": "1.0",
        "hub": {"evidence": ["proof/hub-note.md"], "note": "fixture hub"},
        "jobs": {
            "Alpha Capability": {
                "status": "implemented",
                "evidence": ["proof/alpha-proof.txt"],
                "note": "fixture alpha",
            },
            "Beta Missing Proof": {
                "status": "implemented",
                "evidence": ["proof/absent.txt"],
            },
            "Delta External": {
                "status": "external",
                "evidence": ["proof/delta-local.md"],
                "external_evidence": [str(evidence / "seam" / "delta-seal.txt")],
            },
        },
    }
    (source / "references" / "evidence-map.json").write_text(
        json.dumps(evidence_map), encoding="utf-8"
    )

    (source / "README.md").write_text("local seam note\n", encoding="utf-8")
    (source / "deploy" / "skills" / "gamma-skill-thing" / "SKILL.md").write_text(
        "---\nname: Gamma Skill Thing\ndescription: fixture\n---\n", encoding="utf-8"
    )
    (evidence / "proof" / "alpha-proof.txt").write_text(
        "alpha durable proof\n", encoding="utf-8"
    )
    (evidence / "proof" / "delta-local.md").write_text(
        "delta local proof\n", encoding="utf-8"
    )
    (evidence / "proof" / "hub-note.md").write_text("hub note\n", encoding="utf-8")
    (evidence / "seam" / "delta-seal.txt").write_text(
        "external seam\n", encoding="utf-8"
    )
    (evidence / "outside" / "secret.txt").write_text("outside\n", encoding="utf-8")
    return source, evidence


def run_fixture(
    source: Path,
    evidence_root: Path | None = None,
    check: bool = False,
    compat_report: Path | None = None,
    output: Path | None = None,
    report: Path | None = None,
    evidence_map: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        "--root",
        str(source),
        "--export",
        str(source / "export"),
        "--evidence-map",
        str(evidence_map or source / "references" / "evidence-map.json"),
        "--skill-root",
        str(source / "deploy" / "skills"),
        "--output",
        str(output or source / "skilltree" / "registry.json"),
        "--report",
        str(report or source / "skilltree" / "IMPLEMENTATION_STATUS.md"),
    ]
    if evidence_root is not None:
        command += ["--evidence-root", str(evidence_root)]
    if check:
        command += [
            "--check",
            "--compat-report",
            str(
                compat_report
                or report
                or source / "skilltree" / "IMPLEMENTATION_REPORT.md"
            ),
        ]
    return subprocess.run(command, text=True, capture_output=True, timeout=30)


def tree_hash(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() or path.is_symlink()
    }


def test_evidence_root_separation_replay_and_read_only_guarantee(
    tmp_path: Path,
) -> None:
    source, evidence = make_fixture(tmp_path)
    before = tree_hash(evidence)

    result = run_fixture(source, evidence_root=evidence)
    assert result.returncode == 0, result.stderr
    registry = json.loads(
        (source / "skilltree" / "registry.json").read_text(encoding="utf-8")
    )
    assert registry["jobs_total"] == 4
    assert registry["counts"] == {
        "available": 1,
        "documented": 1,
        "external": 1,
        "implemented": 1,
    }
    rows = {row["job"]: row for row in registry["jobs"]}
    assert rows["Alpha Capability"]["status"] == "implemented"
    assert rows["Alpha Capability"]["evidence_found"] == ["proof/alpha-proof.txt"]
    assert rows["Beta Missing Proof"]["status"] == "documented"
    assert rows["Beta Missing Proof"]["evidence_missing"] == ["proof/absent.txt"]
    assert rows["Gamma Skill Thing"]["status"] == "available"
    delta = rows["Delta External"]
    assert delta["status"] == "external"
    assert delta["external_evidence_found"] == [
        str(evidence / "seam" / "delta-seal.txt")
    ]

    assert tree_hash(evidence) == before, "evidence root must never be written"

    first_registry = (source / "skilltree" / "registry.json").read_bytes()
    first_report = (source / "skilltree" / "IMPLEMENTATION_STATUS.md").read_bytes()
    replay = run_fixture(source, evidence_root=evidence)
    assert replay.returncode == 0, replay.stderr
    assert (source / "skilltree" / "registry.json").read_bytes() == first_registry
    assert (
        source / "skilltree" / "IMPLEMENTATION_STATUS.md"
    ).read_bytes() == first_report


def test_default_evidence_root_is_the_source_root(tmp_path: Path) -> None:
    source, _ = make_fixture(tmp_path)
    result = run_fixture(source)
    assert result.returncode == 0, result.stderr
    registry = json.loads(
        (source / "skilltree" / "registry.json").read_text(encoding="utf-8")
    )
    rows = {row["job"]: row for row in registry["jobs"]}
    assert rows["Alpha Capability"]["status"] == "documented"
    assert rows["Alpha Capability"]["evidence_missing"] == ["proof/alpha-proof.txt"]


def test_check_mode_accepts_canonical_and_rejects_each_drifted_surface(
    tmp_path: Path,
) -> None:
    source, evidence = make_fixture(tmp_path)
    assert run_fixture(source, evidence_root=evidence).returncode == 0
    (source / "skilltree" / "IMPLEMENTATION_REPORT.md").symlink_to(
        "IMPLEMENTATION_STATUS.md"
    )

    ok = run_fixture(source, evidence_root=evidence, check=True)
    assert ok.returncode == 0, ok.stderr
    assert json.loads(ok.stdout)["check"] == "ok"

    registry_path = source / "skilltree" / "registry.json"
    canonical_registry = registry_path.read_bytes()
    registry_path.write_bytes(
        canonical_registry.replace(b'"jobs_total": 4', b'"jobs_total": 3')
    )
    drifted = run_fixture(source, evidence_root=evidence, check=True)
    assert drifted.returncode == 1
    assert "registry" in drifted.stderr
    registry_path.write_bytes(canonical_registry)

    report_path = source / "skilltree" / "IMPLEMENTATION_STATUS.md"
    canonical_report = report_path.read_bytes()
    report_path.write_bytes(canonical_report + b"stale tail\n")
    drifted = run_fixture(source, evidence_root=evidence, check=True)
    assert drifted.returncode == 1
    assert "report" in drifted.stderr
    report_path.write_bytes(canonical_report)

    assert run_fixture(source, evidence_root=evidence, check=True).returncode == 0


def test_compatibility_surface_cannot_silently_diverge(tmp_path: Path) -> None:
    source, evidence = make_fixture(tmp_path)
    assert run_fixture(source, evidence_root=evidence).returncode == 0
    compat = source / "skilltree" / "IMPLEMENTATION_REPORT.md"

    missing = run_fixture(source, evidence_root=evidence, check=True)
    assert missing.returncode == 1
    assert "compatibility surface must be a symlink" in missing.stderr

    compat.write_bytes((source / "skilltree" / "IMPLEMENTATION_STATUS.md").read_bytes())
    copy = run_fixture(source, evidence_root=evidence, check=True)
    assert copy.returncode == 1
    assert "compatibility surface must be a symlink" in copy.stderr

    compat.unlink()
    compat.symlink_to("../outside/secret.txt")
    wrong = run_fixture(source, evidence_root=evidence, check=True)
    assert wrong.returncode == 1
    assert "compatibility surface symlink diverged" in wrong.stderr

    compat.unlink()
    compat.symlink_to("IMPLEMENTATION_STATUS.md")
    good = run_fixture(source, evidence_root=evidence, check=True)
    assert good.returncode == 0, good.stderr


def test_generation_outputs_are_constrained_to_the_source_root(tmp_path: Path) -> None:
    source, evidence = make_fixture(tmp_path)

    outside = run_fixture(
        source,
        output=tmp_path / "elsewhere" / "registry.json",
        report=source / "skilltree" / "IMPLEMENTATION_STATUS.md",
    )
    assert outside.returncode != 0
    assert "must stay inside the giga-user source root" in outside.stderr

    inside_evidence = run_fixture(
        source,
        evidence_root=evidence,
        output=evidence / "registry.json",
        report=source / "skilltree" / "IMPLEMENTATION_STATUS.md",
    )
    assert inside_evidence.returncode != 0
    assert (
        "refusing to use a path inside the read-only evidence root"
        in inside_evidence.stderr
    )
    assert not (evidence / "registry.json").exists()


def test_check_mode_requires_explicit_compat_surface(tmp_path: Path) -> None:
    source, evidence = make_fixture(tmp_path)
    command = [
        sys.executable,
        str(SCRIPT),
        "--root",
        str(source),
        "--export",
        str(source / "export"),
        "--evidence-map",
        str(source / "references" / "evidence-map.json"),
        "--evidence-root",
        str(evidence),
        "--output",
        str(source / "skilltree" / "registry.json"),
        "--report",
        str(source / "skilltree" / "IMPLEMENTATION_STATUS.md"),
    ]
    bare = subprocess.run(
        command + ["--check"], text=True, capture_output=True, timeout=30
    )
    assert bare.returncode == 2
    assert "--check requires --compat-report" in bare.stderr

    stray = subprocess.run(
        command
        + ["--compat-report", str(source / "skilltree" / "IMPLEMENTATION_REPORT.md")],
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert stray.returncode == 2
    assert "--compat-report is only valid together with --check" in stray.stderr


def test_evidence_root_escape_and_symlink_escape_fail_closed(tmp_path: Path) -> None:
    source, evidence = make_fixture(tmp_path)
    map_path = source / "references" / "evidence-map.json"
    document = json.loads(map_path.read_text(encoding="utf-8"))

    document["jobs"]["Alpha Capability"]["evidence"] = ["../outside/secret.txt"]
    map_path.write_text(json.dumps(document), encoding="utf-8")
    parent_escape = run_fixture(source, evidence_root=evidence)
    assert parent_escape.returncode != 0
    assert "escapes evidence root" in parent_escape.stderr

    outside = tmp_path / "outside-secret.txt"
    outside.write_text("outside evidence root\n", encoding="utf-8")
    link = evidence / "proof" / "escape-link.txt"
    link.symlink_to(outside)
    document["jobs"]["Alpha Capability"]["evidence"] = ["proof/escape-link.txt"]
    map_path.write_text(json.dumps(document), encoding="utf-8")
    symlink_escape = run_fixture(source, evidence_root=evidence)
    assert symlink_escape.returncode != 0
    assert "escapes evidence root" in symlink_escape.stderr


def test_source_authority_and_relative_evidence_fail_closed(tmp_path: Path) -> None:
    source, evidence = make_fixture(tmp_path)
    outside_map = tmp_path / "outside-evidence-map.json"
    outside_map.write_bytes((source / "references" / "evidence-map.json").read_bytes())
    outside = run_fixture(source, evidence_root=evidence, evidence_map=outside_map)
    assert outside.returncode != 0
    assert (
        "evidence map must be a regular file inside the source root" in outside.stderr
    )

    map_path = source / "references" / "evidence-map.json"
    document = json.loads(map_path.read_text(encoding="utf-8"))
    document["jobs"]["Alpha Capability"]["evidence"] = [
        str(evidence / "proof" / "alpha-proof.txt")
    ]
    map_path.write_text(json.dumps(document), encoding="utf-8")
    absolute = run_fixture(source, evidence_root=evidence)
    assert absolute.returncode != 0
    assert "evidence must be an exact repository-relative path" in absolute.stderr


def test_atomic_pair_rollback_restores_originals_and_cleans_temps(
    tmp_path: Path, monkeypatch
) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.md"
    first.write_bytes(b"original-first\n")
    second.write_bytes(b"original-second\n")

    real_replace = audit_tree._os_replace
    calls = {"count": 0}

    def flaky_replace(source_path: Path, target: Path) -> None:
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("injected second-replace failure")
        real_replace(source_path, target)

    monkeypatch.setattr(audit_tree, "_os_replace", flaky_replace)
    with pytest.raises(
        audit_tree.AtomicPairWriteError, match="injected second-replace failure"
    ):
        audit_tree.write_atomic_pair(
            [
                (first, b"updated-first\n"),
                (second, b"updated-second\n"),
            ]
        )

    assert first.read_bytes() == b"original-first\n"
    assert second.read_bytes() == b"original-second\n"
    assert list(tmp_path.glob(".*.new")) == []
    assert list(tmp_path.glob(".*.backup")) == []

    monkeypatch.setattr(audit_tree, "_os_replace", real_replace)
    audit_tree.write_atomic_pair(
        [
            (first, b"updated-first\n"),
            (second, b"updated-second\n"),
        ]
    )
    assert first.read_bytes() == b"updated-first\n"
    assert second.read_bytes() == b"updated-second\n"


def test_tracked_surfaces_preserve_pinned_decisions_and_compat_symlink() -> None:
    registry = json.loads(
        (ROOT / "skilltree" / "implementation-registry.json").read_text("utf-8")
    )
    pinned = {
        "implemented": 7,
        "external": 2,
        "partial": 1,
        "available": 5,
        "blocked": 2,
        "documented": 120,
    }
    assert registry["jobs_total"] == 137
    assert len(registry["jobs"]) == 137
    assert registry["counts"] == pinned
    assert registry["source_export"] == "outputs/skilltree-export-2026-07-22"

    status = (ROOT / "skilltree" / "IMPLEMENTATION_STATUS.md").read_text("utf-8")
    for status_name, count in pinned.items():
        assert f"| {status_name} | {count} |" in status

    compat = ROOT / "skilltree" / "IMPLEMENTATION_REPORT.md"
    assert compat.is_symlink()
    assert (
        compat.resolve() == (ROOT / "skilltree" / "IMPLEMENTATION_STATUS.md").resolve()
    )


def test_real_generation_is_deterministic_across_runs(lane_scratch: Path) -> None:
    first_dir, second_dir = lane_scratch / "one", lane_scratch / "two"
    first_dir.mkdir()
    second_dir.mkdir()
    first = run_audit(first_dir)
    second = run_audit(second_dir)
    assert first.returncode == 0 and second.returncode == 0, (
        first.stderr + second.stderr
    )
    assert (first_dir / "registry.json").read_bytes() == (
        second_dir / "registry.json"
    ).read_bytes()
    assert (first_dir / "report.md").read_bytes() == (
        second_dir / "report.md"
    ).read_bytes()
