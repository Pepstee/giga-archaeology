from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .models import CostTier, ModelSpec


@dataclass(frozen=True)
class WorkloadProfile:
    id: str
    purpose: str
    prompt: str
    objective_gate: str
    cadence: str
    risk: str


@dataclass(frozen=True)
class HarvestTarget:
    model_id: str
    preview: bool
    experiment_id: str


def load_profiles(path: Path) -> list[WorkloadProfile]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [WorkloadProfile(**item) for item in payload["profiles"]]


def model_window_diff(previous: list[ModelSpec], current: list[ModelSpec]) -> dict[str, list[str]]:
    def ids(rows: list[ModelSpec], *, free: bool = False, preview: bool = False) -> set[str]:
        return {
            row.model_id for row in rows
            if (not free or row.cost_tier == CostTier.FREE)
            and (not preview or (row.cost_tier == CostTier.FREE and row.preview))
        }

    old_free, new_free = ids(previous, free=True), ids(current, free=True)
    old_preview, new_preview = ids(previous, preview=True), ids(current, preview=True)
    return {
        "newly_free": sorted(new_free - old_free),
        "no_longer_free": sorted(old_free - new_free),
        "preview_opened": sorted(new_preview - old_preview),
        "preview_closed": sorted(old_preview - new_preview),
    }


def harvest_experiment_id(
    benchmark_binding: dict, model_id: str, *, max_rounds: int,
) -> str:
    contract = json.dumps({
        "benchmark_binding": benchmark_binding, "model_id": model_id,
        "max_rounds": max_rounds, "use_experience": False,
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "harvest-" + hashlib.sha256(contract.encode("utf-8")).hexdigest()[:24]


def harvest_targets(
    models: list[ModelSpec], benchmark_binding: dict, *, max_rounds: int,
    excluded_model_ids: set[str], claimed_experiment_ids: set[str],
) -> list[HarvestTarget]:
    targets = []
    for model in models:
        if (
            not model.available or model.cost_tier != CostTier.FREE
            or "text" not in model.capabilities or model.model_id in excluded_model_ids
        ):
            continue
        experiment_id = harvest_experiment_id(
            benchmark_binding, model.model_id, max_rounds=max_rounds,
        )
        if experiment_id in claimed_experiment_ids:
            continue
        targets.append(HarvestTarget(model.model_id, model.preview, experiment_id))
    return sorted(targets, key=lambda target: (not target.preview, target.model_id))
