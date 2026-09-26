"""Adopt the canonical mapper as the first step of architectural work.

This is deliberately an orchestration/receipt boundary, not another scanner or
graph owner.  It asks the existing mapper which sources are relevant, refreshes
only those source paths (or performs a full reconciliation for an exhaustive
claim), recompiles the canonical facts, verifies the consulted sources against
the live filesystem, and publishes a non-authorizing consultation receipt.
"""

from __future__ import annotations

import os
import sqlite3
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from .dossier import build_context_projection
from .evidence import canonical_bytes, seal_document
from .mapper import current_mapper_run, refresh_mapper
from .navigation_inventory import (
    current_navigation_run,
    locate_navigation_inventory,
    refresh_navigation_inventory,
    refresh_navigation_inventory_delta,
)


CONSULTATION_SCHEMA = "giga.archaeology.architecture-consultation.v2"
CONSULTATION_CONTEXT_BUDGET = 512
TASK_DOSSIERS = {
    "architecture": "architecture",
    "ownership": "consolidation",
    "duplication": "consolidation",
    "consolidation": "consolidation",
    "feature-loss": "claim_review",
}


class ConsultationError(ValueError):
    """A bounded architecture consultation could not be proved."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _safe_relative(path: str) -> str:
    pure = PurePosixPath(path)
    if (
        not path
        or "\x00" in path
        or pure.is_absolute()
        or ".." in pure.parts
        or pure.as_posix() != path
    ):
        raise ConsultationError(f"unsafe relevant path: {path!r}")
    return path


def _preserved_inputs(
    previous: Any,
) -> tuple[tuple[Path, ...], Path | None, tuple[Path, ...]]:
    runtime = tuple(
        Path(item["path"])
        for item in previous.manifest.get("runtime_inputs", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    )
    semantic = previous.manifest.get("semantic_input")
    semantic_store = (
        Path(semantic["store"])
        if isinstance(semantic, dict) and isinstance(semantic.get("store"), str)
        else None
    )
    scip = tuple(
        Path(item["manifest_path"])
        for item in previous.manifest.get("scip_inputs", [])
        if isinstance(item, dict) and isinstance(item.get("manifest_path"), str)
    )
    return runtime, semantic_store, scip


def _context_sources(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the exact unique sources actually admitted to ranked context."""

    sources: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in context["entries"]:
        source = entry.get("source")
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            continue
        key = (source["path"], source["identity_sha256"])
        sources[key] = {
            "path": source["path"],
            "identity_sha256": source["identity_sha256"],
            "source_location": source.get("source_location"),
            "location_class": entry["location_class"],
            "ownership": entry["ownership"],
        }
    return [sources[key] for key in sorted(sources)]


def _current_live_source_paths(inventory_store: Path) -> set[str]:
    inventory = current_navigation_run(inventory_store)
    connection = sqlite3.connect(inventory.run_directory / "inventory.sqlite3")
    try:
        return {
            row[0]
            for row in connection.execute(
                """SELECT path FROM files
                   WHERE kind='regular' AND scan_error IS NULL
                   ORDER BY path"""
            )
        }
    finally:
        connection.close()


def _write_private_receipt(
    root: Path, destination: Path, payload: dict[str, Any]
) -> None:
    destination = destination.absolute()
    parent = destination.parent.resolve(strict=False)
    if destination.parent != parent:
        raise ConsultationError("consultation receipt path must be canonical")
    if parent == root or root in parent.parents:
        raise ConsultationError(
            "consultation receipts must remain outside the scanned root"
        )
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = parent.lstat()
    if parent.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise ConsultationError("consultation receipt parent must be a real directory")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise ConsultationError(
            "consultation receipt parent must be current-UID mode 0700"
        )
    descriptor, temporary = tempfile.mkstemp(prefix=".consultation-", dir=parent)
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        raw = canonical_bytes(payload)
        remaining = memoryview(raw)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise ConsultationError("consultation receipt write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary_path, destination, follow_symlinks=False)
        except FileExistsError as exc:
            raise ConsultationError("consultation receipt already exists") from exc
        temporary_path.unlink()
        parent_descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_path.exists():
            temporary_path.unlink()


def consult_before_decision(
    root: Path,
    inventory_store: Path,
    mapper_store: Path,
    *,
    task_id: str,
    task_class: str,
    terms: Sequence[str],
    receipt_path: Path,
    relevant_paths: Sequence[str] = (),
    exhaustive: bool = False,
) -> dict[str, Any]:
    """Compile first, verify consulted sources, and emit a bounded receipt."""

    if not task_id or "\x00" in task_id:
        raise ConsultationError("task_id must be non-empty")
    if task_class not in TASK_DOSSIERS:
        raise ConsultationError("unsupported architecture consultation class")
    if not terms or any(not term or "\x00" in term for term in terms):
        raise ConsultationError("at least one non-empty consultation term is required")
    root = root.resolve(strict=True)
    previous_mapper = current_mapper_run(mapper_store)
    live_source_paths = _current_live_source_paths(inventory_store)
    initial = build_context_projection(
        mapper_store,
        TASK_DOSSIERS[task_class],
        tuple(terms),
        token_budget=CONSULTATION_CONTEXT_BUDGET,
        allowed_source_paths=live_source_paths,
    )
    selected = {_safe_relative(path) for path in relevant_paths}
    selected.update(
        _safe_relative(item["path"])
        for item in _context_sources(initial)
        if isinstance(item.get("path"), str)
    )
    if not selected and not exhaustive:
        raise ConsultationError(
            "bounded consultation found no relevant paths; provide --path or use --exhaustive"
        )

    runtime_registries, semantic_store, scip_manifests = _preserved_inputs(
        previous_mapper
    )
    if exhaustive:
        inventory = refresh_navigation_inventory(root, inventory_store)
    else:
        inventory = refresh_navigation_inventory_delta(
            root,
            inventory_store,
            include_paths=tuple(sorted(selected)),
        )
    mapper_reused_for_verified_paths = bool(
        not exhaustive
        and inventory.selected_paths_unchanged
        and inventory.verified_live_paths
    )
    mapper = (
        previous_mapper
        if mapper_reused_for_verified_paths
        else refresh_mapper(
            inventory_store,
            mapper_store,
            runtime_registries=runtime_registries,
            semantic_store=semantic_store,
            scip_manifests=scip_manifests,
        )
    )
    live_source_paths = _current_live_source_paths(inventory_store)
    context = build_context_projection(
        mapper_store,
        TASK_DOSSIERS[task_class],
        tuple(terms),
        token_budget=CONSULTATION_CONTEXT_BUDGET,
        allowed_source_paths=live_source_paths,
    )

    initial_sources = {item["path"]: item for item in _context_sources(initial)}
    final_sources = {item["path"]: item for item in _context_sources(context)}
    consulted_paths = sorted(selected | set(final_sources))
    verified_sources: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for path in consulted_paths:
        source = final_sources.get(path) or initial_sources.get(path)
        located = locate_navigation_inventory(inventory_store, path, limit=500)
        exact = next(
            (item for item in located["results"] if item["path"] == path), None
        )
        matches = bool(
            exact is not None and exact["source"]["live_matches_inventory"] is True
        )
        verified_sources.append(
            {
                "path": path,
                "inventory_live_match": matches,
                "source_identity_sha256": (
                    source["identity_sha256"]
                    if source is not None
                    else exact["source"]["inventory_sha256"]
                    if exact is not None
                    else None
                ),
                "source_location": (
                    source.get("source_location") if source is not None else None
                ),
                "location_class": (
                    source["location_class"]
                    if source is not None
                    else "EXPLICIT_RELEVANT_PATH"
                ),
                "selection_basis": (
                    "RANKED_CONTEXT"
                    if path in initial_sources or path in final_sources
                    else "EXPLICIT_RELEVANT_PATH"
                ),
            }
        )
        if not matches:
            failures.append(
                {"path": path, "reason": "consulted-source-does-not-match-live-file"}
            )

    refreshed = (
        set(inventory.verified_live_paths)
        if inventory.reused_current
        else set(inventory.manifest["scan"].get("explicit_paths", []))
    )
    consulted = {item["path"] for item in verified_sources}
    unrefreshed_consulted = sorted(consulted - refreshed) if not exhaustive else []
    if unrefreshed_consulted:
        failures.extend(
            {"path": path, "reason": "consulted-source-not-in-scoped-refresh"}
            for path in unrefreshed_consulted
        )
    bounded_ready = bool(verified_sources) and not failures
    exhaustive_ready = bool(
        exhaustive
        and bounded_ready
        and inventory.manifest["status"] == "CURRENT"
        and mapper.manifest["status"] == "CURRENT"
        and context["completeness"] == "COVERED_WITHIN_DECLARED_MAP_SCOPE"
    )
    receipt = seal_document(
        {
            "schema": CONSULTATION_SCHEMA,
            "status": "READY_FOR_BOUNDED_DECISION" if bounded_ready else "PARTIAL",
            "authority": "non-authoritative-codebase-navigation-consultation",
            "authority_granted": False,
            "task": {
                "id": task_id,
                "class": task_class,
                "terms": list(terms),
                "exhaustive": exhaustive,
            },
            "compiled_at": _utc_now(),
            "refresh": {
                "mode": "FULL_RECONCILIATION" if exhaustive else "RELEVANT_PATH_DELTA",
                "inventory_status": inventory.manifest["status"],
                "inventory_scope": inventory.manifest["scan"]["scope"],
                "inventory_run_id": inventory.manifest["run_id"],
                "inventory_receipt_sha256": inventory.manifest["receipt_sha256"],
                "inventory_reused_current": inventory.reused_current,
                "verified_reused_paths": list(inventory.verified_live_paths),
                "mapper_status": mapper.manifest["status"],
                "mapper_run_id": mapper.manifest["run_id"],
                "mapper_receipt_sha256": mapper.manifest["receipt_sha256"],
                "mapper_inventory_run_id": mapper.manifest["inventory"]["run_id"],
                "mapper_reused_for_verified_paths": mapper_reused_for_verified_paths,
                "relevant_paths": sorted(selected),
                "uncovered_git_visible_paths": inventory.manifest["scan"].get(
                    "unrefreshed_git_visible_paths", []
                ),
                "unverified_surfaces": inventory.manifest["scan"].get(
                    "unverified_surfaces", []
                ),
            },
            "retrieval": {
                "mode": "RANKED_CONTEXT",
                "token_budget": CONSULTATION_CONTEXT_BUDGET,
                "entry_count": context["entry_count"],
                "consulted_source_count": len(verified_sources),
            },
            "ranked_context": context,
            "consulted_sources": verified_sources,
            "failures": failures,
            "claims": {
                "bounded_architectural_decision_ready": bounded_ready,
                "whole_folder_current": exhaustive_ready,
                "complete_inventory_allowed": exhaustive_ready,
                "current_architecture_allowed": exhaustive_ready,
                "no_feature_loss_allowed": exhaustive_ready,
                "canonical_owner_asserted": False,
                "execution_authority_granted": False,
            },
        }
    )
    _write_private_receipt(root, receipt_path, receipt)
    return receipt
