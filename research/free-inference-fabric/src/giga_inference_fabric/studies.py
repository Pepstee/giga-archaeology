from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path

from .models import CostTier


@dataclass(frozen=True)
class StudyArm:
    id: str
    description: str
    cost_tier: CostTier
    candidates_per_round: int
    critics_per_candidate: int
    min_distinct_models: int
    max_rounds: int
    use_experience: bool
    repeats: int


@dataclass(frozen=True)
class StudyDefinition:
    id: str
    question: str
    benchmark_id: str
    arms: tuple[StudyArm, ...]


def study_catalogue_hash(path: Path) -> str:
    identity_path = path.with_name(path.name + ".sha256")
    if not identity_path.is_file():
        raise ValueError(f"study catalogue identity is absent: {identity_path}")
    expected = identity_path.read_text(encoding="utf-8").strip()
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        raise ValueError("study catalogue identity is invalid")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("study catalogue drift detected")
    return actual


def load_studies(path: Path) -> list[StudyDefinition]:
    study_catalogue_hash(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if set(payload) != {"schema", "studies"} or payload["schema"] != "giga.study-catalogue.v1":
        raise ValueError("invalid study catalogue")
    if not isinstance(payload["studies"], list):
        raise ValueError("study catalogue studies must be an array")
    studies = []
    study_ids = set()
    for raw_study in payload["studies"]:
        if set(raw_study) != {"id", "question", "benchmark_id", "arms"}:
            raise ValueError("invalid study definition fields")
        if raw_study["id"] in study_ids:
            raise ValueError("duplicate study ID")
        study_ids.add(raw_study["id"])
        arms = []
        arm_ids = set()
        for raw_arm in raw_study["arms"]:
            expected = {
                "id", "description", "cost_tier", "candidates_per_round",
                "critics_per_candidate", "min_distinct_models", "max_rounds",
                "use_experience", "repeats",
            }
            if set(raw_arm) != expected:
                raise ValueError("invalid study arm fields")
            arm = StudyArm(
                id=raw_arm["id"], description=raw_arm["description"],
                cost_tier=CostTier(raw_arm["cost_tier"]),
                candidates_per_round=raw_arm["candidates_per_round"],
                critics_per_candidate=raw_arm["critics_per_candidate"],
                min_distinct_models=raw_arm["min_distinct_models"],
                max_rounds=raw_arm["max_rounds"],
                use_experience=raw_arm["use_experience"], repeats=raw_arm["repeats"],
            )
            if arm.id in arm_ids:
                raise ValueError("duplicate study arm ID")
            arm_ids.add(arm.id)
            if (
                arm.candidates_per_round < 1 or arm.max_rounds < 1 or arm.repeats < 1
                or arm.critics_per_candidate < 0 or arm.min_distinct_models < 1
                or arm.min_distinct_models > arm.candidates_per_round
            ):
                raise ValueError("invalid study arm bounds")
            if arm.critics_per_candidate > 0 and arm.min_distinct_models < 2:
                raise ValueError("critic arm must require cross-model diversity")
            arms.append(arm)
        studies.append(StudyDefinition(
            id=raw_study["id"], question=raw_study["question"],
            benchmark_id=raw_study["benchmark_id"], arms=tuple(arms),
        ))
    return studies


def resolve_study_arm(path: Path, study_id: str, arm_id: str) -> tuple[StudyDefinition, StudyArm]:
    for study in load_studies(path):
        if study.id == study_id:
            for arm in study.arms:
                if arm.id == arm_id:
                    return study, arm
            raise KeyError(f"unknown arm {arm_id} for study {study_id}")
    raise KeyError(f"unknown study {study_id}")
