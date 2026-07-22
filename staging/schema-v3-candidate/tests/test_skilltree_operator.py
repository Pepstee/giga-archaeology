"""Black-box assurance for the evidence-backed SkillTree registry."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/skills/skilltree-operator/scripts/audit_tree.py"
EXPORT = ROOT / "outputs/skilltree-export-2026-07-22"
EVIDENCE = ROOT / "deploy/skills/skilltree-operator/references/evidence-map.json"


def export_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(EXPORT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(EXPORT.rglob("*"))
        if path.is_file()
    }


def run_audit(tmp_path: Path, evidence: Path = EVIDENCE) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root", str(ROOT),
            "--export", str(EXPORT),
            "--evidence-map", str(evidence),
            "--output", str(tmp_path / "registry.json"),
            "--report", str(tmp_path / "report.md"),
            "--skill-root", str(ROOT / "deploy/skills"),
        ],
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_real_audit_covers_every_job_without_modifying_export(tmp_path: Path) -> None:
    before = export_hashes()
    result = run_audit(tmp_path)
    assert result.returncode == 0, result.stderr
    registry = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    assert registry["jobs_total"] == 137
    assert len(registry["jobs"]) == 137
    assert registry["hub"]["status"] == "implemented"
    assert sum(registry["counts"].values()) == 137
    assert export_hashes() == before


def test_missing_evidence_cannot_claim_implemented(tmp_path: Path) -> None:
    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    document["jobs"]["Agent Evaluation"]["evidence"] = ["missing-proof.json"]
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps(document), encoding="utf-8")
    result = run_audit(tmp_path, evidence)
    assert result.returncode == 0, result.stderr
    registry = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    row = next(item for item in registry["jobs"] if item["job"] == "Agent Evaluation")
    assert row["status"] == "documented"
    assert row["evidence_missing"] == ["missing-proof.json"]


def test_unknown_job_and_path_escape_fail_closed(tmp_path: Path) -> None:
    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    document["jobs"]["Invented Capability"] = {"status": "implemented", "evidence": ["00_MASTER.md"]}
    unknown = tmp_path / "unknown.json"
    unknown.write_text(json.dumps(document), encoding="utf-8")
    assert run_audit(tmp_path, unknown).returncode != 0

    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    document["jobs"]["Agent Evaluation"]["evidence"] = ["../outside"]
    escaped = tmp_path / "escaped.json"
    escaped.write_text(json.dumps(document), encoding="utf-8")
    result = run_audit(tmp_path, escaped)
    assert result.returncode != 0
    assert "escapes giga-user root" in result.stderr
