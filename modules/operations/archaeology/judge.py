"""Slice 5: deterministic, fail-closed Archaeology Judge."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from .counterevidence import COUNTEREVIDENCE_SCHEMA
from .evidence import (
    EvidenceError,
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
    write_atomic,
)
from .history import HISTORY_SCHEMA
from .hypotheses import HYPOTHESES_SCHEMA
from .inventory import INVENTORY_SCHEMA


JUDGE_SCHEMA = "giga.archaeologist.judge.v1"
HASH = re.compile(r"[0-9a-f]{64}")
QUOTED_NAME = re.compile(r"'([^']+)'|\"([^\"]+)\"")
POLICY = {
    "version": 1,
    "minimum_independent_tools": 2,
    "counterevidence_clearance": "CLEARED_WITH_COMPLETE_RUNTIME_TRACE",
    "history_clearance": "NO_RELATED_VARIANT_VERIFIED",
    "positive_counterevidence_result": "CONFLICT",
    "positive_history_result": "CONFLICT",
    "missing_or_incomplete_result": "UNKNOWN",
    "verified_candidate_cleanup_permitted": False,
    "verified_candidate_quarantine_candidate": True,
}


class JudgeError(ValueError):
    """Judge inputs are malformed, drifted, or cross-bound incorrectly."""


def _load(path: Path, schema: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JudgeError("input is not strict UTF-8 JSON") from exc
    try:
        validate_self_hash(value)
    except EvidenceError as exc:
        raise JudgeError(str(exc)) from exc
    if value.get("schema") != schema:
        raise JudgeError(f"unsupported input schema: {value.get('schema')!r}")
    if (
        value.get("authority_granted") is not False
        or value.get("cleanup_permitted") is not False
    ):
        raise JudgeError("input authority boundary is not closed")
    return value, raw


def _symbol(item: Mapping[str, Any]) -> str | None:
    symbol = item.get("detail", {}).get("symbol")
    if isinstance(symbol, str) and symbol:
        return symbol
    message = item.get("detail", {}).get("message", "")
    match = QUOTED_NAME.search(message) if isinstance(message, str) else None
    return (match.group(1) or match.group(2)) if match else None


def _subject(item: Mapping[str, Any]) -> dict[str, Any]:
    kind = item.get("kind")
    if kind in {"python-unused-observation", "graph-unreferenced-function-observation"}:
        return {
            "family": "unreferenced-python-symbol",
            "paths": item.get("paths"),
            "symbol": _symbol(item),
            "line": item.get("detail", {}).get("line"),
        }
    if kind == "syntactic-duplicate-observation":
        return {
            "family": "syntactic-duplicate-region",
            "paths": item.get("paths"),
            "first": item.get("detail", {}).get("first"),
            "second": item.get("detail", {}).get("second"),
        }
    return {"family": kind, "paths": item.get("paths"), "detail": item.get("detail")}


def _cleared_counterevidence(record: Mapping[str, Any] | None) -> bool:
    return bool(
        record
        and record.get("hypothesis_state") == "OBSERVED"
        and record.get("counterevidence_state") == "CLEARED_WITH_COMPLETE_RUNTIME_TRACE"
        and record.get("runtime_trace_available") is True
        and record.get("entrypoint_scope_complete") is True
        and record.get("evidence") == []
        and isinstance(record.get("trace_receipt_sha256"), str)
        and HASH.fullmatch(record["trace_receipt_sha256"])
    )


def _cleared_history(record: Mapping[str, Any] | None) -> bool:
    proof = record.get("absence_proof", {}) if record else {}
    receipts = proof.get("comparison_repository_receipts")
    return bool(
        record
        and record.get("hypothesis_state") == "OBSERVED"
        and record.get("historical_state") == "NO_RELATED_VARIANT_VERIFIED"
        and proof.get("all_refs_checked") is True
        and proof.get("rename_history_checked") is True
        and isinstance(receipts, list)
        and receipts
        and all(isinstance(value, str) and HASH.fullmatch(value) for value in receipts)
    )


def build_judgement(
    inventory_path: Path,
    hypotheses_path: Path,
    counterevidence_path: Path,
    history_path: Path,
) -> dict[str, Any]:
    inventory, inventory_raw = _load(inventory_path, INVENTORY_SCHEMA)
    hypotheses, hypotheses_raw = _load(hypotheses_path, HYPOTHESES_SCHEMA)
    counterevidence, counterevidence_raw = _load(
        counterevidence_path, COUNTEREVIDENCE_SCHEMA
    )
    history, history_raw = _load(history_path, HISTORY_SCHEMA)
    if hypotheses["inventory"]["receipt_sha256"] != inventory["receipt_sha256"]:
        raise JudgeError("hypothesis inventory binding mismatch")
    if hypotheses["inventory"]["file_sha256"] != sha256_bytes(inventory_raw):
        raise JudgeError("hypothesis inventory file hash mismatch")
    if counterevidence["inventory"]["receipt_sha256"] != inventory["receipt_sha256"]:
        raise JudgeError("counterevidence inventory binding mismatch")
    if counterevidence["inventory"]["file_sha256"] != sha256_bytes(inventory_raw):
        raise JudgeError("counterevidence inventory file hash mismatch")
    if counterevidence["hypotheses"]["receipt_sha256"] != hypotheses["receipt_sha256"]:
        raise JudgeError("counterevidence hypothesis binding mismatch")
    if counterevidence["hypotheses"]["file_sha256"] != sha256_bytes(hypotheses_raw):
        raise JudgeError("counterevidence hypothesis file hash mismatch")
    if history["inputs"]["inventory"]["receipt_sha256"] != inventory["receipt_sha256"]:
        raise JudgeError("history inventory binding mismatch")
    if history["inputs"]["inventory"]["file_sha256"] != sha256_bytes(inventory_raw):
        raise JudgeError("history inventory file hash mismatch")
    if (
        history["inputs"]["hypotheses"]["receipt_sha256"]
        != hypotheses["receipt_sha256"]
    ):
        raise JudgeError("history hypothesis binding mismatch")
    if history["inputs"]["hypotheses"]["file_sha256"] != sha256_bytes(hypotheses_raw):
        raise JudgeError("history hypothesis file hash mismatch")
    if (
        history["inputs"]["counterevidence"]["receipt_sha256"]
        != counterevidence["receipt_sha256"]
    ):
        raise JudgeError("history counterevidence binding mismatch")
    if history["inputs"]["counterevidence"]["file_sha256"] != sha256_bytes(
        counterevidence_raw
    ):
        raise JudgeError("history counterevidence file hash mismatch")

    findings = hypotheses.get("findings")
    if not isinstance(findings, list):
        raise JudgeError("hypothesis findings must be a list")
    finding_ids = [item.get("id") for item in findings if isinstance(item, Mapping)]
    if len(finding_ids) != len(findings) or len(set(finding_ids)) != len(finding_ids):
        raise JudgeError("hypothesis IDs must be present and unique")
    for item in findings:
        identity = {
            "tool": item.get("tool"),
            "kind": item.get("kind"),
            "paths": item.get("paths"),
            "detail": item.get("detail"),
        }
        if (
            item.get("state") != "OBSERVED"
            or item.get("authority_granted") is not False
            or item.get("cleanup_permitted") is not False
            or not isinstance(item.get("tool"), str)
            or not item["tool"]
            or not isinstance(item.get("id"), str)
            or not HASH.fullmatch(item["id"])
            or item["id"] != sha256_bytes(canonical_bytes(identity))
        ):
            raise JudgeError("hypothesis finding violates the observation boundary")

    counter_records = counterevidence.get("records")
    history_records = history.get("records")
    if not isinstance(counter_records, list) or not isinstance(history_records, list):
        raise JudgeError("counterevidence and history records must be lists")
    counter_ids = [
        item.get("hypothesis_id")
        for item in counter_records
        if isinstance(item, Mapping)
    ]
    history_ids = [
        item.get("hypothesis_id")
        for item in history_records
        if isinstance(item, Mapping)
    ]
    if len(counter_ids) != len(counter_records) or len(set(counter_ids)) != len(
        counter_ids
    ):
        raise JudgeError("counterevidence hypothesis IDs must be present and unique")
    if len(history_ids) != len(history_records) or len(set(history_ids)) != len(
        history_ids
    ):
        raise JudgeError("history hypothesis IDs must be present and unique")
    unknown_counter_ids = set(counter_ids) - set(finding_ids)
    unknown_history_ids = set(history_ids) - set(finding_ids)
    if unknown_counter_ids or unknown_history_ids:
        raise JudgeError("evidence contains records for unknown hypotheses")

    counter_by_id = {item["hypothesis_id"]: item for item in counter_records}
    history_by_id = {item["hypothesis_id"]: item for item in history_records}
    subject_tools: dict[str, set[str]] = defaultdict(set)
    subject_values: dict[str, dict[str, Any]] = {}
    subject_ids: dict[str, str] = {}
    for item in findings:
        subject = _subject(item)
        key = sha256_bytes(canonical_bytes(subject))
        subject_values[key] = subject
        subject_tools[key].add(item["tool"])
        subject_ids[item["id"]] = key

    decisions = []
    for item in findings:
        hypothesis_id = item["id"]
        subject_id = subject_ids[hypothesis_id]
        tools = sorted(subject_tools[subject_id])
        counter = counter_by_id.get(hypothesis_id)
        historical = history_by_id.get(hypothesis_id)
        lifecycle = ["OBSERVED"]
        reasons: list[str] = []
        classification = "UNKNOWN"
        if len(tools) < POLICY["minimum_independent_tools"]:
            reasons.append("INDEPENDENT_TOOL_CORROBORATION_MISSING")
        else:
            lifecycle.append("CORROBORATED")
        if counter and counter.get("counterevidence_state") == "PRESENT":
            classification = "CONFLICT"
            reasons.append("COUNTEREVIDENCE_PRESENT")
        elif not _cleared_counterevidence(counter):
            reasons.append("COUNTEREVIDENCE_INCOMPLETE_OR_UNKNOWN")
        else:
            lifecycle.append("COUNTEREVIDENCE_CHECKED")
        if (
            historical
            and historical.get("historical_state") == "RELATED_VARIANT_OBSERVED"
        ):
            classification = "CONFLICT"
            reasons.append("RELATED_HISTORY_OR_VARIANT_PRESENT")
        elif not _cleared_history(historical):
            reasons.append("HISTORICAL_ABSENCE_INCOMPLETE_OR_UNKNOWN")
        complete = (
            len(tools) >= POLICY["minimum_independent_tools"]
            and _cleared_counterevidence(counter)
            and _cleared_history(historical)
        )
        if complete and classification != "CONFLICT":
            classification = "VERIFIED_CANDIDATE"
            lifecycle.append("VERIFIED_CANDIDATE")
            reasons = ["ALL_DETERMINISTIC_CANDIDATE_GATES_PASS"]
        decisions.append(
            {
                "hypothesis_id": hypothesis_id,
                "subject_id": subject_id,
                "subject": subject_values[subject_id],
                "independent_tools": tools,
                "classification": classification,
                "lifecycle": lifecycle,
                "reasons": sorted(set(reasons)),
                "quarantine_candidate": classification == "VERIFIED_CANDIDATE",
                "cleanup_permitted": False,
                "deletion_permitted": False,
            }
        )
    counts = {
        state: sum(item["classification"] == state for item in decisions)
        for state in ("CONFLICT", "UNKNOWN", "VERIFIED_CANDIDATE")
    }
    return seal_document(
        {
            "schema": JUDGE_SCHEMA,
            "authority": "deterministic-candidate-classification-only",
            "authority_granted": False,
            "cleanup_permitted": False,
            "deletion_permitted": False,
            "policy": {**POLICY, "sha256": sha256_bytes(canonical_bytes(POLICY))},
            "inputs": {
                "inventory": {
                    "file_sha256": sha256_bytes(inventory_raw),
                    "receipt_sha256": inventory["receipt_sha256"],
                },
                "hypotheses": {
                    "file_sha256": sha256_bytes(hypotheses_raw),
                    "receipt_sha256": hypotheses["receipt_sha256"],
                },
                "counterevidence": {
                    "file_sha256": sha256_bytes(counterevidence_raw),
                    "receipt_sha256": counterevidence["receipt_sha256"],
                },
                "history": {
                    "file_sha256": sha256_bytes(history_raw),
                    "receipt_sha256": history["receipt_sha256"],
                },
            },
            "decisions": sorted(decisions, key=lambda item: item["hypothesis_id"]),
            "summary": {"hypotheses": len(decisions), **counts},
        }
    )


def render_judge_report(payload: Mapping[str, Any]) -> str:
    summary = payload["summary"]
    return "\n".join(
        [
            "# GIGA Archaeology deterministic Judge",
            "",
            f"- Hypotheses: {summary['hypotheses']}",
            f"- CONFLICT: {summary['CONFLICT']}",
            f"- UNKNOWN: {summary['UNKNOWN']}",
            f"- VERIFIED_CANDIDATE: {summary['VERIFIED_CANDIDATE']}",
            f"- Policy SHA-256: `{payload['policy']['sha256']}`",
            f"- Receipt SHA-256: `{payload['receipt_sha256']}`",
            "",
            "Only `VERIFIED_CANDIDATE` may enter a quarantine canary. It never permits deletion.",
            "CONFLICT and UNKNOWN fail closed. Scanner confidence and AI prose grant no authority.",
            "",
        ]
    )


def write_judgement(
    inventory_path: Path,
    hypotheses_path: Path,
    counterevidence_path: Path,
    history_path: Path,
    output: Path,
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists() or output.is_symlink():
        raise JudgeError("Judge output directory must not already exist")
    payload = build_judgement(
        inventory_path, hypotheses_path, counterevidence_path, history_path
    )
    output.mkdir(parents=True, mode=0o700)
    try:
        write_atomic(output / "judge.json", canonical_bytes(payload))
        write_atomic(
            output / "JUDGE_REPORT.md", render_judge_report(payload).encode("utf-8")
        )
    except EvidenceError as exc:
        raise JudgeError(str(exc)) from exc
    return payload
