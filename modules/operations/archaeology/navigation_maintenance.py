"""Non-blocking daily and milestone maintenance for the navigation indexes."""

from __future__ import annotations

import os
import signal
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .evidence import canonical_bytes, seal_document, sha256_bytes
from .navigation_inventory import (
    _replace_atomic,
    refresh_navigation_inventory,
    refresh_navigation_inventory_delta,
)
from .os_support import lock_file
from .semantic_graph import (
    GraphifyConfig,
    SemanticGraphError,
    _private_store,
    _verify_local_model,
    refresh_semantic_graph,
)
from .retention import RetentionPolicy, run_navigation_retention
from .scip_map import ScipRefreshConfig, refresh_scip_store


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
        raise NavigationMaintenanceError(
            "managed model startup requires exact port 1235"
        )
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
    mapper_store: Path | None = None,
    scip: ScipRefreshConfig | None = None,
    runtime_registries: tuple[Path, ...] = (),
    startup_timeout: int = 180,
    mode: str = "full",
    retention_policy: RetentionPolicy | None = None,
    retention_reference_roots: tuple[Path, ...] = (),
    retention_enabled: bool = True,
) -> dict[str, Any]:
    """Refresh both layers and always preserve a terminal local receipt."""
    if not reason or "\x00" in reason:
        raise NavigationMaintenanceError("maintenance reason must be non-empty")
    if mode not in {"full", "delta"}:
        raise NavigationMaintenanceError("maintenance mode must be full or delta")
    semantic_store = _private_store(semantic_store)
    maintenance = semantic_store / "maintenance"
    maintenance.mkdir(exist_ok=True, mode=0o700)
    lock_path = maintenance / "maintenance.lock"
    lock = lock_path.open("a+b")
    os.chmod(lock_path, 0o600)
    try:
        try:
            lock_file(lock, blocking=False)
        except BlockingIOError:
            return {
                "schema": MAINTENANCE_SCHEMA,
                "status": "SKIPPED_ALREADY_RUNNING",
                "reason": reason,
            }
        run_id = (
            f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid.uuid4().hex[:12]}"
        )
        staging = maintenance / f".staging-{run_id}"
        staging.mkdir(mode=0o700)
        started_at = _utc_now()
        started = time.monotonic()
        owned_process = stdout = stderr = None
        inventory_result: dict[str, Any] | None = None
        semantic_result: dict[str, Any] | None = None
        mapper_result: dict[str, Any] | None = None
        scip_result: dict[str, Any] | None = None
        scip_manifests: tuple[Path, ...] = ()
        retention_result: dict[str, Any] | None = None
        errors: list[tuple[str, BaseException]] = []
        try:
            inventory = (
                refresh_navigation_inventory(root, inventory_store)
                if mode == "full"
                else refresh_navigation_inventory_delta(root, inventory_store)
            )
            inventory_result = {
                "status": inventory.manifest["status"],
                "run_id": inventory.manifest["run_id"],
                "receipt_sha256": inventory.manifest["receipt_sha256"],
                "files": inventory.manifest["counts"]["files"],
            }
        except BaseException as exc:
            errors.append(("inventory", exc))
        if inventory_result is not None and scip is not None:
            try:
                scip_run = refresh_scip_store(
                    inventory_store,
                    scip.store,
                    node=scip.node,
                    python_indexer_entrypoint=scip.python_indexer_entrypoint,
                    python_package_json=scip.python_package_json,
                    typescript_indexer_entrypoint=scip.typescript_indexer_entrypoint,
                    typescript_package_json=scip.typescript_package_json,
                    timeout_seconds=scip.timeout_seconds,
                )
                scip_manifests = scip_run.manifest_paths
                scip_result = {
                    "status": scip_run.catalog["status"],
                    "run_id": scip_run.catalog["run_id"],
                    "receipt_sha256": scip_run.catalog["receipt_sha256"],
                    "inventory_run_id": inventory_result["run_id"],
                    "catalog_inventory_run_id": scip_run.catalog["inventory"]["run_id"],
                    "inventory_binding_status": scip_run.inventory_binding_status,
                    "indexes": scip_run.catalog["counts"]["indexes"],
                    "documents": scip_run.catalog["counts"]["documents"],
                    "occurrences": scip_run.catalog["counts"]["occurrences"],
                    "bytes": scip_run.catalog["counts"]["bytes"],
                    "excluded_files": sum(
                        item.get("excluded_files", 0)
                        for item in scip_run.catalog["indexes"]
                    ),
                }
            except BaseException as exc:
                errors.append(("scip", exc))
        if inventory_result is not None and mode == "full":
            try:
                owned_process, stdout, stderr = _ensure_model(
                    graphify,
                    model_server_executable,
                    model_path,
                    staging,
                    startup_timeout,
                )
                semantic = refresh_semantic_graph(
                    inventory_store, semantic_store, graphify
                )
                semantic_result = {
                    "status": semantic.manifest["status"],
                    "run_id": semantic.manifest["run_id"],
                    "receipt_sha256": semantic.manifest["receipt_sha256"],
                    "nodes": semantic.manifest["graph"]["nodes"],
                    "edges": semantic.manifest["graph"]["edges"],
                }
            except BaseException as exc:
                errors.append(("semantic", exc))
            finally:
                _stop_owned_model(owned_process, stdout, stderr)
        elif inventory_result is not None:
            semantic_result = {
                "status": "SKIPPED_FAST_DELTA",
                "reason": "semantic reconciliation is reserved for the daily/full lane",
            }
        if (
            inventory_result is not None
            and mapper_store is not None
            and (scip is None or scip_result is not None)
        ):
            try:
                from .mapper import refresh_mapper

                semantic_input = (
                    semantic_store
                    if (semantic_store / "CURRENT.json").is_file()
                    else None
                )
                mapper = refresh_mapper(
                    inventory_store,
                    mapper_store,
                    runtime_registries=runtime_registries,
                    semantic_store=semantic_input,
                    scip_manifests=scip_manifests,
                )
                mapper_result = {
                    "status": mapper.manifest["status"],
                    "run_id": mapper.manifest["run_id"],
                    "receipt_sha256": mapper.manifest["receipt_sha256"],
                    "inventory_run_id": mapper.manifest["inventory"]["run_id"],
                    "entities": mapper.manifest["counts"]["entities"],
                    "relations": mapper.manifest["counts"]["relations"],
                }
            except BaseException as exc:
                errors.append(("mapper", exc))
        retention_prerequisites_met = (
            inventory_result is not None
            and (mapper_store is None or mapper_result is not None)
            and (scip is None or scip_result is not None)
        )
        if retention_enabled and retention_prerequisites_met:
            try:
                root_path = Path(root).resolve(strict=True)
                defaults = (
                    root_path / "architecture/archaeology/reports",
                    root_path / "architecture/archaeology/receipts",
                    # Historical evidence retains its original path identity.
                    root_path / "architecture/archaeologist/reports",
                    root_path / "architecture/archaeologist/receipts",
                    semantic_store / "maintenance/runs",
                )
                if mapper_store is not None:
                    defaults += (
                        Path(mapper_store).absolute().parent / "consultations",
                    )
                retention = run_navigation_retention(
                    inventory_store,
                    mapper_store,
                    semantic_store,
                    scip_store=None if scip is None else scip.store,
                    reference_roots=tuple(
                        path
                        for path in (*defaults, *retention_reference_roots)
                        if path.exists()
                    ),
                    policy=retention_policy,
                    apply=True,
                )
                retention_result = {
                    "status": retention["status"],
                    "run_id": retention["run_id"],
                    "receipt_sha256": retention["receipt_sha256"],
                    "plan_status": retention["plan_status"],
                    "candidate_generations": retention["candidate_generations"],
                    "candidate_bytes": retention["candidate_bytes"],
                    "compaction_candidate_generations": retention[
                        "compaction_candidate_generations"
                    ],
                    "compaction_candidate_bytes": retention[
                        "compaction_candidate_bytes"
                    ],
                    "storage_quota_satisfied_after_plan": retention[
                        "storage_quota_satisfied_after_plan"
                    ],
                    "quarantine": retention["quarantine"],
                    "purges": retention["purges"],
                    "compactions": retention["compactions"],
                }
            except BaseException as exc:
                errors.append(("retention", exc))
        elif retention_enabled:
            retention_result = {
                "status": "SKIPPED_REFRESH_NOT_PUBLISHED",
                "reason": "retention runs only after authenticated inventory/mapper publication",
            }
        blocking_phase_failed = any(
            phase in {"inventory", "scip", "mapper"} for phase, _exc in errors
        )
        status = (
            "FAILED_NON_BLOCKING"
            if blocking_phase_failed
            else "PARTIAL_NON_BLOCKING"
            if errors
            else "PASS"
        )
        receipt = seal_document(
            {
                "schema": MAINTENANCE_SCHEMA,
                "status": status,
                "run_id": run_id,
                "reason": reason,
                "mode": mode,
                "started_at": started_at,
                "finished_at": _utc_now(),
                "duration_seconds": round(time.monotonic() - started, 6),
                "root": str(root.resolve(strict=True)),
                "inventory_store": str(Path(inventory_store).resolve(strict=False)),
                "semantic_store": str(semantic_store),
                "inventory": inventory_result,
                "semantic": semantic_result,
                "scip": scip_result,
                "mapper": mapper_result,
                "retention": retention_result,
                "model_server_started_by_run": owned_process is not None,
                "error": None
                if not errors
                else {
                    "phase": errors[0][0],
                    "type": type(errors[0][1]).__name__,
                    "reason": str(errors[0][1])[-4000:],
                },
                "errors": [
                    {
                        "phase": phase,
                        "type": type(exc).__name__,
                        "reason": str(exc)[-4000:],
                    }
                    for phase, exc in errors
                ],
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
                "receipt_file_sha256": sha256_bytes(
                    (final / "receipt.json").read_bytes()
                ),
                "updated_at": receipt["finished_at"],
            }
        )
        _replace_atomic(maintenance / "CURRENT.json", canonical_bytes(pointer))
        return receipt
    finally:
        lock.close()
