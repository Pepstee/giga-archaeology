from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


PACKET_SHA256 = "c1aec9a2a7787b44f9e76642ad099910fa1d5a99fc297480a348dd31e64318cd"
PROJECT = "giga-free-inference-fabric"
PACKET_PATH = Path(__file__).with_name("source-packet.json")
ALLOWED_PATHS = {
    ".gitignore",
    "README.md",
    "pyproject.toml",
    "config/workloads.json",
    "config/studies.json",
    "config/studies.json.sha256",
    "config/studies-v2.json",
    "config/studies-v2.json.sha256",
    "config/studies-comparative-v2.json",
    "config/studies-comparative-v2.json.sha256",
    "opencode/giga-output-budget.js",
}
FACTS = {
    "package_identity": ("pyproject.toml", 'name = "giga-inference-fabric"'),
    "python_floor": ("pyproject.toml", 'requires-python = ">=3.11"'),
    "runtime_dependencies": ("pyproject.toml", "dependencies = []"),
    "console_entrypoint": ("pyproject.toml", 'giga-inference = "giga_inference_fabric.cli:main"'),
    "state_ignored": (".gitignore", "state/"),
    "single_invocation_guard": ("opencode/giga-output-budget.js", "invocationCount !== 1"),
    "exact_model_guard": ("opencode/giga-output-budget.js", "input.model.id !== expectedModel"),
}
FINDINGS = {
    "package_version_drift": {
        "confidence": "certain",
        "evidence": (("README.md", "v0.4"), ("pyproject.toml", 'version = "0.3.0"')),
    },
    "ruff_cache_not_ignored": {
        "confidence": "certain",
        "evidence": ((".gitignore", ".pytest_cache/"),),
    },
    "build_dependency_not_reproducibly_pinned": {
        "confidence": "inferred",
        "evidence": (("pyproject.toml", 'requires = ["setuptools>=68"]'),),
    },
    "development_test_dependency_undeclared": {
        "confidence": "inferred",
        "evidence": (("README.md", "python3 -m pytest"), ("pyproject.toml", "dependencies = []")),
    },
}
INTEGRITY_CHECKS = {
    "studies_v1_digest": (
        ("config/studies.json", "config/studies.json.sha256"),
        (("config/studies.json", '"schema"'), ("config/studies.json.sha256", "23abca74")),
    ),
    "studies_v2_digest": (
        ("config/studies-v2.json", "config/studies-v2.json.sha256"),
        (("config/studies-v2.json", '"schema"'), ("config/studies-v2.json.sha256", "f6e66e2b")),
    ),
    "comparative_v2_digest": (
        ("config/studies-comparative-v2.json", "config/studies-comparative-v2.json.sha256"),
        (("config/studies-comparative-v2.json", '"schema"'), ("config/studies-comparative-v2.json.sha256", "42642ae1")),
    ),
    "workload_catalogue_schema": (
        None,
        (("config/workloads.json", '"schema": "giga.inference-workload-catalogue.v1"'),),
    ),
    "output_budget_admission": (
        None,
        (("opencode/giga-output-budget.js", 'throw new Error("unadmitted model invocation denied")'),),
    ),
}
ANCHOR = re.compile(r"^(.+):([1-9][0-9]*)$")


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
payload_without_hash = {key: value for key, value in packet.items() if key != "packet_sha256"}
if canonical_hash(payload_without_hash) != PACKET_SHA256:
    reject("frozen source packet binding hash is invalid")
rows = packet.get("files")
if not isinstance(rows, list) or {row.get("path") for row in rows if isinstance(row, dict)} != ALLOWED_PATHS:
    reject("frozen source packet file coverage is invalid")

source_lines: dict[str, list[str]] = {}
for row in rows:
    if not isinstance(row, dict) or not isinstance(row.get("lines"), list):
        reject("frozen source packet row is malformed")
    text = "\n".join(row["lines"]) + ("\n" if row.get("trailing_newline") else "")
    data = text.encode("utf-8")
    if row.get("bytes") != len(data) or row.get("sha256") != hashlib.sha256(data).hexdigest():
        reject(f"frozen source row hash is invalid: {row.get('path')}")
    source_lines[row["path"]] = row["lines"]
if packet.get("total_source_bytes") != sum(
    len(("\n".join(row["lines"]) + ("\n" if row.get("trailing_newline") else "")).encode("utf-8"))
    for row in rows
):
    reject("frozen source packet total is invalid")


def exact_fields(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        reject(f"{label} fields must be exactly {sorted(fields)}")
    return value


def substantive(value: object, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) < 20:
        reject(f"{label} must be a trimmed concrete string of at least 20 characters")
    return value


def resolve_anchor(value: object) -> tuple[str, str]:
    if not isinstance(value, str):
        reject("source anchor must be a string")
    match = ANCHOR.fullmatch(value)
    if not match or match.group(1) not in source_lines:
        reject(f"source anchor is outside the frozen packet: {value}")
    relative, number_text = match.groups()
    number = int(number_text)
    if number > len(source_lines[relative]):
        reject(f"source anchor line is out of range: {value}")
    return relative, source_lines[relative][number - 1]


def verify_evidence(value: object, expected: tuple[tuple[str, str], ...], label: str) -> None:
    if not isinstance(value, list) or not value or len(value) > 8 or len(set(value)) != len(value):
        reject(f"{label} must contain one to eight unique anchors")
    resolved = [resolve_anchor(anchor) for anchor in value]
    for expected_path, token in expected:
        if not any(path == expected_path and token in line for path, line in resolved):
            reject(f"{label} lacks required evidence from {expected_path}")


for content, digest_file in (
    ("config/studies.json", "config/studies.json.sha256"),
    ("config/studies-v2.json", "config/studies-v2.json.sha256"),
    ("config/studies-comparative-v2.json", "config/studies-comparative-v2.json.sha256"),
):
    content_bytes = ("\n".join(source_lines[content]) + "\n").encode("utf-8")
    declared = "\n".join(source_lines[digest_file]).strip()
    if declared != hashlib.sha256(content_bytes).hexdigest():
        reject(f"study catalogue digest mismatch: {content}")
if ".ruff_cache/" in source_lines[".gitignore"]:
    reject("frozen packet no longer contains the admitted ruff-cache finding")

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

exact_fields(
    candidate_payload,
    {"schema", "project", "source_packet_sha256", "facts", "findings", "integrity_checks"},
    "top-level",
)
if candidate_payload["schema"] != "giga.config-audit.v1":
    reject("unsupported config-audit schema")
if candidate_payload["project"] != PROJECT or candidate_payload["source_packet_sha256"] != PACKET_SHA256:
    reject("candidate is not bound to the admitted project and source packet")

facts = candidate_payload["facts"]
if not isinstance(facts, list) or len(facts) != len(FACTS):
    reject("facts must cover every required package/runtime fact")
seen: set[str] = set()
for index, fact in enumerate(facts):
    exact_fields(fact, {"id", "value", "sources"}, f"facts[{index}]")
    fact_id = fact["id"]
    if not isinstance(fact_id, str) or fact_id in seen or fact_id not in FACTS:
        reject(f"unknown or duplicate fact id: {fact_id}")
    seen.add(fact_id)
    substantive(fact["value"], f"facts[{index}].value")
    verify_evidence(fact["sources"], (FACTS[fact_id],), f"facts[{index}].sources")

findings = candidate_payload["findings"]
if not isinstance(findings, list) or len(findings) != len(FINDINGS):
    reject("findings must cover every admitted configuration defect")
seen = set()
for index, finding in enumerate(findings):
    exact_fields(
        finding, {"id", "impact", "remediation", "confidence", "sources"},
        f"findings[{index}]",
    )
    finding_id = finding["id"]
    if not isinstance(finding_id, str) or finding_id in seen or finding_id not in FINDINGS:
        reject(f"unknown or duplicate finding id: {finding_id}")
    seen.add(finding_id)
    substantive(finding["impact"], f"findings[{index}].impact")
    substantive(finding["remediation"], f"findings[{index}].remediation")
    expected = FINDINGS[finding_id]
    if finding["confidence"] != expected["confidence"]:
        reject(f"finding confidence is invalid: {finding_id}")
    verify_evidence(finding["sources"], expected["evidence"], f"findings[{index}].sources")

checks = candidate_payload["integrity_checks"]
if not isinstance(checks, list) or len(checks) != len(INTEGRITY_CHECKS):
    reject("integrity_checks must cover every required deterministic check")
seen = set()
for index, check in enumerate(checks):
    exact_fields(check, {"id", "status", "summary", "sources"}, f"integrity_checks[{index}]")
    check_id = check["id"]
    if not isinstance(check_id, str) or check_id in seen or check_id not in INTEGRITY_CHECKS:
        reject(f"unknown or duplicate integrity check id: {check_id}")
    seen.add(check_id)
    if check["status"] != "pass":
        reject(f"deterministic integrity check must report pass: {check_id}")
    substantive(check["summary"], f"integrity_checks[{index}].summary")
    _digest_pair, expected_evidence = INTEGRITY_CHECKS[check_id]
    verify_evidence(check["sources"], expected_evidence, f"integrity_checks[{index}].sources")

print("VERIFIED giga.config-audit.v1 frozen dependency/config audit")
