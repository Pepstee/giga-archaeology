"""Slice 1: immutable, privacy-filtered repository inventory.

The implementation parses files but never imports target code.  It uses Git's
read-only plumbing with optional locks disabled, follows no repository symlink,
and writes only to a caller-selected directory outside the target repository.
"""

from __future__ import annotations

import ast
import os
import re
import stat
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .evidence import (
    EvidenceError,
    canonical_bytes,
    seal_document,
    sha256_bytes,
    write_atomic,
)


INVENTORY_SCHEMA = "giga.archaeologist.inventory.v1"
SOURCE_SUFFIXES = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".swift",
        ".kt",
        ".kts",
        ".rb",
        ".php",
        ".scala",
        ".lua",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".sql",
        ".json",
        ".toml",
        ".yaml",
        ".yml",
        ".md",
        ".rst",
        ".txt",
        ".plist",
    }
)
DEFAULT_EXCLUDED_PREFIXES = (
    ".codex/",
    ".giga-vault/",
    "applications/",
    "audit-work/personal-data/",
    "corpus/",
    "graphify-out/memory/",
    "memory/",
    "output/",
    "outputs/",
    "private/",
    "runtime/outputs/",
    "secrets/",
    "tmp/",
    "vault/",
)
MAX_FILE_BYTES = 64 * 1024 * 1024
HASH_RE = re.compile(r"[0-9a-f]{64}")


class InventoryError(ValueError):
    """The target cannot be inventoried without weakening the evidence boundary."""


@dataclass(frozen=True)
class InventoryPolicy:
    excluded_prefixes: tuple[str, ...] = DEFAULT_EXCLUDED_PREFIXES
    admitted_untracked: tuple[str, ...] = ()
    max_file_bytes: int = MAX_FILE_BYTES

    def __post_init__(self) -> None:
        if isinstance(self.max_file_bytes, bool) or self.max_file_bytes <= 0:
            raise InventoryError("max_file_bytes must be a positive integer")
        for value in (*self.excluded_prefixes, *self.admitted_untracked):
            _relative(value)


def _relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise InventoryError("repository paths must be non-empty strings without NUL")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise InventoryError(f"non-canonical repository path: {value!r}")
    canonical = path.as_posix()
    if canonical != value.rstrip("/"):
        raise InventoryError(f"non-canonical repository path: {value!r}")
    return canonical


def _root_identity(root: Path) -> dict[str, int]:
    metadata = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise InventoryError("repository root must be a real directory")
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mode": stat.S_IMODE(metadata.st_mode),
        "uid": metadata.st_uid,
    }


def _git(root: Path, arguments: Sequence[str]) -> bytes:
    environment = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
        "TZ": "UTC",
    }
    result = subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise InventoryError(f"Git read failed ({' '.join(arguments)}): {detail}")
    return result.stdout


def _git_text(root: Path, arguments: Sequence[str]) -> str:
    try:
        return _git(root, arguments).decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise InventoryError("Git returned a non-UTF-8 path or identity") from exc


def _is_excluded(relative: str, policy: InventoryPolicy) -> bool:
    value = relative + ("/" if not relative.endswith("/") else "")
    return any(
        value.startswith(prefix) or relative == prefix.rstrip("/")
        for prefix in policy.excluded_prefixes
    )


def _read_record(
    root: Path, relative: str, policy: InventoryPolicy, git_oid: str | None
) -> tuple[dict[str, Any], bytes | None]:
    relative = _relative(relative)
    path = root / relative
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode):
        target = os.readlink(path).encode("utf-8", "surrogateescape")
        return (
            {
                "path": relative,
                "kind": "symlink",
                "bytes": len(target),
                "mode": stat.S_IMODE(before.st_mode),
                "sha256": sha256_bytes(target),
                "git_blob_oid": git_oid,
            },
            None,
        )
    if not stat.S_ISREG(before.st_mode):
        raise InventoryError(
            f"tracked path is not a regular file or symlink: {relative}"
        )
    if before.st_size > policy.max_file_bytes:
        raise InventoryError(f"tracked file exceeds inventory ceiling: {relative}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise InventoryError(f"file identity changed before read: {relative}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        opened.st_dev,
        opened.st_ino,
        opened.st_size,
        opened.st_mtime_ns,
        opened.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise InventoryError(f"file changed during read: {relative}")
    content = b"".join(chunks)
    return (
        {
            "path": relative,
            "kind": "regular",
            "bytes": len(content),
            "mode": stat.S_IMODE(opened.st_mode),
            "sha256": sha256_bytes(content),
            "git_blob_oid": git_oid,
        },
        content,
    )


def _tracked(root: Path) -> list[tuple[str, str]]:
    output = _git(root, ["ls-files", "-s", "-z"])
    records: list[tuple[str, str]] = []
    for raw in output.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, path_raw = raw.split(b"\t", 1)
            _mode, oid, stage = metadata.decode("ascii").split(" ")
            path = path_raw.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError) as exc:
            raise InventoryError("malformed Git index record") from exc
        if stage != "0":
            raise InventoryError(f"unmerged index entry cannot be inventoried: {path}")
        records.append((_relative(path), oid))
    return sorted(records)


def _untracked(root: Path) -> list[str]:
    output = _git(root, ["ls-files", "--others", "--exclude-standard", "-z"])
    try:
        return sorted(
            _relative(item.decode("utf-8", "strict"))
            for item in output.split(b"\0")
            if item
        )
    except UnicodeDecodeError as exc:
        raise InventoryError("untracked path is not UTF-8") from exc


class _Symbols(ast.NodeVisitor):
    def __init__(self, relative: str) -> None:
        self.relative = relative
        self.parents: list[str] = []
        self.records: list[dict[str, Any]] = []

    def _add(self, node: ast.AST, kind: str, name: str) -> None:
        qualified = ".".join((*self.parents, name))
        decorators = []
        for decorator in getattr(node, "decorator_list", []):
            try:
                decorators.append(ast.unparse(decorator))
            except Exception:
                decorators.append("<unparseable>")
        self.records.append(
            {
                "path": self.relative,
                "qualified_name": qualified,
                "kind": kind,
                "line": getattr(node, "lineno", 0),
                "decorators": decorators,
            }
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._add(node, "class", node.name)
        self.parents.append(node.name)
        self.generic_visit(node)
        self.parents.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._add(node, "function", node.name)
        self.parents.append(node.name)
        self.generic_visit(node)
        self.parents.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._add(node, "async-function", node.name)
        self.parents.append(node.name)
        self.generic_visit(node)
        self.parents.pop()


def _python_symbols(
    relative: str, content: bytes
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        text = content.decode("utf-8", "strict")
        tree = ast.parse(text, filename=relative)
    except (UnicodeDecodeError, SyntaxError) as exc:
        return [], f"{type(exc).__name__}: {exc}"
    visitor = _Symbols(relative)
    visitor.visit(tree)
    return visitor.records, None


def _declared_entrypoints(
    relative: str, content: bytes, mode: int
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    if relative.endswith("/__main__.py") or relative == "__main__.py":
        result.append(
            {"kind": "python-module-main", "path": relative, "target": relative}
        )
    if mode & 0o111 and PurePosixPath(relative).suffix in {
        "",
        ".sh",
        ".bash",
        ".zsh",
        ".py",
    }:
        result.append({"kind": "executable-file", "path": relative, "target": relative})
    if PurePosixPath(relative).name == "pyproject.toml":
        try:
            parsed = tomllib.loads(content.decode("utf-8", "strict"))
            scripts = parsed.get("project", {}).get("scripts", {})
            if isinstance(scripts, dict):
                for name, target in sorted(scripts.items()):
                    if isinstance(name, str) and isinstance(target, str):
                        result.append(
                            {
                                "kind": "python-project-script",
                                "path": relative,
                                "target": f"{name}={target}",
                            }
                        )
        except (UnicodeDecodeError, tomllib.TOMLDecodeError):
            pass
    return result


def _ref_snapshot(root: Path) -> dict[str, Any]:
    raw = _git(
        root,
        [
            "for-each-ref",
            "--sort=refname",
            "--format=%(refname)%00%(objectname)%00%(objecttype)",
        ],
    )
    refs: list[dict[str, str]] = []
    for line in raw.splitlines():
        if not line:
            continue
        parts = line.split(b"\0")
        if len(parts) != 3:
            raise InventoryError("malformed Git ref record")
        try:
            refname, oid, object_type = (
                part.decode("utf-8", "strict") for part in parts
            )
        except UnicodeDecodeError as exc:
            raise InventoryError("Git ref is not UTF-8") from exc
        refs.append({"ref": refname, "oid": oid, "type": object_type})
    if [item["ref"] for item in refs] != sorted(item["ref"] for item in refs):
        raise InventoryError("Git refs are not sorted")
    return {
        "sha256": sha256_bytes(raw),
        "bytes": len(raw),
        "count": len(refs),
        "refs": refs,
    }


def _status_snapshot(root: Path) -> dict[str, Any]:
    raw = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    entries = [item for item in raw.split(b"\0") if item]
    return {
        "sha256": sha256_bytes(raw),
        "bytes": len(raw),
        "entries": len(entries),
        "clean": not entries,
    }


def _version(root: Path) -> dict[str, str]:
    git_version = _git_text(root, ["--version"]).strip()
    return {"git": git_version, "python": sys.version.split()[0]}


def build_inventory(
    root: Path, policy: InventoryPolicy | None = None
) -> dict[str, Any]:
    """Build a deterministic inventory without writing to *root*."""
    policy = policy or InventoryPolicy()
    root = root.resolve(strict=True)
    identity_before = _root_identity(root)
    if not (root / ".git").exists():
        try:
            _git(root, ["rev-parse", "--git-dir"])
        except InventoryError as exc:
            raise InventoryError("target is not a Git worktree") from exc
    tracked = _tracked(root)
    untracked = _untracked(root)
    admitted = set(policy.admitted_untracked)
    missing = sorted(admitted - set(untracked))
    if missing:
        raise InventoryError(
            f"admitted untracked paths are absent or ignored: {missing}"
        )

    files: list[dict[str, Any]] = []
    symbols: list[dict[str, Any]] = []
    entrypoints: list[dict[str, str]] = []
    parse_errors: list[dict[str, str]] = []
    excluded_paths: list[str] = []
    contents: dict[str, bytes] = {}

    candidates: list[tuple[str, str | None, str]] = [
        (path, oid, "tracked") for path, oid in tracked
    ] + [(path, None, "admitted-untracked") for path in sorted(admitted)]
    for relative, oid, provenance in candidates:
        if _is_excluded(relative, policy):
            excluded_paths.append(relative)
            continue
        record, content = _read_record(root, relative, policy, oid)
        record["provenance"] = provenance
        files.append(record)
        if content is not None:
            contents[relative] = content
            entrypoints.extend(_declared_entrypoints(relative, content, record["mode"]))
            if PurePosixPath(relative).suffix in {".py", ".pyi"}:
                found, error = _python_symbols(relative, content)
                symbols.extend(found)
                if error:
                    parse_errors.append({"path": relative, "error": error})

    duplicates: list[dict[str, Any]] = []
    by_hash: dict[str, list[str]] = {}
    for record in files:
        if record["kind"] == "regular" and record["bytes"] > 0:
            by_hash.setdefault(record["sha256"], []).append(record["path"])
    for digest, paths in sorted(by_hash.items()):
        if len(paths) > 1:
            duplicates.append(
                {"sha256": digest, "paths": sorted(paths), "copies": len(paths)}
            )

    head = _git_text(root, ["rev-parse", "HEAD"]).strip()
    tree = _git_text(root, ["rev-parse", "HEAD^{tree}"]).strip()
    branch = _git_text(root, ["branch", "--show-current"]).strip()
    status = _status_snapshot(root)
    refs = _ref_snapshot(root)
    identity_after = _root_identity(root)
    if identity_before != identity_after:
        raise InventoryError("repository root changed during inventory")

    payload = {
        "schema": INVENTORY_SCHEMA,
        "authority": "read-only-observation",
        "authority_granted": False,
        "cleanup_permitted": False,
        "repository": {
            "root": str(root),
            "head": head,
            "tree": tree,
            "branch": branch,
            "identity": identity_after,
            "status": status,
            "refs": refs,
        },
        "policy": {
            "excluded_prefixes": list(policy.excluded_prefixes),
            "admitted_untracked": list(policy.admitted_untracked),
            "max_file_bytes": policy.max_file_bytes,
        },
        "privacy": {
            "excluded_count": len(excluded_paths),
            "excluded_path_list_sha256": sha256_bytes(
                canonical_bytes(sorted(excluded_paths))
            ),
            "excluded_paths_recorded": False,
        },
        "tool_versions": _version(root),
        "files": sorted(files, key=lambda item: item["path"]),
        "symbols": sorted(
            symbols,
            key=lambda item: (item["path"], item["line"], item["qualified_name"]),
        ),
        "declared_entrypoints": sorted(
            entrypoints, key=lambda item: (item["path"], item["kind"], item["target"])
        ),
        "exact_duplicates": duplicates,
        "parse_errors": sorted(parse_errors, key=lambda item: item["path"]),
        "untracked": {
            "observed_count": len(untracked),
            "admitted_count": len(admitted),
            "unadmitted_path_list_sha256": sha256_bytes(
                canonical_bytes(sorted(set(untracked) - admitted))
            ),
            "unadmitted_paths_recorded": False,
        },
        "summary": {
            "included_files": len(files),
            "symbols": len(symbols),
            "declared_entrypoints": len(entrypoints),
            "exact_duplicate_groups": len(duplicates),
            "parse_errors": len(parse_errors),
            "excluded_paths": len(excluded_paths),
        },
    }
    return seal_document(payload)


def render_inventory_report(inventory: Mapping[str, Any]) -> str:
    summary = inventory["summary"]
    repository = inventory["repository"]
    lines = [
        "# GIGA Archaeology immutable inventory",
        "",
        f"- Repository: `{repository['root']}`",
        f"- HEAD: `{repository['head']}`",
        f"- Tree: `{repository['tree']}`",
        f"- Dirty state entries: {repository['status']['entries']}",
        f"- Included files: {summary['included_files']}",
        f"- Python symbols: {summary['symbols']}",
        f"- Declared entrypoints: {summary['declared_entrypoints']}",
        f"- Exact duplicate groups: {summary['exact_duplicate_groups']}",
        f"- Excluded sensitive paths: {summary['excluded_paths']} (names not recorded)",
        f"- Parse errors: {summary['parse_errors']}",
        f"- Receipt SHA-256: `{inventory['receipt_sha256']}`",
        "",
        "This is a read-only inventory. It grants no cleanup, quarantine, migration, or deletion authority.",
        "",
    ]
    return "\n".join(lines)


def write_inventory(
    root: Path, output: Path, policy: InventoryPolicy | None = None
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    output = output.resolve(strict=False)
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        raise InventoryError("inventory output must be outside the target repository")
    if output.exists():
        raise InventoryError("inventory output directory must not already exist")
    output.mkdir(parents=True, mode=0o700)
    inventory = build_inventory(root, policy)
    try:
        write_atomic(output / "inventory.json", canonical_bytes(inventory))
        write_atomic(
            output / "INVENTORY_REPORT.md",
            render_inventory_report(inventory).encode("utf-8"),
        )
    except EvidenceError as exc:
        raise InventoryError(str(exc)) from exc
    return inventory
