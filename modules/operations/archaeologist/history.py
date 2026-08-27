"""Slice 4: read-only Git and cross-repository variant evidence."""

from __future__ import annotations

import json
import re
import stat
import subprocess
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .counterevidence import COUNTEREVIDENCE_SCHEMA
from .evidence import (
    EvidenceError,
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
    write_atomic,
)
from .hypotheses import HYPOTHESES_SCHEMA
from .inventory import DEFAULT_EXCLUDED_PREFIXES, INVENTORY_SCHEMA


HISTORY_SCHEMA = "giga.archaeologist.history.v1"
OID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
MAX_HISTORY_COMMITS = 50


class HistoryError(ValueError):
    """Historical comparison cannot be completed without weakening evidence."""


def _load(path: Path, schema: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryError("input is not strict UTF-8 JSON") from exc
    try:
        validate_self_hash(value)
    except EvidenceError as exc:
        raise HistoryError(str(exc)) from exc
    if value.get("schema") != schema:
        raise HistoryError(f"unsupported input schema: {value.get('schema')!r}")
    if value.get("authority_granted") is not False or value.get("cleanup_permitted") is not False:
        raise HistoryError("input authority boundary is not closed")
    return value, raw


def _git(root: Path, arguments: Sequence[str], *, ceiling: int = 16 * 1024 * 1024) -> bytes:
    result = subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        env={
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
            "TZ": "UTC",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if len(result.stdout) > ceiling or len(result.stderr) > ceiling:
        raise HistoryError("Git output exceeded evidence ceiling")
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise HistoryError(f"Git read failed ({' '.join(arguments)}): {detail}")
    return result.stdout


def _text(root: Path, arguments: Sequence[str]) -> str:
    try:
        return _git(root, arguments).decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise HistoryError("Git returned non-UTF-8 identity data") from exc


def _repository_snapshot(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    metadata = root.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise HistoryError("comparison repository must be a real directory")
    status = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    refs = _git(
        root,
        ["for-each-ref", "--sort=refname", "--format=%(refname)%00%(objectname)%00%(objecttype)"],
    )
    return {
        "root": str(root),
        "head": _text(root, ["rev-parse", "HEAD"]).strip(),
        "tree": _text(root, ["rev-parse", "HEAD^{tree}"]).strip(),
        "branch": _text(root, ["branch", "--show-current"]).strip(),
        "identity": {
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode),
            "uid": metadata.st_uid,
        },
        "status": {"sha256": sha256_bytes(status), "bytes": len(status)},
        "refs": {"sha256": sha256_bytes(refs), "bytes": len(refs)},
    }


def _excluded(path: str) -> bool:
    value = path + "/"
    return any(
        value.startswith(prefix) or path == prefix.rstrip("/")
        for prefix in DEFAULT_EXCLUDED_PREFIXES
    )


def _head_tree(root: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    raw = _git(root, ["ls-tree", "-r", "-z", "HEAD"])
    by_path: dict[str, str] = {}
    by_basename: dict[str, list[str]] = defaultdict(list)
    for item in raw.split(b"\0"):
        if not item:
            continue
        try:
            metadata, path_raw = item.split(b"\t", 1)
            _mode, kind, oid = metadata.decode("ascii").split(" ")
            path = path_raw.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError) as exc:
            raise HistoryError("malformed Git tree record") from exc
        if kind != "blob" or _excluded(path):
            continue
        by_path[path] = oid
        by_basename[PurePosixPath(path).name].append(path)
    return by_path, {name: sorted(paths) for name, paths in by_basename.items()}


def _versions(root: Path, path: str) -> list[dict[str, str]]:
    commits: list[str] = []
    for arguments in (
        ["log", "--format=%H", "--follow", "--", path],
        ["log", "--all", "--format=%H", "--", path],
    ):
        for commit in _text(root, arguments).splitlines():
            if OID.fullmatch(commit) and commit not in commits:
                commits.append(commit)
            if len(commits) >= MAX_HISTORY_COMMITS:
                break
    versions: list[dict[str, str]] = []
    seen_blobs: set[str] = set()
    for commit in commits:
        result = subprocess.run(
            ["/usr/bin/git", "rev-parse", f"{commit}:{path}"],
            cwd=root,
            env={
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin",
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
        oid = result.stdout.decode("ascii", "ignore").strip()
        if result.returncode == 0 and OID.fullmatch(oid) and oid not in seen_blobs:
            seen_blobs.add(oid)
            versions.append({"commit": commit, "blob_oid": oid, "path": path})
    return versions


def build_history(
    inventory_path: Path,
    hypotheses_path: Path,
    counterevidence_path: Path,
    comparison_repository: Path,
) -> dict[str, Any]:
    inventory, inventory_raw = _load(inventory_path, INVENTORY_SCHEMA)
    hypotheses, hypotheses_raw = _load(hypotheses_path, HYPOTHESES_SCHEMA)
    counterevidence, counterevidence_raw = _load(counterevidence_path, COUNTEREVIDENCE_SCHEMA)
    if hypotheses["inventory"]["receipt_sha256"] != inventory["receipt_sha256"]:
        raise HistoryError("hypotheses do not bind the supplied inventory")
    if counterevidence["inventory"]["receipt_sha256"] != inventory["receipt_sha256"]:
        raise HistoryError("counterevidence inventory binding mismatch")
    if counterevidence["hypotheses"]["receipt_sha256"] != hypotheses["receipt_sha256"]:
        raise HistoryError("counterevidence hypothesis binding mismatch")
    root = Path(inventory["repository"]["root"]).resolve(strict=True)
    comparison = comparison_repository.resolve(strict=True)
    primary_before = _repository_snapshot(root)
    comparison_before = _repository_snapshot(comparison)
    secondary_paths, secondary_names = _head_tree(comparison)
    current_records = {item["path"]: item for item in inventory["files"]}
    paths = sorted({path for item in hypotheses["findings"] for path in item["paths"]})
    path_evidence: dict[str, dict[str, Any]] = {}
    for path in paths:
        current = current_records.get(path)
        if current is None:
            raise HistoryError(f"hypothesis path is absent from inventory: {path}")
        versions = _versions(root, path)
        matches = []
        candidate_paths = set(secondary_names.get(PurePosixPath(path).name, []))
        if path in secondary_paths:
            candidate_paths.add(path)
        for secondary_path in sorted(candidate_paths):
            secondary_oid = secondary_paths[secondary_path]
            relation = (
                "EXACT_GIT_BLOB"
                if secondary_oid == current.get("git_blob_oid")
                else "RELATED_BASENAME_DIFFERENT_BLOB"
            )
            matches.append(
                {"path": secondary_path, "blob_oid": secondary_oid, "relation": relation}
            )
        additional = len({item["blob_oid"] for item in versions}) > 1 or bool(matches)
        path_evidence[path] = {
            "path": path,
            "current_git_blob_oid": current.get("git_blob_oid"),
            "historical_versions": versions,
            "comparison_matches": matches,
            "state": "RELATED_VARIANT_OBSERVED" if additional else "NO_ADDITIONAL_VARIANT_OBSERVED",
            "authority_granted": False,
            "cleanup_permitted": False,
        }
    records = []
    for hypothesis in hypotheses["findings"]:
        evidence = [path_evidence[path] for path in hypothesis["paths"]]
        observed = any(item["state"] == "RELATED_VARIANT_OBSERVED" for item in evidence)
        records.append(
            {
                "hypothesis_id": hypothesis["id"],
                "hypothesis_state": "OBSERVED",
                "historical_state": "RELATED_VARIANT_OBSERVED" if observed else "UNKNOWN",
                "paths": evidence,
                "authority_granted": False,
                "cleanup_permitted": False,
            }
        )
    primary_after = _repository_snapshot(root)
    comparison_after = _repository_snapshot(comparison)
    if primary_before != primary_after or comparison_before != comparison_after:
        raise HistoryError("repository identity, refs or status changed during comparison")
    related = sum(item["historical_state"] == "RELATED_VARIANT_OBSERVED" for item in records)
    return seal_document(
        {
            "schema": HISTORY_SCHEMA,
            "authority": "read-only-historical-evidence",
            "authority_granted": False,
            "cleanup_permitted": False,
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
            },
            "repositories": {"primary": primary_after, "comparison": comparison_after},
            "path_evidence": [path_evidence[path] for path in paths],
            "records": sorted(records, key=lambda item: item["hypothesis_id"]),
            "summary": {
                "hypotheses": len(records),
                "unique_paths": len(paths),
                "related_variant_observed": related,
                "unknown": len(records) - related,
                "comparison_tree_files": len(secondary_paths),
            },
        }
    )


def render_history_report(payload: Mapping[str, Any]) -> str:
    summary = payload["summary"]
    return "\n".join(
        [
            "# GIGA Archaeologist historical and cross-repository variants",
            "",
            f"- Hypotheses inspected: {summary['hypotheses']}",
            f"- Unique source paths: {summary['unique_paths']}",
            f"- Related variant observed: {summary['related_variant_observed']}",
            f"- No related variant established: {summary['unknown']} (`UNKNOWN`)",
            f"- Comparison-tree files: {summary['comparison_tree_files']}",
            f"- Receipt SHA-256: `{payload['receipt_sha256']}`",
            "",
            "A historical or parallel variant is preservation evidence, not proof that either copy is obsolete.",
            "No match is `UNKNOWN`, not proof that no variant exists.",
            "",
        ]
    )


def write_history(
    inventory_path: Path,
    hypotheses_path: Path,
    counterevidence_path: Path,
    comparison_repository: Path,
    output: Path,
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists() or output.is_symlink():
        raise HistoryError("history output directory must not already exist")
    payload = build_history(
        inventory_path, hypotheses_path, counterevidence_path, comparison_repository
    )
    output.mkdir(parents=True, mode=0o700)
    try:
        write_atomic(output / "history.json", canonical_bytes(payload))
        write_atomic(output / "HISTORY_REPORT.md", render_history_report(payload).encode("utf-8"))
    except EvidenceError as exc:
        raise HistoryError(str(exc)) from exc
    return payload
