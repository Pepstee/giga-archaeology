"""Evidence-derived implementation maturity scorecard.

Scores describe roadmap completion, not intelligence, product quality or forecast accuracy.
They exist to prevent prose status from drifting away from observable artefacts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .health import snapshot as health_snapshot
from .integrity import verify_hash_baseline
from .store import DEFAULT_DATABASE, TwinStore


def _phase(
    phase: str,
    name: str,
    score: float,
    status: str,
    evidence: list[str],
    missing: list[str],
) -> dict[str, Any]:
    return {
        "phase": phase,
        "name": name,
        "completion": score,
        "status": status,
        "evidence": evidence,
        "missing_for_gate": missing,
    }


def scorecard(giga_root: Path, database: Path = DEFAULT_DATABASE) -> dict[str, Any]:
    giga_root = giga_root.resolve()
    health = health_snapshot(giga_root, database)
    integrity = verify_hash_baseline(
        giga_root, giga_root / "architecture" / "EXPORT_IMMUTABILITY_BASELINE.sha256"
    )
    architecture_files = [
        giga_root / "architecture" / name
        for name in (
            "01_LIGHT_MAP.md",
            "02_MEDIUM_MAP.md",
            "03_DEEP_MAP.md",
            "04_VIRTUAL_TWIN_TARGET.md",
            "05_TRANSITION_ROADMAP.md",
        )
    ]
    secure_modes = all(
        health["permissions"].get(key) in {"0o600", "0o700"}
        for key in ("jarvis_dir", "config", "state", "offset", "twin_dir", "twin_database")
        if health["permissions"].get(key) is not None
    )
    trust_files = all(
        (giga_root / "twin_core" / name).exists()
        for name in ("store.py", "integrity.py", "memory_validation.py", "health.py")
    )
    memory_ok = bool(health["memory"]["ok"])
    twin_counts = health["twin_store"]
    artifact_audit = TwinStore(database).audit_artifacts(giga_root)

    phases = [
        _phase(
            "P0",
            "Evidence and scope protection",
            1.0 if integrity["ok"] and all(path.exists() for path in architecture_files) else 0.5,
            "passed" if integrity["ok"] and all(path.exists() for path in architecture_files) else "in_progress",
            ["immutable export baseline verifies", "light/medium/deep maps and target/roadmap exist"],
            [] if integrity["ok"] else ["restore export integrity before any promotion"],
        ),
        _phase(
            "P1",
            "Trust kernel",
            1.0 if trust_files and memory_ok and secure_modes and artifact_audit["ok"] else 0.6,
            "passed" if trust_files and memory_ok and secure_modes and artifact_audit["ok"] else "in_progress",
            [
                "SQLite event/attempt/receipt/goal/decision schemas",
                "deterministic memory validator",
                "machine-derived health and maturity commands",
                "owner-only runtime state",
            ],
            [] if trust_files and memory_ok and secure_modes and artifact_audit["ok"] else ["resolve failed trust-kernel or lineage checks"],
        ),
        _phase(
            "P2",
            "Transactional capture and backfill",
            0.7,
            "in_progress",
            [
                "idempotent Telegram capture, processing attempts and receipts are deployed",
                "model emits strict no-tool proposals into a deterministic stage/validate/commit path",
                "atomic offsets, replay receipts and provider failure recovery are tested",
                "Claude-to-Codex isolated fallback smoke-tested live",
                "daily batches are fresh-first, character-bounded, run-addressed and receipted before state advances",
            ],
            [
                "observe and inspect the first natural daily run through the new boundary",
                "kill-process fault injection at every live transition",
            ],
        ),
        _phase(
            "P3",
            "Memory accuracy",
            0.25,
            "in_progress",
            [
                "42-entry memory validates with index/provenance/sensitivity checks",
                "bounded deterministic lexical/reminder/one-hop context compiler is live for Telegram",
            ],
            ["typed temporal/epistemic metadata", "retrieval evaluation and richer routing", "locked recall evaluation"],
        ),
        _phase(
            "P4",
            "Goal, preference and decision OS",
            0.2 if twin_counts["goals"] and twin_counts["decisions"] else 0.1,
            "in_progress",
            ["goal and decision schemas", "operator-ratified virtual-twin goal seeded"],
            ["preference ledger", "recommendation/outcome lifecycle", "shadow-decision evaluation"],
        ),
        _phase(
            "P5",
            "External state and daily counsel",
            0.05,
            "not_started",
            ["Telegram reminder surface exists outside the new kernel"],
            ["read-only calendar/email adapters", "shared morning packet", "injection tests"],
        ),
        _phase(
            "P6",
            "Speaking style",
            0.05,
            "gated",
            ["prepared conversation datasets exist"],
            ["operator authorisation", "mode map", "blind baseline and leakage evaluation"],
        ),
        _phase(
            "P7",
            "Thinking style and self-scrutiny",
            0.1,
            "in_progress",
            [f"prediction ledger contains {health['prediction']['predictions']} forecasts"],
            ["outcome adjudications", "held-out decision suite", "hypothesis correction lifecycle"],
        ),
        _phase(
            "P8",
            "Bounded agency and domain adapters",
            0.0,
            "not_started",
            [],
            ["authority-policy engine", "sandboxed capability adapters", "rollback and extinction drills"],
        ),
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meaning": "roadmap completion only; not a measure of twin intelligence or accuracy",
        "overall_completion": round(sum(item["completion"] for item in phases) / len(phases), 3),
        "current_promotion_frontier": "P2 transactional capture",
        "exports": integrity,
        "runtime": {
            "memory_ok": memory_ok,
            "jarvis_running": health["processes"]["jarvis"],
            "prediction": health["prediction"],
            "twin_store": twin_counts,
            "derived_artifacts": artifact_audit,
        },
        "phases": phases,
    }
