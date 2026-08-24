from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path


PROJECT = "giga-free-inference-fabric"
PACKET_SHA256 = "be20698dff9fe65831ea3529308bd8d2253e3cc62e5796d1695e2beedab99775"
PACKET_PATH = Path(__file__).parents[1] / "fabric-structural-debt-001" / "source-packet.json"
BASELINE_PATH = Path(__file__).with_name("baseline.json")
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


def exact_fields(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        reject(f"{label} fields must be exactly {sorted(fields)}")
    return value


def substantive(value: object, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) < 30:
        reject(f"{label} must be a trimmed explanation of at least 30 characters")
    if len(value) > 1200:
        reject(f"{label} exceeds bounded explanation size")
    return value


try:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"baseline is unreadable: {exc}")
exact_fields(
    baseline,
    {"schema", "project", "recorded_at", "source_packet_sha256", "metrics"},
    "baseline",
)
if (
    baseline["schema"] != "giga.legacy-audit-baseline.v1"
    or baseline["project"] != PROJECT
    or baseline["recorded_at"] != "2026-08-24"
    or baseline["source_packet_sha256"] != PACKET_SHA256
):
    reject("baseline identity is invalid")

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
if not isinstance(rows, list) or {
    row.get("path") for row in rows if isinstance(row, dict)
} != EXPECTED_PATHS:
    reject("frozen source packet coverage is invalid")

sources: dict[str, str] = {}
source_lines: dict[str, list[str]] = {}
for row in rows:
    if (
        not isinstance(row, dict)
        or not isinstance(row.get("lines"), list)
        or not all(isinstance(line, str) for line in row["lines"])
    ):
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
current = {
    "cli_module_size": {
        "name": "physical_lines",
        "value": len(source_lines[cli_path]),
        "unit": "lines",
        "sources": ((cli_path, 1),),
    },
    "build_parser_span": {
        "name": "definition_span",
        "value": parser.end_lineno - parser.lineno + 1,
        "unit": "lines",
        "sources": ((cli_path, parser.lineno),),
    },
    "duplicated_worker_run_construction": {
        "name": "shared_construction_calls",
        "value": len(shared_calls),
        "unit": "calls",
        "sources": ((cli_path, worker.lineno), (cli_path, run.lineno)),
    },
    "experiment_store_span": {
        "name": "class_span",
        "value": store_class.end_lineno - store_class.lineno + 1,
        "unit": "lines",
        "sources": ((store_path, store_class.lineno),),
    },
    "opencode_adapter_span": {
        "name": "class_span",
        "value": adapter_class.end_lineno - adapter_class.lineno + 1,
        "unit": "lines",
        "sources": ((providers_path, adapter_class.lineno),),
    },
}

baseline_rows = baseline["metrics"]
if not isinstance(baseline_rows, list) or len(baseline_rows) != len(current):
    reject("baseline metric coverage is invalid")
baseline_by_id: dict[str, dict] = {}
for index, row in enumerate(baseline_rows):
    exact_fields(row, {"id", "name", "value", "unit", "sources"}, f"baseline.metrics[{index}]")
    metric_id = row["id"]
    if not isinstance(metric_id, str) or metric_id in baseline_by_id or metric_id not in current:
        reject(f"unknown or duplicate baseline metric: {metric_id}")
    expected = current[metric_id]
    expected_sources = [f"{path}:{line}" for path, line in expected["sources"]]
    if (
        row["name"] != expected["name"]
        or row["unit"] != expected["unit"]
        or not isinstance(row["value"], int)
        or row["sources"] != expected_sources
    ):
        reject(f"baseline metric definition is invalid: {metric_id}")
    baseline_by_id[metric_id] = row


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
    payload = json.loads(candidate.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"candidate is not strict UTF-8 JSON: {exc}")
exact_fields(
    payload,
    {
        "schema", "project", "baseline_source_packet_sha256",
        "current_source_packet_sha256", "findings", "summary",
    },
    "top-level",
)
if payload["schema"] != "giga.legacy-reaudit-report.v1" or payload["project"] != PROJECT:
    reject("candidate identity is invalid")
if (
    payload["baseline_source_packet_sha256"] != PACKET_SHA256
    or payload["current_source_packet_sha256"] != PACKET_SHA256
):
    reject("candidate is not bound to the admitted baseline and current source packet")
findings = payload["findings"]
if not isinstance(findings, list) or len(findings) != len(current):
    reject("findings must cover all five re-audited metrics")

counts = {"improved": 0, "regressed": 0, "unchanged": 0}
seen: set[str] = set()
for index, finding in enumerate(findings):
    exact_fields(
        finding,
        {
            "id", "metric", "baseline_value", "current_value", "delta", "status",
            "confidence", "interpretation", "remediation", "sources",
        },
        f"findings[{index}]",
    )
    metric_id = finding["id"]
    if not isinstance(metric_id, str) or metric_id in seen or metric_id not in current:
        reject(f"unknown or duplicate finding id: {metric_id}")
    seen.add(metric_id)
    expected = current[metric_id]
    baseline_value = baseline_by_id[metric_id]["value"]
    current_value = expected["value"]
    delta = current_value - baseline_value
    status = "unchanged" if delta == 0 else ("improved" if delta < 0 else "regressed")
    metric = exact_fields(finding["metric"], {"name", "unit"}, f"findings[{index}].metric")
    if metric != {"name": expected["name"], "unit": expected["unit"]}:
        reject(f"metric definition is incorrect: {metric_id}")
    if (
        finding["baseline_value"] != baseline_value
        or finding["current_value"] != current_value
        or finding["delta"] != delta
        or finding["status"] != status
        or finding["confidence"] != "certain"
    ):
        reject(f"re-audit classification is incorrect: {metric_id}")
    substantive(finding["interpretation"], f"findings[{index}].interpretation")
    remediation = substantive(finding["remediation"], f"findings[{index}].remediation")
    if any(word in remediation.lower() for word in ("rewrite everything", "whole-system rewrite")):
        reject("remediation must remain bounded")
    source_values = finding["sources"]
    if not isinstance(source_values, list) or {
        resolve_anchor(value) for value in source_values
    } != set(expected["sources"]):
        reject(f"definition anchors are incorrect: {metric_id}")
    counts[status] += 1

summary = exact_fields(
    payload["summary"], {"improved", "regressed", "unchanged", "verdict", "scope_note"},
    "summary",
)
if summary["improved"] != counts["improved"] or summary["regressed"] != counts["regressed"]:
    reject("summary changed-counts are incorrect")
if summary["unchanged"] != counts["unchanged"]:
    reject("summary unchanged-count is incorrect")
expected_verdict = "NO_STRUCTURAL_CHANGE" if counts == {
    "improved": 0, "regressed": 0, "unchanged": len(current),
} else "STRUCTURAL_CHANGE_DETECTED"
if summary["verdict"] != expected_verdict:
    reject("summary verdict is incorrect")
scope_note = substantive(summary["scope_note"], "summary.scope_note")
if "other" not in scope_note.lower() or "debt" not in scope_note.lower():
    reject("scope note must state that this bounded audit does not exclude other debt")

print(
    "VERIFIED giga.legacy-reaudit-report.v1 "
    f"improved={counts['improved']} regressed={counts['regressed']} unchanged={counts['unchanged']}"
)
