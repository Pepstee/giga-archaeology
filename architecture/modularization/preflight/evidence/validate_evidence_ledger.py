#!/usr/bin/env python3
"""Deterministic validator for the GIGA immutable-evidence ledger.

The validator never extracts an archive or parses message semantics. It checks
bytes, paths, archive metadata, source-manifest bindings, and filesystem modes.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import stat
import subprocess
import sys
import tarfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
DEFAULT_LEDGER = HERE / "RAW_SOURCE_EXPORT_LEDGER.json"
HEX = set("0123456789abcdef")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_mode(path: Path) -> str:
    return f"{stat.S_IMODE(path.stat().st_mode):04o}"


def _unsafe_archive_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    candidate = PurePosixPath(normalized)
    return candidate.is_absolute() or ".." in candidate.parts


def _zip_is_dir(name: str) -> bool:
    return name.endswith(("/", "\\"))


def zip_observation(path: Path, full_crc: bool = False) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        result: dict[str, Any] = {
            "entries": len(infos),
            "file_entries": sum(not _zip_is_dir(name) for name in names),
            "directory_entries": sum(_zip_is_dir(name) for name in names),
            "compressed_member_bytes": sum(item.compress_size for item in infos),
            "uncompressed_bytes": sum(item.file_size for item in infos),
            "unsafe_paths": sum(_unsafe_archive_name(name) for name in names),
            "encrypted_entries": sum(bool(item.flag_bits & 1) for item in infos),
            "duplicate_names": len(names) - len(set(names)),
            "symlink_entries": sum(
                stat.S_ISLNK((item.external_attr >> 16) & 0o170000)
                for item in infos
            ),
        }
        if full_crc:
            result["crc_test"] = "pass" if archive.testzip() is None else "fail"
        return result


def zip_member_tree_sha256(path: Path) -> str:
    rows: list[tuple[str, int, str]] = []
    with zipfile.ZipFile(path, "r") as archive:
        for item in archive.infolist():
            if _zip_is_dir(item.filename):
                continue
            payload = archive.read(item)
            rows.append(
                (
                    item.filename.replace("\\", "/"),
                    len(payload),
                    hashlib.sha256(payload).hexdigest(),
                )
            )
    return digest_rows(rows)


def tree_observation(path: Path) -> dict[str, Any]:
    rows: list[tuple[str, int, str]] = []
    symlinks = 0
    modes: Counter[str] = Counter()
    for candidate in sorted(
        path.rglob("*"), key=lambda item: item.relative_to(path).as_posix()
    ):
        if candidate.is_symlink():
            symlinks += 1
            continue
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(path).as_posix()
        size = candidate.stat().st_size
        rows.append((relative, size, sha256_file(candidate)))
        modes[file_mode(candidate)] += 1
    return {
        "files": len(rows),
        "bytes": sum(size for _, size, _ in rows),
        "tree_sha256": digest_rows(rows),
        "symlinks": symlinks,
        "root_mode": file_mode(path),
        "file_modes": dict(sorted(modes.items())),
    }


def digest_rows(rows: Iterable[tuple[str, int, str]]) -> str:
    digest = hashlib.sha256()
    for relative, size, file_hash in sorted(rows):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def tar_observation(path: Path) -> dict[str, Any]:
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
    names = [member.name for member in members]
    return {
        "entries": len(members),
        "regular_files": sum(member.isfile() for member in members),
        "directories": sum(member.isdir() for member in members),
        "symlinks": sum(member.issym() or member.islnk() for member in members),
        "uncompressed_regular_bytes": sum(
            member.size for member in members if member.isfile()
        ),
        "unsafe_paths": sum(_unsafe_archive_name(name) for name in names),
        "duplicate_names": len(names) - len(set(names)),
        "listing": "pass",
    }


def _archive_suffix(path: Path, extensions: list[str]) -> str | None:
    lowered = path.name.casefold()
    for suffix in sorted(extensions, key=len, reverse=True):
        if lowered.endswith(suffix.casefold()):
            return suffix
    return None


def discover_archives(repo: Path, discovery: dict[str, Any]) -> list[str]:
    excluded_names = set(discovery["excluded_directory_names"])
    fragments = tuple(discovery["excluded_path_fragments_casefold"])
    found: list[str] = []
    for root, directories, files in os.walk(repo, followlinks=False):
        root_path = Path(root)
        directories[:] = [
            directory
            for directory in directories
            if directory not in excluded_names
            and not any(
                fragment in (root_path / directory).relative_to(repo).as_posix().casefold()
                for fragment in fragments
            )
        ]
        for filename in files:
            candidate = root_path / filename
            relative = candidate.relative_to(repo).as_posix()
            if any(fragment in relative.casefold() for fragment in fragments):
                continue
            if _archive_suffix(candidate, discovery["extensions"]):
                found.append(relative)
    return sorted(found)


def _claude_manifest_path(row: dict[str, str], mapping: str) -> str | None:
    bucket = row["Bucket"]
    relative = row["RelativePath"].replace("\\", "/")
    if mapping == "uk_claude_archive":
        if bucket == "raw/claude/local-agent-mode-sessions":
            return "local-agent-mode-sessions/" + relative
        if bucket == "restricted/claude":
            return relative
        if bucket == "restricted/claude/.claude":
            return ".claude/" + relative
        return None
    if mapping == "uk_claude_raw":
        if bucket != "raw/claude/local-agent-mode-sessions":
            return None
        return "local-agent-mode-sessions/" + relative
    if mapping == "uk_claude_restricted":
        if bucket == "restricted/claude":
            return relative
        if bucket == "restricted/claude/.claude":
            return ".claude/" + relative
        return None
    raise ValueError(f"unsupported Claude mapping: {mapping}")


def manifest_binding_observation(
    repo: Path, asset_path: Path, binding: dict[str, Any], kind: str
) -> dict[str, Any]:
    manifest = repo / binding["manifest_path"]
    mapping = binding["mapping"]
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    expected: dict[str, tuple[int, str]] = {}
    if mapping.startswith("uk_claude_"):
        for row in rows:
            mapped = _claude_manifest_path(row, mapping)
            if mapped is not None:
                expected[mapped] = (int(row["Bytes"]), row["SHA256"].lower())
    elif mapping in {"uk_codex_archive", "uk_codex_snapshot"}:
        expected = {
            row["RelativePath"].replace("\\", "/"): (
                int(row["Bytes"]),
                row["SHA256"].lower(),
            )
            for row in rows
        }
    else:
        raise ValueError(f"unsupported manifest mapping: {mapping}")

    actual: dict[str, tuple[int, str]] = {}
    if kind == "archive":
        with zipfile.ZipFile(asset_path, "r") as archive:
            for item in archive.infolist():
                if _zip_is_dir(item.filename):
                    continue
                name = item.filename.replace("\\", "/")
                if mapping == "uk_codex_archive":
                    if name == "CODEX_SOURCE_SHA256.csv":
                        actual[name] = (
                            item.file_size,
                            hashlib.sha256(archive.read(item)).hexdigest(),
                        )
                        continue
                    prefix = "codex/"
                    if not name.startswith(prefix):
                        actual[name] = (
                            item.file_size,
                            hashlib.sha256(archive.read(item)).hexdigest(),
                        )
                        continue
                    name = name[len(prefix) :]
                payload = archive.read(item)
                actual[name] = (len(payload), hashlib.sha256(payload).hexdigest())
    else:
        for candidate in asset_path.rglob("*"):
            if candidate.is_file() and not candidate.is_symlink():
                relative = candidate.relative_to(asset_path).as_posix()
                actual[relative] = (candidate.stat().st_size, sha256_file(candidate))

    shared = set(expected) & set(actual)
    changed = sorted(name for name in shared if expected[name] != actual[name])
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    return {
        "manifest_rows_considered": len(expected),
        "matched": sum(expected[name] == actual[name] for name in shared),
        "missing": missing,
        "changed": changed,
        "extra": extra,
    }


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in HEX for character in value)
    )


def _compare(
    label: str, expected: Any, actual: Any, errors: list[str]
) -> None:
    if expected != actual:
        errors.append(f"{label}: expected {expected!r}, observed {actual!r}")


def load_ledger(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        ledger = json.load(handle)
    if ledger.get("schema") != "giga.immutable-evidence-ledger.v1":
        raise ValueError("unsupported or missing ledger schema")
    return ledger


def resolve_repo(ledger_path: Path, ledger: dict[str, Any]) -> Path:
    declared = ledger.get("repository_root", ".")
    if declared != ".":
        return Path(declared).expanduser().resolve()
    # evidence -> preflight -> modularization -> architecture -> repository root
    return ledger_path.resolve().parents[4]


def validate(
    ledger_path: Path,
    *,
    mode: str = "inventory",
    full_crc: bool = False,
    repo_override: Path | None = None,
) -> dict[str, Any]:
    ledger = load_ledger(ledger_path)
    repo = repo_override.resolve() if repo_override else resolve_repo(ledger_path, ledger)
    errors: list[str] = []
    warnings: list[str] = []
    hash_cache: dict[Path, str] = {}

    def cached_hash(path: Path) -> str:
        if path not in hash_cache:
            hash_cache[path] = sha256_file(path)
        return hash_cache[path]

    assets = ledger.get("assets", [])
    ids = [asset.get("id") for asset in assets]
    if len(ids) != len(set(ids)):
        errors.append("asset IDs are not unique")

    for asset in assets:
        asset_id = asset["id"]
        relative = asset["relative_path"]
        candidate_relative = PurePosixPath(relative)
        if candidate_relative.is_absolute() or ".." in candidate_relative.parts:
            errors.append(f"{asset_id}: unsafe relative path")
            continue
        if "dubbing-studio" in relative.casefold():
            errors.append(f"{asset_id}: Dubbing Studio is outside scope")
            continue
        candidate = repo / relative
        if not candidate.exists():
            errors.append(f"{asset_id}: missing {relative}")
            continue

        kind = asset["kind"]
        if kind in {"file", "archive"}:
            if not candidate.is_file() or candidate.is_symlink():
                errors.append(f"{asset_id}: expected regular non-symlink file")
                continue
            _compare(
                f"{asset_id}.size_bytes",
                asset["size_bytes"],
                candidate.stat().st_size,
                errors,
            )
            if not _valid_sha256(asset["sha256"]):
                errors.append(f"{asset_id}: invalid recorded SHA-256")
            else:
                _compare(
                    f"{asset_id}.sha256",
                    asset["sha256"],
                    cached_hash(candidate),
                    errors,
                )
            _compare(
                f"{asset_id}.mode",
                asset["permissions"]["mode"],
                file_mode(candidate),
                errors,
            )
            if asset.get("format") == "zip":
                observed = zip_observation(candidate, full_crc=full_crc)
                for key, expected in asset["archive_integrity"].items():
                    if key == "member_tree_sha256":
                        actual = zip_member_tree_sha256(candidate)
                    elif key == "crc_test" and not full_crc:
                        continue
                    else:
                        actual = observed.get(key)
                    _compare(
                        f"{asset_id}.archive_integrity.{key}",
                        expected,
                        actual,
                        errors,
                    )
        elif kind == "directory":
            if not candidate.is_dir() or candidate.is_symlink():
                errors.append(f"{asset_id}: expected non-symlink directory")
                continue
            observed_tree = tree_observation(candidate)
            for key, expected in asset["tree_observation"].items():
                _compare(
                    f"{asset_id}.tree_observation.{key}",
                    expected,
                    observed_tree.get(key),
                    errors,
                )
        else:
            errors.append(f"{asset_id}: unsupported kind {kind!r}")

        for reference in asset.get("consumer_references", []):
            if not (repo / reference).exists():
                errors.append(f"{asset_id}: missing consumer reference {reference}")
        for reference in asset.get("baseline_coverage", []):
            if not (repo / reference).exists():
                errors.append(f"{asset_id}: missing baseline reference {reference}")
        if asset.get("manifest_binding"):
            try:
                observed_binding = manifest_binding_observation(
                    repo, candidate, asset["manifest_binding"], kind
                )
                for key, expected in asset["manifest_binding"]["expected"].items():
                    _compare(
                        f"{asset_id}.manifest_binding.{key}",
                        expected,
                        observed_binding.get(key),
                        errors,
                    )
            except Exception as exc:  # deterministic error reporting
                errors.append(f"{asset_id}: manifest binding failed: {exc}")
        for gap in asset.get("protection_gaps", []):
            warnings.append(f"{asset_id}: {gap}")

    discovery = ledger["archive_discovery"]
    expected_archives = sorted(
        item["relative_path"] for item in discovery["inventory"]
    )
    actual_archives = discover_archives(repo, discovery)
    _compare("archive_discovery.paths", expected_archives, actual_archives, errors)

    for item in discovery["inventory"]:
        candidate = repo / item["relative_path"]
        if not candidate.is_file():
            errors.append(f"archive inventory missing: {item['relative_path']}")
            continue
        _compare(
            f"archive_inventory.{item['relative_path']}.size",
            item["size_bytes"],
            candidate.stat().st_size,
            errors,
        )
        _compare(
            f"archive_inventory.{item['relative_path']}.sha256",
            item["sha256"],
            cached_hash(candidate),
            errors,
        )
        _compare(
            f"archive_inventory.{item['relative_path']}.mode",
            item["mode"],
            file_mode(candidate),
            errors,
        )
        expected_integrity = item.get("integrity")
        if not expected_integrity:
            continue
        archive_format = item["format"]
        if archive_format == "zip":
            observed = zip_observation(candidate, full_crc=full_crc)
            for key, expected in expected_integrity.items():
                if key == "crc_test" and not full_crc:
                    continue
                _compare(
                    f"archive_inventory.{item['relative_path']}.{key}",
                    expected,
                    observed.get(key),
                    errors,
                )
        elif archive_format == "tar.gz":
            observed = tar_observation(candidate)
            for key, expected in expected_integrity.items():
                _compare(
                    f"archive_inventory.{item['relative_path']}.{key}",
                    expected,
                    observed.get(key),
                    errors,
                )
        elif archive_format == "gzip" and full_crc:
            try:
                with gzip.open(candidate, "rb") as handle:
                    for _ in iter(lambda: handle.read(1024 * 1024), b""):
                        pass
            except Exception as exc:
                errors.append(f"{item['relative_path']}: gzip CRC failed: {exc}")
        elif archive_format == "git_bundle":
            result = subprocess.run(
                ["git", "bundle", "verify", str(candidate)],
                cwd=repo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                errors.append(
                    f"{item['relative_path']}: git bundle verification failed"
                )

    if mode == "acceptance":
        readiness = ledger["migration_readiness"]
        if not readiness.get("ready"):
            for finding in readiness.get("blocking_findings", []):
                errors.append(
                    f"{finding['id']} [{finding['severity']}]: {finding['finding']}"
                )

    return {
        "ok": not errors,
        "mode": mode,
        "full_crc": full_crc,
        "repository_root": str(repo),
        "assets_checked": len(assets),
        "archive_like_files_checked": len(discovery["inventory"]),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--mode", choices=("inventory", "acceptance"), default="inventory"
    )
    parser.add_argument(
        "--full-crc",
        action="store_true",
        help="read every compressed member/stream instead of central metadata only",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="override repository root (used by isolated tests)",
    )
    arguments = parser.parse_args(argv)
    try:
        result = validate(
            arguments.ledger,
            mode=arguments.mode,
            full_crc=arguments.full_crc,
            repo_override=arguments.repo_root,
        )
    except Exception as exc:
        result = {
            "ok": False,
            "mode": arguments.mode,
            "errors": [f"validator exception: {exc}"],
            "warnings": [],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
