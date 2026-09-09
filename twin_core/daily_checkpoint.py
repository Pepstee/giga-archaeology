"""Fail-closed daily Git checkpointing for sanctioned GIGA knowledge changes."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .integrity import authority_path

SCHEMA = "giga.daily-checkpoint.v1"
TECHNICAL_PREFIXES = ("twin_core/", "scripts/", "tests/", "modules/", "contracts/")
TECHNICAL_EXACT = {"pyproject.toml", "README.md", "AGENTS.md", "CONTEXT.md", "CHARTER.md"}
DENIED_PARTS = {
    "memory", "private", "personal", "corpus", "vault", "profile", "profiles",
    "credentials", "credential", "secrets", "secret", "exports", "export",
    "quarantine", "upstreams", "runtime", "graphify-out", "data", "raw", ".git",
}


class DailyCheckpointError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckpointBaseline:
    root: Path
    head: str
    branch: str
    upstream: str | None
    run_id: str
    write_set: tuple[str, ...]
    push_remote: str | None
    push_branch: str | None
    push_url: str | None


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
         "-c", "user.name=Artiom Gutu", "-c", "user.email=gutu.artiom444@gmail.com",
         "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env={**os.environ, "GIT_AUTHOR_NAME": "Artiom Gutu",
             "GIT_AUTHOR_EMAIL": "gutu.artiom444@gmail.com",
             "GIT_COMMITTER_NAME": "Artiom Gutu",
             "GIT_COMMITTER_EMAIL": "gutu.artiom444@gmail.com"},
    )
    if check and result.returncode:
        raise DailyCheckpointError((result.stderr or result.stdout).strip())
    return result


def _staged_sha256(root: Path, relative: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f":{relative}"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise DailyCheckpointError(result.stderr.decode(errors="replace").strip())
    return hashlib.sha256(result.stdout).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _status(root: Path) -> list[tuple[str, str]]:
    raw = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    fields = raw.split("\0")
    records: list[tuple[str, str]] = []
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        if len(field) < 4:
            raise DailyCheckpointError("unparseable Git status record")
        code, path = field[:2], field[3:]
        if "R" in code or "C" in code:
            raise DailyCheckpointError("daily checkpoint does not accept rename/copy status")
        records.append((code, path))
    return records


def _allowed(relative: str) -> bool:
    path = Path(relative)
    if (not relative or path.is_absolute() or ".." in path.parts
            or relative != path.as_posix() or relative.endswith("/")):
        return False
    if DENIED_PARTS.intersection(part.casefold() for part in path.parts):
        return False
    return relative in TECHNICAL_EXACT or any(relative.startswith(p) for p in TECHNICAL_PREFIXES)


def _technical_path(root: Path, relative: str) -> Path:
    if not _allowed(relative):
        raise DailyCheckpointError(f"not an admitted technical file: {relative}")
    try:
        path = authority_path(root, relative)
    except ValueError as exc:
        raise DailyCheckpointError(str(exc)) from exc
    if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
        raise DailyCheckpointError(f"not a regular single-link technical file: {relative}")
    return path


def _fresh(baseline: CheckpointBaseline) -> None:
    root = baseline.root
    if _git(root, "rev-parse", "HEAD").stdout.strip() != baseline.head:
        raise DailyCheckpointError("HEAD changed during the daily run")
    if _git(root, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip() != baseline.branch:
        raise DailyCheckpointError("branch changed during the daily run")


def _push_binding(baseline: CheckpointBaseline) -> None:
    if not baseline.push_remote or not baseline.push_branch or not baseline.push_url:
        raise DailyCheckpointError("push requires an explicit remote and branch binding")
    if not baseline.push_branch.startswith("codex/") or baseline.branch != baseline.push_branch:
        raise DailyCheckpointError("push target must be the exact nonprotected codex branch")
    root = baseline.root
    upstream = _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}").stdout.strip()
    remote = _git(root, "config", f"branch.{baseline.branch}.remote").stdout.strip()
    merge = _git(root, "config", f"branch.{baseline.branch}.merge").stdout.strip()
    url = _git(root, "remote", "get-url", "--push", baseline.push_remote).stdout.strip()
    if (upstream != baseline.upstream or remote != baseline.push_remote
            or merge != f"refs/heads/{baseline.push_branch}" or url != baseline.push_url):
        raise DailyCheckpointError("push upstream binding changed")


def begin_daily_checkpoint(
    root: Path,
    *,
    run_id: str,
    write_set: tuple[str, ...],
    push_remote: str | None = None,
    push_branch: str | None = None,
    cleanup_lock: Path | None = None,
    require_upstream: bool = False,
) -> CheckpointBaseline:
    root = root.resolve()
    if not write_set or len(set(write_set)) != len(write_set):
        raise DailyCheckpointError("an exact nonempty technical write set is required")
    for relative in write_set:
        _technical_path(root, relative)
    if (push_remote is None) != (push_branch is None):
        raise DailyCheckpointError("push requires both remote and branch")
    top = Path(_git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if top != root:
        raise DailyCheckpointError("daily checkpoint root is not the Git worktree root")
    lock = cleanup_lock or Path.home() / ".giga/locks/giga-user-cleanup-sequence.v1.lock"
    if lock.exists():
        raise DailyCheckpointError("cleanup writer lock is active; daily checkpoint refused")
    dirty = _status(root)
    if dirty:
        raise DailyCheckpointError(
            "daily checkpoint requires a clean baseline; pre-existing changes: "
            + ", ".join(path for _, path in dirty[:12])
        )
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if branch.returncode:
        raise DailyCheckpointError("daily checkpoint refuses detached HEAD")
    upstream_result = _git(
        root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", check=False
    )
    upstream = upstream_result.stdout.strip() if upstream_result.returncode == 0 else None
    if require_upstream and upstream is None:
        raise DailyCheckpointError("daily checkpoint requires a configured push upstream")
    baseline = CheckpointBaseline(
        root=root,
        head=_git(root, "rev-parse", "HEAD").stdout.strip(),
        branch=branch.stdout.strip(),
        upstream=upstream,
        run_id=run_id,
        write_set=tuple(write_set),
        push_remote=push_remote,
        push_branch=push_branch,
        push_url=_git(root, "remote", "get-url", "--push", push_remote).stdout.strip() if push_remote else None,
    )
    if push_remote:
        _push_binding(baseline)
    return baseline


def complete_daily_checkpoint(
    baseline: CheckpointBaseline,
    *,
    day: str,
    details: dict[str, Any],
    push: bool = False,
) -> dict[str, Any]:
    root = baseline.root
    _fresh(baseline)
    if date.fromisoformat(day).isoformat() != day:
        raise DailyCheckpointError("checkpoint day must be an ISO date")
    if push:
        _push_binding(baseline)
    changes = _status(root)
    rejected = [path for _, path in changes if path not in baseline.write_set or not _allowed(path)]
    if rejected:
        raise DailyCheckpointError(
            "daily checkpoint encountered out-of-scope changes: " + ", ".join(rejected[:12])
        )
    files: list[dict[str, Any]] = []
    for code, relative in changes:
        path = _technical_path(root, relative)
        if "D" in code or not path.is_file() or path.is_symlink():
            raise DailyCheckpointError(f"daily checkpoint refuses deletion or unsafe file: {relative}")
        files.append({"path": relative, "sha256": _sha256(path), "bytes": path.stat().st_size})
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "result": "ready-to-commit",
        "run_id": baseline.run_id,
        "day": day,
        "branch": baseline.branch,
        "upstream": baseline.upstream,
        "parent_commit": baseline.head,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "files": sorted(files, key=lambda item: item["path"]),
        "details": details,
        "scope_policy": {
            "allowed_exact": sorted(baseline.write_set),
            "private_corpus": False,
            "deletions": False,
            "pre_existing_dirty_tree": False,
        },
    }
    receipt["receipt_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    receipt_path = (
        root / "runtime/outputs/daily-checkpoints"
        / f"{day}-{receipt['receipt_sha256']}.json"
    )
    try:
        authority_path(root, receipt_path.relative_to(root).as_posix())
    except ValueError as exc:
        raise DailyCheckpointError(str(exc)) from exc
    _atomic_json(receipt_path, receipt)
    relative_receipt = receipt_path.relative_to(root).as_posix()
    staged_paths = [item["path"] for item in files] + [relative_receipt]
    approved_hashes = {item["path"]: item["sha256"] for item in files}
    approved_hashes[relative_receipt] = _sha256(receipt_path)
    try:
        _fresh(baseline)
        for relative in baseline.write_set:
            _technical_path(root, relative)
        _git(root, "add", "--", *staged_paths)
        staged = _git(root, "diff", "--cached", "--name-only").stdout.splitlines()
        if sorted(staged) != sorted(staged_paths):
            raise DailyCheckpointError("staged daily checkpoint differs from the approved write set")
        staged_hashes = {path: _staged_sha256(root, path) for path in staged_paths}
        if staged_hashes != approved_hashes:
            raise DailyCheckpointError("staged content differs from the hash-approved write set")
        _fresh(baseline)
        _git(root, "commit", "-m", f"daily: knowledge checkpoint {day}")
    except Exception:
        _git(root, "restore", "--staged", "--", *staged_paths, check=False)
        raise
    commit = _git(root, "rev-parse", "HEAD").stdout.strip()
    if _status(root):
        raise DailyCheckpointError("daily checkpoint committed but worktree is not clean")
    if push:
        if baseline.upstream is None:
            raise DailyCheckpointError("daily push requested without a configured upstream")
        _push_binding(baseline)
        if _git(root, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip() != baseline.branch:
            raise DailyCheckpointError("branch changed before push")
        _git(root, "push", "--porcelain", baseline.push_url, f"{commit}:refs/heads/{baseline.push_branch}")
    return {
        "schema": SCHEMA,
        "result": "committed",
        "run_id": baseline.run_id,
        "parent_commit": baseline.head,
        "commit": commit,
        "receipt": relative_receipt,
        "files_committed": len(staged_paths),
        "pushed": push,
        "upstream": baseline.upstream,
    }


def report_daily_failure(
    *,
    run_id: str,
    error: Exception,
    destination: Path | None = None,
) -> Path:
    destination = destination or Path.home() / ".giga/daily-checkpoint-failures"
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "result": "failed",
        "run_id": run_id,
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "error_class": type(error).__name__,
        "error": str(error)[:2_000],
        "success_claim_allowed": False,
    }
    report["report_sha256"] = hashlib.sha256(_canonical(report)).hexdigest()
    path = destination / f"{report['report_sha256']}.json"
    _atomic_json(path, report)
    return path
