"""Complete, local, non-authoritative filesystem navigation inventory.

This is intentionally a sibling of :mod:`inventory`, not a replacement for it.
The Archaeologist evidence inventory admits only privacy-filtered Git material;
this index has a distinct responsibility and lifecycle: record every working-tree
file (including ignored and untracked files) without following symlinks, while
separately deciding which content may enter semantic extraction.

Publication is external to the scanned root.  Each run is immutable and a small
``CURRENT.json`` pointer is replaced only after the new database and manifest are
durable, so an interrupted refresh leaves the previous run usable.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .evidence import canonical_bytes, seal_document, sha256_bytes, validate_self_hash


NAVIGATION_SCHEMA = "giga.navigation.inventory-manifest.v2"
POINTER_SCHEMA = "giga.navigation.current-pointer.v1"
LOCATE_SCHEMA = "giga.navigation.locate-result.v1"
DATABASE_SCHEMA = 2
CONTROL_EXCLUSIONS = (".git",)

SEMANTIC_SUFFIXES = frozenset(
    {
        ".c",
        ".cc",
        ".cpp",
        ".css",
        ".csv",
        ".go",
        ".h",
        ".hpp",
        ".html",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".kt",
        ".kts",
        ".lua",
        ".md",
        ".mjs",
        ".php",
        ".plist",
        ".py",
        ".pyi",
        ".rb",
        ".rs",
        ".rst",
        ".scss",
        ".sh",
        ".sql",
        ".swift",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
        ".zsh",
    }
)
DEPENDENCY_COMPONENTS = frozenset(
    {
        ".bundle",
        ".gradle",
        ".mypy_cache",
        ".next",
        ".npm",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "bower_components",
        "build",
        "dist",
        "node_modules",
        "site-packages",
        "target",
        "vendor",
        "venv",
    }
)
GENERATED_COMPONENTS = frozenset(
    {
        ".codex-tmp",
        ".playwright-cli",
        ".tmp-surfaces",
        ".work",
        ".worktrees",
        "graphify-out",
        "output",
        "outputs",
        "runtime",
        "staging",
        "tmp",
    }
)
SENSITIVE_COMPONENTS = frozenset(
    {
        ".giga-vault",
        "company-admin",
        "corpus",
        "credentials",
        "identity",
        "life-admin",
        "life-logging",
        "memory",
        "personal-data",
        "private",
        "secrets",
        "vault",
    }
)
SENSITIVE_NAME_TOKENS = (
    "credential",
    "identity-document",
    "passport",
    "private-key",
    "secret",
    "seed-phrase",
)
HISTORICAL_COMPONENTS = frozenset(
    {
        "archive",
        "archived",
        "history",
        "historical",
        "quarantine",
        "rejected",
        "snapshots",
    }
)
EVIDENCE_COMPONENTS = frozenset(
    {"canary", "canaries", "evidence", "receipts", "reports", "work_orders"}
)


class NavigationInventoryError(ValueError):
    """The navigation inventory cannot be created or trusted."""


@dataclass(frozen=True)
class NavigationPolicy:
    """Deterministic content-admission policy for the semantic layer."""

    semantic_max_bytes: int = 2 * 1024 * 1024
    control_exclusions: tuple[str, ...] = CONTROL_EXCLUSIONS

    def __post_init__(self) -> None:
        if isinstance(self.semantic_max_bytes, bool) or self.semantic_max_bytes <= 0:
            raise NavigationInventoryError(
                "semantic_max_bytes must be a positive integer"
            )
        if self.control_exclusions != CONTROL_EXCLUSIONS:
            raise NavigationInventoryError("the .git control exclusion is fixed")


@dataclass(frozen=True)
class NavigationRun:
    run_directory: Path
    manifest: Mapping[str, Any]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _file_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _stable_root(path: Path) -> tuple[Path, os.stat_result]:
    resolved = path.resolve(strict=True)
    before = resolved.lstat()
    if resolved.is_symlink() or not stat.S_ISDIR(before.st_mode):
        raise NavigationInventoryError("scan root must be a real directory")
    return resolved, before


def _private_store(path: Path, root: Path) -> Path:
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        pass
    else:
        raise NavigationInventoryError(
            "inventory store must be outside the scanned root"
        )
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = resolved.lstat()
    if resolved.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise NavigationInventoryError("inventory store must be a real directory")
    if metadata.st_uid != os.getuid():
        raise NavigationInventoryError(
            "inventory store must belong to the current user"
        )
    if stat.S_IMODE(metadata.st_mode) != 0o700:
        raise NavigationInventoryError("inventory store must have mode 0700")
    return resolved


def _git(root: Path, arguments: Sequence[str], *, timeout: int = 600) -> bytes:
    result = subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        env={
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
            "TZ": "UTC",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise NavigationInventoryError(
            f"Git read failed ({' '.join(arguments)}): {detail}"
        )
    return result.stdout


def _git_text(root: Path, arguments: Sequence[str]) -> str:
    try:
        return _git(root, arguments).decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise NavigationInventoryError("Git emitted non-UTF-8 identity data") from exc


def _tracked_files(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in _git(root, ["ls-files", "-s", "-z"]).split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            _mode, oid, stage = metadata.decode("ascii").split(" ")
            path = raw_path.decode("utf-8", "strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise NavigationInventoryError("malformed Git index record") from exc
        if stage != "0":
            raise NavigationInventoryError(f"unmerged Git entry: {path}")
        result[path] = oid
    return result


def _status_snapshot(
    root: Path,
) -> tuple[dict[str, str], list[dict[str, Any]], dict[str, Any]]:
    raw = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    result: dict[str, str] = {}
    entries: list[dict[str, Any]] = []
    records = raw.split(b"\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2:3] != b" ":
            raise NavigationInventoryError("malformed Git status record")
        try:
            code = record[:2].decode("ascii")
            path = record[3:].decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise NavigationInventoryError("Git status path is not UTF-8") from exc
        secondary_path: str | None = None
        if "R" in code or "C" in code:
            if index >= len(records) or not records[index]:
                raise NavigationInventoryError("malformed Git rename/copy record")
            try:
                secondary_path = records[index].decode("utf-8", "strict")
            except UnicodeDecodeError as exc:
                raise NavigationInventoryError("Git status path is not UTF-8") from exc
            index += 1
        result[path] = code
        entries.append(
            {
                "ordinal": len(entries),
                "code": code,
                "path": path,
                "secondary_path": secondary_path,
            }
        )
    entries_sha256 = sha256_bytes(canonical_bytes(entries))
    return (
        result,
        entries,
        {
            "sha256": sha256_bytes(raw),
            "bytes": len(raw),
            "entries": len(entries),
            "entries_sha256": entries_sha256,
            "clean": not entries,
        },
    )


def _ignored_paths(
    root: Path, paths: Iterable[str], *, batch_size: int = 10_000
) -> set[str]:
    ignored: set[str] = set()
    batch: list[str] = []

    def submit(values: list[str]) -> None:
        if not values:
            return
        payload = (
            b"\0".join(value.encode("utf-8", "strict") for value in values) + b"\0"
        )
        result = subprocess.run(
            ["/usr/bin/git", "check-ignore", "--no-index", "-z", "--stdin"],
            cwd=root,
            env={
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
            },
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        if result.returncode not in (0, 1):
            detail = result.stderr.decode("utf-8", "replace").strip()
            raise NavigationInventoryError(
                f"Git ignore classification failed: {detail}"
            )
        try:
            ignored.update(
                value.decode("utf-8", "strict")
                for value in result.stdout.split(b"\0")
                if value
            )
        except UnicodeDecodeError as exc:
            raise NavigationInventoryError("Git ignored path is not UTF-8") from exc

    for path in paths:
        batch.append(path)
        if len(batch) >= batch_size:
            submit(batch)
            batch = []
    submit(batch)
    return ignored


def _walk_files(
    root: Path, exclusions: tuple[str, ...]
) -> Iterator[tuple[str, os.DirEntry[str]]]:
    def visit(
        directory: Path, relative_directory: PurePosixPath | None
    ) -> Iterator[tuple[str, os.DirEntry[str]]]:
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            synthetic = f"{relative_directory.as_posix() if relative_directory else '.'}/<scan-error:{exc.errno}>"
            raise NavigationInventoryError(
                f"cannot enumerate {synthetic}: {exc}"
            ) from exc
        for entry in entries:
            relative = (
                PurePosixPath(entry.name)
                if relative_directory is None
                else relative_directory / entry.name
            )
            relative_text = relative.as_posix()
            if relative_directory is None and relative_text in exclusions:
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    yield from visit(Path(entry.path), relative)
                else:
                    yield relative_text, entry
            except OSError:
                yield relative_text, entry

    yield from visit(root, None)


def _kind(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "regular"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISCHR(mode):
        return "character-device"
    if stat.S_ISBLK(mode):
        return "block-device"
    return "other"


def _semantic_disposition(
    path: str, kind: str, size: int, policy: NavigationPolicy
) -> tuple[int, str]:
    parts = tuple(part.casefold() for part in PurePosixPath(path).parts)
    name = parts[-1]
    if any(part in SENSITIVE_COMPONENTS for part in parts) or any(
        token in name for token in SENSITIVE_NAME_TOKENS
    ):
        return 0, "sensitive-path"
    if any("canary" in part for part in parts):
        return 0, "private-canary-evidence"
    if any(part in DEPENDENCY_COMPONENTS for part in parts):
        return 0, "dependency-or-build-tree"
    if any(part in GENERATED_COMPONENTS for part in parts):
        return 0, "generated-or-runtime-output"
    if kind != "regular":
        return 0, "non-regular-file"
    if size > policy.semantic_max_bytes:
        return 0, "semantic-size-ceiling"
    if PurePosixPath(name).suffix.casefold() not in SEMANTIC_SUFFIXES:
        return 0, "unsupported-semantic-format"
    return 1, "eligible-local-only"


def _stable_hash(path: Path, before: os.stat_result) -> tuple[str, str | None]:
    if stat.S_ISLNK(before.st_mode):
        try:
            target = os.readlink(path).encode("utf-8", "surrogateescape")
        except OSError as exc:
            return "error", f"readlink:{exc.errno}"
        return sha256_bytes(target), None
    if not stat.S_ISREG(before.st_mode):
        return "", None
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            return "error", "identity-changed-before-read"
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(descriptor)
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if tuple(getattr(opened, item) for item in fields) != tuple(
            getattr(after, item) for item in fields
        ):
            return "error", "changed-during-read"
        return digest.hexdigest(), None
    except OSError as exc:
        return "error", f"read:{exc.errno}"
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _configure_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        PRAGMA page_size=4096;
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
        CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            ctime_ns INTEGER NOT NULL,
            mode INTEGER NOT NULL,
            uid INTEGER NOT NULL,
            gid INTEGER NOT NULL,
            device INTEGER NOT NULL,
            inode INTEGER NOT NULL,
            nlink INTEGER NOT NULL,
            content_sha256 TEXT,
            hash_status TEXT NOT NULL,
            git_status TEXT NOT NULL,
            git_tracked INTEGER NOT NULL,
            git_blob_oid TEXT,
            suffix TEXT NOT NULL,
            media_type TEXT,
            semantic_eligible INTEGER NOT NULL,
            semantic_reason TEXT NOT NULL,
            scan_error TEXT
        );
        CREATE INDEX files_sha256_idx ON files(content_sha256);
        CREATE INDEX files_git_status_idx ON files(git_status);
        CREATE INDEX files_semantic_idx ON files(semantic_eligible, semantic_reason);
        CREATE TABLE duplicate_groups (
            content_sha256 TEXT PRIMARY KEY,
            copies INTEGER NOT NULL,
            total_bytes INTEGER NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE git_status_entries (
            phase TEXT NOT NULL CHECK(phase IN ('before','after')),
            ordinal INTEGER NOT NULL,
            code TEXT NOT NULL,
            path TEXT NOT NULL,
            secondary_path TEXT,
            PRIMARY KEY (phase, ordinal)
        ) WITHOUT ROWID;
        CREATE INDEX git_status_entries_path_idx ON git_status_entries(path);
        """
    )


def _write_status_entries(
    connection: sqlite3.Connection, phase: str, entries: Sequence[Mapping[str, Any]]
) -> None:
    connection.executemany(
        """INSERT INTO git_status_entries(phase,ordinal,code,path,secondary_path)
           VALUES (?,?,?,?,?)""",
        (
            (
                phase,
                entry["ordinal"],
                entry["code"],
                entry["path"],
                entry["secondary_path"],
            )
            for entry in entries
        ),
    )


def _status_row_digest(connection: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    for row in connection.execute(
        """SELECT phase,ordinal,code,path,secondary_path
           FROM git_status_entries ORDER BY phase,ordinal"""
    ):
        digest.update(canonical_bytes(list(row)))
    return digest.hexdigest()


def _load_previous(
    store: Path, root: Path
) -> tuple[sqlite3.Connection | None, dict[str, Any] | None, str | None]:
    pointer_path = store / "CURRENT.json"
    if not pointer_path.exists():
        return None, None, None
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        validate_self_hash(pointer)
        if pointer.get("schema") != POINTER_SCHEMA or pointer.get("root") != str(root):
            raise NavigationInventoryError("current pointer does not bind this root")
        run_id = pointer["run_id"]
        run = store / "runs" / run_id
        manifest_path = run / "manifest.json"
        database_path = run / "inventory.sqlite3"
        manifest_raw = manifest_path.read_bytes()
        if sha256_bytes(manifest_raw) != pointer["manifest_file_sha256"]:
            raise NavigationInventoryError("current manifest file hash mismatch")
        manifest = json.loads(manifest_raw)
        validate_self_hash(manifest)
        database_sha, _ = _file_sha256(database_path)
        if database_sha != manifest["database"]["sha256"]:
            raise NavigationInventoryError("current database hash mismatch")
        connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
        return connection, manifest, None
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        sqlite3.Error,
    ) as exc:
        return None, None, f"previous-run-unusable:{type(exc).__name__}:{exc}"


def _previous_records(
    connection: sqlite3.Connection | None,
) -> dict[str, tuple[Any, ...]]:
    if connection is None:
        return {}
    return {
        row[0]: tuple(row[1:])
        for row in connection.execute(
            """SELECT path,content_sha256,hash_status,device,inode,size_bytes,
                      mtime_ns,ctime_ns,mode,kind,git_status
               FROM files ORDER BY path"""
        )
    }


def _previous_hash(
    records: Mapping[str, tuple[Any, ...]],
    path: str,
    metadata: os.stat_result,
    kind: str,
) -> tuple[str | None, str | None]:
    row = records.get(path)
    if row is None or row[1] not in ("hashed", "reused"):
        return None, None
    expected = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        stat.S_IMODE(metadata.st_mode),
        kind,
    )
    if tuple(row[2:9]) != expected:
        return None, None
    return row[0], row[9]


def _row_digest(connection: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    columns = (
        "path,kind,size_bytes,mtime_ns,ctime_ns,mode,uid,gid,device,inode,nlink,"
        "content_sha256,CASE WHEN hash_status IN ('hashed','reused') THEN 'available' "
        "ELSE hash_status END,git_status,git_tracked,git_blob_oid,suffix,"
        "media_type,semantic_eligible,semantic_reason,scan_error"
    )
    for row in connection.execute(f"SELECT {columns} FROM files ORDER BY path"):
        digest.update(canonical_bytes(list(row)))
    return digest.hexdigest()


def _replace_atomic(path: Path, payload: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temp_path.unlink(missing_ok=True)


def _render_report(manifest: Mapping[str, Any]) -> str:
    counts = manifest["counts"]
    lines = [
        "# GIGA folder navigation inventory",
        "",
        f"- Status: **{manifest['status']}**",
        f"- Scanned root: `{manifest['root']['path']}`",
        f"- Scan window: `{manifest['scan']['started_at']}` to `{manifest['scan']['finished_at']}`",
        f"- Files observed: {counts['files']:,}",
        f"- Content hashes calculated: {counts['hashed']:,}",
        f"- Content hashes reused: {counts['reused']:,}",
        f"- Read/stat errors: {counts['errors']:,}",
        f"- Semantic-eligible safe local inputs: {counts['semantic_eligible']:,}",
        f"- Exact duplicate groups: {counts['duplicate_groups']:,}",
        f"- Deterministic row digest: `{manifest['database']['row_digest_sha256']}`",
        f"- Database SHA-256: `{manifest['database']['sha256']}`",
        f"- Receipt SHA-256: `{manifest['receipt_sha256']}`",
        "",
        "## Scope and limits",
        "",
        "The inventory covers every filesystem entry that is a file, symlink, or special file under the root.",
        "Only `.git` control internals are excluded; this is stated in the manifest.",
        "The semantic eligibility flag is a privacy boundary, not an inventory omission.",
        "This database is a navigation index. It grants no authority and never substitutes for reading source.",
        "",
    ]
    if manifest["failures"]:
        lines.extend(("## Failures", ""))
        lines.extend(f"- {item}" for item in manifest["failures"])
        lines.append("")
    return "\n".join(lines)


def refresh_navigation_inventory(
    root: Path, store: Path, policy: NavigationPolicy | None = None
) -> NavigationRun:
    """Refresh the complete local inventory and atomically publish a new current run."""
    policy = policy or NavigationPolicy()
    root, root_before = _stable_root(root)
    store = _private_store(store, root)
    started_at = _utc_now()
    monotonic_start = time.monotonic()
    run_id = (
        f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid.uuid4().hex[:12]}"
    )
    staging = store / f".staging-{run_id}"
    runs = store / "runs"
    runs.mkdir(exist_ok=True, mode=0o700)
    if staging.exists():
        raise NavigationInventoryError("staging path unexpectedly exists")
    staging.mkdir(mode=0o700)
    previous, previous_manifest, previous_failure = _load_previous(store, root)
    database_path = staging / "inventory.sqlite3"
    failures: list[str] = []
    if previous_failure:
        failures.append(previous_failure)
    connection: sqlite3.Connection | None = None
    try:
        tracked = _tracked_files(root)
        status_map, status_before, git_before = _status_snapshot(root)
        previous_records = _previous_records(previous)
        connection = sqlite3.connect(database_path)
        _configure_database(connection)
        _write_status_entries(connection, "before", status_before)
        pending_git: list[str] = []
        counters = {
            "files": 0,
            "hashed": 0,
            "reused": 0,
            "not_applicable": 0,
            "errors": 0,
            "semantic_eligible": 0,
        }
        insert = connection.cursor()
        for relative, entry in _walk_files(root, policy.control_exclusions):
            counters["files"] += 1
            try:
                metadata = entry.stat(follow_symlinks=False)
                kind = _kind(metadata.st_mode)
                eligible, reason = _semantic_disposition(
                    relative, kind, metadata.st_size, policy
                )
                counters["semantic_eligible"] += eligible
                reused, previous_git_status = _previous_hash(
                    previous_records, relative, metadata, kind
                )
                error: str | None = None
                if reused is not None:
                    content_sha = reused
                    hash_status = "reused"
                    counters["reused"] += 1
                else:
                    content_sha, error = _stable_hash(Path(entry.path), metadata)
                    if error:
                        hash_status = "error"
                        content_sha = None
                        counters["errors"] += 1
                    elif content_sha:
                        hash_status = "hashed"
                        counters["hashed"] += 1
                    else:
                        hash_status = "not_applicable"
                        content_sha = None
                        counters["not_applicable"] += 1
                git_status = status_map.get(relative, "pending")
                if relative in tracked and git_status == "pending":
                    git_status = "  "
                elif previous_git_status is not None and git_status == "pending":
                    git_status = previous_git_status
                elif git_status == "pending":
                    pending_git.append(relative)
                suffix = PurePosixPath(relative).suffix.casefold()
                media_type = mimetypes.guess_type(relative, strict=False)[0]
                insert.execute(
                    """INSERT INTO files (
                        path,kind,size_bytes,mtime_ns,ctime_ns,mode,uid,gid,device,inode,nlink,
                        content_sha256,hash_status,git_status,git_tracked,git_blob_oid,suffix,
                        media_type,semantic_eligible,semantic_reason,scan_error
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        relative,
                        kind,
                        metadata.st_size,
                        metadata.st_mtime_ns,
                        metadata.st_ctime_ns,
                        stat.S_IMODE(metadata.st_mode),
                        metadata.st_uid,
                        metadata.st_gid,
                        metadata.st_dev,
                        metadata.st_ino,
                        metadata.st_nlink,
                        content_sha,
                        hash_status,
                        git_status,
                        int(relative in tracked),
                        tracked.get(relative),
                        suffix,
                        media_type,
                        eligible,
                        reason,
                        error,
                    ),
                )
            except OSError as exc:
                counters["errors"] += 1
                failures.append(f"{relative}:stat:{exc.errno}")
                insert.execute(
                    """INSERT INTO files (
                        path,kind,size_bytes,mtime_ns,ctime_ns,mode,uid,gid,device,inode,nlink,
                        content_sha256,hash_status,git_status,git_tracked,git_blob_oid,suffix,
                        media_type,semantic_eligible,semantic_reason,scan_error
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        relative,
                        "unknown",
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        None,
                        "error",
                        status_map.get(relative, "unknown"),
                        int(relative in tracked),
                        tracked.get(relative),
                        PurePosixPath(relative).suffix.casefold(),
                        None,
                        0,
                        "scan-error",
                        f"stat:{exc.errno}",
                    ),
                )
            if counters["files"] % 10_000 == 0:
                connection.commit()

        ignored = _ignored_paths(root, pending_git)
        connection.executemany(
            "UPDATE files SET git_status = ? WHERE path = ?",
            (("!!" if path in ignored else "??", path) for path in pending_git),
        )
        connection.execute(
            """INSERT INTO duplicate_groups(content_sha256,copies,total_bytes)
               SELECT content_sha256, COUNT(*), SUM(size_bytes)
               FROM files
               WHERE content_sha256 IS NOT NULL AND size_bytes > 0
               GROUP BY content_sha256 HAVING COUNT(*) > 1"""
        )
        duplicate_groups = connection.execute(
            "SELECT COUNT(*) FROM duplicate_groups"
        ).fetchone()[0]
        row_digest = _row_digest(connection)
        git_head = _git_text(root, ["rev-parse", "HEAD"])
        git_tree = _git_text(root, ["rev-parse", "HEAD^{tree}"])
        git_branch = _git_text(root, ["branch", "--show-current"])
        _status_after_map, status_after, git_after = _status_snapshot(root)
        _write_status_entries(connection, "after", status_after)
        status_row_digest = _status_row_digest(connection)
        root_after = root.lstat()
        root_stable = (root_before.st_dev, root_before.st_ino) == (
            root_after.st_dev,
            root_after.st_ino,
        )
        git_stable = git_before["sha256"] == git_after["sha256"]
        if not root_stable:
            failures.append("root-identity-changed-during-scan")
        if not git_stable:
            failures.append("git-status-changed-during-scan")
        for key, value in {
            "schema_version": str(DATABASE_SCHEMA),
            "root": str(root),
            "row_digest_sha256": row_digest,
            "git_status_row_digest_sha256": status_row_digest,
        }.items():
            connection.execute("INSERT INTO meta(key,value) VALUES (?,?)", (key, value))
        connection.commit()
        connection.close()
        connection = None
        os.chmod(database_path, 0o600)
        database_sha, database_bytes = _file_sha256(database_path)
        finished_at = _utc_now()
        status = "CURRENT" if not failures and counters["errors"] == 0 else "PARTIAL"
        manifest = seal_document(
            {
                "schema": NAVIGATION_SCHEMA,
                "authority": "non-authoritative-local-navigation-index",
                "authority_granted": False,
                "status": status,
                "run_id": run_id,
                "root": {
                    "path": str(root),
                    "device": root_after.st_dev,
                    "inode": root_after.st_ino,
                    "mode": stat.S_IMODE(root_after.st_mode),
                    "uid": root_after.st_uid,
                },
                "scan": {
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duration_seconds": round(time.monotonic() - monotonic_start, 6),
                    "scope": "all-working-tree-files",
                    "control_exclusions": [
                        {"path": ".git", "reason": "mutable Git control internals"}
                    ],
                    "incremental_from": previous_manifest["run_id"]
                    if previous_manifest is not None
                    else None,
                },
                "git": {
                    "head": git_head,
                    "tree": git_tree,
                    "branch": git_branch,
                    "before": git_before,
                    "after": git_after,
                    "stable_during_scan": git_stable,
                },
                "database": {
                    "path": "inventory.sqlite3",
                    "schema_version": DATABASE_SCHEMA,
                    "sha256": database_sha,
                    "bytes": database_bytes,
                    "row_digest_sha256": row_digest,
                    "git_status_row_digest_sha256": status_row_digest,
                    "sqlite_version": sqlite3.sqlite_version,
                },
                "policy": {
                    "semantic_processing": "local-only",
                    "semantic_max_bytes": policy.semantic_max_bytes,
                    "sensitive_content_recorded_in_inventory": False,
                    "sensitive_file_metadata_recorded": True,
                },
                "counts": {**counters, "duplicate_groups": duplicate_groups},
                "failures": sorted(failures),
            }
        )
        manifest_raw = canonical_bytes(manifest)
        (staging / "manifest.json").write_bytes(manifest_raw)
        os.chmod(staging / "manifest.json", 0o600)
        (staging / "REPORT.md").write_text(_render_report(manifest), encoding="utf-8")
        os.chmod(staging / "REPORT.md", 0o600)
        for path in (database_path, staging / "manifest.json", staging / "REPORT.md"):
            descriptor = os.open(path, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        staging_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(staging_fd)
        finally:
            os.close(staging_fd)
        run_directory = runs / run_id
        os.rename(staging, run_directory)
        runs_fd = os.open(runs, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(runs_fd)
        finally:
            os.close(runs_fd)
        pointer = seal_document(
            {
                "schema": POINTER_SCHEMA,
                "root": str(root),
                "run_id": run_id,
                "status": status,
                "updated_at": finished_at,
                "manifest_file_sha256": sha256_bytes(manifest_raw),
                "manifest_receipt_sha256": manifest["receipt_sha256"],
            }
        )
        _replace_atomic(store / "CURRENT.json", canonical_bytes(pointer))
        return NavigationRun(run_directory=run_directory, manifest=manifest)
    except Exception:
        if connection is not None:
            connection.close()
        shutil.rmtree(staging, ignore_errors=True)
        raise
    finally:
        if previous is not None:
            previous.close()


def current_navigation_run(store: Path) -> NavigationRun:
    """Open and authenticate the atomically selected current inventory run."""
    store = store.resolve(strict=True)
    try:
        pointer_raw = (store / "CURRENT.json").read_bytes()
        pointer = json.loads(pointer_raw)
        validate_self_hash(pointer)
        if pointer.get("schema") != POINTER_SCHEMA:
            raise NavigationInventoryError("unsupported current pointer schema")
        run = store / "runs" / pointer["run_id"]
        manifest_raw = (run / "manifest.json").read_bytes()
        if sha256_bytes(manifest_raw) != pointer["manifest_file_sha256"]:
            raise NavigationInventoryError("current manifest file hash mismatch")
        manifest = json.loads(manifest_raw)
        validate_self_hash(manifest)
        if manifest["receipt_sha256"] != pointer["manifest_receipt_sha256"]:
            raise NavigationInventoryError("current manifest receipt mismatch")
        database_sha, _ = _file_sha256(run / manifest["database"]["path"])
        if database_sha != manifest["database"]["sha256"]:
            raise NavigationInventoryError("current inventory database hash mismatch")
        return NavigationRun(run_directory=run, manifest=manifest)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, NavigationInventoryError):
            raise
        raise NavigationInventoryError(f"current inventory is unusable: {exc}") from exc


def search_navigation_inventory(
    store: Path, query: str, *, limit: int = 50, semantic_only: bool = False
) -> list[dict[str, Any]]:
    """Search the current authenticated inventory by path and file classification."""
    if not query or "\x00" in query:
        raise NavigationInventoryError("query must be non-empty and contain no NUL")
    if isinstance(limit, bool) or not 1 <= limit <= 500:
        raise NavigationInventoryError("limit must be between 1 and 500")
    current = current_navigation_run(store)
    database = current.run_directory / current.manifest["database"]["path"]
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        clause = "AND semantic_eligible = 1" if semantic_only else ""
        escaped_query = query.replace("%", "\\%").replace("_", "\\_")
        rows = connection.execute(
            f"""SELECT path,kind,size_bytes,mtime_ns,content_sha256,hash_status,
                       git_status,git_tracked,semantic_eligible,semantic_reason,scan_error
                FROM files
                WHERE path LIKE ? ESCAPE '\\' {clause}
                ORDER BY CASE WHEN path = ? THEN 0 WHEN path LIKE ? THEN 1 ELSE 2 END,
                         length(path), path
                LIMIT ?""",
            (f"%{escaped_query}%", query, f"{query}%", limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _closest_repository(root: Path, path: Path) -> dict[str, Any] | None:
    """Return a live, read-only identity for the closest containing Git repository."""
    current = path.parent
    while True:
        if (current / ".git").exists():
            try:
                top = Path(
                    _git_text(current, ["rev-parse", "--show-toplevel"])
                ).resolve(strict=True)
            except (NavigationInventoryError, OSError):
                top = None
            if top == current:
                relative = path.relative_to(current).as_posix()
                try:
                    _git(current, ["ls-files", "--error-unmatch", "--", relative])
                    tracked = True
                except NavigationInventoryError:
                    tracked = False
                return {
                    "root": current.relative_to(root).as_posix()
                    if current != root
                    else ".",
                    "head": _git_text(current, ["rev-parse", "HEAD"]),
                    "tree": _git_text(current, ["rev-parse", "HEAD^{tree}"]),
                    "branch": _git_text(current, ["branch", "--show-current"]),
                    "path": relative,
                    "tracked": tracked,
                }
        if current == root:
            return None
        try:
            current.relative_to(root)
        except ValueError:
            return None
        current = current.parent


def _navigation_role(
    path: str, repository: Mapping[str, Any] | None
) -> tuple[str, str]:
    pure = PurePosixPath(path)
    components = {part.casefold() for part in pure.parts}
    name = pure.name.casefold()
    if components & (DEPENDENCY_COMPONENTS | GENERATED_COMPONENTS):
        return "GENERATED_OR_CACHE_COPY", "generated-or-dependency-path-component"
    if components & HISTORICAL_COMPONENTS:
        return "HISTORICAL_OR_ARCHIVED_COPY", "history-or-archive-path-component"
    if components & EVIDENCE_COMPONENTS:
        return "EVIDENCE_OR_RECEIPT", "evidence-path-component"
    if "tests" in components or name.startswith(("test_", "test-")):
        return "TEST_OR_TEST_FIXTURE", "test-path-or-name"
    if repository is not None and repository["tracked"]:
        if pure.suffix.casefold() in GRAPH_SOURCE_SUFFIXES:
            return "CANONICAL_SOURCE_CANDIDATE", "tracked-source-in-closest-repository"
        return "TRACKED_PROJECT_FILE", "tracked-file-in-closest-repository"
    if repository is not None:
        return "UNTRACKED_WORKING_COPY", "untracked-file-in-closest-repository"
    return "UNOWNED_OR_STALE_PATH", "no-live-containing-repository"


GRAPH_SOURCE_SUFFIXES = frozenset(
    {
        ".c",
        ".cc",
        ".cpp",
        ".go",
        ".h",
        ".hpp",
        ".java",
        ".js",
        ".jsx",
        ".kt",
        ".kts",
        ".lua",
        ".mjs",
        ".php",
        ".py",
        ".pyi",
        ".rb",
        ".rs",
        ".sh",
        ".sql",
        ".swift",
        ".ts",
        ".tsx",
        ".zsh",
    }
)


def locate_navigation_inventory(
    store: Path, query: str, *, limit: int = 50, semantic_only: bool = False
) -> dict[str, Any]:
    """Return a closed, hash-bound navigation result with conservative path roles."""
    current = current_navigation_run(store)
    root = Path(current.manifest["root"]["path"]).resolve(strict=True)
    located: list[dict[str, Any]] = []
    for row in search_navigation_inventory(
        store, query, limit=limit, semantic_only=semantic_only
    ):
        pure = PurePosixPath(row["path"])
        if pure.is_absolute() or ".." in pure.parts:
            raise NavigationInventoryError("inventory contains an unsafe path")
        live_path = root.joinpath(*pure.parts)
        repository = (
            _closest_repository(root, live_path) if live_path.exists() else None
        )
        role, basis = _navigation_role(row["path"], repository)
        live_sha256: str | None = None
        live_matches_inventory = False
        try:
            metadata = live_path.lstat()
            if stat.S_ISREG(metadata.st_mode):
                live_sha256, _ = _file_sha256(live_path)
                live_matches_inventory = live_sha256 == row["content_sha256"]
        except OSError:
            pass
        located.append(
            {
                **row,
                "role": role,
                "role_basis": basis,
                "canonicality_claimed": False,
                "repository": repository,
                "source": {
                    "absolute_path": str(live_path),
                    "inventory_sha256": row["content_sha256"],
                    "live_sha256": live_sha256,
                    "live_matches_inventory": live_matches_inventory,
                },
            }
        )
    return seal_document(
        {
            "schema": LOCATE_SCHEMA,
            "status": "PASS",
            "authority": "non-authoritative-navigation-result",
            "authority_granted": False,
            "query": query,
            "limit": limit,
            "semantic_only": semantic_only,
            "inventory": {
                "run_id": current.manifest["run_id"],
                "manifest_receipt_sha256": current.manifest["receipt_sha256"],
                "database_sha256": current.manifest["database"]["sha256"],
                "row_digest_sha256": current.manifest["database"]["row_digest_sha256"],
                "git_status_row_digest_sha256": current.manifest["database"][
                    "git_status_row_digest_sha256"
                ],
            },
            "results": located,
        }
    )
