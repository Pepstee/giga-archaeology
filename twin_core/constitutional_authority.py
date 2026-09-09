"""Fail-closed adapter for the unactivated JSR-005 authority candidate.

The vendored package is evidence, not runtime authority. Production remains
REFUSE until protected governance installs an activation record and pins its
exact digest in this module.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


class AuthorityRefused(RuntimeError):
    """Raised whenever no exact constitutional ALLOW decision is available."""

    def __init__(
        self,
        message: str,
        *,
        durable: bool = False,
        receipt: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.durable = durable
        self.receipt = receipt


_AUTHORITY_ROOT = Path(__file__).resolve().parent / "_authority_vendor"
_AUTHORITY_MANIFEST_SHA256 = "2e5b1a5655e91c30caa552058f90f21fccdf462ff73084bc2e667c86289a9b31"
_AUTHORITY_PROVENANCE_SHA256 = "8afac75fe10207002f6073f86d2d2253e673e10f21d33de25326a234c1ae50a4"
_CONSTITUTION_SHA256 = "dc278a45286ce712683e9660de353cc2c02e0b5d9fa935e96632259730f0c714"
_POLICY_SHA256 = "24392f9ded53a7fd44145e52a2a43d1f689038eddb90beaa75b12f4dd541e935"
_POLICY_FILE_SHA256 = "1eac6acb6c19c7cdd2e4053c538c4bf1e59e883d624324e90e727abb03834953"
_POLICY_PATH = "contracts/constitution/constitution.v1.json"
_ACTIVATION_PATH = Path(__file__).resolve().parent / "runtime-authority-activation.json"

# A protected integration action must populate this exact digest. Merely
# creating an activation file cannot activate production.
_PINNED_ACTIVATION_SHA256: str | None = None

AUTHORITY_STATE = "CANDIDATE_ONLY"
KNOWN_EFFECTS = frozenset(
    {
        "twin-cli.init",
        "twin-cli.validate-memory",
        "twin-cli.health",
        "twin-cli.maturity",
        "twin-cli.verify-exports",
        "twin-cli.register-artifact",
        "twin-cli.verify-artifacts",
        "twin-cli.record-event",
        "twin-cli.compile-proof",
        "twin-cli.reconcile-lineage",
        "jarvis.provider.claude.invoke",
        "jarvis.provider.codex.invoke",
    }
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_GIT_ID = re.compile(r"^[0-9a-f]{40,64}$")
_EFFECT_ID = re.compile(r"^[a-z][a-z0-9.-]{2,127}$")
_GENESIS = "0" * 64
_LEDGER_SCHEMA = "giga.constitution-decision-receipt.v2"
_LEDGER_KEYS = frozenset(
    {
        "schema", "sequence", "recorded_at", "effect", "request_sha256",
        "authority_manifest_sha256", "policy_sha256", "authority_state",
        "decision", "reason_code", "previous_receipt_sha256", "receipt_sha256",
    }
)
_ACTIVATION_KEYS = frozenset(
    {
        "schema", "status", "product_commit", "product_tree",
        "authority_manifest_sha256", "authority_provenance_sha256",
        "policy_sha256", "default_decision", "allowed_effects", "grants",
        "protected_action_receipt_sha256",
    }
)
_GRANT_KEYS = frozenset(
    {"effect", "decision", "capability_id", "work_order_sha256", "request_sha256", "expires_at"}
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _strict_json(data: bytes, label: str) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AuthorityRefused(f"{label}: duplicate field {key}")
            result[key] = value
        return result

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=object_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthorityRefused(f"{label}: invalid JSON") from exc


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise AuthorityRefused("authority manifest contains an unsafe path")
    return path


def _manifest_entries(manifest: Mapping[str, Any]) -> dict[str, tuple[str, int, int]]:
    raw = manifest.get("files")
    entries: dict[str, tuple[str, int, int]] = {}
    if isinstance(raw, dict):
        raise AuthorityRefused("authority manifest uses the wrong files representation")
    elif isinstance(raw, list):
        iterable = raw
    else:
        raise AuthorityRefused("authority manifest has no files inventory")
    for item in iterable:
        if not isinstance(item, dict) or set(item) != {"bytes", "mode", "path", "sha256"}:
            raise AuthorityRefused("authority manifest file record is not exact")
        path = str(_safe_relative_path(item["path"]))
        digest = item["sha256"]
        size = item["bytes"]
        mode = item["mode"]
        if (
            path in entries
            or not isinstance(digest, str)
            or not _HEX64.fullmatch(digest)
            or not isinstance(size, int)
            or size < 0
            or not isinstance(mode, str)
            or not re.fullmatch(r"0[0-7]{3}", mode)
        ):
            raise AuthorityRefused("authority manifest file record is invalid")
        entries[path] = (digest, size, int(mode, 8))
    return entries


def _verify_candidate_directory(
    root: Path = _AUTHORITY_ROOT,
    expected_manifest_sha256: str = _AUTHORITY_MANIFEST_SHA256,
) -> None:
    root_stat = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != os.getuid():
        raise AuthorityRefused("authority root is not an owned real directory")
    manifest_path = root / "manifest.json"
    manifest_stat = manifest_path.lstat()
    if manifest_path.is_symlink() or not stat.S_ISREG(manifest_stat.st_mode) or manifest_stat.st_nlink != 1:
        raise AuthorityRefused("authority manifest path is unsafe")
    manifest_bytes = manifest_path.read_bytes()
    if _sha256(manifest_bytes) != expected_manifest_sha256:
        raise AuthorityRefused("authority manifest identity drift")
    manifest = _strict_json(manifest_bytes, "authority manifest")
    if not isinstance(manifest, dict):
        raise AuthorityRefused("authority manifest is not an object")
    entries = _manifest_entries(manifest)

    observed: set[str] = set()
    verified_bytes: dict[str, bytes] = {}
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in list(directory_names):
            child = base / name
            child_stat = child.lstat()
            if child.is_symlink() or not stat.S_ISDIR(child_stat.st_mode):
                raise AuthorityRefused("authority tree contains a linked or non-directory component")
            if name == "__pycache__":
                raise AuthorityRefused("authority tree contains a bytecode cache")
        for name in file_names:
            child = base / name
            relative = child.relative_to(root).as_posix()
            if name.endswith((".pyc", ".pyo")):
                raise AuthorityRefused("authority tree contains bytecode")
            child_stat = child.lstat()
            if child.is_symlink() or not stat.S_ISREG(child_stat.st_mode) or child_stat.st_nlink != 1:
                raise AuthorityRefused("authority tree contains an unsafe file")
            observed.add(relative)
            data = child.read_bytes()
            post = child.stat(follow_symlinks=False)
            if (child_stat.st_dev, child_stat.st_ino, child_stat.st_size) != (post.st_dev, post.st_ino, post.st_size):
                raise AuthorityRefused("authority file changed during verification")
            verified_bytes[relative] = data

    # provenance.json is the separately pinned assembly receipt and is
    # intentionally outside the candidate's 37-file source inventory.
    if observed != set(entries) | {"manifest.json", "provenance.json"}:
        raise AuthorityRefused("authority tree differs from its exact manifest")
    for relative, (digest, size, mode) in entries.items():
        source_stat = (root / relative).stat(follow_symlinks=False)
        if (
            _sha256(verified_bytes[relative]) != digest
            or len(verified_bytes[relative]) != size
            or stat.S_IMODE(source_stat.st_mode) != mode
        ):
            raise AuthorityRefused(f"authority file identity drift: {relative}")
    if _sha256(verified_bytes.get("provenance.json", b"")) != _AUTHORITY_PROVENANCE_SHA256:
        raise AuthorityRefused("authority provenance identity drift")
    if _sha256(verified_bytes.get(_POLICY_PATH, b"")) != _POLICY_FILE_SHA256:
        raise AuthorityRefused("Constitution policy identity drift")
    provenance = _strict_json(verified_bytes["provenance.json"], "authority provenance")
    if b'"protected_integration":false' not in _canonical(provenance):
        raise AuthorityRefused("authority provenance is not candidate-only")

    with tempfile.TemporaryDirectory(prefix="giga-authority-snapshot-") as temporary:
        snapshot = Path(temporary)
        for relative, data in verified_bytes.items():
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes(data)
            if relative in entries:
                target.chmod(entries[relative][2])
        runner = (
            "import runpy,sys; sys.path.insert(0,sys.argv[1]); "
            "sys.argv=['giga_control','check']; runpy.run_module('giga_control',run_name='__main__')"
        )
        environment = {
            "HOME": temporary, "LANG": "C", "LC_ALL": "C", "PATH": os.defpath,
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
        }
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", runner, str(snapshot)],
            cwd=snapshot, env=environment, capture_output=True, text=True,
            timeout=30, check=False,
        )
        if result.returncode != 0:
            raise AuthorityRefused("canonical authority foundation check failed")


def _verify_candidate(
    root: Path | None = None,
    expected_manifest_sha256: str = _AUTHORITY_MANIFEST_SHA256,
) -> None:
    """Verify the same pinned candidate from its bytecode-free package transport."""
    if root is not None:
        _verify_candidate_directory(root, expected_manifest_sha256)
        return
    archive_path = Path(__file__).with_name("_authority_vendor.zip")
    if archive_path.is_symlink() or not archive_path.is_file():
        raise AuthorityRefused("candidate archive is unavailable or linked")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(infos) != 39 or len(set(names)) != len(names):
                raise AuthorityRefused("candidate archive inventory differs")
            if sum(item.file_size for item in infos) > 2 * 1024 * 1024:
                raise AuthorityRefused("candidate archive exceeds its bounded size")
            with tempfile.TemporaryDirectory(prefix="giga-authority-package-") as temporary:
                stage = Path(temporary)
                for item in infos:
                    relative = _safe_relative_path(item.filename)
                    mode = item.external_attr >> 16
                    if not stat.S_ISREG(mode) or stat.S_IMODE(mode) not in {0o644, 0o755}:
                        raise AuthorityRefused("candidate archive member mode is unsafe")
                    target = stage.joinpath(*relative.parts)
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    target.write_bytes(archive.read(item))
                    target.chmod(stat.S_IMODE(mode))
                _verify_candidate_directory(stage, expected_manifest_sha256)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        if isinstance(exc, AuthorityRefused):
            raise
        raise AuthorityRefused("candidate archive cannot be verified") from exc


def candidate_status() -> Mapping[str, Any]:
    """Inspect only packaged candidate bytes, without reading activation or state."""
    _verify_candidate()
    return {
        "schema": "giga.authority-candidate-status.v1",
        "authority_state": AUTHORITY_STATE,
        "candidate_verified": True,
        "activation_pinned": _PINNED_ACTIVATION_SHA256 is not None,
        "decision": "REFUSE",
        "reason_code": "RUNTIME_ACTIVATION_REQUIRED",
        "authority_manifest_sha256": _AUTHORITY_MANIFEST_SHA256,
        "authority_provenance_sha256": _AUTHORITY_PROVENANCE_SHA256,
        "host_bound_corpus_authority": "UNAVAILABLE",
    }


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AuthorityRefused(f"{label}: invalid timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AuthorityRefused(f"{label}: invalid timestamp") from exc


def _activation_decision(
    effect: str,
    request_sha256: str,
    activation_bytes: bytes,
    expected_sha256: str,
    *,
    now: datetime | None = None,
) -> tuple[str, str, str]:
    """Evaluate exact grants. Tests may call this with an explicit fixture only."""
    if not _HEX64.fullmatch(expected_sha256) or _sha256(activation_bytes) != expected_sha256:
        raise AuthorityRefused("activation identity drift")
    activation = _strict_json(activation_bytes, "activation")
    if not isinstance(activation, dict) or set(activation) != _ACTIVATION_KEYS:
        raise AuthorityRefused("activation schema fields are not exact")
    if activation["schema"] != "giga.runtime-authority-activation.v1" or activation["status"] != "ACTIVE":
        raise AuthorityRefused("activation is not active")
    if activation["authority_manifest_sha256"] != _AUTHORITY_MANIFEST_SHA256:
        raise AuthorityRefused("activation manifest identity drift")
    if activation["authority_provenance_sha256"] != _AUTHORITY_PROVENANCE_SHA256:
        raise AuthorityRefused("activation provenance identity drift")
    if activation["policy_sha256"] != _POLICY_SHA256 or activation["default_decision"] != "DENY":
        raise AuthorityRefused("activation policy is not exact default-deny")
    if not isinstance(activation["product_commit"], str) or not _GIT_ID.fullmatch(activation["product_commit"]):
        raise AuthorityRefused("activation product commit is invalid")
    if not isinstance(activation["product_tree"], str) or not _GIT_ID.fullmatch(activation["product_tree"]):
        raise AuthorityRefused("activation product tree is invalid")
    receipt = activation["protected_action_receipt_sha256"]
    if not isinstance(receipt, str) or not _HEX64.fullmatch(receipt):
        raise AuthorityRefused("activation has no protected action receipt")
    allowed = activation["allowed_effects"]
    grants = activation["grants"]
    if not isinstance(allowed, list) or allowed != sorted(set(allowed)) or not set(allowed).issubset(KNOWN_EFFECTS):
        raise AuthorityRefused("activation allowed-effect set is invalid")
    if not isinstance(grants, list):
        raise AuthorityRefused("activation grants are invalid")
    grant_effects: set[str] = set()
    current = now or datetime.now(timezone.utc)
    for grant in grants:
        if not isinstance(grant, dict) or set(grant) != _GRANT_KEYS:
            raise AuthorityRefused("activation grant fields are not exact")
        grant_effect = grant["effect"]
        if grant_effect in grant_effects or grant_effect not in KNOWN_EFFECTS or grant["decision"] != "ALLOW":
            raise AuthorityRefused("activation grant is invalid")
        for field in ("work_order_sha256", "request_sha256"):
            if not isinstance(grant[field], str) or not _HEX64.fullmatch(grant[field]):
                raise AuthorityRefused(f"activation grant {field} is invalid")
        if not isinstance(grant["capability_id"], str) or not grant["capability_id"]:
            raise AuthorityRefused("activation grant capability is invalid")
        if _parse_time(grant["expires_at"], "activation grant") <= current:
            raise AuthorityRefused("activation grant is expired")
        grant_effects.add(grant_effect)
    if grant_effects != set(allowed):
        raise AuthorityRefused("activation grants differ from the allowed-effect set")
    if effect not in KNOWN_EFFECTS or effect not in grant_effects:
        return "ACTIVATED", "REFUSE", "UNKNOWN_OR_UNGRANTED_EFFECT"
    matching = next(grant for grant in grants if grant["effect"] == effect)
    if matching["request_sha256"] != request_sha256:
        return "ACTIVATED", "REFUSE", "REQUEST_NOT_GRANTED"
    return "ACTIVATED", "ALLOW", "ACTIVATED_EXACT_GRANT"


def _validate_receipt(receipt: Any, sequence: int, previous: str) -> str:
    if not isinstance(receipt, dict) or set(receipt) != _LEDGER_KEYS:
        raise AuthorityRefused("decision ledger receipt fields are not exact")
    if receipt["schema"] != _LEDGER_SCHEMA or receipt["sequence"] != sequence:
        raise AuthorityRefused("decision ledger sequence/schema is invalid")
    _parse_time(receipt["recorded_at"], "decision ledger")
    effect = receipt["effect"]
    if not isinstance(effect, str) or not _EFFECT_ID.fullmatch(effect):
        raise AuthorityRefused("decision ledger effect is invalid")
    for field in ("request_sha256", "authority_manifest_sha256", "policy_sha256", "previous_receipt_sha256", "receipt_sha256"):
        if not isinstance(receipt[field], str) or not _HEX64.fullmatch(receipt[field]):
            raise AuthorityRefused(f"decision ledger {field} is invalid")
    if receipt["authority_manifest_sha256"] != _AUTHORITY_MANIFEST_SHA256 or receipt["policy_sha256"] != _POLICY_SHA256:
        raise AuthorityRefused("decision ledger policy identity is invalid")
    if receipt["previous_receipt_sha256"] != previous:
        raise AuthorityRefused("decision ledger predecessor is forged")
    if receipt["authority_state"] not in {"CANDIDATE_ONLY", "ACTIVATED"}:
        raise AuthorityRefused("decision ledger authority state is invalid")
    if receipt["decision"] not in {"ALLOW", "REFUSE"} or not isinstance(receipt["reason_code"], str):
        raise AuthorityRefused("decision ledger decision is invalid")
    if receipt["decision"] == "ALLOW":
        raise AuthorityRefused("candidate-only decision ledger contains ALLOW")
    if effect not in KNOWN_EFFECTS and receipt["decision"] != "REFUSE":
        raise AuthorityRefused("decision ledger permits an unknown effect")
    unsigned = dict(receipt)
    claimed = unsigned.pop("receipt_sha256")
    if _sha256(_canonical(unsigned)) != claimed:
        raise AuthorityRefused("decision ledger self-hash is forged")
    return claimed


def _private_parent(path: Path) -> int:
    parent = path.parent
    try:
        parent_lstat = parent.lstat()
    except OSError as exc:
        raise AuthorityRefused("decision ledger parent is unavailable") from exc
    if parent.is_symlink() or not stat.S_ISDIR(parent_lstat.st_mode) or parent_lstat.st_uid != os.getuid():
        raise AuthorityRefused("decision ledger parent is not an owned real directory")
    if stat.S_IMODE(parent_lstat.st_mode) & 0o077:
        raise AuthorityRefused("decision ledger parent is not private")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(parent, flags)
    opened = os.fstat(directory_fd)
    if (opened.st_dev, opened.st_ino) != (parent_lstat.st_dev, parent_lstat.st_ino):
        os.close(directory_fd)
        raise AuthorityRefused("decision ledger parent changed during open")
    return directory_fd


def ensure_private_state_parent(path: Path) -> Path:
    """Create an absent private parent or validate an existing one without repairing it."""
    parent = Path(path).parent
    try:
        parent_lstat = parent.lstat()
    except FileNotFoundError:
        grandparent = parent.parent
        grand_lstat = grandparent.lstat()
        if (
            grandparent.is_symlink()
            or not stat.S_ISDIR(grand_lstat.st_mode)
            or grand_lstat.st_uid != os.getuid()
        ):
            raise AuthorityRefused("state parent owner directory is unsafe")
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        grand_fd = os.open(grandparent, flags)
        try:
            opened_grand = os.fstat(grand_fd)
            if (opened_grand.st_dev, opened_grand.st_ino) != (
                grand_lstat.st_dev,
                grand_lstat.st_ino,
            ):
                raise AuthorityRefused("state parent owner directory changed during open")
            try:
                os.mkdir(parent.name, 0o700, dir_fd=grand_fd)
            except FileExistsError as exc:
                raise AuthorityRefused("state parent appeared during exclusive creation") from exc
        finally:
            os.close(grand_fd)
        parent_lstat = parent.lstat()
    except OSError as exc:
        raise AuthorityRefused("state parent is unavailable") from exc

    if (
        parent.is_symlink()
        or not stat.S_ISDIR(parent_lstat.st_mode)
        or parent_lstat.st_uid != os.getuid()
        or stat.S_IMODE(parent_lstat.st_mode) != 0o700
    ):
        raise AuthorityRefused("state parent is not an owned real 0700 directory")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_fd = os.open(parent, flags)
    try:
        opened_parent = os.fstat(parent_fd)
        if (
            (opened_parent.st_dev, opened_parent.st_ino)
            != (parent_lstat.st_dev, parent_lstat.st_ino)
            or opened_parent.st_uid != os.getuid()
            or not stat.S_ISDIR(opened_parent.st_mode)
            or stat.S_IMODE(opened_parent.st_mode) != 0o700
        ):
            raise AuthorityRefused("state parent changed during validation")
    finally:
        os.close(parent_fd)
    return parent


def _append_receipt(path: Path, unsigned: dict[str, Any]) -> dict[str, Any]:
    if path.name in {"", ".", ".."} or path.parent == path:
        raise AuthorityRefused("decision ledger path is invalid")
    directory_fd = _private_parent(path)
    fd = -1
    created = False
    try:
        flags = os.O_RDWR | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path.name, flags, dir_fd=directory_fd)
        except FileNotFoundError:
            try:
                fd = os.open(path.name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory_fd)
                created = True
            except FileExistsError:
                fd = os.open(path.name, flags, dir_fd=directory_fd)
        fcntl.flock(fd, fcntl.LOCK_EX)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_nlink != 1:
            raise AuthorityRefused("decision ledger is not an owned single-link regular file")
        if created:
            os.fchmod(fd, 0o600)
            before = os.fstat(fd)
        elif stat.S_IMODE(before.st_mode) != 0o600:
            raise AuthorityRefused("decision ledger is not private")

        os.lseek(fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = before.st_size
        if remaining > 16 * 1024 * 1024:
            raise AuthorityRefused("decision ledger exceeds the bounded size")
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                raise AuthorityRefused("decision ledger truncated during read")
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        previous = _GENESIS
        sequence = 0
        if raw:
            if not raw.endswith(b"\n"):
                raise AuthorityRefused("decision ledger has a partial tail")
            for line in raw.splitlines():
                if not line or len(line) > 65536:
                    raise AuthorityRefused("decision ledger line is invalid")
                previous = _validate_receipt(_strict_json(line, "decision ledger"), sequence, previous)
                sequence += 1

        unsigned["sequence"] = sequence
        unsigned["previous_receipt_sha256"] = previous
        receipt = dict(unsigned)
        receipt["receipt_sha256"] = _sha256(_canonical(unsigned))
        _validate_receipt(receipt, sequence, previous)
        encoded = _canonical(receipt) + b"\n"
        if os.write(fd, encoded) != len(encoded):
            raise AuthorityRefused("decision ledger append was partial")
        os.fsync(fd)
        after = os.fstat(fd)
        if (
            (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            or after.st_nlink != 1
            or not stat.S_ISREG(after.st_mode)
            or stat.S_IMODE(after.st_mode) != 0o600
            or after.st_size != before.st_size + len(encoded)
        ):
            raise AuthorityRefused("decision ledger changed during append")
        return receipt
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(directory_fd)


def require_authority(*, effect: str, decision_ledger: Path, request: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return only after a durable exact ALLOW; otherwise durably refuse and raise."""
    if not isinstance(effect, str) or not _EFFECT_ID.fullmatch(effect):
        effect = "invalid.effect"
    request_sha256 = _sha256(_canonical(dict(request)))
    state = AUTHORITY_STATE
    decision = "REFUSE"
    reason = "RUNTIME_ACTIVATION_REQUIRED"
    try:
        _verify_candidate()
        if effect not in KNOWN_EFFECTS:
            reason = "UNKNOWN_EFFECT"
        elif _PINNED_ACTIVATION_SHA256 is None:
            reason = "RUNTIME_ACTIVATION_REQUIRED"
        else:
            activation_stat = _ACTIVATION_PATH.lstat()
            if _ACTIVATION_PATH.is_symlink() or not stat.S_ISREG(activation_stat.st_mode) or activation_stat.st_nlink != 1:
                raise AuthorityRefused("activation path is unsafe")
            state, decision, reason = _activation_decision(
                effect,
                request_sha256,
                _ACTIVATION_PATH.read_bytes(),
                _PINNED_ACTIVATION_SHA256,
            )
    except (AuthorityRefused, OSError, subprocess.SubprocessError):
        state = AUTHORITY_STATE
        decision = "REFUSE"
        reason = "AUTHORITY_VERIFICATION_FAILED"

    unsigned: dict[str, Any] = {
        "schema": _LEDGER_SCHEMA,
        "sequence": 0,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "effect": effect,
        "request_sha256": request_sha256,
        "authority_manifest_sha256": _AUTHORITY_MANIFEST_SHA256,
        "policy_sha256": _POLICY_SHA256,
        "authority_state": state,
        "decision": decision,
        "reason_code": reason,
        "previous_receipt_sha256": _GENESIS,
    }
    receipt = _append_receipt(Path(decision_ledger), unsigned)
    if decision != "ALLOW":
        raise AuthorityRefused(f"{reason}: {effect}", durable=True, receipt=receipt)
    return receipt
