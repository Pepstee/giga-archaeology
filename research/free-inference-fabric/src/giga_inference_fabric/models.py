from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CostTier(StrEnum):
    LOCAL = "local"
    FREE = "free"
    PAID = "paid"


class PrivacyClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PERSONAL = "personal"
    VAULT = "vault"


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    adapter: str
    cost_tier: CostTier
    context_length: int = 0
    capabilities: frozenset[str] = frozenset({"text"})
    supports_tools: bool = False
    supports_structured_output: bool = False
    zero_data_retention: bool = False
    preview: bool = False
    available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelPolicy:
    allowed_tiers: frozenset[CostTier] = frozenset({CostTier.LOCAL, CostTier.FREE})
    allowed_adapters: frozenset[str] = frozenset({"openrouter", "local"})
    privacy_class: PrivacyClass = PrivacyClass.INTERNAL
    require_zdr: bool = False
    allow_paid_escalation: bool = False
    max_total_cost_usd: float = 0.0

    def allows(self, model: ModelSpec) -> bool:
        if not model.available or model.cost_tier not in self.allowed_tiers:
            return False
        if model.adapter not in self.allowed_adapters:
            return False
        if model.cost_tier == CostTier.PAID and not self.allow_paid_escalation:
            return False
        if self.require_zdr and not model.zero_data_retention:
            return False
        if self.privacy_class == PrivacyClass.VAULT and model.adapter != "local" and not model.zero_data_retention:
            return False
        return True


@dataclass(frozen=True)
class ExperimentRequest:
    objective: str
    prompt: str
    workload: str = "implementation"
    candidates_per_round: int = 3
    critics_per_candidate: int = 2
    min_distinct_models: int = 2
    max_rounds: int = 4
    max_remote_calls: int = 50
    daily_remote_limit: int = 50
    max_output_tokens: int = 4096
    stagnation_rounds: int = 2
    min_score_improvement: float = 0.01
    required_capabilities: frozenset[str] = frozenset({"text"})
    policy: ModelPolicy = field(default_factory=ModelPolicy)
    context: str = ""
    experiment_id: str | None = None
    benchmark_id: str | None = None
    study_id: str | None = None
    study_arm_id: str | None = None
    study_contract_sha256: str | None = None
    repeat_index: int | None = None
    use_experience: bool = True
    source_experiment_id: str | None = None
    source_result_sha256: str | None = None


@dataclass(frozen=True)
class Completion:
    text: str
    model_id: str
    adapter: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    experiment_id: str
    round_number: int
    approach: str
    completion: Completion
    output_hash: str
    requested_model_id: str | None = None


@dataclass(frozen=True)
class GateResult:
    passed: bool
    score: float
    summary: str
    checks: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Critique:
    candidate_id: str
    critic_model_id: str
    text: str
    findings_hash: str


@dataclass(frozen=True)
class ExperimentResult:
    experiment_id: str
    status: str
    best_candidate: Candidate | None
    best_gate: GateResult | None
    rounds: int
    attempts: int
    remote_calls: int
    stop_reason: str
    escalation_packet: dict[str, Any]
