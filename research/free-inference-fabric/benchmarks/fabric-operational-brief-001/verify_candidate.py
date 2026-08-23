from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


PACKET_SHA256 = "caada6897d0f4db28a3d5371b39c3bed5f5f1cf7207efd5926088530a178edda"
PROJECT = "giga-free-inference-fabric"
SOURCE_HASHES = {
    "src/giga_inference_fabric/benchmarks.py": "9a6daf4a6c63e97ed29dcff3b566f1b839171c1436f2d3a9e533c6fe32e78480",
    "src/giga_inference_fabric/catalogue.py": "d42280cd30e0a3b6a89edcdce406dd28f05c5cd518d02873a4bfb6465f6ea86d",
    "src/giga_inference_fabric/cli.py": "3748407c8c52c25de3f3161093378348e32be6831d326a1b4499e57bbce60219",
    "src/giga_inference_fabric/engine.py": "b58e731e7c4b40c26a347644b740d74c76f34cfb068636ea5cade08034d433c5",
    "src/giga_inference_fabric/evaluators.py": "ad868592ce7e21a3da56a547008d16a380211b0dfbfbf0cb72e74904a955ec27",
    "src/giga_inference_fabric/models.py": "4a932423ba04f5a6c5bc308673acf13956f8728ae8b627dbcd71fe82acd04982",
    "src/giga_inference_fabric/providers.py": "d5a49525db692dabcd62634b4c72657563ad36944b15a10f34432ca573e58915",
    "src/giga_inference_fabric/source_packets.py": "6abcab4db74c432195291692523960b9fc4e1633f3bd2a47087fb72020f4d788",
    "src/giga_inference_fabric/store.py": "6be85a91e01c74a0b107ba7dced81fed390115fecbcf6f4bf5ae278081903911",
    "src/giga_inference_fabric/studies.py": "79719def1faac301f5ad0d2177b0722da8e8fb7e34a935b40f945dff60190016",
}
ENTRYPOINTS = {
    "discover": ("src/giga_inference_fabric/cli.py", "def discover("),
    "monitor_once": ("src/giga_inference_fabric/cli.py", "def monitor_once("),
    "queue_add": ("src/giga_inference_fabric/cli.py", "def queue_add("),
    "source_packet": ("src/giga_inference_fabric/cli.py", "def source_packet("),
    "escalate": ("src/giga_inference_fabric/cli.py", "def escalate("),
    "worker_once": ("src/giga_inference_fabric/cli.py", "def worker_once("),
    "run": ("src/giga_inference_fabric/cli.py", "def run("),
}
STATE_STORES = {
    name: ("src/giga_inference_fabric/store.py", f"CREATE TABLE IF NOT EXISTS {name}")
    for name in (
        "experiments", "provider_calls", "model_observations", "solution_patterns",
        "failure_patterns", "benchmarks", "work_queue",
    )
}
FAILURE_PATHS = {
    "no_eligible_models": ("src/giga_inference_fabric/engine.py", "no policy-compatible models"),
    "provider_failure": ("src/giga_inference_fabric/engine.py", "except ProviderError"),
    "stagnation": ("src/giga_inference_fabric/engine.py", "STAGNATION DETECTED"),
    "daily_budget_exhaustion": ("src/giga_inference_fabric/engine.py", "daily remote-call budget exhausted"),
    "benchmark_drift": ("src/giga_inference_fabric/benchmarks.py", "benchmark fixture drift detected"),
    "source_packet_secret": ("src/giga_inference_fabric/source_packets.py", "high-confidence secret pattern"),
    "queue_attempt_exhaustion": ("src/giga_inference_fabric/store.py", '"EXHAUSTED" if'),
}
OPERATING_RULES = {
    "objective_gate_authority": ("src/giga_inference_fabric/engine.py", 'stop_reason = "objective gate passed"'),
    "paid_requires_admission": ("src/giga_inference_fabric/models.py", "not self.allow_paid_escalation"),
    "vault_requires_local_or_zdr": ("src/giga_inference_fabric/models.py", "PrivacyClass.VAULT"),
    "full_cell_budget_before_lease": ("src/giga_inference_fabric/cli.py", "worst_case_remote_calls > remaining"),
    "benchmark_revalidated_before_lease": ("src/giga_inference_fabric/cli.py", "_preflight_queued_benchmark(store, pending)"),
}
ANCHOR = re.compile(r"^(src/giga_inference_fabric/[a-z_]+\.py):([1-9][0-9]*)$")
ROOT = Path(__file__).resolve().parents[2]


def reject(reason: str) -> None:
    print(reason)
    raise SystemExit(1)


def exact_fields(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        reject(f"{label} fields must be exactly {sorted(fields)}")
    return value


def substantive(value: object, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) < 20:
        reject(f"{label} must be a trimmed concrete string of at least 20 characters")
    return value


source_lines: dict[str, list[str]] = {}
for relative, expected_hash in SOURCE_HASHES.items():
    try:
        data = (ROOT / relative).read_bytes()
    except OSError as exc:
        reject(f"bound source unavailable: {relative}: {exc}")
    if hashlib.sha256(data).hexdigest() != expected_hash:
        reject(f"bound source drift: {relative}")
    try:
        source_lines[relative] = data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        reject(f"bound source is no longer UTF-8: {relative}")


def resolve_anchor(value: object) -> tuple[str, str]:
    if not isinstance(value, str):
        reject("source anchor must be a string")
    match = ANCHOR.fullmatch(value)
    if not match or match.group(1) not in source_lines:
        reject(f"source anchor is outside the bound packet: {value}")
    relative, number_text = match.groups()
    number = int(number_text)
    if number > len(source_lines[relative]):
        reject(f"source anchor line is out of range: {value}")
    return relative, source_lines[relative][number - 1]


def verify_evidence(value: object, expected: tuple[str, str], label: str) -> None:
    if not isinstance(value, list) or not value or len(value) > 6 or len(set(value)) != len(value):
        reject(f"{label} must contain one to six unique anchors")
    resolved = [resolve_anchor(anchor) for anchor in value]
    expected_path, expected_token = expected
    if not any(path == expected_path and expected_token in line for path, line in resolved):
        reject(f"{label} lacks its defining source anchor")


def verify_named_section(
    value: object,
    expected: dict[str, tuple[str, str]],
    fields: set[str],
    prose_fields: tuple[str, ...],
    label: str,
) -> None:
    if not isinstance(value, list) or len(value) != len(expected):
        reject(f"{label} must cover every required item exactly once")
    seen: set[str] = set()
    for index, item in enumerate(value):
        exact_fields(item, fields, f"{label}[{index}]")
        item_id = item["id"]
        if not isinstance(item_id, str) or item_id in seen or item_id not in expected:
            reject(f"unknown or duplicate {label} id: {item_id}")
        seen.add(item_id)
        for field in prose_fields:
            substantive(item[field], f"{label}[{index}].{field}")
        verify_evidence(item["sources"], expected[item_id], f"{label}[{index}].sources")
    if seen != set(expected):
        reject(f"{label} coverage is incomplete")


candidate_path = os.environ.get("GIGA_CANDIDATE_PATH")
if not candidate_path:
    reject("GIGA_CANDIDATE_PATH is absent")
candidate = Path(candidate_path)
if not candidate.is_file() or candidate.stat().st_size > 98_304:
    reject("candidate must be a regular JSON file no larger than 98304 bytes")
try:
    payload = json.loads(candidate.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"candidate is not strict UTF-8 JSON: {exc}")

exact_fields(
    payload,
    {"schema", "project", "source_packet_sha256", "entrypoints", "state_stores", "failure_paths", "operating_rules"},
    "top-level",
)
if payload["schema"] != "giga.operational-brief.v1":
    reject("unsupported operational-brief schema")
if payload["project"] != PROJECT or payload["source_packet_sha256"] != PACKET_SHA256:
    reject("candidate is not bound to the admitted project and source packet")

verify_named_section(
    payload["entrypoints"], ENTRYPOINTS, {"id", "responsibility", "sources"},
    ("responsibility",), "entrypoints",
)
verify_named_section(
    payload["state_stores"], STATE_STORES, {"id", "responsibility", "sources"},
    ("responsibility",), "state_stores",
)
verify_named_section(
    payload["failure_paths"], FAILURE_PATHS,
    {"id", "trigger", "containment", "confidence", "sources"},
    ("trigger", "containment"), "failure_paths",
)
if any(item["confidence"] != "certain" for item in payload["failure_paths"]):
    reject("directly encoded failure paths must have confidence=certain")
verify_named_section(
    payload["operating_rules"], OPERATING_RULES, {"id", "statement", "sources"},
    ("statement",), "operating_rules",
)

print("VERIFIED giga.operational-brief.v1 source-bound operational documentation")
