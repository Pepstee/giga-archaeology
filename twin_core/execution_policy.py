"""Deterministic observe-only routing for registered official execution surfaces."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping


REGISTRY_SCHEMA = "giga.execution-capability-registry.v1"
REQUEST_SCHEMA = "giga.execution-request.v1"
DECISION_SCHEMA = "giga.execution-route-decision.v1"
DEFAULT_REGISTRY = "execution/capabilities.v1.json"
MAX_REGISTRY_BYTES = 2 * 1024 * 1024
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUEST_FIELDS = {
    "schema_version",
    "registry_version",
    "capability_id",
    "operation_id",
    "caller_id",
    "idempotency_key",
    "input_sha256",
    "requested_authority",
    "target",
    "max_cost_usd",
    "max_tokens",
    "timeout_seconds",
    "reversibility",
    "expected_receipt_type",
}
CAPABILITY_FIELDS = {
    "capability_id",
    "operation_id",
    "approved_callers",
    "route",
    "maximum_authority",
    "target",
    "max_cost_usd",
    "max_tokens",
    "timeout_seconds",
    "reversibility",
    "expected_receipt_type",
    "proposal_contract",
    "live_shadow_policy",
    "evidence",
}
LIVE_SHADOW_POLICY_SCHEMA = "giga.live-shadow-policy.v1"
LIVE_SHADOW_POLICY_FIELDS = {
    "schema_version",
    "status",
    "sample_size_max",
    "provider_attempts_max",
    "provider_cost_usd_max",
    "provider_tokens_max",
    "max_samples_per_minute",
    "collection_window_seconds_max",
    "grant_validity_seconds_max",
    "retention_seconds_max",
    "target_binding",
    "sampling_rule",
    "data_scope",
    "storage_boundary",
    "telemetry_field_allowlist",
    "required_grant_fields",
    "required_receipts",
    "stop_conditions",
    "telemetry_collection_authorized",
    "raw_message_capture_authorized",
    "secret_material_capture_authorized",
    "external_export_authorized",
    "new_provider_execution_authorized",
    "enforcement_promotion_authorized",
}
LIVE_SHADOW_REQUIRED_GRANT_FIELDS = (
    "authority_id",
    "capability_record_sha256",
    "collection_window_seconds",
    "data_handling_policy_sha256",
    "escalation_contact",
    "expires_at",
    "issued_at",
    "justification",
    "max_cost_usd",
    "max_provider_attempts",
    "max_samples_per_minute",
    "max_tokens_total",
    "operator_authentication_receipt_sha256",
    "operator_identity",
    "registry_sha256",
    "retention_seconds",
    "revocation_contact",
    "sample_size",
    "source_commit",
    "target_selector_sha256",
)
LIVE_SHADOW_REQUIRED_RECEIPTS = (
    "legacy-completion-receipt",
    "provider-boundary-receipt",
    "shadow-comparison-receipt",
    "shadow-route-receipt",
)
LIVE_SHADOW_STOP_CONDITIONS = (
    "authority-expired",
    "authority-hash-drift",
    "comparison-integrity-error",
    "cost-ceiling-reached",
    "cost-or-token-evidence-missing",
    "data-scope-violation",
    "operator-revoked",
    "provider-error",
    "rate-limit-reached",
    "receipt-persistence-failure",
    "sample-size-reached",
    "secret-or-raw-content-detected",
    "target-mismatch",
)
LIVE_SHADOW_TELEMETRY_FIELDS = (
    "attempt_number",
    "comparison_reason_codes",
    "comparison_status",
    "completion_status",
    "event_id_sha256",
    "provider_boundary_seen",
    "shadow_decision",
    "shadow_decision_sha256",
    "shadow_reason_codes",
)
LIVE_SHADOW_POLICY_CONTRACT = {
    "schema_version": LIVE_SHADOW_POLICY_SCHEMA,
    "status": "operator-grant-required",
    "sample_size_max": 20,
    "provider_attempts_max": 20,
    "provider_cost_usd_max": 1.0,
    "provider_tokens_max": 81920,
    "max_samples_per_minute": 2,
    "collection_window_seconds_max": 3600,
    "grant_validity_seconds_max": 86400,
    "retention_seconds_max": 86400,
    "target_binding": "operator-issued-opaque-target-selector-sha256",
    "sampling_rule": "first-eligible-operator-events-no-synthetic-provider-calls",
    "data_scope": "existing-receipt-metadata-and-hashes-only",
    "storage_boundary": "local-twinstore-receipts-only",
    "telemetry_field_allowlist": LIVE_SHADOW_TELEMETRY_FIELDS,
    "required_grant_fields": LIVE_SHADOW_REQUIRED_GRANT_FIELDS,
    "required_receipts": LIVE_SHADOW_REQUIRED_RECEIPTS,
    "stop_conditions": LIVE_SHADOW_STOP_CONDITIONS,
    "telemetry_collection_authorized": False,
    "raw_message_capture_authorized": False,
    "secret_material_capture_authorized": False,
    "external_export_authorized": False,
    "new_provider_execution_authorized": False,
    "enforcement_promotion_authorized": False,
}


class ExecutionPolicyError(ValueError):
    """Mechanically invalid policy input that must fail closed."""

    def __init__(self, reason: str, message: str):
        super().__init__(f"[{reason}] {message}")
        self.reason = reason


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ExecutionPolicyError(
            "POLICY_JSON_INVALID", "value is not canonical JSON"
        ) from exc
    return rendered.encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _contained_regular_file(root: Path, relative: str, *, field: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ExecutionPolicyError(
            "POLICY_PATH_INVALID", f"{field} path must be non-empty"
        )
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ExecutionPolicyError("POLICY_PATH_INVALID", f"{field} path is absolute")
    root = root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ExecutionPolicyError(
            "POLICY_PATH_ESCAPE", f"{field} path escapes root"
        ) from exc
    if candidate.as_posix() != relative or any(
        part in {".", ".."} for part in candidate.parts
    ):
        raise ExecutionPolicyError(
            "POLICY_PATH_INVALID", f"{field} path is not canonical"
        )
    declared = root
    try:
        for part in candidate.parts:
            declared /= part
            if declared.is_symlink():
                raise ExecutionPolicyError(
                    "POLICY_PATH_SYMLINK", f"{field} path contains a symlink"
                )
        if not resolved.is_file():
            raise ExecutionPolicyError(
                "POLICY_PATH_MISSING", f"{field} path is not a regular file"
            )
    except OSError as exc:
        raise ExecutionPolicyError(
            "POLICY_PATH_UNREADABLE", f"{field} path is unreadable"
        ) from exc
    return resolved


def _json_object(raw: bytes) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID", "registry is not strict JSON"
        ) from exc
    if not isinstance(value, dict):
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID", "registry must be an object"
        )
    return value


def _nonnegative_number(
    value: Any, field: str, *, reason: str = "POLICY_REGISTRY_INVALID"
) -> float:
    try:
        finite = math.isfinite(value) if isinstance(value, (int, float)) else False
    except OverflowError:
        finite = False
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not finite
        or value < 0
    ):
        raise ExecutionPolicyError(reason, f"{field} must be finite and non-negative")
    return float(value)


def _positive_integer(
    value: Any, field: str, *, reason: str = "POLICY_REGISTRY_INVALID"
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExecutionPolicyError(reason, f"{field} must be positive")
    return value


def _validate_evidence(root: Path, records: Any) -> list[dict[str, Any]]:
    if not isinstance(records, list) or not records:
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID", "capability evidence is empty"
        )
    checked: list[dict[str, Any]] = []
    paths: list[str] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "bytes"}:
            raise ExecutionPolicyError(
                "POLICY_REGISTRY_INVALID", "invalid evidence record"
            )
        relative = record["path"]
        if not isinstance(relative, str) or not relative:
            raise ExecutionPolicyError(
                "POLICY_REGISTRY_INVALID", "invalid evidence path"
            )
        if not isinstance(record["sha256"], str) or not SHA256.fullmatch(
            record["sha256"]
        ):
            raise ExecutionPolicyError(
                "POLICY_REGISTRY_INVALID", "invalid evidence hash"
            )
        if (
            isinstance(record["bytes"], bool)
            or not isinstance(record["bytes"], int)
            or record["bytes"] < 0
        ):
            raise ExecutionPolicyError(
                "POLICY_REGISTRY_INVALID", "invalid evidence size"
            )
        path = _contained_regular_file(root, relative, field="evidence")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ExecutionPolicyError(
                "POLICY_EVIDENCE_UNREADABLE", "evidence became unreadable"
            ) from exc
        current = {"path": relative, "sha256": _sha256(raw), "bytes": len(raw)}
        if current != record:
            raise ExecutionPolicyError(
                "POLICY_EVIDENCE_DRIFT", f"evidence drifted: {relative}"
            )
        paths.append(relative)
        checked.append(current)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID", "evidence paths must be unique and sorted"
        )
    return checked


def _validate_live_shadow_policy(
    capability: Mapping[str, Any], policy: Any
) -> dict[str, Any]:
    """Validate the closed future live-shadow ceiling without granting authority."""
    if not isinstance(policy, dict) or set(policy) != LIVE_SHADOW_POLICY_FIELDS:
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID", "invalid live-shadow policy fields"
        )
    if _canonical_bytes(policy) != _canonical_bytes(LIVE_SHADOW_POLICY_CONTRACT):
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID",
            "live-shadow policy differs from the closed contract",
        )
    for field in (
        "telemetry_collection_authorized",
        "raw_message_capture_authorized",
        "secret_material_capture_authorized",
        "external_export_authorized",
        "new_provider_execution_authorized",
        "enforcement_promotion_authorized",
    ):
        if policy[field] is not False:
            raise ExecutionPolicyError(
                "POLICY_REGISTRY_INVALID",
                f"live-shadow policy must not pre-authorize {field}",
            )
    if policy["provider_cost_usd_max"] > float(capability["max_cost_usd"]):
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID",
            "live-shadow total cost exceeds the capability ceiling",
        )
    if policy["provider_tokens_max"] > (
        int(capability["max_tokens"]) * policy["sample_size_max"]
    ):
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID",
            "live-shadow total tokens exceed the per-sample ceiling",
        )
    return dict(policy)


def _validate_capability(root: Path, capability: Any) -> dict[str, Any]:
    if not isinstance(capability, dict) or set(capability) != CAPABILITY_FIELDS:
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID", "invalid capability fields"
        )
    for field in (
        "capability_id",
        "operation_id",
        "route",
        "maximum_authority",
        "target",
        "reversibility",
        "expected_receipt_type",
        "proposal_contract",
    ):
        if not isinstance(capability[field], str) or not capability[field]:
            raise ExecutionPolicyError("POLICY_REGISTRY_INVALID", f"invalid {field}")
    if (
        capability["route"] != "proposal-only"
        or capability["maximum_authority"] != "A0"
    ):
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID",
            "observe-only v1 accepts proposal-only A0 entries",
        )
    callers = capability["approved_callers"]
    if (
        not isinstance(callers, list)
        or not callers
        or any(not isinstance(item, str) or not item for item in callers)
        or callers != sorted(callers)
        or len(callers) != len(set(callers))
    ):
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID", "invalid approved callers"
        )
    _nonnegative_number(capability["max_cost_usd"], "max_cost_usd")
    _positive_integer(capability["max_tokens"], "max_tokens")
    _positive_integer(capability["timeout_seconds"], "timeout_seconds")
    validated = dict(capability)
    validated["live_shadow_policy"] = _validate_live_shadow_policy(
        capability, capability["live_shadow_policy"]
    )
    validated["evidence"] = _validate_evidence(root, capability["evidence"])
    return validated


def load_registry(
    root: Path, relative: str | Path = DEFAULT_REGISTRY
) -> tuple[dict[str, Any], bytes]:
    """Load and fully revalidate the one canonical observe-only capability registry."""
    root = root.resolve()
    path = _contained_regular_file(root, str(relative), field="registry")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_UNREADABLE", "registry is unreadable"
        ) from exc
    if len(raw) > MAX_REGISTRY_BYTES:
        raise ExecutionPolicyError("POLICY_REGISTRY_INVALID", "registry is too large")
    registry = _json_object(raw)
    required = {
        "schema_version",
        "registry_version",
        "mode",
        "authority",
        "authority_granted",
        "command_execution",
        "capabilities",
    }
    if set(registry) != required:
        raise ExecutionPolicyError("POLICY_REGISTRY_INVALID", "invalid registry fields")
    if (
        registry["schema_version"] != REGISTRY_SCHEMA
        or registry["registry_version"] != 1
        or registry["mode"] != "observe-only"
        or registry["authority"] != "routing-evidence-only"
        or registry["authority_granted"] is not False
        or registry["command_execution"] is not False
    ):
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_IDENTITY", "registry identity drifted"
        )
    capabilities = registry["capabilities"]
    if not isinstance(capabilities, list) or not capabilities:
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID", "registry has no capabilities"
        )
    validated = [_validate_capability(root, item) for item in capabilities]
    ids = [item["capability_id"] for item in validated]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_INVALID", "capability ids must be unique and sorted"
        )
    try:
        current_raw = path.read_bytes()
    except OSError as exc:
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_RACE", "registry became unreadable during validation"
        ) from exc
    if current_raw != raw:
        raise ExecutionPolicyError(
            "POLICY_REGISTRY_RACE", "registry changed during validation"
        )
    for capability in validated:
        if _validate_evidence(root, capability["evidence"]) != capability["evidence"]:
            raise ExecutionPolicyError(
                "POLICY_EVIDENCE_RACE", "capability evidence changed during validation"
            )
    result = dict(registry)
    result["capabilities"] = validated
    return result, raw


def _validate_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping) or set(request) != REQUEST_FIELDS:
        raise ExecutionPolicyError(
            "POLICY_REQUEST_INVALID", "request fields are missing or extra"
        )
    for field in (
        "capability_id",
        "operation_id",
        "caller_id",
        "idempotency_key",
        "target",
        "requested_authority",
        "reversibility",
        "expected_receipt_type",
    ):
        if not isinstance(request[field], str) or not request[field]:
            raise ExecutionPolicyError("POLICY_REQUEST_INVALID", f"invalid {field}")
        if len(request[field]) > 512:
            raise ExecutionPolicyError("POLICY_REQUEST_INVALID", f"{field} is too long")
    if request["schema_version"] != REQUEST_SCHEMA or request["registry_version"] != 1:
        raise ExecutionPolicyError(
            "POLICY_REQUEST_VERSION", "unsupported request version"
        )
    if not isinstance(request["input_sha256"], str) or not SHA256.fullmatch(
        request["input_sha256"]
    ):
        raise ExecutionPolicyError("POLICY_REQUEST_INVALID", "invalid input hash")
    _nonnegative_number(
        request["max_cost_usd"], "max_cost_usd", reason="POLICY_REQUEST_INVALID"
    )
    _positive_integer(
        request["max_tokens"], "max_tokens", reason="POLICY_REQUEST_INVALID"
    )
    _positive_integer(
        request["timeout_seconds"],
        "timeout_seconds",
        reason="POLICY_REQUEST_INVALID",
    )


def decide_route(
    root: Path,
    request: Mapping[str, Any],
    *,
    registry_path: str | Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    """Return a deterministic shadow decision; never execute or authorise the route."""
    _validate_request(request)
    registry, registry_raw = load_registry(root, registry_path)
    request_dict = dict(request)
    request_sha256 = _sha256(_canonical_bytes(request_dict))
    registry_sha256 = _sha256(registry_raw)
    matches = [
        item
        for item in registry["capabilities"]
        if item["capability_id"] == request["capability_id"]
    ]
    reasons: list[str] = []
    capability: dict[str, Any] | None = matches[0] if matches else None
    if capability is None:
        reasons.append("CAPABILITY_UNKNOWN")
    else:
        comparisons = (
            (
                request["operation_id"] == capability["operation_id"],
                "OPERATION_MISMATCH",
            ),
            (
                request["caller_id"] in capability["approved_callers"],
                "CALLER_NOT_APPROVED",
            ),
            (
                request["requested_authority"] == capability["maximum_authority"],
                "AUTHORITY_MISMATCH",
            ),
            (request["target"] == capability["target"], "TARGET_MISMATCH"),
            (
                request["max_cost_usd"] <= capability["max_cost_usd"],
                "COST_LIMIT_EXCEEDED",
            ),
            (request["max_tokens"] <= capability["max_tokens"], "TOKEN_LIMIT_EXCEEDED"),
            (
                request["timeout_seconds"] <= capability["timeout_seconds"],
                "TIMEOUT_LIMIT_EXCEEDED",
            ),
            (
                request["reversibility"] == capability["reversibility"],
                "REVERSIBILITY_MISMATCH",
            ),
            (
                request["expected_receipt_type"] == capability["expected_receipt_type"],
                "RECEIPT_TYPE_MISMATCH",
            ),
        )
        reasons.extend(code for passed, code in comparisons if not passed)
    decision = "refuse" if reasons else "proposal-only"
    capability_hash = (
        _sha256(_canonical_bytes(capability)) if capability is not None else None
    )
    return {
        "schema_version": DECISION_SCHEMA,
        "mode": "observe-only",
        "decision": decision,
        "reason_codes": sorted(reasons),
        "request_sha256": request_sha256,
        "registry_sha256": registry_sha256,
        "capability_record_sha256": capability_hash,
        "registry_version": registry["registry_version"],
        "execution_authorized": False,
        "authority_granted": False,
        "command_execution": False,
    }
