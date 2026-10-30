"""Reference-aware retention for immutable Archaeology map generations.

The navigation producers intentionally publish immutable generations and move a
small authenticated ``CURRENT.json`` pointer.  This module owns the distinct
storage lifecycle for those generations.  It never removes repository source
and never treats a map result as cleanup authority.

Storage reduction is deliberately evidence preserving:

1. stale generations named by historical reports are deterministically compressed
   in place and remain exactly restorable for native historical queries;
2. stale, unreferenced generations are moved into authenticated quarantine;
3. a later invocation may purge a quarantine after its grace period, while
   retaining the intent/outcome receipts and any semantic failure receipt.

Any incomplete reference scan, malformed store, symlink, concurrent drift,
failed restore proof, or failed post-move authentication prevents destructive
progress.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from .evidence import (
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
    write_atomic,
)
from .os_support import lock_file, unlock_file
from .mapper import MAPPER_POINTER_SCHEMA
from .navigation_inventory import POINTER_SCHEMA as INVENTORY_POINTER_SCHEMA
from .navigation_inventory import _replace_atomic
from .scip_map import (
    SCIP_STORE_CURRENT_SCHEMA,
    ScipMapError,
    current_scip_store,
)
from .semantic_graph import SEMANTIC_POINTER_SCHEMA

RETENTION_PLAN_SCHEMA = "giga.archaeologist.retention-plan.v3"
RETENTION_INTENT_SCHEMA = "giga.archaeologist.retention-quarantine-intent.v1"
RETENTION_OUTCOME_SCHEMA = "giga.archaeologist.retention-quarantine-outcome.v1"
RETENTION_PURGE_SCHEMA = "giga.archaeologist.retention-purge-outcome.v1"
RETENTION_RUN_SCHEMA = "giga.archaeologist.retention-run.v2"
RETENTION_POINTER_SCHEMA = "giga.archaeologist.retention-current.v1"
RETENTION_COMPACTION_SCHEMA = "giga.archaeologist.retention-compaction.v1"
RETENTION_INSPECTION_SCHEMA = "giga.archaeology.retention-receipt-inspection.v1"
RETENTION_RECOVERY_SCHEMA = "giga.archaeologist.retention-compaction-recovery.v1"
RETENTION_STREAM_VERIFICATION_SCHEMA = (
    "giga.archaeology.retention-restore-stream-verification.v1"
)
SEMANTIC_COMPACTION_SCHEMA = "giga.archaeology.semantic-compaction.v1"
SEMANTIC_RESTORE_SCHEMA = "giga.archaeology.semantic-restore-result.v1"
SEMANTIC_ROUND_TRIP_SCHEMA = "giga.archaeology.semantic-round-trip-canary.v1"
SEMANTIC_STREAM_VERIFICATION_SCHEMA = (
    "giga.archaeology.semantic-restore-stream-verification.v1"
)
SCIP_COMPACTION_SCHEMA = "giga.archaeology.scip-compaction.v1"
SCIP_RESTORE_SCHEMA = "giga.archaeology.scip-restore-result.v1"
SCIP_ROUND_TRIP_SCHEMA = "giga.archaeology.scip-round-trip-canary.v1"
SCIP_STREAM_VERIFICATION_SCHEMA = (
    "giga.archaeology.scip-restore-stream-verification.v1"
)
DERIVED_FAMILY_ASSESSMENT_SCHEMA = (
    "giga.archaeology.derived-family-retention-assessment.v1"
)
DERIVED_MAP_LINEAGE_ASSESSMENT_SCHEMA = (
    "giga.archaeology.cross-store-derived-map-lineage-assessment.v1"
)
DERIVED_MAP_LINEAGE_PRIVATE_LEDGER_SCHEMA = (
    "giga.archaeology.cross-store-derived-map-lineage-private-ledger.v1"
)
DERIVED_MAP_LINEAGE_REPORT_SCHEMA = (
    "giga.archaeology.cross-store-derived-map-lineage-report.v1"
)
DERIVED_MAP_ACTIVE_CONSUMER_REGISTRY_SCHEMA = (
    "giga.archaeology.active-derived-map-consumers.v1"
)
_M74_PRIVATE_LEDGER_BINDING_CORRECTION_SCHEMA = (
    "giga.archaeology.m74-private-ledger-binding-correction.v1"
)
_M74_PRIVATE_LEDGER_SAFE_PROJECTION_SCHEMA = (
    "giga.archaeology.m74-private-ledger-safe-projection.v1"
)
M75_MAC_DERIVED_MAP_RETENTION_CANDIDATE_PLAN_SCHEMA = (
    "giga.archaeology.mac-derived-map-retention-candidate-plan.v1"
)
M77_DERIVED_MAP_LIVENESS_OBSERVATION_SCHEMA = (
    "giga.archaeology.derived-map-liveness-observation.v2"
)
M77_SCOPED_DERIVED_MAP_LIVENESS_ASSESSMENT_SCHEMA = (
    "giga.archaeology.scoped-derived-map-liveness-assessment.v1"
)
M77_TASK_LEASE_CENSUS_SCHEMA = "giga.archaeology.codex-task-lease-census.v1"
_BYTE_ACCOUNTING_CLASSES = (
    "RECOGNIZED_DERIVED_PAYLOAD",
    "PRESERVED_HISTORY_METADATA_LOG_REPORT_RECEIPT_POINTER",
    "UNSUPPORTED_UNKNOWN",
    "EXCLUDED_BUT_COUNTED_PRIVATE_WORKSPACE",
    "OTHER_EXPLICIT_RUNTIME_FILE",
)
_M74_PARENT_ASSESSMENT_RECEIPT_SHA256 = (
    "a952606206a26379eaed312b802f7043bc3d1a33e27a72d2f190c8798660e0a1"
)
_M74_EXPECTED_COUNTS = {
    "current_pointer_count": 65,
    "derived_store_family_count": 61,
    "metadata_store_family_count": 4,
    "generation_records": 359,
    "payload_records": 400,
    "regular_file_count": 12859,
    "regular_file_bytes": 37427641649,
}
_M74_EXPECTED_BYTE_CLASS_BYTES = {
    "EXCLUDED_BUT_COUNTED_PRIVATE_WORKSPACE": 20537764,
    "OTHER_EXPLICIT_RUNTIME_FILE": 453746613,
    "PRESERVED_HISTORY_METADATA_LOG_REPORT_RECEIPT_POINTER": 659426593,
    "RECOGNIZED_DERIVED_PAYLOAD": 35395658858,
    "UNSUPPORTED_UNKNOWN": 898271821,
}
_M74_PRIVATE_LEDGER_BINDING_REFUSAL = (
    "M74 private ledger correction refused: CONTENT_UNAVAILABLE"
)
_M75_CANDIDATE_PLAN_REFUSAL = (
    "M75 derived-map retention candidate plan refused: CONTENT_UNAVAILABLE"
)
_M77_LIVENESS_ASSESSMENT_REFUSAL = (
    "M77 derived-map liveness assessment refused: CONTENT_UNAVAILABLE"
)
_M75_STALE_AFTER_SECONDS = 24 * 60 * 60
_M75_GLOBAL_RECENT_WINDOW = 3
_M77_OBSERVATION_FRESHNESS_SECONDS = 60 * 60
_M77_LAUNCHD_LABEL_SUFFIXES = (
    ".giga-navigation-maintenance",
    ".giga-navigation-milestone",
)
_M77_DEFAULT_COHORT_BYTES = {
    "generation-000156": ("mapper", 101625089),
    "generation-000160": ("mapper", 25034809),
    "generation-000167": ("mapper", 24654219),
    "generation-000168": ("mapper", 98080003),
    "generation-000170": ("mapper", 94716218),
    "generation-000175": ("mapper", 90542612),
    "generation-000179": ("mapper", 19966212),
    "generation-000320": ("inventory", 221434),
    "generation-000326": ("inventory", 651264),
    "generation-000327": ("inventory", 651264),
    "generation-000330": ("inventory", 647168),
}
_M77_DEFAULT_COHORT_ALIASES = tuple(sorted(_M77_DEFAULT_COHORT_BYTES))
_M77_ACCEPTED_M75_PLAN_RECEIPT_SHA256 = (
    "b6ff495e13da34380882bd7b2dee938bf8e24ca1b4e7a31d7d5aa73244a4bfe9"
)
_M75_SUPPORTED_MANIFEST_SCHEMAS = {
    "giga.archaeologist.mapper-manifest.v1",
    "giga.archaeologist.mapper-manifest.v2",
    "giga.archaeologist.scip-store-catalog.v1",
    "giga.navigation.inventory-manifest.v1",
    "giga.navigation.inventory-manifest.v2",
    "giga.navigation.semantic-graph-manifest.v1",
}
_M75_SUPPORTED_GENERATION_STATUSES = {
    "CURRENT",
    "OBSERVED_LOCAL_PRECISION_STORE",
    "OBSERVED_LOCAL_PRECISION_STORE_PARTIAL",
    "PARTIAL",
}
_M75_INCOMPLETE_GENERATION_STATUSES = {
    "OBSERVED_LOCAL_PRECISION_STORE_PARTIAL",
    "PARTIAL",
}
_M75_SUPPORTED_PAYLOAD_CLASSIFICATIONS = {
    "PAYLOAD_RETIRE_CANDIDATE",
    "RETAIN_ACTIVE_CONSUMER",
    "RETAIN_CURRENT",
    "RETAIN_GLOBAL_RECENT",
    "RETAIN_NONREGENERABLE_DIRTY_SOURCE",
    "UNKNOWN_BLOCKED",
}
_RUN_ID_FORMAT = "%Y%m%dT%H%M%S.%fZ"
_READ_LIMIT = 16 * 1024 * 1024
_RETENTION_RECEIPT_SCHEMAS = {
    "giga.archaeologist.retention-plan.v1": ("plan", 1, 3),
    "giga.archaeologist.retention-plan.v2": ("plan", 2, 3),
    RETENTION_PLAN_SCHEMA: ("plan", 3, 3),
    "giga.archaeologist.retention-run.v1": ("run", 1, 2),
    RETENTION_RUN_SCHEMA: ("run", 2, 2),
    RETENTION_POINTER_SCHEMA: ("pointer", 1, 1),
    RETENTION_INTENT_SCHEMA: ("quarantine_intent", 1, 1),
    RETENTION_OUTCOME_SCHEMA: ("quarantine_outcome", 1, 1),
    RETENTION_PURGE_SCHEMA: ("purge_outcome", 1, 1),
    RETENTION_COMPACTION_SCHEMA: ("compaction", 1, 1),
}
_SAFE_RETENTION_SCALAR_FIELDS = (
    "status",
    "mode",
    "run_id",
    "batch_id",
    "generated_at",
    "finished_at",
    "updated_at",
    "created_at",
    "compacted_at",
    "purged_at",
    "plan_status",
    "candidate_generations",
    "candidate_bytes",
    "compaction_candidate_generations",
    "compaction_candidate_bytes",
    "storage_quota_satisfied_after_plan",
    "reference_scan_complete",
    "repository_cleanup_authority",
)
_SAFE_RETENTION_COLLECTION_FIELDS = (
    "stores",
    "reference_roots",
    "reference_failures",
    "quarantine",
    "purges",
    "compactions",
    "recovered_quarantines",
    "candidates",
    "generations",
    "deleted",
    "preserved_failure_receipts",
)
_POINTER_SCHEMAS = {
    "inventory": INVENTORY_POINTER_SCHEMA,
    "mapper": MAPPER_POINTER_SCHEMA,
    "semantic": SEMANTIC_POINTER_SCHEMA,
    "scip": SCIP_STORE_CURRENT_SCHEMA,
}
_DERIVED_POINTER_KINDS = {
    INVENTORY_POINTER_SCHEMA: "inventory",
    MAPPER_POINTER_SCHEMA: "mapper",
    SEMANTIC_POINTER_SCHEMA: "semantic",
    SCIP_STORE_CURRENT_SCHEMA: "scip",
}
_NON_PAYLOAD_POINTER_KINDS = {
    "giga.navigation.maintenance-current.v1": "maintenance",
    RETENTION_POINTER_SCHEMA: "retention",
}
_DERIVED_MANIFEST_NAMES = {
    "inventory": "manifest.json",
    "mapper": "manifest.json",
    "semantic": "manifest.json",
    "scip": "catalog.json",
}


class RetentionError(ValueError):
    """A retention plan or mutation could not be proved safe."""


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], *, label: str
) -> None:
    if set(value) != expected:
        raise RetentionError(f"{label} has an unexpected field set")


@dataclass(frozen=True)
class RetentionPolicy:
    """Bounded storage policy; bytes are physical payload sizes, not claims."""

    keep_successes: int = 3
    keep_failures: int = 2
    min_age_seconds: int = 24 * 60 * 60
    quarantine_grace_seconds: int = 7 * 24 * 60 * 60
    inventory_max_bytes: int = 256 * 1024 * 1024
    mapper_max_bytes: int = 2 * 1024 * 1024 * 1024
    semantic_max_bytes: int = 2 * 1024 * 1024 * 1024
    scip_max_bytes: int = 1024 * 1024 * 1024
    failure_max_bytes: int = 512 * 1024 * 1024

    def validate(self) -> None:
        values = {
            "keep_successes": self.keep_successes,
            "keep_failures": self.keep_failures,
            "min_age_seconds": self.min_age_seconds,
            "quarantine_grace_seconds": self.quarantine_grace_seconds,
            "inventory_max_bytes": self.inventory_max_bytes,
            "mapper_max_bytes": self.mapper_max_bytes,
            "semantic_max_bytes": self.semantic_max_bytes,
            "scip_max_bytes": self.scip_max_bytes,
            "failure_max_bytes": self.failure_max_bytes,
        }
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in values.values()
        ):
            raise RetentionError("retention policy values must be integers")
        if self.keep_successes < 2 or self.keep_failures < 1:
            raise RetentionError("retention policy must keep recovery generations")
        if any(value < 0 for name, value in values.items() if name.endswith("seconds")):
            raise RetentionError("retention time bounds must be non-negative")
        if any(value <= 0 for name, value in values.items() if name.endswith("bytes")):
            raise RetentionError("retention byte bounds must be positive")


@dataclass(frozen=True)
class _Store:
    kind: str
    root: Path
    runs: Path
    quota: int
    current_run_id: str | None
    current_manifest: Mapping[str, Any] | None


def _utc_now(now: datetime | None = None) -> str:
    value = now or datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _unavailable_location_label(*, purpose: str) -> str:
    """Return a stable generic label without deriving identity from a path."""

    return f"{purpose}:CONTENT_UNAVAILABLE"


def _private_directory(path: Path, *, create: bool = False) -> Path:
    path = path.absolute()
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = path.lstat()
    identity = _unavailable_location_label(purpose="retention-path")
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise RetentionError(
            f"retention path is not a real directory: {identity}"
        )
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise RetentionError(
            f"retention path must be current-UID mode 0700: {identity}"
        )
    return path.resolve(strict=True)


def _safe_run_id(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or PurePosixPath(value).name != value
        or "\x00" in value
    ):
        raise RetentionError("unsafe map generation identifier")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    identity = _unavailable_location_label(purpose="retention-json-input")
    try:
        before = path.lstat()
    except OSError as exc:
        raise RetentionError(f"invalid retention JSON input: {identity}") from exc
    if path.is_symlink() or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise RetentionError(
            f"retention JSON input is not a regular single-link file: {identity}"
        )
    try:
        raw = path.read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        raise RetentionError(f"invalid retention JSON input: {identity}") from exc
    after = path.lstat()
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise RetentionError(f"retention JSON input changed while reading: {identity}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RetentionError(f"invalid retention JSON input: {identity}") from exc
    if not isinstance(value, dict):
        raise RetentionError(f"retention JSON root is not an object: {identity}")
    return value


def _read_retention_receipt_exact(path: Path) -> tuple[dict[str, Any], bytes]:
    """Read one bounded receipt without following links or accepting duplicate keys."""

    path = path.absolute()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    identity = _unavailable_location_label(purpose="retention-receipt-location")
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RetentionError(
            f"cannot open retention receipt safely: {identity}"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > _READ_LIMIT
        ):
            raise RetentionError(
                "retention receipt must be a bounded regular single-link file"
            )
        chunks = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                raise RetentionError("retention receipt ended before its bound size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise RetentionError("retention receipt grew while reading")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    if identity != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise RetentionError("retention receipt changed while reading")
    raw = b"".join(chunks)

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise RetentionError(
                    f"duplicate JSON field in retention receipt: {key}"
                )
            result[key] = value
        return result

    try:
        document = json.loads(raw, object_pairs_hook=reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RetentionError("retention receipt is not strict UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise RetentionError("retention receipt root is not an object")
    return document, raw


def _observed_or_unknown(
    document: Mapping[str, Any], key: str, expected: tuple[type, ...]
) -> dict[str, Any]:
    if key not in document:
        return {"state": "UNKNOWN_MISSING_LEGACY_FIELD", "value": None}
    value = document[key]
    if isinstance(value, bool) and bool not in expected:
        raise RetentionError(f"retention receipt field has invalid type: {key}")
    if not isinstance(value, expected):
        raise RetentionError(f"retention receipt field has invalid type: {key}")
    return {"state": "OBSERVED", "value": value}


def inspect_retention_receipt(
    path: Path, *, expected_raw_sha256: str | None = None
) -> dict[str, Any]:
    """Authenticate and safely normalise current or historical retention evidence.

    The view deliberately excludes stores, generation paths and other payload-bearing
    structures.  It grants no storage-lifecycle authority and never rewrites the input.
    """

    document, raw = _read_retention_receipt_exact(path)
    raw_sha256 = sha256_bytes(raw)
    if expected_raw_sha256 is not None and raw_sha256 != expected_raw_sha256:
        raise RetentionError("retention receipt raw SHA-256 does not match expectation")
    try:
        validate_self_hash(document)
    except ValueError as exc:
        raise RetentionError("retention receipt self-hash mismatch") from exc
    schema = document.get("schema")
    if schema not in _RETENTION_RECEIPT_SCHEMAS:
        raise RetentionError("unsupported retention receipt schema")
    family, version, current_version = _RETENTION_RECEIPT_SCHEMAS[schema]
    receipt_sha256 = document.get("receipt_sha256")
    if (
        not isinstance(receipt_sha256, str)
        or len(receipt_sha256) != 64
        or any(character not in "0123456789abcdef" for character in receipt_sha256)
    ):
        raise RetentionError("retention receipt has an invalid self-hash field")
    scalar_types: dict[str, tuple[type, ...]] = {
        "status": (str,),
        "mode": (str,),
        "run_id": (str,),
        "batch_id": (str,),
        "generated_at": (str,),
        "finished_at": (str,),
        "updated_at": (str,),
        "created_at": (str,),
        "compacted_at": (str,),
        "purged_at": (str,),
        "plan_status": (str,),
        "candidate_generations": (int,),
        "candidate_bytes": (int,),
        "compaction_candidate_generations": (int,),
        "compaction_candidate_bytes": (int,),
        "storage_quota_satisfied_after_plan": (bool,),
        "reference_scan_complete": (bool,),
        "repository_cleanup_authority": (bool,),
    }
    safe_fields = {
        key: _observed_or_unknown(document, key, scalar_types[key])
        for key in _SAFE_RETENTION_SCALAR_FIELDS
    }
    collection_counts: dict[str, dict[str, Any]] = {}
    for key in _SAFE_RETENTION_COLLECTION_FIELDS:
        if key not in document:
            collection_counts[key] = {
                "state": "UNKNOWN_MISSING_LEGACY_FIELD",
                "count": None,
            }
            continue
        value = document[key]
        if value is None:
            count = 0
        elif isinstance(value, (list, dict)):
            count = len(value)
        else:
            raise RetentionError(
                f"retention receipt collection has invalid type: {key}"
            )
        collection_counts[key] = {"state": "OBSERVED", "count": count}
    hash_links = {}
    for key, value in document.items():
        if key == "receipt_sha256" or not key.endswith("_sha256"):
            continue
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise RetentionError(f"retention receipt hash link is invalid: {key}")
        hash_links[key] = value
    missing_current_fields = []
    if family == "plan" and version < 3:
        missing_current_fields = [
            key
            for key in (
                "compaction_candidate_generations",
                "compaction_candidate_bytes",
            )
            if key not in document
        ]
    elif family == "run" and version < 2:
        missing_current_fields = [
            key
            for key in (
                "compaction_candidate_generations",
                "compaction_candidate_bytes",
                "compactions",
            )
            if key not in document
        ]
    return seal_document(
        {
            "schema": RETENTION_INSPECTION_SCHEMA,
            "status": "PASS_AUTHENTICATED_READ_ONLY_INSPECTION",
            "authority": "retention-evidence-inspection-only",
            "authority_granted": False,
            "cleanup_authority_granted": False,
            "quarantine_authority_granted": False,
            "purge_authority_granted": False,
            "source": {
                "identity": {
                    "purpose": "retention-receipt-content",
                    "algorithm": "content-addressed-retention-receipt-v1",
                    "raw_sha256": raw_sha256,
                    "receipt_sha256": receipt_sha256,
                    "literal_path_disclosed": False,
                    "path_derived_identity_disclosed": False,
                },
                "literal_path_disclosed": False,
                "path_derived_identity_disclosed": False,
                "raw_sha256": raw_sha256,
                "bytes": len(raw),
                "receipt_sha256": receipt_sha256,
                "self_hash_valid": True,
                "historical_bytes_rewritten": False,
            },
            "receipt": {
                "schema": schema,
                "family": family,
                "version": version,
                "current_writer_version": current_version,
                "compatibility": (
                    "CURRENT_NATIVE"
                    if version == current_version
                    else "HISTORICAL_AUTHENTICATED_COMPATIBILITY"
                ),
                "writer_status": (
                    "CURRENT"
                    if version == current_version
                    else "SUPERSEDED_WRITER_COMPATIBLE_READER"
                ),
                "observed_fields": sorted(document),
                "missing_current_generation_fields": missing_current_fields,
                "safe_scalar_fields": safe_fields,
                "safe_collection_counts": collection_counts,
                "hash_links": {key: hash_links[key] for key in sorted(hash_links)},
            },
            "privacy": {
                "raw_payload_included": False,
                "stores_included": False,
                "generation_paths_included": False,
                "reference_roots_included": False,
            },
            "claims": {
                "writer_behavior_replayed": False,
                "historical_payload_copied": False,
                "cleanup_permitted": False,
                "quarantine_permitted": False,
                "purge_permitted": False,
                "repository_cleanup_permitted": False,
            },
        }
    )


def render_retention_receipt_inspection(inspection: Mapping[str, Any]) -> str:
    source = inspection["source"]
    receipt = inspection["receipt"]
    missing = receipt["missing_current_generation_fields"]
    lines = [
        "Retention receipt: authenticated read-only view",
        f"Schema: {receipt['schema']}",
        f"Family/version: {receipt['family']} v{receipt['version']} (current writer v{receipt['current_writer_version']})",
        f"Compatibility: {receipt['compatibility']}",
        "Source identity: "
        f"retention-receipt-content:{source['identity']['receipt_sha256']}",
        f"Raw identity: {source['raw_sha256']} ({source['bytes']} bytes)",
        f"Receipt identity: {source['receipt_sha256']}",
        "Historical bytes rewritten: no",
        "Cleanup/quarantine/purge authority: none",
        "Missing current-generation fields: "
        + (", ".join(missing) if missing else "none"),
    ]
    return "\n".join(lines)


def _file_hash(path: Path) -> tuple[str, int]:
    metadata = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
    ):
        identity = _unavailable_location_label(purpose="retention-artifact")
        raise RetentionError(
            "retention artifact must be a regular single-link file: "
            f"{identity}"
        )
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    after = path.lstat()
    if (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        identity = _unavailable_location_label(purpose="retention-artifact")
        raise RetentionError(
            f"retention artifact changed while hashing: {identity}"
        )
    return digest.hexdigest(), size


def _database_binding(
    kind: str, run: Path, manifest: Mapping[str, Any]
) -> tuple[Path, str, int]:
    artifact = manifest.get("database")
    if not isinstance(artifact, Mapping):
        raise RetentionError(f"{kind} manifest has no database binding")
    relative = artifact.get("path")
    digest = artifact.get("sha256")
    size = artifact.get("bytes")
    if (
        not isinstance(relative, str)
        or PurePosixPath(relative).name != relative
        or not isinstance(digest, str)
        or len(digest) != 64
        or isinstance(size, bool)
        or not isinstance(size, int)
        or size < 0
    ):
        raise RetentionError(f"{kind} database binding is invalid")
    return run / relative, digest, size


def _validate_compaction_receipt(
    kind: str, run: Path, manifest: Mapping[str, Any]
) -> dict[str, Any] | None:
    receipt_path = run / "compaction.json"
    if not receipt_path.exists() and not receipt_path.is_symlink():
        return None
    receipt = _read_json(receipt_path)
    try:
        validate_self_hash(receipt)
    except ValueError as exc:
        raise RetentionError("compaction receipt self-hash mismatch") from exc
    raw_path, raw_sha256, raw_bytes = _database_binding(kind, run, manifest)
    compressed = receipt.get("compressed")
    source = receipt.get("source")
    manifest_binding = receipt.get("manifest")
    if (
        receipt.get("schema") != RETENTION_COMPACTION_SCHEMA
        or receipt.get("status") != "COMPRESSED"
        or receipt.get("kind") != kind
        or receipt.get("run_id") != run.name
        or not isinstance(source, Mapping)
        or source
        != {
            "path": raw_path.name,
            "sha256": raw_sha256,
            "bytes": raw_bytes,
            "mode": 0o600,
        }
        or not isinstance(compressed, Mapping)
        or compressed.get("path") != f"{raw_path.name}.gz"
        or compressed.get("algorithm") != "gzip-9-mtime-zero"
        or not isinstance(compressed.get("sha256"), str)
        or len(compressed["sha256"]) != 64
        or isinstance(compressed.get("bytes"), bool)
        or not isinstance(compressed.get("bytes"), int)
        or compressed["bytes"] <= 0
        or not isinstance(manifest_binding, Mapping)
        or manifest_binding.get("path") != "manifest.json"
        or manifest_binding.get("receipt_sha256") != manifest.get("receipt_sha256")
    ):
        raise RetentionError("compaction receipt does not bind the generation")
    manifest_digest, manifest_size = _file_hash(run / "manifest.json")
    if manifest_binding != {
        "path": "manifest.json",
        "sha256": manifest_digest,
        "bytes": manifest_size,
        "receipt_sha256": manifest.get("receipt_sha256"),
    }:
        raise RetentionError("compaction manifest binding mismatch")
    compressed_path = run / compressed["path"]
    digest, size = _file_hash(compressed_path)
    if digest != compressed["sha256"] or size != compressed["bytes"]:
        raise RetentionError("compressed database binding mismatch")
    return receipt


def _database_storage_state(
    kind: str, run: Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    raw_path, raw_sha256, raw_bytes = _database_binding(kind, run, manifest)
    compressed_path = run / f"{raw_path.name}.gz"
    raw_exists = raw_path.exists() or raw_path.is_symlink()
    compressed_exists = compressed_path.exists() or compressed_path.is_symlink()
    receipt = _validate_compaction_receipt(kind, run, manifest)
    if raw_exists:
        metadata = raw_path.lstat()
        if (
            raw_path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise RetentionError("raw map database is not a private regular file")
        digest, size = _file_hash(raw_path)
        if digest != raw_sha256 or size != raw_bytes:
            raise RetentionError("raw map database binding mismatch")
    elif receipt is None:
        raise RetentionError("map generation has neither raw nor restorable database")
    if compressed_exists and receipt is None and not raw_exists:
        raise RetentionError("compressed map database has no authenticated receipt")
    return {
        "path": raw_path.name,
        "raw_sha256": raw_sha256,
        "raw_bytes": raw_bytes,
        "raw_present": raw_exists,
        "compressed_present": compressed_exists,
        "compaction_receipt_sha256": None
        if receipt is None
        else receipt["receipt_sha256"],
        "compressed_path": None if receipt is None else receipt["compressed"]["path"],
        "compressed_sha256": None if receipt is None else receipt["compressed"]["sha256"],
        "compressed_bytes": None if receipt is None else receipt["compressed"]["bytes"],
    }


def _tree_record(path: Path) -> dict[str, Any]:
    root = _private_directory(path)
    rows: list[dict[str, Any]] = []
    total = 0
    for candidate in sorted(root.rglob("*")):
        relative = candidate.relative_to(root).as_posix()
        metadata = candidate.lstat()
        identity = _unavailable_location_label(purpose="retention-artifact")
        if candidate.is_symlink():
            raise RetentionError(
                f"retention generation contains a symlink: {identity}"
            )
        if stat.S_ISDIR(metadata.st_mode):
            if metadata.st_uid != os.getuid():
                raise RetentionError(
                    f"retention directory has a foreign owner: {identity}"
                )
            rows.append(
                {
                    "path": relative,
                    "kind": "directory",
                    "mode": stat.S_IMODE(metadata.st_mode),
                }
            )
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise RetentionError(f"unsupported retention artifact: {identity}")
        digest, size = _file_hash(candidate)
        total += size
        rows.append(
            {
                "path": relative,
                "kind": "file",
                "mode": stat.S_IMODE(metadata.st_mode),
                "bytes": size,
                "sha256": digest,
            }
        )
    return {
        "bytes": total,
        "entries": len(rows),
        "tree_sha256": sha256_bytes(canonical_bytes(rows)),
    }


def _tree_size(path: Path) -> tuple[int, int]:
    """Validate a generation's shape and count bytes without reading payloads."""

    root = _private_directory(path)
    total = 0
    entries = 0
    for candidate in sorted(root.rglob("*")):
        entries += 1
        metadata = candidate.lstat()
        identity = _unavailable_location_label(purpose="retention-artifact")
        if candidate.is_symlink():
            raise RetentionError(
                f"retention generation contains a symlink: {identity}"
            )
        if stat.S_ISDIR(metadata.st_mode):
            if metadata.st_uid != os.getuid():
                raise RetentionError(
                    f"retention directory has a foreign owner: {identity}"
                )
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise RetentionError(f"unsupported retention artifact: {identity}")
        total += metadata.st_size
    return total, entries


def _validate_current_artifacts(
    kind: str, run: Path, manifest: Mapping[str, Any]
) -> None:
    if manifest.get("run_id") != run.name:
        raise RetentionError(f"{kind} current manifest has the wrong run identity")
    if kind in {"inventory", "mapper"}:
        artifact = manifest.get("database")
        if not isinstance(artifact, Mapping):
            raise RetentionError(f"{kind} current manifest has no database binding")
        path = artifact.get("path")
        if not isinstance(path, str) or PurePosixPath(path).name != path:
            raise RetentionError(f"{kind} current database path is unsafe")
        digest, size = _file_hash(run / path)
        if digest != artifact.get("sha256") or size != artifact.get("bytes"):
            raise RetentionError(f"{kind} current database binding mismatch")
    elif kind == "semantic":
        graph = manifest.get("graph")
        if not isinstance(graph, Mapping):
            raise RetentionError("semantic current manifest has no graph binding")
        for path_key, hash_key, bytes_key in (
            ("path", "sha256", "bytes"),
            ("raw_path", "raw_sha256", "raw_bytes"),
        ):
            relative = graph.get(path_key)
            if not isinstance(relative, str):
                raise RetentionError("semantic graph path is unsafe")
            pure = PurePosixPath(relative)
            if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != relative:
                raise RetentionError("semantic graph path is unsafe")
            digest, size = _file_hash(run / relative)
            if digest != graph.get(hash_key) or size != graph.get(bytes_key):
                raise RetentionError("semantic current graph binding mismatch")


def _load_store(kind: str, path: Path, quota: int) -> _Store | None:
    if not path.exists():
        return None
    root = _private_directory(path)
    runs = root / "runs"
    if not runs.exists():
        return None
    runs = _private_directory(runs)
    if kind == "scip":
        try:
            current = current_scip_store(root)
        except ScipMapError as exc:
            raise RetentionError("scip CURRENT generation is invalid") from exc
        return _Store(
            kind,
            root,
            runs,
            quota,
            current.catalog["run_id"],
            current.catalog,
        )
    pointer_path = root / "CURRENT.json"
    if not pointer_path.is_file():
        raise RetentionError(f"{kind} store has runs but no CURRENT pointer")
    pointer = _read_json(pointer_path)
    try:
        validate_self_hash(pointer)
    except ValueError as exc:
        raise RetentionError(f"{kind} CURRENT pointer self-hash mismatch") from exc
    if pointer.get("schema") != _POINTER_SCHEMAS[kind]:
        raise RetentionError(f"{kind} CURRENT pointer schema mismatch")
    run_id = _safe_run_id(pointer.get("run_id"))
    run = _private_directory(runs / run_id)
    manifest_path = run / "manifest.json"
    manifest_raw = manifest_path.read_bytes()
    if sha256_bytes(manifest_raw) != pointer.get("manifest_file_sha256"):
        raise RetentionError(f"{kind} CURRENT manifest hash mismatch")
    manifest = _read_json(manifest_path)
    try:
        validate_self_hash(manifest)
    except ValueError as exc:
        raise RetentionError(f"{kind} current manifest self-hash mismatch") from exc
    if manifest.get("receipt_sha256") != pointer.get("manifest_receipt_sha256"):
        raise RetentionError(f"{kind} CURRENT receipt binding mismatch")
    _validate_current_artifacts(kind, run, manifest)
    return _Store(kind, root, runs, quota, run_id, manifest)


def _sqlite_integrity(path: Path) -> None:
    try:
        connection = sqlite3.connect(
            f"file:{path}?mode=ro&immutable=1", uri=True, timeout=1.0
        )
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise RetentionError("recovered mapper database is not valid SQLite") from exc
    if result != ("ok",):
        raise RetentionError("recovered mapper database failed integrity_check")


def _validate_current_mapper_compaction_receipt(
    run: Path,
    *,
    run_id: str,
    manifest: Mapping[str, Any],
    manifest_raw: bytes,
) -> tuple[dict[str, Any], Path, Path]:
    receipt = _read_json(run / "compaction.json")
    _require_exact_keys(
        receipt,
        {
            "schema",
            "status",
            "kind",
            "run_id",
            "compacted_at",
            "source",
            "compressed",
            "manifest",
            "repository_cleanup_authority",
            "receipt_sha256",
        },
        label="compaction receipt",
    )
    try:
        validate_self_hash(receipt)
    except ValueError as exc:
        raise RetentionError("compaction receipt self-hash mismatch") from exc
    if (
        receipt["schema"] != RETENTION_COMPACTION_SCHEMA
        or receipt["status"] != "COMPRESSED"
        or receipt["kind"] != "mapper"
        or receipt["run_id"] != run_id
        or receipt["repository_cleanup_authority"] is not False
        or not isinstance(receipt["compacted_at"], str)
    ):
        raise RetentionError("compaction receipt authority or identity mismatch")

    source = receipt["source"]
    compressed = receipt["compressed"]
    manifest_binding = receipt["manifest"]
    if not all(
        isinstance(item, Mapping) for item in (source, compressed, manifest_binding)
    ):
        raise RetentionError("compaction receipt artifact binding is malformed")
    _require_exact_keys(
        source, {"path", "sha256", "bytes", "mode"}, label="compaction source"
    )
    _require_exact_keys(
        compressed,
        {"algorithm", "path", "sha256", "bytes"},
        label="compressed artifact",
    )
    _require_exact_keys(
        manifest_binding,
        {"path", "sha256", "bytes", "receipt_sha256"},
        label="compaction manifest binding",
    )
    database = manifest.get("database")
    if not isinstance(database, Mapping):
        raise RetentionError("current mapper manifest has no database binding")
    if (
        source.get("path") != "facts.sqlite3"
        or source.get("path") != database.get("path")
        or source.get("sha256") != database.get("sha256")
        or source.get("bytes") != database.get("bytes")
        or source.get("mode") != 0o600
    ):
        raise RetentionError("compaction source does not bind the current manifest")
    if (
        compressed.get("algorithm") != "gzip-9-mtime-zero"
        or compressed.get("path") != "facts.sqlite3.gz"
    ):
        raise RetentionError("unsupported compaction artifact")
    if (
        manifest_binding.get("path") != "manifest.json"
        or manifest_binding.get("sha256") != sha256_bytes(manifest_raw)
        or manifest_binding.get("bytes") != len(manifest_raw)
        or manifest_binding.get("receipt_sha256") != manifest.get("receipt_sha256")
    ):
        raise RetentionError("compaction manifest binding mismatch")
    for value, label in (
        (source.get("bytes"), "source bytes"),
        (compressed.get("bytes"), "compressed bytes"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise RetentionError(f"invalid compaction {label}")
    for value, label in (
        (source.get("sha256"), "source hash"),
        (compressed.get("sha256"), "compressed hash"),
    ):
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise RetentionError(f"invalid compaction {label}")

    archive = run / compressed["path"]
    try:
        metadata = archive.lstat()
    except OSError as exc:
        raise RetentionError("compressed mapper database is missing") from exc
    if (
        archive.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise RetentionError("compressed mapper database is not a private stable file")
    archive_hash, archive_bytes = _file_hash(archive)
    if archive_hash != compressed["sha256"] or archive_bytes != compressed["bytes"]:
        raise RetentionError("compressed mapper database binding mismatch")
    return receipt, run / source["path"], archive


def recover_current_compacted_mapper(
    mapper_store: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Explicitly restore one authenticated externally-compacted CURRENT mapper DB.

    The gzip archive and compaction receipt are preserved.  Nothing is recovered
    unless the CURRENT pointer, manifest, compaction receipt, archive and intended
    database identity form one exact chain.
    """

    root = _private_directory(Path(mapper_store))
    runs = _private_directory(root / "runs")
    lock_path = root / "compaction-recovery.lock"
    lock = lock_path.open("a+b")
    os.chmod(lock_path, 0o600)
    try:
        lock_file(lock)
        pointer = _read_json(root / "CURRENT.json")
        pointer_raw = (root / "CURRENT.json").read_bytes()
        if pointer_raw != canonical_bytes(pointer):
            raise RetentionError("mapper CURRENT pointer changed while binding")
        try:
            validate_self_hash(pointer)
        except ValueError as exc:
            raise RetentionError("mapper CURRENT pointer self-hash mismatch") from exc
        if pointer.get("schema") != MAPPER_POINTER_SCHEMA:
            raise RetentionError("mapper CURRENT pointer schema mismatch")
        run_id = _safe_run_id(pointer.get("run_id"))
        run = _private_directory(runs / run_id)
        manifest_path = run / "manifest.json"
        manifest = _read_json(manifest_path)
        manifest_raw = manifest_path.read_bytes()
        if manifest_raw != canonical_bytes(manifest):
            raise RetentionError("mapper current manifest changed while binding")
        if sha256_bytes(manifest_raw) != pointer.get("manifest_file_sha256"):
            raise RetentionError("mapper CURRENT manifest hash mismatch")
        try:
            validate_self_hash(manifest)
        except ValueError as exc:
            raise RetentionError("mapper current manifest self-hash mismatch") from exc
        if (
            manifest.get("receipt_sha256") != pointer.get("manifest_receipt_sha256")
            or manifest.get("run_id") != run_id
        ):
            raise RetentionError("mapper CURRENT receipt or run binding mismatch")
        compaction, destination, archive = _validate_current_mapper_compaction_receipt(
            run, run_id=run_id, manifest=manifest, manifest_raw=manifest_raw
        )
        source = compaction["source"]
        recovery_path = run / "recovery.json"
        if recovery_path.exists() or recovery_path.is_symlink():
            existing = _read_json(recovery_path)
            try:
                validate_self_hash(existing)
            except ValueError as exc:
                raise RetentionError("recovery receipt self-hash mismatch") from exc
            _require_exact_keys(
                existing,
                {
                    "schema",
                    "status",
                    "kind",
                    "run_id",
                    "recovered_at",
                    "current_pointer_sha256",
                    "manifest_sha256",
                    "manifest_receipt_sha256",
                    "compaction_receipt_sha256",
                    "source",
                    "compressed",
                    "archive_preserved",
                    "repository_cleanup_authority",
                    "receipt_sha256",
                },
                label="recovery receipt",
            )
            if (
                existing.get("schema") != RETENTION_RECOVERY_SCHEMA
                or existing.get("status") not in {"RECOVERED", "ALREADY_EXACT"}
                or existing.get("kind") != "mapper"
                or existing.get("run_id") != run_id
                or not isinstance(existing.get("recovered_at"), str)
                or existing.get("current_pointer_sha256") != sha256_bytes(pointer_raw)
                or existing.get("manifest_sha256") != sha256_bytes(manifest_raw)
                or existing.get("manifest_receipt_sha256") != manifest["receipt_sha256"]
                or existing.get("compaction_receipt_sha256")
                != compaction["receipt_sha256"]
                or existing.get("source") != compaction["source"]
                or existing.get("compressed") != compaction["compressed"]
                or existing.get("archive_preserved") is not True
                or existing.get("repository_cleanup_authority") is not False
            ):
                raise RetentionError("recovery receipt binding mismatch")
            if not destination.is_file() or destination.is_symlink():
                raise RetentionError("restored mapper database is missing")
            digest, size = _file_hash(destination)
            if digest != source["sha256"] or size != source["bytes"]:
                raise RetentionError("restored mapper database binding mismatch")
            _sqlite_integrity(destination)
            return existing

        installed = False
        if destination.exists() or destination.is_symlink():
            digest, size = _file_hash(destination)
            if digest != source["sha256"] or size != source["bytes"]:
                raise RetentionError("existing mapper database blocks exact recovery")
            _sqlite_integrity(destination)
        else:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".facts-recovery-", dir=run
            )
            temporary = Path(temporary_name)
            try:
                os.fchmod(descriptor, 0o600)
                digest = hashlib.sha256()
                written = 0
                with os.fdopen(descriptor, "wb", closefd=True) as target:
                    descriptor = -1
                    try:
                        with gzip.open(archive, "rb") as source_stream:
                            while chunk := source_stream.read(1024 * 1024):
                                written += len(chunk)
                                if written > source["bytes"]:
                                    raise RetentionError(
                                        "decompressed mapper database exceeds binding"
                                    )
                                digest.update(chunk)
                                target.write(chunk)
                    except (OSError, EOFError) as exc:
                        raise RetentionError(
                            "compressed mapper database is invalid"
                        ) from exc
                    target.flush()
                    os.fsync(target.fileno())
                if written != source["bytes"] or digest.hexdigest() != source["sha256"]:
                    raise RetentionError(
                        "decompressed mapper database binding mismatch"
                    )
                _sqlite_integrity(temporary)
                try:
                    os.link(temporary, destination, follow_symlinks=False)
                except FileExistsError as exc:
                    raise RetentionError(
                        "mapper database appeared during exact recovery"
                    ) from exc
                temporary.unlink()
                directory = os.open(run, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
                installed = True
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
                temporary.unlink(missing_ok=True)

        _validate_current_artifacts("mapper", run, manifest)
        receipt = seal_document(
            {
                "schema": RETENTION_RECOVERY_SCHEMA,
                "status": "RECOVERED" if installed else "ALREADY_EXACT",
                "kind": "mapper",
                "run_id": run_id,
                "recovered_at": _utc_now(now),
                "current_pointer_sha256": sha256_bytes(pointer_raw),
                "manifest_sha256": sha256_bytes(manifest_raw),
                "manifest_receipt_sha256": manifest["receipt_sha256"],
                "compaction_receipt_sha256": compaction["receipt_sha256"],
                "source": dict(source),
                "compressed": dict(compaction["compressed"]),
                "archive_preserved": True,
                "repository_cleanup_authority": False,
            }
        )
        _write_create_once(recovery_path, receipt)
        return receipt
    finally:
        lock.close()


def _load_failures(path: Path, quota: int) -> _Store | None:
    if not path.exists():
        return None
    root = _private_directory(path.parent)
    failures = _private_directory(path)
    return _Store("semantic_failure", root, failures, quota, None, None)


def _run_finished_at(run_id: str, manifest: Mapping[str, Any] | None) -> datetime:
    candidates: list[Any] = []
    if manifest is not None:
        scan = manifest.get("scan")
        if isinstance(scan, Mapping):
            candidates.extend(
                (scan.get("finished_at"), scan.get("failed_at"), scan.get("started_at"))
            )
        candidates.extend(
            (
                manifest.get("finished_at"),
                manifest.get("failed_at"),
                manifest.get("started_at"),
            )
        )
    for value in candidates:
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed.astimezone(UTC)
            except ValueError:
                pass
    prefix = run_id.rsplit("-", 1)[0]
    try:
        return datetime.strptime(prefix, _RUN_ID_FORMAT).replace(tzinfo=UTC)
    except ValueError as exc:
        raise RetentionError(f"run has no trustworthy timestamp: {run_id}") from exc


def _iter_generation_records(store: _Store) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(store.runs.iterdir()):
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            identity = _unavailable_location_label(purpose="retention-generation")
            raise RetentionError(
                f"unsafe generation path in {store.kind}: {identity}"
            )
        run_id = _safe_run_id(path.name)
        manifest_path = path / (
            "failure.json"
            if store.kind == "semantic_failure"
            else "catalog.json"
            if store.kind == "scip"
            else "manifest.json"
        )
        manifest: dict[str, Any] | None = None
        if manifest_path.is_file():
            manifest = _read_json(manifest_path)
            try:
                validate_self_hash(manifest)
            except ValueError as exc:
                identity = _unavailable_location_label(
                    purpose="retention-generation"
                )
                raise RetentionError(
                    f"generation evidence self-hash mismatch: {identity}"
                ) from exc
        elif store.kind != "semantic_failure":
            identity = _unavailable_location_label(purpose="retention-generation")
            raise RetentionError(f"generation has no manifest: {identity}")
        database_storage = None
        semantic_storage = None
        scip_storage = None
        if store.kind in {"inventory", "mapper"}:
            if manifest is None:
                raise RetentionError(f"{store.kind} generation has no manifest")
            database_storage = _database_storage_state(store.kind, path, manifest)
        elif store.kind == "semantic":
            if manifest is None:
                raise RetentionError("semantic generation has no manifest")
            semantic_storage = _semantic_storage_state(path, manifest)
        elif store.kind == "scip":
            if manifest is None:
                raise RetentionError("SCIP generation has no catalog")
            scip_storage = _scip_storage_state(path, manifest)
        total, entries = _tree_size(path)
        records.append(
            {
                "kind": store.kind,
                "run_id": run_id,
                "path": str(path),
                "finished_at": _utc_now(_run_finished_at(run_id, manifest)),
                "bytes": total,
                "entries": entries,
                "tree_sha256": None,
                "manifest_receipt_sha256": None
                if manifest is None
                else manifest.get("receipt_sha256"),
                "database_storage": database_storage,
                "semantic_storage": semantic_storage,
                "scip_storage": scip_storage,
            }
        )
    return records


def _external_references(
    run_ids: Iterable[str], reference_roots: Sequence[Path]
) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    needles = {run_id: run_id.encode("ascii") for run_id in run_ids}
    found = {run_id: [] for run_id in needles}
    failures: list[dict[str, str]] = []
    for supplied in reference_roots:
        path = supplied.absolute()
        if not path.exists() and not path.is_symlink():
            continue
        try:
            supplied_metadata = path.lstat()
        except OSError as exc:
            failures.append(
                {"path": str(path), "reason": f"reference-root:{type(exc).__name__}"}
            )
            continue
        if path.is_symlink() or not (
            stat.S_ISREG(supplied_metadata.st_mode)
            or stat.S_ISDIR(supplied_metadata.st_mode)
        ):
            failures.append({"path": str(path), "reason": "unsafe-reference-root"})
            continue
        candidates = [path] if path.is_file() else sorted(path.rglob("*"))
        for candidate in candidates:
            try:
                metadata = candidate.lstat()
                if candidate.is_symlink():
                    failures.append(
                        {"path": str(candidate), "reason": "symlink-reference-input"}
                    )
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    continue
                if metadata.st_size > _READ_LIMIT:
                    failures.append(
                        {"path": str(candidate), "reason": "reference-input-too-large"}
                    )
                    continue
                raw = candidate.read_bytes()
                after = candidate.lstat()
                if (
                    metadata.st_dev,
                    metadata.st_ino,
                    metadata.st_size,
                    metadata.st_mtime_ns,
                ) != (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                ):
                    failures.append(
                        {"path": str(candidate), "reason": "reference-input-drift"}
                    )
                    continue
                for run_id, needle in needles.items():
                    if needle in raw:
                        found[run_id].append(str(candidate))
            except OSError as exc:
                failures.append(
                    {
                        "path": str(candidate),
                        "reason": f"reference-read:{type(exc).__name__}",
                    }
                )
    return ({key: sorted(value) for key, value in found.items() if value}, failures)


def _known_manifest_references(stores: Sequence[_Store]) -> dict[str, set[str]]:
    references: dict[str, set[str]] = {}
    for store in stores:
        if store.current_run_id is None or store.current_manifest is None:
            continue
        references.setdefault(store.current_run_id, set()).add(f"{store.kind}:CURRENT")
        manifest = store.current_manifest
        scan = manifest.get("scan")
        if isinstance(scan, Mapping) and isinstance(scan.get("incremental_from"), str):
            references.setdefault(scan["incremental_from"], set()).add(
                f"{store.kind}:current.incremental_from"
            )
        inventory = manifest.get("inventory")
        if isinstance(inventory, Mapping) and isinstance(inventory.get("run_id"), str):
            references.setdefault(inventory["run_id"], set()).add(
                f"{store.kind}:current.inventory"
            )
    return references


def plan_navigation_retention(
    inventory_store: Path,
    mapper_store: Path | None,
    semantic_store: Path,
    *,
    scip_store: Path | None = None,
    reference_roots: Sequence[Path] = (),
    policy: RetentionPolicy | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return a sealed, non-authorizing retention plan without changing a store."""

    policy = policy or RetentionPolicy()
    policy.validate()
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    stores = [
        _load_store("inventory", Path(inventory_store), policy.inventory_max_bytes),
        None
        if mapper_store is None
        else _load_store("mapper", Path(mapper_store), policy.mapper_max_bytes),
        None
        if scip_store is None
        else _load_store("scip", Path(scip_store), policy.scip_max_bytes),
        _load_store("semantic", Path(semantic_store), policy.semantic_max_bytes),
        _load_failures(Path(semantic_store) / "failures", policy.failure_max_bytes),
    ]
    active = [item for item in stores if item is not None]
    records_by_store = {store.kind: _iter_generation_records(store) for store in active}
    all_ids = [
        record["run_id"] for records in records_by_store.values() for record in records
    ]
    if len(all_ids) != len(set(all_ids)):
        raise RetentionError(
            "generation identifiers are not globally unique across stores"
        )
    protected = _known_manifest_references(active)
    external, reference_failures = _external_references(all_ids, reference_roots)
    for run_id, paths in external.items():
        protected.setdefault(run_id, set()).update(f"external:{path}" for path in paths)

    store_plans: list[dict[str, Any]] = []
    candidate_count = candidate_bytes = 0
    compaction_candidate_count = compaction_candidate_bytes = 0
    for store in active:
        records = records_by_store[store.kind]
        total = sum(item["bytes"] for item in records)
        keep = (
            policy.keep_failures
            if store.kind == "semantic_failure"
            else policy.keep_successes
        )
        ordered = sorted(
            records,
            key=lambda item: (item["finished_at"], item["run_id"]),
            reverse=True,
        )
        generation_rank = {
            item["run_id"]: rank for rank, item in enumerate(ordered, start=1)
        }
        newest = {item["run_id"] for item in ordered[:keep]}
        eligible: list[dict[str, Any]] = []
        annotated: list[dict[str, Any]] = []
        for item in records:
            protection_reasons = set(protected.get(item["run_id"], set()))
            reasons = set(protection_reasons)
            inside_generation_window = item["run_id"] in newest
            if inside_generation_window:
                reasons.add("recent-recovery-window")
            age = max(
                0,
                int(
                    (
                        current_time
                        - datetime.fromisoformat(
                            item["finished_at"].replace("Z", "+00:00")
                        )
                    ).total_seconds()
                ),
            )
            stale_by_age = age >= policy.min_age_seconds
            stale_by_generation = not inside_generation_window
            if age < policy.min_age_seconds:
                reasons.add("minimum-age-window")
            elif store.kind != "semantic_failure":
                reasons.add("age-window-expired")
            if stale_by_generation and store.kind != "semantic_failure":
                reasons.add("outside-success-generation-window")
            disposition = "RETAIN"
            if store.kind == "semantic_failure":
                candidate = not reasons and total > store.quota
            else:
                # Successful map generations are stale on either boundary. The
                # byte quota is observed evidence, never a reason to retain an
                # otherwise stale, unprotected generation.
                candidate = (
                    stale_by_age or stale_by_generation
                ) and not protection_reasons
            if candidate and not reference_failures:
                disposition = "QUARANTINE_CANDIDATE"
                eligible.append(item)
            database_storage = item.get("database_storage")
            non_external_protection_reasons = {
                reason
                for reason in protection_reasons
                if not reason.startswith("external:")
            }
            compaction_disposition = "NOT_APPLICABLE"
            if isinstance(database_storage, Mapping):
                if not database_storage["raw_present"]:
                    compaction_disposition = "ALREADY_COMPACTED"
                elif database_storage["compressed_present"]:
                    compaction_disposition = "FINISH_INTERRUPTED_COMPACTION"
                elif (
                    disposition == "RETAIN"
                    and stale_by_generation
                    and bool(external.get(item["run_id"]))
                    and not non_external_protection_reasons
                    and not reference_failures
                ):
                    compaction_disposition = "COMPACT_CANDIDATE"
                else:
                    compaction_disposition = "RETAIN_RAW"
            annotated.append(
                {
                    **item,
                    "age_seconds": age,
                    "generation_rank": generation_rank[item["run_id"]],
                    "stale_by_age": stale_by_age,
                    "stale_by_generation": stale_by_generation,
                    "disposition": disposition,
                    "reasons": sorted(reasons),
                    "external_references": external.get(item["run_id"], []),
                    "compaction_disposition": compaction_disposition,
                }
            )
            if compaction_disposition in {
                "COMPACT_CANDIDATE",
                "FINISH_INTERRUPTED_COMPACTION",
            }:
                compaction_candidate_count += 1
                compaction_candidate_bytes += database_storage["raw_bytes"]
        selected: set[str] = set()
        remaining = total
        ordered_eligible = sorted(
            eligible, key=lambda value: (value["finished_at"], value["run_id"])
        )
        for item in ordered_eligible:
            if store.kind == "semantic_failure" and remaining <= store.quota:
                break
            selected.add(item["run_id"])
            remaining -= item["bytes"]
        for item in annotated:
            if (
                item["disposition"] == "QUARANTINE_CANDIDATE"
                and item["run_id"] not in selected
            ):
                item["disposition"] = "RETAIN_QUOTA_SATISFIED"
            elif item["run_id"] in selected:
                tree = _tree_record(Path(item["path"]))
                if tree["bytes"] != item["bytes"] or tree["entries"] != item["entries"]:
                    raise RetentionError("candidate generation changed during planning")
                item["tree_sha256"] = tree["tree_sha256"]
                candidate_count += 1
                candidate_bytes += item["bytes"]
        store_plans.append(
            {
                "kind": store.kind,
                "root": str(store.root),
                "runs_path": str(store.runs),
                "quota_bytes": store.quota,
                "total_bytes": total,
                "projected_bytes_after_quarantine": remaining,
                "quota_satisfied_after_plan": remaining <= store.quota,
                "current_run_id": store.current_run_id,
                "generations": annotated,
            }
        )
    quota_satisfied = all(item["quota_satisfied_after_plan"] for item in store_plans)
    status = (
        "PARTIAL_NO_ACTION"
        if reference_failures
        else "MIXED_CANDIDATES"
        if candidate_count and compaction_candidate_count
        else "QUARANTINE_CANDIDATES"
        if candidate_count
        else "COMPACTION_CANDIDATES"
        if compaction_candidate_count
        else "OVER_QUOTA_PROTECTED"
        if not quota_satisfied
        else "NO_ACTION"
    )
    return seal_document(
        {
            "schema": RETENTION_PLAN_SCHEMA,
            "status": status,
            "authority": "map-generation-storage-lifecycle-only",
            "repository_cleanup_authority": False,
            "generated_at": _utc_now(current_time),
            "policy": {
                "keep_successes": policy.keep_successes,
                "keep_failures": policy.keep_failures,
                "min_age_seconds": policy.min_age_seconds,
                "quarantine_grace_seconds": policy.quarantine_grace_seconds,
                "inventory_max_bytes": policy.inventory_max_bytes,
                "mapper_max_bytes": policy.mapper_max_bytes,
                "semantic_max_bytes": policy.semantic_max_bytes,
                "scip_max_bytes": policy.scip_max_bytes,
                "failure_max_bytes": policy.failure_max_bytes,
            },
            "reference_roots": [str(path.absolute()) for path in reference_roots],
            "reference_scan_complete": not reference_failures,
            "reference_failures": reference_failures,
            "candidate_generations": candidate_count,
            "candidate_bytes": candidate_bytes,
            "compaction_candidate_generations": compaction_candidate_count,
            "compaction_candidate_bytes": compaction_candidate_bytes,
            "storage_quota_satisfied_after_plan": quota_satisfied,
            "stores": store_plans,
        }
    )


def _safe_artifact_path(run: Path, relative: Any, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise RetentionError(f"{label} path is invalid")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != relative:
        raise RetentionError(f"{label} path is unsafe")
    candidate = run.joinpath(*pure.parts)
    try:
        candidate.relative_to(run)
    except ValueError as exc:
        raise RetentionError(f"{label} path escapes its generation") from exc
    return candidate


def _bound_artifact(
    run: Path,
    *,
    relative: Any,
    digest: Any,
    size: Any,
    artifact_class: str,
    role: str,
    bound_by: str,
) -> dict[str, Any]:
    path = _safe_artifact_path(run, relative, label=role)
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or isinstance(size, bool)
        or not isinstance(size, int)
        or size < 0
    ):
        raise RetentionError(f"{role} binding is invalid")
    observed_digest, observed_size = _file_hash(path)
    if observed_digest != digest or observed_size != size:
        raise RetentionError(f"{role} artifact binding mismatch")
    return {
        "path": path.relative_to(run).as_posix(),
        "artifact_class": artifact_class,
        "role": role,
        "sha256": digest,
        "bytes": size,
        "bound_by": bound_by,
    }


def _semantic_manifest_artifact_specs(
    manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    graph = manifest.get("graph")
    if not isinstance(graph, Mapping):
        raise RetentionError("semantic generation has no graph binding")
    return [
        {
            "relative": graph.get("path"),
            "digest": graph.get("sha256"),
            "size": graph.get("bytes"),
            "artifact_class": "CONTENT_ADDRESSED_JSON_OUTPUT",
            "role": "normalized-semantic-graph",
            "bound_by": "manifest.json:graph",
        },
        {
            "relative": graph.get("raw_path"),
            "digest": graph.get("raw_sha256"),
            "size": graph.get("raw_bytes"),
            "artifact_class": "CONTENT_ADDRESSED_JSON_OUTPUT",
            "role": "raw-semantic-graph",
            "bound_by": "manifest.json:graph",
        },
    ]


def _semantic_artifacts(
    run: Path, manifest: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [
        _bound_artifact(
            run,
            relative=spec["relative"],
            digest=spec["digest"],
            size=spec["size"],
            artifact_class=spec["artifact_class"],
            role=spec["role"],
            bound_by=spec["bound_by"],
        )
        for spec in _semantic_manifest_artifact_specs(manifest)
    ]


def _scip_expected_sources(
    run: Path, catalog: Mapping[str, Any], *, verify_raw: bool
) -> tuple[list[dict[str, Any]], list[str]]:
    indexes = catalog.get("indexes")
    if not isinstance(indexes, list):
        raise RetentionError("SCIP generation has no index catalog")
    artifacts: list[dict[str, Any]] = []
    preserved_manifests: list[str] = []
    seen_projects: set[str] = set()
    for item in indexes:
        if not isinstance(item, Mapping):
            raise RetentionError("SCIP catalog index entry is invalid")
        project_id = item.get("project_id")
        manifest_relative = item.get("manifest_path")
        if not isinstance(project_id, str) or not project_id or project_id in seen_projects:
            raise RetentionError("SCIP catalog project identity is invalid")
        seen_projects.add(project_id)
        manifest_path = _safe_artifact_path(
            run, manifest_relative, label="SCIP project manifest"
        )
        manifest_pure = PurePosixPath(str(manifest_relative))
        if (
            len(manifest_pure.parts) != 3
            or manifest_pure.parts[0] != "projects"
            or manifest_pure.name != "manifest.json"
        ):
            raise RetentionError("SCIP project manifest path is unsafe")
        manifest_digest, manifest_size = _file_hash(manifest_path)
        if (
            manifest_digest != item.get("manifest_file_sha256")
            or not isinstance(item.get("manifest_receipt_sha256"), str)
        ):
            raise RetentionError("SCIP project manifest binding mismatch")
        project_manifest = _read_json(manifest_path)
        try:
            validate_self_hash(project_manifest)
        except ValueError as exc:
            raise RetentionError("SCIP project manifest self-hash mismatch") from exc
        if project_manifest.get("receipt_sha256") != item.get(
            "manifest_receipt_sha256"
        ):
            raise RetentionError("SCIP project manifest receipt mismatch")
        index = project_manifest.get("index")
        if not isinstance(index, Mapping):
            raise RetentionError("SCIP project manifest has no index binding")
        if (
            index.get("sha256") != item.get("index_sha256")
            or index.get("bytes") != item.get("index_bytes")
        ):
            raise RetentionError("SCIP catalog and project index binding differ")
        index_relative = index.get("path")
        if (
            not isinstance(index_relative, str)
            or PurePosixPath(index_relative).name != index_relative
        ):
            raise RetentionError("SCIP index path is unsafe")
        index_path = manifest_path.parent / index_relative
        try:
            relative_index = index_path.relative_to(run).as_posix()
        except ValueError as exc:
            raise RetentionError("SCIP index path escapes its generation") from exc
        digest = index.get("sha256")
        size = index.get("bytes")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size <= 0
        ):
            raise RetentionError("SCIP index source binding is invalid")
        if verify_raw:
            _bound_artifact(
                run,
                relative=relative_index,
                digest=digest,
                size=size,
                artifact_class="CONTENT_ADDRESSED_SCIP_INDEX",
                role=f"scip-index:{project_id}",
                bound_by=str(manifest_relative),
            )
            metadata = index_path.lstat()
            if (
                metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600
            ):
                raise RetentionError("SCIP index is not a private mode-0600 file")
        artifacts.append(
            {
                "path": relative_index,
                "sha256": digest,
                "bytes": size,
                "mode": 0o600,
                "artifact_class": "CONTENT_ADDRESSED_SCIP_INDEX",
                "role": f"scip-index:{project_id}",
                "bound_by": str(manifest_relative),
            }
        )
        preserved_manifests.append(str(manifest_relative))
        if manifest_size <= 0:
            raise RetentionError("SCIP project manifest is empty")
    return sorted(artifacts, key=lambda item: item["path"]), sorted(
        preserved_manifests
    )


def _scip_artifacts(
    run: Path, catalog: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    sources, manifests = _scip_expected_sources(run, catalog, verify_raw=True)
    return [
        {
            key: value
            for key, value in source.items()
            if key != "mode"
        }
        for source in sources
    ], manifests


def _preservation_bindings(
    run: Path, paths: Sequence[str]
) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for relative in sorted(set(paths)):
        path = _safe_artifact_path(run, relative, label="preserved artifact")
        digest, size = _file_hash(path)
        bindings.append({"path": relative, "sha256": digest, "bytes": size})
    return bindings


def _generation_assessment_artifacts(
    kind: str,
    generation: Mapping[str, Any],
    *,
    include_compressed_payloads: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    run = Path(str(generation["path"]))
    manifest_name = "catalog.json" if kind == "scip" else "manifest.json"
    manifest = _read_json(run / manifest_name)
    if manifest.get("receipt_sha256") != generation.get("manifest_receipt_sha256"):
        raise RetentionError(f"{kind} generation manifest receipt drift")
    preserved = [manifest_name]
    report = run / "REPORT.md"
    if report.is_file():
        preserved.append("REPORT.md")
    if kind in {"inventory", "mapper"}:
        storage = generation.get("database_storage")
        if not isinstance(storage, Mapping):
            raise RetentionError(f"{kind} generation has no database storage state")
        role = (
            "navigation-inventory-database"
            if kind == "inventory"
            else "archaeology-mapper-database"
        )
        artifacts: list[dict[str, Any]] = []
        if storage.get("raw_present"):
            artifacts.append(
                _bound_artifact(
                    run,
                    relative=storage.get("path"),
                    digest=storage.get("raw_sha256"),
                    size=storage.get("raw_bytes"),
                    artifact_class="SQLITE_DATABASE",
                    role=role,
                    bound_by="manifest.json:database",
                )
            )
        if storage.get("compressed_present"):
            preserved.append("compaction.json")
            if include_compressed_payloads:
                artifacts.append(
                    _bound_artifact(
                        run,
                        relative=storage.get("compressed_path"),
                        digest=storage.get("compressed_sha256"),
                        size=storage.get("compressed_bytes"),
                        artifact_class="AUTHENTICATED_GZIP_PAYLOAD_ARCHIVE",
                        role=f"{role}:exact-restore-archive",
                        bound_by="compaction.json:compressed",
                    )
                )
        if not artifacts:
            return [], sorted(preserved)
        return sorted(artifacts, key=lambda item: item["path"]), sorted(preserved)
    if kind == "semantic":
        storage = generation.get("semantic_storage")
        if not isinstance(storage, Mapping):
            raise RetentionError("semantic generation has no storage state")
        artifacts = []
        if storage.get("raw_complete"):
            artifacts.extend(_semantic_artifacts(run, manifest))
        elif storage.get("raw_present"):
            raise RetentionError("partial semantic compaction requires explicit recovery")
        if storage.get("compressed_present"):
            preserved.append("semantic-compaction.json")
            if include_compressed_payloads:
                for archive in storage["compressed"]:
                    artifacts.append(
                        _bound_artifact(
                            run,
                            relative=archive.get("path"),
                            digest=archive.get("sha256"),
                            size=archive.get("bytes"),
                            artifact_class="AUTHENTICATED_GZIP_PAYLOAD_ARCHIVE",
                            role="semantic-graph:exact-restore-archive",
                            bound_by="semantic-compaction.json:compressed",
                        )
                    )
    elif kind == "scip":
        storage = generation.get("scip_storage")
        if not isinstance(storage, Mapping):
            raise RetentionError("SCIP generation has no storage state")
        artifacts = []
        if storage.get("raw_complete"):
            artifacts, project_manifests = _scip_artifacts(run, manifest)
        elif storage.get("raw_present"):
            raise RetentionError("partial SCIP compaction requires explicit recovery")
        else:
            _sources, project_manifests = _scip_expected_sources(
                run, manifest, verify_raw=False
            )
        if storage.get("compressed_present"):
            preserved.append("scip-compaction.json")
            if include_compressed_payloads:
                for archive in storage["compressed"]:
                    artifacts.append(
                        _bound_artifact(
                            run,
                            relative=archive.get("path"),
                            digest=archive.get("sha256"),
                            size=archive.get("bytes"),
                            artifact_class="AUTHENTICATED_GZIP_PAYLOAD_ARCHIVE",
                            role="scip-index:exact-restore-archive",
                            bound_by="scip-compaction.json:compressed",
                        )
                    )
        preserved.extend(project_manifests)
    else:
        raise RetentionError(f"unsupported derived retention family: {kind}")
    bound_paths = {item["path"] for item in artifacts}
    preserved_set = set(preserved)
    for path in sorted(run.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(run).as_posix()
        if relative not in bound_paths:
            preserved_set.add(relative)
    return artifacts, sorted(preserved_set)


def assess_derived_family_retention(
    inventory_store: Path,
    semantic_store: Path,
    *,
    scip_store: Path | None = None,
    reference_roots: Sequence[Path] = (),
    policy: RetentionPolicy | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Classify derived map storage without granting mutation authority.

    This is intentionally a dry-run ledger.  It protects the newest three raw
    generations even when they are older than the time boundary.  A generation
    is a compression candidate only when it is outside that recovery window and
    stale by age or generation count.  Semantic and SCIP artifacts remain
    blocked until their own authenticated exact-restore adapter exists.
    """

    policy = policy or RetentionPolicy()
    policy.validate()
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    source_plan = plan_navigation_retention(
        inventory_store,
        None,
        semantic_store,
        scip_store=scip_store,
        reference_roots=reference_roots,
        policy=policy,
        now=current_time,
    )
    selected_kinds = {"inventory", "semantic", "scip"}
    stores: list[dict[str, Any]] = []
    candidate_generations = 0
    candidate_bytes = 0
    restore_ready_generations = 0
    restore_ready_bytes = 0
    blocked_generations = 0
    blocked_bytes = 0
    blocked_restore_adapter_generations = 0
    blocked_restore_adapter_bytes = 0
    blocked_reference_scan_generations = 0
    blocked_reference_scan_bytes = 0
    for store in source_plan["stores"]:
        kind = store["kind"]
        if kind not in selected_kinds:
            continue
        ordered = sorted(
            store["generations"],
            key=lambda item: (item["finished_at"], item["run_id"]),
            reverse=True,
        )
        generation_rows: list[dict[str, Any]] = []
        for rank, generation in enumerate(ordered, start=1):
            artifacts, preserved_paths = _generation_assessment_artifacts(
                kind, generation
            )
            preserved_artifacts = _preservation_bindings(
                Path(str(generation["path"])), preserved_paths
            )
            manifest_name = "catalog.json" if kind == "scip" else "manifest.json"
            manifest_after = _read_json(Path(str(generation["path"])) / manifest_name)
            try:
                validate_self_hash(manifest_after)
            except ValueError as exc:
                raise RetentionError(
                    f"{kind} generation manifest drifted during assessment"
                ) from exc
            manifest_binding = next(
                item for item in preserved_artifacts if item["path"] == manifest_name
            )
            if (
                manifest_after.get("receipt_sha256")
                != generation.get("manifest_receipt_sha256")
                or sha256_bytes(canonical_bytes(manifest_after))
                != manifest_binding["sha256"]
            ):
                raise RetentionError(
                    f"{kind} generation manifest drifted during assessment"
                )
            artifact_bytes = sum(item["bytes"] for item in artifacts)
            newest_three = rank <= 3
            stale_by_generation = rank > 3
            stale_by_age = generation["age_seconds"] >= policy.min_age_seconds
            candidate = (
                not newest_three
                and (stale_by_age or stale_by_generation)
                and bool(artifacts)
            )
            restore = (
                "AUTHENTICATED_DATABASE_GZIP_V1"
                if kind == "inventory"
                else "AUTHENTICATED_SEMANTIC_GZIP_V1"
                if kind == "semantic"
                else "AUTHENTICATED_SCIP_GZIP_V1"
            )
            if generation["run_id"] == store["current_run_id"]:
                disposition = "CURRENT_RAW_PROTECTED"
            elif newest_three:
                disposition = "NEWEST_THREE_RAW_PROTECTED"
            elif not artifacts:
                disposition = (
                    "ALREADY_COMPACTED_AUTHENTICATED"
                    if kind in {"inventory", "semantic", "scip"}
                    else "EMPTY_BOUND_ARTIFACT_SET"
                )
            elif not candidate:
                disposition = "RETAIN_NOT_STALE"
            elif source_plan["reference_scan_complete"] and kind in {
                "inventory",
                "semantic",
                "scip",
            }:
                disposition = "DRY_RUN_COMPRESSION_CANDIDATE"
                restore_ready_generations += 1
                restore_ready_bytes += artifact_bytes
            else:
                disposition = (
                    "BLOCKED_REFERENCE_SCAN_INCOMPLETE"
                    if not source_plan["reference_scan_complete"]
                    else "BLOCKED_EXACT_RESTORE_ADAPTER_REQUIRED"
                )
                blocked_generations += 1
                blocked_bytes += artifact_bytes
                if not source_plan["reference_scan_complete"]:
                    blocked_reference_scan_generations += 1
                    blocked_reference_scan_bytes += artifact_bytes
                else:
                    blocked_restore_adapter_generations += 1
                    blocked_restore_adapter_bytes += artifact_bytes
            if candidate:
                candidate_generations += 1
                candidate_bytes += artifact_bytes
            generation_rows.append(
                {
                    "run_id": generation["run_id"],
                    "path": generation["path"],
                    "finished_at": generation["finished_at"],
                    "age_seconds": generation["age_seconds"],
                    "generation_rank": rank,
                    "stale_by_age": stale_by_age,
                    "stale_by_generation": stale_by_generation,
                    "newest_three_raw_protected": newest_three,
                    "external_references": generation["external_references"],
                    "artifact_bytes": artifact_bytes,
                    "artifacts": artifacts,
                    "preserved_paths": preserved_paths,
                    "preserved_artifacts": preserved_artifacts,
                    "restore_capability": restore,
                    "disposition": disposition,
                }
            )
        pointer_path = Path(store["root"]) / "CURRENT.json"
        pointer = _read_json(pointer_path)
        try:
            validate_self_hash(pointer)
        except ValueError as exc:
            raise RetentionError(
                f"{kind} CURRENT pointer drifted during assessment"
            ) from exc
        if (
            pointer.get("schema") != _POINTER_SCHEMAS[kind]
            or pointer.get("run_id") != store["current_run_id"]
        ):
            raise RetentionError(f"{kind} CURRENT pointer drifted during assessment")
        pointer_digest, pointer_bytes = _file_hash(pointer_path)
        if pointer_digest != sha256_bytes(canonical_bytes(pointer)):
            raise RetentionError(f"{kind} CURRENT pointer drifted during assessment")
        stores.append(
            {
                "kind": kind,
                "root": store["root"],
                "current_run_id": store["current_run_id"],
                "total_bytes": store["total_bytes"],
                "generation_count": len(generation_rows),
                "current_pointer": {
                    "path": str(Path(store["root"]) / "CURRENT.json"),
                    "sha256": pointer_digest,
                    "bytes": pointer_bytes,
                },
                "generations": generation_rows,
            }
        )
    status = (
        "PARTIAL_NO_ACTION"
        if not source_plan["reference_scan_complete"]
        else "CANDIDATES_WITH_RESTORE_GAPS"
        if blocked_generations
        else "DRY_RUN_CANDIDATES"
        if restore_ready_generations
        else "NO_ACTION"
    )
    return seal_document(
        {
            "schema": DERIVED_FAMILY_ASSESSMENT_SCHEMA,
            "status": status,
            "authority": "derived-map-retention-assessment-only",
            "mutation_authority": False,
            "repository_cleanup_authority": False,
            "source_history_retirement_authority": False,
            "generated_at": _utc_now(current_time),
            "policy": {
                "stale_when": "age_seconds>=min_age_seconds OR generation_rank>3",
                "newest_raw_generations_protected": 3,
                "min_age_seconds": policy.min_age_seconds,
            },
            "source_retention_plan_receipt_sha256": source_plan["receipt_sha256"],
            "reference_roots": source_plan["reference_roots"],
            "reference_scan_complete": source_plan["reference_scan_complete"],
            "reference_failures": source_plan["reference_failures"],
            "candidate_generations": candidate_generations,
            "candidate_bytes": candidate_bytes,
            "restore_ready_generations": restore_ready_generations,
            "restore_ready_bytes": restore_ready_bytes,
            "blocked_restore_adapter_generations": (
                blocked_restore_adapter_generations
            ),
            "blocked_restore_adapter_bytes": blocked_restore_adapter_bytes,
            "blocked_reference_scan_generations": (
                blocked_reference_scan_generations
            ),
            "blocked_reference_scan_bytes": blocked_reference_scan_bytes,
            "blocked_candidate_generations": blocked_generations,
            "blocked_candidate_bytes": blocked_bytes,
            "stores": stores,
        }
    )


def write_derived_family_retention_assessment(
    inventory_store: Path,
    semantic_store: Path,
    output: Path,
    *,
    scip_store: Path | None = None,
    reference_roots: Sequence[Path] = (),
    policy: RetentionPolicy | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Publish one immutable dry-run ledger without touching a map store."""

    assessment = assess_derived_family_retention(
        inventory_store,
        semantic_store,
        scip_store=scip_store,
        reference_roots=reference_roots,
        policy=policy,
        now=now,
    )
    write_atomic(Path(output), canonical_bytes(assessment))
    return assessment


def _safe_sha256(value: Any) -> str:
    """Hash closed, pathless JSON metadata supplied by the caller."""

    return sha256_bytes(canonical_bytes(value))


def _hex_digest(value: Any, *, length: int = 64) -> str | None:
    if not isinstance(value, str) or len(value) != length:
        return None
    if any(character not in "0123456789abcdef" for character in value):
        return None
    return value


def _safe_assessment_root(path: Path) -> Path:
    root = Path(path).absolute()
    identity = _unavailable_location_label(purpose="derived-map-runtime-root")
    try:
        metadata = root.lstat()
    except OSError as exc:
        raise RetentionError(
            f"derived-map runtime root is unavailable: {identity}"
        ) from exc
    if root.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise RetentionError(f"derived-map runtime root is invalid: {identity}")
    return root


def _current_pointer_files(runtime_roots: Sequence[Path]) -> list[Path]:
    if not runtime_roots:
        raise RetentionError(
            "derived-map runtime root is unavailable: "
            f"{_unavailable_location_label(purpose='derived-map-runtime-root')}"
        )
    roots = [_safe_assessment_root(root) for root in runtime_roots]
    pointers: list[Path] = []
    for root in roots:
        for pointer in sorted(root.rglob("CURRENT.json")):
            metadata = pointer.lstat()
            if pointer.is_symlink() or not stat.S_ISREG(metadata.st_mode):
                raise RetentionError("unsafe cross-store CURRENT pointer")
            pointers.append(pointer)
    if not pointers:
        raise RetentionError("no cross-store CURRENT pointers found")
    return pointers


def _manifest_path_for_current(
    store_root: Path, kind: str, run_id: str
) -> Path:
    try:
        manifest_name = _DERIVED_MANIFEST_NAMES[kind]
    except KeyError as exc:
        raise RetentionError("unsupported derived-map generation kind") from exc
    return store_root / "runs" / run_id / manifest_name


def _load_current_generation(
    pointer_path: Path,
) -> tuple[str, str, dict[str, Any], dict[str, Any], Path]:
    pointer = _read_json(pointer_path)
    try:
        validate_self_hash(pointer)
    except ValueError as exc:
        raise RetentionError("cross-store CURRENT pointer self-hash mismatch") from exc
    schema = pointer.get("schema")
    kind = _DERIVED_POINTER_KINDS.get(schema)
    if kind is None:
        if schema in _NON_PAYLOAD_POINTER_KINDS:
            return (
                _NON_PAYLOAD_POINTER_KINDS[schema],
                "",
                pointer,
                {},
                pointer_path.parent,
            )
        raise RetentionError("unsupported cross-store CURRENT schema")
    run_id = _safe_run_id(pointer.get("run_id"))
    manifest_path = _manifest_path_for_current(pointer_path.parent, kind, run_id)
    manifest = _read_json(manifest_path)
    try:
        validate_self_hash(manifest)
    except ValueError as exc:
        raise RetentionError(
            "cross-store CURRENT manifest self-hash mismatch"
        ) from exc
    manifest_digest, _manifest_bytes = _file_hash(manifest_path)
    digest_field = "catalog_file_sha256" if kind == "scip" else "manifest_file_sha256"
    receipt_field = (
        "catalog_receipt_sha256" if kind == "scip" else "manifest_receipt_sha256"
    )
    if manifest_digest != pointer.get(digest_field):
        raise RetentionError("cross-store CURRENT manifest binding mismatch")
    if manifest.get("receipt_sha256") != pointer.get(receipt_field):
        raise RetentionError("cross-store CURRENT receipt binding mismatch")
    if manifest.get("run_id") != run_id:
        raise RetentionError("cross-store CURRENT run binding mismatch")
    return kind, run_id, pointer, manifest, pointer_path.parent


def _runtime_tree_metadata_snapshot(roots: Sequence[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for supplied in roots:
        root = _safe_assessment_root(supplied)
        for item in sorted(root.rglob("*")):
            try:
                metadata = item.lstat()
            except OSError as exc:
                raise RetentionError("runtime metadata snapshot failed") from exc
            if stat.S_ISDIR(metadata.st_mode):
                kind = "directory"
            elif stat.S_ISREG(metadata.st_mode):
                kind = "file"
            elif stat.S_ISLNK(metadata.st_mode):
                kind = "symlink"
            else:
                kind = "other"
            rows.append(
                {
                    "path": str(item),
                    "kind": kind,
                    "mode": stat.S_IMODE(metadata.st_mode),
                    "uid": metadata.st_uid,
                    "bytes": metadata.st_size if kind == "file" else 0,
                    "mtime_ns": metadata.st_mtime_ns,
                    "inode": metadata.st_ino,
                    "device": metadata.st_dev,
                }
            )
    return rows


def _git_source_view(kind: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    git: Mapping[str, Any] | None = None
    private_root: str | None = None
    if kind == "inventory":
        candidate = manifest.get("git")
        if isinstance(candidate, Mapping):
            git = candidate
        root = manifest.get("root")
        if isinstance(root, Mapping) and isinstance(root.get("path"), str):
            private_root = root["path"]
    elif kind == "mapper":
        repository = manifest.get("repository")
        if isinstance(repository, Mapping):
            candidate = repository.get("git")
            if isinstance(candidate, Mapping):
                git = candidate
            root = repository.get("root")
            if isinstance(root, Mapping) and isinstance(root.get("path"), str):
                private_root = root["path"]
    elif kind == "semantic":
        root = manifest.get("root")
        if isinstance(root, str):
            private_root = root
        elif isinstance(root, Mapping) and isinstance(root.get("path"), str):
            private_root = root["path"]
    elif kind == "scip":
        inventory = manifest.get("inventory")
        if isinstance(inventory, Mapping):
            candidate = inventory.get("git")
            if isinstance(candidate, Mapping):
                git = candidate

    branch = git.get("branch") if isinstance(git, Mapping) else None
    head = _hex_digest(git.get("head"), length=40) if isinstance(git, Mapping) else None
    tree = _hex_digest(git.get("tree"), length=40) if isinstance(git, Mapping) else None
    stable = git.get("stable_during_scan") if isinstance(git, Mapping) else None
    after = git.get("after") if isinstance(git, Mapping) else None
    clean = after.get("clean") if isinstance(after, Mapping) else None
    if not isinstance(branch, str):
        branch = None
    if not isinstance(stable, bool):
        stable = None
    if not isinstance(clean, bool):
        clean = None
    if git is None:
        source_class = "NO_DIRECT_GIT_SOURCE"
    elif clean is True and head and tree:
        source_class = "CLEAN_GIT_SOURCE"
    elif clean is False:
        source_class = "DIRTY_GIT_SOURCE"
    else:
        source_class = "INCOMPLETE_GIT_SOURCE"
    public = {
        "source_class": source_class,
        "branch": branch,
        "head": head,
        "tree": tree,
        "clean": clean,
        "stable_during_scan": stable,
    }
    private = {**public, "source_root": private_root}
    return {"public": public, "private": private}


def _git_object_exists(repository: Path, object_name: str) -> bool:
    try:
        result = subprocess.run(
            ["/usr/bin/git", "-C", str(repository), "cat-file", "-e", object_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _source_reproducibility(source: Mapping[str, Any]) -> dict[str, Any]:
    root = source.get("source_root")
    head = source.get("head")
    tree = source.get("tree")
    clean = source.get("clean")
    stable = source.get("stable_during_scan")
    if clean is False:
        return {
            "status": "DIRTY_SOURCE_WITHOUT_PRESERVED_BUNDLE",
            "clean_source_reproducible": False,
        }
    if clean is not True or stable is not True or not head or not tree:
        return {
            "status": "SOURCE_REPRODUCIBILITY_UNKNOWN",
            "clean_source_reproducible": False,
        }
    if not isinstance(root, str) or not root:
        return {
            "status": "SOURCE_REPOSITORY_UNAVAILABLE",
            "clean_source_reproducible": False,
        }
    repository = Path(root)
    if not _git_object_exists(repository, f"{head}^{{commit}}"):
        return {
            "status": "SOURCE_COMMIT_NOT_PRESERVED",
            "clean_source_reproducible": False,
        }
    if not _git_object_exists(repository, f"{tree}^{{tree}}"):
        return {
            "status": "SOURCE_TREE_NOT_PRESERVED",
            "clean_source_reproducible": False,
        }
    return {
        "status": "PRESERVED_CLEAN_SOURCE",
        "clean_source_reproducible": True,
    }


def _producer_public_identity(kind: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "kind": kind,
        "manifest_schema": manifest.get("schema"),
        "status": manifest.get("status"),
    }
    database = manifest.get("database")
    if isinstance(database, Mapping):
        identity["database_schema_version"] = database.get("schema_version")
    if kind == "mapper":
        compiler = manifest.get("compiler")
        if isinstance(compiler, Mapping):
            compiler_files = compiler.get("files")
            compiler_hashes = []
            if isinstance(compiler_files, list):
                for item in compiler_files:
                    if isinstance(item, Mapping):
                        digest = _hex_digest(item.get("sha256"))
                        if digest:
                            compiler_hashes.append(digest)
            identity["compiler_sha256"] = _hex_digest(compiler.get("sha256"))
            identity["compiler_file_hashes_sha256"] = _safe_sha256(
                sorted(compiler_hashes)
            )
            for key in (
                "cleanup_policy_sha256",
                "flow_policy_sha256",
                "operational_policy_sha256",
                "quality_policy_sha256",
                "runtime_policy_sha256",
            ):
                identity[key] = _hex_digest(compiler.get(key))
    elif kind == "semantic":
        graphify = manifest.get("graphify")
        if isinstance(graphify, Mapping):
            identity["graphify_manifest_sha256"] = _hex_digest(
                graphify.get("graphify_manifest_sha256")
            )
            identity["graphify_python_sha256"] = _hex_digest(
                graphify.get("python_sha256")
            )
        local_model = manifest.get("local_model")
        if isinstance(local_model, Mapping):
            model = local_model.get("model")
            identity["local_model"] = model if isinstance(model, str) else None
    elif kind == "scip":
        counts = manifest.get("counts")
        if isinstance(counts, Mapping):
            identity["index_count"] = counts.get("indexes")
            identity["document_count"] = counts.get("documents")
        index_hashes: list[str] = []
        indexes = manifest.get("indexes")
        if isinstance(indexes, list):
            for item in indexes:
                if isinstance(item, Mapping):
                    digest = _hex_digest(item.get("index_sha256"))
                    if digest:
                        index_hashes.append(digest)
        identity["index_payload_hashes_sha256"] = _safe_sha256(sorted(index_hashes))
    return identity


def _lineage_basis(kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "source_project_scope": "admitted-derived-map-runtime-families",
        "ranking_scope": (
            "global-across-store-families-and-producer-versions; exact source "
            "commit/tree, producer version and payload hashes remain "
            "per-generation evidence"
        ),
    }


def _current_manifest_payload_references(
    kind: str, manifest: Mapping[str, Any]
) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    scan = manifest.get("scan")
    if isinstance(scan, Mapping) and isinstance(scan.get("incremental_from"), str):
        references.append((scan["incremental_from"], f"{kind}:current.incremental_from"))
    inventory = manifest.get("inventory")
    if isinstance(inventory, Mapping) and isinstance(inventory.get("run_id"), str):
        references.append((inventory["run_id"], f"{kind}:current.inventory"))
    semantic = manifest.get("semantic_input")
    if isinstance(semantic, Mapping) and isinstance(semantic.get("run_id"), str):
        references.append((semantic["run_id"], f"{kind}:current.semantic_input"))
    return references


def _lock_status(store_root: Path, run: Path) -> dict[str, Any]:
    candidates = [
        store_root / "retention" / "retention.lock",
        store_root / "maintenance" / "maintenance.lock",
        store_root / ".lock",
        run / ".lock",
        run / "lease.lock",
    ]
    checked = 0
    for lock_path in candidates:
        if not lock_path.exists() and not lock_path.is_symlink():
            continue
        checked += 1
        try:
            metadata = lock_path.lstat()
            if lock_path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
                return {"status": "UNKNOWN", "reason": "UNSAFE_LOCK_ARTIFACT"}
            with lock_path.open("a+b") as handle:
                try:
                    lock_file(handle, blocking=False)
                    unlock_file(handle)
                except BlockingIOError:
                    return {"status": "ACTIVE", "reason": "LOCK_HELD"}
        except OSError:
            return {"status": "UNKNOWN", "reason": "LOCK_CHECK_FAILED"}
    return {"status": "NONE", "checked": checked}


def _payload_open_consumer_status(path: Path) -> dict[str, Any]:
    executable = shutil.which("lsof")
    if executable is None:
        return {"status": "UNKNOWN", "reason": "OPEN_CONSUMER_CHECK_UNAVAILABLE"}
    try:
        result = subprocess.run(
            [executable, "-t", "--", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "UNKNOWN", "reason": "OPEN_CONSUMER_CHECK_FAILED"}
    if result.returncode == 0 and result.stdout.strip():
        return {"status": "ACTIVE", "reason": "OPEN_FILE_HANDLE"}
    if result.returncode == 1:
        return {"status": "NONE"}
    return {"status": "UNKNOWN", "reason": "OPEN_CONSUMER_CHECK_INDETERMINATE"}


def _reference_scan_for_lineage(
    run_ids: Iterable[str], reference_roots: Sequence[Path]
) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    if not reference_roots:
        return {}, []
    return _external_references(run_ids, reference_roots)


def _active_consumer_registry_view(
    registry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if registry is None:
        return {
            "status": "UNKNOWN",
            "reason": "NO_AUTHORITATIVE_ACTIVE_CONSUMER_REGISTRY",
            "active_run_ids": [],
            "negative_run_ids": [],
        }
    if registry.get("schema") != DERIVED_MAP_ACTIVE_CONSUMER_REGISTRY_SCHEMA:
        raise RetentionError("unsupported active-consumer registry schema")
    try:
        validate_self_hash(registry)
    except ValueError as exc:
        raise RetentionError("active-consumer registry self-hash mismatch") from exc
    active_run_ids = registry.get("active_run_ids")
    negative_run_ids = registry.get("negative_run_ids")
    if not isinstance(active_run_ids, list) or not isinstance(negative_run_ids, list):
        raise RetentionError("active-consumer registry has invalid run-id sets")
    active = []
    negative = []
    for item in active_run_ids:
        active.append(_safe_run_id(item))
    for item in negative_run_ids:
        negative.append(_safe_run_id(item))
    if len(active) != len(set(active)) or len(negative) != len(set(negative)):
        raise RetentionError("active-consumer registry has duplicate run IDs")
    if set(active) & set(negative):
        raise RetentionError("active-consumer registry has contradictory run IDs")
    authority = registry.get("authority")
    if authority != "authoritative-derived-map-runtime-liveness":
        raise RetentionError("active-consumer registry authority is invalid")
    return {
        "status": "BOUND",
        "reason": "AUTHORITATIVE_LIVENESS_REGISTRY",
        "active_run_ids": sorted(active),
        "negative_run_ids": sorted(negative),
        "receipt_sha256": registry["receipt_sha256"],
    }


def read_active_consumer_registry(path: Path) -> dict[str, Any]:
    """Read the optional M74 liveness registry without exposing its location."""

    registry = _read_json(Path(path))
    _active_consumer_registry_view(registry)
    return registry


def _summarise_classifications(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, int], dict[str, int]]:
    counts: dict[str, int] = {}
    bytes_by_class: dict[str, int] = {}
    for row in rows:
        classification = str(row["classification"])
        counts[classification] = counts.get(classification, 0) + 1
        bytes_by_class[classification] = bytes_by_class.get(classification, 0) + int(
            row["bytes"]
        )
    return dict(sorted(counts.items())), dict(sorted(bytes_by_class.items()))


def _safe_payload_public(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "payload_alias": row["payload_alias"],
        "classification": row["classification"],
        "bytes": row["bytes"],
        "sha256": row["sha256"],
        "artifact_class": row["artifact_class"],
        "role": row["role"],
        "generation_alias": row["generation_alias"],
        "lineage_alias": row["lineage_alias"],
        "reasons": row["reasons"],
        "active_reference_count": row["active_reference_count"],
        "metadata_only_reference_count": row["metadata_only_reference_count"],
        "open_consumer_status": row["open_consumer_status"],
        "lock_status": row["lock_status"],
        "source_reproducibility_status": row["source_reproducibility_status"],
    }


def _safe_store_group_key(store: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": store["kind"],
        "current_run_id": store.get("current_run_id"),
        "current_status": store.get("current_status"),
        "generation_count": store.get("generation_count"),
        "lineage_identities": store.get("lineage_identities"),
    }


def _path_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _private_workspace_file(path: Path) -> bool:
    private_markers = {
        "private-ledgers",
        "private-workspace",
        "private-inputs",
        "operator-private",
    }
    return bool(private_markers.intersection(path.parts))


def _runtime_byte_accounting(
    snapshot: Sequence[Mapping[str, Any]],
    *,
    pointer_files: Sequence[Path],
    generation_rows: Sequence[Mapping[str, Any]],
    metadata_store_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    classified_payloads: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    payload_paths = {
        str(Path(str(payload["private_artifact_path"]))): payload
        for payload in classified_payloads
    }
    preserved_paths = {str(Path(pointer)) for pointer in pointer_files}
    generation_roots: list[Path] = []
    for generation in generation_rows:
        generation_path = Path(str(generation["generation_path"]))
        generation_roots.append(generation_path)
        for relative in generation.get("preserved_paths", []):
            preserved_paths.add(str(generation_path / str(relative)))
    metadata_roots = [Path(str(row["store_root"])) for row in metadata_store_rows]
    failure_roots = [Path(str(row["failure_path"])) for row in failure_rows]

    rows: list[dict[str, Any]] = []
    class_counts = {key: 0 for key in _BYTE_ACCOUNTING_CLASSES}
    class_bytes = {key: 0 for key in _BYTE_ACCOUNTING_CLASSES}
    regular_file_count = 0
    regular_file_bytes = 0
    non_regular_counts: dict[str, int] = {}
    non_regular_bytes: dict[str, int] = {}
    observed_paths: set[str] = set()
    payload_paths_seen: set[str] = set()

    for item in snapshot:
        kind = item.get("kind")
        if kind != "file":
            key = str(kind)
            non_regular_counts[key] = non_regular_counts.get(key, 0) + 1
            non_regular_bytes[key] = non_regular_bytes.get(key, 0) + int(
                item.get("bytes", 0)
            )
            continue
        path = Path(str(item["path"]))
        path_key = str(path)
        if path_key in observed_paths:
            raise RetentionError("runtime byte accounting observed a duplicate file")
        observed_paths.add(path_key)
        size = int(item["bytes"])
        regular_file_count += 1
        regular_file_bytes += size
        payload = payload_paths.get(path_key)
        if payload is not None:
            payload_paths_seen.add(path_key)
            byte_class = "RECOGNIZED_DERIVED_PAYLOAD"
            payload_alias = payload["payload_alias"]
            payload_classification = payload["classification"]
        elif _private_workspace_file(path):
            byte_class = "EXCLUDED_BUT_COUNTED_PRIVATE_WORKSPACE"
            payload_alias = None
            payload_classification = None
        elif path_key in preserved_paths or any(
            _path_within(path, root) for root in metadata_roots
        ):
            byte_class = "PRESERVED_HISTORY_METADATA_LOG_REPORT_RECEIPT_POINTER"
            payload_alias = None
            payload_classification = None
        elif any(_path_within(path, root) for root in failure_roots) or any(
            _path_within(path, root) for root in generation_roots
        ):
            byte_class = "UNSUPPORTED_UNKNOWN"
            payload_alias = None
            payload_classification = None
        else:
            byte_class = "OTHER_EXPLICIT_RUNTIME_FILE"
            payload_alias = None
            payload_classification = None
        class_counts[byte_class] += 1
        class_bytes[byte_class] += size
        rows.append(
            {
                "path": path_key,
                "bytes": size,
                "byte_class": byte_class,
                "payload_alias": payload_alias,
                "payload_classification": payload_classification,
            }
        )

    missing_payload_paths = sorted(set(payload_paths) - payload_paths_seen)
    if missing_payload_paths:
        raise RetentionError("runtime byte accounting missed a recognized payload")
    class_count_sum = sum(class_counts.values())
    class_byte_sum = sum(class_bytes.values())
    if class_count_sum != regular_file_count or class_byte_sum != regular_file_bytes:
        raise RetentionError("runtime byte accounting sum invariant failed")
    public = {
        "schema": "giga.archaeology.runtime-byte-accounting.v1",
        "scope": "regular-non-symlink-files-under-admitted-runtime-families",
        "classes": list(_BYTE_ACCOUNTING_CLASSES),
        "regular_file_count": regular_file_count,
        "regular_file_bytes": regular_file_bytes,
        "class_counts": {
            key: value for key, value in class_counts.items() if value
        },
        "class_bytes": {key: value for key, value in class_bytes.items() if value},
        "non_regular_entry_counts": dict(sorted(non_regular_counts.items())),
        "non_regular_entry_bytes": dict(sorted(non_regular_bytes.items())),
        "recognized_payload_bytes": class_bytes["RECOGNIZED_DERIVED_PAYLOAD"],
        "preserved_metadata_bytes": class_bytes[
            "PRESERVED_HISTORY_METADATA_LOG_REPORT_RECEIPT_POINTER"
        ],
        "unsupported_unknown_bytes": class_bytes["UNSUPPORTED_UNKNOWN"],
        "excluded_but_counted_private_workspace_bytes": class_bytes[
            "EXCLUDED_BUT_COUNTED_PRIVATE_WORKSPACE"
        ],
        "other_explicit_runtime_file_bytes": class_bytes[
            "OTHER_EXPLICIT_RUNTIME_FILE"
        ],
        "sum_invariant": {
            "status": "PASS",
            "class_count_sum": class_count_sum,
            "class_byte_sum": class_byte_sum,
            "matches_regular_file_count": class_count_sum == regular_file_count,
            "matches_regular_file_bytes": class_byte_sum == regular_file_bytes,
        },
        "candidate_payload_bytes": sum(
            int(payload["bytes"])
            for payload in classified_payloads
            if payload["classification"] == "PAYLOAD_RETIRE_CANDIDATE"
        ),
        "protected_regular_file_bytes": regular_file_bytes
        - sum(
            int(payload["bytes"])
            for payload in classified_payloads
            if payload["classification"] == "PAYLOAD_RETIRE_CANDIDATE"
        ),
        "unrecognized_or_unsupported_file_count": class_counts["UNSUPPORTED_UNKNOWN"],
        "unrecognized_or_unsupported_bytes": class_bytes["UNSUPPORTED_UNKNOWN"],
        "path_derived_identity_disclosed": False,
        "private_paths_disclosed": False,
    }
    return {
        "public": public,
        "private_rows": rows,
    }


def _build_cross_store_lineage_documents(
    runtime_roots: Sequence[Path],
    *,
    reference_roots: Sequence[Path] = (),
    active_consumer_registry: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Assess all derived map stores without granting payload mutation authority."""

    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    consumer_registry = _active_consumer_registry_view(active_consumer_registry)
    pointer_files = _current_pointer_files(runtime_roots)
    before = _runtime_tree_metadata_snapshot(runtime_roots)
    store_rows: list[dict[str, Any]] = []
    metadata_store_rows: list[dict[str, Any]] = []
    generation_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []

    for pointer_index, pointer_path in enumerate(pointer_files, start=1):
        kind, current_run_id, pointer, current_manifest, store_root = (
            _load_current_generation(pointer_path)
        )
        if kind in _NON_PAYLOAD_POINTER_KINDS.values():
            metadata_store_rows.append(
                {
                    "schema": pointer.get("schema"),
                    "kind": kind,
                    "store_root": str(store_root),
                    "current_pointer_path": str(pointer_path),
                    "current_status": pointer.get("status"),
                    "current_run_id": pointer.get("run_id"),
                }
            )
            continue

        runs = store_root / "runs"
        store = _Store(
            kind=kind,
            root=store_root,
            runs=runs,
            quota=2**63 - 1,
            current_run_id=current_run_id,
            current_manifest=current_manifest,
        )
        records = _iter_generation_records(store)
        lineages_for_store: set[str] = set()
        for generation in records:
            run = Path(str(generation["path"]))
            manifest_name = _DERIVED_MANIFEST_NAMES[kind]
            manifest_path = run / manifest_name
            manifest = _read_json(manifest_path)
            try:
                validate_self_hash(manifest)
            except ValueError as exc:
                raise RetentionError("cross-store generation manifest mismatch") from exc
            manifest_sha256, manifest_bytes = _file_hash(manifest_path)
            artifacts, preserved_paths = _generation_assessment_artifacts(
                kind, generation, include_compressed_payloads=True
            )
            source_view = _git_source_view(kind, manifest)
            producer = _producer_public_identity(kind, manifest)
            lineage_basis = _lineage_basis(kind)
            lineage_identity = _safe_sha256(lineage_basis)
            lineages_for_store.add(lineage_identity)
            generation_rows.append(
                {
                    "kind": kind,
                    "store_private_index": pointer_index,
                    "store_root": str(store_root),
                    "current_pointer_path": str(pointer_path),
                    "store_current_run_id": current_run_id,
                    "local_current": generation["run_id"] == current_run_id,
                    "current_manifest_payload_refs": (
                        _current_manifest_payload_references(kind, manifest)
                        if generation["run_id"] == current_run_id
                        else []
                    ),
                    "current_status": pointer.get("status"),
                    "run_id": generation["run_id"],
                    "generation_path": str(run),
                    "manifest_name": manifest_name,
                    "manifest_path": str(manifest_path),
                    "manifest_sha256": manifest_sha256,
                    "manifest_bytes": manifest_bytes,
                    "manifest_receipt_sha256": manifest.get("receipt_sha256"),
                    "manifest_schema": manifest.get("schema"),
                    "finished_at": generation["finished_at"],
                    "bytes": generation["bytes"],
                    "entries": generation["entries"],
                    "artifacts": artifacts,
                    "preserved_paths": preserved_paths,
                    "source": source_view["private"],
                    "source_public": source_view["public"],
                    "producer_public": producer,
                    "lineage_basis": lineage_basis,
                    "lineage_identity_sha256": lineage_identity,
                    "database_storage": generation.get("database_storage"),
                    "semantic_storage": generation.get("semantic_storage"),
                    "scip_storage": generation.get("scip_storage"),
                }
            )
        failures = store_root / "failures"
        if kind == "semantic" and failures.exists():
            failure_store = _Store(
                kind="semantic_failure",
                root=store_root,
                runs=failures,
                quota=2**63 - 1,
                current_run_id=None,
                current_manifest=None,
            )
            for failure in _iter_generation_records(failure_store):
                failure_rows.append(
                    {
                        "store_private_index": pointer_index,
                        "run_id": failure["run_id"],
                        "failure_path": failure["path"],
                        "finished_at": failure["finished_at"],
                        "bytes": failure["bytes"],
                        "entries": failure["entries"],
                    }
                )
        store_rows.append(
            {
                "kind": kind,
                "schema": pointer.get("schema"),
                "store_root": str(store_root),
                "current_pointer_path": str(pointer_path),
                "current_status": pointer.get("status"),
                "current_run_id": current_run_id,
                "generation_count": len(records),
                "lineage_identities": sorted(lineages_for_store),
            }
        )

    run_ids = sorted({row["run_id"] for row in generation_rows})
    external_references, reference_failures = _reference_scan_for_lineage(
        run_ids, reference_roots
    )
    after = _runtime_tree_metadata_snapshot(runtime_roots)
    zero_mutation = before == after

    lineages: dict[str, list[dict[str, Any]]] = {}
    for row in generation_rows:
        lineages.setdefault(row["lineage_identity_sha256"], []).append(row)
    lineage_aliases = {
        lineage_identity: f"lineage-{index:03d}"
        for index, lineage_identity in enumerate(sorted(lineages), start=1)
    }
    active_payload_references: dict[str, set[str]] = {}
    for row in generation_rows:
        if row["run_id"] not in consumer_registry["active_run_ids"]:
            continue
        active_payload_references.setdefault(row["run_id"], set()).add(
            f"{row['kind']}:LIVE_CURRENT"
        )
        for run_id, reason in row["current_manifest_payload_refs"]:
            active_payload_references.setdefault(run_id, set()).add(reason)

    classified_payloads: list[dict[str, Any]] = []
    public_generations: list[dict[str, Any]] = []
    private_generations: list[dict[str, Any]] = []
    for lineage_identity, rows in sorted(lineages.items()):
        ordered = sorted(
            rows,
            key=lambda item: (item["finished_at"], item["run_id"]),
            reverse=True,
        )
        lineage_alias = lineage_aliases[lineage_identity]
        for rank, generation in enumerate(ordered, start=1):
            safe_generation_identity = _safe_sha256(
                {
                    "run_id": generation["run_id"],
                    "source": generation["source_public"],
                    "producer": generation["producer_public"],
                    "payload_sha256s": sorted(
                        item["sha256"] for item in generation["artifacts"]
                    ),
                }
            )
            generation_alias = (
                f"{lineage_alias}-generation-{rank:04d}-"
                f"{safe_generation_identity[:12]}"
            )
            is_current = generation["run_id"] in consumer_registry["active_run_ids"]
            source_reproducibility = _source_reproducibility(generation["source"])
            lock = _lock_status(
                Path(str(generation["store_root"])),
                Path(str(generation["generation_path"])),
            )
            generation_payloads: list[dict[str, Any]] = []
            for artifact_index, artifact in enumerate(
                sorted(generation["artifacts"], key=lambda item: item["sha256"]),
                start=1,
            ):
                active_refs = sorted(
                    active_payload_references.get(generation["run_id"], set())
                )
                metadata_refs = sorted(external_references.get(generation["run_id"], []))
                open_consumer = _payload_open_consumer_status(
                    Path(str(generation["generation_path"])) / artifact["path"]
                )
                reasons: list[str] = []
                if is_current:
                    classification = "RETAIN_CURRENT"
                    reasons.append("generation is a live CURRENT target")
                elif rank <= 3:
                    classification = "RETAIN_GLOBAL_RECENT"
                    reasons.append("inside newest-three global lineage window")
                elif active_refs:
                    classification = "RETAIN_ACTIVE_CONSUMER"
                    reasons.append("referenced by an active current consumer")
                elif lock["status"] == "ACTIVE" or open_consumer["status"] == "ACTIVE":
                    classification = "RETAIN_ACTIVE_CONSUMER"
                    reasons.append("active lock or open consumer observed")
                elif generation["source"].get("clean") is False:
                    classification = "RETAIN_NONREGENERABLE_DIRTY_SOURCE"
                    reasons.append("source tree was dirty and no source bundle is bound")
                elif reference_failures:
                    classification = "UNKNOWN_BLOCKED"
                    reasons.append("reference scan incomplete")
                elif (
                    consumer_registry["status"] != "BOUND"
                    or generation["run_id"]
                    not in consumer_registry["negative_run_ids"]
                ):
                    classification = "UNKNOWN_BLOCKED"
                    reasons.append("active consumer negative is not proved")
                elif lock["status"] == "UNKNOWN" or open_consumer["status"] == "UNKNOWN":
                    classification = "UNKNOWN_BLOCKED"
                    reasons.append("active consumer absence is not proved")
                elif not source_reproducibility["clean_source_reproducible"]:
                    classification = "UNKNOWN_BLOCKED"
                    reasons.append("clean source regeneration is not proved")
                else:
                    classification = "PAYLOAD_RETIRE_CANDIDATE"
                    reasons.append(
                        "non-current payload is globally stale and exactly bound"
                    )
                    if metadata_refs:
                        reasons.append(
                            "external run-id references are metadata-only in M74"
                        )
                payload_alias = (
                    f"{generation_alias}-payload-{artifact_index:02d}-"
                    f"{artifact['sha256'][:12]}"
                )
                payload = {
                    "payload_alias": payload_alias,
                    "classification": classification,
                    "bytes": artifact["bytes"],
                    "sha256": artifact["sha256"],
                    "artifact_class": artifact["artifact_class"],
                    "role": artifact["role"],
                    "generation_alias": generation_alias,
                    "lineage_alias": lineage_alias,
                    "reasons": reasons,
                    "active_reference_count": len(active_refs),
                    "active_references": active_refs,
                    "metadata_only_reference_count": len(metadata_refs),
                    "metadata_only_references": metadata_refs,
                    "open_consumer_status": open_consumer["status"],
                    "open_consumer": open_consumer,
                    "lock_status": lock["status"],
                    "lock": lock,
                    "source_reproducibility_status": source_reproducibility["status"],
                    "source_reproducibility": source_reproducibility,
                    "private_artifact_path": str(
                        Path(str(generation["generation_path"])) / artifact["path"]
                    ),
                }
                classified_payloads.append(payload)
                generation_payloads.append(payload)
            public_generations.append(
                {
                    "generation_alias": generation_alias,
                    "lineage_alias": lineage_alias,
                    "lineage_identity_sha256": lineage_identity,
                    "kind": generation["kind"],
                    "run_id": generation["run_id"],
                    "finished_at": generation["finished_at"],
                    "global_lineage_rank": rank,
                    "current": is_current,
                    "local_current_pointer": generation["local_current"],
                    "manifest_schema": generation["manifest_schema"],
                    "source": generation["source_public"],
                    "producer": generation["producer_public"],
                    "payload_count": len(generation_payloads),
                    "payload_bytes": sum(item["bytes"] for item in generation_payloads),
                    "payload_classification_counts": _summarise_classifications(
                        generation_payloads
                    )[0],
                }
            )
            private_generations.append(
                {
                    **generation,
                    "generation_alias": generation_alias,
                    "lineage_alias": lineage_alias,
                    "global_lineage_rank": rank,
                    "current": is_current,
                    "source_reproducibility": source_reproducibility,
                    "lock": lock,
                    "payloads": generation_payloads,
                }
            )

    classification_counts, classification_bytes = _summarise_classifications(
        classified_payloads
    )
    byte_accounting = _runtime_byte_accounting(
        after,
        pointer_files=pointer_files,
        generation_rows=generation_rows,
        metadata_store_rows=metadata_store_rows,
        failure_rows=failure_rows,
        classified_payloads=classified_payloads,
    )
    candidate_bytes = classification_bytes.get("PAYLOAD_RETIRE_CANDIDATE", 0)
    unknown_bytes = classification_bytes.get("UNKNOWN_BLOCKED", 0)
    if reference_failures:
        status = "PARTIAL_REFERENCE_SCAN_BLOCKED"
    elif candidate_bytes and unknown_bytes:
        status = "MIXED_CANDIDATES_AND_UNKNOWN_BLOCKERS"
    elif candidate_bytes:
        status = "PAYLOAD_RETIRE_CANDIDATES"
    elif unknown_bytes:
        status = "UNKNOWN_BLOCKED"
    else:
        status = "NO_PAYLOAD_RETIRE_CANDIDATES"

    store_groups: dict[str, dict[str, Any]] = {}
    for store in store_rows:
        key = _safe_sha256(_safe_store_group_key(store))
        group = store_groups.setdefault(
            key,
            {
                "store_group_identity_sha256": key,
                "kind": store["kind"],
                "current_status": store["current_status"],
                "store_family_count": 0,
                "generation_count": 0,
                "lineage_count": 0,
            },
        )
        group["store_family_count"] += 1
        group["generation_count"] += int(store["generation_count"])
        group["lineage_count"] = len(set(store["lineage_identities"]))

    public_lineages: list[dict[str, Any]] = []
    for lineage_identity, rows in sorted(lineages.items()):
        lineage_payloads = [
            item
            for item in classified_payloads
            if item["lineage_alias"] == lineage_aliases[lineage_identity]
        ]
        counts, bytes_by_class = _summarise_classifications(lineage_payloads)
        sample_basis = rows[0]["lineage_basis"]
        public_lineages.append(
            {
                "lineage_alias": lineage_aliases[lineage_identity],
                "lineage_identity_sha256": lineage_identity,
                "basis": sample_basis,
                "store_family_count": len(
                    {row["store_private_index"] for row in rows}
                ),
                "generation_count": len(rows),
                "payload_count": len(lineage_payloads),
                "payload_bytes": sum(item["bytes"] for item in lineage_payloads),
                "classification_counts": counts,
                "classification_bytes": bytes_by_class,
            }
        )

    private_ledger = seal_document(
        {
            "schema": DERIVED_MAP_LINEAGE_PRIVATE_LEDGER_SCHEMA,
            "status": status,
            "authority": "private-path-bearing-cross-store-dry-run-ledger",
            "mutation_authority": False,
            "payload_removal_authority": False,
            "generated_at": _utc_now(current_time),
            "active_consumer_registry": consumer_registry,
            "runtime_roots": [str(_safe_assessment_root(root)) for root in runtime_roots],
            "reference_roots": [str(Path(root).absolute()) for root in reference_roots],
            "reference_failures": reference_failures,
            "before_snapshot": before,
            "after_snapshot": after,
            "zero_mutation": zero_mutation,
            "derived_stores": store_rows,
            "metadata_current_stores": metadata_store_rows,
            "failure_generations": failure_rows,
            "generations": private_generations,
            "payloads": classified_payloads,
            "classification_counts": classification_counts,
            "classification_bytes": classification_bytes,
            "byte_accounting": byte_accounting["public"],
            "byte_accounting_rows": byte_accounting["private_rows"],
        }
    )

    public_payloads = [_safe_payload_public(row) for row in classified_payloads]
    public_assessment = seal_document(
        {
            "schema": DERIVED_MAP_LINEAGE_ASSESSMENT_SCHEMA,
            "status": status,
            "authority": "cross-store-derived-map-lineage-assessment-only",
            "mutation_authority": False,
            "payload_removal_authority": False,
            "repository_cleanup_authority": False,
            "source_history_retirement_authority": False,
            "generated_at": _utc_now(current_time),
            "scope": {
                "expected_runtime_families": 2,
                "runtime_family_count": len(runtime_roots),
                "current_pointer_count": len(pointer_files),
                "derived_store_family_count": len(store_rows),
                "non_payload_current_store_count": len(metadata_store_rows),
                "semantic_failure_generation_count": len(failure_rows),
                "private_paths_in_public_output": False,
                "path_derived_hashes_in_public_output": False,
            },
            "policy": {
                "classification_values": [
                    "RETAIN_CURRENT",
                    "RETAIN_GLOBAL_RECENT",
                    "RETAIN_ACTIVE_CONSUMER",
                    "RETAIN_NONREGENERABLE_DIRTY_SOURCE",
                    "PAYLOAD_RETIRE_CANDIDATE",
                    "UNKNOWN_BLOCKED",
                ],
                "global_recent_window": 3,
                "newest_three_scope": "logical-lineage-global-not-per-store",
                "current_scope": (
                    "authoritative-active-consumer-registry-not-local-pointer"
                ),
                "candidate_requires_authenticated_payload": True,
                "candidate_requires_authoritative_active_consumer_negative": True,
                "candidate_requires_reproducible_clean_source": True,
                "payload_removal_deferred_to_separate_M75_authority": True,
            },
            "graph_status": {
                "queried_as_index_before_m74": True,
                "refresh_performed_in_m74": False,
                "reported_status": "PARTIAL_STALE_NOT_REFRESHED_IN_M74",
            },
            "private_ledger": {
                "produced": True,
                "path_disclosed": False,
                "receipt_hash_disclosed": False,
                "reason": (
                    "ledger contains private filesystem paths and is intentionally "
                    "not content-addressed in public output"
                ),
            },
            "reference_scan": {
                "reference_root_count": len(reference_roots),
                "complete": not reference_failures,
                "failure_count": len(reference_failures),
                "external_run_id_references_do_not_imply_payload_need": True,
            },
            "active_consumer_registry": {
                "status": consumer_registry["status"],
                "reason": consumer_registry["reason"],
                "active_run_id_count": len(consumer_registry["active_run_ids"]),
                "negative_run_id_count": len(consumer_registry["negative_run_ids"]),
                "historical_current_pointers_are_not_activity_proof": True,
            },
            "zero_mutation": {
                "status": "PASS" if zero_mutation else "FAILED",
                "assessed_runtime_metadata_unchanged_during_scan": zero_mutation,
                "path_bearing_snapshot_publicly_disclosed": False,
                "move_delete_quarantine_purge_performed": False,
            },
            "counts": {
                "lineages": len(public_lineages),
                "generation_records": len(public_generations),
                "payload_records": len(public_payloads),
                "total_payload_bytes": sum(item["bytes"] for item in public_payloads),
                "candidate_payload_bytes": candidate_bytes,
                "unknown_blocked_payload_bytes": unknown_bytes,
                "protected_payload_bytes": sum(
                    item["bytes"]
                    for item in public_payloads
                    if item["classification"] != "PAYLOAD_RETIRE_CANDIDATE"
                ),
                "total_regular_file_bytes": byte_accounting["public"][
                    "regular_file_bytes"
                ],
                "protected_regular_file_bytes": byte_accounting["public"][
                    "protected_regular_file_bytes"
                ],
                "unsupported_unknown_regular_file_bytes": byte_accounting["public"][
                    "unsupported_unknown_bytes"
                ],
                "excluded_but_counted_private_workspace_bytes": byte_accounting[
                    "public"
                ]["excluded_but_counted_private_workspace_bytes"],
            },
            "byte_accounting": byte_accounting["public"],
            "classification_counts": classification_counts,
            "classification_bytes": classification_bytes,
            "store_groups": sorted(
                store_groups.values(),
                key=lambda item: item["store_group_identity_sha256"],
            ),
            "lineages": public_lineages,
            "generations": sorted(
                public_generations,
                key=lambda item: (item["lineage_alias"], item["global_lineage_rank"]),
            ),
            "payloads": sorted(public_payloads, key=lambda item: item["payload_alias"]),
        }
    )
    return public_assessment, private_ledger


def assess_cross_store_derived_map_lineage(
    runtime_roots: Sequence[Path],
    *,
    reference_roots: Sequence[Path] = (),
    active_consumer_registry: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    assessment, _private_ledger = _build_cross_store_lineage_documents(
        runtime_roots,
        reference_roots=reference_roots,
        active_consumer_registry=active_consumer_registry,
        now=now,
    )
    return assessment


def render_cross_store_derived_map_lineage_report(
    assessment: Mapping[str, Any],
) -> str:
    lines = [
        "# M74 cross-store derived-map lineage assessment",
        "",
        f"Schema: {assessment['schema']}",
        f"Status: {assessment['status']}",
        "Authority: assessment-only; no payload removal, cleanup, quarantine or purge.",
        f"Generated at: {assessment['generated_at']}",
        "",
        "## Scope",
        "",
        f"- Derived map stores: {assessment['scope']['derived_store_family_count']}",
        f"- Current pointers observed: {assessment['scope']['current_pointer_count']}",
        f"- Logical lineages: {assessment['counts']['lineages']}",
        f"- Generations: {assessment['counts']['generation_records']}",
        f"- Payload records: {assessment['counts']['payload_records']}",
        "",
        "## Bytes",
        "",
        f"- Total regular runtime file bytes: {assessment['counts']['total_regular_file_bytes']}",
        f"- Total payload bytes: {assessment['counts']['total_payload_bytes']}",
        f"- Retire-candidate bytes: {assessment['counts']['candidate_payload_bytes']}",
        f"- Unknown-blocked bytes: {assessment['counts']['unknown_blocked_payload_bytes']}",
        f"- Protected payload bytes: {assessment['counts']['protected_payload_bytes']}",
        f"- Protected regular file bytes: {assessment['counts']['protected_regular_file_bytes']}",
        "- Byte-accounting sum invariant: "
        f"{assessment['byte_accounting']['sum_invariant']['status']}",
        "",
        "## Exhaustive byte accounting",
        "",
    ]
    for key, value in assessment["byte_accounting"]["class_bytes"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
        "",
        "## Classification counts",
        "",
        ]
    )
    for key, value in assessment["classification_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Lineages",
            "",
        ]
    )
    for lineage in assessment["lineages"]:
        lines.append(
            "- "
            f"{lineage['lineage_alias']}: kind={lineage['basis']['kind']}, "
            f"stores={lineage['store_family_count']}, "
            f"generations={lineage['generation_count']}, "
            f"candidate_bytes={lineage['classification_bytes'].get('PAYLOAD_RETIRE_CANDIDATE', 0)}, "
            f"unknown_bytes={lineage['classification_bytes'].get('UNKNOWN_BLOCKED', 0)}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Public output omits filesystem paths, basenames and path-derived hashes.",
            "- Private path-bearing ledger is intentionally not hashed into this public report.",
            "- M75 or later authority is required before any payload removal.",
            f"- Graph status: {assessment['graph_status']['reported_status']}.",
            "",
        ]
    )
    return "\n".join(lines)


def write_cross_store_derived_map_lineage_assessment(
    runtime_roots: Sequence[Path],
    *,
    public_output: Path | None = None,
    report_output: Path | None = None,
    private_ledger_output: Path | None = None,
    reference_roots: Sequence[Path] = (),
    active_consumer_registry: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    assessment, private_ledger = _build_cross_store_lineage_documents(
        runtime_roots,
        reference_roots=reference_roots,
        active_consumer_registry=active_consumer_registry,
        now=now,
    )
    if private_ledger_output is not None:
        _write_create_once(Path(private_ledger_output), private_ledger)
    if public_output is not None:
        write_atomic(Path(public_output), canonical_bytes(assessment))
    if report_output is not None:
        report = seal_document(
            {
                "schema": DERIVED_MAP_LINEAGE_REPORT_SCHEMA,
                "assessment_receipt_sha256": assessment["receipt_sha256"],
                "rendered_sha256": sha256_bytes(
                    render_cross_store_derived_map_lineage_report(
                        assessment
                    ).encode("utf-8")
                ),
            }
        )
        text = (
            render_cross_store_derived_map_lineage_report(assessment)
            + "\n"
            + f"\nReport receipt: {report['receipt_sha256']}\n"
        )
        write_atomic(Path(report_output), text.encode("utf-8"))
    return assessment


def _raise_m74_private_ledger_binding_refusal(exc: BaseException | None = None) -> None:
    raise RetentionError(_M74_PRIVATE_LEDGER_BINDING_REFUSAL) from exc


def _m74_strict_json_object(raw: bytes) -> dict[str, Any]:
    def object_pairs_hook(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _raise_m74_private_ledger_binding_refusal()
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=object_pairs_hook)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)
    if not isinstance(value, dict):
        _raise_m74_private_ledger_binding_refusal()
    return value


def _read_m74_private_ledger_read_only(path: Path) -> dict[str, Any]:
    try:
        ledger_path = Path(path).absolute()
        parent = ledger_path.parent
        parent_metadata = parent.lstat()
        if (
            parent.is_symlink()
            or not stat.S_ISDIR(parent_metadata.st_mode)
            or parent_metadata.st_uid != os.getuid()
            or stat.S_IMODE(parent_metadata.st_mode) != 0o700
        ):
            _raise_m74_private_ledger_binding_refusal()
        before = ledger_path.lstat()
        if (
            ledger_path.is_symlink()
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_size <= 0
            or before.st_size > _READ_LIMIT
        ):
            _raise_m74_private_ledger_binding_refusal()
        descriptor = os.open(ledger_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            opened = os.fstat(descriptor)
            opened_identity = (
                opened.st_dev,
                opened.st_ino,
                opened.st_size,
                opened.st_mtime_ns,
                opened.st_ctime_ns,
            )
            before_identity = (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            if opened_identity != before_identity:
                _raise_m74_private_ledger_binding_refusal()
            chunks: list[bytes] = []
            remaining = opened.st_size
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    _raise_m74_private_ledger_binding_refusal()
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                _raise_m74_private_ledger_binding_refusal()
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        final = ledger_path.lstat()
        stable_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        final_identity = (
            final.st_dev,
            final.st_ino,
            final.st_size,
            final.st_mtime_ns,
            final.st_ctime_ns,
        )
        if stable_identity != final_identity:
            _raise_m74_private_ledger_binding_refusal()
        ledger = _m74_strict_json_object(b"".join(chunks))
        validate_self_hash(ledger)
        return ledger
    except (OSError, ValueError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)


def _read_m74_parent_assessment(path: Path) -> dict[str, Any]:
    try:
        assessment = _read_json(Path(path))
        validate_self_hash(assessment)
        return assessment
    except (OSError, ValueError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)


def _m74_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _raise_m74_private_ledger_binding_refusal()
    return value


def _m74_expected_counts_from_assessment(
    assessment: Mapping[str, Any],
) -> dict[str, int]:
    try:
        scope = assessment["scope"]
        counts = assessment["counts"]
        byte_accounting = assessment["byte_accounting"]
        return {
            "current_pointer_count": _m74_integer(scope["current_pointer_count"]),
            "derived_store_family_count": _m74_integer(
                scope["derived_store_family_count"]
            ),
            "metadata_store_family_count": _m74_integer(
                scope["non_payload_current_store_count"]
            ),
            "generation_records": _m74_integer(counts["generation_records"]),
            "payload_records": _m74_integer(counts["payload_records"]),
            "regular_file_count": _m74_integer(
                byte_accounting["regular_file_count"]
            ),
            "regular_file_bytes": _m74_integer(
                byte_accounting["regular_file_bytes"]
            ),
        }
    except (KeyError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)


def _m74_expected_byte_class_bytes_from_assessment(
    assessment: Mapping[str, Any],
) -> dict[str, int]:
    try:
        return {
            key: _m74_integer(value)
            for key, value in assessment["byte_accounting"]["class_bytes"].items()
        }
    except (AttributeError, KeyError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)


def _m74_private_ledger_counts(ledger: Mapping[str, Any]) -> dict[str, int]:
    try:
        return {
            "current_pointer_count": len(ledger["derived_stores"])
            + len(ledger["metadata_current_stores"]),
            "derived_store_family_count": len(ledger["derived_stores"]),
            "metadata_store_family_count": len(ledger["metadata_current_stores"]),
            "generation_records": len(ledger["generations"]),
            "payload_records": len(ledger["payloads"]),
            "regular_file_count": _m74_integer(
                ledger["byte_accounting"]["regular_file_count"]
            ),
            "regular_file_bytes": _m74_integer(
                ledger["byte_accounting"]["regular_file_bytes"]
            ),
        }
    except (KeyError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)


def _m74_normalised_int_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        _raise_m74_private_ledger_binding_refusal()
    return dict(
        sorted((str(key), _m74_integer(item)) for key, item in value.items())
    )


def _m74_nonzero_mapping(value: Mapping[str, int]) -> dict[str, int]:
    return {key: amount for key, amount in value.items() if amount != 0}


def _m74_validate_byte_accounting_rows(
    ledger: Mapping[str, Any],
) -> tuple[dict[str, int], dict[str, int]]:
    try:
        rows = ledger["byte_accounting_rows"]
    except KeyError as exc:
        _raise_m74_private_ledger_binding_refusal(exc)
    if not isinstance(rows, list):
        _raise_m74_private_ledger_binding_refusal()
    class_counts = {key: 0 for key in _BYTE_ACCOUNTING_CLASSES}
    class_bytes = {key: 0 for key in _BYTE_ACCOUNTING_CLASSES}
    for row in rows:
        if not isinstance(row, Mapping):
            _raise_m74_private_ledger_binding_refusal()
        byte_class = row.get("byte_class")
        if byte_class not in class_counts:
            _raise_m74_private_ledger_binding_refusal()
        row_bytes = _m74_integer(row.get("bytes"))
        class_counts[str(byte_class)] += 1
        class_bytes[str(byte_class)] += row_bytes
    return class_counts, class_bytes


def _m74_validate_assessment_and_private_ledger(
    assessment: Mapping[str, Any],
    private_ledger: Mapping[str, Any],
    *,
    expected_parent_assessment_receipt_sha256: str,
    expected_counts: Mapping[str, int],
    expected_byte_class_bytes: Mapping[str, int],
) -> dict[str, Any]:
    try:
        if assessment["schema"] != DERIVED_MAP_LINEAGE_ASSESSMENT_SCHEMA:
            _raise_m74_private_ledger_binding_refusal()
        if (
            assessment["receipt_sha256"]
            != expected_parent_assessment_receipt_sha256
        ):
            _raise_m74_private_ledger_binding_refusal()
        if private_ledger["schema"] != DERIVED_MAP_LINEAGE_PRIVATE_LEDGER_SCHEMA:
            _raise_m74_private_ledger_binding_refusal()
        if private_ledger["mutation_authority"] is not False:
            _raise_m74_private_ledger_binding_refusal()
        if private_ledger["payload_removal_authority"] is not False:
            _raise_m74_private_ledger_binding_refusal()
        if private_ledger["byte_accounting"] != assessment["byte_accounting"]:
            _raise_m74_private_ledger_binding_refusal()
        if private_ledger["classification_counts"] != assessment[
            "classification_counts"
        ]:
            _raise_m74_private_ledger_binding_refusal()
        if private_ledger["classification_bytes"] != assessment[
            "classification_bytes"
        ]:
            _raise_m74_private_ledger_binding_refusal()
        if private_ledger["zero_mutation"] is not True:
            _raise_m74_private_ledger_binding_refusal()
        if assessment["zero_mutation"]["status"] != "PASS":
            _raise_m74_private_ledger_binding_refusal()
        if (
            assessment["zero_mutation"][
                "assessed_runtime_metadata_unchanged_during_scan"
            ]
            is not True
        ):
            _raise_m74_private_ledger_binding_refusal()
        if (
            assessment["zero_mutation"]["move_delete_quarantine_purge_performed"]
            is not False
        ):
            _raise_m74_private_ledger_binding_refusal()
        if (
            assessment["zero_mutation"]["path_bearing_snapshot_publicly_disclosed"]
            is not False
        ):
            _raise_m74_private_ledger_binding_refusal()
        if private_ledger["status"] != assessment["status"]:
            _raise_m74_private_ledger_binding_refusal()
    except (KeyError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)

    expected_counts_view = {
        key: _m74_integer(value) for key, value in expected_counts.items()
    }
    if _m74_expected_counts_from_assessment(assessment) != expected_counts_view:
        _raise_m74_private_ledger_binding_refusal()
    if _m74_private_ledger_counts(private_ledger) != expected_counts_view:
        _raise_m74_private_ledger_binding_refusal()

    expected_byte_classes = _m74_normalised_int_mapping(expected_byte_class_bytes)
    assessment_byte_classes = _m74_expected_byte_class_bytes_from_assessment(
        assessment
    )
    if assessment_byte_classes != expected_byte_classes:
        _raise_m74_private_ledger_binding_refusal()
    try:
        ledger_byte_accounting = private_ledger["byte_accounting"]
        ledger_byte_classes = _m74_normalised_int_mapping(
            ledger_byte_accounting["class_bytes"]
        )
        if ledger_byte_classes != expected_byte_classes:
            _raise_m74_private_ledger_binding_refusal()
        if ledger_byte_accounting["sum_invariant"]["status"] != "PASS":
            _raise_m74_private_ledger_binding_refusal()
        if sum(ledger_byte_classes.values()) != expected_counts_view[
            "regular_file_bytes"
        ]:
            _raise_m74_private_ledger_binding_refusal()
    except (KeyError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)

    row_class_counts, row_class_bytes = _m74_validate_byte_accounting_rows(
        private_ledger
    )
    try:
        public_class_counts = _m74_normalised_int_mapping(
            private_ledger["byte_accounting"]["class_counts"]
        )
    except (KeyError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)
    row_class_counts = _m74_nonzero_mapping(row_class_counts)
    row_class_bytes = _m74_nonzero_mapping(row_class_bytes)
    if row_class_counts != public_class_counts:
        _raise_m74_private_ledger_binding_refusal()
    if row_class_bytes != expected_byte_classes:
        _raise_m74_private_ledger_binding_refusal()
    if sum(row_class_counts.values()) != expected_counts_view["regular_file_count"]:
        _raise_m74_private_ledger_binding_refusal()

    classification_counts = _m74_normalised_int_mapping(
        private_ledger["classification_counts"]
    )
    classification_bytes = _m74_normalised_int_mapping(
        private_ledger["classification_bytes"]
    )
    try:
        if (
            sum(classification_counts.values())
            != expected_counts_view["payload_records"]
        ):
            _raise_m74_private_ledger_binding_refusal()
        if sum(classification_bytes.values()) != assessment["counts"][
            "total_payload_bytes"
        ]:
            _raise_m74_private_ledger_binding_refusal()
    except (KeyError, TypeError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)

    return {
        "counts": expected_counts_view,
        "byte_class_counts": row_class_counts,
        "byte_class_bytes": expected_byte_classes,
        "classification_counts": classification_counts,
        "classification_bytes": classification_bytes,
        "total_payload_bytes": _m74_integer(
            assessment["counts"]["total_payload_bytes"]
        ),
        "candidate_payload_bytes": _m74_integer(
            assessment["counts"]["candidate_payload_bytes"]
        ),
        "unknown_blocked_payload_bytes": _m74_integer(
            assessment["counts"]["unknown_blocked_payload_bytes"]
        ),
        "protected_payload_bytes": _m74_integer(
            assessment["counts"]["protected_payload_bytes"]
        ),
    }


def _assert_m74_public_correction_is_pathless(value: Any) -> None:
    forbidden_key_parts = (
        "path",
        "root",
        "basename",
        "location",
        "filesystem",
        "raw",
        "content",
        "payload_hash",
        "source_hash",
        "ledger_hash",
    )
    forbidden_string_parts = (
        "/",
        "\\",
        "\x00",
        "file:",
        "~",
        "Users",
        "ox-alpha-giga-workspace",
        "giga-user",
        "ledger.exhaustive",
        "ledger.final",
    )
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in forbidden_key_parts):
                _raise_m74_private_ledger_binding_refusal()
            _assert_m74_public_correction_is_pathless(item)
    elif isinstance(value, list):
        for item in value:
            _assert_m74_public_correction_is_pathless(item)
    elif isinstance(value, str):
        if any(part in value for part in forbidden_string_parts):
            _raise_m74_private_ledger_binding_refusal()


def build_m74_private_ledger_binding_correction(
    parent_assessment: Mapping[str, Any],
    private_ledger: Mapping[str, Any],
    *,
    now: datetime | None = None,
    expected_parent_assessment_receipt_sha256: str = (
        _M74_PARENT_ASSESSMENT_RECEIPT_SHA256
    ),
    expected_counts: Mapping[str, int] | None = None,
    expected_byte_class_bytes: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Build a public, aggregate-only correction for the existing M74 ledger.

    The input ledger is deliberately path-bearing private evidence. This function
    validates it against the public parent assessment, then seals only aggregate
    counts and byte totals. It never publishes ledger paths, raw ledger hashes,
    payload content hashes, repository roots, basenames, or path-derived values.
    """

    try:
        validate_self_hash(parent_assessment)
        validate_self_hash(private_ledger)
        expected_counts_view = dict(expected_counts or _M74_EXPECTED_COUNTS)
        expected_byte_classes = dict(
            expected_byte_class_bytes or _M74_EXPECTED_BYTE_CLASS_BYTES
        )
        aggregate = _m74_validate_assessment_and_private_ledger(
            parent_assessment,
            private_ledger,
            expected_parent_assessment_receipt_sha256=(
                expected_parent_assessment_receipt_sha256
            ),
            expected_counts=expected_counts_view,
            expected_byte_class_bytes=expected_byte_classes,
        )
        generated_at = _utc_now(now)
        safe_projection = seal_document(
            {
                "schema": _M74_PRIVATE_LEDGER_SAFE_PROJECTION_SCHEMA,
                "status": "VALIDATED_EXISTING_LEDGER_AGGREGATE_ONLY",
                "generated_at": generated_at,
                "parent_assessment_receipt_sha256": (
                    expected_parent_assessment_receipt_sha256
                ),
                "counts": aggregate["counts"],
                "byte_accounting": {
                    "sum_invariant_status": "PASS",
                    "regular_file_count": aggregate["counts"][
                        "regular_file_count"
                    ],
                    "regular_file_bytes": aggregate["counts"][
                        "regular_file_bytes"
                    ],
                    "class_counts": aggregate["byte_class_counts"],
                    "class_bytes": aggregate["byte_class_bytes"],
                },
                "payload_classifications": {
                    "counts": aggregate["classification_counts"],
                    "bytes": aggregate["classification_bytes"],
                    "total_payload_bytes": aggregate["total_payload_bytes"],
                    "candidate_payload_bytes": aggregate[
                        "candidate_payload_bytes"
                    ],
                    "unknown_blocked_payload_bytes": aggregate[
                        "unknown_blocked_payload_bytes"
                    ],
                    "protected_payload_bytes": aggregate[
                        "protected_payload_bytes"
                    ],
                },
                "zero_action": {
                    "assessment_rescan_performed": False,
                    "private_evidence_written_or_moved": False,
                    "payload_move_delete_quarantine_purge_performed": False,
                    "runtime_graph_refresh_performed": False,
                    "successor_payload_action_performed": False,
                },
            }
        )
        correction = seal_document(
            {
                "schema": _M74_PRIVATE_LEDGER_BINDING_CORRECTION_SCHEMA,
                "status": "PENDING_INDEPENDENT_REVIEW",
                "generated_at": generated_at,
                "parent_assessment_receipt_sha256": (
                    expected_parent_assessment_receipt_sha256
                ),
                "rejected_preserved_commit": (
                    "8a3857c1c4aedcede8109e6622334fbbb108aaf7"
                ),
                "reason": (
                    "Parent M74 assessment omitted a machine-checkable binding "
                    "to the exhaustive private ledger. This child validates the "
                    "existing ledger read-only and publishes only aggregate "
                    "safe projection evidence."
                ),
                "safe_projection_receipt_sha256": safe_projection[
                    "receipt_sha256"
                ],
                "safe_projection": safe_projection,
                "invalidated_public_outputs": {
                    "removed_public_output_count": 5,
                    "reconciliation": (
                        "Earlier statement of two outputs was incomplete. "
                        "Sealed correction evidence records five invalidated "
                        "newly generated public assessment outputs, not any "
                        "observed map-store payload, prior committed evidence, "
                        "private ledger, or runtime receipt."
                    ),
                    "waves": [
                        {
                            "label": "FIRST_PUBLIC_ASSESSMENT_WAVE",
                            "count": 2,
                            "public_output_roles": [
                                "machine_assessment",
                                "human_report",
                            ],
                        },
                        {
                            "label": "BYTE_COMPLETENESS_ASSESSMENT_WAVE",
                            "count": 2,
                            "public_output_roles": [
                                "machine_assessment",
                                "human_report",
                            ],
                        },
                        {
                            "label": "INTERMEDIATE_ACCOUNTING_WAVE",
                            "count": 1,
                            "public_output_roles": [
                                "machine_accounting_receipt",
                            ],
                        },
                    ],
                },
            }
        )
        _assert_m74_public_correction_is_pathless(correction)
        return correction
    except (KeyError, TypeError, ValueError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)


def write_m74_private_ledger_binding_correction(
    parent_assessment_path: Path,
    private_ledger_path: Path,
    public_output: Path,
    *,
    now: datetime | None = None,
    expected_parent_assessment_receipt_sha256: str = (
        _M74_PARENT_ASSESSMENT_RECEIPT_SHA256
    ),
    expected_counts: Mapping[str, int] | None = None,
    expected_byte_class_bytes: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Create the M74 correction receipt after read-only private-ledger validation."""

    parent_assessment = _read_m74_parent_assessment(Path(parent_assessment_path))
    private_ledger = _read_m74_private_ledger_read_only(Path(private_ledger_path))
    correction = build_m74_private_ledger_binding_correction(
        parent_assessment,
        private_ledger,
        now=now,
        expected_parent_assessment_receipt_sha256=(
            expected_parent_assessment_receipt_sha256
        ),
        expected_counts=expected_counts,
        expected_byte_class_bytes=expected_byte_class_bytes,
    )
    try:
        _write_create_once(Path(public_output), correction)
    except (OSError, ValueError) as exc:
        _raise_m74_private_ledger_binding_refusal(exc)
    return correction


def _raise_m75_candidate_plan_refusal(exc: BaseException | None = None) -> None:
    raise RetentionError(_M75_CANDIDATE_PLAN_REFUSAL) from exc


def _m75_parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or "/" in value:
        _raise_m75_candidate_plan_refusal()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        _raise_m75_candidate_plan_refusal(exc)
    return parsed.astimezone(UTC)


def _m75_validate_m74_correction(
    correction: Mapping[str, Any],
    *,
    expected_parent_assessment_receipt_sha256: str,
    expected_counts: Mapping[str, int],
    expected_byte_class_bytes: Mapping[str, int],
) -> str:
    try:
        validate_self_hash(correction)
        if correction["schema"] != _M74_PRIVATE_LEDGER_BINDING_CORRECTION_SCHEMA:
            _raise_m75_candidate_plan_refusal()
        if correction["status"] not in {
            "PENDING_INDEPENDENT_REVIEW",
            "ACCEPTED_BY_INDEPENDENT_PRIVACY_REVIEW",
        }:
            _raise_m75_candidate_plan_refusal()
        if (
            correction["parent_assessment_receipt_sha256"]
            != expected_parent_assessment_receipt_sha256
        ):
            _raise_m75_candidate_plan_refusal()
        projection = correction["safe_projection"]
        validate_self_hash(projection)
        if projection["schema"] != _M74_PRIVATE_LEDGER_SAFE_PROJECTION_SCHEMA:
            _raise_m75_candidate_plan_refusal()
        if (
            correction["safe_projection_receipt_sha256"]
            != projection["receipt_sha256"]
        ):
            _raise_m75_candidate_plan_refusal()
        if projection["counts"] != dict(expected_counts):
            _raise_m75_candidate_plan_refusal()
        if (
            projection["byte_accounting"]["class_bytes"]
            != dict(expected_byte_class_bytes)
        ):
            _raise_m75_candidate_plan_refusal()
        return str(projection["receipt_sha256"])
    except (KeyError, TypeError, ValueError) as exc:
        _raise_m75_candidate_plan_refusal(exc)


def _m75_validate_graph_status(graph_status: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "queried_existing_graph_first",
        "reported_status",
        "local_graph_output_present",
        "runtime_graph_outputs_observed",
        "refresh_performed",
        "covers_m75_current_commit",
        "covers_m69_to_m74_current_census",
        "reason",
    }
    if not isinstance(graph_status, Mapping):
        _raise_m75_candidate_plan_refusal()
    if set(graph_status) != required:
        _raise_m75_candidate_plan_refusal()
    if graph_status["queried_existing_graph_first"] is not True:
        _raise_m75_candidate_plan_refusal()
    if graph_status["refresh_performed"] is not False:
        _raise_m75_candidate_plan_refusal()
    if graph_status["reported_status"] not in {"PARTIAL_STALE", "CURRENT"}:
        _raise_m75_candidate_plan_refusal()
    view = dict(graph_status)
    _assert_m75_public_plan_is_pathless(view)
    return view


def _m75_payload_status_counts(
    payloads: Iterable[Mapping[str, Any]],
    key: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for payload in payloads:
        status_value = str(payload.get(key, "UNKNOWN"))
        counts[status_value] = counts.get(status_value, 0) + 1
    return dict(sorted(counts.items()))


def _m75_payload_state_blockers(
    payloads: Sequence[Mapping[str, Any]],
) -> list[str]:
    blockers: set[str] = set()
    for payload in payloads:
        classification = payload.get("classification")
        if classification not in _M75_SUPPORTED_PAYLOAD_CLASSIFICATIONS:
            blockers.add("PAYLOAD_STATE_UNSUPPORTED")
        elif classification == "UNKNOWN_BLOCKED":
            blockers.add("PAYLOAD_STATE_UNKNOWN")
        elif classification == "RETAIN_NONREGENERABLE_DIRTY_SOURCE":
            blockers.add("PAYLOAD_STATE_DIRTY_OR_NONREGENERABLE")
        reasons = payload.get("reasons", [])
        if not isinstance(reasons, list):
            blockers.add("PAYLOAD_STATE_UNKNOWN")
            continue
        reason_text = " ".join(str(item).lower() for item in reasons)
        if "dirty" in reason_text:
            blockers.add("PAYLOAD_STATE_DIRTY_OR_NONREGENERABLE")
        if "partial" in reason_text or "incomplete" in reason_text:
            blockers.add("PAYLOAD_STATE_INCOMPLETE")
        if "unknown" in reason_text or "not proved" in reason_text:
            blockers.add("PAYLOAD_STATE_UNKNOWN")
    return sorted(blockers)


def _m75_safe_payload_bijection_view(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        view = _safe_payload_public(payload)
    except KeyError as exc:
        _raise_m75_candidate_plan_refusal(exc)
    for key in ("payload_alias", "generation_alias", "lineage_alias", "sha256"):
        value = view[key]
        if not isinstance(value, str) or not value or "/" in value or "\\" in value:
            _raise_m75_candidate_plan_refusal()
    for key in (
        "bytes",
        "active_reference_count",
        "metadata_only_reference_count",
    ):
        view[key] = _m74_integer(view[key])
    if view["classification"] not in _M75_SUPPORTED_PAYLOAD_CLASSIFICATIONS:
        _raise_m75_candidate_plan_refusal()
    if not isinstance(view["reasons"], list) or any(
        not isinstance(item, str) or not item for item in view["reasons"]
    ):
        _raise_m75_candidate_plan_refusal()
    return view


def _m75_validate_generation_payload_bijection(
    private_ledger: Mapping[str, Any],
    aggregate: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        top_level_payloads = private_ledger["payloads"]
        generations = private_ledger["generations"]
    except KeyError as exc:
        _raise_m75_candidate_plan_refusal(exc)
    if not isinstance(top_level_payloads, list) or not isinstance(generations, list):
        _raise_m75_candidate_plan_refusal()

    top_level_by_alias: dict[str, dict[str, Any]] = {}
    for payload in top_level_payloads:
        if not isinstance(payload, Mapping):
            _raise_m75_candidate_plan_refusal()
        view = _m75_safe_payload_bijection_view(payload)
        alias = view["payload_alias"]
        if alias in top_level_by_alias:
            _raise_m75_candidate_plan_refusal()
        top_level_by_alias[alias] = view

    nested_by_alias: dict[str, dict[str, Any]] = {}
    nested_count_by_generation: dict[str, int] = {}
    nested_bytes_by_generation: dict[str, int] = {}
    for generation in generations:
        if not isinstance(generation, Mapping):
            _raise_m75_candidate_plan_refusal()
        generation_alias = generation.get("generation_alias")
        if (
            not isinstance(generation_alias, str)
            or not generation_alias
            or "/" in generation_alias
            or "\\" in generation_alias
        ):
            _raise_m75_candidate_plan_refusal()
        payloads = generation.get("payloads")
        if not isinstance(payloads, list):
            _raise_m75_candidate_plan_refusal()
        for payload in payloads:
            if not isinstance(payload, Mapping):
                _raise_m75_candidate_plan_refusal()
            view = _m75_safe_payload_bijection_view(payload)
            if view["generation_alias"] != generation_alias:
                _raise_m75_candidate_plan_refusal()
            alias = view["payload_alias"]
            if alias in nested_by_alias:
                _raise_m75_candidate_plan_refusal()
            nested_by_alias[alias] = view
            nested_count_by_generation[generation_alias] = (
                nested_count_by_generation.get(generation_alias, 0) + 1
            )
            nested_bytes_by_generation[generation_alias] = (
                nested_bytes_by_generation.get(generation_alias, 0)
                + int(view["bytes"])
            )

    if set(top_level_by_alias) != set(nested_by_alias):
        _raise_m75_candidate_plan_refusal()
    for alias, view in top_level_by_alias.items():
        if nested_by_alias[alias] != view:
            _raise_m75_candidate_plan_refusal()

    nested_counts, nested_bytes = _summarise_classifications(
        nested_by_alias.values()
    )
    expected_counts = aggregate["classification_counts"]
    expected_bytes = aggregate["classification_bytes"]
    if nested_counts != expected_counts or nested_bytes != expected_bytes:
        _raise_m75_candidate_plan_refusal()
    try:
        if len(nested_by_alias) != _m74_integer(aggregate["counts"]["payload_records"]):
            _raise_m75_candidate_plan_refusal()
        if sum(nested_bytes.values()) != _m74_integer(
            aggregate["total_payload_bytes"]
        ):
            _raise_m75_candidate_plan_refusal()
    except (KeyError, TypeError) as exc:
        _raise_m75_candidate_plan_refusal(exc)

    return {
        "status": "PASS",
        "top_level_payload_records": len(top_level_by_alias),
        "nested_generation_payload_records": len(nested_by_alias),
        "generation_records_with_payloads": len(nested_count_by_generation),
        "nested_payload_bytes": sum(nested_bytes.values()),
        "classification_counts": nested_counts,
        "classification_bytes": nested_bytes,
    }


def _m75_generation_plan_row(
    generation: Mapping[str, Any],
    *,
    ordinal: int,
    now: datetime,
    consumer_registry: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        finished_at = _m75_parse_utc(generation["finished_at"])
        rank = _m74_integer(generation["global_lineage_rank"])
        manifest_schema = generation.get("manifest_schema")
        current_status = generation.get("current_status")
        payloads = generation["payloads"]
        if not isinstance(payloads, list):
            _raise_m75_candidate_plan_refusal()
        payload_count = len(payloads)
        payload_bytes = sum(_m74_integer(payload["bytes"]) for payload in payloads)
        open_counts = _m75_payload_status_counts(payloads, "open_consumer_status")
        lock_counts = _m75_payload_status_counts(payloads, "lock_status")
        payload_classification_counts, payload_classification_bytes = (
            _summarise_classifications(payloads)
        )
    except (KeyError, TypeError) as exc:
        _raise_m75_candidate_plan_refusal(exc)

    age_seconds = int((now - finished_at).total_seconds())
    if age_seconds < 0:
        _raise_m75_candidate_plan_refusal()
    stale_by_age = age_seconds > _M75_STALE_AFTER_SECONDS
    stale_by_rank = rank > _M75_GLOBAL_RECENT_WINDOW
    stale = stale_by_age or stale_by_rank
    protections: list[str] = []
    blockers: list[str] = []
    recommendation = "NO_RETENTION_ACTION_RECOMMENDED"
    try:
        run_id = str(generation["run_id"])
        is_live_current = run_id in consumer_registry["active_run_ids"]
        active_negative_proved = run_id in consumer_registry["negative_run_ids"]
    except (KeyError, TypeError) as exc:
        _raise_m75_candidate_plan_refusal(exc)

    if generation.get("local_current") is True or is_live_current:
        protections.append("RETAIN_CURRENT_POINTER")
    if rank <= _M75_GLOBAL_RECENT_WINDOW:
        protections.append("RETAIN_GLOBAL_RECENT")
    if manifest_schema not in _M75_SUPPORTED_MANIFEST_SCHEMAS:
        blockers.append("UNKNOWN_OR_UNSUPPORTED_SCHEMA")
    if current_status not in _M75_SUPPORTED_GENERATION_STATUSES:
        blockers.append("GENERATION_STATE_UNKNOWN")
    elif current_status in _M75_INCOMPLETE_GENERATION_STATUSES:
        blockers.append("GENERATION_STATE_INCOMPLETE_OR_INDETERMINATE")
    if any(status == "ACTIVE" for status in open_counts) or any(
        status == "ACTIVE" for status in lock_counts
    ):
        protections.append("RETAIN_ACTIVE_CONSUMER")
    if any(status == "UNKNOWN" for status in open_counts):
        blockers.append("OPEN_CONSUMER_UNKNOWN")
    if any(status == "UNKNOWN" for status in lock_counts):
        blockers.append("LOCK_OR_HANDLE_UNKNOWN")
    source_reproducibility = generation.get("source_reproducibility")
    if not isinstance(source_reproducibility, Mapping):
        blockers.append("MISSING_PROVENANCE")
    elif source_reproducibility.get("clean_source_reproducible") is not True:
        blockers.append("MISSING_OR_NONREGENERABLE_PROVENANCE")
    if consumer_registry.get("status") != "AUTHORITATIVE":
        blockers.append("ACTIVE_CONSUMER_ABSENCE_NOT_PROVED")
    elif not active_negative_proved and not is_live_current:
        blockers.append("ACTIVE_CONSUMER_ABSENCE_NOT_PROVED")
    blockers.extend(_m75_payload_state_blockers(payloads))

    if protections:
        classification = protections[0]
    elif not stale:
        classification = "RETAIN_NOT_STALE"
    elif blockers:
        classification = "UNKNOWN_BLOCKED"
    else:
        classification = "PAYLOAD_RETIRE_CANDIDATE"
        recommendation = "RECOVERABLE_QUARANTINE_CANDIDATE"

    return {
        "plan_generation_alias": f"generation-{ordinal:06d}",
        "lineage_alias": generation["lineage_alias"],
        "kind": generation["kind"],
        "global_lineage_rank": rank,
        "manifest_schema_supported": (
            manifest_schema in _M75_SUPPORTED_MANIFEST_SCHEMAS
        ),
        "generation_state_status": (
            str(current_status)
            if current_status in _M75_SUPPORTED_GENERATION_STATUSES
            else "UNKNOWN"
        ),
        "age_seconds": age_seconds,
        "stale_by_age_gt_24h": stale_by_age,
        "stale_by_rank_gt_newest_three": stale_by_rank,
        "stale": stale,
        "payload_count": payload_count,
        "payload_bytes": payload_bytes,
        "payload_classification_counts": payload_classification_counts,
        "payload_classification_bytes": payload_classification_bytes,
        "open_consumer_status_counts": open_counts,
        "lock_status_counts": lock_counts,
        "protections": protections,
        "blockers": sorted(set(blockers)),
        "classification": classification,
        "recommendation": recommendation,
    }


def _m75_summarise_plan(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, int], dict[str, int]]:
    counts: dict[str, int] = {}
    bytes_by_class: dict[str, int] = {}
    for row in rows:
        classification = str(row["classification"])
        counts[classification] = counts.get(classification, 0) + 1
        bytes_by_class[classification] = bytes_by_class.get(classification, 0) + int(
            row["payload_bytes"]
        )
    return dict(sorted(counts.items())), dict(sorted(bytes_by_class.items()))


def _assert_m75_public_plan_is_pathless(value: Any) -> None:
    forbidden_key_parts = (
        "path",
        "root",
        "basename",
        "location",
        "filesystem",
        "raw",
        "content",
        "payload_hash",
        "source_hash",
        "ledger_hash",
    )
    forbidden_string_parts = (
        "/",
        "\\",
        "\x00",
        "file:",
        "~",
        "Users",
        "ox-alpha-giga-workspace",
        "giga-user",
        "ledger.exhaustive",
        "ledger.final",
    )
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in forbidden_key_parts):
                _raise_m75_candidate_plan_refusal()
            _assert_m75_public_plan_is_pathless(item)
    elif isinstance(value, list):
        for item in value:
            _assert_m75_public_plan_is_pathless(item)
    elif isinstance(value, str):
        if any(part in value for part in forbidden_string_parts):
            _raise_m75_candidate_plan_refusal()


def build_m75_mac_derived_map_retention_candidate_plan(
    parent_assessment: Mapping[str, Any],
    private_ledger: Mapping[str, Any],
    m74_correction: Mapping[str, Any],
    *,
    graph_status: Mapping[str, Any],
    now: datetime | None = None,
    expected_parent_assessment_receipt_sha256: str = (
        _M74_PARENT_ASSESSMENT_RECEIPT_SHA256
    ),
    expected_counts: Mapping[str, int] | None = None,
    expected_byte_class_bytes: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Build a no-action M75 retention candidate plan from accepted M74 evidence."""

    try:
        validate_self_hash(parent_assessment)
        validate_self_hash(private_ledger)
        expected_counts_view = dict(expected_counts or _M74_EXPECTED_COUNTS)
        expected_byte_classes = dict(
            expected_byte_class_bytes or _M74_EXPECTED_BYTE_CLASS_BYTES
        )
        projection_receipt = _m75_validate_m74_correction(
            m74_correction,
            expected_parent_assessment_receipt_sha256=(
                expected_parent_assessment_receipt_sha256
            ),
            expected_counts=expected_counts_view,
            expected_byte_class_bytes=expected_byte_classes,
        )
        aggregate = _m74_validate_assessment_and_private_ledger(
            parent_assessment,
            private_ledger,
            expected_parent_assessment_receipt_sha256=(
                expected_parent_assessment_receipt_sha256
            ),
            expected_counts=expected_counts_view,
            expected_byte_class_bytes=expected_byte_classes,
        )
        payload_bijection = _m75_validate_generation_payload_bijection(
            private_ledger,
            aggregate,
        )
        generated_at = _utc_now(now)
        now_value = _m75_parse_utc(generated_at)
        registry = private_ledger["active_consumer_registry"]
        if not isinstance(registry, Mapping):
            _raise_m75_candidate_plan_refusal()
        if set(registry.get("active_run_ids", [])) or set(
            registry.get("negative_run_ids", [])
        ):
            registry_mode = "AUTHORITATIVE"
        else:
            registry_mode = str(registry.get("status", "UNKNOWN"))
        consumer_registry = {
            "status": registry_mode,
            "active_run_ids": sorted(str(item) for item in registry["active_run_ids"]),
            "negative_run_ids": sorted(
                str(item) for item in registry["negative_run_ids"]
            ),
        }
        generations = private_ledger["generations"]
        if not isinstance(generations, list):
            _raise_m75_candidate_plan_refusal()
        rows = [
            _m75_generation_plan_row(
                generation,
                ordinal=index,
                now=now_value,
                consumer_registry=consumer_registry,
            )
            for index, generation in enumerate(generations, start=1)
        ]
        class_counts, class_bytes = _m75_summarise_plan(rows)
        candidate_rows = [
            row
            for row in rows
            if row["recommendation"] == "RECOVERABLE_QUARANTINE_CANDIDATE"
        ]
        graph_view = _m75_validate_graph_status(graph_status)
        plan = seal_document(
            {
                "schema": M75_MAC_DERIVED_MAP_RETENTION_CANDIDATE_PLAN_SCHEMA,
                "status": "PENDING_INDEPENDENT_REVIEW",
                "authority": "assessment_and_planning_only",
                "generated_at": generated_at,
                "zero_action": {
                    "payload_move_delete_quarantine_purge_performed": False,
                    "runtime_store_mutation_performed": False,
                    "repository_or_history_cleanup_performed": False,
                    "graph_refresh_performed": False,
                    "provider_or_browser_action_performed": False,
                    "successor_action_performed": False,
                },
                "stale_policy": {
                    "stale_after_seconds": _M75_STALE_AFTER_SECONDS,
                    "global_recent_window": _M75_GLOBAL_RECENT_WINDOW,
                    "operator_rule": (
                        "stale_when_age_exceeds_24h_OR_older_than_newest_three"
                    ),
                    "override_order": [
                        "current_pointer",
                        "newest_three",
                        "dirty_or_incomplete_provenance",
                        "unknown_schema",
                        "active_lock_handle_or_consumer",
                        "missing_provenance",
                        "uncertain_state",
                    ],
                    "absence_of_live_consumer_registry": "UNKNOWN_BLOCKED",
                },
                "graph": graph_view,
                "evidence": {
                    "m74_parent_assessment_receipt_sha256": (
                        parent_assessment["receipt_sha256"]
                    ),
                    "m74_private_ledger_binding_correction_receipt_sha256": (
                        m74_correction["receipt_sha256"]
                    ),
                    "m74_safe_projection_receipt_sha256": projection_receipt,
                    "rejected_parent_commit_preserved": (
                        "8a3857c1c4aedcede8109e6622334fbbb108aaf7"
                    ),
                    "accepted_correction_commit": (
                        "dc7d58ef9fd26f96592be34f5d85e0ba8664a61f"
                    ),
                },
                "census": {
                    "current_pointer_count": aggregate["counts"][
                        "current_pointer_count"
                    ],
                    "derived_store_family_count": aggregate["counts"][
                        "derived_store_family_count"
                    ],
                    "metadata_store_family_count": aggregate["counts"][
                        "metadata_store_family_count"
                    ],
                    "generation_records": aggregate["counts"][
                        "generation_records"
                    ],
                    "payload_records": aggregate["counts"]["payload_records"],
                    "regular_file_count": aggregate["counts"][
                        "regular_file_count"
                    ],
                    "regular_file_bytes": aggregate["counts"][
                        "regular_file_bytes"
                    ],
                    "byte_class_counts": aggregate["byte_class_counts"],
                    "byte_class_bytes": aggregate["byte_class_bytes"],
                    "byte_sum_invariant_status": "PASS",
                },
                "candidate_plan": {
                    "generation_records": len(rows),
                    "classification_counts": class_counts,
                    "classification_bytes": class_bytes,
                    "recoverable_quarantine_candidate_generations": len(
                        candidate_rows
                    ),
                    "recoverable_quarantine_candidate_payload_bytes": sum(
                        int(row["payload_bytes"]) for row in candidate_rows
                    ),
                    "absence_of_live_consumer_registry_treated_as_negative_proof": (
                        False
                    ),
                },
                "payload_bijection": {
                    "status": payload_bijection["status"],
                    "top_level_payload_records": payload_bijection[
                        "top_level_payload_records"
                    ],
                    "nested_generation_payload_records": payload_bijection[
                        "nested_generation_payload_records"
                    ],
                    "generation_records_with_payloads": payload_bijection[
                        "generation_records_with_payloads"
                    ],
                    "nested_payload_bytes": payload_bijection[
                        "nested_payload_bytes"
                    ],
                    "classification_counts": payload_bijection[
                        "classification_counts"
                    ],
                    "classification_bytes": payload_bijection[
                        "classification_bytes"
                    ],
                    "material_safe_fields_checked": [
                        "payload_alias",
                        "generation_alias",
                        "lineage_alias",
                        "classification",
                        "bytes",
                        "artifact_class",
                        "role",
                        "reasons",
                        "active_reference_count",
                        "metadata_only_reference_count",
                        "open_consumer_status",
                        "lock_status",
                        "clean_rebuild_provenance_status",
                    ],
                },
                "generations": rows,
            }
        )
        _assert_m75_public_plan_is_pathless(plan)
        return plan
    except (KeyError, TypeError, ValueError) as exc:
        _raise_m75_candidate_plan_refusal(exc)


def write_m75_mac_derived_map_retention_candidate_plan(
    parent_assessment_path: Path,
    private_ledger_path: Path,
    m74_correction_path: Path,
    public_output: Path,
    *,
    graph_status: Mapping[str, Any],
    now: datetime | None = None,
    expected_parent_assessment_receipt_sha256: str = (
        _M74_PARENT_ASSESSMENT_RECEIPT_SHA256
    ),
    expected_counts: Mapping[str, int] | None = None,
    expected_byte_class_bytes: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Create one no-action M75 plan from existing M74 evidence."""

    try:
        parent_assessment = _read_m74_parent_assessment(Path(parent_assessment_path))
        private_ledger = _read_m74_private_ledger_read_only(Path(private_ledger_path))
        m74_correction = _read_json(Path(m74_correction_path))
        plan = build_m75_mac_derived_map_retention_candidate_plan(
            parent_assessment,
            private_ledger,
            m74_correction,
            graph_status=graph_status,
            now=now,
            expected_parent_assessment_receipt_sha256=(
                expected_parent_assessment_receipt_sha256
            ),
            expected_counts=expected_counts,
            expected_byte_class_bytes=expected_byte_class_bytes,
        )
        _write_create_once(Path(public_output), plan)
        return plan
    except (OSError, ValueError, TypeError) as exc:
        _raise_m75_candidate_plan_refusal(exc)


def _raise_m77_liveness_assessment_refusal(
    exc: BaseException | None = None,
) -> None:
    raise RetentionError(_M77_LIVENESS_ASSESSMENT_REFUSAL) from exc


def _m77_strict_json_object(raw: bytes) -> dict[str, Any]:
    def object_pairs_hook(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _raise_m77_liveness_assessment_refusal()
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=object_pairs_hook)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        _raise_m77_liveness_assessment_refusal(exc)
    if not isinstance(value, dict):
        _raise_m77_liveness_assessment_refusal()
    return value


def _read_m77_json_read_only(path: Path) -> dict[str, Any]:
    identity = _unavailable_location_label(purpose="m77-liveness-input")
    try:
        candidate = Path(path).absolute()
        before = candidate.lstat()
        if (
            candidate.is_symlink()
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > _READ_LIMIT
        ):
            _raise_m77_liveness_assessment_refusal()
        raw = candidate.read_bytes()
        after = candidate.lstat()
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            _raise_m77_liveness_assessment_refusal()
        return _m77_strict_json_object(raw)
    except (OSError, ValueError, TypeError) as exc:
        raise RetentionError(
            f"M77 liveness input refused: {identity}"
        ) from exc


def _m77_parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or "/" in value:
        _raise_m77_liveness_assessment_refusal()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        _raise_m77_liveness_assessment_refusal(exc)
    return parsed.astimezone(UTC)


def _m77_assert_public_is_pathless(value: Any) -> None:
    forbidden_key_parts = (
        "path",
        "root",
        "basename",
        "location",
        "filesystem",
    )
    forbidden_string_parts = (
        "/",
        "\\",
        "\x00",
        "file:",
        "~",
        "Users",
        "ox-alpha-giga-workspace",
        "giga-user",
        "ledger.exhaustive",
        "ledger.final",
    )
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in forbidden_key_parts):
                _raise_m77_liveness_assessment_refusal()
            _m77_assert_public_is_pathless(item)
    elif isinstance(value, list):
        for item in value:
            _m77_assert_public_is_pathless(item)
    elif isinstance(value, str):
        if any(part in value for part in forbidden_string_parts):
            _raise_m77_liveness_assessment_refusal()


def _m77_validate_graph_status(graph_status: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "queried_existing_graph_first",
        "reported_status",
        "local_graph_output_present",
        "runtime_graph_outputs_observed",
        "refresh_performed",
        "covers_m77_current_commit",
        "covers_m76_to_m77_candidate",
        "reason",
    }
    if not isinstance(graph_status, Mapping) or set(graph_status) != required:
        _raise_m77_liveness_assessment_refusal()
    if graph_status["queried_existing_graph_first"] is not True:
        _raise_m77_liveness_assessment_refusal()
    if graph_status["refresh_performed"] is not False:
        _raise_m77_liveness_assessment_refusal()
    if graph_status["reported_status"] not in {"PARTIAL_STALE", "CURRENT"}:
        _raise_m77_liveness_assessment_refusal()
    view = dict(graph_status)
    _m77_assert_public_is_pathless(view)
    return view


def _m77_validate_m75_plan(
    plan: Mapping[str, Any],
    aggregate: Mapping[str, Any],
    *,
    expected_m75_plan_receipt_sha256: str | None,
) -> dict[str, Mapping[str, Any]]:
    try:
        validate_self_hash(plan)
        if plan["schema"] != M75_MAC_DERIVED_MAP_RETENTION_CANDIDATE_PLAN_SCHEMA:
            _raise_m77_liveness_assessment_refusal()
        if plan["status"] not in {
            "PENDING_INDEPENDENT_REVIEW",
            "ACCEPTED_BY_INDEPENDENT_REVIEW",
        }:
            _raise_m77_liveness_assessment_refusal()
        if expected_m75_plan_receipt_sha256 is not None and (
            plan["receipt_sha256"] != expected_m75_plan_receipt_sha256
        ):
            _raise_m77_liveness_assessment_refusal()
        if plan["zero_action"]["payload_move_delete_quarantine_purge_performed"]:
            _raise_m77_liveness_assessment_refusal()
        if plan["zero_action"]["runtime_store_mutation_performed"]:
            _raise_m77_liveness_assessment_refusal()
        if plan["zero_action"]["graph_refresh_performed"]:
            _raise_m77_liveness_assessment_refusal()
        census = plan["census"]
        expected_counts = aggregate["counts"]
        if census["current_pointer_count"] != expected_counts["current_pointer_count"]:
            _raise_m77_liveness_assessment_refusal()
        if (
            census["derived_store_family_count"]
            != expected_counts["derived_store_family_count"]
        ):
            _raise_m77_liveness_assessment_refusal()
        if (
            census["metadata_store_family_count"]
            != expected_counts["metadata_store_family_count"]
        ):
            _raise_m77_liveness_assessment_refusal()
        if census["generation_records"] != expected_counts["generation_records"]:
            _raise_m77_liveness_assessment_refusal()
        if census["payload_records"] != expected_counts["payload_records"]:
            _raise_m77_liveness_assessment_refusal()
        if census["regular_file_count"] != expected_counts["regular_file_count"]:
            _raise_m77_liveness_assessment_refusal()
        if census["regular_file_bytes"] != expected_counts["regular_file_bytes"]:
            _raise_m77_liveness_assessment_refusal()
        rows = plan["generations"]
        if not isinstance(rows, list):
            _raise_m77_liveness_assessment_refusal()
    except (KeyError, TypeError, ValueError) as exc:
        _raise_m77_liveness_assessment_refusal(exc)

    by_alias: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            _raise_m77_liveness_assessment_refusal()
        alias = row.get("plan_generation_alias")
        if (
            not isinstance(alias, str)
            or not alias.startswith("generation-")
            or alias in by_alias
            or "/" in alias
            or "\\" in alias
        ):
            _raise_m77_liveness_assessment_refusal()
        by_alias[alias] = row
    return by_alias


def _m77_selected_generation_rows(
    private_ledger: Mapping[str, Any],
    m75_rows: Mapping[str, Mapping[str, Any]],
    *,
    cohort_aliases: Sequence[str],
    expected_cohort_bytes: Mapping[str, tuple[str, int]] | None,
) -> list[dict[str, Any]]:
    if len(set(cohort_aliases)) != len(cohort_aliases):
        _raise_m77_liveness_assessment_refusal()
    requested = tuple(sorted(str(alias) for alias in cohort_aliases))
    if any(
        not alias.startswith("generation-") or "/" in alias or "\\" in alias
        for alias in requested
    ):
        _raise_m77_liveness_assessment_refusal()
    try:
        generations = private_ledger["generations"]
    except KeyError as exc:
        _raise_m77_liveness_assessment_refusal(exc)
    if not isinstance(generations, list):
        _raise_m77_liveness_assessment_refusal()
    selected: list[dict[str, Any]] = []
    for ordinal, generation in enumerate(generations, start=1):
        alias = f"generation-{ordinal:06d}"
        if alias not in requested:
            continue
        if not isinstance(generation, Mapping):
            _raise_m77_liveness_assessment_refusal()
        plan_row = m75_rows.get(alias)
        if plan_row is None:
            _raise_m77_liveness_assessment_refusal()
        try:
            payloads = generation["payloads"]
            if not isinstance(payloads, list):
                _raise_m77_liveness_assessment_refusal()
            payload_bytes = sum(_m74_integer(payload["bytes"]) for payload in payloads)
            kind = str(generation["kind"])
            if plan_row["kind"] != kind:
                _raise_m77_liveness_assessment_refusal()
            if plan_row["payload_bytes"] != payload_bytes:
                _raise_m77_liveness_assessment_refusal()
            if plan_row["payload_count"] != len(payloads):
                _raise_m77_liveness_assessment_refusal()
            if expected_cohort_bytes is not None:
                expected = expected_cohort_bytes.get(alias)
                if expected is None or expected != (kind, payload_bytes):
                    _raise_m77_liveness_assessment_refusal()
        except (KeyError, TypeError, ValueError) as exc:
            _raise_m77_liveness_assessment_refusal(exc)
        selected.append(
            {
                "plan_generation_alias": alias,
                "generation": generation,
                "m75_row": plan_row,
            }
        )
    if tuple(row["plan_generation_alias"] for row in selected) != requested:
        _raise_m77_liveness_assessment_refusal()
    return selected


def _m77_cohort_state_identity(selected: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    private_rows: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []
    for item in selected:
        alias = str(item["plan_generation_alias"])
        generation = item["generation"]
        kind = str(generation["kind"])
        try:
            run = Path(str(generation["generation_path"]))
            manifest_name = _DERIVED_MANIFEST_NAMES[kind]
            manifest_path = run / manifest_name
            manifest_sha256, manifest_bytes = _file_hash(manifest_path)
            artifacts = generation["artifacts"]
        except (KeyError, TypeError, ValueError) as exc:
            _raise_m77_liveness_assessment_refusal(exc)
        artifact_rows = []
        if not isinstance(artifacts, list):
            _raise_m77_liveness_assessment_refusal()
        for artifact in artifacts:
            if not isinstance(artifact, Mapping):
                _raise_m77_liveness_assessment_refusal()
            artifact_path = run / str(artifact.get("path"))
            digest, size = _file_hash(artifact_path)
            artifact_rows.append(
                {
                    "alias": alias,
                    "role": artifact.get("role"),
                    "bytes": size,
                    "sha256": digest,
                }
            )
        private_rows.append(
            {
                "alias": alias,
                "kind": kind,
                "manifest_sha256": manifest_sha256,
                "manifest_bytes": manifest_bytes,
                "artifacts": sorted(artifact_rows, key=lambda row: row["role"]),
            }
        )
        public_rows.append(
            {
                "alias": alias,
                "kind": kind,
                "lineage_alias": generation.get("lineage_alias"),
                "payload_aliases": sorted(
                    str(payload.get("payload_alias"))
                    for payload in generation.get("payloads", [])
                ),
                "payload_bytes": sum(
                    _m74_integer(payload.get("bytes", 0))
                    for payload in generation.get("payloads", [])
                    if isinstance(payload, Mapping)
                ),
            }
        )
    return {
        "entry_count": len(private_rows),
        "identity_sha256": _safe_sha256(public_rows),
        "private_drift_sha256": _safe_sha256(private_rows),
    }


def _m77_payload_state_for_generation(generation: Mapping[str, Any]) -> dict[str, Any]:
    try:
        kind = str(generation["kind"])
        run = Path(str(generation["generation_path"]))
        manifest_name = _DERIVED_MANIFEST_NAMES[kind]
        manifest = _read_json(run / manifest_name)
        validate_self_hash(manifest)
        if manifest.get("receipt_sha256") != generation.get("manifest_receipt_sha256"):
            _raise_m77_liveness_assessment_refusal()
        artifacts = generation["artifacts"]
        payloads = generation["payloads"]
    except (KeyError, TypeError, ValueError) as exc:
        _raise_m77_liveness_assessment_refusal(exc)
    if not isinstance(artifacts, list) or not isinstance(payloads, list):
        _raise_m77_liveness_assessment_refusal()
    if len(artifacts) != len(payloads):
        _raise_m77_liveness_assessment_refusal()

    proofs = {
        "manifest_self_hash": "PASS",
        "payload_records": len(payloads),
        "payload_bytes": 0,
        "bound_artifact_count": 0,
        "authenticated_gzip_restore_stream_count": 0,
        "raw_database_binding_count": 0,
        "unsupported_artifact_count": 0,
    }
    for payload in payloads:
        _m75_safe_payload_bijection_view(payload)
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            _raise_m77_liveness_assessment_refusal()
        _bound_artifact(
            run,
            relative=artifact.get("path"),
            digest=artifact.get("sha256"),
            size=artifact.get("bytes"),
            artifact_class=str(artifact.get("artifact_class")),
            role=str(artifact.get("role")),
            bound_by=str(artifact.get("bound_by")),
        )
        proofs["payload_bytes"] += _m74_integer(artifact.get("bytes"))
        proofs["bound_artifact_count"] += 1
        artifact_class = artifact.get("artifact_class")
        artifact_path = run / str(artifact.get("path"))
        if artifact_class == "AUTHENTICATED_GZIP_PAYLOAD_ARCHIVE":
            if kind not in {"inventory", "mapper"}:
                proofs["unsupported_artifact_count"] += 1
                continue
            receipt = _validate_compaction_receipt(kind, run, manifest)
            if receipt is None:
                _raise_m77_liveness_assessment_refusal()
            compressed = receipt["compressed"]
            if (
                compressed["path"] != artifact.get("path")
                or compressed["sha256"] != artifact.get("sha256")
                or compressed["bytes"] != artifact.get("bytes")
            ):
                _raise_m77_liveness_assessment_refusal()
            _verify_gzip_content(
                artifact_path,
                receipt["source"]["sha256"],
                receipt["source"]["bytes"],
            )
            proofs["authenticated_gzip_restore_stream_count"] += 1
        elif artifact_class == "SQLITE_DATABASE":
            proofs["raw_database_binding_count"] += 1
        else:
            proofs["unsupported_artifact_count"] += 1
    status = (
        "PASS"
        if proofs["unsupported_artifact_count"] == 0 and proofs["payload_records"] > 0
        else "UNKNOWN"
    )
    return {
        "status": status,
        "proofs": proofs,
    }


def _m77_current_pointer_evidence(generation: Mapping[str, Any]) -> dict[str, Any]:
    try:
        kind = str(generation["kind"])
        run_id = str(generation["run_id"])
        pointer_path = Path(str(generation["current_pointer_path"]))
        current_kind, current_run_id, _pointer, manifest, _store = (
            _load_current_generation(pointer_path)
        )
        if current_kind != kind:
            return {"status": "UNKNOWN", "reason": "CURRENT_KIND_MISMATCH"}
        active_reasons = []
        if current_run_id == run_id:
            active_reasons.append("CURRENT_TARGET")
        for referenced_run_id, reason in _current_manifest_payload_references(
            kind, manifest
        ):
            if referenced_run_id == run_id:
                active_reasons.append(reason)
        return {
            "status": "ACTIVE" if active_reasons else "NONE",
            "active_reason_count": len(active_reasons),
        }
    except (OSError, KeyError, TypeError, ValueError):
        return {"status": "UNKNOWN", "reason": "CURRENT_POINTER_CHECK_FAILED"}


def _m77_lock_evidence(generation: Mapping[str, Any]) -> dict[str, Any]:
    try:
        result = _lock_status(
            Path(str(generation["store_root"])),
            Path(str(generation["generation_path"])),
        )
    except (OSError, KeyError, TypeError, ValueError):
        return {"status": "UNKNOWN", "reason": "LOCK_CHECK_FAILED"}
    return {"status": result.get("status", "UNKNOWN")}


def _m77_open_consumer_evidence(generation: Mapping[str, Any]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    try:
        payloads = generation["payloads"]
    except KeyError:
        return {"status": "UNKNOWN", "reason": "PAYLOAD_LIST_MISSING"}
    if not isinstance(payloads, list) or not payloads:
        return {"status": "UNKNOWN", "reason": "PAYLOAD_LIST_INVALID"}
    for payload in payloads:
        if not isinstance(payload, Mapping):
            return {"status": "UNKNOWN", "reason": "PAYLOAD_LIST_INVALID"}
        try:
            result = _payload_open_consumer_status(
                Path(str(payload["private_artifact_path"]))
            )
        except (OSError, KeyError, TypeError, ValueError):
            return {"status": "UNKNOWN", "reason": "OPEN_CONSUMER_CHECK_FAILED"}
        status_value = str(result.get("status", "UNKNOWN"))
        statuses[status_value] = statuses.get(status_value, 0) + 1
    if "ACTIVE" in statuses:
        status = "ACTIVE"
    elif "UNKNOWN" in statuses:
        status = "UNKNOWN"
    elif set(statuses) == {"NONE"}:
        status = "NONE"
    else:
        status = "UNKNOWN"
    return {"status": status, "status_counts": dict(sorted(statuses.items()))}


def _m77_process_argv_evidence(
    run_ids_by_alias: Mapping[str, str],
) -> dict[str, Any]:
    executable = shutil.which("ps") or "/bin/ps"
    try:
        result = subprocess.run(
            [executable, "-axo", "pid=,command="],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "UNKNOWN", "reason": "PROCESS_SCAN_UNAVAILABLE"}
    if result.returncode != 0:
        return {"status": "UNKNOWN", "reason": "PROCESS_SCAN_FAILED"}
    active_aliases = []
    commands = result.stdout.splitlines()
    for alias, run_id in run_ids_by_alias.items():
        if any(run_id in command for command in commands):
            active_aliases.append(alias)
    return {
        "status": "COMPLETE",
        "active_generation_aliases": sorted(active_aliases),
        "matched_process_count": len(active_aliases),
    }


def _m77_launchd_label_status(label: str) -> dict[str, Any]:
    executable = shutil.which("launchctl")
    if executable is None:
        return {"status": "UNKNOWN", "reason": "LAUNCHD_UNAVAILABLE"}
    try:
        result = subprocess.run(
            [executable, "print", f"gui/{os.getuid()}/{label}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "UNKNOWN", "reason": "LAUNCHD_CHECK_FAILED"}
    if result.returncode != 0:
        return {"status": "NOT_LOADED"}
    if "state = running" in result.stdout:
        return {"status": "ACTIVE"}
    return {"status": "LOADED_NOT_RUNNING"}


def _m77_launchd_labels() -> tuple[str, ...] | None:
    executable = shutil.which("launchctl")
    if executable is None:
        return None
    try:
        result = subprocess.run(
            [executable, "list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None

    labels = set()
    for line in result.stdout.splitlines():
        columns = line.split()
        if len(columns) < 3:
            continue
        label = columns[-1]
        if label.startswith("com.") and label.endswith(_M77_LAUNCHD_LABEL_SUFFIXES):
            labels.add(label)
    return tuple(sorted(labels))


def _m77_launchd_evidence() -> dict[str, Any]:
    labels = _m77_launchd_labels()
    if labels is None:
        return {
            "status": "UNKNOWN",
            "reason": "LAUNCHD_DISCOVERY_FAILED",
            "observed_label_count": 0,
            "active_label_count": 0,
        }
    statuses = {
        label: _m77_launchd_label_status(label)["status"]
        for label in labels
    }
    if any(status == "UNKNOWN" for status in statuses.values()):
        status = "UNKNOWN"
    elif any(status == "ACTIVE" for status in statuses.values()):
        status = "ACTIVE"
    else:
        status = "COMPLETE"
    return {
        "status": status,
        "observed_label_count": len(statuses),
        "active_label_count": sum(1 for value in statuses.values() if value == "ACTIVE"),
    }


def _m77_alias_census_evidence(
    census: Mapping[str, Any] | None,
    *,
    expected_schema: str,
    expected_aliases: Sequence[str],
    label: str,
) -> dict[str, Any]:
    if census is None:
        return {"status": "UNKNOWN", "reason": f"{label}_UNAVAILABLE"}
    try:
        validate_self_hash(census)
        if census["schema"] != expected_schema:
            return {"status": "UNKNOWN", "reason": f"{label}_SCHEMA_UNSUPPORTED"}
        covered = census["covered_generation_aliases"]
        active = census["active_generation_aliases"]
        unknown = census["unknown_generation_aliases"]
        if not all(isinstance(value, list) for value in (covered, active, unknown)):
            return {"status": "UNKNOWN", "reason": f"{label}_MALFORMED"}
        covered_set = set(str(item) for item in covered)
        active_set = set(str(item) for item in active)
        unknown_set = set(str(item) for item in unknown)
        expected_set = set(expected_aliases)
        if covered_set != expected_set:
            return {"status": "UNKNOWN", "reason": f"{label}_INCOMPLETE"}
        if unknown_set:
            return {"status": "UNKNOWN", "reason": f"{label}_UNKNOWN_ALIASES"}
        return {
            "status": "COMPLETE",
            "active_generation_aliases": sorted(active_set & expected_set),
            "covered_generation_count": len(covered_set),
        }
    except (KeyError, TypeError, ValueError):
        return {"status": "UNKNOWN", "reason": f"{label}_INVALID"}


def _m77_reference_evidence(
    private_ledger: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    configured_reference_inputs: Sequence[Path],
) -> dict[str, Any]:
    try:
        failures = private_ledger.get("reference_failures", [])
        if not isinstance(failures, list):
            return {"status": "UNKNOWN", "reason": "REFERENCE_SCAN_INVALID"}
    except (KeyError, TypeError):
        return {"status": "UNKNOWN", "reason": "REFERENCE_SCAN_INVALID"}
    if failures:
        return {"status": "UNKNOWN", "reason": "REFERENCE_SCAN_FAILED"}
    active_aliases = []
    metadata_only_count = 0
    for item in selected:
        alias = str(item["plan_generation_alias"])
        generation = item["generation"]
        payloads = generation.get("payloads")
        if not isinstance(payloads, list):
            return {"status": "UNKNOWN", "reason": "REFERENCE_PAYLOADS_INVALID"}
        for payload in payloads:
            if not isinstance(payload, Mapping):
                return {"status": "UNKNOWN", "reason": "REFERENCE_PAYLOADS_INVALID"}
            if _m74_integer(payload.get("active_reference_count")):
                active_aliases.append(alias)
            metadata_only_count += _m74_integer(
                payload.get("metadata_only_reference_count")
            )
    return {
        "status": "COMPLETE",
        "configured_reference_input_count": len(configured_reference_inputs),
        "active_generation_aliases": sorted(set(active_aliases)),
        "metadata_only_reference_count": metadata_only_count,
    }


def _m77_run_liveness_status(
    *,
    alias: str,
    current: Mapping[str, Any],
    lock: Mapping[str, Any],
    open_consumer: Mapping[str, Any],
    process_evidence: Mapping[str, Any],
    launchd_evidence: Mapping[str, Any],
    task_lease_evidence: Mapping[str, Any],
    reference_evidence: Mapping[str, Any],
    capability_evidence: Mapping[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if current["status"] == "ACTIVE":
        reasons.append("CURRENT_POINTER_OR_CURRENT_MANIFEST_REFERENCE")
    if lock["status"] == "ACTIVE":
        reasons.append("LOCK_HELD")
    if open_consumer["status"] == "ACTIVE":
        reasons.append("OPEN_FILE_HANDLE")
    for evidence, reason in (
        (process_evidence, "PROCESS_ARGV_MATCH"),
        (task_lease_evidence, "CODEX_TASK_LEASE_MATCH"),
        (reference_evidence, "ACTIVE_REFERENCE_MATCH"),
        (capability_evidence, "CAPABILITY_ADOPTION_LIVENESS_MATCH"),
    ):
        if alias in evidence.get("active_generation_aliases", []):
            reasons.append(reason)
    if reasons:
        return "ACTIVE", sorted(set(reasons))
    unknown_sources = []
    for name, evidence in (
        ("current_pointer", current),
        ("lock", lock),
        ("open_consumer", open_consumer),
        ("process_argv", process_evidence),
        ("launchd", launchd_evidence),
        ("codex_task_lease", task_lease_evidence),
        ("reference_inputs", reference_evidence),
        ("capability_adoption", capability_evidence),
    ):
        if evidence.get("status") in {"UNKNOWN", "ACTIVE"}:
            unknown_sources.append(name)
    if unknown_sources:
        return "UNKNOWN", [f"{name.upper()}_NOT_INACTIVE_PROOF" for name in unknown_sources]
    return "INACTIVE_PROVED", ["ALL_REQUIRED_SOURCES_OBSERVED_NO_ACTIVE_BINDING"]


def observe_m77_derived_map_liveness(
    private_ledger: Mapping[str, Any],
    m75_plan: Mapping[str, Any],
    *,
    cohort_aliases: Sequence[str] = _M77_DEFAULT_COHORT_ALIASES,
    expected_cohort_bytes: Mapping[str, tuple[str, int]] | None = (
        _M77_DEFAULT_COHORT_BYTES
    ),
    task_lease_census: Mapping[str, Any] | None = None,
    capability_adoption_liveness: Mapping[str, Any] | None = None,
    configured_reference_inputs: Sequence[Path] = (),
    now: datetime | None = None,
    freshness_seconds: int = _M77_OBSERVATION_FRESHNESS_SECONDS,
) -> dict[str, Any]:
    """Produce a pathless v2 liveness observation for the M77 scoped cohort."""

    try:
        validate_self_hash(private_ledger)
        aggregate = {
            "counts": _m74_private_ledger_counts(private_ledger),
            "classification_counts": _m74_normalised_int_mapping(
                private_ledger["classification_counts"]
            ),
            "classification_bytes": _m74_normalised_int_mapping(
                private_ledger["classification_bytes"]
            ),
            "total_payload_bytes": sum(
                _m74_integer(value)
                for value in private_ledger["classification_bytes"].values()
            ),
        }
        m75_rows = _m77_validate_m75_plan(
            m75_plan,
            aggregate,
            expected_m75_plan_receipt_sha256=None,
        )
        selected = _m77_selected_generation_rows(
            private_ledger,
            m75_rows,
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_cohort_bytes,
        )
        current_time = (now or datetime.now(UTC)).astimezone(UTC)
        if isinstance(freshness_seconds, bool) or freshness_seconds <= 0:
            _raise_m77_liveness_assessment_refusal()
    except (KeyError, TypeError, ValueError) as exc:
        _raise_m77_liveness_assessment_refusal(exc)

    before = _m77_cohort_state_identity(selected)
    run_ids_by_alias = {
        str(item["plan_generation_alias"]): str(item["generation"]["run_id"])
        for item in selected
    }
    process_evidence = _m77_process_argv_evidence(run_ids_by_alias)
    launchd_evidence = _m77_launchd_evidence()
    task_lease_evidence = _m77_alias_census_evidence(
        task_lease_census,
        expected_schema=M77_TASK_LEASE_CENSUS_SCHEMA,
        expected_aliases=cohort_aliases,
        label="CODEX_TASK_LEASE_CENSUS",
    )
    capability_evidence = _m77_alias_census_evidence(
        capability_adoption_liveness,
        expected_schema="giga.archaeology.capability-adoption-liveness-binding.v1",
        expected_aliases=cohort_aliases,
        label="CAPABILITY_ADOPTION_LIVENESS",
    )
    reference_evidence = _m77_reference_evidence(
        private_ledger,
        selected,
        configured_reference_inputs,
    )

    rows: list[dict[str, Any]] = []
    source_completeness = {
        "current_pointer_and_manifest": True,
        "lock_probe": True,
        "open_consumer_probe": True,
        "process_argv_scan": process_evidence.get("status") == "COMPLETE",
        "launchd_labels": launchd_evidence.get("status") == "COMPLETE",
        "codex_task_lease_census": task_lease_evidence.get("status") == "COMPLETE",
        "configured_reference_inputs": reference_evidence.get("status") == "COMPLETE",
        "capability_adoption_liveness": capability_evidence.get("status")
        == "COMPLETE",
    }
    for item in selected:
        alias = str(item["plan_generation_alias"])
        generation = item["generation"]
        current = _m77_current_pointer_evidence(generation)
        lock = _m77_lock_evidence(generation)
        open_consumer = _m77_open_consumer_evidence(generation)
        source_completeness["current_pointer_and_manifest"] = (
            source_completeness["current_pointer_and_manifest"]
            and current.get("status") != "UNKNOWN"
        )
        source_completeness["lock_probe"] = (
            source_completeness["lock_probe"] and lock.get("status") != "UNKNOWN"
        )
        source_completeness["open_consumer_probe"] = (
            source_completeness["open_consumer_probe"]
            and open_consumer.get("status") != "UNKNOWN"
        )
        status, reasons = _m77_run_liveness_status(
            alias=alias,
            current=current,
            lock=lock,
            open_consumer=open_consumer,
            process_evidence=process_evidence,
            launchd_evidence=launchd_evidence,
            task_lease_evidence=task_lease_evidence,
            reference_evidence=reference_evidence,
            capability_evidence=capability_evidence,
        )
        rows.append(
            {
                "generation_alias": alias,
                "kind": generation["kind"],
                "lineage_alias": generation["lineage_alias"],
                "liveness": status,
                "reasons": reasons,
                "current_pointer": {
                    "status": current["status"],
                    "active_reason_count": current.get("active_reason_count", 0),
                },
                "lock_probe": {"status": lock["status"]},
                "open_consumer_probe": {
                    "status": open_consumer["status"],
                    "status_counts": open_consumer.get("status_counts", {}),
                },
            }
        )
    after = _m77_cohort_state_identity(selected)
    if before["private_drift_sha256"] != after["private_drift_sha256"]:
        _raise_m77_liveness_assessment_refusal()
    observed_at = _utc_now(current_time)
    expires_at = _utc_now(current_time + timedelta(seconds=freshness_seconds))
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["liveness"]] = status_counts.get(row["liveness"], 0) + 1
    observation = seal_document(
        {
            "schema": M77_DERIVED_MAP_LIVENESS_OBSERVATION_SCHEMA,
            "status": "FRESH",
            "authority": "read_only_liveness_observation",
            "observed_at": observed_at,
            "expires_at": expires_at,
            "freshness_seconds": freshness_seconds,
            "covered_generation_aliases": list(cohort_aliases),
            "covered_generation_count": len(rows),
            "covered_kind_counts": _m75_payload_status_counts(rows, "kind"),
            "covered_payload_bytes": sum(
                _m74_integer(item["m75_row"]["payload_bytes"]) for item in selected
            ),
            "state_identity": {
                "before_sha256": before["identity_sha256"],
                "after_sha256": after["identity_sha256"],
                "unchanged": True,
                "entry_count": before["entry_count"],
            },
            "source_completeness": source_completeness,
            "shared_sources": {
                "process_argv_scan": {
                    "status": process_evidence["status"],
                    "matched_process_count": process_evidence.get(
                        "matched_process_count", 0
                    ),
                },
                "launchd_labels": launchd_evidence,
                "codex_task_lease_census": {
                    "status": task_lease_evidence["status"],
                    "covered_generation_count": task_lease_evidence.get(
                        "covered_generation_count", 0
                    ),
                },
                "configured_reference_inputs": {
                    "status": reference_evidence["status"],
                    "configured_reference_input_count": reference_evidence.get(
                        "configured_reference_input_count", 0
                    ),
                    "metadata_only_reference_count": reference_evidence.get(
                        "metadata_only_reference_count", 0
                    ),
                },
                "capability_adoption_liveness": {
                    "status": capability_evidence["status"],
                    "covered_generation_count": capability_evidence.get(
                        "covered_generation_count", 0
                    ),
                },
            },
            "liveness_counts": dict(sorted(status_counts.items())),
            "runs": rows,
            "zero_action": {
                "payload_move_delete_quarantine_purge_performed": False,
                "runtime_store_mutation_performed": False,
                "graph_refresh_performed": False,
                "provider_or_browser_action_performed": False,
                "successor_action_performed": False,
            },
        }
    )
    _m77_assert_public_is_pathless(observation)
    return observation


def _m77_validate_observation(
    observation: Mapping[str, Any],
    *,
    cohort_aliases: Sequence[str],
    now: datetime,
) -> dict[str, Mapping[str, Any]]:
    try:
        validate_self_hash(observation)
        if observation["schema"] != M77_DERIVED_MAP_LIVENESS_OBSERVATION_SCHEMA:
            _raise_m77_liveness_assessment_refusal()
        if observation["status"] != "FRESH":
            _raise_m77_liveness_assessment_refusal()
        observed_at = _m77_parse_utc(observation["observed_at"])
        expires_at = _m77_parse_utc(observation["expires_at"])
        freshness_seconds = observation["freshness_seconds"]
        if (
            isinstance(freshness_seconds, bool)
            or not isinstance(freshness_seconds, int)
            or freshness_seconds <= 0
        ):
            _raise_m77_liveness_assessment_refusal()
        expected_expires_at = observed_at + timedelta(seconds=freshness_seconds)
        if expires_at != expected_expires_at:
            _raise_m77_liveness_assessment_refusal()
        if observed_at > now or expires_at < now:
            _raise_m77_liveness_assessment_refusal()
        if tuple(sorted(observation["covered_generation_aliases"])) != tuple(
            sorted(cohort_aliases)
        ):
            _raise_m77_liveness_assessment_refusal()
        if observation["state_identity"]["unchanged"] is not True:
            _raise_m77_liveness_assessment_refusal()
        if (
            observation["state_identity"]["before_sha256"]
            != observation["state_identity"]["after_sha256"]
        ):
            _raise_m77_liveness_assessment_refusal()
        if any(
            observation["zero_action"][key] is not False
            for key in (
                "payload_move_delete_quarantine_purge_performed",
                "runtime_store_mutation_performed",
                "graph_refresh_performed",
                "provider_or_browser_action_performed",
                "successor_action_performed",
            )
        ):
            _raise_m77_liveness_assessment_refusal()
        rows = observation["runs"]
        if not isinstance(rows, list):
            _raise_m77_liveness_assessment_refusal()
    except (KeyError, TypeError, ValueError) as exc:
        _raise_m77_liveness_assessment_refusal(exc)

    by_alias: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            _raise_m77_liveness_assessment_refusal()
        alias = row.get("generation_alias")
        if alias in by_alias or alias not in cohort_aliases:
            _raise_m77_liveness_assessment_refusal()
        if row.get("liveness") not in {"ACTIVE", "INACTIVE_PROVED", "UNKNOWN"}:
            _raise_m77_liveness_assessment_refusal()
        by_alias[str(alias)] = row
    if tuple(sorted(by_alias)) != tuple(sorted(cohort_aliases)):
        _raise_m77_liveness_assessment_refusal()
    _m77_assert_public_is_pathless(observation)
    return by_alias


def _m77_observation_source_projection(
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the source-derived fields that must not be accepted on trust."""

    try:
        rows = observation["runs"]
        if not isinstance(rows, list):
            _raise_m77_liveness_assessment_refusal()
        projected_rows = []
        for row in rows:
            if not isinstance(row, Mapping):
                _raise_m77_liveness_assessment_refusal()
            projected_rows.append(
                {
                    "generation_alias": row["generation_alias"],
                    "kind": row["kind"],
                    "lineage_alias": row["lineage_alias"],
                    "liveness": row["liveness"],
                    "reasons": list(row["reasons"]),
                    "current_pointer": dict(row["current_pointer"]),
                    "lock_probe": dict(row["lock_probe"]),
                    "open_consumer_probe": dict(row["open_consumer_probe"]),
                }
            )
        return {
            "observed_at": observation["observed_at"],
            "expires_at": observation["expires_at"],
            "freshness_seconds": observation["freshness_seconds"],
            "covered_generation_aliases": list(
                observation["covered_generation_aliases"]
            ),
            "covered_generation_count": observation["covered_generation_count"],
            "covered_kind_counts": dict(observation["covered_kind_counts"]),
            "covered_payload_bytes": observation["covered_payload_bytes"],
            "state_identity": dict(observation["state_identity"]),
            "source_completeness": dict(observation["source_completeness"]),
            "shared_sources": {
                "process_argv_scan": dict(
                    observation["shared_sources"]["process_argv_scan"]
                ),
                "launchd_labels": dict(
                    observation["shared_sources"]["launchd_labels"]
                ),
                "codex_task_lease_census": dict(
                    observation["shared_sources"]["codex_task_lease_census"]
                ),
                "configured_reference_inputs": dict(
                    observation["shared_sources"]["configured_reference_inputs"]
                ),
                "capability_adoption_liveness": dict(
                    observation["shared_sources"]["capability_adoption_liveness"]
                ),
            },
            "liveness_counts": dict(observation["liveness_counts"]),
            "runs": sorted(projected_rows, key=lambda row: row["generation_alias"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        _raise_m77_liveness_assessment_refusal(exc)


def _m77_validate_observation_source_binding(
    supplied_observation: Mapping[str, Any],
    source_observation: Mapping[str, Any],
    *,
    cohort_aliases: Sequence[str],
    now: datetime,
) -> dict[str, Mapping[str, Any]]:
    """Bind a supplied public observation to a fresh source-derived projection."""

    _m77_validate_observation(
        supplied_observation,
        cohort_aliases=cohort_aliases,
        now=now,
    )
    source_rows = _m77_validate_observation(
        source_observation,
        cohort_aliases=cohort_aliases,
        now=now,
    )
    supplied_projection = _m77_observation_source_projection(supplied_observation)
    source_projection = _m77_observation_source_projection(source_observation)
    if supplied_projection != source_projection:
        _raise_m77_liveness_assessment_refusal()
    return source_rows


def _m77_assessment_row(
    item: Mapping[str, Any],
    *,
    observation_row: Mapping[str, Any],
    payload_state: Mapping[str, Any],
) -> dict[str, Any]:
    generation = item["generation"]
    m75_row = item["m75_row"]
    blockers: list[str] = []
    protections: list[str] = []
    liveness = str(observation_row["liveness"])
    if liveness == "ACTIVE":
        protections.append("RETAIN_ACTIVE_CONSUMER")
    elif liveness == "UNKNOWN":
        blockers.append("M77_LIVENESS_UNKNOWN")
    if payload_state["status"] != "PASS":
        blockers.append("M77_PAYLOAD_STATE_NOT_PROVED")
    manifest_schema = generation.get("manifest_schema")
    current_status = generation.get("current_status")
    if manifest_schema not in _M75_SUPPORTED_MANIFEST_SCHEMAS:
        blockers.append("UNKNOWN_OR_UNSUPPORTED_SCHEMA")
    if current_status not in _M75_SUPPORTED_GENERATION_STATUSES:
        blockers.append("GENERATION_STATE_UNKNOWN")
    elif current_status in _M75_INCOMPLETE_GENERATION_STATUSES:
        blockers.append("GENERATION_STATE_INCOMPLETE_OR_INDETERMINATE")
    source_reproducibility = generation.get("source_reproducibility")
    if not isinstance(source_reproducibility, Mapping) or (
        source_reproducibility.get("clean_source_reproducible") is not True
    ):
        blockers.append("MISSING_OR_NONREGENERABLE_PROVENANCE")
    if not bool(m75_row.get("stale")):
        classification = "RETAIN_NOT_STALE"
        recommendation = "NO_RETENTION_ACTION_RECOMMENDED"
    elif protections:
        classification = protections[0]
        recommendation = "NO_RETENTION_ACTION_RECOMMENDED"
    elif blockers:
        classification = "UNKNOWN_BLOCKED"
        recommendation = "NO_RETENTION_ACTION_RECOMMENDED"
    else:
        classification = "PAYLOAD_RETIRE_CANDIDATE"
        recommendation = "RECOVERABLE_QUARANTINE_CANDIDATE"
    return {
        "generation_alias": item["plan_generation_alias"],
        "kind": generation["kind"],
        "lineage_alias": generation["lineage_alias"],
        "global_lineage_rank": generation["global_lineage_rank"],
        "stale": bool(m75_row["stale"]),
        "liveness": liveness,
        "payload_state": payload_state["status"],
        "payload_count": m75_row["payload_count"],
        "payload_bytes": m75_row["payload_bytes"],
        "payload_proofs": payload_state["proofs"],
        "protections": protections,
        "blockers": sorted(set(blockers)),
        "classification": classification,
        "recommendation": recommendation,
        "m75_prior_classification": m75_row["classification"],
        "m75_prior_blocker_count": len(m75_row.get("blockers", [])),
    }


def build_m77_scoped_derived_map_liveness_assessment(
    parent_assessment: Mapping[str, Any],
    private_ledger: Mapping[str, Any],
    m74_correction: Mapping[str, Any],
    m75_plan: Mapping[str, Any],
    liveness_observation: Mapping[str, Any],
    *,
    graph_status: Mapping[str, Any],
    cohort_aliases: Sequence[str] = _M77_DEFAULT_COHORT_ALIASES,
    expected_cohort_bytes: Mapping[str, tuple[str, int]] | None = (
        _M77_DEFAULT_COHORT_BYTES
    ),
    now: datetime | None = None,
    expected_m75_plan_receipt_sha256: str | None = (
        _M77_ACCEPTED_M75_PLAN_RECEIPT_SHA256
    ),
    expected_parent_assessment_receipt_sha256: str = (
        _M74_PARENT_ASSESSMENT_RECEIPT_SHA256
    ),
    expected_counts: Mapping[str, int] | None = None,
    expected_byte_class_bytes: Mapping[str, int] | None = None,
    task_lease_census: Mapping[str, Any] | None = None,
    capability_adoption_liveness: Mapping[str, Any] | None = None,
    configured_reference_inputs: Sequence[Path] = (),
) -> dict[str, Any]:
    """Build one M77 no-action liveness assessment for the scoped cohort."""

    try:
        validate_self_hash(parent_assessment)
        validate_self_hash(private_ledger)
        validate_self_hash(m74_correction)
        expected_counts_view = dict(expected_counts or _M74_EXPECTED_COUNTS)
        expected_byte_classes = dict(
            expected_byte_class_bytes or _M74_EXPECTED_BYTE_CLASS_BYTES
        )
        projection_receipt = _m75_validate_m74_correction(
            m74_correction,
            expected_parent_assessment_receipt_sha256=(
                expected_parent_assessment_receipt_sha256
            ),
            expected_counts=expected_counts_view,
            expected_byte_class_bytes=expected_byte_classes,
        )
        aggregate = _m74_validate_assessment_and_private_ledger(
            parent_assessment,
            private_ledger,
            expected_parent_assessment_receipt_sha256=(
                expected_parent_assessment_receipt_sha256
            ),
            expected_counts=expected_counts_view,
            expected_byte_class_bytes=expected_byte_classes,
        )
        payload_bijection = _m75_validate_generation_payload_bijection(
            private_ledger,
            aggregate,
        )
        m75_rows = _m77_validate_m75_plan(
            m75_plan,
            aggregate,
            expected_m75_plan_receipt_sha256=expected_m75_plan_receipt_sha256,
        )
        selected = _m77_selected_generation_rows(
            private_ledger,
            m75_rows,
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_cohort_bytes,
        )
        current_time = (now or datetime.now(UTC)).astimezone(UTC)
        _m77_validate_observation(
            liveness_observation,
            cohort_aliases=cohort_aliases,
            now=current_time,
        )
        observation_time = _m77_parse_utc(liveness_observation["observed_at"])
        source_observation = observe_m77_derived_map_liveness(
            private_ledger,
            m75_plan,
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_cohort_bytes,
            task_lease_census=task_lease_census,
            capability_adoption_liveness=capability_adoption_liveness,
            configured_reference_inputs=configured_reference_inputs,
            now=observation_time,
            freshness_seconds=liveness_observation["freshness_seconds"],
        )
        observed_rows = _m77_validate_observation_source_binding(
            liveness_observation,
            source_observation,
            cohort_aliases=cohort_aliases,
            now=current_time,
        )
    except (KeyError, TypeError, ValueError) as exc:
        _raise_m77_liveness_assessment_refusal(exc)

    rows: list[dict[str, Any]] = []
    for item in selected:
        alias = str(item["plan_generation_alias"])
        payload_state = _m77_payload_state_for_generation(item["generation"])
        rows.append(
            _m77_assessment_row(
                item,
                observation_row=observed_rows[alias],
                payload_state=payload_state,
            )
        )
    class_counts, class_bytes = _m75_summarise_plan(rows)
    candidate_rows = [
        row
        for row in rows
        if row["recommendation"] == "RECOVERABLE_QUARANTINE_CANDIDATE"
    ]
    graph_view = _m77_validate_graph_status(graph_status)
    assessment = seal_document(
        {
            "schema": M77_SCOPED_DERIVED_MAP_LIVENESS_ASSESSMENT_SCHEMA,
            "status": "PENDING_INDEPENDENT_REVIEW",
            "authority": "assessment_and_planning_only",
            "generated_at": _utc_now(current_time),
            "zero_action": {
                "payload_move_delete_quarantine_purge_performed": False,
                "runtime_store_mutation_performed": False,
                "repository_or_history_cleanup_performed": False,
                "graph_refresh_performed": False,
                "provider_or_browser_action_performed": False,
                "successor_action_performed": False,
            },
            "scope": {
                "m77_slice": "SCOPED_DERIVED_MAP_LIVENESS_AND_PAYLOAD_STATE_CANARY",
                "covered_generation_aliases": list(cohort_aliases),
                "covered_generation_count": len(rows),
                "all_other_runs": "UNKNOWN_NOT_ASSESSED_IN_M77",
                "layout_disclosed": False,
                "layout_fingerprint_disclosed": False,
            },
            "graph": graph_view,
            "evidence": {
                "m74_parent_assessment_receipt_sha256": parent_assessment[
                    "receipt_sha256"
                ],
                "m74_ledger_binding_correction_receipt_sha256": (
                    m74_correction["receipt_sha256"]
                ),
                "m74_safe_projection_receipt_sha256": projection_receipt,
                "m75_plan_receipt_sha256": m75_plan["receipt_sha256"],
                "m77_liveness_observation_receipt_sha256": (
                    liveness_observation["receipt_sha256"]
                ),
                "m77_liveness_observation_source_binding": "PASS",
                "m76_parent_commit": "2d5566184135fae6e8acba9ebe4e0abc74861b31",
            },
            "census": {
                "m74_derived_store_family_count": aggregate["counts"][
                    "derived_store_family_count"
                ],
                "m74_metadata_store_family_count": aggregate["counts"][
                    "metadata_store_family_count"
                ],
                "m74_generation_records": aggregate["counts"]["generation_records"],
                "m74_payload_records": aggregate["counts"]["payload_records"],
                "m74_regular_file_bytes": aggregate["counts"]["regular_file_bytes"],
                "m75_generation_records": m75_plan["candidate_plan"][
                    "generation_records"
                ],
                "payload_bijection_status": payload_bijection["status"],
            },
            "liveness_observation": liveness_observation,
            "candidate_plan": {
                "generation_records": len(rows),
                "classification_counts": class_counts,
                "classification_bytes": class_bytes,
                "recoverable_quarantine_candidate_generations": len(candidate_rows),
                "recoverable_quarantine_candidate_payload_bytes": sum(
                    int(row["payload_bytes"]) for row in candidate_rows
                ),
                "consumer_proof_alone_clears_other_blockers": False,
                "all_unassessed_runs_remain_unknown": True,
            },
            "generations": rows,
        }
    )
    _m77_assert_public_is_pathless(assessment)
    return assessment


def render_m77_scoped_derived_map_liveness_report(
    assessment: Mapping[str, Any],
) -> str:
    lines = [
        "# M77 scoped derived map liveness assessment",
        "",
        f"Schema: {assessment['schema']}",
        f"Status: {assessment['status']}",
        "Authority: assessment only. No payload move delete quarantine purge.",
        f"Generated at: {assessment['generated_at']}",
        "",
        "## Scope",
        "",
        f"- Covered generations: {assessment['scope']['covered_generation_count']}",
        f"- Other runs: {assessment['scope']['all_other_runs']}",
        f"- Graph status: {assessment['graph']['reported_status']}",
        "",
        "## Candidate plan",
        "",
        "- Candidate generations: "
        f"{assessment['candidate_plan']['recoverable_quarantine_candidate_generations']}",
        "- Candidate bytes: "
        f"{assessment['candidate_plan']['recoverable_quarantine_candidate_payload_bytes']}",
        "",
        "## Classifications",
        "",
    ]
    for key, value in assessment["candidate_plan"]["classification_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Generations", ""])
    for row in assessment["generations"]:
        lines.append(
            "- "
            f"{row['generation_alias']}: kind={row['kind']}, "
            f"liveness={row['liveness']}, "
            f"classification={row['classification']}, "
            f"bytes={row['payload_bytes']}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Public output omits private layout and path derived identity.",
            "- M78 or separate authority is required before any payload action.",
            "",
        ]
    )
    report = "\n".join(lines)
    if "/" in report or "\\" in report:
        _raise_m77_liveness_assessment_refusal()
    return report


def write_m77_scoped_derived_map_liveness_assessment(
    parent_assessment_path: Path,
    private_ledger_path: Path,
    m74_correction_path: Path,
    m75_plan_path: Path,
    public_output: Path,
    *,
    report_output: Path | None = None,
    graph_status: Mapping[str, Any],
    cohort_aliases: Sequence[str] = _M77_DEFAULT_COHORT_ALIASES,
    expected_cohort_bytes: Mapping[str, tuple[str, int]] | None = (
        _M77_DEFAULT_COHORT_BYTES
    ),
    task_lease_census: Mapping[str, Any] | None = None,
    capability_adoption_liveness: Mapping[str, Any] | None = None,
    configured_reference_inputs: Sequence[Path] = (),
    now: datetime | None = None,
    expected_m75_plan_receipt_sha256: str | None = (
        _M77_ACCEPTED_M75_PLAN_RECEIPT_SHA256
    ),
    expected_parent_assessment_receipt_sha256: str = (
        _M74_PARENT_ASSESSMENT_RECEIPT_SHA256
    ),
    expected_counts: Mapping[str, int] | None = None,
    expected_byte_class_bytes: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Create the M77 public no-action assessment after read-only observation."""

    try:
        parent_assessment = _read_m77_json_read_only(Path(parent_assessment_path))
        validate_self_hash(parent_assessment)
        private_ledger = _read_m74_private_ledger_read_only(Path(private_ledger_path))
        m74_correction = _read_m77_json_read_only(Path(m74_correction_path))
        validate_self_hash(m74_correction)
        m75_plan = _read_m77_json_read_only(Path(m75_plan_path))
        validate_self_hash(m75_plan)
        observation = observe_m77_derived_map_liveness(
            private_ledger,
            m75_plan,
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_cohort_bytes,
            task_lease_census=task_lease_census,
            capability_adoption_liveness=capability_adoption_liveness,
            configured_reference_inputs=configured_reference_inputs,
            now=now,
        )
        assessment = build_m77_scoped_derived_map_liveness_assessment(
            parent_assessment,
            private_ledger,
            m74_correction,
            m75_plan,
            observation,
            graph_status=graph_status,
            cohort_aliases=cohort_aliases,
            expected_cohort_bytes=expected_cohort_bytes,
            now=now,
            expected_m75_plan_receipt_sha256=expected_m75_plan_receipt_sha256,
            expected_parent_assessment_receipt_sha256=(
                expected_parent_assessment_receipt_sha256
            ),
            expected_counts=expected_counts,
            expected_byte_class_bytes=expected_byte_class_bytes,
            task_lease_census=task_lease_census,
            capability_adoption_liveness=capability_adoption_liveness,
            configured_reference_inputs=configured_reference_inputs,
        )
        _write_create_once(Path(public_output), assessment)
        if report_output is not None:
            report = render_m77_scoped_derived_map_liveness_report(assessment)
            write_atomic(Path(report_output), report.encode("utf-8"))
        return assessment
    except (OSError, ValueError, TypeError) as exc:
        _raise_m77_liveness_assessment_refusal(exc)


def _write_create_once(path: Path, payload: Mapping[str, Any]) -> None:
    parent = _private_directory(path.parent, create=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".retention-", dir=parent)
    temp = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        raw = canonical_bytes(payload)
        remaining = memoryview(raw)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise RetentionError("retention evidence write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.link(temp, path, follow_symlinks=False)
        temp.unlink()
        directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except FileExistsError as exc:
        identity = _unavailable_location_label(purpose="retention-evidence")
        raise RetentionError(
            f"retention evidence already exists: {identity}"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temp.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _verify_gzip_content(path: Path, expected_sha256: str, expected_bytes: int) -> None:
    digest = hashlib.sha256()
    total = 0
    try:
        with gzip.open(path, "rb") as handle:
            while chunk := handle.read(1024 * 1024):
                total += len(chunk)
                if total > expected_bytes:
                    raise RetentionError("compressed map expands beyond its binding")
                digest.update(chunk)
    except (OSError, EOFError) as exc:
        raise RetentionError("compressed map database is unreadable") from exc
    if total != expected_bytes or digest.hexdigest() != expected_sha256:
        raise RetentionError("compressed map database does not restore exact bytes")


def verify_compacted_generation_restore_stream(
    kind: str, generation: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Read and hash one complete archive without installing restored bytes."""

    if kind not in {"inventory", "mapper"}:
        raise RetentionError("only inventory and mapper databases are stream-verifiable")
    run = _private_directory(Path(generation))
    manifest_path = run / "manifest.json"
    manifest = _read_json(manifest_path)
    try:
        validate_self_hash(manifest)
    except ValueError as exc:
        raise RetentionError("restore-stream manifest self-hash mismatch") from exc
    if manifest.get("run_id") != run.name:
        raise RetentionError("restore-stream generation identity mismatch")
    receipt = _validate_compaction_receipt(kind, run, manifest)
    if receipt is None:
        raise RetentionError("generation has no authenticated compaction receipt")
    source_path, source_sha256, source_bytes = _database_binding(kind, run, manifest)
    storage = _database_storage_state(kind, run, manifest)
    if storage["compaction_receipt_sha256"] != receipt["receipt_sha256"]:
        raise RetentionError("restore-stream storage state differs from its receipt")
    compressed_path = run / receipt["compressed"]["path"]
    _verify_gzip_content(compressed_path, source_sha256, source_bytes)
    compressed_sha256, compressed_bytes = _file_hash(compressed_path)
    if (
        compressed_sha256 != receipt["compressed"]["sha256"]
        or compressed_bytes != receipt["compressed"]["bytes"]
    ):
        raise RetentionError("compressed map changed during restore-stream verification")
    manifest_sha256, manifest_bytes = _file_hash(manifest_path)
    if (
        manifest_sha256 != sha256_bytes(canonical_bytes(manifest))
        or manifest.get("receipt_sha256")
        != receipt["manifest"]["receipt_sha256"]
    ):
        raise RetentionError("manifest changed during restore-stream verification")
    return seal_document(
        {
            "schema": RETENTION_STREAM_VERIFICATION_SCHEMA,
            "status": "PASS",
            "authority": "read-only-exact-restore-verification",
            "mutation_authority": False,
            "kind": kind,
            "run_id": run.name,
            "generation_path": str(run),
            "verified_at": _utc_now(now),
            "source": {
                "path": source_path.name,
                "sha256": source_sha256,
                "bytes": source_bytes,
            },
            "compressed": dict(receipt["compressed"]),
            "manifest": {
                "path": "manifest.json",
                "sha256": manifest_sha256,
                "bytes": manifest_bytes,
                "receipt_sha256": manifest["receipt_sha256"],
            },
            "compaction_receipt_sha256": receipt["receipt_sha256"],
            "exact_restore_stream_verified": True,
            "raw_database_installed": source_path.exists(),
        }
    )


def write_compacted_generation_restore_verification(
    kind: str,
    generation: Path,
    output: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    verification = verify_compacted_generation_restore_stream(
        kind, generation, now=now
    )
    write_atomic(Path(output), canonical_bytes(verification))
    return verification


def _publish_deterministic_gzip(
    source: Path, destination: Path, *, expected_sha256: str, expected_bytes: int
) -> tuple[str, int]:
    parent = _private_directory(destination.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=".compaction-", dir=parent)
    temp = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as raw_output:
            descriptor = -1
            with source.open("rb") as raw_input:
                with gzip.GzipFile(
                    filename="",
                    mode="wb",
                    compresslevel=9,
                    fileobj=raw_output,
                    mtime=0,
                ) as compressed:
                    shutil.copyfileobj(raw_input, compressed, length=1024 * 1024)
            raw_output.flush()
            os.fsync(raw_output.fileno())
        _verify_gzip_content(temp, expected_sha256, expected_bytes)
        digest, size = _file_hash(temp)
        try:
            os.link(temp, destination, follow_symlinks=False)
        except FileExistsError:
            existing_digest, existing_size = _file_hash(destination)
            if existing_digest != digest or existing_size != size:
                raise RetentionError("pre-existing compressed map differs")
        _fsync_directory(parent)
        return digest, size
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temp.unlink(missing_ok=True)


def _semantic_expected_sources(
    run: Path, manifest: Mapping[str, Any], *, verify_raw: bool
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in _semantic_manifest_artifact_specs(manifest):
        path = _safe_artifact_path(run, spec["relative"], label=spec["role"])
        relative = path.relative_to(run).as_posix()
        digest = spec["digest"]
        size = spec["size"]
        if relative in seen:
            raise RetentionError("semantic manifest repeats an artifact path")
        seen.add(relative)
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size <= 0
        ):
            raise RetentionError("semantic source binding is invalid")
        if verify_raw:
            _bound_artifact(
                run,
                relative=relative,
                digest=digest,
                size=size,
                artifact_class=spec["artifact_class"],
                role=spec["role"],
                bound_by=spec["bound_by"],
            )
            metadata = path.lstat()
            if (
                metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600
            ):
                raise RetentionError("semantic source is not a private mode-0600 file")
        sources.append(
            {
                "path": relative,
                "sha256": digest,
                "bytes": size,
                "mode": 0o600,
                "role": spec["role"],
            }
        )
    return sorted(sources, key=lambda item: item["path"])


def _multi_payload_preserved_artifacts(
    run: Path,
    source_paths: set[str],
    *,
    receipt_name: str = "semantic-compaction.json",
    family: str = "semantic",
) -> list[dict[str, Any]]:
    excluded = {
        receipt_name,
        *(f"{path}.gz" for path in source_paths),
        *source_paths,
    }
    preserved: list[dict[str, Any]] = []
    for path in sorted(run.rglob("*")):
        relative = path.relative_to(run).as_posix()
        metadata = path.lstat()
        if path.is_symlink():
            raise RetentionError(f"{family} generation contains a symlink")
        if stat.S_ISDIR(metadata.st_mode):
            if metadata.st_uid != os.getuid():
                raise RetentionError(
                    f"{family} generation directory has a foreign owner"
                )
            continue
        if relative in excluded:
            continue
        digest, size = _file_hash(path)
        preserved.append(
            {
                "path": relative,
                "sha256": digest,
                "bytes": size,
                "mode": stat.S_IMODE(metadata.st_mode),
            }
        )
    return preserved


def _validate_semantic_compaction_receipt(
    run: Path, manifest: Mapping[str, Any]
) -> dict[str, Any] | None:
    receipt_path = run / "semantic-compaction.json"
    if not receipt_path.exists() and not receipt_path.is_symlink():
        return None
    receipt = _read_json(receipt_path)
    try:
        validate_self_hash(receipt)
    except ValueError as exc:
        raise RetentionError("semantic compaction receipt self-hash mismatch") from exc
    _require_exact_keys(
        receipt,
        {
            "schema",
            "status",
            "kind",
            "run_id",
            "compacted_at",
            "inactive_reason",
            "sources",
            "compressed",
            "manifest",
            "preserved_artifacts",
            "repository_cleanup_authority",
            "receipt_sha256",
        },
        label="semantic compaction receipt",
    )
    expected_sources = _semantic_expected_sources(run, manifest, verify_raw=False)
    source_paths = {item["path"] for item in expected_sources}
    compressed = receipt.get("compressed")
    manifest_binding = receipt.get("manifest")
    if (
        receipt.get("schema") != SEMANTIC_COMPACTION_SCHEMA
        or receipt.get("status") != "COMPRESSED"
        or receipt.get("kind") != "semantic"
        or receipt.get("run_id") != run.name
        or receipt.get("repository_cleanup_authority") is not False
        or not isinstance(receipt.get("compacted_at"), str)
        or not isinstance(receipt.get("inactive_reason"), str)
        or not receipt["inactive_reason"].strip()
        or receipt.get("sources") != expected_sources
        or not isinstance(compressed, list)
        or not isinstance(manifest_binding, Mapping)
        or not isinstance(receipt.get("preserved_artifacts"), list)
    ):
        raise RetentionError("semantic compaction receipt identity differs")
    expected_compressed_paths = {f"{path}.gz" for path in source_paths}
    if len(compressed) != len(expected_sources):
        raise RetentionError("semantic compressed artifact set is incomplete")
    seen_compressed: set[str] = set()
    for source, archive in zip(expected_sources, compressed, strict=True):
        if not isinstance(archive, Mapping):
            raise RetentionError("semantic compressed artifact binding is invalid")
        expected_path = f"{source['path']}.gz"
        if (
            set(archive)
            != {"source_path", "path", "sha256", "bytes", "algorithm"}
            or archive.get("source_path") != source["path"]
            or archive.get("path") != expected_path
            or archive.get("algorithm") != "gzip-9-mtime-zero"
            or not isinstance(archive.get("sha256"), str)
            or len(archive["sha256"]) != 64
            or isinstance(archive.get("bytes"), bool)
            or not isinstance(archive.get("bytes"), int)
            or archive["bytes"] <= 0
            or expected_path in seen_compressed
        ):
            raise RetentionError("semantic compressed artifact binding is invalid")
        seen_compressed.add(expected_path)
        archive_path = _safe_artifact_path(
            run, expected_path, label="semantic compressed artifact"
        )
        metadata = archive_path.lstat()
        if (
            archive_path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise RetentionError("semantic compressed artifact is not private")
        digest, size = _file_hash(archive_path)
        if digest != archive["sha256"] or size != archive["bytes"]:
            raise RetentionError("semantic compressed artifact binding mismatch")
    if seen_compressed != expected_compressed_paths:
        raise RetentionError("semantic compressed artifact set differs")
    manifest_sha256, manifest_bytes = _file_hash(run / "manifest.json")
    if manifest_binding != {
        "path": "manifest.json",
        "sha256": manifest_sha256,
        "bytes": manifest_bytes,
        "receipt_sha256": manifest.get("receipt_sha256"),
    }:
        raise RetentionError("semantic compaction manifest binding mismatch")
    preserved = _multi_payload_preserved_artifacts(run, source_paths)
    if receipt["preserved_artifacts"] != preserved:
        raise RetentionError("semantic preserved artifact set changed")
    return receipt


def _semantic_storage_state(
    run: Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    expected_sources = _semantic_expected_sources(run, manifest, verify_raw=False)
    receipt = _validate_semantic_compaction_receipt(run, manifest)
    raw_present = 0
    for source in expected_sources:
        path = _safe_artifact_path(run, source["path"], label="semantic source")
        if path.exists() or path.is_symlink():
            _bound_artifact(
                run,
                relative=source["path"],
                digest=source["sha256"],
                size=source["bytes"],
                artifact_class="CONTENT_ADDRESSED_JSON_OUTPUT",
                role=source["role"],
                bound_by="manifest.json:graph",
            )
            metadata = path.lstat()
            if (
                metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != source["mode"]
            ):
                raise RetentionError("semantic source is not a private mode-0600 file")
            raw_present += 1
    if raw_present == 0 and receipt is None:
        raise RetentionError("semantic generation has no raw or restorable graph payload")
    if 0 < raw_present < len(expected_sources) and receipt is None:
        raise RetentionError("semantic generation has a partial raw payload")
    return {
        "sources": expected_sources,
        "raw_present": raw_present,
        "raw_complete": raw_present == len(expected_sources),
        "compressed_present": receipt is not None,
        "compaction_receipt_sha256": None
        if receipt is None
        else receipt["receipt_sha256"],
        "compressed": [] if receipt is None else receipt["compressed"],
    }


def _restore_gzip_exact(
    archive: Path, destination: Path, source: Mapping[str, Any]
) -> bool:
    parent = _private_directory(destination.parent)
    if destination.exists() or destination.is_symlink():
        digest, size = _file_hash(destination)
        if digest != source["sha256"] or size != source["bytes"]:
            raise RetentionError("existing semantic restore destination differs")
        metadata = destination.lstat()
        if (
            metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != source["mode"]
        ):
            raise RetentionError("existing semantic restore destination is not private")
        return False
    descriptor, temporary = tempfile.mkstemp(prefix=".semantic-restore-", dir=parent)
    temp = Path(temporary)
    try:
        os.fchmod(descriptor, source["mode"])
        digest = hashlib.sha256()
        total = 0
        with os.fdopen(descriptor, "wb") as output:
            descriptor = -1
            try:
                with gzip.open(archive, "rb") as compressed:
                    while chunk := compressed.read(1024 * 1024):
                        total += len(chunk)
                        if total > source["bytes"]:
                            raise RetentionError(
                                "semantic archive expands beyond its source binding"
                            )
                        digest.update(chunk)
                        output.write(chunk)
            except (OSError, EOFError) as exc:
                raise RetentionError("semantic archive is unreadable") from exc
            output.flush()
            os.fsync(output.fileno())
        if total != source["bytes"] or digest.hexdigest() != source["sha256"]:
            raise RetentionError("semantic archive does not restore exact bytes")
        try:
            os.link(temp, destination, follow_symlinks=False)
        except FileExistsError:
            existing_digest, existing_size = _file_hash(destination)
            if (
                existing_digest != source["sha256"]
                or existing_size != source["bytes"]
            ):
                raise RetentionError("concurrent semantic restore differs")
            return False
        _fsync_directory(parent)
        return True
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temp.unlink(missing_ok=True)


def _semantic_generation_rank(
    semantic_store: Path, run_id: str
) -> tuple[_Store, Path, int]:
    store = _load_store("semantic", Path(semantic_store), 2**63 - 1)
    if store is None:
        raise RetentionError("semantic store has no published generations")
    records = sorted(
        _iter_generation_records(store),
        key=lambda item: (item["finished_at"], item["run_id"]),
        reverse=True,
    )
    by_id = {item["run_id"]: (rank, item) for rank, item in enumerate(records, 1)}
    if run_id not in by_id:
        raise RetentionError("semantic generation is not present in the store")
    rank, item = by_id[run_id]
    run = _private_directory(Path(item["path"]))
    if run.parent != store.runs:
        raise RetentionError("semantic generation path is outside the canonical store")
    return store, run, rank


def compact_inactive_semantic_generation(
    semantic_store: Path,
    run_id: str,
    *,
    inactive_reason: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Losslessly compact one non-current semantic generation outside newest three."""

    run_id = _safe_run_id(run_id)
    if (
        not isinstance(inactive_reason, str)
        or not inactive_reason.strip()
        or len(inactive_reason.encode("utf-8")) > 1024
        or "\x00" in inactive_reason
    ):
        raise RetentionError("inactive semantic generation reason is invalid")
    root = _private_directory(Path(semantic_store))
    retention_root = _private_directory(root / "retention", create=True)
    lock_path = retention_root / "retention.lock"
    lock = lock_path.open("a+b")
    os.chmod(lock_path, 0o600)
    try:
        try:
            lock_file(lock, blocking=False)
        except BlockingIOError as exc:
            raise RetentionError("retention maintenance is already running") from exc
        store, run, rank = _semantic_generation_rank(root, run_id)
        if run_id == store.current_run_id or rank <= 3:
            raise RetentionError("newest three semantic generations must remain raw")
        manifest = _read_json(run / "manifest.json")
        try:
            validate_self_hash(manifest)
        except ValueError as exc:
            raise RetentionError("semantic compaction manifest self-hash mismatch") from exc
        state = _semantic_storage_state(run, manifest)
        receipt = _validate_semantic_compaction_receipt(run, manifest)
        if receipt is not None and receipt["inactive_reason"] != inactive_reason:
            raise RetentionError("semantic compaction reason differs from existing receipt")
        if receipt is None:
            if not state["raw_complete"]:
                raise RetentionError("semantic raw payload is incomplete before compaction")
            sources = _semantic_expected_sources(run, manifest, verify_raw=True)
            source_paths = {item["path"] for item in sources}
            preserved = _multi_payload_preserved_artifacts(run, source_paths)
            archives: list[dict[str, Any]] = []
            for source in sources:
                source_path = _safe_artifact_path(
                    run, source["path"], label="semantic source"
                )
                archive_path = _safe_artifact_path(
                    run, f"{source['path']}.gz", label="semantic archive"
                )
                archive_sha256, archive_bytes = _publish_deterministic_gzip(
                    source_path,
                    archive_path,
                    expected_sha256=source["sha256"],
                    expected_bytes=source["bytes"],
                )
                archives.append(
                    {
                        "source_path": source["path"],
                        "path": f"{source['path']}.gz",
                        "sha256": archive_sha256,
                        "bytes": archive_bytes,
                        "algorithm": "gzip-9-mtime-zero",
                    }
                )
            manifest_sha256, manifest_bytes = _file_hash(run / "manifest.json")
            receipt = seal_document(
                {
                    "schema": SEMANTIC_COMPACTION_SCHEMA,
                    "status": "COMPRESSED",
                    "kind": "semantic",
                    "run_id": run_id,
                    "compacted_at": _utc_now(now),
                    "inactive_reason": inactive_reason,
                    "sources": sources,
                    "compressed": archives,
                    "manifest": {
                        "path": "manifest.json",
                        "sha256": manifest_sha256,
                        "bytes": manifest_bytes,
                        "receipt_sha256": manifest["receipt_sha256"],
                    },
                    "preserved_artifacts": preserved,
                    "repository_cleanup_authority": False,
                }
            )
            _write_create_once(run / "semantic-compaction.json", receipt)
        receipt = _validate_semantic_compaction_receipt(run, manifest)
        if receipt is None:
            raise RetentionError("semantic compaction receipt was not published")
        for source in receipt["sources"]:
            source_path = _safe_artifact_path(
                run, source["path"], label="semantic source"
            )
            if source_path.exists() or source_path.is_symlink():
                digest, size = _file_hash(source_path)
                if digest != source["sha256"] or size != source["bytes"]:
                    raise RetentionError("semantic source changed before removal")
                source_path.unlink()
                _fsync_directory(source_path.parent)
        final_state = _semantic_storage_state(run, manifest)
        if final_state["raw_present"] != 0:
            raise RetentionError("semantic compaction left raw payload bytes")
        compressed_bytes = sum(item["bytes"] for item in receipt["compressed"])
        source_bytes = sum(item["bytes"] for item in receipt["sources"])
        return seal_document(
            {
                "schema": "giga.archaeology.inactive-semantic-compaction.v1",
                "status": "PASS",
                "kind": "semantic",
                "run_id": run_id,
                "generation_rank": rank,
                "generation_path": str(run),
                "inactive_reason": inactive_reason,
                "compaction_receipt_sha256": receipt["receipt_sha256"],
                "source_bytes": source_bytes,
                "compressed_bytes": compressed_bytes,
                "logical_bytes_reclaimed": source_bytes - compressed_bytes,
                "newest_three_raw_protected": True,
                "repository_cleanup_authority": False,
            }
        )
    finally:
        lock.close()


def verify_semantic_compacted_generation_restore_stream(
    generation: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Verify every semantic archive stream without installing source bytes."""

    run = _private_directory(Path(generation))
    manifest = _read_json(run / "manifest.json")
    try:
        validate_self_hash(manifest)
    except ValueError as exc:
        raise RetentionError("semantic verification manifest self-hash mismatch") from exc
    receipt = _validate_semantic_compaction_receipt(run, manifest)
    if receipt is None:
        raise RetentionError("generation has no authenticated semantic compaction")
    for source, archive in zip(
        receipt["sources"], receipt["compressed"], strict=True
    ):
        _verify_gzip_content(
            _safe_artifact_path(run, archive["path"], label="semantic archive"),
            source["sha256"],
            source["bytes"],
        )
    _validate_semantic_compaction_receipt(run, manifest)
    return seal_document(
        {
            "schema": SEMANTIC_STREAM_VERIFICATION_SCHEMA,
            "status": "PASS",
            "authority": "read-only-exact-semantic-restore-verification",
            "mutation_authority": False,
            "kind": "semantic",
            "run_id": run.name,
            "generation_path": str(run),
            "verified_at": _utc_now(now),
            "sources": receipt["sources"],
            "compressed": receipt["compressed"],
            "manifest": receipt["manifest"],
            "preserved_artifacts": receipt["preserved_artifacts"],
            "compaction_receipt_sha256": receipt["receipt_sha256"],
            "exact_restore_stream_verified": True,
            "raw_artifacts_installed": sum(
                int(
                    _safe_artifact_path(run, source["path"], label="semantic source")
                    .exists()
                )
                for source in receipt["sources"]
            ),
        }
    )


def restore_compacted_semantic_generation(
    generation: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Restore every exact semantic source while preserving archives and evidence."""

    run = _private_directory(Path(generation))
    manifest = _read_json(run / "manifest.json")
    try:
        validate_self_hash(manifest)
    except ValueError as exc:
        raise RetentionError("semantic restore manifest self-hash mismatch") from exc
    receipt = _validate_semantic_compaction_receipt(run, manifest)
    if receipt is None:
        raise RetentionError("generation has no authenticated semantic compaction")
    installed: list[str] = []
    for source, archive in zip(
        receipt["sources"], receipt["compressed"], strict=True
    ):
        if _restore_gzip_exact(
            _safe_artifact_path(run, archive["path"], label="semantic archive"),
            _safe_artifact_path(run, source["path"], label="semantic source"),
            source,
        ):
            installed.append(source["path"])
    state = _semantic_storage_state(run, manifest)
    if not state["raw_complete"]:
        raise RetentionError("semantic restore did not recover every source artifact")
    return seal_document(
        {
            "schema": SEMANTIC_RESTORE_SCHEMA,
            "status": "RESTORED" if installed else "ALREADY_RESTORED",
            "kind": "semantic",
            "run_id": run.name,
            "restored_at": _utc_now(now),
            "installed_paths": sorted(installed),
            "archives_preserved": True,
            "compaction_receipt_sha256": receipt["receipt_sha256"],
            "repository_cleanup_authority": False,
        }
    )


def run_semantic_round_trip_canary(
    generation: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Compress and verify real semantic bytes in temporary storage only."""

    run = _private_directory(Path(generation))
    manifest = _read_json(run / "manifest.json")
    try:
        validate_self_hash(manifest)
    except ValueError as exc:
        raise RetentionError("semantic canary manifest self-hash mismatch") from exc
    state = _semantic_storage_state(run, manifest)
    if not state["raw_complete"]:
        raise RetentionError("semantic canary requires complete raw source artifacts")
    sources = _semantic_expected_sources(run, manifest, verify_raw=True)
    before = _tree_record(run)
    archives: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="giga-semantic-round-trip-") as temporary:
        scratch = Path(temporary)
        os.chmod(scratch, 0o700)
        for ordinal, source in enumerate(sources):
            source_path = _safe_artifact_path(
                run, source["path"], label="semantic source"
            )
            archive_path = scratch / f"artifact-{ordinal:02d}.gz"
            digest, size = _publish_deterministic_gzip(
                source_path,
                archive_path,
                expected_sha256=source["sha256"],
                expected_bytes=source["bytes"],
            )
            _verify_gzip_content(archive_path, source["sha256"], source["bytes"])
            archives.append(
                {
                    "source_path": source["path"],
                    "path": f"temporary/artifact-{ordinal:02d}.gz",
                    "sha256": digest,
                    "bytes": size,
                    "algorithm": "gzip-9-mtime-zero",
                }
            )
    after = _tree_record(run)
    if after != before:
        raise RetentionError("semantic canary changed its source generation")
    manifest_sha256, manifest_bytes = _file_hash(run / "manifest.json")
    return seal_document(
        {
            "schema": SEMANTIC_ROUND_TRIP_SCHEMA,
            "status": "PASS",
            "authority": "non-installing-semantic-round-trip-canary",
            "mutation_authority": False,
            "kind": "semantic",
            "run_id": run.name,
            "generation_path": str(run),
            "verified_at": _utc_now(now),
            "sources": sources,
            "compressed": archives,
            "manifest": {
                "path": "manifest.json",
                "sha256": manifest_sha256,
                "bytes": manifest_bytes,
                "receipt_sha256": manifest["receipt_sha256"],
            },
            "source_tree_sha256": before["tree_sha256"],
            "source_tree_bytes": before["bytes"],
            "exact_restore_stream_verified": True,
            "temporary_archives_removed": True,
            "source_generation_unchanged": True,
        }
    )


def write_semantic_round_trip_canary(
    generation: Path, output: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    receipt = run_semantic_round_trip_canary(generation, now=now)
    write_atomic(Path(output), canonical_bytes(receipt))
    return receipt


def write_semantic_restore_stream_verification(
    generation: Path, output: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    receipt = verify_semantic_compacted_generation_restore_stream(
        generation, now=now
    )
    write_atomic(Path(output), canonical_bytes(receipt))
    return receipt


def _validate_scip_compaction_receipt(
    run: Path, catalog: Mapping[str, Any]
) -> dict[str, Any] | None:
    receipt_path = run / "scip-compaction.json"
    if not receipt_path.exists() and not receipt_path.is_symlink():
        return None
    receipt = _read_json(receipt_path)
    try:
        validate_self_hash(receipt)
    except ValueError as exc:
        raise RetentionError("SCIP compaction receipt self-hash mismatch") from exc
    _require_exact_keys(
        receipt,
        {
            "schema",
            "status",
            "kind",
            "run_id",
            "compacted_at",
            "inactive_reason",
            "sources",
            "compressed",
            "catalog",
            "preserved_artifacts",
            "repository_cleanup_authority",
            "receipt_sha256",
        },
        label="SCIP compaction receipt",
    )
    if (
        receipt["schema"] != SCIP_COMPACTION_SCHEMA
        or receipt["status"] != "COMPRESSED"
        or receipt["kind"] != "scip"
        or receipt["run_id"] != run.name
        or receipt["repository_cleanup_authority"] is not False
        or not isinstance(receipt["compacted_at"], str)
        or not isinstance(receipt["inactive_reason"], str)
    ):
        raise RetentionError("SCIP compaction receipt identity differs")
    expected_sources, _manifests = _scip_expected_sources(
        run, catalog, verify_raw=False
    )
    sources = receipt.get("sources")
    compressed = receipt.get("compressed")
    catalog_binding = receipt.get("catalog")
    if (
        sources != expected_sources
        or not isinstance(compressed, list)
        or not isinstance(catalog_binding, Mapping)
        or not isinstance(receipt.get("preserved_artifacts"), list)
    ):
        raise RetentionError("SCIP compaction receipt source identity differs")
    if len(compressed) != len(expected_sources):
        raise RetentionError("SCIP compressed artifact set is incomplete")
    seen: set[str] = set()
    for source, archive in zip(expected_sources, compressed, strict=True):
        expected_path = f"{source['path']}.gz"
        if (
            not isinstance(archive, Mapping)
            or set(archive)
            != {"source_path", "path", "sha256", "bytes", "algorithm"}
            or archive.get("source_path") != source["path"]
            or archive.get("path") != expected_path
            or archive.get("algorithm") != "gzip-9-mtime-zero"
            or not isinstance(archive.get("sha256"), str)
            or len(archive["sha256"]) != 64
            or isinstance(archive.get("bytes"), bool)
            or not isinstance(archive.get("bytes"), int)
            or archive["bytes"] <= 0
            or expected_path in seen
        ):
            raise RetentionError("SCIP compressed artifact binding is invalid")
        seen.add(expected_path)
        archive_path = _safe_artifact_path(
            run, expected_path, label="SCIP compressed artifact"
        )
        metadata = archive_path.lstat()
        if (
            archive_path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise RetentionError("SCIP compressed artifact is not private")
        digest, size = _file_hash(archive_path)
        if digest != archive["sha256"] or size != archive["bytes"]:
            raise RetentionError("SCIP compressed artifact binding mismatch")
    catalog_sha256, catalog_bytes = _file_hash(run / "catalog.json")
    if catalog_binding != {
        "path": "catalog.json",
        "sha256": catalog_sha256,
        "bytes": catalog_bytes,
        "receipt_sha256": catalog.get("receipt_sha256"),
    }:
        raise RetentionError("SCIP compaction catalog binding mismatch")
    source_paths = {item["path"] for item in expected_sources}
    preserved = _multi_payload_preserved_artifacts(
        run,
        source_paths,
        receipt_name="scip-compaction.json",
        family="SCIP",
    )
    if receipt["preserved_artifacts"] != preserved:
        raise RetentionError("SCIP preserved artifact set changed")
    return receipt


def _scip_storage_state(
    run: Path, catalog: Mapping[str, Any]
) -> dict[str, Any]:
    sources, _manifests = _scip_expected_sources(run, catalog, verify_raw=False)
    receipt = _validate_scip_compaction_receipt(run, catalog)
    if not sources:
        if receipt is not None:
            raise RetentionError("empty SCIP generation has a compaction receipt")
        return {
            "sources": [],
            "raw_present": 0,
            "raw_complete": True,
            "compressed_present": False,
            "compaction_receipt_sha256": None,
            "compressed": [],
        }
    raw_present = 0
    for source in sources:
        path = _safe_artifact_path(run, source["path"], label="SCIP index")
        if path.exists() or path.is_symlink():
            _bound_artifact(
                run,
                relative=source["path"],
                digest=source["sha256"],
                size=source["bytes"],
                artifact_class=source["artifact_class"],
                role=source["role"],
                bound_by=source["bound_by"],
            )
            metadata = path.lstat()
            if (
                metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != source["mode"]
            ):
                raise RetentionError("SCIP index is not a private mode-0600 file")
            raw_present += 1
    if raw_present == 0 and receipt is None:
        raise RetentionError("SCIP generation has no raw or restorable index payload")
    if 0 < raw_present < len(sources) and receipt is None:
        raise RetentionError("SCIP generation has a partial raw payload")
    return {
        "sources": sources,
        "raw_present": raw_present,
        "raw_complete": raw_present == len(sources),
        "compressed_present": receipt is not None,
        "compaction_receipt_sha256": None
        if receipt is None
        else receipt["receipt_sha256"],
        "compressed": [] if receipt is None else receipt["compressed"],
    }


def _scip_generation_rank(scip_store: Path, run_id: str) -> tuple[_Store, Path, int]:
    store = _load_store("scip", Path(scip_store), 2**63 - 1)
    if store is None:
        raise RetentionError("SCIP store has no published generations")
    records = sorted(
        _iter_generation_records(store),
        key=lambda item: (item["finished_at"], item["run_id"]),
        reverse=True,
    )
    by_id = {item["run_id"]: rank for rank, item in enumerate(records, 1)}
    if run_id not in by_id:
        raise RetentionError("SCIP generation is not present in the store")
    run = _private_directory(store.runs / run_id)
    return store, run, by_id[run_id]


def compact_inactive_scip_generation(
    scip_store: Path,
    run_id: str,
    *,
    inactive_reason: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Losslessly compact one inactive SCIP generation outside newest three."""

    run_id = _safe_run_id(run_id)
    if (
        not isinstance(inactive_reason, str)
        or not inactive_reason.strip()
        or len(inactive_reason.encode("utf-8")) > 1024
        or "\x00" in inactive_reason
    ):
        raise RetentionError("inactive SCIP generation reason is invalid")
    root = _private_directory(Path(scip_store))
    retention_root = _private_directory(root / "retention", create=True)
    lock_path = retention_root / "retention.lock"
    lock = lock_path.open("a+b")
    os.chmod(lock_path, 0o600)
    try:
        try:
            lock_file(lock, blocking=False)
        except BlockingIOError as exc:
            raise RetentionError("retention maintenance is already running") from exc
        store, run, rank = _scip_generation_rank(root, run_id)
        if run_id == store.current_run_id or rank <= 3:
            raise RetentionError("newest three SCIP generations must remain raw")
        catalog = _read_json(run / "catalog.json")
        try:
            validate_self_hash(catalog)
        except ValueError as exc:
            raise RetentionError("SCIP compaction catalog self-hash mismatch") from exc
        state = _scip_storage_state(run, catalog)
        receipt = _validate_scip_compaction_receipt(run, catalog)
        if receipt is not None and receipt["inactive_reason"] != inactive_reason:
            raise RetentionError("SCIP compaction reason differs from existing receipt")
        if receipt is None:
            if not state["raw_complete"]:
                raise RetentionError("SCIP raw payload is incomplete before compaction")
            sources, _manifests = _scip_expected_sources(
                run, catalog, verify_raw=True
            )
            source_paths = {item["path"] for item in sources}
            preserved = _multi_payload_preserved_artifacts(
                run,
                source_paths,
                receipt_name="scip-compaction.json",
                family="SCIP",
            )
            archives: list[dict[str, Any]] = []
            for source in sources:
                source_path = _safe_artifact_path(
                    run, source["path"], label="SCIP source"
                )
                archive_path = _safe_artifact_path(
                    run, f"{source['path']}.gz", label="SCIP archive"
                )
                archive_sha256, archive_bytes = _publish_deterministic_gzip(
                    source_path,
                    archive_path,
                    expected_sha256=source["sha256"],
                    expected_bytes=source["bytes"],
                )
                archives.append(
                    {
                        "source_path": source["path"],
                        "path": f"{source['path']}.gz",
                        "sha256": archive_sha256,
                        "bytes": archive_bytes,
                        "algorithm": "gzip-9-mtime-zero",
                    }
                )
            catalog_sha256, catalog_bytes = _file_hash(run / "catalog.json")
            receipt = seal_document(
                {
                    "schema": SCIP_COMPACTION_SCHEMA,
                    "status": "COMPRESSED",
                    "kind": "scip",
                    "run_id": run_id,
                    "compacted_at": _utc_now(now),
                    "inactive_reason": inactive_reason,
                    "sources": sources,
                    "compressed": archives,
                    "catalog": {
                        "path": "catalog.json",
                        "sha256": catalog_sha256,
                        "bytes": catalog_bytes,
                        "receipt_sha256": catalog["receipt_sha256"],
                    },
                    "preserved_artifacts": preserved,
                    "repository_cleanup_authority": False,
                }
            )
            _write_create_once(run / "scip-compaction.json", receipt)
        receipt = _validate_scip_compaction_receipt(run, catalog)
        if receipt is None:
            raise RetentionError("SCIP compaction receipt was not published")
        for source in receipt["sources"]:
            source_path = _safe_artifact_path(
                run, source["path"], label="SCIP source"
            )
            if source_path.exists() or source_path.is_symlink():
                digest, size = _file_hash(source_path)
                if digest != source["sha256"] or size != source["bytes"]:
                    raise RetentionError("SCIP source changed before removal")
                source_path.unlink()
                _fsync_directory(source_path.parent)
        final_state = _scip_storage_state(run, catalog)
        if final_state["raw_present"] != 0:
            raise RetentionError("SCIP compaction left raw payload bytes")
        source_bytes = sum(item["bytes"] for item in receipt["sources"])
        compressed_bytes = sum(item["bytes"] for item in receipt["compressed"])
        return seal_document(
            {
                "schema": "giga.archaeology.inactive-scip-compaction.v1",
                "status": "PASS",
                "kind": "scip",
                "run_id": run_id,
                "generation_rank": rank,
                "generation_path": str(run),
                "inactive_reason": inactive_reason,
                "compaction_receipt_sha256": receipt["receipt_sha256"],
                "source_bytes": source_bytes,
                "compressed_bytes": compressed_bytes,
                "logical_bytes_reclaimed": source_bytes - compressed_bytes,
                "newest_three_raw_protected": True,
                "repository_cleanup_authority": False,
            }
        )
    finally:
        lock.close()


def verify_scip_compacted_generation_restore_stream(
    generation: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Verify every SCIP archive without installing an index."""

    run = _private_directory(Path(generation))
    catalog = _read_json(run / "catalog.json")
    try:
        validate_self_hash(catalog)
    except ValueError as exc:
        raise RetentionError("SCIP verification catalog self-hash mismatch") from exc
    receipt = _validate_scip_compaction_receipt(run, catalog)
    if receipt is None:
        raise RetentionError("generation has no authenticated SCIP compaction")
    for source, archive in zip(
        receipt["sources"], receipt["compressed"], strict=True
    ):
        _verify_gzip_content(
            _safe_artifact_path(run, archive["path"], label="SCIP archive"),
            source["sha256"],
            source["bytes"],
        )
    _validate_scip_compaction_receipt(run, catalog)
    return seal_document(
        {
            "schema": SCIP_STREAM_VERIFICATION_SCHEMA,
            "status": "PASS",
            "authority": "read-only-exact-scip-restore-verification",
            "mutation_authority": False,
            "kind": "scip",
            "run_id": run.name,
            "generation_path": str(run),
            "verified_at": _utc_now(now),
            "sources": receipt["sources"],
            "compressed": receipt["compressed"],
            "catalog": receipt["catalog"],
            "preserved_artifacts": receipt["preserved_artifacts"],
            "compaction_receipt_sha256": receipt["receipt_sha256"],
            "exact_restore_stream_verified": True,
            "raw_artifacts_installed": sum(
                int(
                    _safe_artifact_path(run, source["path"], label="SCIP index").exists()
                )
                for source in receipt["sources"]
            ),
        }
    )


def restore_compacted_scip_generation(
    generation: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Restore exact SCIP indexes while preserving archives and evidence."""

    run = _private_directory(Path(generation))
    catalog = _read_json(run / "catalog.json")
    try:
        validate_self_hash(catalog)
    except ValueError as exc:
        raise RetentionError("SCIP restore catalog self-hash mismatch") from exc
    receipt = _validate_scip_compaction_receipt(run, catalog)
    if receipt is None:
        raise RetentionError("generation has no authenticated SCIP compaction")
    installed: list[str] = []
    for source, archive in zip(
        receipt["sources"], receipt["compressed"], strict=True
    ):
        if _restore_gzip_exact(
            _safe_artifact_path(run, archive["path"], label="SCIP archive"),
            _safe_artifact_path(run, source["path"], label="SCIP index"),
            source,
        ):
            installed.append(source["path"])
    state = _scip_storage_state(run, catalog)
    if not state["raw_complete"]:
        raise RetentionError("SCIP restore did not recover every index")
    return seal_document(
        {
            "schema": SCIP_RESTORE_SCHEMA,
            "status": "RESTORED" if installed else "ALREADY_RESTORED",
            "kind": "scip",
            "run_id": run.name,
            "restored_at": _utc_now(now),
            "installed_paths": sorted(installed),
            "archives_preserved": True,
            "compaction_receipt_sha256": receipt["receipt_sha256"],
            "repository_cleanup_authority": False,
        }
    )


def run_scip_round_trip_canary(
    generation: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Compress and verify real SCIP index bytes in temporary storage only."""

    run = _private_directory(Path(generation))
    catalog = _read_json(run / "catalog.json")
    try:
        validate_self_hash(catalog)
    except ValueError as exc:
        raise RetentionError("SCIP canary catalog self-hash mismatch") from exc
    state = _scip_storage_state(run, catalog)
    if not state["raw_complete"]:
        raise RetentionError("SCIP canary requires complete raw index payloads")
    sources, _manifests = _scip_expected_sources(run, catalog, verify_raw=True)
    before = _tree_record(run)
    archives: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="giga-scip-round-trip-") as temporary:
        scratch = Path(temporary)
        os.chmod(scratch, 0o700)
        for ordinal, source in enumerate(sources):
            source_path = _safe_artifact_path(
                run, source["path"], label="SCIP source"
            )
            archive_path = scratch / f"artifact-{ordinal:02d}.gz"
            digest, size = _publish_deterministic_gzip(
                source_path,
                archive_path,
                expected_sha256=source["sha256"],
                expected_bytes=source["bytes"],
            )
            _verify_gzip_content(archive_path, source["sha256"], source["bytes"])
            archives.append(
                {
                    "source_path": source["path"],
                    "path": f"temporary/artifact-{ordinal:02d}.gz",
                    "sha256": digest,
                    "bytes": size,
                    "algorithm": "gzip-9-mtime-zero",
                }
            )
    after = _tree_record(run)
    if after != before:
        raise RetentionError("SCIP canary changed its source generation")
    catalog_sha256, catalog_bytes = _file_hash(run / "catalog.json")
    return seal_document(
        {
            "schema": SCIP_ROUND_TRIP_SCHEMA,
            "status": "PASS",
            "authority": "non-installing-scip-round-trip-canary",
            "mutation_authority": False,
            "kind": "scip",
            "run_id": run.name,
            "generation_path": str(run),
            "verified_at": _utc_now(now),
            "sources": sources,
            "compressed": archives,
            "catalog": {
                "path": "catalog.json",
                "sha256": catalog_sha256,
                "bytes": catalog_bytes,
                "receipt_sha256": catalog["receipt_sha256"],
            },
            "source_tree_sha256": before["tree_sha256"],
            "source_tree_bytes": before["bytes"],
            "exact_restore_stream_verified": True,
            "temporary_archives_removed": True,
            "source_generation_unchanged": True,
        }
    )


def write_scip_round_trip_canary(
    generation: Path, output: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    receipt = run_scip_round_trip_canary(generation, now=now)
    write_atomic(Path(output), canonical_bytes(receipt))
    return receipt


def write_scip_restore_stream_verification(
    generation: Path, output: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    receipt = verify_scip_compacted_generation_restore_stream(
        generation, now=now
    )
    write_atomic(Path(output), canonical_bytes(receipt))
    return receipt


def _compact_generation(
    item: Mapping[str, Any], *, compacted_at: datetime
) -> dict[str, Any]:
    kind = item["kind"]
    if kind not in {"inventory", "mapper"}:
        raise RetentionError("only map databases can be compacted")
    run = _private_directory(Path(item["path"]))
    manifest = _read_json(run / "manifest.json")
    try:
        validate_self_hash(manifest)
    except ValueError as exc:
        raise RetentionError("compaction manifest self-hash mismatch") from exc
    raw_path, raw_sha256, raw_bytes = _database_binding(kind, run, manifest)
    compressed_path = run / f"{raw_path.name}.gz"
    receipt_path = run / "compaction.json"
    existing_receipt = _validate_compaction_receipt(kind, run, manifest)
    if not raw_path.exists() and not raw_path.is_symlink():
        if existing_receipt is None:
            raise RetentionError("compaction lost the raw database before receipt")
        return existing_receipt
    storage = _database_storage_state(kind, run, manifest)
    if storage["raw_sha256"] != raw_sha256 or storage["raw_bytes"] != raw_bytes:
        raise RetentionError("compaction source changed after planning")
    if existing_receipt is None:
        compressed_sha256, compressed_bytes = _publish_deterministic_gzip(
            raw_path,
            compressed_path,
            expected_sha256=raw_sha256,
            expected_bytes=raw_bytes,
        )
        manifest_sha256, manifest_bytes = _file_hash(run / "manifest.json")
        receipt = seal_document(
            {
                "schema": RETENTION_COMPACTION_SCHEMA,
                "status": "COMPRESSED",
                "kind": kind,
                "run_id": run.name,
                "compacted_at": _utc_now(compacted_at),
                "source": {
                    "path": raw_path.name,
                    "sha256": raw_sha256,
                    "bytes": raw_bytes,
                    "mode": 0o600,
                },
                "compressed": {
                    "path": compressed_path.name,
                    "sha256": compressed_sha256,
                    "bytes": compressed_bytes,
                    "algorithm": "gzip-9-mtime-zero",
                },
                "manifest": {
                    "path": "manifest.json",
                    "sha256": manifest_sha256,
                    "bytes": manifest_bytes,
                    "receipt_sha256": manifest.get("receipt_sha256"),
                },
                "repository_cleanup_authority": False,
            }
        )
        _write_create_once(receipt_path, receipt)
        existing_receipt = _validate_compaction_receipt(kind, run, manifest)
    if existing_receipt is None:
        raise RetentionError("compaction receipt was not durably published")
    _verify_gzip_content(compressed_path, raw_sha256, raw_bytes)
    digest, size = _file_hash(raw_path)
    if digest != raw_sha256 or size != raw_bytes:
        raise RetentionError("raw map changed before compaction unlink")
    raw_path.unlink()
    _fsync_directory(run)
    receipt_bytes = (run / "compaction.json").stat().st_size
    return {
        **existing_receipt,
        "logical_bytes_reclaimed": max(
            0,
            raw_bytes - existing_receipt["compressed"]["bytes"] - receipt_bytes,
        ),
    }


def restore_compacted_generation(kind: str, generation: Path) -> dict[str, Any]:
    """Restore one compacted map database exactly for a native historical query."""

    if kind not in {"inventory", "mapper"}:
        raise RetentionError("only inventory and mapper databases are restorable")
    run = _private_directory(Path(generation))
    manifest = _read_json(run / "manifest.json")
    try:
        validate_self_hash(manifest)
    except ValueError as exc:
        raise RetentionError("restore manifest self-hash mismatch") from exc
    raw_path, raw_sha256, raw_bytes = _database_binding(kind, run, manifest)
    receipt = _validate_compaction_receipt(kind, run, manifest)
    if receipt is None:
        raise RetentionError("generation has no authenticated compaction receipt")
    if raw_path.exists() or raw_path.is_symlink():
        storage = _database_storage_state(kind, run, manifest)
        if not storage["raw_present"]:
            raise RetentionError("restored database state is inconsistent")
        status = "ALREADY_RESTORED"
    else:
        compressed_path = run / receipt["compressed"]["path"]
        descriptor, temporary = tempfile.mkstemp(prefix=".restore-", dir=run)
        temp = Path(temporary)
        try:
            os.fchmod(descriptor, 0o600)
            digest = hashlib.sha256()
            total = 0
            with os.fdopen(descriptor, "wb") as output:
                descriptor = -1
                with gzip.open(compressed_path, "rb") as source:
                    while chunk := source.read(1024 * 1024):
                        total += len(chunk)
                        if total > raw_bytes:
                            raise RetentionError(
                                "compressed map expands beyond its binding"
                            )
                        digest.update(chunk)
                        output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if total != raw_bytes or digest.hexdigest() != raw_sha256:
                raise RetentionError("restored map database identity mismatch")
            try:
                os.link(temp, raw_path, follow_symlinks=False)
            except FileExistsError:
                existing_digest, existing_size = _file_hash(raw_path)
                if existing_digest != raw_sha256 or existing_size != raw_bytes:
                    raise RetentionError("concurrent restored database differs")
            _fsync_directory(run)
            status = "RESTORED"
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temp.unlink(missing_ok=True)
    return seal_document(
        {
            "schema": "giga.archaeologist.retention-restore-result.v1",
            "status": status,
            "kind": kind,
            "run_id": run.name,
            "source": receipt["source"],
            "compaction_receipt_sha256": receipt["receipt_sha256"],
            "repository_cleanup_authority": False,
        }
    )


def compact_inactive_generation(
    kind: str,
    generation: Path,
    *,
    inactive_reason: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compact an explicitly retired map runtime while preserving exact restore.

    This entrypoint does not infer liveness or retirement.  Its caller must bind
    an exact inactive generation and a truthful reason; the function only owns
    the lossless storage transition for that already-classified derived map.
    """

    if kind not in {"inventory", "mapper"}:
        raise RetentionError("only inventory and mapper generations are compactable")
    if (
        not isinstance(inactive_reason, str)
        or not inactive_reason.strip()
        or len(inactive_reason.encode("utf-8")) > 1024
        or "\x00" in inactive_reason
    ):
        raise RetentionError("inactive generation reason is invalid")
    run = _private_directory(Path(generation))
    compaction = _compact_generation(
        {"kind": kind, "path": str(run), "run_id": run.name},
        compacted_at=(now or datetime.now(UTC)).astimezone(UTC),
    )
    return seal_document(
        {
            "schema": "giga.archaeologist.inactive-generation-compaction.v1",
            "status": "PASS",
            "kind": kind,
            "run_id": run.name,
            "generation_path": str(run),
            "inactive_reason": inactive_reason,
            "compaction_receipt_sha256": compaction["receipt_sha256"],
            "source_bytes": compaction["source"]["bytes"],
            "compressed_bytes": compaction["compressed"]["bytes"],
            "logical_bytes_reclaimed": compaction.get("logical_bytes_reclaimed", 0),
            "repository_cleanup_authority": False,
        }
    )


def _candidate_records(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        generation
        for store in plan["stores"]
        for generation in store["generations"]
        if generation["disposition"] == "QUARANTINE_CANDIDATE"
    ]


def _compaction_candidate_records(
    plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        generation
        for store in plan["stores"]
        for generation in store["generations"]
        if generation["compaction_disposition"]
        in {"COMPACT_CANDIDATE", "FINISH_INTERRUPTED_COMPACTION"}
    ]


def _quarantine(
    retention_root: Path,
    plan: Mapping[str, Any],
    *,
    batch_id: str,
    now: datetime,
) -> dict[str, Any]:
    candidates = _candidate_records(plan)
    batch = retention_root / "quarantine" / batch_id
    batch.mkdir(parents=True, mode=0o700)
    intent = seal_document(
        {
            "schema": RETENTION_INTENT_SCHEMA,
            "status": "INTENT",
            "batch_id": batch_id,
            "created_at": _utc_now(now),
            "plan_receipt_sha256": plan["receipt_sha256"],
            "candidates": candidates,
        }
    )
    _write_create_once(batch / "intent.json", intent)
    moved: list[dict[str, Any]] = []
    try:
        for item in candidates:
            source = Path(item["path"])
            destination = batch / item["kind"] / item["run_id"]
            _private_directory(destination.parent, create=True)
            if destination.exists() or destination.is_symlink():
                raise RetentionError("quarantine destination already exists")
            if _tree_record(source)["tree_sha256"] != item["tree_sha256"]:
                raise RetentionError("candidate generation changed after planning")
            if source.parent.stat().st_dev != destination.parent.stat().st_dev:
                raise RetentionError("quarantine must remain on the source filesystem")
            os.rename(source, destination)
            if _tree_record(destination)["tree_sha256"] != item["tree_sha256"]:
                raise RetentionError("quarantined generation identity mismatch")
            moved.append({**item, "quarantine_path": str(destination)})
    except BaseException as exc:
        for item in reversed(moved):
            source = Path(item["path"])
            destination = Path(item["quarantine_path"])
            if destination.exists() and not source.exists():
                os.rename(destination, source)
        rejected = seal_document(
            {
                "schema": RETENTION_OUTCOME_SCHEMA,
                "status": "ROLLED_BACK",
                "batch_id": batch_id,
                "finished_at": _utc_now(now),
                "intent_receipt_sha256": intent["receipt_sha256"],
                "generations": moved,
                "bytes": 0,
                "error": {"type": type(exc).__name__, "reason": str(exc)[-4000:]},
            }
        )
        _write_create_once(batch / "outcome.json", rejected)
        raise
    outcome = seal_document(
        {
            "schema": RETENTION_OUTCOME_SCHEMA,
            "status": "QUARANTINED",
            "batch_id": batch_id,
            "finished_at": _utc_now(now),
            "intent_receipt_sha256": intent["receipt_sha256"],
            "generations": moved,
            "bytes": sum(item["bytes"] for item in moved),
        }
    )
    _write_create_once(batch / "outcome.json", outcome)
    return outcome


def _recover_incomplete_quarantines(retention_root: Path) -> list[dict[str, Any]]:
    """Roll back a crash that published intent but no terminal outcome."""

    quarantine = retention_root / "quarantine"
    if not quarantine.exists():
        return []
    recovered: list[dict[str, Any]] = []
    for batch in sorted(quarantine.iterdir()):
        if not batch.is_dir() or batch.is_symlink():
            raise RetentionError("unsafe retention quarantine entry")
        intent_path = batch / "intent.json"
        outcome_path = batch / "outcome.json"
        if not intent_path.is_file() or outcome_path.exists():
            continue
        intent = _read_json(intent_path)
        validate_self_hash(intent)
        restored: list[dict[str, Any]] = []
        for item in reversed(intent["candidates"]):
            source = Path(item["path"])
            destination = batch / item["kind"] / item["run_id"]
            source_exists = source.exists() or source.is_symlink()
            destination_exists = destination.exists() or destination.is_symlink()
            if source_exists and destination_exists:
                raise RetentionError(
                    "interrupted quarantine has duplicate source and destination"
                )
            if not source_exists and not destination_exists:
                raise RetentionError(
                    "interrupted quarantine lost a candidate generation"
                )
            if destination_exists:
                if _tree_record(destination)["tree_sha256"] != item["tree_sha256"]:
                    raise RetentionError(
                        "interrupted quarantine candidate identity mismatch"
                    )
                _private_directory(source.parent)
                os.rename(destination, source)
                restored.append(item)
        outcome = seal_document(
            {
                "schema": RETENTION_OUTCOME_SCHEMA,
                "status": "ROLLED_BACK_INTERRUPTED",
                "batch_id": intent["batch_id"],
                "finished_at": _utc_now(),
                "intent_receipt_sha256": intent["receipt_sha256"],
                "generations": restored,
                "bytes": 0,
                "error": {
                    "type": "InterruptedQuarantine",
                    "reason": "intent existed without a terminal outcome",
                },
            }
        )
        _write_create_once(outcome_path, outcome)
        recovered.append(outcome)
    return recovered


def _preserve_failure_receipt(
    retention_root: Path, item: Mapping[str, Any], source: Path
) -> dict[str, Any]:
    raw = source.read_bytes()
    destination = retention_root / "failure-receipts" / f"{item['run_id']}.json"
    if destination.exists() or destination.is_symlink():
        digest, size = _file_hash(destination)
        if digest != sha256_bytes(raw) or size != len(raw):
            raise RetentionError("preserved semantic failure receipt identity mismatch")
    else:
        _write_create_once(destination, json.loads(raw))
    return {
        "run_id": item["run_id"],
        "path": str(destination),
        "sha256": sha256_bytes(raw),
    }


def _purge_ready(
    retention_root: Path,
    *,
    policy: RetentionPolicy,
    external_reference_roots: Sequence[Path],
    now: datetime,
) -> list[dict[str, Any]]:
    quarantine = retention_root / "quarantine"
    if not quarantine.exists():
        return []
    results: list[dict[str, Any]] = []
    for batch in sorted(quarantine.iterdir()):
        if not batch.is_dir() or batch.is_symlink():
            raise RetentionError("unsafe retention quarantine entry")
        intent = _read_json(batch / "intent.json")
        outcome = _read_json(batch / "outcome.json")
        validate_self_hash(intent)
        validate_self_hash(outcome)
        if outcome.get("intent_receipt_sha256") != intent.get("receipt_sha256"):
            raise RetentionError("quarantine intent/outcome binding mismatch")
        if outcome.get("status") != "QUARANTINED":
            continue
        if (batch / "rollback.json").exists():
            rollback = _read_json(batch / "rollback.json")
            validate_self_hash(rollback)
            continue
        if (batch / "purge.json").exists():
            continue
        finished = datetime.fromisoformat(outcome["finished_at"].replace("Z", "+00:00"))
        if (now - finished).total_seconds() < policy.quarantine_grace_seconds:
            continue
        run_ids = [item["run_id"] for item in outcome["generations"]]
        references, failures = _external_references(run_ids, external_reference_roots)
        if failures or references:
            continue
        rolled_back = [
            item
            for item in outcome["generations"]
            if Path(item["path"]).exists() or Path(item["path"]).is_symlink()
        ]
        if rolled_back:
            for item in reversed(outcome["generations"]):
                source = Path(item["path"])
                destination = Path(item["quarantine_path"])
                if source.exists() or source.is_symlink():
                    if destination.exists() or destination.is_symlink():
                        raise RetentionError(
                            "rolled-back quarantine has duplicate source and destination"
                        )
                    continue
                if not destination.exists() or destination.is_symlink():
                    raise RetentionError("rolled-back quarantine lost a generation")
                if _tree_record(destination)["tree_sha256"] != item["tree_sha256"]:
                    raise RetentionError("rolled-back quarantine identity mismatch")
                os.rename(destination, source)
            rollback = seal_document(
                {
                    "schema": RETENTION_OUTCOME_SCHEMA,
                    "status": "ROLLED_BACK_RECOVERED",
                    "batch_id": outcome["batch_id"],
                    "finished_at": _utc_now(now),
                    "quarantine_outcome_receipt_sha256": outcome["receipt_sha256"],
                }
            )
            if not (batch / "rollback.json").exists():
                _write_create_once(batch / "rollback.json", rollback)
            continue
        preserved_failures: list[dict[str, Any]] = []
        deleted: list[dict[str, Any]] = []
        for item in outcome["generations"]:
            path = Path(item["quarantine_path"])
            if not path.exists() and not path.is_symlink():
                deleted.append({**item, "recovered_already_absent": True})
                continue
            if _tree_record(path)["tree_sha256"] != item["tree_sha256"]:
                raise RetentionError("quarantine changed before purge")
            if item["kind"] == "semantic_failure" and (path / "failure.json").is_file():
                preserved_failures.append(
                    _preserve_failure_receipt(
                        retention_root, item, path / "failure.json"
                    )
                )
            shutil.rmtree(path)
            deleted.append({**item, "recovered_already_absent": False})
        purge = seal_document(
            {
                "schema": RETENTION_PURGE_SCHEMA,
                "status": "PURGED",
                "batch_id": outcome["batch_id"],
                "purged_at": _utc_now(now),
                "outcome_receipt_sha256": outcome["receipt_sha256"],
                "deleted": deleted,
                "preserved_failure_receipts": preserved_failures,
                "bytes_reclaimed": sum(item["bytes"] for item in deleted),
            }
        )
        _write_create_once(batch / "purge.json", purge)
        results.append(purge)
    return results


def run_navigation_retention(
    inventory_store: Path,
    mapper_store: Path | None,
    semantic_store: Path,
    *,
    scip_store: Path | None = None,
    reference_roots: Sequence[Path] = (),
    policy: RetentionPolicy | None = None,
    apply: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Plan retention and optionally quarantine/purge eligible generations."""

    policy = policy or RetentionPolicy()
    policy.validate()
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    semantic_store = _private_directory(Path(semantic_store))
    retention_root = _private_directory(semantic_store / "retention", create=True)
    lock_path = retention_root / "retention.lock"
    lock = lock_path.open("a+b")
    os.chmod(lock_path, 0o600)
    try:
        try:
            lock_file(lock, blocking=False)
        except BlockingIOError as exc:
            raise RetentionError("retention maintenance is already running") from exc
        recovered_quarantines = _recover_incomplete_quarantines(retention_root)
        plan = plan_navigation_retention(
            inventory_store,
            mapper_store,
            semantic_store,
            scip_store=scip_store,
            reference_roots=reference_roots,
            policy=policy,
            now=timestamp,
        )
        batch_id = f"{timestamp.strftime(_RUN_ID_FORMAT)}-{uuid.uuid4().hex[:12]}"
        quarantine = None
        if apply and plan["candidate_generations"]:
            candidate_ids = [item["run_id"] for item in _candidate_records(plan)]
            late_references, late_failures = _external_references(
                candidate_ids, reference_roots
            )
            if late_failures or late_references:
                raise RetentionError(
                    "retention references changed between planning and quarantine"
                )
            quarantine = _quarantine(
                retention_root, plan, batch_id=batch_id, now=timestamp
            )
            try:
                # Re-authenticate the exact live stores after moving non-current data.
                plan_navigation_retention(
                    inventory_store,
                    mapper_store,
                    semantic_store,
                    scip_store=scip_store,
                    reference_roots=reference_roots,
                    policy=policy,
                    now=timestamp,
                )
            except BaseException:
                for item in reversed(quarantine["generations"]):
                    source = Path(item["path"])
                    destination = Path(item["quarantine_path"])
                    if destination.exists() and not source.exists():
                        os.rename(destination, source)
                rollback = seal_document(
                    {
                        "schema": RETENTION_OUTCOME_SCHEMA,
                        "status": "ROLLED_BACK_AFTER_VERIFICATION",
                        "batch_id": batch_id,
                        "finished_at": _utc_now(timestamp),
                        "quarantine_outcome_receipt_sha256": quarantine[
                            "receipt_sha256"
                        ],
                    }
                )
                _write_create_once(
                    retention_root / "quarantine" / batch_id / "rollback.json",
                    rollback,
                )
                raise
        compactions = []
        if apply and plan["compaction_candidate_generations"]:
            compaction_ids = [
                item["run_id"] for item in _compaction_candidate_records(plan)
            ]
            late_references, late_failures = _external_references(
                compaction_ids, reference_roots
            )
            if late_failures or set(late_references) != set(compaction_ids):
                raise RetentionError(
                    "compaction references changed between planning and application"
                )
            for item in _compaction_candidate_records(plan):
                compactions.append(_compact_generation(item, compacted_at=timestamp))
            plan_navigation_retention(
                inventory_store,
                mapper_store,
                semantic_store,
                scip_store=scip_store,
                reference_roots=reference_roots,
                policy=policy,
                now=timestamp,
            )
        purges = (
            _purge_ready(
                retention_root,
                policy=policy,
                external_reference_roots=reference_roots,
                now=timestamp,
            )
            if apply
            else []
        )
        receipt = seal_document(
            {
                "schema": RETENTION_RUN_SCHEMA,
                "status": "PASS",
                "mode": "APPLY" if apply else "DRY_RUN",
                "run_id": batch_id,
                "finished_at": _utc_now(timestamp),
                "plan_receipt_sha256": plan["receipt_sha256"],
                "plan_status": plan["status"],
                "candidate_generations": plan["candidate_generations"],
                "candidate_bytes": plan["candidate_bytes"],
                "compaction_candidate_generations": plan[
                    "compaction_candidate_generations"
                ],
                "compaction_candidate_bytes": plan["compaction_candidate_bytes"],
                "storage_quota_satisfied_after_plan": plan[
                    "storage_quota_satisfied_after_plan"
                ],
                "quarantine": None
                if quarantine is None
                else {
                    "receipt_sha256": quarantine["receipt_sha256"],
                    "generations": len(quarantine["generations"]),
                    "bytes": quarantine["bytes"],
                },
                "purges": [
                    {
                        "receipt_sha256": purge["receipt_sha256"],
                        "generations": len(purge["deleted"]),
                        "bytes_reclaimed": purge["bytes_reclaimed"],
                    }
                    for purge in purges
                ],
                "compactions": [
                    {
                        "receipt_sha256": item["receipt_sha256"],
                        "kind": item["kind"],
                        "run_id": item["run_id"],
                        "source_bytes": item["source"]["bytes"],
                        "compressed_bytes": item["compressed"]["bytes"],
                        "logical_bytes_reclaimed": item.get(
                            "logical_bytes_reclaimed", 0
                        ),
                    }
                    for item in compactions
                ],
                "recovered_quarantines": [
                    item["receipt_sha256"] for item in recovered_quarantines
                ],
                "repository_cleanup_authority": False,
            }
        )
        runs = _private_directory(retention_root / "runs", create=True)
        run_path = runs / batch_id
        run_path.mkdir(mode=0o700)
        _write_create_once(run_path / "plan.json", plan)
        _write_create_once(run_path / "receipt.json", receipt)
        pointer = seal_document(
            {
                "schema": RETENTION_POINTER_SCHEMA,
                "run_id": batch_id,
                "status": receipt["status"],
                "retention_receipt_sha256": receipt["receipt_sha256"],
                "receipt_file_sha256": sha256_bytes(
                    (run_path / "receipt.json").read_bytes()
                ),
                "updated_at": receipt["finished_at"],
            }
        )
        _replace_atomic(retention_root / "CURRENT.json", canonical_bytes(pointer))
        return receipt
    finally:
        lock.close()
