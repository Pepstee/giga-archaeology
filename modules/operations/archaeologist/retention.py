"""Reference-aware retention for immutable Archaeologist map generations.

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
import stat
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from .evidence import canonical_bytes, seal_document, sha256_bytes, validate_self_hash
from .os_support import lock_file
# Mapper support is optional in the modularised installation.  Retention can
# still safely manage the inventory and semantic stores when no mapper store is
# configured; this schema is consulted only when one is supplied.
try:
    from .mapper import MAPPER_POINTER_SCHEMA
except ModuleNotFoundError:
    MAPPER_POINTER_SCHEMA = "giga.archaeologist.mapper-current-pointer.v1"
from .navigation_inventory import POINTER_SCHEMA as INVENTORY_POINTER_SCHEMA
from .navigation_inventory import _replace_atomic
from .semantic_graph import SEMANTIC_POINTER_SCHEMA


RETENTION_PLAN_SCHEMA = "giga.archaeologist.retention-plan.v3"
RETENTION_INTENT_SCHEMA = "giga.archaeologist.retention-quarantine-intent.v1"
RETENTION_OUTCOME_SCHEMA = "giga.archaeologist.retention-quarantine-outcome.v1"
RETENTION_PURGE_SCHEMA = "giga.archaeologist.retention-purge-outcome.v1"
RETENTION_RUN_SCHEMA = "giga.archaeologist.retention-run.v2"
RETENTION_POINTER_SCHEMA = "giga.archaeologist.retention-current.v1"
RETENTION_COMPACTION_SCHEMA = "giga.archaeologist.retention-compaction.v1"
_RUN_ID_FORMAT = "%Y%m%dT%H%M%S.%fZ"
_READ_LIMIT = 16 * 1024 * 1024
_POINTER_SCHEMAS = {
    "inventory": INVENTORY_POINTER_SCHEMA,
    "mapper": MAPPER_POINTER_SCHEMA,
    "semantic": SEMANTIC_POINTER_SCHEMA,
}


class RetentionError(ValueError):
    """A retention plan or mutation could not be proved safe."""


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


def _private_directory(path: Path, *, create: bool = False) -> Path:
    path = path.absolute()
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise RetentionError(f"retention path is not a real directory: {path}")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise RetentionError(f"retention path must be current-UID mode 0700: {path}")
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
    try:
        before = path.lstat()
    except OSError as exc:
        raise RetentionError(f"invalid retention JSON input: {path}") from exc
    if path.is_symlink() or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise RetentionError(
            f"retention JSON input is not a regular single-link file: {path}"
        )
    try:
        raw = path.read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        raise RetentionError(f"invalid retention JSON input: {path}") from exc
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
        raise RetentionError(f"retention JSON input changed while reading: {path}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RetentionError(f"invalid retention JSON input: {path}") from exc
    if not isinstance(value, dict):
        raise RetentionError(f"retention JSON root is not an object: {path}")
    return value


def _file_hash(path: Path) -> tuple[str, int]:
    metadata = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
    ):
        raise RetentionError(
            f"retention artifact must be a regular single-link file: {path}"
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
        raise RetentionError(f"retention artifact changed while hashing: {path}")
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
        "compressed_bytes": None if receipt is None else receipt["compressed"]["bytes"],
    }


def _tree_record(path: Path) -> dict[str, Any]:
    root = _private_directory(path)
    rows: list[dict[str, Any]] = []
    total = 0
    for candidate in sorted(root.rglob("*")):
        relative = candidate.relative_to(root).as_posix()
        metadata = candidate.lstat()
        if candidate.is_symlink():
            raise RetentionError(
                f"retention generation contains a symlink: {candidate}"
            )
        if stat.S_ISDIR(metadata.st_mode):
            if metadata.st_uid != os.getuid():
                raise RetentionError(
                    f"retention directory has a foreign owner: {candidate}"
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
            raise RetentionError(f"unsupported retention artifact: {candidate}")
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
        if candidate.is_symlink():
            raise RetentionError(
                f"retention generation contains a symlink: {candidate}"
            )
        if stat.S_ISDIR(metadata.st_mode):
            if metadata.st_uid != os.getuid():
                raise RetentionError(
                    f"retention directory has a foreign owner: {candidate}"
                )
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise RetentionError(f"unsupported retention artifact: {candidate}")
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
            raise RetentionError(f"unsafe generation path in {store.kind}: {path}")
        run_id = _safe_run_id(path.name)
        manifest_path = path / (
            "failure.json" if store.kind == "semantic_failure" else "manifest.json"
        )
        manifest: dict[str, Any] | None = None
        if manifest_path.is_file():
            manifest = _read_json(manifest_path)
            try:
                validate_self_hash(manifest)
            except ValueError as exc:
                raise RetentionError(
                    f"generation evidence self-hash mismatch: {path}"
                ) from exc
        elif store.kind != "semantic_failure":
            raise RetentionError(f"generation has no manifest: {path}")
        database_storage = None
        if store.kind in {"inventory", "mapper"}:
            if manifest is None:
                raise RetentionError(f"{store.kind} generation has no manifest")
            database_storage = _database_storage_state(store.kind, path, manifest)
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
            reasons = set(protected.get(item["run_id"], set()))
            if item["run_id"] in newest:
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
            stale_by_generation = generation_rank[item["run_id"]] > keep
            if not stale_by_age and not stale_by_generation:
                reasons.add("minimum-age-window")
            disposition = "RETAIN"
            if (
                not reasons
                and (stale_by_age or stale_by_generation)
                and not reference_failures
            ):
                disposition = "QUARANTINE_CANDIDATE"
                eligible.append(item)
            database_storage = item.get("database_storage")
            non_external_reasons = {
                reason for reason in reasons if not reason.startswith("external:")
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
                    and not non_external_reasons
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
        selected = {item["run_id"] for item in eligible}
        remaining = total
        for item in sorted(
            eligible, key=lambda value: (value["finished_at"], value["run_id"])
        ):
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
        raise RetentionError(f"retention evidence already exists: {path}") from exc
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
        lock_file(lock)
        recovered_quarantines = _recover_incomplete_quarantines(retention_root)
        plan = plan_navigation_retention(
            inventory_store,
            mapper_store,
            semantic_store,
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
