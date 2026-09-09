"""Read-only verification of the complete immutable export authority set."""

from __future__ import annotations

import json
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .integrity import SHA256, authority_path, verify_hash_baseline


class ExportProtectionError(RuntimeError):
    pass


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExportProtectionError(f"cannot load export protection evidence: {path}") from exc


def _baseline_entries(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or not SHA256.fullmatch(parts[0]):
            raise ExportProtectionError(f"invalid baseline line {number}")
        relative = parts[1].strip()
        if relative in entries:
            raise ExportProtectionError(f"duplicate baseline path: {relative}")
        entries[relative] = parts[0]
    return entries


def _unsafe(name: str) -> bool:
    candidate = PurePosixPath(name.replace("\\", "/"))
    return candidate.is_absolute() or ".." in candidate.parts


def _zip_integrity(path: Path, full_crc: bool) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        failed_member = archive.testzip() if full_crc else None
    return {
        "entries": len(infos),
        "unsafe_paths": sum(_unsafe(name) for name in names),
        "encrypted_entries": sum(bool(item.flag_bits & 1) for item in infos),
        "duplicate_names": len(names) - len(set(names)),
        "symlink_entries": sum(stat.S_ISLNK((item.external_attr >> 16) & 0o170000) for item in infos),
        "crc": "pass" if full_crc and failed_member is None else ("not-run" if not full_crc else "fail"),
    }


def verify_export_set(
    workspace_root: Path,
    evidence_root: Path,
    *,
    policy_path: Path,
    full_crc: bool = False,
) -> dict[str, Any]:
    if workspace_root.is_symlink() or evidence_root.is_symlink():
        raise ExportProtectionError("authority roots must not be symlinks")
    workspace_root, evidence_root = workspace_root.resolve(), evidence_root.resolve()
    try:
        policy_file = authority_path(workspace_root, str(policy_path))
        policy = _load(policy_file)
        ledger_file = authority_path(workspace_root, policy["ledger"])
        baseline_path = authority_path(workspace_root, policy["baseline"])
        ledger = _load(ledger_file)
    except (ValueError, TypeError, KeyError) as exc:
        raise ExportProtectionError("invalid policy authority path") from exc
    baseline = _baseline_entries(baseline_path)
    authorities = [asset for asset in ledger["assets"] if asset.get("authority_role") == "immutable_original"]
    errors: list[str] = []
    if len(authorities) != policy["authority_count"]:
        errors.append("ledger authority count disagrees with policy")
    expected = {asset["relative_path"]: asset["sha256"] for asset in authorities}
    if baseline != expected:
        errors.append("baseline is not exactly the immutable-original ledger set")
    if len(expected) != len(authorities):
        errors.append("duplicate ledger authority")
    try:
        sources = {relative: authority_path(evidence_root, relative) for relative in expected}
        for relative in baseline:
            authority_path(evidence_root, relative)
    except (ValueError, TypeError) as exc:
        raise ExportProtectionError("invalid export authority path") from exc
    if errors:
        raise ExportProtectionError("; ".join(errors))
    hashes = verify_hash_baseline(evidence_root, baseline_path)
    if not hashes["ok"]:
        errors.append("one or more immutable export hashes failed")

    archive_checks: dict[str, Any] = {}
    modes: dict[str, str | None] = {}
    immutable_flags: dict[str, bool] = {}
    for asset in authorities:
        relative = asset["relative_path"]
        source = sources[relative]
        if source.is_file():
            mode = f"{stat.S_IMODE(source.stat().st_mode):04o}"
            modes[relative] = mode
            immutable_flags[relative] = bool(getattr(source.stat(), "st_flags", 0) & getattr(stat, "UF_IMMUTABLE", 0))
        else:
            modes[relative] = None
            immutable_flags[relative] = False
        if asset["format"] == "zip" and source.is_file() and hashes["ok"]:
            try:
                observed = _zip_integrity(source, full_crc)
            except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
                raise ExportProtectionError(f"cannot verify ZIP authority: {relative}") from exc
            archive_checks[relative] = observed
            if any(observed[key] for key in ("unsafe_paths", "encrypted_entries", "duplicate_names", "symlink_entries")):
                errors.append(f"unsafe ZIP structure: {relative}")
            if full_crc and observed["crc"] != "pass":
                errors.append(f"ZIP CRC failure: {relative}")

    permission_gaps = sorted(path for path, mode in modes.items() if mode != policy["required_source_mode"])
    immutable_gaps = sorted(path for path, enabled in immutable_flags.items() if not enabled)
    operational_blockers = []
    if permission_gaps:
        operational_blockers.append("source-permissions")
    if immutable_gaps:
        operational_blockers.append("filesystem-immutable-flags")
    if policy["encrypted_content_addressed_vault_required"]:
        operational_blockers.append("encrypted-two-copy-vault-and-restore-drill")
    return {
        "schema": "giga.export-protection-verification.v1",
        "workspace_root": str(workspace_root),
        "evidence_root": str(evidence_root),
        "authority_count": len(authorities),
        "baseline_complete": baseline == expected,
        "hashes": hashes,
        "archive_checks": archive_checks,
        "full_crc": full_crc,
        "source_mutation_performed": False,
        "permission_gaps": permission_gaps,
        "immutable_flag_gaps": immutable_gaps,
        "integrity_ok": not errors,
        "operational_acceptance": not errors and not operational_blockers,
        "operational_blockers": operational_blockers,
        "promotion_authorized": False,
        "errors": errors,
    }
