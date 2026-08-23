from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "benchmarks/fabric-config-audit-001/verify_candidate.py"
PACKET_SHA256 = "c1aec9a2a7787b44f9e76642ad099910fa1d5a99fc297480a348dd31e64318cd"
FACTS = {
    "package_identity": "pyproject.toml:6",
    "python_floor": "pyproject.toml:9",
    "runtime_dependencies": "pyproject.toml:10",
    "console_entrypoint": "pyproject.toml:13",
    "state_ignored": ".gitignore:1",
    "single_invocation_guard": "opencode/giga-output-budget.js:26",
    "exact_model_guard": "opencode/giga-output-budget.js:27",
}
FINDINGS = {
    "package_version_drift": ("certain", ["README.md:1", "pyproject.toml:7"]),
    "ruff_cache_not_ignored": ("certain", [".gitignore:4"]),
    "build_dependency_not_reproducibly_pinned": ("inferred", ["pyproject.toml:2"]),
    "development_test_dependency_undeclared": (
        "inferred", ["README.md:234", "pyproject.toml:10"],
    ),
}
CHECKS = {
    "studies_v1_digest": ["config/studies.json:2", "config/studies.json.sha256:1"],
    "studies_v2_digest": ["config/studies-v2.json:2", "config/studies-v2.json.sha256:1"],
    "comparative_v2_digest": [
        "config/studies-comparative-v2.json:2",
        "config/studies-comparative-v2.json.sha256:1",
    ],
    "workload_catalogue_schema": ["config/workloads.json:2"],
    "output_budget_admission": ["opencode/giga-output-budget.js:28"],
}


def valid_candidate() -> dict:
    return {
        "schema": "giga.config-audit.v1",
        "project": "giga-free-inference-fabric",
        "source_packet_sha256": PACKET_SHA256,
        "facts": [
            {
                "id": item_id,
                "value": f"The frozen configuration explicitly defines the {item_id} value.",
                "sources": [anchor],
            }
            for item_id, anchor in FACTS.items()
        ],
        "findings": [
            {
                "id": item_id,
                "impact": f"The {item_id} condition reduces reproducibility or configuration clarity.",
                "remediation": f"Resolve {item_id} in one bounded configuration-only change with checks.",
                "confidence": confidence,
                "sources": anchors,
            }
            for item_id, (confidence, anchors) in FINDINGS.items()
        ],
        "integrity_checks": [
            {
                "id": item_id,
                "status": "pass",
                "summary": f"The frozen packet objectively satisfies the {item_id} integrity check.",
                "sources": anchors,
            }
            for item_id, anchors in CHECKS.items()
        ],
    }


def verify(tmp_path: Path, candidate: dict) -> subprocess.CompletedProcess[str]:
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    environment = {key: os.environ[key] for key in ("PATH", "LANG") if key in os.environ}
    environment["GIGA_CANDIDATE_PATH"] = str(candidate_path)
    return subprocess.run(
        ["python3", str(VERIFIER)], cwd=VERIFIER.parent, env=environment,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )


def test_config_audit_accepts_complete_frozen_packet_report(tmp_path: Path):
    result = verify(tmp_path, valid_candidate())
    assert result.returncode == 0, result.stdout
    assert "VERIFIED" in result.stdout


def test_config_audit_rejects_missing_finding_and_false_digest_status(tmp_path: Path):
    missing_finding = valid_candidate()
    missing_finding["findings"].pop()
    result = verify(tmp_path, missing_finding)
    assert result.returncode == 1
    assert "every admitted configuration defect" in result.stdout

    false_status = valid_candidate()
    false_status["integrity_checks"][0]["status"] = "fail"
    result = verify(tmp_path, false_status)
    assert result.returncode == 1
    assert "must report pass" in result.stdout
