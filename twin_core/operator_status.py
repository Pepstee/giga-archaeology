"""Deterministic, read-only compilation of the GIGA operator status contract."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .adapter_evidence import (AdapterEvidenceError, verify_registry_files,
                               current_adapter_file_records, validate_registry)


SCHEMA_VERSION = "giga.operator-status.v1"
EVIDENCE_SCHEMA = "giga.operator-status-evidence.v1"
SECTION_NAMES = (
    "context",
    "toolCalls",
    "activeAgents",
    "todos",
    "checks",
    "cost",
    "risk",
    "queueState",
    "sessionControls",
    "sync",
)
RUNTIME_SECTIONS = ("toolCalls", "activeAgents", "cost", "queueState")
STATES = ("observed", "healthy", "degraded", "blocked", "unknown", "unavailable", "stale")
MAX_JSON_BYTES = 5 * 1024 * 1024

ADMITTED_ADAPTER_ID = "operator-status-local"
ADMISSION_ONRAMP = "python3 scripts/operator_status.py --no-write"
ADMISSION_REGISTRY_PATH = "outputs/adapter-evidence/registry.json"
ADMISSION_REGISTRY_SCHEMA = "giga.adapter-registry.v1"
ADMISSION_KEYS = frozenset(
    {
        "adapter_id",
        "declared_state",
        "effective_state",
        "verification_state",
        "authority",
        "onramp",
        "registry_schema_version",
        "registry_authority",
        "authority_granted",
        "command_execution",
        "registry_path",
        "registry_sha256",
        "adapter_record_sha256",
        "commands_executed",
        "supported_assets",
        "source_docs",
        "evidence",
    }
)


class OperatorStatusError(ValueError):
    """Raised when status evidence violates the contract."""


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise OperatorStatusError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OperatorStatusError("timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _contained(root: Path, candidate: str | Path) -> Path:
    candidate = Path(candidate)
    if candidate.is_absolute():
        raise OperatorStatusError(f"absolute paths are forbidden: {candidate}")
    root = root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise OperatorStatusError(f"path escapes repository root: {candidate}") from exc
    return resolved


def _load_json(root: Path, relative: str | Path, *, required: bool = True) -> dict[str, Any] | None:
    path = _contained(root, relative)
    if not path.exists():
        if required:
            raise OperatorStatusError(f"required evidence is missing: {relative}")
        return None
    if not path.is_file():
        raise OperatorStatusError(f"evidence is not a regular file: {relative}")
    if path.stat().st_size > MAX_JSON_BYTES:
        raise OperatorStatusError(f"evidence exceeds {MAX_JSON_BYTES} bytes: {relative}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OperatorStatusError(f"malformed evidence: {relative}") from exc
    if not isinstance(value, dict):
        raise OperatorStatusError(f"evidence must be a JSON object: {relative}")
    return value


def _envelope(value: Any, state: str, source: str, observed_at: str) -> dict[str, Any]:
    return {"value": value, "state": state, "source": source, "observed_at": observed_at}


def _master_todos(root: Path) -> dict[str, Any]:
    relative = "00_MASTER.md"
    path = _contained(root, relative)
    if not path.is_file():
        raise OperatorStatusError(f"required evidence is missing: {relative}")
    rows: list[dict[str, str]] = []
    pattern = re.compile(r"^\|\s*(\d{2})\s*\|\s*([^|]+?)\s*\|[^|]*\|\s*([^|]+?)\s*\|")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            rows.append({"id": match.group(1), "session": match.group(2).strip(), "status": match.group(3).strip()})
    if not rows:
        raise OperatorStatusError("00_MASTER.md contains no parseable workstream rows")
    counts = Counter(row["status"].split("(", 1)[0].strip() for row in rows)
    return {"workstreams": rows, "status_counts": dict(sorted(counts.items()))}


def _validate_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    jobs = registry.get("jobs")
    if not isinstance(jobs, list):
        raise OperatorStatusError("SkillTree registry has no jobs array")
    counts = Counter()
    by_name: dict[str, Mapping[str, Any]] = {}
    for record in jobs:
        if not isinstance(record, dict) or not isinstance(record.get("job"), str) or not isinstance(record.get("status"), str):
            raise OperatorStatusError("SkillTree registry contains an invalid job record")
        name = record["job"]
        if name in by_name:
            raise OperatorStatusError(f"SkillTree registry contains duplicate job: {name}")
        by_name[name] = record
        counts[record["status"]] += 1
    monitoring = by_name.get("Monitoring & Alerting")
    if not isinstance(monitoring, dict) or not isinstance(monitoring.get("status"), str):
        raise OperatorStatusError("SkillTree registry lacks Monitoring & Alerting status")
    if registry.get("jobs_total") != len(jobs) or registry.get("counts") != dict(counts):
        raise OperatorStatusError("SkillTree registry summary disagrees with its jobs")
    return {"jobs_total": len(jobs), "status_counts": dict(sorted(counts.items())), "monitoring": monitoring["status"]}


def _validate_ecc(upstream: Mapping[str, Any], ledger: Mapping[str, Any]) -> dict[str, Any]:
    if upstream.get("schema") != "giga.ecc-upstream.v1" or not isinstance(upstream.get("commit"), str):
        raise OperatorStatusError("invalid ECC upstream manifest")
    if ledger.get("schema") != "giga.ecc-import-ledger.v1" or not isinstance(ledger.get("entries"), list):
        raise OperatorStatusError("invalid ECC import ledger")
    decisions = Counter()
    for entry in ledger["entries"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("decision"), str):
            raise OperatorStatusError("invalid ECC import ledger entry")
        decisions[entry["decision"]] += 1
    return {
        "commit": upstream["commit"],
        "deployed": ledger.get("deployed") is True,
        "entry_decisions": dict(sorted(decisions.items())),
    }


def _validate_adapters(
    root: Path,
    registry: Mapping[str, Any],
    observed_at: str,
    stale_after_seconds: int,
) -> dict[str, Any]:
    try:
        verify_registry_files(root, registry)
    except AdapterEvidenceError as exc:
        raise OperatorStatusError(f"invalid adapter registry: {exc}") from exc
    registered_at = registry["observed_at"]
    age = (_timestamp(observed_at) - _timestamp(registered_at)).total_seconds()
    if age < 0:
        raise OperatorStatusError("adapter registry is dated after the status observation")
    registry_state = "stale" if age > stale_after_seconds else "verified"
    return {
        "registry_state": registry_state,
        "registered_at": registered_at,
        "total": registry["summary"]["total"],
        "effective_states": registry["summary"]["effective_states"],
        "verification_states": registry["summary"]["verification_states"],
        "authorities": registry["summary"]["authorities"],
        "command_execution": registry["command_execution"],
        "authority_granted": registry["authority_granted"],
    }


def _runtime_evidence(root: Path, relative: str | Path | None, observed_at: str, stale_after_seconds: int) -> dict[str, dict[str, Any]]:
    result = {
        name: _envelope(None, "unknown", "no runtime evidence supplied", observed_at)
        for name in RUNTIME_SECTIONS
    }
    if relative is None:
        return result
    packet = _load_json(root, relative)
    assert packet is not None
    if packet.get("schema") != EVIDENCE_SCHEMA or not isinstance(packet.get("signals"), dict):
        raise OperatorStatusError("invalid runtime evidence packet")
    packet_time_text = packet.get("observed_at")
    if not isinstance(packet_time_text, str):
        raise OperatorStatusError("runtime evidence lacks observed_at")
    packet_time = _timestamp(packet_time_text)
    age = (_timestamp(observed_at) - packet_time).total_seconds()
    if age < 0:
        raise OperatorStatusError("runtime evidence is dated after the status observation")
    signals = packet["signals"]
    unknown = sorted(set(signals) - set(RUNTIME_SECTIONS))
    if unknown:
        raise OperatorStatusError(f"unsupported runtime signals: {', '.join(unknown)}")
    source = Path(relative).as_posix()
    for name, signal in signals.items():
        if not isinstance(signal, dict) or set(signal) != {"value", "state"}:
            raise OperatorStatusError(f"invalid runtime signal: {name}")
        state = signal["state"]
        if state not in STATES:
            raise OperatorStatusError(f"invalid runtime signal state: {name}")
        if signal["value"] is None and state in {"healthy", "observed"}:
            raise OperatorStatusError(f"empty runtime signal cannot be {state}: {name}")
        if age > stale_after_seconds:
            state = "stale"
        result[name] = _envelope(signal["value"], state, source, packet_time_text)
    return result


def _summary(sections: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(section["state"] for section in sections.values())
    ordered = {state: counts.get(state, 0) for state in STATES}
    priority = ("blocked", "degraded", "stale", "unknown", "unavailable", "healthy", "observed")
    overall = next(state for state in priority if counts.get(state, 0))
    return {"overall_state": overall, "state_counts": ordered}


class AdapterAdmissionError(OperatorStatusError):
    """Raised when the official no-write onramp cannot admit its adapter."""

    def __init__(self, reason: str, message: str):
        super().__init__(f"[{reason}] {message}")
        self.reason = reason


def admit_no_write_adapter(root: Path) -> dict[str, Any]:
    """Deterministically admit the official read-only no-write adapter or fail closed.

    The compiled registry is validated, its identity and no-authority/no-execution
    fields are bound, exactly one ``operator-status-local`` record must carry the
    exact official onramp string with read-only authority and a verified native
    effective state, and every bound file record is re-hashed against current
    bytes. Manifest commands are data here and are never executed.
    """
    root = root.resolve()
    try:
        registry_file = _contained(root, ADMISSION_REGISTRY_PATH)
    except OperatorStatusError as exc:
        raise AdapterAdmissionError("adapter-registry-path-unsafe", str(exc)) from exc
    declared_path = root
    registry_path_has_symlink = False
    for part in Path(ADMISSION_REGISTRY_PATH).parts:
        declared_path /= part
        if declared_path.is_symlink():
            registry_path_has_symlink = True
            break
    if registry_path_has_symlink or not registry_file.is_file():
        raise AdapterAdmissionError(
            "adapter-registry-path-uncertain",
            f"adapter registry is not a contained regular file: {ADMISSION_REGISTRY_PATH}",
        )
    try:
        raw = registry_file.read_bytes()
    except OSError as exc:
        raise AdapterAdmissionError(
            "adapter-registry-path-uncertain",
            f"adapter registry changed or became unreadable while admitting: {exc}",
        ) from exc
    if len(raw) > MAX_JSON_BYTES:
        raise AdapterAdmissionError(
            "adapter-registry-unreadable",
            f"adapter registry exceeds {MAX_JSON_BYTES} bytes",
        )
    try:
        registry = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AdapterAdmissionError(
            "adapter-registry-unreadable", "malformed adapter registry"
        ) from exc
    if not isinstance(registry, dict):
        raise AdapterAdmissionError(
            "adapter-registry-unreadable", "adapter registry must be an object"
        )

    records = registry.get("adapters")
    if not isinstance(records, list):
        raise AdapterAdmissionError(
            "adapter-registry-invalid", "adapter registry has no adapters array"
        )
    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("id"), str)
        and record["id"] == ADMITTED_ADAPTER_ID
    ]
    if len(matches) > 1:
        raise AdapterAdmissionError(
            "adapter-duplicate",
            f"multiple adapter records claim id {ADMITTED_ADAPTER_ID}",
        )
    identity = (
        registry.get("schema_version") == ADMISSION_REGISTRY_SCHEMA
        and registry.get("authority") == "read-only-evidence"
        and registry.get("authority_granted") is False
        and registry.get("command_execution") is False
    )
    if not identity:
        raise AdapterAdmissionError(
            "adapter-registry-identity",
            "registry identity, no-authority or no-command-execution fields drifted",
        )
    try:
        validate_registry(registry)
    except AdapterEvidenceError as exc:
        raise AdapterAdmissionError("adapter-registry-invalid", str(exc)) from exc
    if not matches:
        registered = sorted(
            record["id"]
            for record in records
            if isinstance(record, dict) and isinstance(record.get("id"), str)
        )
        raise AdapterAdmissionError(
            "adapter-missing",
            f"no adapter {ADMITTED_ADAPTER_ID}; registered ids: {registered}",
        )
    record = matches[0]
    if record["onramp"] != ADMISSION_ONRAMP:
        raise AdapterAdmissionError(
            "adapter-onramp-mismatch",
            f"adapter onramp does not match the official no-write path: {record['onramp']!r}",
        )
    if record["authority"] != "read-only":
        raise AdapterAdmissionError(
            "adapter-authority-mismatch",
            f"adapter authority is {record['authority']!r}, not read-only",
        )
    if record["verification_state"] != "verified":
        raise AdapterAdmissionError(
            "adapter-stale", "adapter verification state is not verified"
        )
    if record["effective_state"] == "reference-only":
        raise AdapterAdmissionError(
            "adapter-reference-only", "adapter degraded to reference-only"
        )
    if record["declared_state"] != "native" or record["effective_state"] != "native":
        raise AdapterAdmissionError(
            "adapter-state-mismatch",
            "the official no-write adapter must be declared and effective native",
        )
    try:
        verify_registry_files(root, registry)
        fresh_records = current_adapter_file_records(root, record)
    except AdapterEvidenceError as exc:
        raise AdapterAdmissionError("adapter-evidence-drift", str(exc)) from exc
    for field in ("supported_assets", "source_docs", "evidence"):
        if fresh_records[field] != record[field]:
            raise AdapterAdmissionError(
                "adapter-evidence-race",
                f"adapter {field} changed while it was being admitted",
            )
    try:
        reread = registry_file.read_bytes()
    except OSError as exc:
        raise AdapterAdmissionError(
            "adapter-registry-race",
            f"adapter registry changed or became unreadable while admitting: {exc}",
        ) from exc
    if reread != raw:
        raise AdapterAdmissionError(
            "adapter-registry-race",
            "adapter registry changed while it was being admitted",
        )

    canonical_record = json.dumps(
        record, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return {
        "adapter_id": record["id"],
        "declared_state": record["declared_state"],
        "effective_state": record["effective_state"],
        "verification_state": record["verification_state"],
        "authority": record["authority"],
        "onramp": record["onramp"],
        "registry_schema_version": registry["schema_version"],
        "registry_authority": registry["authority"],
        "authority_granted": registry["authority_granted"],
        "command_execution": registry["command_execution"],
        "registry_path": ADMISSION_REGISTRY_PATH,
        "registry_sha256": hashlib.sha256(raw).hexdigest(),
        "adapter_record_sha256": hashlib.sha256(
            canonical_record.encode("utf-8")
        ).hexdigest(),
        "commands_executed": False,
        **fresh_records,
    }


def _validate_admission(admission: Mapping[str, Any]) -> None:
    """Refuse forged or misused admission receipts before they enter the snapshot."""
    if not isinstance(admission, Mapping) or set(admission) != ADMISSION_KEYS:
        raise AdapterAdmissionError(
            "adapter-admission-forgery",
            "admission receipt fields are missing or unexpected",
        )
    if (
        admission["adapter_id"] != ADMITTED_ADAPTER_ID
        or admission["onramp"] != ADMISSION_ONRAMP
        or admission["commands_executed"] is not False
        or admission["authority"] != "read-only"
        or admission["authority_granted"] is not False
        or admission["command_execution"] is not False
    ):
        raise AdapterAdmissionError(
            "adapter-admission-forgery",
            "admission receipt claims a different adapter, authority or execution",
        )


def compile_status(
    root: Path,
    observed_at: str,
    *,
    runtime_evidence: str | Path | None = None,
    stale_after_seconds: int = 86_400,
    registry_path: str | Path = "skilltree/implementation-registry.json",
    upstream_path: str | Path = "ecc-integration/UPSTREAM.json",
    ledger_path: str | Path = "ecc-integration/IMPORT_LEDGER.json",
    adapter_registry_path: str | Path = "outputs/adapter-evidence/registry.json",
    admission: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile a status snapshot without contacting or mutating source systems."""
    _timestamp(observed_at)
    if (
        isinstance(stale_after_seconds, bool)
        or not isinstance(stale_after_seconds, int)
        or stale_after_seconds < 0
    ):
        raise OperatorStatusError("stale_after_seconds must be a non-negative integer")
    if admission is not None:
        _validate_admission(admission)
    registry = _load_json(root, registry_path)
    upstream = _load_json(root, upstream_path)
    ledger = _load_json(root, ledger_path)
    adapter_registry = _load_json(root, adapter_registry_path)
    assert (
        registry is not None
        and upstream is not None
        and ledger is not None
        and adapter_registry is not None
    )
    skilltree = _validate_registry(registry)
    ecc = _validate_ecc(upstream, ledger)
    adapters = _validate_adapters(
        root, adapter_registry, observed_at, stale_after_seconds
    )
    if admission is not None:
        expected_admission = admit_no_write_adapter(root)
        if dict(admission) != expected_admission:
            raise AdapterAdmissionError(
                "adapter-admission-forgery",
                "admission receipt does not match current deterministic evidence",
            )
    todos = _master_todos(root)
    runtime = _runtime_evidence(
        root, runtime_evidence, observed_at, stale_after_seconds
    )
    unknown_runtime = [
        name
        for name in RUNTIME_SECTIONS
        if runtime[name]["state"] in {"unknown", "unavailable", "stale"}
    ]

    sections: dict[str, dict[str, Any]] = {
        "context": _envelope(
            {"repository": "giga-user", "root": ".", "contract": SCHEMA_VERSION},
            "observed",
            "compiler:giga.operator-status",
            observed_at,
        ),
        **runtime,
        "todos": _envelope(todos, "observed", "00_MASTER.md", observed_at),
        "checks": _envelope(
            {
                "skilltree": skilltree,
                "ecc": ecc,
                "adapters": adapters,
                **(
                    {"adapter_admission": dict(admission)}
                    if admission is not None
                    else {}
                ),
            },
            "observed",
            "skilltree/implementation-registry.json;ecc-integration/UPSTREAM.json;ecc-integration/IMPORT_LEDGER.json;outputs/adapter-evidence/registry.json",
            observed_at,
        ),
        "risk": _envelope(
            {
                "unknown_or_stale_runtime_signals": unknown_runtime,
                "monitoring_status": skilltree["monitoring"],
                "ecc_deployed": ecc["deployed"],
                "adapter_registry_state": adapters["registry_state"],
            },
            "degraded"
            if unknown_runtime
            or skilltree["monitoring"] != "implemented"
            or not ecc["deployed"]
            or adapters["registry_state"] != "verified"
            else "healthy",
            "derived:checks+runtime",
            observed_at,
        ),
        "sessionControls": _envelope(
            {
                "supported": ["status"],
                "unsupported": [
                    "create",
                    "resume",
                    "stop",
                    "diff",
                    "pullRequest",
                    "mergeQueue",
                    "conflictQueue",
                ],
                "mutation_performed": False,
            },
            "observed",
            "contract:giga.operator-status.v1",
            observed_at,
        ),
        "sync": _envelope(
            {
                "ecc_import_deployed": ecc["deployed"],
                "entry_decisions": ecc["entry_decisions"],
            },
            "observed",
            "ecc-integration/IMPORT_LEDGER.json",
            observed_at,
        ),
    }
    ordered = {name: sections[name] for name in SECTION_NAMES}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "authority": "read-only-status",
        "observed_at": observed_at,
        "sections": ordered,
        "summary": _summary(ordered),
    }
    validate_status(payload)
    return payload


def validate_status(payload: Mapping[str, Any]) -> None:
    """Strict stdlib validation mirroring the published JSON Schema."""
    if set(payload) != {"schema_version", "authority", "observed_at", "sections", "summary"}:
        raise OperatorStatusError("invalid top-level status fields")
    if payload["schema_version"] != SCHEMA_VERSION or payload["authority"] != "read-only-status":
        raise OperatorStatusError("invalid status identity or authority")
    observed_at = payload["observed_at"]
    if not isinstance(observed_at, str):
        raise OperatorStatusError("observed_at must be a string")
    _timestamp(observed_at)
    sections = payload["sections"]
    if not isinstance(sections, dict) or tuple(sections) != SECTION_NAMES:
        raise OperatorStatusError("status sections are missing, extra, or out of order")
    for name, section in sections.items():
        if not isinstance(section, dict) or set(section) != {"value", "state", "source", "observed_at"}:
            raise OperatorStatusError(f"invalid envelope: {name}")
        if section["state"] not in STATES or not isinstance(section["source"], str) or not section["source"]:
            raise OperatorStatusError(f"invalid state or source: {name}")
        if not isinstance(section["observed_at"], str):
            raise OperatorStatusError(f"invalid observed_at: {name}")
        _timestamp(section["observed_at"])
        if section["value"] is None and section["state"] in {"healthy", "observed"}:
            raise OperatorStatusError(f"empty value cannot be green: {name}")
    if sections["sessionControls"]["value"].get("mutation_performed") is not False:
        raise OperatorStatusError("sessionControls must not perform mutations")
    if payload["summary"] != _summary(sections):
        raise OperatorStatusError("status summary disagrees with section states")


def render_summary(payload: Mapping[str, Any]) -> str:
    validate_status(payload)
    lines = [f"Operator status: {payload['summary']['overall_state']}", f"Observed: {payload['observed_at']}"]
    lines.extend(f"- {name}: {payload['sections'][name]['state']}" for name in SECTION_NAMES)
    return "\n".join(lines) + "\n"


def canonical_json(payload: Mapping[str, Any]) -> str:
    validate_status(payload)
    # Section order is part of the strict schema contract. Sorting nested keys
    # would serialize a payload that fails validation when it is loaded again.
    return json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
