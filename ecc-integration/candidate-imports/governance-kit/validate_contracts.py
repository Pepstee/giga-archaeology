#!/usr/bin/env python3
"""Validate staged governance evidence without external dependencies."""

from __future__ import annotations

import datetime as dt
import re


STATES = {"native", "adapter-backed", "instruction-backed", "reference-only"}
DECISIONS = {"staged", "certified", "rejected", "retired"}


def _required(record: dict, names: set[str]) -> list[str]:
    return [f"missing:{name}" for name in sorted(names - record.keys())]


def validate_adapter(record: dict) -> list[str]:
    required = {"id", "state", "supported_assets", "unsupported_surfaces", "onramp", "verification_commands", "risk_notes", "owner", "source_docs", "verified_at"}
    errors = _required(record, required)
    if record.get("state") not in STATES:
        errors.append("invalid:state")
    for field in ("verification_commands", "risk_notes", "source_docs"):
        if not record.get(field):
            errors.append(f"empty:{field}")
    try:
        dt.datetime.fromisoformat(record.get("verified_at", "").replace("Z", "+00:00"))
    except ValueError:
        errors.append("invalid:verified_at")
    return sorted(set(errors))


def validate_evaluator(record: dict) -> list[str]:
    required = {"scenario", "trace", "report", "candidates", "verifier", "rollback", "promoted"}
    errors = _required(record, required)
    candidates = record.get("candidates", [])
    decisions = {candidate.get("decision") for candidate in candidates if isinstance(candidate, dict)}
    if "accepted" not in decisions:
        errors.append("missing:accepted_candidate")
    if "rejected" not in decisions:
        errors.append("missing:rejected_negative_control")
    if record.get("promoted") and (errors or not record.get("rollback")):
        errors.append("unsafe:promotion_without_complete_evidence")
    return sorted(set(errors))


def validate_provenance(record: dict) -> list[str]:
    required = {"upstream", "commit", "source_path", "source_sha256", "destination", "adaptation", "tests", "decision"}
    errors = _required(record, required)
    if not re.fullmatch(r"[0-9a-f]{40}", record.get("commit", "")):
        errors.append("invalid:commit")
    if not re.fullmatch(r"[0-9a-f]{64}", record.get("source_sha256", "")):
        errors.append("invalid:source_sha256")
    if record.get("decision") not in DECISIONS:
        errors.append("invalid:decision")
    if not record.get("tests"):
        errors.append("empty:tests")
    return sorted(set(errors))
