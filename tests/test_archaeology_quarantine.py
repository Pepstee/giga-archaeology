from __future__ import annotations

import json
import os
import subprocess
import socket
import sys
from pathlib import Path

import pytest

from modules.operations.archaeology.evidence import (
    canonical_bytes,
    seal_document,
    validate_self_hash,
)
from modules.operations.archaeology.judge import build_judgement
from modules.operations.archaeology.quarantine import (
    PROBE_ARGV,
    QuarantineError,
    _sandbox_profile,
    _sandbox_command,
    write_quarantine_canary,
)
from test_archaeology_judge import _candidate_evidence

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="quarantine probe sandbox is not supported on Windows"
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _judge(paths: dict[str, Path], tmp_path: Path) -> tuple[Path, str]:
    value = build_judgement(
        paths["inventory"], paths["hypotheses"], paths["counter"], paths["history"]
    )
    judge = tmp_path / "judge.json"
    judge.write_bytes(canonical_bytes(value))
    return judge, value["decisions"][0]["hypothesis_id"]


def _run(paths: dict[str, Path], judge: Path, hypothesis: str, output: Path):
    return write_quarantine_canary(
        paths["repository"],
        paths["inventory"],
        paths["hypotheses"],
        paths["counter"],
        paths["history"],
        judge,
        hypothesis,
        output,
    )


def _require_linux_namespace_runtime(tmp_path: Path) -> None:
    if sys.platform != "linux":
        return
    repository = tmp_path / "sandbox-preflight-repository"
    scratch = tmp_path / "sandbox-preflight-scratch"
    repository.mkdir()
    scratch.mkdir()
    process = subprocess.run(
        _sandbox_command(repository, scratch, [PROBE_ARGV[0], "-c", "pass"]),
        capture_output=True,
        timeout=10,
    )
    if process.returncode:
        detail = process.stderr.decode("utf-8", "replace").lower()
        if "operation not permitted" in detail or "permission denied" in detail:
            pytest.skip(
                "Linux runner lacks the user/network namespace capability required by bubblewrap"
            )
        pytest.fail(f"bubblewrap sandbox preflight failed: {detail}")


def test_candidate_is_quarantined_probed_and_restored(tmp_path: Path) -> None:
    _require_linux_namespace_runtime(tmp_path)
    paths = _candidate_evidence(
        tmp_path,
        probe_argv=list(PROBE_ARGV),
    )
    judge, hypothesis = _judge(paths, tmp_path)
    target = paths["repository"] / "src/candidate.py"
    before = target.read_bytes()
    payload = _run(paths, judge, hypothesis, tmp_path / "output")
    validate_self_hash(payload)
    assert payload["status"] == "PASS"
    assert payload["restored"] is True
    assert payload["probe"]["network_authorized"] is False
    assert payload["probe"]["repository_write_authorized"] is False
    assert target.read_bytes() == before
    assert (
        _git(paths["repository"], "status", "--porcelain=v1", "--untracked-files=all")
        == ""
    )
    assert not (paths["repository"] / ".giga-archaeologist-quarantine").exists()
    assert all(
        os.stat(path, follow_symlinks=False).st_mode & 0o777 == 0o600
        for path in (tmp_path / "output").iterdir()
    )


def test_failed_probe_is_rejected_but_restored(tmp_path: Path) -> None:
    paths = _candidate_evidence(
        tmp_path, probe_argv=list(PROBE_ARGV), probe_should_pass=False
    )
    judge, hypothesis = _judge(paths, tmp_path)
    payload = _run(paths, judge, hypothesis, tmp_path / "output")
    assert payload["status"] == "REJECT"
    assert payload["restored"] is True
    assert (
        _git(paths["repository"], "status", "--porcelain=v1", "--untracked-files=all")
        == ""
    )


def test_non_candidate_refuses_before_quarantine(tmp_path: Path) -> None:
    paths = _candidate_evidence(tmp_path, probe_argv=list(PROBE_ARGV))
    value = json.loads(paths["counter"].read_text())
    value.pop("receipt_sha256")
    value["records"][0]["counterevidence_state"] = "PRESENT"
    paths["counter"].write_bytes(canonical_bytes(seal_document(value)))
    counter = json.loads(paths["counter"].read_text())
    history = json.loads(paths["history"].read_text())
    history.pop("receipt_sha256")
    history["inputs"]["counterevidence"] = {
        "file_sha256": __import__("hashlib")
        .sha256(paths["counter"].read_bytes())
        .hexdigest(),
        "receipt_sha256": counter["receipt_sha256"],
    }
    paths["history"].write_bytes(canonical_bytes(seal_document(history)))
    judge, hypothesis = _judge(paths, tmp_path)
    with pytest.raises(QuarantineError, match="does not authorize"):
        _run(paths, judge, hypothesis, tmp_path / "output")
    assert (
        _git(paths["repository"], "status", "--porcelain=v1", "--untracked-files=all")
        == ""
    )


def test_forged_judge_refuses_exact_reproduction(tmp_path: Path) -> None:
    paths = _candidate_evidence(tmp_path, probe_argv=list(PROBE_ARGV))
    judge, hypothesis = _judge(paths, tmp_path)
    value = json.loads(judge.read_text())
    value.pop("receipt_sha256")
    value["summary"]["VERIFIED_CANDIDATE"] = 99
    judge.write_bytes(canonical_bytes(seal_document(value)))
    with pytest.raises(QuarantineError, match="does not reproduce"):
        _run(paths, judge, hypothesis, tmp_path / "output")
    assert (
        _git(paths["repository"], "status", "--porcelain=v1", "--untracked-files=all")
        == ""
    )


def test_non_scratch_repository_refuses(tmp_path: Path) -> None:
    paths = _candidate_evidence(tmp_path, probe_argv=list(PROBE_ARGV))
    judge, hypothesis = _judge(paths, tmp_path)
    with pytest.raises(QuarantineError, match="scratch tree"):
        write_quarantine_canary(
            Path("/"),
            paths["inventory"],
            paths["hypotheses"],
            paths["counter"],
            paths["history"],
            judge,
            hypothesis,
            tmp_path / "output",
        )


@pytest.mark.skipif(sys.platform != "darwin", reason="Darwin sandbox profile")
def test_probe_sandbox_blocks_personal_reads_and_repository_writes(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    scratch = tmp_path / "scratch"
    repository.mkdir()
    scratch.mkdir()
    private_root = tmp_path / "private"
    private_root.mkdir()
    private_file = private_root / "credential.txt"
    private_file.write_text("private", encoding="utf-8")
    profile = _sandbox_profile(repository.resolve(), scratch.resolve(), private_root.resolve())
    personal = subprocess.run(
        [
            "/usr/bin/sandbox-exec",
            "-p",
            profile,
            "--",
            "/bin/cat",
            str(private_file),
        ],
        capture_output=True,
        check=False,
    )
    assert personal.returncode != 0
    assert personal.stdout == b""
    blocked = subprocess.run(
        [
            "/usr/bin/sandbox-exec",
            "-p",
            profile,
            "--",
            "/usr/bin/touch",
            str(repository / "forbidden"),
        ],
        capture_output=True,
        check=False,
    )
    assert blocked.returncode != 0
    assert not (repository / "forbidden").exists()
    allowed = subprocess.run(
        [
            "/usr/bin/sandbox-exec",
            "-p",
            profile,
            "--",
            "/usr/bin/touch",
            str(scratch / "allowed"),
        ],
        capture_output=True,
        check=False,
    )
    assert allowed.returncode == 0
    assert (scratch / "allowed").is_file()


@pytest.mark.skipif(sys.platform != "linux", reason="Linux sandbox runtime")
def test_linux_probe_denies_host_reads_writes_and_network(tmp_path: Path) -> None:
    _require_linux_namespace_runtime(tmp_path)
    repository = tmp_path / "repository"
    scratch = tmp_path / "scratch"
    repository.mkdir()
    scratch.mkdir()
    outside = tmp_path / "host-only"
    outside.write_text("synthetic private sentinel")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        source = f'''from pathlib import Path
import socket
assert not Path({str(outside)!r}).exists()
try:
    Path({str(repository / "forbidden")!r}).write_text("bad")
except OSError:
    pass
else:
    raise AssertionError("repository write allowed")
try:
    socket.create_connection(("127.0.0.1", {port}), timeout=1)
except OSError:
    pass
else:
    raise AssertionError("host network reachable")
Path({str(scratch / "allowed")!r}).write_text("ok")
'''
        process = subprocess.run(
            _sandbox_command(repository, scratch, [PROBE_ARGV[0], "-c", source]),
            capture_output=True, timeout=10,
        )
    assert process.returncode == 0, process.stderr.decode()
    assert outside.read_text() == "synthetic private sentinel"
    assert not (repository / "forbidden").exists()
    assert (scratch / "allowed").read_text() == "ok"
