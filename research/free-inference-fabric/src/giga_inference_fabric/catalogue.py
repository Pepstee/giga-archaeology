from __future__ import annotations

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
