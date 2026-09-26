"""Deterministic capability adoption and liveness gate.

This module consumes evidence produced by capability owners.  It never discovers
features, executes declared commands, or grants effect authority.  A separate
retrospective candidate feed is deliberately status-only so an inventory can
propose adoption work without promoting its own observations to ACTIVE.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


MANIFEST_SCHEMA = "giga.capability-adoption-manifest.v1"
RECEIPT_SCHEMA = "giga.capability-liveness-receipt.v1"
REGISTRY_SCHEMA = "giga.capability-adoption-registry.v1"
LIVENESS_REPORT_SCHEMA = "giga.capability-liveness-report.v1"
CANDIDATE_FEED_SCHEMA = "giga.retrospective-capability-candidates.v1"
CAPABILITY_STATES = (
    "ACTIVE",
    "ADOPTED_UNPROVEN",
    "DEGRADED",
    "STALE",
    "BROKEN",
)
CANDIDATE_DISPOSITIONS = (
    "DORMANT_ADOPTABLE",
    "DISCONNECTED",
    "DUPLICATED",
    "BROKEN",
    "OBSOLETE",
)
TRIGGER_KINDS = ("manual", "schedule", "event", "service")
MAX_JSON_BYTES = 5 * 1024 * 1024
MAX_STATUS_OUTPUT_BYTES = 5 * 1024 * 1024
STATUS_TIMEOUT_SECONDS = 300
_ID = re.compile(r"[a-z0-9]+(?:[.-][a-z0-9]+)*")
_SHA256 = re.compile(r"[0-9a-f]{64}")

MANIFEST_FIELDS = {
    "schema",
    "id",
    "owner",
    "responsibility",
    "claim",
    "implementation_paths",
    "configuration_paths",
    "proof_paths",
    "entrypoint",
    "trigger",
    "authority",
    "recovery",
    "liveness_receipt",
}
RECEIPT_FIELDS = {
    "schema",
    "capability_id",
    "manifest_sha256",
    "observed_at",
    "status",
    "implementation",
    "configuration",
    "proofs",
    "entrypoint",
    "trigger",
    "authority",
    "recovery",
    "last_success_at",
    "last_failure_at",
    "next_check_at",
    "verification",
    "self_sha256",
}


class CapabilityAdoptionError(ValueError):
    """Raised when adoption evidence cannot support its claim."""


def _reject_constant(value: str) -> None:
    raise CapabilityAdoptionError(f"non-finite JSON value is forbidden: {value}")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CapabilityAdoptionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CapabilityAdoptionError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise CapabilityAdoptionError(f"{label} must be a JSON object")
    return value


def _timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise CapabilityAdoptionError(f"{label} must be a timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CapabilityAdoptionError(f"{label} is not a real timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CapabilityAdoptionError(f"{label} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CapabilityAdoptionError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value != path.as_posix()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise CapabilityAdoptionError(f"{label} is not a canonical relative path")
    return value


def _strings(value: object, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise CapabilityAdoptionError(
            f"{label} must be a {'possibly empty' if allow_empty else 'non-empty'} array"
        )
    if any(not isinstance(item, str) or not item for item in value):
        raise CapabilityAdoptionError(f"{label} must contain non-empty strings")
    if len(set(value)) != len(value):
        raise CapabilityAdoptionError(f"{label} contains duplicates")
    return list(value)


def _root(root: Path) -> Path:
    root = root.absolute()
    metadata = root.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise CapabilityAdoptionError("repository root must be a real directory")
    if metadata.st_uid != os.getuid():
        raise CapabilityAdoptionError(
            "repository root must be owned by the current user"
        )
    return root


def _read_file(root: Path, relative: str, label: str) -> bytes:
    relative = _relative(relative, label)
    parts = PurePosixPath(relative).parts
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    opened: list[int] = [root_fd]
    try:
        parent_fd = root_fd
        for component in parts[:-1]:
            parent_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=parent_fd,
            )
            opened.append(parent_fd)
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        opened.append(descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise CapabilityAdoptionError(f"{label} must be a single-link regular file")
        if before.st_uid != os.getuid():
            raise CapabilityAdoptionError(f"{label} must be owned by the current user")
        if before.st_size > MAX_JSON_BYTES and relative.endswith(".json"):
            raise CapabilityAdoptionError(f"{label} exceeds {MAX_JSON_BYTES} bytes")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        current = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if stable != current:
            raise CapabilityAdoptionError(f"{label} changed while it was read")
        return b"".join(chunks)
    except (FileNotFoundError, NotADirectoryError, OSError) as exc:
        if isinstance(exc, CapabilityAdoptionError):
            raise
        raise CapabilityAdoptionError(f"{label} is missing or unsafe") from exc
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _file_record(root: Path, relative: str, label: str) -> dict[str, Any]:
    raw = _read_file(root, relative, label)
    return {"path": relative, "sha256": _sha256(raw), "bytes": len(raw)}


def _records(root: Path, paths: Sequence[str], label: str) -> list[dict[str, Any]]:
    return [_file_record(root, path, f"{label}: {path}") for path in paths]


def _closed(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise CapabilityAdoptionError(f"{label} does not have the exact schema")
    return value


def _argv(value: object, label: str, *, allow_empty: bool = False) -> list[str]:
    values = _strings(value, label, allow_empty=allow_empty)
    if any("\x00" in item for item in values):
        raise CapabilityAdoptionError(f"{label} contains a NUL byte")
    return values


def _entrypoint(value: object) -> dict[str, Any]:
    record = _closed(value, {"argv", "working_directory"}, "entrypoint")
    working_directory = record["working_directory"]
    if working_directory != ".":
        working_directory = _relative(working_directory, "entrypoint working directory")
    return {
        "argv": _argv(record["argv"], "entrypoint argv"),
        "working_directory": working_directory,
    }


def _trigger(value: object) -> dict[str, str]:
    record = _closed(value, {"kind", "identity"}, "trigger")
    if (
        record["kind"] not in TRIGGER_KINDS
        or not isinstance(record["identity"], str)
        or not record["identity"]
    ):
        raise CapabilityAdoptionError("trigger is invalid")
    return {"kind": record["kind"], "identity": record["identity"]}


def _authority(value: object) -> dict[str, Any]:
    record = _closed(
        value,
        {"capabilities", "privacy", "external_effects", "vault_required"},
        "authority",
    )
    capabilities = _strings(record["capabilities"], "authority capabilities")
    if not isinstance(record["privacy"], str) or not record["privacy"]:
        raise CapabilityAdoptionError("authority privacy must be a non-empty string")
    if (
        type(record["external_effects"]) is not bool
        or type(record["vault_required"]) is not bool
    ):
        raise CapabilityAdoptionError("authority booleans must be exact booleans")
    return {
        "capabilities": capabilities,
        "privacy": record["privacy"],
        "external_effects": record["external_effects"],
        "vault_required": record["vault_required"],
    }


def _recovery(value: object) -> dict[str, Any]:
    record = _closed(
        value, {"status_argv", "reconcile_argv", "disable_argv"}, "recovery"
    )
    return {
        "status_argv": _argv(record["status_argv"], "recovery status argv"),
        "reconcile_argv": _argv(
            record["reconcile_argv"], "recovery reconcile argv", allow_empty=True
        ),
        "disable_argv": _argv(
            record["disable_argv"], "recovery disable argv", allow_empty=True
        ),
    }


def _manifest(root: Path, path: str) -> tuple[dict[str, Any], bytes]:
    raw = _read_file(root, path, f"capability manifest {path}")
    value = _strict_json(raw, f"capability manifest {path}")
    if set(value) != MANIFEST_FIELDS or value.get("schema") != MANIFEST_SCHEMA:
        raise CapabilityAdoptionError(
            f"capability manifest {path} has the wrong schema"
        )
    capability_id = value["id"]
    if not isinstance(capability_id, str) or _ID.fullmatch(capability_id) is None:
        raise CapabilityAdoptionError(f"capability manifest {path} has an invalid id")
    if not isinstance(value["owner"], str) or not value["owner"]:
        raise CapabilityAdoptionError(f"capability {capability_id} has no owner")
    if not isinstance(value["responsibility"], str) or not value["responsibility"]:
        raise CapabilityAdoptionError(
            f"capability {capability_id} has no responsibility"
        )
    if value["claim"] not in {"ACTIVE", "ADOPTED"}:
        raise CapabilityAdoptionError(
            f"capability {capability_id} has an invalid claim"
        )
    implementation = [
        _relative(item, "implementation path")
        for item in _strings(value["implementation_paths"], "implementation paths")
    ]
    configuration = [
        _relative(item, "configuration path")
        for item in _strings(
            value["configuration_paths"], "configuration paths", allow_empty=True
        )
    ]
    proofs = [
        _relative(item, "proof path")
        for item in _strings(value["proof_paths"], "proof paths")
    ]
    all_paths = implementation + configuration + proofs
    if len(set(all_paths)) != len(all_paths):
        raise CapabilityAdoptionError(
            f"capability {capability_id} reuses a path across binding classes"
        )
    return {
        **value,
        "implementation_paths": implementation,
        "configuration_paths": configuration,
        "proof_paths": proofs,
        "entrypoint": _entrypoint(value["entrypoint"]),
        "trigger": _trigger(value["trigger"]),
        "authority": _authority(value["authority"]),
        "recovery": _recovery(value["recovery"]),
        "liveness_receipt": _relative(value["liveness_receipt"], "liveness receipt"),
    }, raw


def inspect_capability_manifest(root: Path, path: str) -> dict[str, Any]:
    """Return one strictly validated declaration without evaluating liveness.

    This is the read-only metadata boundary for consumers such as Archaeology.
    Successful inspection proves what the manifest declares; it grants no runtime,
    execution, ownership-promotion, or activation authority.
    """

    root = _root(root)
    canonical_path = _relative(path, "capability manifest path")
    manifest, raw = _manifest(root, canonical_path)
    return {
        **manifest,
        "manifest_path": canonical_path,
        "manifest_sha256": _sha256(raw),
        "declaration_only": True,
        "canonicality_claimed": False,
        "execution_authority_granted": False,
    }


def _record_list(value: object, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise CapabilityAdoptionError(f"{label} must be an array")
    result: list[dict[str, Any]] = []
    for item in value:
        record = _closed(item, {"path", "sha256", "bytes"}, label)
        path = _relative(record["path"], f"{label} path")
        if (
            not isinstance(record["sha256"], str)
            or _SHA256.fullmatch(record["sha256"]) is None
        ):
            raise CapabilityAdoptionError(f"{label} contains an invalid SHA-256")
        if (
            isinstance(record["bytes"], bool)
            or not isinstance(record["bytes"], int)
            or record["bytes"] < 0
        ):
            raise CapabilityAdoptionError(f"{label} contains an invalid byte count")
        result.append(
            {"path": path, "sha256": record["sha256"], "bytes": record["bytes"]}
        )
    if len({item["path"] for item in result}) != len(result):
        raise CapabilityAdoptionError(f"{label} contains duplicate paths")
    return result


def _validate_self_hash(value: Mapping[str, Any], label: str) -> None:
    recorded = value.get("self_sha256")
    if not isinstance(recorded, str) or _SHA256.fullmatch(recorded) is None:
        raise CapabilityAdoptionError(f"{label} has an invalid self hash")
    material = dict(value)
    del material["self_sha256"]
    calculated = _sha256(
        json.dumps(
            material, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    )
    if recorded != calculated:
        raise CapabilityAdoptionError(f"{label} self hash differs")


def _evaluate(
    root: Path, manifest: Mapping[str, Any], manifest_raw: bytes, observed_at: str
) -> dict[str, Any]:
    capability_id = manifest["id"]
    base = {
        "id": capability_id,
        "owner": manifest["owner"],
        "responsibility": manifest["responsibility"],
        "claim": manifest["claim"],
        "entrypoint": manifest["entrypoint"],
        "trigger": manifest["trigger"],
        "authority": manifest["authority"],
        "recovery": manifest["recovery"],
        "execution_authority_granted": False,
    }
    try:
        implementation = _records(
            root, manifest["implementation_paths"], "implementation"
        )
        configuration = _records(root, manifest["configuration_paths"], "configuration")
        proofs = _records(root, manifest["proof_paths"], "proof")
        raw = _read_file(root, manifest["liveness_receipt"], "liveness receipt")
        receipt = _strict_json(raw, "liveness receipt")
        if set(receipt) != RECEIPT_FIELDS or receipt.get("schema") != RECEIPT_SCHEMA:
            raise CapabilityAdoptionError("liveness receipt has the wrong schema")
        _validate_self_hash(receipt, "liveness receipt")
        if receipt["capability_id"] != capability_id or receipt[
            "manifest_sha256"
        ] != _sha256(manifest_raw):
            raise CapabilityAdoptionError(
                "liveness receipt does not bind the capability manifest"
            )
        if (
            _record_list(receipt["implementation"], "receipt implementation")
            != implementation
        ):
            raise CapabilityAdoptionError("liveness receipt implementation differs")
        if (
            _record_list(receipt["configuration"], "receipt configuration")
            != configuration
        ):
            raise CapabilityAdoptionError("liveness receipt configuration differs")
        if _record_list(receipt["proofs"], "receipt proofs") != proofs:
            raise CapabilityAdoptionError("liveness receipt proofs differ")
        if _entrypoint(receipt["entrypoint"]) != manifest["entrypoint"]:
            raise CapabilityAdoptionError("liveness receipt entrypoint differs")
        if _trigger(receipt["trigger"]) != manifest["trigger"]:
            raise CapabilityAdoptionError("liveness receipt trigger differs")
        if _authority(receipt["authority"]) != manifest["authority"]:
            raise CapabilityAdoptionError("liveness receipt authority differs")
        if _recovery(receipt["recovery"]) != manifest["recovery"]:
            raise CapabilityAdoptionError("liveness receipt recovery differs")
        verification = _closed(
            receipt["verification"],
            {"argv", "exit_code", "stdout_sha256", "stdout_bytes"},
            "verification",
        )
        verification_argv = _argv(verification["argv"], "verification argv")
        if verification_argv != manifest["recovery"]["status_argv"]:
            raise CapabilityAdoptionError(
                "verification argv differs from the owner status command"
            )
        if (
            isinstance(verification["exit_code"], bool)
            or not isinstance(verification["exit_code"], int)
            or verification["exit_code"] not in {0, 1, 2}
        ):
            raise CapabilityAdoptionError("verification exit code is invalid")
        if (
            not isinstance(verification["stdout_sha256"], str)
            or _SHA256.fullmatch(verification["stdout_sha256"]) is None
        ):
            raise CapabilityAdoptionError("verification stdout SHA-256 is invalid")
        if (
            isinstance(verification["stdout_bytes"], bool)
            or not isinstance(verification["stdout_bytes"], int)
            or verification["stdout_bytes"] < 0
        ):
            raise CapabilityAdoptionError("verification stdout byte count is invalid")
        observed = _timestamp(receipt["observed_at"], "receipt observed_at")
        now = _timestamp(observed_at, "gate observed_at")
        success = (
            None
            if receipt["last_success_at"] is None
            else _timestamp(receipt["last_success_at"], "last_success_at")
        )
        failure = (
            None
            if receipt["last_failure_at"] is None
            else _timestamp(receipt["last_failure_at"], "last_failure_at")
        )
        next_check = _timestamp(receipt["next_check_at"], "next_check_at")
        if (
            observed > now
            or success is not None
            and success > observed
            or failure is not None
            and failure > observed
        ):
            raise CapabilityAdoptionError("liveness receipt chronology differs")
        if receipt["status"] not in {"PASS", "FAIL"}:
            raise CapabilityAdoptionError("liveness receipt status is invalid")
        if receipt["status"] == "PASS" and (
            verification["exit_code"] != 0 or success is None
        ):
            raise CapabilityAdoptionError(
                "PASS liveness has no successful verification"
            )
        if receipt["status"] == "FAIL" and failure is None:
            raise CapabilityAdoptionError("FAIL liveness has no failure timestamp")
        if receipt["status"] == "PASS" and failure is not None and failure > success:
            raise CapabilityAdoptionError(
                "PASS liveness is followed by a later failure"
            )
        if receipt["status"] == "FAIL" and success is not None and success > failure:
            raise CapabilityAdoptionError(
                "FAIL liveness is followed by a later success"
            )
        state = "DEGRADED" if receipt["status"] == "FAIL" else "ACTIVE"
        reason = (
            "owner verification failed"
            if state == "DEGRADED"
            else "current owner proof is bound"
        )
        if next_check <= now:
            state, reason = "STALE", "liveness proof expired"
        if manifest["claim"] != "ACTIVE" and state == "ACTIVE":
            state, reason = (
                "ADOPTED_UNPROVEN",
                "manifest does not claim active operation",
            )
        return {
            **base,
            "state": state,
            "reason": reason,
            "manifest_sha256": _sha256(manifest_raw),
            "liveness_receipt": _file_record(
                root, manifest["liveness_receipt"], "liveness receipt"
            ),
            "last_success_at": receipt["last_success_at"],
            "last_failure_at": receipt["last_failure_at"],
            "next_check_at": receipt["next_check_at"],
            "verification": verification,
        }
    except CapabilityAdoptionError as exc:
        message = str(exc)
        missing = "missing or unsafe" in message and "liveness receipt" in message
        drift = any(
            marker in message
            for marker in (
                "implementation differs",
                "configuration differs",
                "proofs differ",
                "manifest differs",
                "entrypoint differs",
                "trigger differs",
                "authority differs",
                "recovery differs",
            )
        )
        return {
            **base,
            "state": "ADOPTED_UNPROVEN" if missing else "STALE" if drift else "BROKEN",
            "reason": message,
            "manifest_sha256": _sha256(manifest_raw),
            "liveness_receipt": None,
            "last_success_at": None,
            "last_failure_at": None,
            "next_check_at": None,
            "verification": None,
        }


def _git_head_verifier(root: Path, paths: Sequence[str]) -> None:
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
    for path in paths:
        process = subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-C",
                str(root),
                "show",
                f"HEAD:{path}",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        if process.returncode != 0:
            raise CapabilityAdoptionError(
                f"tracked authority is missing from HEAD: {path}"
            )
        if process.stdout != _read_file(root, path, f"tracked authority {path}"):
            raise CapabilityAdoptionError(f"working tree differs from HEAD: {path}")


def _candidate_feed(
    root: Path, path: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = _read_file(root, path, f"retrospective feed {path}")
    value = _strict_json(raw, f"retrospective feed {path}")
    fields = {
        "schema",
        "producer",
        "inventory_manifest_sha256",
        "generated_at",
        "candidates",
        "self_sha256",
    }
    if set(value) != fields or value.get("schema") != CANDIDATE_FEED_SCHEMA:
        raise CapabilityAdoptionError(f"retrospective feed {path} has the wrong schema")
    _validate_self_hash(value, f"retrospective feed {path}")
    if not isinstance(value["producer"], str) or not value["producer"]:
        raise CapabilityAdoptionError("retrospective feed has no producer")
    if (
        not isinstance(value["inventory_manifest_sha256"], str)
        or _SHA256.fullmatch(value["inventory_manifest_sha256"]) is None
    ):
        raise CapabilityAdoptionError(
            "retrospective feed has an invalid inventory identity"
        )
    _timestamp(value["generated_at"], "retrospective feed generated_at")
    if not isinstance(value["candidates"], list):
        raise CapabilityAdoptionError("retrospective feed candidates must be an array")
    candidates: list[dict[str, Any]] = []
    for item in value["candidates"]:
        record = _closed(
            item,
            {
                "candidate_id",
                "capability_id",
                "disposition",
                "owner_hint",
                "source_refs",
                "entrypoint_hints",
                "reason",
            },
            "retrospective candidate",
        )
        if (
            not isinstance(record["candidate_id"], str)
            or _ID.fullmatch(record["candidate_id"]) is None
        ):
            raise CapabilityAdoptionError("retrospective candidate id is invalid")
        if (
            not isinstance(record["capability_id"], str)
            or _ID.fullmatch(record["capability_id"]) is None
        ):
            raise CapabilityAdoptionError("retrospective capability id is invalid")
        if record["disposition"] not in CANDIDATE_DISPOSITIONS:
            raise CapabilityAdoptionError(
                "retrospective candidate disposition is invalid"
            )
        if not isinstance(record["owner_hint"], str) or not record["owner_hint"]:
            raise CapabilityAdoptionError(
                "retrospective candidate owner hint is invalid"
            )
        source_refs = _record_list(record["source_refs"], "retrospective source refs")
        if not source_refs:
            raise CapabilityAdoptionError(
                "retrospective candidate must bind at least one source"
            )
        current = [
            _file_record(root, source["path"], "retrospective source")
            for source in source_refs
        ]
        if current != source_refs:
            raise CapabilityAdoptionError(
                "retrospective candidate source differs from inventory"
            )
        entrypoints = _strings(
            record["entrypoint_hints"],
            "retrospective entrypoint hints",
            allow_empty=True,
        )
        if not isinstance(record["reason"], str) or not record["reason"]:
            raise CapabilityAdoptionError("retrospective candidate reason is invalid")
        candidates.append(
            {
                **record,
                "source_refs": source_refs,
                "entrypoint_hints": entrypoints,
                "state": record["disposition"],
                "execution_authority_granted": False,
                "source_feed": path,
            }
        )
    if len({item["candidate_id"] for item in candidates}) != len(candidates):
        raise CapabilityAdoptionError(
            "retrospective feed contains duplicate candidate ids"
        )
    return value, candidates


def compile_adoption_registry(
    root: Path,
    observed_at: str,
    *,
    manifest_dir: str = "capabilities/manifests",
    candidate_feeds: Sequence[str] = (),
    require_git_head: bool = True,
) -> dict[str, Any]:
    """Compile adopted capabilities and inventory candidates into one status registry."""
    root = _root(root)
    _timestamp(observed_at, "gate observed_at")
    directory = root / _relative(manifest_dir, "manifest directory")
    if not directory.is_dir() or directory.is_symlink():
        raise CapabilityAdoptionError(
            "capability manifest directory is missing or unsafe"
        )
    unexpected = sorted(
        path.name
        for path in directory.iterdir()
        if not path.name.startswith(".")
        and (not path.is_file() or path.is_symlink() or path.suffix != ".json")
    )
    if unexpected:
        raise CapabilityAdoptionError(
            f"capability manifest directory contains unsupported entries: {', '.join(unexpected)}"
        )
    manifest_paths = sorted(
        path.relative_to(root).as_posix()
        for path in directory.iterdir()
        if path.is_file() and not path.is_symlink() and path.suffix == ".json"
    )
    if not manifest_paths:
        raise CapabilityAdoptionError("capability manifest directory is empty")
    capabilities: list[dict[str, Any]] = []
    tracked_paths: list[str] = []
    ids: set[str] = set()
    for path in manifest_paths:
        manifest, raw = _manifest(root, path)
        if manifest["id"] in ids:
            raise CapabilityAdoptionError(f"duplicate capability id: {manifest['id']}")
        ids.add(manifest["id"])
        evaluated = _evaluate(root, manifest, raw, observed_at)
        capabilities.append(evaluated)
        tracked_paths.extend(
            [
                path,
                *manifest["implementation_paths"],
                *manifest["configuration_paths"],
                *manifest["proof_paths"],
            ]
        )
        if evaluated["liveness_receipt"] is not None:
            tracked_paths.append(manifest["liveness_receipt"])
    candidates: list[dict[str, Any]] = []
    feed_records: list[dict[str, Any]] = []
    feed_self_hashes: set[str] = set()
    for path in candidate_feeds:
        path = _relative(path, "candidate feed")
        feed, records = _candidate_feed(root, path)
        if feed["self_sha256"] in feed_self_hashes:
            raise CapabilityAdoptionError(
                "retrospective feeds must have unique content identities"
            )
        feed_self_hashes.add(feed["self_sha256"])
        if _timestamp(
            feed["generated_at"], "retrospective feed generated_at"
        ) > _timestamp(observed_at, "gate observed_at"):
            raise CapabilityAdoptionError(
                "retrospective feed is dated after the gate observation"
            )
        candidates.extend(records)
        feed_records.append(
            {
                "path": path,
                "sha256": _sha256(_read_file(root, path, "candidate feed")),
                "producer": feed["producer"],
                "inventory_manifest_sha256": feed["inventory_manifest_sha256"],
            }
        )
        tracked_paths.append(path)
        tracked_paths.extend(
            source["path"]
            for candidate in records
            for source in candidate["source_refs"]
        )
    if len({item["candidate_id"] for item in candidates}) != len(candidates):
        raise CapabilityAdoptionError(
            "candidate ids collide across retrospective feeds"
        )
    if require_git_head:
        _git_head_verifier(root, sorted(set(tracked_paths)))
    capabilities.sort(key=lambda item: item["id"])
    candidates.sort(key=lambda item: item["candidate_id"])
    state_counts = Counter(item["state"] for item in capabilities)
    disposition_counts = Counter(item["disposition"] for item in candidates)
    payload = {
        "schema": REGISTRY_SCHEMA,
        "observed_at": observed_at,
        "authority": "adoption-and-liveness-status-only",
        "source_authority": "git-head"
        if require_git_head
        else "uncommitted-development",
        "execution_authority_granted": False,
        "capabilities": capabilities,
        "retrospective_socket": {
            "schema": CANDIDATE_FEED_SCHEMA,
            "feeds": feed_records,
            "candidates": candidates,
            "promotion_authority": False,
        },
        "summary": {
            "capabilities_total": len(capabilities),
            "capability_states": {
                state: state_counts.get(state, 0) for state in CAPABILITY_STATES
            },
            "retrospective_candidates_total": len(candidates),
            "candidate_dispositions": {
                state: disposition_counts.get(state, 0)
                for state in CANDIDATE_DISPOSITIONS
            },
        },
    }
    payload["registry_sha256"] = _sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    )
    return payload


def _validated_registry_capabilities(
    payload: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if (
        payload.get("schema") != REGISTRY_SCHEMA
        or payload.get("execution_authority_granted") is not False
    ):
        raise CapabilityAdoptionError("invalid adoption registry")
    if payload.get("source_authority") != "git-head":
        raise CapabilityAdoptionError(
            "ACTIVE enforcement requires exact current-HEAD source authority"
        )
    material = dict(payload)
    recorded = material.pop("registry_sha256", None)
    calculated = _sha256(
        json.dumps(
            material, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    )
    if recorded != calculated:
        raise CapabilityAdoptionError("adoption registry self hash differs")
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list) or any(
        not isinstance(item, dict) for item in capabilities
    ):
        raise CapabilityAdoptionError("adoption registry capabilities are invalid")
    return capabilities


def require_declared_active(
    payload: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Require every manifest claiming ACTIVE to have current ACTIVE evidence."""
    capabilities = _validated_registry_capabilities(payload)
    declared = [item for item in capabilities if item.get("claim") == "ACTIVE"]
    for capability in declared:
        if capability.get("state") != "ACTIVE":
            raise CapabilityAdoptionError(
                "declared ACTIVE capability is not current: "
                f"{capability.get('id')} ({capability.get('state')})"
            )
    return declared


def verify_declared_active(
    root: Path, payload: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    """Re-execute every declared-active owner's exact bound status command."""
    declared = require_declared_active(payload)
    report = observe_liveness(root, payload)
    observations = {
        item["id"]: item for item in report["capabilities"] if item["claim"] == "ACTIVE"
    }
    for capability in declared:
        observation = observations[capability["id"]]
        if observation["state"] != "ACTIVE":
            raise CapabilityAdoptionError(
                "declared ACTIVE capability is not current after owner observation: "
                f"{capability['id']} ({observation['state']}): {observation['reason']}"
            )
    return declared


def observe_liveness(root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Observe current capability state without granting owner effect authority."""
    root = _root(root)
    capabilities = _validated_registry_capabilities(payload)
    observations: list[dict[str, Any]] = []
    for capability in capabilities:
        state = capability["state"]
        reason = capability["reason"]
        live_check: dict[str, Any] = {
            "performed": False,
            "status": "NOT_REQUIRED",
            "observed_verification": None,
        }
        if capability["claim"] == "ACTIVE" and state == "ACTIVE":
            state, reason, live_check = _observe_active_owner(root, capability)
        observations.append(
            {
                "id": capability["id"],
                "owner": capability["owner"],
                "claim": capability["claim"],
                "state": state,
                "reason": reason,
                "last_success_at": capability["last_success_at"],
                "last_failure_at": capability["last_failure_at"],
                "next_check_at": capability["next_check_at"],
                "live_check": live_check,
                "execution_authority_granted": False,
            }
        )
    counts = Counter(item["state"] for item in observations)
    report = {
        "schema": LIVENESS_REPORT_SCHEMA,
        "observed_at": payload["observed_at"],
        "source_authority": payload["source_authority"],
        "registry_sha256": payload["registry_sha256"],
        "execution_authority_granted": False,
        "capabilities": observations,
        "summary": {
            "capabilities_total": len(observations),
            "states": {state: counts.get(state, 0) for state in CAPABILITY_STATES},
        },
    }
    report["report_sha256"] = _sha256(
        json.dumps(
            report, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    )
    return report


def _observe_active_owner(
    root: Path, capability: Mapping[str, Any]
) -> tuple[str, str, dict[str, Any]]:
    try:
        working_directory = capability["entrypoint"]["working_directory"]
        directory = root
        if working_directory != ".":
            for component in PurePosixPath(working_directory).parts:
                directory = directory / component
                metadata = directory.lstat()
                if (
                    not stat.S_ISDIR(metadata.st_mode)
                    or stat.S_ISLNK(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                ):
                    raise CapabilityAdoptionError(
                        f"capability status working directory is unsafe: {working_directory}"
                    )
        expected = capability.get("verification")
        if not isinstance(expected, dict):
            raise CapabilityAdoptionError(
                f"capability has no bound verification: {capability.get('id')}"
            )
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            in {
                "LANG",
                "LC_ALL",
                "LC_CTYPE",
                "PATH",
                "SYSTEMROOT",
                "TMPDIR",
            }
        }
        env.update(
            {
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_NOSYSTEM": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
            }
        )
        returncode, stdout = _run_read_only_status(
            root,
            directory,
            capability["recovery"]["status_argv"],
            env,
            capability["id"],
        )
        observed = {
            "argv": capability["recovery"]["status_argv"],
            "exit_code": returncode,
            "stdout_sha256": _sha256(stdout),
            "stdout_bytes": len(stdout),
        }
        if observed != expected:
            state = "DEGRADED" if returncode != 0 else "BROKEN"
            return (
                state,
                "live owner status differs from its receipt",
                {
                    "performed": True,
                    "status": "FAIL",
                    "observed_verification": observed,
                },
            )
        return (
            "ACTIVE",
            "live owner status matches its receipt",
            {
                "performed": True,
                "status": "PASS",
                "observed_verification": observed,
            },
        )
    except CapabilityAdoptionError as exc:
        return (
            "BROKEN",
            str(exc),
            {
                "performed": True,
                "status": "REFUSED",
                "observed_verification": None,
            },
        )


def _run_read_only_status(
    root: Path,
    directory: Path,
    argv: Sequence[str],
    env: Mapping[str, str],
    capability_id: str,
) -> tuple[int, bytes]:
    if sys.platform != "darwin":
        raise CapabilityAdoptionError(
            "capability owner status requires the admitted macOS read-only sandbox"
        )
    sandbox = Path("/usr/bin/sandbox-exec")
    metadata = sandbox.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_mode & 0o022
    ):
        raise CapabilityAdoptionError("macOS read-only sandbox authority is unsafe")
    with tempfile.TemporaryDirectory(prefix="giga-capability-status-") as scratch:
        scratch_path = Path(scratch)
        scratch_path.chmod(0o700)
        runtime_paths = _status_runtime_read_paths(argv, env)
        profile_lines = [
            "(version 1)",
            "(deny default)",
            "(allow process*)",
            "(allow file-read*)",
            f"(deny file-read* (subpath {json.dumps(str(Path.home()))}))",
            f"(allow file-read* (subpath {json.dumps(str(root))}))",
        ]
        profile_lines.extend(
            f"(allow file-read* (subpath {json.dumps(str(path))}))"
            if path.is_dir()
            else f"(allow file-read* (literal {json.dumps(str(path))}))"
            for path in runtime_paths
        )
        profile_lines.extend(
            (
                f"(allow file-write* (subpath {json.dumps(str(scratch_path))}))",
                "(deny network*)",
            )
        )
        profile = "\n".join(profile_lines)
        sandbox_env = dict(env)
        sandbox_env.update({"HOME": scratch, "TMPDIR": scratch})
        command = [str(sandbox), "-p", profile, *argv]
        try:
            process = subprocess.Popen(
                command,
                cwd=directory,
                env=sandbox_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as exc:
            raise CapabilityAdoptionError(
                f"capability owner status command failed to run: {capability_id}"
            ) from exc
        assert process.stdout is not None
        assert process.stderr is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        output = {"stdout": bytearray(), "stderr": bytearray()}
        deadline = time.monotonic() + STATUS_TIMEOUT_SECONDS
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CapabilityAdoptionError(
                        f"capability owner status timed out: {capability_id}"
                    )
                for key, _ in selector.select(min(remaining, 0.25)):
                    chunk = os.read(key.fileobj.fileno(), 64 * 1024)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    stream = output[key.data]
                    stream.extend(chunk)
                    if len(stream) > MAX_STATUS_OUTPUT_BYTES:
                        raise CapabilityAdoptionError(
                            f"capability owner status output is too large: {capability_id}"
                        )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CapabilityAdoptionError(
                    f"capability owner status timed out: {capability_id}"
                )
            try:
                returncode = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                raise CapabilityAdoptionError(
                    f"capability owner status timed out: {capability_id}"
                ) from exc
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return returncode, bytes(output["stdout"])
        except CapabilityAdoptionError:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
        finally:
            selector.close()


def _status_runtime_read_paths(
    argv: Sequence[str], env: Mapping[str, str]
) -> tuple[Path, ...]:
    executable = argv[0]
    located = (
        shutil.which(executable, path=env.get("PATH"))
        if "/" not in executable
        else executable
    )
    if not located:
        raise CapabilityAdoptionError("capability owner status executable is missing")
    command = Path(located).resolve(strict=True)
    metadata = command.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid not in {0, os.getuid()}
        or metadata.st_mode & 0o002
    ):
        raise CapabilityAdoptionError("capability owner status executable is unsafe")
    paths = {command}
    if command == Path(sys.executable).resolve(strict=True):
        runtime = Path(sys.base_prefix).resolve(strict=True)
        runtime_metadata = runtime.lstat()
        if (
            not stat.S_ISDIR(runtime_metadata.st_mode)
            or stat.S_ISLNK(runtime_metadata.st_mode)
            or runtime_metadata.st_uid not in {0, os.getuid()}
            or runtime_metadata.st_mode & 0o002
        ):
            raise CapabilityAdoptionError("Python runtime authority is unsafe")
        paths.add(runtime)
    return tuple(sorted(paths, key=lambda path: str(path)))


def require_active(payload: Mapping[str, Any], capability_id: str) -> Mapping[str, Any]:
    """Refuse any capability that is not currently ACTIVE in a compiled registry."""
    capabilities = _validated_registry_capabilities(payload)
    matches = [item for item in capabilities if item.get("id") == capability_id]
    if len(matches) != 1:
        raise CapabilityAdoptionError(
            f"capability is not uniquely registered: {capability_id}"
        )
    capability = matches[0]
    if capability.get("state") != "ACTIVE":
        raise CapabilityAdoptionError(
            f"capability is not ACTIVE: {capability_id} ({capability.get('state')})"
        )
    return capability


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
