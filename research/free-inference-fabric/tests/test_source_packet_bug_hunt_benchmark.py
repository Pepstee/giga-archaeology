from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "benchmarks/fabric-source-packet-bug-hunt-001/verify_candidate.py"
PACKET_SHA256 = "cbb53200fa16401afcd5f7151e1baf16764e945d747c7e3940fae33af18206d3"
SOURCE = "src/giga_inference_fabric/source_packets.py"


def valid_candidate() -> dict:
    return {
        "schema": "giga.source-packet-bug-report.v1",
        "project": "giga-free-inference-fabric",
        "source_packet_sha256": PACKET_SHA256,
        "findings": [
            {
                "id": "embedded-newline-canonicalization",
                "defect": "The verifier accepts one logical row containing an embedded newline.",
                "impact": "Line counts and path-line anchors can disagree with canonical builder output.",
                "confidence": "certain",
                "sources": [f"{SOURCE}:67", f"{SOURCE}:162"],
                "reproducer": {"kind": "embedded_newline", "payload": "first\nsecond"},
                "expected": "Verifier should reject non-canonical embedded line separators.",
                "observed": "Verifier accepts one line while the builder produces two canonical lines.",
            },
            {
                "id": "unsupported-control-acceptance",
                "defect": "The verifier accepts hash-consistent external content containing carriage return.",
                "impact": "Untrusted packets bypass the same control-character policy enforced by the builder.",
                "confidence": "certain",
                "sources": [f"{SOURCE}:60", f"{SOURCE}:162"],
                "reproducer": {"kind": "unsupported_control", "payload": "first\rsecond"},
                "expected": "Verifier should reject the unsupported carriage-return content.",
                "observed": "Verifier accepts the packet while the builder rejects identical file bytes.",
            },
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


def test_bug_hunt_reproduces_both_builder_verifier_differentials(tmp_path: Path):
    result = verify(tmp_path, valid_candidate())
    assert result.returncode == 0, result.stdout
    assert "differential_defects=2/2" in result.stdout


def test_bug_hunt_rejects_duplicate_class_and_non_reproducing_payload(tmp_path: Path):
    duplicate = valid_candidate()
    duplicate["findings"][1]["reproducer"] = {
        "kind": "embedded_newline", "payload": "third\nfourth",
    }
    result = verify(tmp_path, duplicate)
    assert result.returncode == 1
    assert "kinds must be unique" in result.stdout

    no_control = valid_candidate()
    no_control["findings"][1]["reproducer"]["payload"] = "ordinary text"
    result = verify(tmp_path, no_control)
    assert result.returncode == 1
    assert "must contain CR or NUL" in result.stdout
