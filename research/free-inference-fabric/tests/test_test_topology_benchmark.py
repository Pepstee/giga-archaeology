from __future__ import annotations

import ast
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks/fabric-test-topology-001"


def candidate() -> dict:
    packet = json.loads((FIXTURE / "source-packet.json").read_text(encoding="utf-8"))
    modules = []
    edges = []
    for row in packet["files"]:
        path = row["path"]
        tree = ast.parse("\n".join(row["lines"]), filename=path)
        tests = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ]
        module_id = Path(path).stem
        modules.append({
            "id": module_id,
            "path": path,
            "test_count": len(tests),
            "responsibility": "Exercises the bounded behaviour represented by this admitted test module.",
            "sources": [f"{path}:{min(node.lineno for node in tests)}"],
        })
        seen = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if not node.module.startswith("giga_inference_fabric"):
                continue
            parts = node.module.split(".")
            target = parts[1] if len(parts) > 1 else "__init__"
            if target in seen:
                continue
            seen.add(target)
            edges.append({
                "from": module_id,
                "to": target,
                "kind": "tests",
                "evidence": [f"{path}:{node.lineno}"],
            })
    return {
        "schema": "giga.test-topology.v1",
        "project": "giga-free-inference-fabric",
        "source_packet_sha256": packet["packet_sha256"],
        "modules": modules,
        "edges": edges,
        "exclusions": [
            {"path": "tests/test_source_packet_generation_benchmark.py", "reason": "secret-pattern-boundary"},
            {"path": "tests/test_source_packets.py", "reason": "secret-pattern-boundary"},
        ],
        "risks": [
            {
                "statement": "The two excluded secret-pattern fixtures require local-only review coverage.",
                "confidence": "inferred",
                "sources": [modules[0]["sources"][0]],
            },
            {
                "statement": "Concentrated test counts may make failures harder to isolate by responsibility.",
                "confidence": "low",
                "sources": [modules[-1]["sources"][0]],
            },
        ],
    }


def run_verifier(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    environment = {**os.environ, "GIGA_CANDIDATE_PATH": str(path)}
    return subprocess.run(
        ["python3", "verify_candidate.py"], cwd=FIXTURE, env=environment,
        text=True, capture_output=True, check=False,
    )


def test_test_topology_accepts_exact_ast_derived_map(tmp_path: Path):
    result = run_verifier(tmp_path, candidate())
    assert result.returncode == 0, result.stdout + result.stderr
    assert "modules=8 tests=58 edges=13 exclusions=2" in result.stdout


def test_test_topology_rejects_invented_count_and_secret_boundary(tmp_path: Path):
    payload = candidate()
    payload["modules"][0]["test_count"] += 1
    result = run_verifier(tmp_path, payload)
    assert result.returncode == 1
    assert "path/count is incorrect" in result.stdout

    payload = candidate()
    payload["exclusions"][0]["reason"] = "not-interesting"
    result = run_verifier(tmp_path, payload)
    assert result.returncode == 1
    assert "exclusion boundary is incorrect" in result.stdout
