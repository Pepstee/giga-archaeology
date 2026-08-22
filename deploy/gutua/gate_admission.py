#!/usr/bin/env python3
"""Machine gate between findings and mutable repair dispatch."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence


APPROVING_DECISIONS = {
    "CONTINUE",
    "REPAIR_WITHIN_SCOPE",
    "APPROVE_SCOPE_EXCEPTION",
}

WRITER_LEASE_ROOT = Path(
    "/home/gutua/software-factory/.control/fable-governed-dfi-20260725/writer-leases"
)


class WriterLeaseUnavailable(RuntimeError):
    """Another mutable worker already owns the worktree."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _usage_from_stdout(path: Path) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {"status": "UNKNOWN"}
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("total_cost_usd"), (int, float)):
            return {
                "status": "KNOWN",
                "total_cost_usd": value["total_cost_usd"],
                "session_id": value.get("session_id"),
            }
    return {"status": "UNKNOWN"}


@contextmanager
def exclusive_worktree_lease(
    worktree: Path,
    *,
    lease_root: Path = WRITER_LEASE_ROOT,
) -> Iterator[None]:
    """Hold a non-blocking, process-scoped lease for one resolved worktree."""
    resolved = worktree.resolve(strict=True)
    lease_root.mkdir(parents=True, exist_ok=True)
    lease_name = hashlib.sha256(os.fsencode(resolved)).hexdigest() + ".lock"
    fd = os.open(lease_root / lease_name, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WriterLeaseUnavailable(
                f"mutable writer already active for {resolved}"
            ) from exc
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()} {resolved}\n".encode())
        os.fsync(fd)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def run_writer_command(
    worktree: Path,
    command: Sequence[str],
    *,
    timeout_seconds: float,
    lease_root: Path = WRITER_LEASE_ROOT,
    run_dir: Path | None = None,
) -> int:
    """Run one mutable provider as an owned process group under a worktree lease."""
    if not command:
        raise ValueError("writer command is required")
    if run_dir is None:
        raise ValueError("run_dir is required for durable writer capture")
    run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    invocation_id = str(uuid.uuid4())
    argv_digest = hashlib.sha256(
        json.dumps(list(command), separators=(",", ":")).encode()
    ).hexdigest()
    invocation = {
        "schema": "giga.provider-invocation.v1",
        "invocation_id": invocation_id,
        "created_at": _utc_now(),
        "worktree": str(worktree.resolve(strict=True)),
        "argv_sha256": argv_digest,
        "timeout_seconds": timeout_seconds,
    }
    _write_exclusive_json(run_dir / "invocation.json", invocation)
    stdout_path = run_dir / "stdout.jsonl"
    stderr_path = run_dir / "stderr.log"
    with exclusive_worktree_lease(worktree, lease_root=lease_root):
        with stdout_path.open("xb", buffering=0) as stdout_fh, stderr_path.open(
            "xb", buffering=0
        ) as stderr_fh:
            process = subprocess.Popen(
                list(command),
                cwd=worktree,
                start_new_session=True,
                stdout=stdout_fh,
                stderr=stderr_fh,
            )
            _write_exclusive_json(
                run_dir / "launched.json",
                {**invocation, "launched_at": _utc_now(), "pid": process.pid},
            )
            try:
                returncode = process.wait(timeout=timeout_seconds)
            except (KeyboardInterrupt, subprocess.TimeoutExpired) as exc:
                reason = "KEYBOARD_INTERRUPT" if isinstance(exc, KeyboardInterrupt) else "TIMEOUT"
                _write_exclusive_json(
                    run_dir / "timeout.json",
                    {
                        "schema": "giga.provider-timeout.v1",
                        "invocation_id": invocation_id,
                        "recorded_at": _utc_now(),
                        "reason": reason,
                        "pid": process.pid,
                    },
                )
                _terminate_process_group(process)
                _write_exclusive_json(
                    run_dir / "termination.json",
                    {
                        "schema": "giga.provider-termination.v1",
                        "invocation_id": invocation_id,
                        "recorded_at": _utc_now(),
                        "pid": process.pid,
                        "returncode": process.returncode,
                    },
                )
                _write_exclusive_json(
                    run_dir / "settlement.json",
                    {
                        "schema": "giga.provider-settlement.v1",
                        "invocation_id": invocation_id,
                        "recorded_at": _utc_now(),
                        "outcome": "INTERRUPTED",
                        "returncode": process.returncode,
                        "usage": _usage_from_stdout(stdout_path),
                    },
                )
                raise
            _write_exclusive_json(
                run_dir / "settlement.json",
                {
                    "schema": "giga.provider-settlement.v1",
                    "invocation_id": invocation_id,
                    "recorded_at": _utc_now(),
                    "outcome": "COMPLETED",
                    "returncode": returncode,
                    "usage": _usage_from_stdout(stdout_path),
                },
            )
            return returncode


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decide(
    findings_path: Path,
    ruling_path: Path | None,
    receipt_path: Path | None,
) -> tuple[bool, str]:
    findings = json.loads(findings_path.read_text(encoding="utf-8"))
    expansions = [
        finding
        for finding in findings.get("findings", [])
        if finding.get("status", "open") == "open"
        and finding.get("classification") == "ARCHITECTURE_EXPANSION"
    ]
    if not expansions:
        return True, "no open ARCHITECTURE_EXPANSION finding"
    if ruling_path is None or receipt_path is None:
        return False, "Fable ruling and receipt required"

    ruling = json.loads(ruling_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "giga.fable-gate-receipt.v1":
        return False, "invalid Fable receipt schema"
    if receipt.get("ruling_sha256") != digest(ruling_path):
        return False, "Fable ruling hash does not match receipt"
    if ruling.get("decision") not in APPROVING_DECISIONS:
        return False, f"Fable decision {ruling.get('decision')!r} does not admit repair"

    finding_ids = {str(finding.get("id")) for finding in expansions}
    ratified_ids = {str(value) for value in ruling.get("ratified_finding_ids", [])}
    if not finding_ids <= ratified_ids:
        missing = sorted(finding_ids - ratified_ids)
        return False, f"open expansions lack exact Fable ratification: {missing}"
    return True, "all open architecture expansions have hash-bound Fable ratification"


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "constitution":
        from constitutional_gate import main as constitutional_main

        return constitutional_main(arguments[1:])
    parser = argparse.ArgumentParser()
    parser.add_argument("--findings", type=Path)
    parser.add_argument("--ruling", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--writer-worktree", type=Path)
    parser.add_argument("--writer-timeout", type=float, default=1800)
    parser.add_argument("--writer-run-dir", type=Path)
    parser.add_argument("writer_command", nargs=argparse.REMAINDER)
    args = parser.parse_args(arguments)
    if args.writer_worktree is not None:
        command = args.writer_command
        if command[:1] == ["--"]:
            command = command[1:]
        try:
            return run_writer_command(
                args.writer_worktree,
                command,
                timeout_seconds=args.writer_timeout,
                run_dir=args.writer_run_dir,
            )
        except WriterLeaseUnavailable as exc:
            print(json.dumps({"admitted": False, "reason": str(exc)}, sort_keys=True))
            return 42
    if args.findings is None:
        parser.error("--findings is required unless --writer-worktree is used")
    admitted, reason = decide(args.findings, args.ruling, args.receipt)
    print(json.dumps({"admitted": admitted, "reason": reason}, sort_keys=True))
    return 0 if admitted else 42


if __name__ == "__main__":
    raise SystemExit(main())
