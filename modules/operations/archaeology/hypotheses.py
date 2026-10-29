"""Slice 2: read-only, observation-only scanner orchestration."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
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
from .inventory import INVENTORY_SCHEMA, SOURCE_SUFFIXES
from .sandbox import linux_sandbox_command


HYPOTHESES_SCHEMA = "giga.archaeologist.hypotheses.v1"
MAX_TOOL_OUTPUT = 4 * 1024 * 1024
VULTURE_LINE = re.compile(r"^(.*?):(\d+): (.+?) \((\d+)% confidence\)$")


class HypothesisError(ValueError):
    """Scanner evidence cannot be produced without weakening the boundary."""


_LEGACY_TOOL_ROOT = Path.home() / "Documents" / "giga-user"


def _configured_executable(environment_key: str, command: str, legacy_path: Path) -> Path:
    configured = os.environ.get(environment_key)
    if configured:
        return Path(configured)
    discovered = shutil.which(command)
    return Path(discovered) if discovered else legacy_path


def _configured_python() -> Path:
    configured = os.environ.get("GIGA_ARCHAEOLOGIST_CGC_PYTHON")
    return Path(configured) if configured else Path(sys.executable)


@dataclass(frozen=True)
class ScannerPaths:
    vulture: Path = field(
        default_factory=lambda: _configured_executable(
            "GIGA_ARCHAEOLOGIST_VULTURE", "vulture", _LEGACY_TOOL_ROOT / ".venv/bin/vulture"
        )
    )
    jscpd: Path = field(
        default_factory=lambda: _configured_executable(
            "GIGA_ARCHAEOLOGIST_JSCPD", "jscpd",
            _LEGACY_TOOL_ROOT / "node/node_modules/.bin/jscpd",
        )
    )
    cgc_python: Path = field(default_factory=_configured_python)
    cgc_bridge: Path = Path(__file__).with_name("cgc_bridge.py")
    vulture_version: str = "2.16"
    jscpd_version: str = "5.0.16"
    cgc_version: str = "0.6.8"

    @classmethod
    def from_tools_root(cls, root: Path) -> "ScannerPaths":
        try:
            root = root.expanduser().resolve(strict=True)
        except OSError as exc:
            raise HypothesisError("scanner tools root is unavailable") from exc
        return cls(
            vulture=root / ".venv/bin/vulture",
            jscpd=root / "node/node_modules/.bin/jscpd",
            cgc_python=root / ".venv/bin/python",
        )


def _load_inventory(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HypothesisError("inventory is not strict UTF-8 JSON") from exc
    try:
        validate_self_hash(value)
    except EvidenceError as exc:
        raise HypothesisError(str(exc)) from exc
    if value.get("schema") != INVENTORY_SCHEMA:
        raise HypothesisError("unsupported inventory schema")
    if (
        value.get("authority_granted") is not False
        or value.get("cleanup_permitted") is not False
    ):
        raise HypothesisError("inventory authority boundary is not closed")
    if not isinstance(value.get("files"), list):
        raise HypothesisError("inventory files are missing")
    return value, raw


def _safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise HypothesisError(f"non-canonical inventory path: {value!r}")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise HypothesisError(f"non-canonical inventory path: {value!r}")
    return value


def _copy_projection(inventory: Mapping[str, Any], projection: Path) -> list[str]:
    repository = Path(inventory["repository"]["root"]).resolve(strict=True)
    projected: list[str] = []
    for record in inventory["files"]:
        relative = _safe_relative(record.get("path"))
        if (
            record.get("kind") != "regular"
            or PurePosixPath(relative).suffix not in SOURCE_SUFFIXES
        ):
            continue
        source = repository / relative
        before = source.lstat()
        if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode):
            raise HypothesisError(
                f"inventory source is no longer a regular file: {relative}"
            )
        content = source.read_bytes()
        after = source.lstat()
        if (
            (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
            or len(content) != record.get("bytes")
            or sha256_bytes(content) != record.get("sha256")
        ):
            raise HypothesisError(f"source drifted from inventory: {relative}")
        target = projection / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_bytes(content)
        target.chmod(0o400)
        projected.append(relative)
    return sorted(projected)


def _seatbelt_profile(scratch: Path) -> str:
    escaped = str(scratch).replace('"', '\\"')
    global_config = str(Path.home() / ".codegraphcontext").replace('"', '\\"')
    return "\n".join(
        [
            "(version 1)",
            "(allow default)",
            "(deny network*)",
            "(deny file-write*)",
            f'(allow file-write* (subpath "{escaped}"))',
            '(allow file-write* (literal "/dev/null"))',
            f'(deny file-write* (literal "{global_config}"))',
            f'(deny file-write* (subpath "{global_config}"))',
            "",
        ]
    )


def _run_bounded(
    tool_id: str,
    argv: Sequence[str],
    scratch: Path,
    *,
    accepted_exit_codes: frozenset[int],
    timeout: int,
    use_sandbox: bool,
    read_only: Sequence[Path] = (),
) -> tuple[dict[str, Any], bytes, bytes]:
    stdout_path = scratch / f"{tool_id}.stdout"
    stderr_path = scratch / f"{tool_id}.stderr"
    environment = {
        "LC_ALL": "C",
        "TZ": "UTC",
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(scratch),
        "XDG_CACHE_HOME": str(scratch / "cache"),
        "NO_COLOR": "1",
    }
    command = list(argv)
    if use_sandbox and sys.platform == "linux":
        command = linux_sandbox_command(
            scratch, command, read_only=read_only, cwd=scratch
        )
    elif use_sandbox and sys.platform == "darwin":
        profile = scratch / f"{tool_id}.sb"
        profile.write_text(_seatbelt_profile(scratch), encoding="utf-8")
        command = ["/usr/bin/sandbox-exec", "-f", str(profile), *command]
    elif use_sandbox:
        raise HypothesisError("no admitted scanner sandbox for this platform")
    with (
        stdout_path.open("wb") as stdout_handle,
        stderr_path.open("wb") as stderr_handle,
    ):
        process = subprocess.Popen(
            command,
            cwd=scratch,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )
        timed_out = False
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            return_code = process.wait()
    stdout = stdout_path.read_bytes()
    stderr = stderr_path.read_bytes()
    overflow = len(stdout) > MAX_TOOL_OUTPUT or len(stderr) > MAX_TOOL_OUTPUT
    if timed_out:
        status = "TIMEOUT"
    elif overflow:
        status = "OUTPUT_LIMIT"
    elif return_code in accepted_exit_codes:
        status = "PASS"
    else:
        status = "ERROR"
    normalized = [item.replace(str(scratch), "<SCRATCH>") for item in argv]
    return (
        {
            "id": tool_id,
            "status": status,
            "argv": normalized,
            "exit_code": return_code,
            "timed_out": timed_out,
            "output_overflow": overflow,
            "sandboxed": use_sandbox,
            "network_authorized": False,
            "stdout": {"bytes": len(stdout), "sha256": sha256_bytes(stdout)},
            "stderr": {"bytes": len(stderr), "sha256": sha256_bytes(stderr)},
        },
        stdout if not overflow else b"",
        stderr if not overflow else b"",
    )


def _hypothesis(
    tool: str, kind: str, paths: list[str], detail: Mapping[str, Any]
) -> dict[str, Any]:
    identity = {"tool": tool, "kind": kind, "paths": paths, "detail": dict(detail)}
    return {
        "id": sha256_bytes(canonical_bytes(identity)),
        "tool": tool,
        "kind": kind,
        "paths": paths,
        "detail": dict(detail),
        "state": "OBSERVED",
        "authority_granted": False,
        "cleanup_permitted": False,
    }


def _relative_tool_path(value: str, projection: Path) -> str | None:
    candidate = Path(value)
    try:
        if candidate.is_absolute():
            return candidate.resolve(strict=False).relative_to(projection).as_posix()
    except ValueError:
        return None
    normalized = candidate.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    projection_prefix = projection.name + "/"
    if normalized.startswith(projection_prefix):
        normalized = normalized[len(projection_prefix) :]
    projected = projection / normalized
    if not projected.is_file() and ":" in normalized:
        path_without_format, _separator, _format = normalized.rpartition(":")
        if (projection / path_without_format).is_file():
            normalized = path_without_format
    try:
        relative = _safe_relative(normalized)
    except HypothesisError:
        return None
    if not (projection / relative).is_file():
        return None
    return relative


def _parse_vulture(stdout: bytes, projection: Path) -> list[dict[str, Any]]:
    findings = []
    for line in stdout.decode("utf-8", "replace").splitlines():
        match = VULTURE_LINE.match(line)
        if not match:
            continue
        relative = _relative_tool_path(match.group(1), projection)
        if relative is None:
            continue
        findings.append(
            _hypothesis(
                "vulture",
                "python-unused-observation",
                [relative],
                {
                    "line": int(match.group(2)),
                    "message": match.group(3),
                    "tool_confidence_percent": int(match.group(4)),
                },
            )
        )
    return findings


def _parse_jscpd(path: Path, projection: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    findings = []
    for duplicate in payload.get("duplicates", []):
        first = duplicate.get("firstFile", {})
        second = duplicate.get("secondFile", {})
        first_path = _relative_tool_path(first.get("name", ""), projection)
        second_path = _relative_tool_path(second.get("name", ""), projection)
        if first_path is None or second_path is None:
            continue
        findings.append(
            _hypothesis(
                "jscpd",
                "syntactic-duplicate-observation",
                sorted([first_path, second_path]),
                {
                    "format": duplicate.get("format"),
                    "lines": duplicate.get("lines"),
                    "tokens": duplicate.get("tokens"),
                    "first": {"start": first.get("start"), "end": first.get("end")},
                    "second": {"start": second.get("start"), "end": second.get("end")},
                },
            )
        )
    return findings


def _parse_cgc(path: Path, projection: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    findings = []
    for item in payload.get("potentially_unused_functions", []):
        relative = _relative_tool_path(item.get("path", ""), projection)
        if relative is None:
            continue
        findings.append(
            _hypothesis(
                "codegraphcontext",
                "graph-unreferenced-function-observation",
                [relative],
                {
                    "line": item.get("line_number"),
                    "symbol": item.get("function_name"),
                    "tool_confidence": item.get("confidence"),
                    "tool_reason": item.get("confidence_reason"),
                },
            )
        )
    return findings


def build_hypotheses(
    inventory_path: Path,
    scanner_paths: ScannerPaths | None = None,
    *,
    use_sandbox: bool = True,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    scanners = scanner_paths or ScannerPaths()
    for executable in (
        scanners.vulture,
        scanners.jscpd,
        scanners.cgc_python,
        scanners.cgc_bridge,
    ):
        if not executable.is_file():
            raise HypothesisError(f"scanner executable is missing: {executable}")
    inventory, inventory_raw = _load_inventory(inventory_path)
    global_config = Path.home() / ".codegraphcontext"
    global_config_before = _path_identity(global_config)
    parent = inventory_path.resolve(strict=True).parent
    with tempfile.TemporaryDirectory(prefix=".slice02-", dir=parent) as temporary:
        scratch = Path(temporary)
        projection = scratch / "projection"
        projection.mkdir(mode=0o700)
        projected = _copy_projection(inventory, projection)
        scanner_inputs = tuple(dict.fromkeys((
            projection,
            scanners.vulture.parent.parent,
            scanners.jscpd.parent.parent,
            scanners.cgc_python.parent.parent,
            scanners.cgc_bridge,
        )))
        tool_records: list[dict[str, Any]] = []
        raw_outputs: dict[str, bytes] = {}
        findings: list[dict[str, Any]] = []

        vulture_argv = [str(scanners.vulture), str(projection), "--min-confidence", "0"]
        record, stdout, stderr = _run_bounded(
            "vulture",
            vulture_argv,
            scratch,
            accepted_exit_codes=frozenset({0, 3}),
            timeout=300,
            use_sandbox=use_sandbox,
            read_only=scanner_inputs,
        )
        record["version"] = scanners.vulture_version
        tool_records.append(record)
        raw_outputs["vulture.stdout"] = stdout
        raw_outputs["vulture.stderr"] = stderr
        if record["status"] == "PASS":
            findings.extend(_parse_vulture(stdout, projection))

        jscpd_dir = scratch / "jscpd"
        jscpd_argv = [
            str(scanners.jscpd),
            str(projection),
            "--reporters",
            "json",
            "--output",
            str(jscpd_dir),
            "--min-lines",
            "5",
            "--min-tokens",
            "40",
            "--silent",
        ]
        record, stdout, stderr = _run_bounded(
            "jscpd",
            jscpd_argv,
            scratch,
            accepted_exit_codes=frozenset({0}),
            timeout=300,
            use_sandbox=use_sandbox,
            read_only=scanner_inputs,
        )
        record["version"] = scanners.jscpd_version
        report_path = jscpd_dir / "jscpd-report.json"
        if record["status"] == "PASS" and not report_path.is_file():
            record["status"] = "ERROR"
            record["reason"] = "JSON report missing"
        tool_records.append(record)
        raw_outputs["jscpd.stdout"] = stdout
        raw_outputs["jscpd.stderr"] = stderr
        if report_path.is_file() and report_path.stat().st_size <= MAX_TOOL_OUTPUT:
            raw_outputs["jscpd.report.json"] = report_path.read_bytes()
        if record["status"] == "PASS":
            findings.extend(_parse_jscpd(report_path, projection))

        cgc_output = scratch / "cgc-result.json"
        cgc_argv = [
            str(scanners.cgc_python),
            str(scanners.cgc_bridge),
            "--projection",
            str(projection),
            "--config-root",
            str(scratch / "cgc-config"),
            "--database",
            str(scratch / "cgc-db"),
            "--output",
            str(cgc_output),
        ]
        record, stdout, stderr = _run_bounded(
            "codegraphcontext",
            cgc_argv,
            scratch,
            accepted_exit_codes=frozenset({0}),
            timeout=900,
            use_sandbox=use_sandbox,
            read_only=scanner_inputs,
        )
        record["version"] = scanners.cgc_version
        if record["status"] == "PASS" and not cgc_output.is_file():
            record["status"] = "ERROR"
            record["reason"] = "analysis result missing"
        tool_records.append(record)
        raw_outputs["codegraphcontext.stdout"] = stdout
        raw_outputs["codegraphcontext.stderr"] = stderr
        if cgc_output.is_file() and cgc_output.stat().st_size <= MAX_TOOL_OUTPUT:
            raw_outputs["codegraphcontext.result.json"] = cgc_output.read_bytes()
        if record["status"] == "PASS":
            findings.extend(_parse_cgc(cgc_output, projection))

        source_before = {
            item["path"]: item["sha256"]
            for item in inventory["files"]
            if item["path"] in projected
        }
        source_after = {
            relative: sha256_bytes(
                (Path(inventory["repository"]["root"]) / relative).read_bytes()
            )
            for relative in projected
        }
        if source_before != source_after:
            raise HypothesisError("source repository changed during scanner execution")
        if _path_identity(global_config) != global_config_before:
            raise HypothesisError(
                "scanner changed the global CodeGraphContext configuration"
            )
        if any(
            item["state"] != "OBSERVED" or item["cleanup_permitted"]
            for item in findings
        ):
            raise HypothesisError("scanner attempted to mint authority")

        payload = seal_document(
            {
                "schema": HYPOTHESES_SCHEMA,
                "authority": "read-only-observation",
                "authority_granted": False,
                "cleanup_permitted": False,
                "inventory": {
                    "path": str(inventory_path.resolve(strict=True)),
                    "file_sha256": sha256_bytes(inventory_raw),
                    "receipt_sha256": inventory["receipt_sha256"],
                    "repository_head": inventory["repository"]["head"],
                    "repository_tree": inventory["repository"]["tree"],
                },
                "projection": {
                    "files": len(projected),
                    "path_list_sha256": sha256_bytes(canonical_bytes(projected)),
                    "persisted": False,
                    "source_unchanged": True,
                },
                "tools": sorted(tool_records, key=lambda item: item["id"]),
                "findings": sorted(findings, key=lambda item: item["id"]),
                "summary": {
                    "observations": len(findings),
                    "tools_passed": sum(
                        item["status"] == "PASS" for item in tool_records
                    ),
                    "tools_not_passed": sum(
                        item["status"] != "PASS" for item in tool_records
                    ),
                    "states": {"OBSERVED": len(findings)},
                },
            }
        )
        return payload, raw_outputs


def _path_identity(path: Path) -> tuple[int, int, int, int, int] | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def render_hypotheses_report(payload: Mapping[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# GIGA Archaeology scanner observations",
        "",
        f"- Inventory receipt: `{payload['inventory']['receipt_sha256']}`",
        f"- Observations: {summary['observations']}",
        f"- Tools passed: {summary['tools_passed']}",
        f"- Tools not passed: {summary['tools_not_passed']}",
        f"- Receipt SHA-256: `{payload['receipt_sha256']}`",
        "",
        "Every item is only `OBSERVED`. No item is established dead, redundant, disconnected, safe, or removable.",
        "A tool failure is preserved as evidence and cannot improve a hypothesis state.",
        "",
    ]
    for tool in payload["tools"]:
        lines.append(f"- `{tool['id']}` {tool['version']}: {tool['status']}")
    lines.append("")
    return "\n".join(lines)


def write_hypotheses(
    inventory_path: Path,
    output: Path,
    scanner_paths: ScannerPaths | None = None,
    *,
    use_sandbox: bool = True,
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists() or output.is_symlink():
        raise HypothesisError("hypothesis output directory must not already exist")
    payload, raw_outputs = build_hypotheses(
        inventory_path, scanner_paths=scanner_paths, use_sandbox=use_sandbox
    )
    output.mkdir(parents=True, mode=0o700)
    try:
        write_atomic(output / "hypotheses.json", canonical_bytes(payload))
        write_atomic(
            output / "HYPOTHESES_REPORT.md",
            render_hypotheses_report(payload).encode("utf-8"),
        )
        for name, content in sorted(raw_outputs.items()):
            write_atomic(output / "tools" / name, content)
    except EvidenceError as exc:
        raise HypothesisError(str(exc)) from exc
    return payload
