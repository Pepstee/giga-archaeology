from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "benchmarks/fabric-operational-brief-001/verify_candidate.py"
PACKET_SHA256 = "caada6897d0f4db28a3d5371b39c3bed5f5f1cf7207efd5926088530a178edda"
ENTRYPOINTS = {
    "discover": "src/giga_inference_fabric/cli.py:171",
    "monitor_once": "src/giga_inference_fabric/cli.py:201",
    "queue_add": "src/giga_inference_fabric/cli.py:501",
    "source_packet": "src/giga_inference_fabric/cli.py:553",
    "escalate": "src/giga_inference_fabric/cli.py:603",
    "worker_once": "src/giga_inference_fabric/cli.py:698",
    "run": "src/giga_inference_fabric/cli.py:789",
}
STATE_STORES = {
    "experiments": "src/giga_inference_fabric/store.py:15",
    "provider_calls": "src/giga_inference_fabric/store.py:30",
    "model_observations": "src/giga_inference_fabric/store.py:36",
    "solution_patterns": "src/giga_inference_fabric/store.py:44",
    "failure_patterns": "src/giga_inference_fabric/store.py:48",
    "benchmarks": "src/giga_inference_fabric/store.py:53",
    "work_queue": "src/giga_inference_fabric/store.py:57",
}
FAILURE_PATHS = {
    "no_eligible_models": "src/giga_inference_fabric/engine.py:74",
    "provider_failure": "src/giga_inference_fabric/engine.py:126",
    "stagnation": "src/giga_inference_fabric/engine.py:183",
    "daily_budget_exhaustion": "src/giga_inference_fabric/engine.py:285",
    "benchmark_drift": "src/giga_inference_fabric/benchmarks.py:69",
    "source_packet_secret": "src/giga_inference_fabric/source_packets.py:62",
    "queue_attempt_exhaustion": "src/giga_inference_fabric/store.py:455",
}
OPERATING_RULES = {
    "objective_gate_authority": "src/giga_inference_fabric/engine.py:167",
    "paid_requires_admission": "src/giga_inference_fabric/models.py:50",
    "vault_requires_local_or_zdr": "src/giga_inference_fabric/models.py:54",
    "full_cell_budget_before_lease": "src/giga_inference_fabric/cli.py:713",
    "benchmark_revalidated_before_lease": "src/giga_inference_fabric/cli.py:728",
}


def valid_candidate() -> dict:
    return {
        "schema": "giga.operational-brief.v1",
        "project": "giga-free-inference-fabric",
        "source_packet_sha256": PACKET_SHA256,
        "entrypoints": [
            {
                "id": item_id,
                "responsibility": f"Executes the bounded {item_id} operation and emits a receipt.",
                "sources": [anchor],
            }
            for item_id, anchor in ENTRYPOINTS.items()
        ],
        "state_stores": [
            {
                "id": item_id,
                "responsibility": f"Persists canonical {item_id} evidence for later verification.",
                "sources": [anchor],
            }
            for item_id, anchor in STATE_STORES.items()
        ],
        "failure_paths": [
            {
                "id": item_id,
                "trigger": f"The encoded {item_id} condition becomes true during bounded execution.",
                "containment": f"Execution follows the explicit {item_id} failure branch and cannot certify success.",
                "confidence": "certain",
                "sources": [anchor],
            }
            for item_id, anchor in FAILURE_PATHS.items()
        ],
        "operating_rules": [
            {
                "id": item_id,
                "statement": f"The runtime unavoidably enforces the {item_id} operating invariant.",
                "sources": [anchor],
            }
            for item_id, anchor in OPERATING_RULES.items()
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


def test_operational_brief_accepts_complete_source_bound_documentation(tmp_path: Path):
    result = verify(tmp_path, valid_candidate())
    assert result.returncode == 0, result.stdout
    assert "VERIFIED" in result.stdout


def test_operational_brief_rejects_missing_store_and_unbound_failure(tmp_path: Path):
    missing_store = valid_candidate()
    missing_store["state_stores"].pop()
    result = verify(tmp_path, missing_store)
    assert result.returncode == 1
    assert "cover every required item" in result.stdout

    bad_anchor = valid_candidate()
    bad_anchor["failure_paths"][0]["sources"] = ["src/giga_inference_fabric/engine.py:1"]
    result = verify(tmp_path, bad_anchor)
    assert result.returncode == 1
    assert "defining source anchor" in result.stdout
