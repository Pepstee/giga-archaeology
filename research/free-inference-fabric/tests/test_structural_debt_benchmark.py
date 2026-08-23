from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "benchmarks/fabric-structural-debt-001/verify_candidate.py"
PACKET_SHA256 = "be20698dff9fe65831ea3529308bd8d2253e3cc62e5796d1695e2beedab99775"
EXPECTED = {
    "cli_module_size": (
        {"name": "physical_lines", "value": 1116, "unit": "lines"},
        ["src/giga_inference_fabric/cli.py:1"],
    ),
    "build_parser_span": (
        {"name": "definition_span", "value": 218, "unit": "lines"},
        ["src/giga_inference_fabric/cli.py:890"],
    ),
    "duplicated_worker_run_construction": (
        {"name": "shared_construction_calls", "value": 9, "unit": "calls"},
        ["src/giga_inference_fabric/cli.py:698", "src/giga_inference_fabric/cli.py:789"],
    ),
    "experiment_store_span": (
        {"name": "class_span", "value": 410, "unit": "lines"},
        ["src/giga_inference_fabric/store.py:73"],
    ),
    "opencode_adapter_span": (
        {"name": "class_span", "value": 174, "unit": "lines"},
        ["src/giga_inference_fabric/providers.py:142"],
    ),
}


def valid_candidate() -> dict:
    return {
        "schema": "giga.structural-debt-report.v1",
        "project": "giga-free-inference-fabric",
        "source_packet_sha256": PACKET_SHA256,
        "findings": [
            {
                "id": finding_id,
                "metric": metric,
                "impact": f"The measured {finding_id} increases bounded maintenance and review cost.",
                "remediation": f"Extract one coherent {finding_id} responsibility behind a tested internal contract.",
                "confidence": "inferred",
                "sources": anchors,
            }
            for finding_id, (metric, anchors) in EXPECTED.items()
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


def test_structural_debt_accepts_all_ast_derived_metrics(tmp_path: Path):
    result = verify(tmp_path, valid_candidate())
    assert result.returncode == 0, result.stdout
    assert "ast_metrics=5/5" in result.stdout


def test_structural_debt_rejects_missing_and_invented_metrics(tmp_path: Path):
    missing = valid_candidate()
    missing["findings"].pop()
    result = verify(tmp_path, missing)
    assert result.returncode == 1
    assert "all five" in result.stdout

    invented = valid_candidate()
    invented["findings"][0]["metric"]["value"] = 9999
    result = verify(tmp_path, invented)
    assert result.returncode == 1
    assert "metric is incorrect" in result.stdout
