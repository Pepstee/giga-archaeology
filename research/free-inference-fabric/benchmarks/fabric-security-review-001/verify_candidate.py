from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path


PROJECT = "giga-free-inference-fabric"
PACKET_SHA256 = "be20698dff9fe65831ea3529308bd8d2253e3cc62e5796d1695e2beedab99775"
PACKET_PATH = Path(__file__).parents[1] / "fabric-structural-debt-001" / "source-packet.json"
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
    if not isinstance(value, str) or value != value.strip() or len(value) < 35:
        reject(f"{label} must be a trimmed explanation of at least 35 characters")
    if len(value) > 1200:
        reject(f"{label} exceeds bounded explanation size")
    return value


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


providers_path = "src/giga_inference_fabric/providers.py"
providers_tree = ast.parse(sources[providers_path], filename=providers_path)
local_function = top_level(providers_tree, "local_adapter", ast.FunctionDef)
adapter_class = top_level(providers_tree, "OpenCodeOpenRouterAdapter", ast.ClassDef)
complete = next(
    (
        node for node in adapter_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "complete"
    ),
    None,
)
if complete is None:
    reject("frozen adapter AST is missing complete")
local_source = ast.get_source_segment(sources[providers_path], local_function) or ""
complete_source = ast.get_source_segment(sources[providers_path], complete) or ""
if (
    "base_url=base_url" not in local_source
    or any(token in local_source for token in ("urlparse", "ip_address", "is_loopback"))
    or "--local-base-url" not in sources["src/giga_inference_fabric/cli.py"]
    or 'model.adapter != "local"' not in sources["src/giga_inference_fabric/engine.py"]
    or "WHERE adapter!='local'" not in sources["src/giga_inference_fabric/store.py"]
):
    reject("frozen local/remote classification condition is no longer present")
if (
    "plugin_path.is_file()" not in complete_source
    or "plugin_path.as_uri()" not in complete_source
    or "hook_receipt" not in complete_source
    or any(token in complete_source for token in ("sha256", "file_digest"))
):
    reject("frozen plugin-integrity condition is no longer present")

EXPECTED = {
    "SEC-LOCAL-REMOTE-CLASSIFICATION": {
        "severity": "high",
        "sources": {
            (providers_path, local_function.lineno),
            ("src/giga_inference_fabric/cli.py", 1067),
            ("src/giga_inference_fabric/engine.py", 280),
            ("src/giga_inference_fabric/store.py", 151),
        },
        "required_words": ("loopback", "local", "remote"),
    },
    "SEC-PLUGIN-INTEGRITY": {
        "severity": "medium",
        "sources": {(providers_path, 179), (providers_path, 223)},
        "required_words": ("plugin", "digest", "receipt"),
    },
}


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
exact_fields(payload, {"schema", "project", "source_packet_sha256", "findings", "scope"}, "top-level")
if (
    payload["schema"] != "giga.security-review-report.v1"
    or payload["project"] != PROJECT
    or payload["source_packet_sha256"] != PACKET_SHA256
):
    reject("candidate is not bound to the admitted review source")
findings = payload["findings"]
if not isinstance(findings, list) or len(findings) != len(EXPECTED):
    reject("findings must cover exactly the two admitted security conditions")
seen: set[str] = set()
for index, finding in enumerate(findings):
    exact_fields(
        finding,
        {
            "id", "severity", "condition_confidence", "impact_confidence", "title",
            "condition", "impact", "remediation", "sources",
        },
        f"findings[{index}]",
    )
    finding_id = finding["id"]
    if not isinstance(finding_id, str) or finding_id in seen or finding_id not in EXPECTED:
        reject(f"unknown or duplicate security finding: {finding_id}")
    seen.add(finding_id)
    expected = EXPECTED[finding_id]
    if (
        finding["severity"] != expected["severity"]
        or finding["condition_confidence"] != "certain"
        or finding["impact_confidence"] != "inferred"
    ):
        reject(f"severity/confidence classification is incorrect: {finding_id}")
    title = substantive(finding["title"], f"findings[{index}].title")
    condition = substantive(finding["condition"], f"findings[{index}].condition")
    impact = substantive(finding["impact"], f"findings[{index}].impact")
    remediation = substantive(finding["remediation"], f"findings[{index}].remediation")
    combined = " ".join((title, condition, impact, remediation)).lower()
    if not all(word in combined for word in expected["required_words"]):
        reject(f"finding does not explain its admitted security condition: {finding_id}")
    if not any(term in remediation.lower() for term in ("reject", "fail closed", "allowlist", "sha-256", "sha256")):
        reject(f"remediation is not fail-closed and bounded: {finding_id}")
    source_values = finding["sources"]
    if not isinstance(source_values, list) or {
        resolve_anchor(value) for value in source_values
    } != expected["sources"]:
        reject(f"source anchors are incorrect: {finding_id}")

scope = exact_fields(payload["scope"], {"exploit_performed", "fixes_applied", "bounded_note"}, "scope")
if scope["exploit_performed"] is not False or scope["fixes_applied"] is not False:
    reject("security review must remain passive and must not claim fixes")
bounded_note = substantive(scope["bounded_note"], "scope.bounded_note")
if "live exploit" not in bounded_note.lower() or "not" not in bounded_note.lower():
    reject("scope must not claim live exploitability")

print("VERIFIED giga.security-review-report.v1 findings=2 passive=true")
