"""Deterministic compilation of root-contained adapter capability evidence."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


MANIFEST_SCHEMA = "giga.adapter-evidence.v1"
REGISTRY_SCHEMA = "giga.adapter-registry.v1"
ADAPTER_STATES = ("native", "adapter-backed", "instruction-backed", "reference-only")
AUTHORITIES = ("read-only", "proposal-only", "bounded-write")
VERIFICATION_STATES = ("verified", "stale")
MAX_MANIFEST_BYTES = 1024 * 1024
REQUIRED_FIELDS = {
    "schema_version",
    "id",
    "state",
    "authority",
    "supported_assets",
    "unsupported_surfaces",
    "onramp",
    "verification_commands",
    "risk_notes",
    "owner",
    "source_docs",
    "evidence_paths",
    "verified_at",
}


class AdapterEvidenceError(ValueError):
    """Raised when an adapter claim lacks valid, contained evidence."""


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise AdapterEvidenceError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdapterEvidenceError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AdapterEvidenceError("timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _contained(root: Path, candidate: str | Path) -> Path:
    candidate = Path(candidate)
    if candidate.is_absolute():
        raise AdapterEvidenceError(f"absolute paths are forbidden: {candidate}")
    root = root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AdapterEvidenceError(f"path escapes repository root: {candidate}") from exc
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AdapterEvidenceError(f"manifest is not a regular file: {path.name}")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise AdapterEvidenceError(f"manifest exceeds {MAX_MANIFEST_BYTES} bytes: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdapterEvidenceError(f"malformed adapter manifest: {path.name}") from exc
    if not isinstance(value, dict):
        raise AdapterEvidenceError(f"adapter manifest must be a JSON object: {path.name}")
    return value


def _strings(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise AdapterEvidenceError(f"{field} must be a non-empty array")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise AdapterEvidenceError(f"{field} must contain non-empty strings")
    if len(set(value)) != len(value):
        raise AdapterEvidenceError(f"{field} contains duplicate values")
    return list(value)


def _file_record(root: Path, relative: str, field: str) -> dict[str, Any]:
    path = _contained(root, relative)
    if not path.is_file():
        raise AdapterEvidenceError(f"{field} does not resolve to a regular file: {relative}")
    digest_builder = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest_builder.update(chunk)
    digest = digest_builder.hexdigest()
    return {"path": Path(relative).as_posix(), "sha256": digest, "bytes": path.stat().st_size}


def _validate_manifest(root: Path, manifest: Mapping[str, Any], observed_at: str, stale_after_seconds: int) -> dict[str, Any]:
    if set(manifest) != REQUIRED_FIELDS:
        missing = sorted(REQUIRED_FIELDS - set(manifest))
        extra = sorted(set(manifest) - REQUIRED_FIELDS)
        raise AdapterEvidenceError(f"invalid manifest fields; missing={missing}, extra={extra}")
    if manifest["schema_version"] != MANIFEST_SCHEMA:
        raise AdapterEvidenceError("unsupported adapter manifest schema")
    adapter_id = manifest["id"]
    if not isinstance(adapter_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", adapter_id):
        raise AdapterEvidenceError("adapter id must be a lowercase kebab-case identifier")
    state = manifest["state"]
    authority = manifest["authority"]
    if state not in ADAPTER_STATES:
        raise AdapterEvidenceError(f"invalid adapter state: {state!r}")
    if authority not in AUTHORITIES:
        raise AdapterEvidenceError(f"invalid adapter authority: {authority!r}")
    if not isinstance(manifest["onramp"], str) or not manifest["onramp"].strip():
        raise AdapterEvidenceError("onramp must be a non-empty string")
    if not isinstance(manifest["owner"], str) or not manifest["owner"].strip():
        raise AdapterEvidenceError("owner must be a non-empty string")
    supported = _strings(manifest["supported_assets"], "supported_assets")
    unsupported = _strings(manifest["unsupported_surfaces"], "unsupported_surfaces", allow_empty=True)
    commands = _strings(manifest["verification_commands"], "verification_commands")
    risks = _strings(manifest["risk_notes"], "risk_notes")
    source_docs = _strings(manifest["source_docs"], "source_docs")
    evidence_paths = _strings(manifest["evidence_paths"], "evidence_paths")
    verified_at_text = manifest["verified_at"]
    verified_at = _timestamp(verified_at_text)
    age = (_timestamp(observed_at) - verified_at).total_seconds()
    if age < 0:
        raise AdapterEvidenceError(f"adapter {adapter_id} is verified in the future")
    verification_state = "stale" if age > stale_after_seconds else "verified"
    assets = [_file_record(root, path, "supported asset") for path in supported]
    docs = [_file_record(root, path, "source document") for path in source_docs]
    evidence = [_file_record(root, path, "evidence path") for path in evidence_paths]
    return {
        "id": adapter_id,
        "declared_state": state,
        "effective_state": state if verification_state == "verified" else "reference-only",
        "verification_state": verification_state,
        "authority": authority,
        "supported_assets": assets,
        "unsupported_surfaces": unsupported,
        "onramp": manifest["onramp"],
        "verification_commands": commands,
        "risk_notes": risks,
        "owner": manifest["owner"],
        "source_docs": docs,
        "evidence": evidence,
        "verified_at": verified_at_text,
    }


def _summary(adapters: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    declared = Counter(adapter["declared_state"] for adapter in adapters)
    effective = Counter(adapter["effective_state"] for adapter in adapters)
    verification = Counter(adapter["verification_state"] for adapter in adapters)
    authorities = Counter(adapter["authority"] for adapter in adapters)
    return {
        "total": len(adapters),
        "declared_states": {state: declared.get(state, 0) for state in ADAPTER_STATES},
        "effective_states": {state: effective.get(state, 0) for state in ADAPTER_STATES},
        "verification_states": {state: verification.get(state, 0) for state in VERIFICATION_STATES},
        "authorities": {authority: authorities.get(authority, 0) for authority in AUTHORITIES},
    }


def compile_registry(
    root: Path,
    observed_at: str,
    *,
    manifest_dir: str | Path = "adapters/manifests",
    stale_after_seconds: int = 30 * 86_400,
) -> dict[str, Any]:
    """Compile adapter claims into a hashed registry without executing their commands."""
    _timestamp(observed_at)
    if isinstance(stale_after_seconds, bool) or not isinstance(stale_after_seconds, int) or stale_after_seconds < 0:
        raise AdapterEvidenceError("stale_after_seconds must be a non-negative integer")
    directory = _contained(root, manifest_dir)
    if not directory.is_dir():
        raise AdapterEvidenceError(f"manifest directory is missing: {manifest_dir}")
    unexpected = sorted(path.name for path in directory.iterdir() if not path.name.startswith(".") and (not path.is_file() or path.suffix != ".json"))
    if unexpected:
        raise AdapterEvidenceError(f"manifest directory contains unsupported entries: {', '.join(unexpected)}")
    paths = sorted(path for path in directory.iterdir() if path.is_file() and path.suffix == ".json")
    if not paths:
        raise AdapterEvidenceError("manifest directory contains no adapter manifests")
    adapters: list[dict[str, Any]] = []
    ids: set[str] = set()
    for path in paths:
        if path.is_symlink():
            raise AdapterEvidenceError(f"manifest symlinks are forbidden: {path.name}")
        adapter = _validate_manifest(root.resolve(), _read_json(path), observed_at, stale_after_seconds)
        if adapter["id"] in ids:
            raise AdapterEvidenceError(f"duplicate adapter id: {adapter['id']}")
        ids.add(adapter["id"])
        adapters.append(adapter)
    adapters.sort(key=lambda item: item["id"])
    payload = {
        "schema_version": REGISTRY_SCHEMA,
        "authority": "read-only-evidence",
        "authority_granted": False,
        "observed_at": observed_at,
        "command_execution": False,
        "adapters": adapters,
        "summary": _summary(adapters),
    }
    validate_registry(payload)
    return payload


def validate_registry(payload: Mapping[str, Any]) -> None:
    """Strict validation for consumers that do not install a JSON Schema package."""
    required = {"schema_version", "authority", "authority_granted", "observed_at", "command_execution", "adapters", "summary"}
    if set(payload) != required:
        raise AdapterEvidenceError("invalid adapter registry fields")
    if payload["schema_version"] != REGISTRY_SCHEMA or payload["authority"] != "read-only-evidence":
        raise AdapterEvidenceError("invalid adapter registry identity or authority")
    if payload["command_execution"] is not False:
        raise AdapterEvidenceError("adapter registry must never execute manifest commands")
    if payload["authority_granted"] is not False:
        raise AdapterEvidenceError("adapter registry records claims but grants no authority")
    _timestamp(payload["observed_at"])
    adapters = payload["adapters"]
    if not isinstance(adapters, list) or not adapters:
        raise AdapterEvidenceError("adapter registry must contain adapters")
    expected_fields = {
        "id", "declared_state", "effective_state", "verification_state", "authority",
        "supported_assets", "unsupported_surfaces", "onramp", "verification_commands",
        "risk_notes", "owner", "source_docs", "evidence", "verified_at",
    }
    ids: list[str] = []
    for adapter in adapters:
        if not isinstance(adapter, dict) or set(adapter) != expected_fields:
            raise AdapterEvidenceError("invalid compiled adapter record")
        ids.append(adapter["id"])
        if adapter["declared_state"] not in ADAPTER_STATES or adapter["effective_state"] not in ADAPTER_STATES:
            raise AdapterEvidenceError("invalid compiled adapter state")
        if adapter["verification_state"] not in VERIFICATION_STATES or adapter["authority"] not in AUTHORITIES:
            raise AdapterEvidenceError("invalid compiled verification state or authority")
        _timestamp(adapter["verified_at"])
        if adapter["verification_state"] == "stale" and adapter["effective_state"] != "reference-only":
            raise AdapterEvidenceError("stale adapters must degrade to reference-only")
        for field in ("supported_assets", "source_docs", "evidence"):
            records = adapter[field]
            if not isinstance(records, list) or not records:
                raise AdapterEvidenceError(f"compiled adapter has no {field}")
            for record in records:
                if not isinstance(record, dict) or set(record) != {"path", "sha256", "bytes"}:
                    raise AdapterEvidenceError(f"invalid compiled file record in {field}")
                if not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
                    raise AdapterEvidenceError(f"invalid compiled file hash in {field}")
                if isinstance(record["bytes"], bool) or not isinstance(record["bytes"], int) or record["bytes"] < 0:
                    raise AdapterEvidenceError(f"invalid compiled file size in {field}")
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise AdapterEvidenceError("adapter registry ids must be unique and sorted")
    if payload["summary"] != _summary(adapters):
        raise AdapterEvidenceError("adapter registry summary disagrees with records")


def verify_registry_files(root: Path, payload: Mapping[str, Any]) -> None:
    """Re-hash compiled evidence so consumers cannot trust a stale file claim."""
    validate_registry(payload)
    for adapter in payload["adapters"]:
        for field in ("supported_assets", "source_docs", "evidence"):
            for recorded in adapter[field]:
                current = _file_record(root.resolve(), recorded["path"], field)
                if current != recorded:
                    raise AdapterEvidenceError(
                        f"compiled adapter evidence changed after verification: {recorded['path']}"
                    )


def current_adapter_file_records(
    root: Path, adapter: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Re-hash one adapter's exact bound files without following declared symlinks."""
    if not isinstance(adapter, Mapping):
        raise AdapterEvidenceError("compiled adapter record must be an object")
    root = root.resolve()
    result: dict[str, list[dict[str, Any]]] = {}
    for field in ("supported_assets", "source_docs", "evidence"):
        records = adapter.get(field)
        if not isinstance(records, list) or not records:
            raise AdapterEvidenceError(f"compiled adapter has no {field}")
        current_records: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict) or set(record) != {
                "path",
                "sha256",
                "bytes",
            }:
                raise AdapterEvidenceError(f"invalid compiled file record in {field}")
            relative = record.get("path")
            if not isinstance(relative, str) or not relative:
                raise AdapterEvidenceError(f"invalid compiled file path in {field}")
            _contained(root, relative)
            declared = root
            try:
                for part in Path(relative).parts:
                    declared /= part
                    if declared.is_symlink():
                        raise AdapterEvidenceError(
                            f"compiled adapter path contains a symlink: {relative}"
                        )
                current_records.append(_file_record(root, relative, field))
            except OSError as exc:
                raise AdapterEvidenceError(
                    f"compiled adapter path became unreadable: {relative}"
                ) from exc
        result[field] = current_records
    return result


def canonical_json(payload: Mapping[str, Any]) -> str:
    validate_registry(payload)
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_summary(payload: Mapping[str, Any]) -> str:
    validate_registry(payload)
    lines = [
        f"Adapter registry: {payload['summary']['total']} adapter(s)",
        f"Observed: {payload['observed_at']}",
        "Manifest commands executed: no",
        "Authority granted: no",
    ]
    lines.extend(
        f"- {adapter['id']}: {adapter['effective_state']} / {adapter['verification_state']} / {adapter['authority']}"
        for adapter in payload["adapters"]
    )
    return "\n".join(lines) + "\n"
