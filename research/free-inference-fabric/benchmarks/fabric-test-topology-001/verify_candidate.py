from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path


PROJECT = "giga-free-inference-fabric"
PACKET_SHA256 = "556e90887355cf2ebccda0b5252ccc529821a96d1e0c5731d602a6133204b96f"
PACKET_PATH = Path(__file__).with_name("source-packet.json")
EXCLUSIONS = {
    "tests/test_source_packet_generation_benchmark.py",
    "tests/test_source_packets.py",
}
ANCHOR = re.compile(r"^(tests/test_[a-z0-9_]+\.py):([1-9][0-9]*)$")


def reject(reason: str) -> None:
    print(reason)
    raise SystemExit(1)


def exact_fields(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        reject(f"{label} fields must be exactly {sorted(fields)}")
    return value


def substantive(value: object, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) < 25:
        reject(f"{label} must be a trimmed explanation of at least 25 characters")
    if len(value) > 1200:
        reject(f"{label} exceeds bounded explanation size")
    return value


def canonical_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


try:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"frozen source packet is unreadable: {exc}")
if not isinstance(packet, dict) or packet.get("packet_sha256") != PACKET_SHA256:
    reject("frozen source packet identity is invalid")
without_hash = {key: value for key, value in packet.items() if key != "packet_sha256"}
if canonical_hash(without_hash) != PACKET_SHA256:
    reject("frozen source packet binding hash is invalid")
rows = packet.get("files")
if not isinstance(rows, list) or len(rows) != 8:
    reject("frozen test shard must contain exactly eight modules")

source_lines: dict[str, list[str]] = {}
expected_modules: dict[str, dict] = {}
expected_edges: dict[tuple[str, str], tuple[str, int]] = {}
for row in rows:
    if (
        not isinstance(row, dict)
        or not isinstance(row.get("path"), str)
        or not isinstance(row.get("lines"), list)
        or not all(isinstance(line, str) for line in row["lines"])
    ):
        reject("frozen source packet row is malformed")
    path = row["path"]
    text = "\n".join(row["lines"]) + ("\n" if row.get("trailing_newline") else "")
    data = text.encode("utf-8")
    if row.get("bytes") != len(data) or row.get("sha256") != hashlib.sha256(data).hexdigest():
        reject(f"frozen test module hash is invalid: {path}")
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as exc:
        reject(f"frozen test module is not valid Python: {path}: {exc}")
    tests = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    if not tests:
        reject(f"frozen module has no tests: {path}")
    module_id = Path(path).stem
    if module_id in expected_modules:
        reject(f"duplicate frozen test module id: {module_id}")
    expected_modules[module_id] = {
        "path": path,
        "test_count": len(tests),
        "anchor": (path, min(node.lineno for node in tests)),
    }
    source_lines[path] = row["lines"]
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if not node.module.startswith("giga_inference_fabric"):
            continue
        parts = node.module.split(".")
        target = parts[1] if len(parts) > 1 else "__init__"
        expected_edges[(module_id, target)] = (path, node.lineno)


def resolve_anchor(value: object) -> tuple[str, int]:
    if not isinstance(value, str):
        reject("source anchor must be a string")
    match = ANCHOR.fullmatch(value)
    if not match or match.group(1) not in source_lines:
        reject(f"source anchor is outside the frozen shard: {value}")
    path, number_text = match.groups()
    number = int(number_text)
    if number > len(source_lines[path]):
        reject(f"source anchor line is out of range: {value}")
    return path, number


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
    {"schema", "project", "source_packet_sha256", "modules", "edges", "exclusions", "risks"},
    "top-level",
)
if (
    payload["schema"] != "giga.test-topology.v1"
    or payload["project"] != PROJECT
    or payload["source_packet_sha256"] != PACKET_SHA256
):
    reject("candidate is not bound to the admitted test shard")

modules = payload["modules"]
if not isinstance(modules, list) or len(modules) != len(expected_modules):
    reject("modules must cover all eight admitted test files")
seen_modules: set[str] = set()
for index, module in enumerate(modules):
    exact_fields(module, {"id", "path", "test_count", "responsibility", "sources"}, f"modules[{index}]")
    module_id = module["id"]
    if not isinstance(module_id, str) or module_id in seen_modules or module_id not in expected_modules:
        reject(f"unknown or duplicate test module: {module_id}")
    seen_modules.add(module_id)
    expected = expected_modules[module_id]
    if module["path"] != expected["path"] or module["test_count"] != expected["test_count"]:
        reject(f"test module path/count is incorrect: {module_id}")
    substantive(module["responsibility"], f"modules[{index}].responsibility")
    anchors = module["sources"]
    if not isinstance(anchors, list) or {resolve_anchor(value) for value in anchors} != {expected["anchor"]}:
        reject(f"test module defining anchor is incorrect: {module_id}")

edges = payload["edges"]
if not isinstance(edges, list) or len(edges) != len(expected_edges):
    reject("edges must contain every and only direct production-module import")
seen_edges: set[tuple[str, str]] = set()
for index, edge in enumerate(edges):
    exact_fields(edge, {"from", "to", "kind", "evidence"}, f"edges[{index}]")
    edge_id = (edge["from"], edge["to"])
    if edge_id in seen_edges or edge_id not in expected_edges or edge["kind"] != "tests":
        reject(f"unknown, duplicate or malformed test edge: {edge_id}")
    seen_edges.add(edge_id)
    evidence = edge["evidence"]
    if not isinstance(evidence, list) or {resolve_anchor(value) for value in evidence} != {expected_edges[edge_id]}:
        reject(f"test edge anchor is incorrect: {edge_id}")

exclusions = payload["exclusions"]
if not isinstance(exclusions, list) or len(exclusions) != len(EXCLUSIONS):
    reject("exclusions must preserve the two secret-pattern boundaries")
seen_exclusions: set[str] = set()
for index, exclusion in enumerate(exclusions):
    exact_fields(exclusion, {"path", "reason"}, f"exclusions[{index}]")
    path = exclusion["path"]
    if path in seen_exclusions or path not in EXCLUSIONS or exclusion["reason"] != "secret-pattern-boundary":
        reject(f"exclusion boundary is incorrect: {path}")
    seen_exclusions.add(path)

risks = payload["risks"]
if not isinstance(risks, list) or not 2 <= len(risks) <= 6:
    reject("risks must contain two to six bounded inferences")
seen_risks: set[str] = set()
for index, risk in enumerate(risks):
    exact_fields(risk, {"statement", "confidence", "sources"}, f"risks[{index}]")
    statement = substantive(risk["statement"], f"risks[{index}].statement")
    if statement in seen_risks or risk["confidence"] not in {"inferred", "low"}:
        reject("risk statements must be unique and non-certain")
    seen_risks.add(statement)
    anchors = risk["sources"]
    if not isinstance(anchors, list) or not anchors or len(anchors) > 8:
        reject(f"risks[{index}].sources must contain one to eight anchors")
    for value in anchors:
        resolve_anchor(value)

print(
    "VERIFIED giga.test-topology.v1 "
    f"modules={len(expected_modules)} tests={sum(row['test_count'] for row in expected_modules.values())} "
    f"edges={len(expected_edges)} exclusions={len(EXCLUSIONS)}"
)
