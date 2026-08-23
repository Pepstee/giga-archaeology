from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "benchmarks/fabric-source-packet-tests-001/verify_candidate.py"
PACKET_SHA256 = "cbb53200fa16401afcd5f7151e1baf16764e945d747c7e3940fae33af18206d3"


def file(path: str, content: str) -> dict:
    return {"path": path, "kind": "file", "content": content, "target": None}


def symlink(path: str, target: str) -> dict:
    return {"path": path, "kind": "symlink", "content": None, "target": target}


def expected_ok(count: int, total: int) -> dict:
    return {"status": "ok", "error_pattern": None, "file_count": count, "total_source_bytes": total}


def expected_reject(pattern: str) -> dict:
    return {"status": "reject", "error_pattern": pattern, "file_count": None, "total_source_bytes": None}


def case(
    test_id: str,
    *,
    project: str = "example",
    requested: list[str],
    setup: list[dict],
    expected: dict,
    total_cap: int = 100,
    file_cap: int = 100,
) -> dict:
    return {
        "id": test_id,
        "project": project,
        "requested_files": requested,
        "setup": setup,
        "max_total_bytes": total_cap,
        "max_file_bytes": file_cap,
        "expected": expected,
    }


def valid_candidate() -> dict:
    return {
        "schema": "giga.executable-source-packet-tests.v1",
        "project": "giga-free-inference-fabric",
        "source_packet_sha256": PACKET_SHA256,
        "tests": [
            case(
                "accept-single", requested=["a.py"], setup=[file("a.py", "x=1\n")],
                expected=expected_ok(1, 4),
            ),
            case(
                "accept-sorted-pair", requested=["b.txt", "a.txt"],
                setup=[file("a.txt", ""), file("b.txt", "abc")], expected=expected_ok(2, 3),
            ),
            case(
                "reject-project", project="", requested=["a.py"], setup=[file("a.py", "x")],
                expected=expected_reject("project must be non-empty"),
            ),
            case(
                "reject-traversal", requested=["../outside.py"], setup=[file("a.py", "x")],
                expected=expected_reject("bounded relative"),
            ),
            case(
                "reject-symlink", requested=["link.py"],
                setup=[file("inside.py", "x"), symlink("link.py", "inside.py")],
                expected=expected_reject("symlink"),
            ),
            case(
                "reject-file-cap", requested=["large.txt"], setup=[file("large.txt", "12345")],
                expected=expected_reject("per-file byte cap"), total_cap=10, file_cap=4,
            ),
            case(
                "reject-cr", requested=["cr.txt"], setup=[file("cr.txt", "a\rb")],
                expected=expected_reject("unsupported binary/CR"),
            ),
            case(
                "reject-secret", requested=["secret.txt"],
                setup=[file("secret.txt", "-----BEGIN PRIVATE KEY-----\nnot-real\n")],
                expected=expected_reject("secret pattern"),
            ),
            case(
                "reject-duplicate", requested=["a.py", "a.py"], setup=[file("a.py", "x")],
                expected=expected_reject("duplicate"),
            ),
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


def test_generated_data_suite_passes_reference_and_kills_all_mutants(tmp_path: Path):
    result = verify(tmp_path, valid_candidate())
    assert result.returncode == 0, result.stdout
    assert "reference=9/9 mutants=7/7" in result.stdout


def test_generated_data_suite_rejects_reference_error_and_surviving_mutant(tmp_path: Path):
    wrong_reference = valid_candidate()
    wrong_reference["tests"][0]["expected"]["total_source_bytes"] = 5
    result = verify(tmp_path, wrong_reference)
    assert result.returncode == 1
    assert "fails the frozen reference" in result.stdout

    surviving_secret_mutant = copy.deepcopy(valid_candidate())
    surviving_secret_mutant["tests"][7] = case(
        "reject-secret-name", requested=[".env"], setup=[file(".env", "safe")],
        expected=expected_reject("secret-bearing by policy"),
    )
    result = verify(tmp_path, surviving_secret_mutant)
    assert result.returncode == 1
    assert "secret_detection" in result.stdout
