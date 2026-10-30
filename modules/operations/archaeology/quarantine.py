"""Slice 6: reversible quarantine canary for a verified synthetic candidate."""

from __future__ import annotations

import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .evidence import (
    EvidenceError,
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
    write_atomic,
)
from .inventory import INVENTORY_SCHEMA
from .judge import JUDGE_SCHEMA, build_judgement
from .sandbox import linux_sandbox_command


QUARANTINE_SCHEMA = "giga.archaeologist.quarantine-canary.v1"
DISPOSABLE_SCHEMA = "giga.archaeologist.disposable-fixture.v1"
HASH = re.compile(r"[0-9a-f]{64}")
OUTPUT_LIMIT = 1_048_576
TIMEOUT_SECONDS = 60
PROBE_ARGV = (
    "/usr/bin/python3" if sys.platform == "linux" else "/opt/homebrew/bin/python3",
    "-m",
    "unittest",
    "discover",
    "-s",
    "tests",
    "-q",
)


class QuarantineError(ValueError):
    """Quarantine cannot proceed or exact restoration cannot be proven."""


def _load(path: Path, schema: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8", "strict"))
        validate_self_hash(value)
    except (UnicodeDecodeError, json.JSONDecodeError, EvidenceError) as exc:
        raise QuarantineError("input is not canonical self-hashed UTF-8 JSON") from exc
    if value.get("schema") != schema:
        raise QuarantineError(f"unsupported input schema: {value.get('schema')!r}")
    return value, raw


def _git(root: Path, *arguments: str) -> bytes:
    process = subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        env={
            "LC_ALL": "C",
            "TZ": "UTC",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_OPTIONAL_LOCKS": "0",
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if (
        process.returncode
        or len(process.stdout) > OUTPUT_LIMIT
        or len(process.stderr) > OUTPUT_LIMIT
    ):
        raise QuarantineError(f"bounded Git inspection failed: {' '.join(arguments)}")
    return process.stdout


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise QuarantineError("candidate path is not canonical and repository-relative")
    if path.parts[0] in {".git", ".giga-archaeologist-quarantine"}:
        raise QuarantineError("candidate path is inside a protected control directory")
    return path


def _metadata(path: Path) -> dict[str, Any]:
    value = os.lstat(path)
    if (
        not stat.S_ISREG(value.st_mode)
        or value.st_nlink != 1
        or value.st_uid != os.getuid()
    ):
        raise QuarantineError(
            "candidate must be a current-UID regular single-link file"
        )
    raw = path.read_bytes()
    return {
        "dev": value.st_dev,
        "ino": value.st_ino,
        "mode": stat.S_IMODE(value.st_mode),
        "uid": value.st_uid,
        "nlink": value.st_nlink,
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
    }


def _snapshot(root: Path) -> dict[str, Any]:
    status = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    return {
        "head": _git(root, "rev-parse", "HEAD").decode().strip(),
        "tree": _git(root, "rev-parse", "HEAD^{tree}").decode().strip(),
        "status_sha256": sha256_bytes(status),
        "status_bytes": len(status),
    }


def _configured_private_root() -> Path:
    configured = os.environ.get("GIGA_ARCHAEOLOGIST_PRIVATE_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / "Private").resolve()


def _sandbox_profile(repository: Path, scratch: Path, private_root: Path | None = None) -> str:
    def literal(path: Path) -> str:
        return str(path).replace("\\", "\\\\").replace('"', '\\"')

    if private_root is None:
        private_root = _configured_private_root()

    return "\n".join(
        [
            "(version 1)",
            "(allow default)",
            "(deny network*)",
            "(deny file-write*)",
            f'(deny file-read* (subpath "{literal(private_root)}"))',
            f'(allow file-read* (subpath "{literal(repository)}"))',
            f'(allow file-read* (subpath "{literal(scratch)}"))',
            f'(allow file-write* (subpath "{literal(scratch)}"))',
            '(allow file-write-data (literal "/dev/null"))',
            f'(deny file-write* (subpath "{literal(repository)}"))',
        ]
    )


def _sandbox_command(repository: Path, scratch: Path, argv: Sequence[str]) -> list[str]:
    if sys.platform == "darwin":
        return ["/usr/bin/sandbox-exec", "-p", _sandbox_profile(repository, scratch), "--", *argv]
    if sys.platform != "linux":
        raise QuarantineError("no admitted probe sandbox for this platform")
    return linux_sandbox_command(scratch, argv, read_only=[repository], cwd=repository)


def _run_probe(repository: Path, argv: Sequence[str]) -> dict[str, Any]:
    if tuple(argv) != PROBE_ARGV:
        raise QuarantineError(
            "disposable fixture does not use the single admitted probe argv"
        )
    with tempfile.TemporaryDirectory(prefix="giga-archaeologist-probe-") as temporary:
        scratch = Path(temporary).resolve(strict=True)
        command = _sandbox_command(repository, scratch, argv)
        process = subprocess.Popen(
            command,
            cwd=repository,
            env={
                "LC_ALL": "C",
                "TZ": "UTC",
                "HOME": str(scratch),
                "TMPDIR": str(scratch),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        overflow = len(stdout) > OUTPUT_LIMIT or len(stderr) > OUTPUT_LIMIT
        return {
            "argv": list(argv),
            "exit_code": process.returncode,
            "timed_out": timed_out,
            "output_overflow": overflow,
            "stdout_sha256": sha256_bytes(stdout[:OUTPUT_LIMIT]),
            "stderr_sha256": sha256_bytes(stderr[:OUTPUT_LIMIT]),
            "stdout_bytes": len(stdout),
            "stderr_bytes": len(stderr),
            "network_authorized": False,
            "repository_write_authorized": False,
            "passed": process.returncode == 0 and not timed_out and not overflow,
        }


def run_quarantine_canary(
    repository: Path,
    inventory_path: Path,
    hypotheses_path: Path,
    counterevidence_path: Path,
    history_path: Path,
    judge_path: Path,
    hypothesis_id: str,
) -> dict[str, Any]:
    repository = repository.resolve(strict=True)
    scratch_roots = (
        (Path("/tmp"),) if sys.platform == "linux"
        else (Path("/private/tmp"), Path("/private/var/folders"))
    )
    if not any(repository.is_relative_to(root) for root in scratch_roots):
        raise QuarantineError(
            "quarantine is permitted only in a disposable platform scratch tree"
        )
    if repository.is_symlink() or os.lstat(repository).st_uid != os.getuid():
        raise QuarantineError("disposable repository root identity is unsafe")
    marker, marker_raw = _load(
        repository / ".giga-archaeologist-disposable.json", DISPOSABLE_SCHEMA
    )
    if (
        marker.get("disposable") is not True
        or marker.get("cleanup_permitted") is not False
    ):
        raise QuarantineError(
            "repository lacks an explicit non-cleanup disposable marker"
        )
    if tuple(marker.get("probe_argv", [])) != PROBE_ARGV:
        raise QuarantineError("disposable marker does not bind the admitted probe")
    if _git(repository, "remote").strip():
        raise QuarantineError("disposable quarantine repository must have no remotes")
    before = _snapshot(repository)
    if before["status_bytes"] != 0:
        raise QuarantineError("disposable repository must start clean")

    inventory, inventory_raw = _load(inventory_path, INVENTORY_SCHEMA)
    judge, judge_raw = _load(judge_path, JUDGE_SCHEMA)
    reproduced = build_judgement(
        inventory_path, hypotheses_path, counterevidence_path, history_path
    )
    if canonical_bytes(reproduced) != judge_raw:
        raise QuarantineError(
            "Judge document does not reproduce from its exact evidence chain"
        )
    if inventory["repository"]["root"] != str(repository):
        raise QuarantineError("inventory does not bind the disposable repository")
    if judge["inputs"]["inventory"] != {
        "file_sha256": sha256_bytes(inventory_raw),
        "receipt_sha256": inventory["receipt_sha256"],
    }:
        raise QuarantineError("Judge does not bind the supplied inventory")
    if (
        judge.get("authority_granted") is not False
        or judge.get("deletion_permitted") is not False
    ):
        raise QuarantineError("Judge authority boundary is not closed")
    decisions = [
        item
        for item in judge["decisions"]
        if item.get("hypothesis_id") == hypothesis_id
    ]
    if len(decisions) != 1:
        raise QuarantineError("exactly one Judge decision must match the hypothesis")
    decision = decisions[0]
    if (
        decision.get("classification") != "VERIFIED_CANDIDATE"
        or decision.get("quarantine_candidate") is not True
        or decision.get("cleanup_permitted") is not False
        or decision.get("deletion_permitted") is not False
    ):
        raise QuarantineError("Judge decision does not authorize a quarantine canary")
    paths = decision.get("subject", {}).get("paths")
    if not isinstance(paths, list) or len(paths) != 1 or not isinstance(paths[0], str):
        raise QuarantineError("quarantine candidate must bind exactly one path")
    relative = _safe_relative(paths[0])
    if marker.get("target_path") != relative.as_posix():
        raise QuarantineError(
            "disposable marker target does not match the Judge candidate"
        )
    inventory_records = [
        item for item in inventory["files"] if item.get("path") == relative.as_posix()
    ]
    if len(inventory_records) != 1 or inventory_records[0].get("kind") != "regular":
        raise QuarantineError("candidate is absent from the bound inventory")
    target = repository.joinpath(*relative.parts)
    before_target = _metadata(target)
    if before_target["sha256"] != inventory_records[0].get("sha256"):
        raise QuarantineError("candidate bytes drifted from the inventory")
    tracked = _git(repository, "ls-files", "--error-unmatch", "--", relative.as_posix())
    if tracked.decode().strip() != relative.as_posix():
        raise QuarantineError("candidate is not exactly one tracked path")

    quarantine = (
        repository / ".giga-archaeologist-quarantine" / hypothesis_id / relative
    )
    quarantine.parent.mkdir(parents=True, mode=0o700)
    probe: dict[str, Any] | None = None
    during: dict[str, Any] | None = None
    restoration_error: Exception | None = None
    try:
        os.rename(target, quarantine)
        if (
            target.exists()
            or target.is_symlink()
            or _metadata(quarantine)["sha256"] != before_target["sha256"]
        ):
            raise QuarantineError("candidate quarantine transition is not exact")
        during = _snapshot(repository)
        if during["status_bytes"] == 0:
            raise QuarantineError("Git did not observe the quarantine transition")
        probe = _run_probe(repository, marker.get("probe_argv", []))
    finally:
        try:
            if quarantine.exists() and not target.exists() and not target.is_symlink():
                target.parent.mkdir(parents=True, exist_ok=True)
                os.rename(quarantine, target)
            control = repository / ".giga-archaeologist-quarantine"
            for parent in quarantine.parents:
                if parent == control.parent:
                    break
                if parent.exists():
                    parent.rmdir()
        except Exception as exc:  # exact restoration failure must remain terminal
            restoration_error = exc
    if restoration_error is not None:
        raise QuarantineError(f"automatic restoration failed: {restoration_error}")
    after_target = _metadata(target)
    after = _snapshot(repository)
    restored = after == before and after_target == before_target
    if not restored:
        raise QuarantineError(
            "automatic restoration did not reproduce the exact starting state"
        )
    if probe is None or during is None:
        raise QuarantineError("quarantine canary did not reach the probe boundary")
    status = "PASS" if probe["passed"] else "REJECT"
    return seal_document(
        {
            "schema": QUARANTINE_SCHEMA,
            "status": status,
            "authority": "disposable-quarantine-canary-only",
            "authority_granted": False,
            "cleanup_permitted": False,
            "deletion_permitted": False,
            "restored": True,
            "inputs": {
                "inventory": {
                    "file_sha256": sha256_bytes(inventory_raw),
                    "receipt_sha256": inventory["receipt_sha256"],
                },
                "judge": {
                    "file_sha256": sha256_bytes(judge_raw),
                    "receipt_sha256": judge["receipt_sha256"],
                },
                "marker": {
                    "file_sha256": sha256_bytes(marker_raw),
                    "receipt_sha256": marker["receipt_sha256"],
                },
            },
            "hypothesis_id": hypothesis_id,
            "target_path": relative.as_posix(),
            "target_before": before_target,
            "repository_before": before,
            "repository_during": during,
            "probe": probe,
            "target_after": after_target,
            "repository_after": after,
            "claims": [
                "candidate quarantined in disposable repository",
                "fixed probe executed",
                "exact source state restored",
            ],
            "nonclaims": [
                "live GIGA target quarantined",
                "cleanup authorized",
                "deletion authorized",
                "production behavior certified",
            ],
        }
    )


def render_quarantine_report(payload: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# GIGA Archaeology reversible quarantine canary",
            "",
            f"- Status: {payload['status']}",
            f"- Hypothesis: `{payload['hypothesis_id']}`",
            f"- Target: `{payload['target_path']}`",
            f"- Probe exit: {payload['probe']['exit_code']}",
            f"- Exact restoration: {str(payload['restored']).lower()}",
            f"- Receipt SHA-256: `{payload['receipt_sha256']}`",
            "",
            "This receipt covers a deliberately disposable fixture only. It grants no cleanup or deletion authority.",
            "",
        ]
    )


def write_quarantine_canary(
    repository: Path,
    inventory_path: Path,
    hypotheses_path: Path,
    counterevidence_path: Path,
    history_path: Path,
    judge_path: Path,
    hypothesis_id: str,
    output: Path,
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists() or output.is_symlink():
        raise QuarantineError("quarantine output directory must not already exist")
    payload = run_quarantine_canary(
        repository,
        inventory_path,
        hypotheses_path,
        counterevidence_path,
        history_path,
        judge_path,
        hypothesis_id,
    )
    output.mkdir(parents=True, mode=0o700)
    try:
        write_atomic(output / "quarantine.json", canonical_bytes(payload))
        write_atomic(
            output / "QUARANTINE_REPORT.md",
            render_quarantine_report(payload).encode("utf-8"),
        )
    except EvidenceError as exc:
        raise QuarantineError(str(exc)) from exc
    return payload
