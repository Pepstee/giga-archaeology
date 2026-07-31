#!/usr/bin/env python3
"""Read-only validators for the GIGA memory-v2 preflight contracts and snapshots."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Mapping


VALIDATOR_VERSION = "giga.memory.preflight-validator.v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[a-z][a-z0-9._:-]{2,159}$")
SLUG = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")
ACTIVE_EPISTEMIC = {"operator-confirmed", "evidence-verified"}
ROOT = Path(__file__).resolve().parent
CONTRACT_FILES = (
    "MEMORY_SCHEMA_V2.json",
    "MEMORY_MIGRATION_PLAN.json",
    "TOMBSTONE_CONTRACT.json",
    "MANDATORY_VALIDATION_GATE.json",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def deterministic_id(prefix: str, value: Mapping[str, Any]) -> str:
    return f"{prefix}:{sha256_value(value)}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_digest(snapshot: Mapping[str, Any]) -> str:
    basis = {
        "schema_version": snapshot.get("schema_version"),
        "evaluated_at": snapshot.get("evaluated_at"),
        "source_manifest": snapshot.get("source_manifest"),
        "entries": snapshot.get("entries"),
        "tombstones": snapshot.get("tombstones"),
    }
    return sha256_value(basis)


def active_truth_digest(rows: list[dict[str, str]]) -> str:
    return sha256_value(
        sorted(
            rows,
            key=lambda item: (
                item["claim_id"],
                item["revision_id"],
                item["statement_sha256"],
            ),
        )
    )


def _unknown(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"state", "reason"}
        and value.get("state") == "unknown"
        and value.get("reason")
        in {"not-recorded", "not-applicable", "ambiguous", "requires-review"}
    )


def _dated(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value[:10])
    except ValueError:
        return False
    return len(value) == 10 or "T" in value


def _evidence_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "source_id",
        "source_sha256",
        "locator",
        "authority",
    }:
        return False
    if (
        not isinstance(value.get("source_id"), str)
        or not IDENTIFIER.fullmatch(value["source_id"])
        or not isinstance(value.get("source_sha256"), str)
        or not SHA256.fullmatch(value["source_sha256"])
    ):
        return False
    locator = value.get("locator")
    if not (_unknown(locator) or isinstance(locator, str) and locator):
        return False
    return value.get("authority") in {
        "operator-confirmed",
        "source-observation",
        "third-party-claim",
        "model-inference",
        "legacy-unclassified",
    }


def _result(
    command: str,
    errors: list[str],
    warnings: list[str],
    **counts: Any,
) -> dict[str, Any]:
    return {
        "validator_version": VALIDATOR_VERSION,
        "command": command,
        "ok": not errors,
        "counts": {
            "errors": len(errors),
            "warnings": len(warnings),
            **counts,
        },
        "error_codes": sorted(Counter(errors).items()),
        "warning_codes": sorted(Counter(warnings).items()),
    }


def validate_contracts(root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    documents: dict[str, Any] = {}
    for name in CONTRACT_FILES:
        path = root / name
        if not path.is_file() or path.is_symlink():
            errors.append("contract-missing-or-unsafe")
            continue
        try:
            documents[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append("contract-invalid-json")
    if len(documents) == len(CONTRACT_FILES):
        schema = documents["MEMORY_SCHEMA_V2.json"]
        plan = documents["MEMORY_MIGRATION_PLAN.json"]
        tombstone = documents["TOMBSTONE_CONTRACT.json"]
        gate = documents["MANDATORY_VALIDATION_GATE.json"]
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append("schema-draft")
        required = set(schema.get("required", []))
        if not {
            "snapshot_sha256",
            "active_truth_sha256",
            "evaluated_at",
            "entries",
            "tombstones",
            "derived_artifacts",
            "migration",
        }.issubset(required):
            errors.append("schema-required-fields")
        claim_required = set(
            schema.get("$defs", {}).get("claim", {}).get("required", [])
        )
        if not {"claim_id", "contradicts_claim_ids", "derived_from_claim_ids"}.issubset(
            claim_required
        ):
            errors.append("schema-claim-fields")
        target = plan.get("target_schema")
        if target != "giga.memory.snapshot.v2":
            errors.append("plan-target-schema")
        observed = plan.get("observed_legacy_store", {})
        if sum(observed.get("type_counts", {}).values()) != observed.get("entry_files"):
            errors.append("plan-type-count")
        if sum(observed.get("lifecycle_counts", {}).values()) != observed.get(
            "entry_files"
        ):
            errors.append("plan-lifecycle-count")
        risk_ids = {item.get("id") for item in plan.get("current_risks", [])}
        if not set(plan.get("acceptance", {}).get("blocking_ids", [])).issubset(
            risk_ids
        ):
            errors.append("plan-blocker-reference")
        if plan.get("live_migration_authorized") is not False:
            errors.append("plan-live-authority")
        if tombstone.get("memory_schema") != target:
            errors.append("tombstone-schema-reference")
        if tombstone.get("resurrection", {}).get("allowed") is not False:
            errors.append("tombstone-resurrection")
        if tombstone.get("rollback", {}).get("receipt_required") is not True:
            errors.append("tombstone-rollback")
        if gate.get("memory_schema") != target or gate.get("policy") != "fail-closed":
            errors.append("gate-schema-or-policy")
        stages = {item.get("stage") for item in gate.get("stages", [])}
        expected_stages = {
            "pre-context",
            "pre-proposal",
            "pre-commit",
            "post-commit",
            "pre-scheduled",
            "post-scheduled",
        }
        if stages != expected_stages:
            errors.append("gate-stages")
        if gate.get("rollback", {}).get("unit") != (
            "whole memory snapshot, never individual files"
        ):
            errors.append("gate-rollback-unit")
        if gate.get("compatibility", {}).get("dual_write") is not False:
            errors.append("gate-dual-write")
    return _result(
        "contracts",
        errors,
        warnings,
        contracts=len(documents),
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def validate_legacy(repo: Path, *, acceptance: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    sys.path.insert(0, str(repo))
    try:
        from twin_core.memory_validation import _frontmatter, validate_memory
    finally:
        sys.path.pop(0)

    plan = json.loads((ROOT / "MEMORY_MIGRATION_PLAN.json").read_text(encoding="utf-8"))
    expected = plan["observed_legacy_store"]
    memory = repo / "memory"
    entries = sorted((memory / "entries").glob("*.md"))
    if any(path.is_symlink() for path in [memory, *memory.rglob("*")]):
        errors.append("legacy-symlink")
    fields: Counter[str] = Counter()
    types: Counter[str] = Counter()
    lifecycles: Counter[str] = Counter()
    for path in entries:
        parsed = _frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        if parsed is None:
            errors.append("legacy-frontmatter")
            continue
        metadata, _ = parsed
        fields.update(metadata.keys())
        types[metadata.get("type", "<missing>")] += 1
        status = metadata.get("status", "<missing>")
        lifecycles[
            "superseded" if status.startswith("superseded-by") else status
        ] += 1
    current = validate_memory(memory)
    current_counts = current.get("counts", {})
    finding_codes = Counter(
        str(item.get("code")) for item in current.get("findings", [])
        if isinstance(item, dict)
    )
    normalized_types = {
        name: int(types.get(name, 0))
        for name in ("decision", "fact", "idea", "question", "reminder")
    }
    comparisons = (
        (len(entries), expected.get("entry_files"), "legacy-entry-count"),
        (current.get("indexed_entries"), expected.get("indexed_entries"), "legacy-index-count"),
        (dict(fields), expected.get("field_presence"), "legacy-field-counts"),
        (normalized_types, expected.get("type_counts"), "legacy-type-counts"),
        (dict(lifecycles), expected.get("lifecycle_counts"), "legacy-lifecycle-counts"),
        (bool(current.get("ok")), expected.get("current_validator", {}).get("ok"), "legacy-validator-state"),
        (current_counts.get("error"), expected.get("current_validator", {}).get("errors"), "legacy-error-count"),
        (current_counts.get("warning"), expected.get("current_validator", {}).get("warnings"), "legacy-warning-count"),
        (dict(finding_codes), expected.get("current_validator", {}).get("finding_codes"), "legacy-finding-codes"),
    )
    for actual, wanted, code in comparisons:
        if actual != wanted:
            errors.append(code)
    for relative, digest in expected.get("control_hashes", {}).items():
        path = repo / relative
        if not path.is_file() or path.is_symlink() or sha256_file(path) != digest:
            errors.append("legacy-control-drift")
    if not current.get("ok"):
        warnings.append("legacy-current-validator-red")
    if acceptance:
        if not current.get("ok"):
            errors.append("acceptance-live-validator-red")
        if not plan.get("acceptance", {}).get("ready"):
            errors.extend(
                "acceptance-declared-blocker"
                for _ in plan.get("acceptance", {}).get("blocking_ids", [])
            )
    return _result(
        "legacy-acceptance" if acceptance else "legacy-inventory",
        errors,
        warnings,
        entries=len(entries),
        indexed_entries=int(current.get("indexed_entries", 0)),
        current_errors=int(current_counts.get("error", 0)),
        current_warnings=int(current_counts.get("warning", 0)),
    )


def validate_snapshot(
    snapshot: Mapping[str, Any], *, acceptance: bool = False
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    expected_top = {
        "schema_version",
        "snapshot_sha256",
        "active_truth_sha256",
        "evaluated_at",
        "source_manifest",
        "entries",
        "tombstones",
        "derived_artifacts",
        "migration",
    }
    if set(snapshot) != expected_top:
        errors.append("snapshot-fields")
    if snapshot.get("schema_version") != "giga.memory.snapshot.v2":
        errors.append("snapshot-schema")
    evaluated_at = snapshot.get("evaluated_at")
    if not _dated(evaluated_at):
        errors.append("snapshot-evaluated-at")
        evaluation_day = "0000-00-00"
    else:
        evaluation_day = str(evaluated_at)[:10]
    for key in ("snapshot_sha256", "active_truth_sha256"):
        if not isinstance(snapshot.get(key), str) or not SHA256.fullmatch(
            str(snapshot.get(key))
        ):
            errors.append(f"{key}-shape")

    manifest = snapshot.get("source_manifest")
    if not isinstance(manifest, dict) or set(manifest) != {
        "history_complete",
        "sources",
    }:
        errors.append("source-manifest")
        manifest = {"history_complete": False, "sources": []}
    source_paths: set[str] = set()
    for source in manifest.get("sources", []):
        if not isinstance(source, dict) or set(source) != {"path", "sha256", "role"}:
            errors.append("source-shape")
            continue
        path = source.get("path")
        if (
            not isinstance(path, str)
            or path.startswith("/")
            or ".." in Path(path).parts
            or path in source_paths
        ):
            errors.append("source-path")
        source_paths.add(str(path))
        if not isinstance(source.get("sha256"), str) or not SHA256.fullmatch(
            source["sha256"]
        ):
            errors.append("source-hash")
        if source.get("role") not in {
            "legacy-entry",
            "legacy-index",
            "legacy-policy",
            "standing-context",
            "migration-receipt",
        }:
            errors.append("source-role")

    entries = snapshot.get("entries")
    if not isinstance(entries, list):
        errors.append("entries-shape")
        entries = []
    entry_by_id: dict[str, Mapping[str, Any]] = {}
    revision_by_id: dict[str, tuple[str, Mapping[str, Any]]] = {}
    claim_by_id: dict[str, tuple[str, str, Mapping[str, Any]]] = {}
    head_revisions: set[str] = set()
    slugs: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("entry-shape")
            continue
        required = {
            "entry_id",
            "slug",
            "legacy_path",
            "legacy_sha256",
            "head_revision_id",
            "revisions",
        }
        if set(entry) != required:
            errors.append("entry-fields")
        entry_id = entry.get("entry_id")
        if (
            not isinstance(entry_id, str)
            or not IDENTIFIER.fullmatch(entry_id)
            or entry_id in entry_by_id
        ):
            errors.append("entry-id")
            continue
        entry_by_id[entry_id] = entry
        slug = entry.get("slug")
        if not isinstance(slug, str) or not SLUG.fullmatch(slug) or slug in slugs:
            errors.append("entry-slug")
        slugs.add(str(slug))
        legacy_path = entry.get("legacy_path")
        if (
            not isinstance(legacy_path, str)
            or legacy_path.startswith("/")
            or ".." in Path(legacy_path).parts
        ):
            errors.append("entry-legacy-path")
        if not isinstance(entry.get("legacy_sha256"), str) or not SHA256.fullmatch(
            entry["legacy_sha256"]
        ):
            errors.append("entry-legacy-hash")
        elif entry_id != deterministic_id(
            "mem",
            {
                "legacy_path": entry.get("legacy_path"),
                "legacy_sha256": entry.get("legacy_sha256"),
            },
        ):
            errors.append("entry-id-formula")
        revisions = entry.get("revisions")
        if not isinstance(revisions, list) or not revisions:
            errors.append("revision-list")
            continue
        local_ids: set[str] = set()
        parent: dict[str, str | None] = {}
        for revision in revisions:
            if not isinstance(revision, dict):
                errors.append("revision-shape")
                continue
            expected_revision = {
                "revision_id",
                "parent_revision_id",
                "created_at",
                "lifecycle",
                "content",
                "content_sha256",
                "original_metadata",
                "claims",
            }
            if set(revision) != expected_revision:
                errors.append("revision-fields")
            revision_id = revision.get("revision_id")
            if (
                not isinstance(revision_id, str)
                or not IDENTIFIER.fullmatch(revision_id)
                or revision_id in revision_by_id
            ):
                errors.append("revision-id")
                continue
            local_ids.add(revision_id)
            revision_by_id[revision_id] = (entry_id, revision)
            parent[revision_id] = revision.get("parent_revision_id")
            if not _dated(revision.get("created_at")):
                errors.append("revision-created-at")
            if revision.get("lifecycle") not in {
                "active",
                "superseded",
                "archived",
                "tombstoned",
            }:
                errors.append("revision-lifecycle")
            content = revision.get("content")
            if not isinstance(content, str) or revision.get(
                "content_sha256"
            ) != sha256_text(content if isinstance(content, str) else ""):
                errors.append("revision-content-hash")
            elif revision_id != deterministic_id(
                "rev",
                {
                    "entry_id": entry_id,
                    "parent_revision_id": revision.get("parent_revision_id"),
                    "content_sha256": revision.get("content_sha256"),
                    "created_at": revision.get("created_at"),
                },
            ):
                errors.append("revision-id-formula")
            if not isinstance(revision.get("original_metadata"), dict) or any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in revision.get("original_metadata", {}).items()
            ):
                errors.append("revision-metadata")
            claims = revision.get("claims")
            if not isinstance(claims, list):
                errors.append("claim-list")
                continue
            for ordinal, claim in enumerate(claims):
                if not isinstance(claim, dict):
                    errors.append("claim-shape")
                    continue
                expected_claim = {
                    "claim_id",
                    "kind",
                    "statement",
                    "statement_sha256",
                    "lifecycle",
                    "epistemic",
                    "temporal",
                    "evidence",
                    "derived_from_claim_ids",
                    "contradicts_claim_ids",
                }
                if set(claim) != expected_claim:
                    errors.append("claim-fields")
                claim_id = claim.get("claim_id")
                if (
                    not isinstance(claim_id, str)
                    or not IDENTIFIER.fullmatch(claim_id)
                    or claim_id in claim_by_id
                ):
                    errors.append("claim-id")
                    continue
                claim_by_id[claim_id] = (entry_id, revision_id, claim)
                statement = claim.get("statement")
                if not isinstance(statement, str) or claim.get(
                    "statement_sha256"
                ) != sha256_text(statement if isinstance(statement, str) else ""):
                    errors.append("claim-statement-hash")
                elif claim_id != deterministic_id(
                    "clm",
                    {
                        "revision_id": revision_id,
                        "ordinal": ordinal,
                        "statement_sha256": claim.get("statement_sha256"),
                    },
                ):
                    errors.append("claim-id-formula")
                if claim.get("lifecycle") not in {
                    "active",
                    "superseded",
                    "archived",
                    "retracted",
                    "tombstoned",
                    "disputed",
                }:
                    errors.append("claim-lifecycle")
                if claim.get("kind") not in {
                    "fact",
                    "decision",
                    "idea",
                    "reminder",
                    "question",
                    "legacy-entry-assertion",
                }:
                    errors.append("claim-kind")
                epistemic = claim.get("epistemic")
                if not isinstance(epistemic, dict) or set(epistemic) != {
                    "status",
                    "confidence",
                    "reviewed_by",
                }:
                    errors.append("claim-epistemic")
                else:
                    if epistemic.get("status") not in {
                        "operator-confirmed",
                        "evidence-verified",
                        "source-observed",
                        "model-inferred",
                        "legacy-unreviewed",
                        "disputed",
                        "retracted",
                        "unknown",
                    }:
                        errors.append("claim-epistemic-status")
                    confidence = epistemic.get("confidence")
                    if not (
                        _unknown(confidence)
                        or isinstance(confidence, (int, float))
                        and not isinstance(confidence, bool)
                        and 0 <= confidence <= 1
                    ):
                        errors.append("claim-confidence")
                    reviewed = epistemic.get("reviewed_by")
                    if not (_unknown(reviewed) or isinstance(reviewed, str) and reviewed):
                        errors.append("claim-reviewer")
                temporal = claim.get("temporal")
                if not isinstance(temporal, dict) or set(temporal) != {
                    "observed_at",
                    "valid_from",
                    "valid_until",
                }:
                    errors.append("claim-temporal")
                else:
                    for value in temporal.values():
                        if not (_unknown(value) or _dated(value)):
                            errors.append("claim-temporal-value")
                evidence = claim.get("evidence")
                if (
                    not isinstance(evidence, list)
                    or not evidence
                    or any(not _evidence_valid(value) for value in evidence)
                ):
                    errors.append("claim-evidence")
                for key in ("derived_from_claim_ids", "contradicts_claim_ids"):
                    values = claim.get(key)
                    if (
                        not isinstance(values, list)
                        or any(not isinstance(value, str) for value in values)
                        or len(values) != len(set(values))
                    ):
                        errors.append(f"claim-{key}")
        for revision_id, parent_id in parent.items():
            if parent_id is not None and parent_id not in local_ids:
                errors.append("revision-parent")
            seen: set[str] = set()
            cursor: str | None = revision_id
            while cursor is not None and cursor in parent:
                if cursor in seen:
                    errors.append("revision-cycle")
                    break
                seen.add(cursor)
                cursor = parent[cursor]
        head = entry.get("head_revision_id")
        if head not in local_ids:
            errors.append("head-revision")
        else:
            head_revisions.add(head)
        for revision_id in local_ids - {str(head)}:
            if revision_by_id[revision_id][1].get("lifecycle") == "active":
                errors.append("non-head-active")

    for claim_id, (_, _, claim) in claim_by_id.items():
        for parent_id in claim.get("derived_from_claim_ids", []):
            if parent_id not in claim_by_id or parent_id == claim_id:
                errors.append("claim-parent-reference")
        for other_id in claim.get("contradicts_claim_ids", []):
            if other_id not in claim_by_id or other_id == claim_id:
                errors.append("contradiction-reference")
            elif claim_id not in claim_by_id[other_id][2].get(
                "contradicts_claim_ids", []
            ):
                errors.append("contradiction-asymmetry")

    tombstones = snapshot.get("tombstones")
    if not isinstance(tombstones, list):
        errors.append("tombstones-shape")
        tombstones = []
    tombstone_ids: set[str] = set()
    target_tombstones: dict[tuple[str, str], str] = {}
    excluded: set[str] = set()
    tombstoned_revisions: set[str] = set()
    for tombstone in tombstones:
        if not isinstance(tombstone, dict):
            errors.append("tombstone-shape")
            continue
        expected_tombstone = {
            "tombstone_id",
            "target_type",
            "target_id",
            "target_sha256",
            "reason_code",
            "rationale",
            "effective_at",
            "authorized_by",
            "evidence",
            "invalidates_derivatives",
        }
        if set(tombstone) != expected_tombstone:
            errors.append("tombstone-fields")
        tombstone_id = tombstone.get("tombstone_id")
        if (
            not isinstance(tombstone_id, str)
            or not IDENTIFIER.fullmatch(tombstone_id)
            or tombstone_id in tombstone_ids
        ):
            errors.append("tombstone-id")
            continue
        tombstone_ids.add(tombstone_id)
        target_type = tombstone.get("target_type")
        target_id = tombstone.get("target_id")
        key = (str(target_type), str(target_id))
        if key in target_tombstones:
            errors.append("tombstone-duplicate-target")
        target_tombstones[key] = tombstone_id
        target_hash: str | None = None
        if target_type == "entry" and target_id in entry_by_id:
            target_hash = str(entry_by_id[target_id].get("legacy_sha256"))
            for claim_id, (entry_id, _, _) in claim_by_id.items():
                if entry_id == target_id:
                    excluded.add(claim_id)
        elif target_type == "revision" and target_id in revision_by_id:
            target_hash = str(revision_by_id[target_id][1].get("content_sha256"))
            tombstoned_revisions.add(target_id)
            for claim_id, (_, revision_id, _) in claim_by_id.items():
                if revision_id == target_id:
                    excluded.add(claim_id)
        elif target_type == "claim" and target_id in claim_by_id:
            target_hash = str(claim_by_id[target_id][2].get("statement_sha256"))
            excluded.add(target_id)
        else:
            errors.append("tombstone-target")
        if target_hash is not None and tombstone.get("target_sha256") != target_hash:
            errors.append("tombstone-target-hash")
        if tombstone_id != deterministic_id(
            "tmb",
            {
                "target_type": tombstone.get("target_type"),
                "target_id": tombstone.get("target_id"),
                "target_sha256": tombstone.get("target_sha256"),
                "reason_code": tombstone.get("reason_code"),
                "effective_at": tombstone.get("effective_at"),
                "authorized_by": tombstone.get("authorized_by"),
            },
        ):
            errors.append("tombstone-id-formula")
        if tombstone.get("invalidates_derivatives") is not True:
            errors.append("tombstone-invalidation")
        if tombstone.get("reason_code") not in {
            "operator-retracted",
            "superseded",
            "duplicate",
            "false",
            "privacy",
            "expired",
            "corrupt",
            "policy",
        }:
            errors.append("tombstone-reason")
        if tombstone.get("authorized_by") not in {
            "operator",
            "deterministic-policy",
        }:
            errors.append("tombstone-authority")
        if not isinstance(tombstone.get("rationale"), str) or not tombstone.get(
            "rationale"
        ):
            errors.append("tombstone-rationale")
        if (
            not isinstance(tombstone.get("evidence"), list)
            or not tombstone.get("evidence")
            or any(not _evidence_valid(value) for value in tombstone["evidence"])
        ):
            errors.append("tombstone-evidence")
        if not _dated(tombstone.get("effective_at")):
            errors.append("tombstone-effective-at")

    for claim_id, (_, revision_id, claim) in claim_by_id.items():
        epistemic = claim.get("epistemic", {})
        temporal = claim.get("temporal", {})
        if revision_id not in head_revisions:
            excluded.add(claim_id)
        if revision_by_id.get(revision_id, ("", {}))[1].get("lifecycle") != "active":
            excluded.add(claim_id)
        if claim.get("lifecycle") != "active":
            excluded.add(claim_id)
        if epistemic.get("status") not in ACTIVE_EPISTEMIC:
            excluded.add(claim_id)
        valid_from = temporal.get("valid_from")
        valid_until = temporal.get("valid_until")
        if isinstance(valid_from, str) and valid_from[:10] > evaluation_day:
            excluded.add(claim_id)
        if isinstance(valid_until, str) and valid_until[:10] < evaluation_day:
            excluded.add(claim_id)
    unresolved_conflicts: set[str] = set()
    for claim_id, (_, _, claim) in claim_by_id.items():
        if claim_id in excluded:
            continue
        for other_id in claim.get("contradicts_claim_ids", []):
            if other_id not in excluded:
                unresolved_conflicts.update((claim_id, other_id))
    excluded.update(unresolved_conflicts)

    changed = True
    while changed:
        changed = False
        for claim_id, (_, _, claim) in claim_by_id.items():
            if claim_id not in excluded and any(
                parent in excluded for parent in claim.get("derived_from_claim_ids", [])
            ):
                excluded.add(claim_id)
                changed = True

    active_rows = [
        {
            "claim_id": claim_id,
            "revision_id": revision_id,
            "statement_sha256": str(claim.get("statement_sha256")),
        }
        for claim_id, (_, revision_id, claim) in claim_by_id.items()
        if claim_id not in excluded
    ]
    expected_active_hash = active_truth_digest(active_rows)
    if snapshot.get("active_truth_sha256") != expected_active_hash:
        errors.append("active-truth-hash")
    expected_snapshot_hash = snapshot_digest(snapshot)
    if snapshot.get("snapshot_sha256") != expected_snapshot_hash:
        errors.append("snapshot-hash")

    artifacts = snapshot.get("derived_artifacts")
    if not isinstance(artifacts, list):
        errors.append("derived-artifacts-shape")
        artifacts = []
    artifact_ids: set[str] = set()
    active_claim_ids = {row["claim_id"] for row in active_rows}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append("derived-artifact-shape")
            continue
        expected_artifact = {
            "artifact_id",
            "stage",
            "artifact_sha256",
            "memory_snapshot_sha256",
            "active_truth_sha256",
            "claim_dependencies",
            "revision_dependencies",
            "state",
            "invalidated_by",
        }
        if set(artifact) != expected_artifact:
            errors.append("derived-artifact-fields")
        artifact_id = artifact.get("artifact_id")
        if (
            not isinstance(artifact_id, str)
            or not IDENTIFIER.fullmatch(artifact_id)
            or artifact_id in artifact_ids
        ):
            errors.append("derived-artifact-id")
        artifact_ids.add(str(artifact_id))
        claim_dependencies = artifact.get("claim_dependencies", [])
        revision_dependencies = artifact.get("revision_dependencies", [])
        if (
            not isinstance(claim_dependencies, list)
            or any(not isinstance(value, str) for value in claim_dependencies)
            or len(claim_dependencies) != len(set(claim_dependencies))
            or not isinstance(revision_dependencies, list)
            or any(not isinstance(value, str) for value in revision_dependencies)
            or len(revision_dependencies) != len(set(revision_dependencies))
        ):
            errors.append("derived-dependencies-shape")
            claim_dependencies = []
            revision_dependencies = []
        for key in (
            "artifact_sha256",
            "memory_snapshot_sha256",
            "active_truth_sha256",
        ):
            if not isinstance(artifact.get(key), str) or not SHA256.fullmatch(
                artifact[key]
            ):
                errors.append("derived-hash")
        if artifact.get("stage") not in {
            "context",
            "proposal",
            "commit",
            "daily",
            "training",
            "graph",
            "profile",
        }:
            errors.append("derived-stage")
        if artifact.get("state") not in {"current", "stale", "superseded"}:
            errors.append("derived-state")
        invalidated_by = artifact.get("invalidated_by")
        if (
            not isinstance(invalidated_by, list)
            or any(not isinstance(value, str) for value in invalidated_by)
            or len(invalidated_by) != len(set(invalidated_by))
        ):
            errors.append("derived-invalidated-by")
        if any(value not in claim_by_id for value in claim_dependencies):
            errors.append("derived-claim-reference")
        if any(value not in revision_by_id for value in revision_dependencies):
            errors.append("derived-revision-reference")
        invalid = (
            artifact.get("memory_snapshot_sha256") != expected_snapshot_hash
            or artifact.get("active_truth_sha256") != expected_active_hash
            or any(value not in active_claim_ids for value in claim_dependencies)
            or any(value not in head_revisions for value in revision_dependencies)
            or any(value in tombstoned_revisions for value in revision_dependencies)
        )
        if invalid and artifact.get("state") == "current":
            errors.append("derived-current-invalid")
        if invalid and not artifact.get("invalidated_by"):
            errors.append("derived-invalidation-receipt")

    migration = snapshot.get("migration")
    if not isinstance(migration, dict) or set(migration) != {
        "rules_version",
        "status",
        "blockers",
        "unknown_values_preserved",
    }:
        errors.append("migration-shape")
        migration = {}
    else:
        if migration.get("rules_version") != "giga.memory.migration-rules.v2":
            errors.append("migration-rules")
        if migration.get("status") not in {
            "preflight",
            "projected",
            "blocked",
            "accepted",
        }:
            errors.append("migration-status")
        blockers = migration.get("blockers")
        if (
            not isinstance(blockers, list)
            or any(not isinstance(value, str) or not value for value in blockers)
            or len(blockers) != len(set(blockers))
        ):
            errors.append("migration-blockers")
        if not isinstance(migration.get("unknown_values_preserved"), bool):
            errors.append("migration-unknown-preservation")
    if acceptance:
        if manifest.get("history_complete") is not True:
            errors.append("acceptance-history-incomplete")
        if migration.get("status") != "accepted":
            errors.append("acceptance-migration-status")
        if migration.get("blockers"):
            errors.append("acceptance-blockers")
        if migration.get("unknown_values_preserved") is not True:
            errors.append("acceptance-unknown-loss")
        for _, revision_id, claim in claim_by_id.values():
            if (
                revision_id in head_revisions
                and revision_by_id[revision_id][1].get("lifecycle") == "active"
                and claim.get("lifecycle") == "active"
                and claim.get("epistemic", {}).get("status")
                in {"legacy-unreviewed", "unknown"}
            ):
                errors.append("acceptance-unreviewed-head-claim")
    elif excluded:
        warnings.append("inactive-claims-excluded")

    return _result(
        "snapshot-acceptance" if acceptance else "snapshot-inventory",
        errors,
        warnings,
        entries=len(entry_by_id),
        revisions=len(revision_by_id),
        claims=len(claim_by_id),
        tombstones=len(tombstone_ids),
        active_truth_claims=len(active_rows),
        derived_artifacts=len(artifact_ids),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("contracts")
    legacy = sub.add_parser("legacy")
    legacy.add_argument("--repo", type=Path, default=_repo_root())
    legacy.add_argument("--acceptance", action="store_true")
    snapshot_parser = sub.add_parser("snapshot")
    snapshot_parser.add_argument("path", type=Path)
    snapshot_parser.add_argument("--acceptance", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "contracts":
        result = validate_contracts()
    elif args.command == "legacy":
        result = validate_legacy(args.repo.resolve(), acceptance=args.acceptance)
    else:
        payload = json.loads(args.path.read_text(encoding="utf-8"))
        result = validate_snapshot(payload, acceptance=args.acceptance)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
