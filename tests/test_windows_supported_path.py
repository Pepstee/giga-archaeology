"""End-to-end portability coverage for the supported local mapping path."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from modules.operations.archaeology.mapper import _inventory_record
from modules.operations.archaeology.navigation_inventory import (
    _configure_database,
    _execute_metadata_insert,
    _metadata_overflow_columns,
    _previous_hash,
    _selected_paths_match_inventory,
    _sqlite_identity_text,
    _stable_hash,
)
from modules.operations.archaeology.python_map import PythonMapError


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def _insert_inventory_file(
    connection: sqlite3.Connection,
    relative: str,
    metadata: os.stat_result | SimpleNamespace,
    content_sha256: str,
) -> None:
    device, inode = _sqlite_identity_text(metadata)
    _execute_metadata_insert(
        connection,
        """INSERT INTO files (
            path,kind,size_bytes,mtime_ns,ctime_ns,mode,uid,gid,device,inode,nlink,
            content_sha256,hash_status,git_status,git_tracked,git_blob_oid,suffix,
            media_type,semantic_eligible,semantic_reason,scan_error
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            relative,
            "regular",
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
            stat.S_IMODE(metadata.st_mode),
            metadata.st_uid,
            metadata.st_gid,
            device,
            inode,
            metadata.st_nlink,
            content_sha256,
            "hashed",
            "  ",
            1,
            "fixture-blob",
            ".py",
            "text/x-python",
            1,
            "eligible-local-only",
            None,
        ),
        metadata,
    )


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _cli(*arguments: str) -> str:
    installed_cli = os.environ.get("GIGA_ARCHAEOLOGY_CLI")
    command = (
        [installed_cli, *arguments]
        if installed_cli
        else [sys.executable, "-m", "modules.operations.scripts.archaeology", *arguments]
    )
    result = subprocess.run(
        command,
        cwd=SOURCE_ROOT,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        columns = _pathless_metadata_overflow_columns(result.stderr)
        detail = (
            f"; SQLite integer overflow in metadata columns: {','.join(columns)}"
            if columns
            else ""
        )
        raise AssertionError(f"CLI failed (exit={result.returncode}){detail}")
    return result.stdout


_SQLITE_METADATA_COLUMN_ALLOWLIST = {
    "size_bytes",
    "mtime_ns",
    "ctime_ns",
    "mode",
    "uid",
    "gid",
    "device",
    "inode",
    "nlink",
}


def _pathless_metadata_overflow_columns(stderr: str) -> list[str]:
    marker = "ARCHAEOLOGY_SQLITE_INTEGER_OVERFLOW:columns="
    for line in stderr.splitlines():
        if marker not in line:
            continue
        value = line.partition(marker)[2].strip()
        if not re.fullmatch(r"[a-z_,]*", value):
            return []
        columns = value.split(",") if value else []
        if all(column in _SQLITE_METADATA_COLUMN_ALLOWLIST for column in columns):
            return sorted(set(columns))
        return []
    return []


def _summarize_scan_errors(values: list[object]) -> list[dict[str, object]]:
    counts: Counter[tuple[str, int | None, str | None]] = Counter()
    allowed_identity_fields = {"st_dev", "st_ino"}

    for value in values:
        if value == "identity-changed-before-read":
            counts[("identity-changed-before-read", None, None)] += 1
        elif isinstance(value, str) and value.startswith("identity-changed-before-read:"):
            fields = value.partition(":")[2].split(",")
            if fields and all(field in allowed_identity_fields for field in fields):
                for field in set(fields):
                    counts[("identity-changed-before-read", None, field)] += 1
            else:
                counts[("other", None, None)] += 1
        elif value == "root-identity-changed-during-scan":
            counts[("root-identity-change", None, None)] += 1
        elif value == "git-status-changed-during-scan":
            counts[("git-status-change", None, None)] += 1
        elif isinstance(value, str):
            match = re.fullmatch(r"(read|readlink|stat):([0-9]+)", value)
            if match:
                counts[(match.group(1), int(match.group(2)), None)] += 1
            else:
                stat_match = re.search(r":stat:([0-9]+)$", value)
                if stat_match:
                    counts[("stat", int(stat_match.group(1)), None)] += 1
                else:
                    counts[("other", None, None)] += 1
        else:
            counts[("other", None, None)] += 1

    return [
        {"category": category, "errno": errno, "field": field, "count": count}
        for (category, errno, field), count in sorted(
            counts.items(),
            key=lambda item: (
                item[0][0],
                item[0][1] if item[0][1] is not None else -1,
                item[0][2] or "",
            ),
        )
    ]


def _mapper_source_diagnostic(store: Path) -> dict[str, object]:
    """Return only pathless mismatch stages and allowlisted field names."""
    try:
        pointer = json.loads((store / "CURRENT.json").read_text(encoding="utf-8"))
        run_id = pointer.get("run_id")
        if not isinstance(run_id, str) or not run_id or "/" in run_id or "\\" in run_id:
            return {"available": False}
        run_directory = store / "runs" / run_id
        manifest = json.loads(
            (run_directory / "manifest.json").read_text(encoding="utf-8")
        )
        database_name = manifest.get("database", {}).get("path")
        if database_name != "facts.sqlite3":
            return {"available": False}
        connection = sqlite3.connect(
            (run_directory / database_name).as_uri() + "?mode=ro", uri=True
        )
        try:
            rows = connection.execute(
                "SELECT payload_json FROM python_fragments"
            ).fetchall()
        finally:
            connection.close()
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return {"available": False}

    allowed_stages = {
        "inventory-vs-lstat",
        "inventory-vs-fstat-before",
        "fstat-before-vs-after",
        "source-unavailable",
        "source-not-regular",
        "inventory-vs-content-hash",
    }
    allowed_fields = {
        "st_dev",
        "st_ino",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_mode",
        "st_uid",
        "st_gid",
        "st_nlink",
    }
    counts: Counter[tuple[str, str]] = Counter()
    stage_counts: Counter[str] = Counter()
    failures = 0
    for (payload_json,) in rows:
        try:
            payload = json.loads(payload_json)
        except (TypeError, ValueError):
            continue
        failure = payload.get("failure") if isinstance(payload, dict) else None
        if (
            not isinstance(failure, dict)
            or failure.get("status") != "FAILED_SOURCE_SNAPSHOT"
        ):
            continue
        failures += 1
        stage = failure.get("snapshot_mismatch_stage")
        fields = failure.get("snapshot_mismatch_fields")
        if not isinstance(stage, str) or stage not in allowed_stages:
            continue
        stage_counts[stage] += 1
        if not isinstance(fields, list):
            continue
        for field in set(item for item in fields if isinstance(item, str)):
            if field in allowed_fields:
                counts[(stage, field)] += 1
    return {
        "available": True,
        "source_snapshot_failures": failures,
        "stages": [
            {"stage": stage, "count": count}
            for stage, count in sorted(stage_counts.items())
        ],
        "mismatches": [
            {"stage": stage, "field": field, "count": count}
            for (stage, field), count in sorted(counts.items())
        ],
    }


def test_navigation_hash_preserves_crlf_bytes(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    content = b"first line\r\nsecond line\r\n"
    source.write_bytes(content)

    digest, error = _stable_hash(source, source.stat())

    assert error is None
    assert digest == hashlib.sha256(content).hexdigest()


def test_filesystem_identity_round_trips_through_sqlite_as_decimal_text() -> None:
    metadata = SimpleNamespace(
        st_size=1, st_mtime_ns=2, st_ctime_ns=3, st_mode=0o100644,
        st_uid=4, st_gid=5, st_dev=1 << 80, st_ino=1 << 96, st_nlink=1,
    )
    connection = sqlite3.connect(":memory:")
    try:
        _configure_database(connection)
        _insert_inventory_file(connection, "sample.py", metadata, "a" * 64)
        stored = connection.execute(
            "SELECT typeof(device),device,typeof(inode),inode FROM files"
        ).fetchone()
        assert stored == (
            "text", str(metadata.st_dev), "text", str(metadata.st_ino)
        )
        normalized = _inventory_record({"device": stored[1], "inode": stored[3]})
        assert normalized == {"device": metadata.st_dev, "inode": metadata.st_ino}
        assert type(normalized["device"]) is int
        assert type(normalized["inode"]) is int
    finally:
        connection.close()


def test_previous_inventory_hash_reuse_accepts_text_and_legacy_identity() -> None:
    metadata = SimpleNamespace(
        st_dev=1 << 80, st_ino=1 << 96, st_size=7, st_mtime_ns=8,
        st_ctime_ns=9, st_mode=0o100644,
    )
    prefix = ("d" * 64, "hashed")
    suffix = (7, 8, 9, 0o644, "regular", "  ")
    identities = (
        (str(metadata.st_dev), str(metadata.st_ino)),
        (metadata.st_dev, metadata.st_ino),
    )
    for identity in identities:
        records = {"sample.py": (*prefix, *identity, *suffix)}
        assert _previous_hash(
            records, "sample.py", metadata, "regular"
        ) == ("d" * 64, "  ")


def test_consultation_reader_normalizes_text_identity_and_fails_closed(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.py"
    source.write_bytes(b"def sample(): pass\n")
    metadata = source.lstat()
    digest, error = _stable_hash(source, metadata)
    assert error is None
    assert digest is not None
    connection = sqlite3.connect(":memory:")
    try:
        _configure_database(connection)
        _insert_inventory_file(connection, source.name, metadata, digest)
        assert _selected_paths_match_inventory(
            connection, source.parent, (source.name,)
        )
        connection.execute(
            "UPDATE files SET device=? WHERE path=?", ("invalid", source.name)
        )
        assert not _selected_paths_match_inventory(
            connection, source.parent, (source.name,)
        )
    finally:
        connection.close()


def test_sqlite_metadata_overflow_diagnostic_is_pathless_and_allowlisted() -> None:
    metadata = SimpleNamespace(
        st_size=1 << 63, st_mtime_ns=2, st_ctime_ns=3, st_mode=0o100644,
        st_uid=4, st_gid=5, st_dev=1 << 70, st_ino=1 << 80, st_nlink=1,
    )
    assert _metadata_overflow_columns(metadata) == ["size_bytes"]
    stderr = (
        "Traceback: C:\\Users\\private\\secret.txt value=9223372036854775808\n"
        "OverflowError: ARCHAEOLOGY_SQLITE_INTEGER_OVERFLOW:columns=size_bytes"
    )
    columns = _pathless_metadata_overflow_columns(stderr)
    assert columns == ["size_bytes"]
    assert "C:\\Users" not in json.dumps(columns)
    assert "9223372036854775808" not in json.dumps(columns)


def test_python_snapshot_diagnostic_is_pathless_and_allowlisted() -> None:
    errors = [
        PythonMapError(
            "C:\\Users\\private\\sample.py secret=source",
            diagnostic_stage="source-unavailable",
        ),
        PythonMapError(
            "C:\\Users\\private\\sample.py secret=kind",
            diagnostic_stage="source-not-regular",
        ),
        PythonMapError(
            "C:\\Users\\private\\sample.py secret=hash",
            diagnostic_stage="inventory-vs-content-hash",
        ),
        PythonMapError(
            "C:\\Users\\private\\sample.py secret=stat",
            diagnostic_stage="inventory-vs-lstat",
            diagnostic_fields=("st_dev", "st_ino", "C:\\private", "st_size:42"),
        ),
        PythonMapError(
            "C:\\Users\\private\\sample.py",
            diagnostic_stage="C:\\private",
            diagnostic_fields=("st_dev",),
        ),
    ]
    diagnostics = [error.safe_diagnostic() for error in errors]
    assert diagnostics == [
        {"snapshot_mismatch_stage": "source-unavailable"},
        {"snapshot_mismatch_stage": "source-not-regular"},
        {"snapshot_mismatch_stage": "inventory-vs-content-hash"},
        {
            "snapshot_mismatch_stage": "inventory-vs-lstat",
            "snapshot_mismatch_fields": ["st_dev", "st_ino"],
        },
        {},
    ]
    serialized = json.dumps(diagnostics)
    assert "C:\\Users" not in serialized
    assert "secret=" not in serialized
    assert "42" not in serialized


def _navigation_diagnostic(store: Path) -> dict[str, object]:
    """Return pathless scan diagnostics suitable for hosted CI logs."""
    try:
        pointer = json.loads((store / "CURRENT.json").read_text(encoding="utf-8"))
        run_id = pointer.get("run_id")
        if not isinstance(run_id, str) or not run_id or "/" in run_id or "\\" in run_id:
            return {"available": False}
        manifest = json.loads(
            (store / "runs" / run_id / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, TypeError, ValueError):
        return {"available": False}

    failures = manifest.get("failures", [])
    if not isinstance(failures, list):
        failures = []
    diagnostic_errors = list(failures)
    scan_errors_available = False
    database = store / "runs" / run_id / "inventory.sqlite3"
    try:
        connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "SELECT scan_error FROM files WHERE scan_error IS NOT NULL"
            ).fetchall()
        finally:
            connection.close()
        diagnostic_errors = [scan_error for (scan_error,) in rows]
        diagnostic_errors.extend(
            failure
            for failure in failures
            if failure in {
                "root-identity-changed-during-scan",
                "git-status-changed-during-scan",
            }
        )
        scan_errors_available = True
    except (OSError, sqlite3.Error, TypeError, ValueError):
        pass

    scan = manifest.get("scan", {})
    scope = scan.get("scope") if isinstance(scan, dict) else None
    if not isinstance(scope, str) or scope not in {
        "all-working-tree-files",
        "explicit-file-allowlist",
    }:
        scope = "unknown"
    counts = manifest.get("counts", {})
    errors = counts.get("errors") if isinstance(counts, dict) else None
    git = manifest.get("git", {})
    stable = git.get("stable_during_scan") if isinstance(git, dict) else None
    if stable not in (True, False, None):
        stable = "unknown"
    status = manifest.get("status")
    if status not in {"CURRENT", "PARTIAL"}:
        status = "unknown"
    return {
        "available": True,
        "status": status,
        "scope": scope,
        "errors": errors if isinstance(errors, int) and not isinstance(errors, bool) else "unknown",
        "failure_reasons": _summarize_scan_errors(diagnostic_errors),
        "scan_errors_available": scan_errors_available,
        "git_stable_during_scan": stable,
    }


def test_scan_error_summary_exposes_only_identity_field_names() -> None:
    summary = _summarize_scan_errors(
        [
            "identity-changed-before-read:st_dev,st_ino",
            "C:\\Users\\private\\sample.py:read:13",
        ]
    )
    assert summary == [
        {
            "category": "identity-changed-before-read",
            "errno": None,
            "field": "st_dev",
            "count": 1,
        },
        {
            "category": "identity-changed-before-read",
            "errno": None,
            "field": "st_ino",
            "count": 1,
        },
        {"category": "other", "errno": None, "field": None, "count": 1},
    ]
    assert "C:\\Users\\private" not in json.dumps(summary)
    assert "13" not in json.dumps(summary)


def test_supported_scan_maps_and_queries_a_committed_python_repository(tmp_path: Path) -> None:
    repository = tmp_path / "source repository"
    repository.mkdir()
    (repository / "sample.py").write_text(
        "def parse_record(value):\n    return value.strip()\n",
        encoding="utf-8",
    )
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "Archaeology test")
    _git(repository, "config", "user.email", "archaeology-test@example.invalid")
    _git(repository, "add", "sample.py")
    _git(repository, "commit", "--quiet", "-m", "fixture")

    inventory_store = tmp_path / "private inventory"
    mapper_store = tmp_path / "private maps"
    try:
        inventory = _cli(
            "navigation-refresh",
            "--root",
            str(repository),
            "--store",
            str(inventory_store),
        )
    except AssertionError as exc:
        diagnostic = json.dumps(_navigation_diagnostic(inventory_store), sort_keys=True)
        raise AssertionError(f"{exc}\nNavigation scan diagnostic: {diagnostic}") from None
    assert json.loads(inventory)["status"] == "CURRENT"

    try:
        mapped = _cli(
            "mapper-refresh",
            "--inventory-store",
            str(inventory_store),
            "--mapper-store",
            str(mapper_store),
        )
        assert json.loads(mapped)["status"] == "CURRENT"
    except (AssertionError, TypeError, ValueError):
        diagnostic = json.dumps(
            _mapper_source_diagnostic(mapper_store), sort_keys=True
        )
        raise AssertionError(
            f"mapper refresh was not CURRENT; pathless diagnostic: {diagnostic}"
        ) from None

    query = _cli(
        "mapper-query",
        "--mapper-store",
        str(mapper_store),
        "--view",
        "symbols",
        "--limit",
        "10",
        "--without-facts",
        "parse_record",
    )
    query_result = json.loads(query)
    assert query_result["status"] == "PASS"
    assert "parse_record" in query
