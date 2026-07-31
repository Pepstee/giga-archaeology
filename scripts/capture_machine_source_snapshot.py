#!/usr/bin/env python3
"""Seal Mac or Gutua source state without promoting or modifying project roots."""

from __future__ import annotations

import argparse
import fnmatch
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Iterable


SCHEMA = "giga.machine-source-snapshot.v1"
PAIR_SCHEMA = "giga.machine-source-snapshot-pair.v1"
CHUNK_BYTES = 1024 * 1024


class SnapshotError(RuntimeError):
    """Snapshot input, capture or seal failure."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def manifest_digest(value: dict[str, Any]) -> str:
    unsigned = dict(value)
    unsigned.pop("manifest_digest", None)
    return sha256_bytes(canonical_bytes(unsigned))


def _git(
    root: Path,
    *args: str,
    check: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess[Any]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=text,
    )
    if check and result.returncode:
        stderr = result.stderr if text else result.stderr.decode("utf-8", "replace")
        raise SnapshotError(f"git {' '.join(args)} failed in {root}: {stderr.strip()}")
    return result


def _path_entry(path: Path, relative: str) -> dict[str, Any]:
    info = path.lstat()
    mode = format(stat.S_IMODE(info.st_mode), "04o")
    result: dict[str, Any] = {"path": relative, "mode": mode}
    if stat.S_ISREG(info.st_mode):
        result.update(type="file", size=info.st_size, sha256=sha256_file(path))
    elif stat.S_ISDIR(info.st_mode):
        result.update(type="directory")
    elif stat.S_ISLNK(info.st_mode):
        result.update(type="symlink", mode="0777", target=os.readlink(path))
    else:
        result.update(type="special")
    return result


def _matches_exclude(relative: str, patterns: Iterable[str]) -> bool:
    parts = relative.split("/")
    for pattern in patterns:
        clean = pattern.strip().strip("/")
        if not clean:
            raise SnapshotError("empty tree exclusion is forbidden")
        if "/" not in clean and clean in parts:
            return True
        if fnmatch.fnmatch(relative, clean) or fnmatch.fnmatch(Path(relative).name, clean):
            return True
        if relative == clean or relative.startswith(clean + "/"):
            return True
    return False


def capture_tree(root: Path, excludes: list[str]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []

    def visit(directory: Path, prefix: str = "") -> None:
        with os.scandir(directory) as iterator:
            children = sorted(iterator, key=lambda item: item.name)
        for child in children:
            relative = f"{prefix}/{child.name}" if prefix else child.name
            if _matches_exclude(relative, excludes):
                continue
            path = Path(child.path)
            entry = _path_entry(path, relative)
            entries.append(entry)
            if entry["type"] == "directory":
                visit(path, relative)

    visit(root)
    return {
        "excludes": excludes,
        "entry_count": len(entries),
        "file_count": sum(item["type"] == "file" for item in entries),
        "regular_file_bytes": sum(item.get("size", 0) for item in entries),
        "content_digest": sha256_bytes(canonical_bytes(entries)),
        "entries": entries,
    }


def _parse_worktrees(raw: str) -> list[dict[str, Any]]:
    worktrees: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in raw.splitlines() + [""]:
        if not line:
            if current:
                worktrees.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key in {"bare", "detached", "prunable"}:
            current[key] = True if not value else value
        else:
            current[key] = value
    return worktrees


def _zero_paths(raw: bytes) -> list[str]:
    return sorted(
        {
            item.decode("utf-8", "surrogateescape")
            for item in raw.split(b"\0")
            if item
        }
    )


def _dirty_entries(worktree: Path) -> tuple[list[dict[str, Any]], list[str]]:
    names: set[str] = set()
    for args in (
        ("diff", "--name-only", "-z", "HEAD", "--"),
        ("diff", "--cached", "--name-only", "-z", "--"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        result = _git(worktree, *args, text=False)
        names.update(_zero_paths(result.stdout))

    entries: list[dict[str, Any]] = []
    missing: list[str] = []
    resolved_root = worktree.resolve()
    for relative in sorted(names):
        candidate = worktree / relative
        try:
            candidate.parent.resolve().relative_to(resolved_root)
        except ValueError as exc:
            raise SnapshotError(f"dirty path escapes worktree: {relative}") from exc
        if candidate.exists() or candidate.is_symlink():
            entries.append(_path_entry(candidate, relative))
        else:
            missing.append(relative)
    return entries, missing


def _capture_worktree(item: dict[str, Any]) -> dict[str, Any]:
    path = Path(item["worktree"])
    result = dict(item)
    result["exists"] = path.is_dir()
    if not result["exists"]:
        return result

    status = _git(path, "status", "--porcelain=v1", "--untracked-files=all").stdout
    diff = _git(path, "diff", "--binary", "HEAD", "--", text=False).stdout
    dirty, missing = _dirty_entries(path)
    result.update(
        status_line_count=len(status.splitlines()),
        status_sha256=sha256_bytes(status.encode("utf-8", "surrogateescape")),
        status=status.splitlines(),
        binary_diff_bytes=len(diff),
        binary_diff_sha256=sha256_bytes(diff),
        dirty_entries=dirty,
        missing_dirty_paths=missing,
        dirty_content_digest=sha256_bytes(canonical_bytes({"entries": dirty, "missing": missing})),
    )
    return result


def capture_git(root: Path) -> dict[str, Any]:
    top = Path(_git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if top != root.resolve():
        raise SnapshotError(f"declared Git root {root} resolves to parent repository {top}")

    refs_raw = _git(
        root,
        "for-each-ref",
        "--format=%(refname)%00%(objectname)%00%(objecttype)%00%(symref)",
        text=False,
    ).stdout
    refs: list[dict[str, str]] = []
    for line in refs_raw.splitlines():
        fields = line.decode("utf-8", "surrogateescape").split("\0")
        fields += [""] * (4 - len(fields))
        refs.append(
            {
                "ref": fields[0],
                "object": fields[1],
                "object_type": fields[2],
                "symref": fields[3],
            }
        )
    refs.sort(key=lambda item: item["ref"])

    worktrees = [
        _capture_worktree(item)
        for item in _parse_worktrees(_git(root, "worktree", "list", "--porcelain").stdout)
    ]
    fsck = _git(root, "fsck", "--connectivity-only", "--no-progress", check=False)
    submodules = _git(root, "submodule", "status", "--recursive", check=False).stdout.splitlines()
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    tree = _git(root, "rev-parse", "HEAD^{tree}").stdout.strip()
    branch_result = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)

    return {
        "head": head,
        "head_tree": tree,
        "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else null_value(),
        "remote_names": sorted(_git(root, "remote").stdout.splitlines()),
        "refs": refs,
        "refs_digest": sha256_bytes(canonical_bytes(refs)),
        "worktrees": worktrees,
        "worktree_count": len(worktrees),
        "dirty_worktree_count": sum(
            item.get("status_line_count", 0) > 0 for item in worktrees
        ),
        "submodules": submodules,
        "fsck_connectivity_ok": fsck.returncode == 0,
        "fsck_output_sha256": sha256_bytes(
            (fsck.stdout + fsck.stderr).encode("utf-8", "surrogateescape")
        ),
    }


def null_value() -> None:
    return None


def load_registry(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"cannot read authority registry: {path}") from exc
    if document.get("schema") != "giga.machine-authority.v1":
        raise SnapshotError("unsupported machine-authority registry")
    return document


def capture(registry_path: Path, host_id: str) -> dict[str, Any]:
    registry = load_registry(registry_path)
    try:
        host_config = registry["hosts"][host_id]
    except KeyError as exc:
        raise SnapshotError(f"host is absent from authority registry: {host_id}") from exc

    roots: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for config in host_config["roots"]:
        root_id = config["id"]
        if root_id in seen_ids:
            raise SnapshotError(f"duplicate root id: {root_id}")
        seen_ids.add(root_id)
        root = Path(config["path"])
        item: dict[str, Any] = {
            "id": root_id,
            "path": str(root),
            "kind": config["kind"],
            "purpose": config["purpose"],
            "exists": root.is_dir(),
        }
        if item["exists"]:
            if config["kind"] == "git":
                item["git"] = capture_git(root)
            elif config["kind"] == "tree":
                item["tree"] = capture_tree(root, list(config.get("excludes", [])))
            else:
                raise SnapshotError(f"unsupported root kind: {config['kind']}")
        roots.append(item)

    snapshot: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "policy_id": registry["policy_id"],
        "registry_sha256": sha256_file(registry_path),
        "host": {
            "id": host_id,
            "role": host_config["role"],
            "hostname": platform.node(),
            "user": getpass.getuser(),
            "platform": platform.platform(),
        },
        "roots": roots,
    }
    snapshot["manifest_digest"] = manifest_digest(snapshot)
    return snapshot


def _write_immutable(path: Path, document: dict[str, Any]) -> None:
    content = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise SnapshotError(f"immutable snapshot already exists with different content: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o444)
    finally:
        if temporary.exists():
            temporary.unlink()


def verify_snapshot(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise SnapshotError(f"unsupported snapshot schema: {path}")
    expected = document.get("manifest_digest")
    actual = manifest_digest(document)
    if expected != actual:
        raise SnapshotError(f"snapshot seal mismatch: {path}")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "manifest_digest": actual,
        "host": document["host"]["id"],
        "root_count": len(document["roots"]),
        "ok": True,
    }


def bind_pair(registry: Path, mac: Path, gutua: Path) -> dict[str, Any]:
    mac_result = verify_snapshot(mac)
    gutua_result = verify_snapshot(gutua)
    if mac_result["host"] != "mac" or gutua_result["host"] != "gutua":
        raise SnapshotError("snapshot pair must contain mac then gutua")
    registry_document = load_registry(registry)
    registry_hash = sha256_file(registry)
    for path in (mac, gutua):
        document = json.loads(path.read_text(encoding="utf-8"))
        if document["registry_sha256"] != registry_hash:
            raise SnapshotError(f"snapshot was not created from current registry: {path}")
    pair: dict[str, Any] = {
        "schema": PAIR_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "policy_id": registry_document["policy_id"],
        "canonical_host": registry_document["authority"]["canonical_host"],
        "registry": {"path": str(registry), "sha256": registry_hash},
        "snapshots": {"mac": mac_result, "gutua": gutua_result},
        "promotion_authority_granted": False,
        "comparison_performed": False,
        "deletion_authority_granted": False,
    }
    pair["manifest_digest"] = manifest_digest(pair)
    return pair


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--registry", type=Path, required=True)
    capture_parser.add_argument("--host", choices=("mac", "gutua"), required=True)
    capture_parser.add_argument("--output", type=Path, required=True)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("snapshot", type=Path)

    pair_parser = sub.add_parser("bind-pair")
    pair_parser.add_argument("--registry", type=Path, required=True)
    pair_parser.add_argument("--mac", type=Path, required=True)
    pair_parser.add_argument("--gutua", type=Path, required=True)
    pair_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "capture":
        document = capture(args.registry, args.host)
        _write_immutable(args.output, document)
        print(json.dumps(verify_snapshot(args.output), indent=2))
        return 0
    if args.command == "verify":
        print(json.dumps(verify_snapshot(args.snapshot), indent=2))
        return 0
    if args.command == "bind-pair":
        document = bind_pair(args.registry, args.mac, args.gutua)
        _write_immutable(args.output, document)
        print(json.dumps(verify_pair(args.output), indent=2))
        return 0
    raise AssertionError(args.command)


def verify_pair(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != PAIR_SCHEMA:
        raise SnapshotError(f"unsupported pair schema: {path}")
    expected = document.get("manifest_digest")
    actual = manifest_digest(document)
    if expected != actual:
        raise SnapshotError(f"pair seal mismatch: {path}")
    return {"path": str(path), "sha256": sha256_file(path), "ok": True}


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SnapshotError as exc:
        print(f"snapshot error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
