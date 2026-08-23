from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path


PACKET_SHA256 = "be20698dff9fe65831ea3529308bd8d2253e3cc62e5796d1695e2beedab99775"
PROJECT = "giga-free-inference-fabric"
PACKET_PATH = Path(__file__).with_name("source-packet.json")
EXPECTED_PATHS = {
    "src/giga_inference_fabric/cli.py",
    "src/giga_inference_fabric/engine.py",
    "src/giga_inference_fabric/providers.py",
    "src/giga_inference_fabric/store.py",
}


def reject(reason: str) -> None:
    print(reason)
    raise SystemExit(1)


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
if not isinstance(rows, list) or {row.get("path") for row in rows if isinstance(row, dict)} != EXPECTED_PATHS:
    reject("frozen source packet module coverage is invalid")

sources: dict[str, str] = {}
source_lines: dict[str, list[str]] = {}
for row in rows:
    if not isinstance(row.get("lines"), list) or not all(isinstance(line, str) for line in row["lines"]):
        reject("frozen source packet row is malformed")
    text = "\n".join(row["lines"]) + ("\n" if row.get("trailing_newline") else "")
    data = text.encode("utf-8")
    if row.get("bytes") != len(data) or row.get("sha256") != hashlib.sha256(data).hexdigest():
        reject(f"frozen module hash is invalid: {row.get('path')}")
    sources[row["path"]] = text
    source_lines[row["path"]] = row["lines"]


def top_level(tree: ast.Module, name: str, kind: type[ast.AST]) -> ast.AST:
    for node in tree.body:
        if isinstance(node, kind) and getattr(node, "name", None) == name:
            return node
    reject(f"frozen AST is missing {name}")


def call_names(node: ast.AST) -> set[str]:
    result: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name):
            result.add(child.func.id)
        elif isinstance(child.func, ast.Attribute):
            result.add(child.func.attr)
    return result


trees = {path: ast.parse(text, filename=path) for path, text in sources.items()}
cli_path = "src/giga_inference_fabric/cli.py"
providers_path = "src/giga_inference_fabric/providers.py"
store_path = "src/giga_inference_fabric/store.py"
cli_tree = trees[cli_path]
worker = top_level(cli_tree, "worker_once", ast.FunctionDef)
run = top_level(cli_tree, "run", ast.FunctionDef)
parser = top_level(cli_tree, "build_parser", ast.FunctionDef)
store_class = top_level(trees[store_path], "ExperimentStore", ast.ClassDef)
adapter_class = top_level(trees[providers_path], "OpenCodeOpenRouterAdapter", ast.ClassDef)
shared_focus = {
    "discover_openrouter_models", "_select_explicit_free_models", "OpenCodeOpenRouterAdapter",
    "local_adapter", "ModelSpec", "ModelPolicy", "ExperimentRequest", "ExperimentEngine",
    "evaluator_from_contract",
}
shared_calls = call_names(worker) & call_names(run) & shared_focus
EXPECTED = {
    "cli_module_size": {
        "metric": ("physical_lines", len(source_lines[cli_path]), "lines"),
        "anchors": ((cli_path, 1),),
    },
    "build_parser_span": {
        "metric": ("definition_span", parser.end_lineno - parser.lineno + 1, "lines"),
        "anchors": ((cli_path, parser.lineno),),
    },
    "duplicated_worker_run_construction": {
        "metric": ("shared_construction_calls", len(shared_calls), "calls"),
        "anchors": ((cli_path, worker.lineno), (cli_path, run.lineno)),
    },
    "experiment_store_span": {
        "metric": ("class_span", store_class.end_lineno - store_class.lineno + 1, "lines"),
        "anchors": ((store_path, store_class.lineno),),
    },
    "opencode_adapter_span": {
        "metric": ("class_span", adapter_class.end_lineno - adapter_class.lineno + 1, "lines"),
        "anchors": ((providers_path, adapter_class.lineno),),
    },
}


def exact_fields(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        reject(f"{label} fields must be exactly {sorted(fields)}")
    return value


def substantive(value: object, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) < 30:
        reject(f"{label} must be a trimmed bounded explanation of at least 30 characters")
    if len(value) > 1200:
        reject(f"{label} exceeds bounded explanation size")
    return value


def resolve_anchor(value: object) -> tuple[str, int]:
    if not isinstance(value, str) or ":" not in value:
        reject(f"source anchor is malformed: {value}")
    path, number_text = value.rsplit(":", 1)
    if path not in source_lines or not number_text.isdigit():
        reject(f"source anchor is outside the frozen packet: {value}")
    number = int(number_text)
    if number < 1 or number > len(source_lines[path]):
        reject(f"source anchor line is invalid: {value}")
    return path, number


candidate_path = os.environ.get("GIGA_CANDIDATE_PATH")
if not candidate_path:
    reject("GIGA_CANDIDATE_PATH is absent")
candidate = Path(candidate_path)
if not candidate.is_file() or candidate.stat().st_size > 65_536:
    reject("candidate must be a regular JSON file no larger than 65536 bytes")
try:
    candidate_payload = json.loads(candidate.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"candidate is not strict UTF-8 JSON: {exc}")
exact_fields(candidate_payload, {"schema", "project", "source_packet_sha256", "findings"}, "top-level")
if candidate_payload["schema"] != "giga.structural-debt-report.v1":
    reject("unsupported structural-debt schema")
if candidate_payload["project"] != PROJECT or candidate_payload["source_packet_sha256"] != PACKET_SHA256:
    reject("candidate is not bound to the frozen project and source packet")
findings = candidate_payload["findings"]
if not isinstance(findings, list) or len(findings) != len(EXPECTED):
    reject("findings must cover all five AST-derived debt signals")

seen: set[str] = set()
for index, finding in enumerate(findings):
    exact_fields(
        finding, {"id", "metric", "impact", "remediation", "confidence", "sources"},
        f"findings[{index}]",
    )
    finding_id = finding["id"]
    if not isinstance(finding_id, str) or finding_id in seen or finding_id not in EXPECTED:
        reject(f"unknown or duplicate finding id: {finding_id}")
    seen.add(finding_id)
    substantive(finding["impact"], f"findings[{index}].impact")
    remediation = substantive(finding["remediation"], f"findings[{index}].remediation")
    if any(word in remediation.lower() for word in ("rewrite everything", "whole-system rewrite")):
        reject("remediation must be a bounded refactor, not a whole-system rewrite")
    if finding["confidence"] != "inferred":
        reject("structural debt conclusions must have confidence=inferred")
    metric = exact_fields(finding["metric"], {"name", "value", "unit"}, f"findings[{index}].metric")
    metric_name, metric_value, metric_unit = EXPECTED[finding_id]["metric"]
    if metric != {"name": metric_name, "value": metric_value, "unit": metric_unit}:
        reject(f"AST-derived metric is incorrect: {finding_id}")
    source_values = finding["sources"]
    if not isinstance(source_values, list) or len(source_values) != len(EXPECTED[finding_id]["anchors"]):
        reject(f"source coverage is incorrect: {finding_id}")
    if {resolve_anchor(value) for value in source_values} != set(EXPECTED[finding_id]["anchors"]):
        reject(f"definition anchors are incorrect: {finding_id}")

print("VERIFIED giga.structural-debt-report.v1 ast_metrics=5/5")
