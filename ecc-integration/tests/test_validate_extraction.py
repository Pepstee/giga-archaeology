from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ecc-integration/scripts/validate_extraction.py"
FINDINGS = ROOT / "ecc-integration/PORTABLE_FINDINGS.json"


def _run(findings: Path = FINDINGS) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(ROOT), "--upstream", str(ROOT / "upstreams/ECC"), "--findings", str(findings)],
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_real_extraction_has_complete_pinned_coverage() -> None:
    result = _run()
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
    }


def test_missing_candidate_coverage_fails_closed(tmp_path: Path) -> None:
    document = json.loads(FINDINGS.read_text(encoding="utf-8"))
    del document["candidate_skill_coverage"]["agent-eval"]
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = _run(path)
    assert result.returncode == 2
    assert "coverage mismatch" in result.stdout


def test_source_hash_tamper_and_destination_escape_fail_closed(tmp_path: Path) -> None:
    document = json.loads(FINDINGS.read_text(encoding="utf-8"))
    document["portable_findings"][0]["sources"][0]["sha256"] = "0" * 64
    path = tmp_path / "hash.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = _run(path)
    assert result.returncode == 2
    assert "source hash mismatch" in result.stdout

    document = json.loads(FINDINGS.read_text(encoding="utf-8"))
    document["portable_findings"][0]["destination"] = "../outside.md"
    path = tmp_path / "escape.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = _run(path)
    assert result.returncode == 2
    assert "escapes its root" in result.stdout
