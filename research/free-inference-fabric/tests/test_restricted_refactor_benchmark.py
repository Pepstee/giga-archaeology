from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "benchmarks/fabric-source-packet-refactor-001/verify_candidate.py"
PACKET_SHA256 = "cbb53200fa16401afcd5f7151e1baf16764e945d747c7e3940fae33af18206d3"


def candidate(block: str) -> dict:
    return {
        "schema": "giga.restricted-refactor.v1",
        "project": "giga-free-inference-fabric",
        "source_packet_sha256": PACKET_SHA256,
        "refactor": {
            "target": "verify_source_packet",
            "rationale": "Restore canonical builder and verifier equivalence without changing valid packet behaviour.",
            "validation_block": block,
        },
    }


def verify(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(payload), encoding="utf-8")
    environment = {key: os.environ[key] for key in ("PATH", "LANG") if key in os.environ}
    environment["GIGA_CANDIDATE_PATH"] = str(candidate_path)
    return subprocess.run(
        ["python3", str(VERIFIER)], cwd=VERIFIER.parent, env=environment,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )


def test_restricted_refactor_preserves_valid_and_rejects_noncanonical_packets(tmp_path: Path):
    block = (
        'if "\\x00" in text or "\\r" in text or any("\\n" in line for line in row["lines"]):\n'
        '    raise ValueError("source packet contains non-canonical line content")'
    )
    result = verify(tmp_path, candidate(block))
    assert result.returncode == 0, result.stdout
    assert "valid=4 invalid=3 ast_restricted=true" in result.stdout


def test_restricted_refactor_rejects_unsafe_and_incomplete_blocks(tmp_path: Path):
    unsafe = (
        'if __import__("os"):\n'
        '    raise ValueError("unsafe")'
    )
    result = verify(tmp_path, candidate(unsafe))
    assert result.returncode == 1
    assert "forbidden" in result.stdout

    incomplete = (
        'if "\\r" in text:\n'
        '    raise ValueError("only carriage return handled")'
    )
    result = verify(tmp_path, candidate(incomplete))
    assert result.returncode == 1
    assert "failed a hidden" in result.stdout
