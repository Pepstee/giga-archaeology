"""Strict import boundary for external capability-adoption registry snapshots.

The capability-adoption gate remains the authority for liveness.  This adapter only preserves a
content-addressed, queryable projection of a gate-produced registry; it cannot promote candidates,
grant execution authority, or infer runtime state from source declarations.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .evidence import canonical_bytes, sha256_bytes


RUNTIME_POLICY_VERSION = "giga.archaeologist.runtime-registry-import.v1"
REGISTRY_SCHEMA = "giga.capability-adoption-registry.v1"
REGISTRY_AUTHORITY = "adoption-and-liveness-status-only"
CAPABILITY_STATES = {
    "ACTIVE",
    "ADOPTED_UNPROVEN",
    "DEGRADED",
    "STALE",
    "BROKEN",
}
TRIGGER_KINDS = {"manual", "schedule", "event", "service"}
MAX_REGISTRY_BYTES = 5 * 1024 * 1024
_ID = re.compile(r"[a-z0-9]+(?:[.-][a-z0-9]+)*")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_TOP_LEVEL_FIELDS = {
    "schema",
    "observed_at",
    "authority",
    "source_authority",
    "execution_authority_granted",
    "capabilities",
    "retrospective_socket",
    "summary",
    "registry_sha256",
}
_CAPABILITY_FIELDS = {
    "authority",
    "claim",
    "entrypoint",
    "execution_authority_granted",
    "id",
    "last_failure_at",
    "last_success_at",
    "liveness_receipt",
    "manifest_sha256",
    "next_check_at",
    "owner",
    "reason",
    "recovery",
    "responsibility",
    "state",
    "trigger",
}


class RuntimeMapError(ValueError):
    """Raised when an external runtime-status input is unsafe or ambiguous."""


@dataclass(frozen=True)
class RuntimeRegistryInput:
    path: Path
    file_sha256: str
    bytes: int
    registry: Mapping[str, Any]

    def manifest_record(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "file_sha256": self.file_sha256,
            "bytes": self.bytes,
            "registry_sha256": self.registry["registry_sha256"],
            "observed_at": self.registry["observed_at"],
            "source_authority": self.registry["source_authority"],
        }


def _strict_object(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeMapError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise RuntimeMapError(f"non-finite JSON value is forbidden: {value}")


def _timestamp(value: object, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise RuntimeMapError(f"{label} must be a timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeMapError(f"{label} is not a real timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeMapError(f"{label} must include a UTC offset")
    return value


def _strings(value: object, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise RuntimeMapError(f"{label} must be an array")
    if any(not isinstance(item, str) or not item or "\x00" in item for item in value):
        raise RuntimeMapError(f"{label} contains an invalid string")
    if len(set(value)) != len(value):
        raise RuntimeMapError(f"{label} contains duplicates")
    return list(value)


def _closed(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise RuntimeMapError(f"{label} does not have the exact schema")
    return value


def _file_record(value: object, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    record = _closed(value, {"path", "sha256", "bytes"}, label)
    if (
        not isinstance(record["path"], str)
        or not record["path"]
        or not isinstance(record["bytes"], int)
        or isinstance(record["bytes"], bool)
        or record["bytes"] < 0
        or not isinstance(record["sha256"], str)
        or _SHA256.fullmatch(record["sha256"]) is None
    ):
        raise RuntimeMapError(f"{label} is invalid")
    return dict(record)


def _capability(value: object) -> dict[str, Any]:
    record = _closed(value, _CAPABILITY_FIELDS, "capability")
    if not isinstance(record["id"], str) or _ID.fullmatch(record["id"]) is None:
        raise RuntimeMapError("capability id is invalid")
    for field in ("claim", "owner", "reason", "responsibility"):
        if not isinstance(record[field], str) or not record[field]:
            raise RuntimeMapError(f"capability {field} is invalid")
    if record["state"] not in CAPABILITY_STATES:
        raise RuntimeMapError("capability state is invalid")
    if record["execution_authority_granted"] is not False:
        raise RuntimeMapError("capability registry must not grant execution authority")
    if (
        not isinstance(record["manifest_sha256"], str)
        or _SHA256.fullmatch(record["manifest_sha256"]) is None
    ):
        raise RuntimeMapError("capability manifest hash is invalid")

    entrypoint = _closed(
        record["entrypoint"], {"argv", "working_directory"}, "entrypoint"
    )
    entrypoint = {
        "argv": _strings(entrypoint["argv"], "entrypoint argv"),
        "working_directory": entrypoint["working_directory"],
    }
    if (
        not isinstance(entrypoint["working_directory"], str)
        or not entrypoint["working_directory"]
    ):
        raise RuntimeMapError("entrypoint working directory is invalid")

    trigger = _closed(record["trigger"], {"kind", "identity"}, "trigger")
    if (
        trigger["kind"] not in TRIGGER_KINDS
        or not isinstance(trigger["identity"], str)
        or not trigger["identity"]
    ):
        raise RuntimeMapError("trigger is invalid")

    authority = _closed(
        record["authority"],
        {"capabilities", "privacy", "external_effects", "vault_required"},
        "authority envelope",
    )
    authority = {
        "capabilities": _strings(authority["capabilities"], "capabilities"),
        "privacy": authority["privacy"],
        "external_effects": authority["external_effects"],
        "vault_required": authority["vault_required"],
    }
    if not isinstance(authority["privacy"], str) or not authority["privacy"]:
        raise RuntimeMapError("authority privacy is invalid")
    if (
        type(authority["external_effects"]) is not bool
        or type(authority["vault_required"]) is not bool
    ):
        raise RuntimeMapError("authority booleans are invalid")

    recovery = _closed(
        record["recovery"],
        {"status_argv", "reconcile_argv", "disable_argv"},
        "recovery",
    )
    recovery = {
        key: _strings(recovery[key], f"recovery {key}", allow_empty=True)
        for key in ("status_argv", "reconcile_argv", "disable_argv")
    }
    liveness_receipt = _file_record(record["liveness_receipt"], "liveness receipt")
    if record["state"] == "ACTIVE" and liveness_receipt is None:
        raise RuntimeMapError("ACTIVE capability has no liveness receipt")
    for field in ("last_failure_at", "last_success_at", "next_check_at"):
        _timestamp(record[field], field, optional=True)
    return {
        **record,
        "entrypoint": entrypoint,
        "trigger": dict(trigger),
        "authority": authority,
        "recovery": recovery,
        "liveness_receipt": liveness_receipt,
    }


def parse_capability_registry(raw: bytes) -> dict[str, Any]:
    """Validate the closed status projection emitted by the canonical adoption gate."""

    if len(raw) > MAX_REGISTRY_BYTES:
        raise RuntimeMapError("capability registry exceeds the byte ceiling")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeMapError("capability registry is not strict UTF-8 JSON") from exc
    registry = _closed(value, _TOP_LEVEL_FIELDS, "capability registry")
    if (
        registry["schema"] != REGISTRY_SCHEMA
        or registry["authority"] != REGISTRY_AUTHORITY
        or registry["source_authority"] not in {"git-head", "uncommitted-development"}
        or registry["execution_authority_granted"] is not False
    ):
        raise RuntimeMapError("capability registry authority boundary is invalid")
    _timestamp(registry["observed_at"], "registry observed_at")
    recorded_hash = registry["registry_sha256"]
    if not isinstance(recorded_hash, str) or _SHA256.fullmatch(recorded_hash) is None:
        raise RuntimeMapError("capability registry hash is invalid")
    unsigned = dict(registry)
    del unsigned["registry_sha256"]
    calculated_hash = hashlib.sha256(
        json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    if calculated_hash != recorded_hash:
        raise RuntimeMapError("capability registry self hash differs")
    if not isinstance(registry["capabilities"], list):
        raise RuntimeMapError("capabilities must be an array")
    capabilities = [_capability(item) for item in registry["capabilities"]]
    if len({item["id"] for item in capabilities}) != len(capabilities):
        raise RuntimeMapError("capability ids are not unique")
    socket = _closed(
        registry["retrospective_socket"],
        {"schema", "feeds", "candidates", "promotion_authority"},
        "retrospective socket",
    )
    if (
        socket["promotion_authority"] is not False
        or not isinstance(socket["feeds"], list)
        or not isinstance(socket["candidates"], list)
    ):
        raise RuntimeMapError("retrospective socket authority boundary is invalid")
    if not isinstance(registry["summary"], dict):
        raise RuntimeMapError("capability registry summary must be an object")
    return {
        **registry,
        "capabilities": capabilities,
        "retrospective_socket": dict(socket),
    }


def load_runtime_registry(path: Path, scanned_root: Path) -> RuntimeRegistryInput:
    """Read one private, stable, external registry snapshot without following symlinks."""

    absolute = path.absolute()
    try:
        supplied_metadata = absolute.lstat()
    except OSError as exc:
        raise RuntimeMapError("runtime registry is missing") from exc
    resolved = absolute.resolve(strict=True)
    if (
        absolute != resolved
        or stat.S_ISLNK(supplied_metadata.st_mode)
        or not stat.S_ISREG(supplied_metadata.st_mode)
    ):
        raise RuntimeMapError("runtime registry path must be canonical and non-symlink")
    try:
        resolved.relative_to(scanned_root.resolve(strict=True))
    except ValueError:
        pass
    else:
        raise RuntimeMapError(
            "runtime registry must live outside the scanned repository"
        )
    descriptor = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_size > MAX_REGISTRY_BYTES
        ):
            raise RuntimeMapError(
                "runtime registry must be a private single-link regular file"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        if identity != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise RuntimeMapError("runtime registry changed while it was read")
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    return RuntimeRegistryInput(
        path=resolved,
        file_sha256=sha256_bytes(raw),
        bytes=len(raw),
        registry=parse_capability_registry(raw),
    )


RUNTIME_POLICY_SHA256 = sha256_bytes(
    canonical_bytes(
        {
            "capability_states": sorted(CAPABILITY_STATES),
            "policy": RUNTIME_POLICY_VERSION,
            "registry_authority": REGISTRY_AUTHORITY,
            "registry_schema": REGISTRY_SCHEMA,
            "trigger_kinds": sorted(TRIGGER_KINDS),
        }
    )
)
