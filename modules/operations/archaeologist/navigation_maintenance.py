"""Non-blocking daily and milestone maintenance for the navigation indexes."""

from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .evidence import canonical_bytes, seal_document, sha256_bytes
from .navigation_inventory import _replace_atomic, refresh_navigation_inventory
from .semantic_graph import (
    GraphifyConfig,
    SemanticGraphError,
    _private_store,
    _verify_local_model,
    refresh_semantic_graph,
)


MAINTENANCE_SCHEMA = "giga.navigation.maintenance-receipt.v1"
MAINTENANCE_POINTER_SCHEMA = "giga.navigation.maintenance-current.v1"


class NavigationMaintenanceError(ValueError):
    """The maintenance controller could not produce a truthful terminal receipt."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _start_model_server(
    executable: Path,
    model_path: Path,
    endpoint: str,
    logs: Path,
) -> tuple[subprocess.Popen[bytes], Any, Any]:
    if endpoint != "http://127.0.0.1:1235/v1":
        raise NavigationMaintenanceError("managed model startup requires exact port 1235")
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise NavigationMaintenanceError("MLX model server executable is unavailable")
    if not model_path.is_dir():
        raise NavigationMaintenanceError("local model snapshot is unavailable")
    stdout = (logs / "model-server.stdout").open("wb")
    stderr = (logs / "model-server.stderr").open("wb")
    try:
        process = subprocess.Popen(
            [
                str(executable),
                "--model",
                str(model_path),
                "--host",
                "127.0.0.1",
                "--port",
                "1235",
                "--max-tokens",
                "4096",
                "--temp",
                "0",
                "--prompt-cache-size",
                "2",
                "--log-level",
                "INFO",
            ],
            env={
                "HF_HUB_OFFLINE": "1",
                "HOME": str(Path.home()),
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
                "TRANSFORMERS_OFFLINE": "1",
                "TZ": "UTC",
            },
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
    except BaseException:
        stdout.close()
        stderr.close()
        raise
    return process, stdout, stderr


def _ensure_model(
    config: GraphifyConfig,
    server_executable: Path,
    model_path: Path,
    logs: Path,
    startup_timeout: int,
) -> tuple[subprocess.Popen[bytes] | None, Any | None, Any | None]:
    try:
        _verify_local_model(config)
        return None, None, None
    except SemanticGraphError:
        pass
    process, stdout, stderr = _start_model_server(
        server_executable, model_path, config.endpoint, logs
    )
    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            _verify_local_model(config)
            return process, stdout, stderr
        except SemanticGraphError:
            time.sleep(1)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()
    stdout.close()
    stderr.close()
    raise NavigationMaintenanceError("local model server did not become ready")


def _stop_owned_model(
    process: subprocess.Popen[bytes] | None,
    stdout: Any | None,
    stderr: Any | None,
) -> None:
    if process is not None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    if stdout is not None:
        stdout.close()
    if stderr is not None:
        stderr.close()


def run_navigation_maintenance(
    root: Path,
    inventory_store: Path,
    semantic_store: Path,
    *,
    reason: str,
    graphify: GraphifyConfig,
    model_server_executable: Path,
    model_path: Path,
    startup_timeout: int = 180,
) -> dict[str, Any]:
    """Refresh both layers and always preserve a terminal local receipt."""
    if not reason or "\x00" in reason:
        raise NavigationMaintenanceError("maintenance reason must be non-empty")
    semantic_store = _private_store(semantic_store)
    maintenance = semantic_store / "maintenance"
    maintenance.mkdir(exist_ok=True, mode=0o700)
    lock_path = maintenance / "maintenance.lock"
    lock = lock_path.open("a+b")
    os.chmod(lock_path, 0o600)
    try:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {
                "schema": MAINTENANCE_SCHEMA,
                "status": "SKIPPED_ALREADY_RUNNING",
                "reason": reason,
            }
        run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid.uuid4().hex[:12]}"
        staging = maintenance / f".staging-{run_id}"
        staging.mkdir(mode=0o700)
        started_at = _utc_now()
        started = time.monotonic()
        owned_process = stdout = stderr = None
        inventory_result: dict[str, Any] | None = None
        semantic_result: dict[str, Any] | None = None
        error: BaseException | None = None
        try:
            inventory = refresh_navigation_inventory(root, inventory_store)
            inventory_result = {
                "status": inventory.manifest["status"],
                "run_id": inventory.manifest["run_id"],
                "receipt_sha256": inventory.manifest["receipt_sha256"],
                "files": inventory.manifest["counts"]["files"],
            }
            owned_process, stdout, stderr = _ensure_model(
                graphify,
                model_server_executable,
                model_path,
                staging,
                startup_timeout,
            )
            semantic = refresh_semantic_graph(inventory_store, semantic_store, graphify)
            semantic_result = {
                "status": semantic.manifest["status"],
                "run_id": semantic.manifest["run_id"],
                "receipt_sha256": semantic.manifest["receipt_sha256"],
                "nodes": semantic.manifest["graph"]["nodes"],
                "edges": semantic.manifest["graph"]["edges"],
            }
        except BaseException as exc:  # preserve receipt, then return non-blocking failure
            error = exc
        finally:
            _stop_owned_model(owned_process, stdout, stderr)
        receipt = seal_document(
            {
                "schema": MAINTENANCE_SCHEMA,
                "status": "PASS" if error is None else "FAILED_NON_BLOCKING",
                "run_id": run_id,
                "reason": reason,
                "started_at": started_at,
                "finished_at": _utc_now(),
                "duration_seconds": round(time.monotonic() - started, 6),
                "root": str(root.resolve(strict=True)),
                "inventory_store": str(Path(inventory_store).resolve(strict=False)),
                "semantic_store": str(semantic_store),
                "inventory": inventory_result,
                "semantic": semantic_result,
                "model_server_started_by_run": owned_process is not None,
                "error": None
                if error is None
                else {"type": type(error).__name__, "reason": str(error)[-4000:]},
                "normal_engineering_blocked": False,
            }
        )
        receipt_path = staging / "receipt.json"
        receipt_path.write_bytes(canonical_bytes(receipt))
        os.chmod(receipt_path, 0o600)
        runs = maintenance / "runs"
        runs.mkdir(exist_ok=True, mode=0o700)
        final = runs / run_id
        os.rename(staging, final)
        pointer = seal_document(
            {
                "schema": MAINTENANCE_POINTER_SCHEMA,
                "run_id": run_id,
                "status": receipt["status"],
                "maintenance_receipt_sha256": receipt["receipt_sha256"],
                "receipt_file_sha256": sha256_bytes((final / "receipt.json").read_bytes()),
                "updated_at": receipt["finished_at"],
            }
        )
        _replace_atomic(maintenance / "CURRENT.json", canonical_bytes(pointer))
        return receipt
    finally:
        lock.close()
