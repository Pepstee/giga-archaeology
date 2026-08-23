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
COMPONENT_SOURCES = {
    "benchmarks": ("src/giga_inference_fabric/benchmarks.py", ("def hash_fixture", "def build_benchmark_contract")),
    "catalogue": ("src/giga_inference_fabric/catalogue.py", ("class WorkloadProfile", "def load_profiles")),
    "cli": ("src/giga_inference_fabric/cli.py", ("def build_parser", "def run")),
    "engine": ("src/giga_inference_fabric/engine.py", ("class ExperimentEngine",)),
    "evaluators": ("src/giga_inference_fabric/evaluators.py", ("class CommandEvaluator", "def evaluator_from_contract")),
    "models": ("src/giga_inference_fabric/models.py", ("class ModelPolicy", "class ExperimentRequest")),
    "providers": ("src/giga_inference_fabric/providers.py", ("class ModelAdapter", "class OpenCodeOpenRouterAdapter")),
    "source_packets": ("src/giga_inference_fabric/source_packets.py", ("SCHEMA =", "def build_source_packet")),
    "store": ("src/giga_inference_fabric/store.py", ("SCHEMA =", "class ExperimentStore")),
    "studies": ("src/giga_inference_fabric/studies.py", ("class StudyDefinition", "def load_studies")),
}
REQUIRED_EDGES = {
    ("catalogue", "models"),
    ("cli", "benchmarks"),
    ("cli", "catalogue"),
    ("cli", "engine"),
    ("cli", "evaluators"),
    ("cli", "models"),
    ("cli", "providers"),
    ("cli", "source_packets"),
    ("cli", "store"),
    ("cli", "studies"),
    ("engine", "evaluators"),
    ("engine", "models"),
    ("engine", "providers"),
    ("engine", "store"),
    ("evaluators", "models"),
    ("providers", "models"),
    ("store", "models"),
    ("studies", "models"),
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


def non_empty_string(value: object, label: str, minimum: int = 1) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) < minimum:
        reject(f"{label} must be a trimmed non-empty string")
    return value


source_lines: dict[str, list[str]] = {}
for relative, expected_hash in SOURCE_HASHES.items():
    path = ROOT / relative
    try:
        data = path.read_bytes()
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
    lines = source_lines[relative]
    if number > len(lines):
        reject(f"source anchor line is out of range: {value}")
    return relative, lines[number - 1]


def anchors(value: object, label: str) -> list[tuple[str, str]]:
    if not isinstance(value, list) or not value or len(value) > 8:
        reject(f"{label} must contain one to eight anchors")
    if len(set(value)) != len(value):
        reject(f"{label} contains duplicate anchors")
    return [resolve_anchor(anchor) for anchor in value]


candidate_path = os.environ.get("GIGA_CANDIDATE_PATH")
if not candidate_path:
    reject("GIGA_CANDIDATE_PATH is absent")
candidate = Path(candidate_path)
if not candidate.is_file() or candidate.stat().st_size > 65_536:
    reject("candidate must be a regular JSON file no larger than 65536 bytes")
try:
    payload = json.loads(candidate.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"candidate is not strict UTF-8 JSON: {exc}")

exact_fields(
    payload,
    {"schema", "project", "source_packet_sha256", "components", "edges", "risks"},
    "top-level",
)
if payload["schema"] != "giga.architecture-map.v1":
    reject("unsupported architecture-map schema")
if payload["project"] != PROJECT or payload["source_packet_sha256"] != PACKET_SHA256:
    reject("candidate is not bound to the admitted project and source packet")

components = payload["components"]
if not isinstance(components, list) or len(components) != len(COMPONENT_SOURCES):
    reject("components must map every admitted module exactly once")
component_ids: set[str] = set()
for index, component in enumerate(components):
    exact_fields(component, {"id", "responsibility", "sources"}, f"component[{index}]")
    component_id = non_empty_string(component["id"], f"component[{index}].id")
    non_empty_string(component["responsibility"], f"component[{index}].responsibility", 20)
    if component_id in component_ids or component_id not in COMPONENT_SOURCES:
        reject(f"unknown or duplicate component: {component_id}")
    component_ids.add(component_id)
    expected_path, tokens = COMPONENT_SOURCES[component_id]
    evidence = anchors(component["sources"], f"component[{index}].sources")
    if not any(path == expected_path and any(token in line for token in tokens) for path, line in evidence):
        reject(f"component lacks a defining source anchor: {component_id}")
if component_ids != set(COMPONENT_SOURCES):
    reject("component coverage is incomplete")

edges = payload["edges"]
if not isinstance(edges, list) or len(edges) != len(REQUIRED_EDGES):
    reject("edges must contain every and only direct internal import")
edge_ids: set[tuple[str, str]] = set()
for index, edge in enumerate(edges):
    exact_fields(edge, {"from", "to", "kind", "confidence", "evidence"}, f"edge[{index}]")
    edge_id = (edge["from"], edge["to"])
    if edge_id in edge_ids or edge_id not in REQUIRED_EDGES:
        reject(f"unknown or duplicate structural edge: {edge_id}")
    edge_ids.add(edge_id)
    if edge["kind"] != "imports" or edge["confidence"] != "certain":
        reject("direct import edges must be kind=imports and confidence=certain")
    from_path = COMPONENT_SOURCES[edge["from"]][0]
    target_token = edge["to"]
    evidence = anchors(edge["evidence"], f"edge[{index}].evidence")
    if not any(path == from_path and target_token in line for path, line in evidence):
        reject(f"edge lacks an import-line anchor: {edge_id}")
if edge_ids != REQUIRED_EDGES:
    reject("direct internal import coverage is incomplete")

risks = payload["risks"]
if not isinstance(risks, list) or not 2 <= len(risks) <= 8:
    reject("risks must contain two to eight source-anchored inferences")
seen_risks: set[str] = set()
for index, risk in enumerate(risks):
    exact_fields(risk, {"statement", "confidence", "sources"}, f"risk[{index}]")
    statement = non_empty_string(risk["statement"], f"risk[{index}].statement", 20)
    if statement in seen_risks:
        reject("risk statements must be unique")
    seen_risks.add(statement)
    if risk["confidence"] not in {"inferred", "low"}:
        reject("architectural risks must not be labelled certain")
    anchors(risk["sources"], f"risk[{index}].sources")

print("VERIFIED giga.architecture-map.v1 source-bound structural map")
