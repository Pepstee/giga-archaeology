from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "benchmarks/fabric-architecture-map-001/verify_candidate.py"
PACKET_SHA256 = "caada6897d0f4db28a3d5371b39c3bed5f5f1cf7207efd5926088530a178edda"
COMPONENT_ANCHORS = {
    "benchmarks": "src/giga_inference_fabric/benchmarks.py:13",
    "catalogue": "src/giga_inference_fabric/catalogue.py:28",
    "cli": "src/giga_inference_fabric/cli.py:890",
    "engine": "src/giga_inference_fabric/engine.py:34",
    "evaluators": "src/giga_inference_fabric/evaluators.py:51",
    "models": "src/giga_inference_fabric/models.py:37",
    "providers": "src/giga_inference_fabric/providers.py:142",
    "source_packets": "src/giga_inference_fabric/source_packets.py:80",
    "store": "src/giga_inference_fabric/store.py:73",
    "studies": "src/giga_inference_fabric/studies.py:25",
}
EDGE_ANCHORS = {
    ("catalogue", "models"): "src/giga_inference_fabric/catalogue.py:8",
    ("cli", "benchmarks"): "src/giga_inference_fabric/cli.py:14",
    ("cli", "catalogue"): "src/giga_inference_fabric/cli.py:15",
    ("cli", "engine"): "src/giga_inference_fabric/cli.py:16",
    ("cli", "evaluators"): "src/giga_inference_fabric/cli.py:17",
    ("cli", "models"): "src/giga_inference_fabric/cli.py:18",
    ("cli", "providers"): "src/giga_inference_fabric/cli.py:19",
    ("cli", "source_packets"): "src/giga_inference_fabric/cli.py:26",
    ("cli", "store"): "src/giga_inference_fabric/cli.py:27",
    ("cli", "studies"): "src/giga_inference_fabric/cli.py:28",
    ("engine", "evaluators"): "src/giga_inference_fabric/engine.py:10",
    ("engine", "models"): "src/giga_inference_fabric/engine.py:11",
    ("engine", "providers"): "src/giga_inference_fabric/engine.py:12",
    ("engine", "store"): "src/giga_inference_fabric/engine.py:13",
    ("evaluators", "models"): "src/giga_inference_fabric/evaluators.py:12",
    ("providers", "models"): "src/giga_inference_fabric/providers.py:15",
    ("store", "models"): "src/giga_inference_fabric/store.py:10",
    ("studies", "models"): "src/giga_inference_fabric/studies.py:8",
}


def valid_candidate() -> dict:
    return {
        "schema": "giga.architecture-map.v1",
        "project": "giga-free-inference-fabric",
        "source_packet_sha256": PACKET_SHA256,
        "components": [
            {
                "id": component,
                "responsibility": f"Owns the bounded {component} responsibility and its contracts.",
                "sources": [anchor],
            }
            for component, anchor in COMPONENT_ANCHORS.items()
        ],
        "edges": [
            {
                "from": source,
                "to": target,
                "kind": "imports",
                "confidence": "certain",
                "evidence": [anchor],
            }
            for (source, target), anchor in EDGE_ANCHORS.items()
        ],
        "risks": [
            {
                "statement": "The command entrypoint imports many internal modules and may accumulate coupling.",
                "confidence": "inferred",
                "sources": ["src/giga_inference_fabric/cli.py:14"],
            },
            {
                "statement": "Persistent experiment evidence depends on a single store module boundary.",
                "confidence": "low",
                "sources": ["src/giga_inference_fabric/store.py:73"],
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


def test_architecture_benchmark_accepts_complete_source_bound_map(tmp_path: Path):
    result = verify(tmp_path, valid_candidate())
    assert result.returncode == 0, result.stdout
    assert "VERIFIED" in result.stdout


def test_architecture_benchmark_rejects_missing_edge_and_false_certainty(tmp_path: Path):
    missing_edge = valid_candidate()
    missing_edge["edges"].pop()
    result = verify(tmp_path, missing_edge)
    assert result.returncode == 1
    assert "every and only" in result.stdout

    false_certainty = valid_candidate()
    false_certainty["risks"][0]["confidence"] = "certain"
    result = verify(tmp_path, false_certainty)
    assert result.returncode == 1
    assert "must not be labelled certain" in result.stdout
