"""Evidence-aware measurement of personal sovereignty.

The index measures control over the shape of a life, not human worth, productivity,
happiness, or the twin's maturity. Scores are deterministic transformations of explicit
observations. Missing or weak evidence lowers coverage/reliability instead of being silently
treated as an average answer.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence


INPUT_SCHEMA = "giga.sovereignty-observation.v1"
RESULT_SCHEMA = "giga.sovereignty-result.v1"
MODEL_VERSION = "giga.sovereignty-model.v1.1"
MIN_DIMENSION_COVERAGE = 0.65
MIN_HEADLINE_COVERAGE = 0.75
MIN_MEASURED_RELIABILITY = 0.75
BOTTLENECK_ALLOWANCE = 20.0
MIN_CHOICE_COMPONENT_COVERAGE = 0.65
SAFE_ASSESSMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")

EVIDENCE_QUALITY = {
    "external_receipt": 1.0,
    "operator_log": 0.90,
    "external_observation": 0.90,
    "operator_confirmed": 0.80,
    "derived_observation": 0.70,
    "operator_rating": 0.65,
    "model_inference": 0.35,
}


class SovereigntyError(ValueError):
    """Raised when an assessment cannot be scored honestly."""


@dataclass(frozen=True)
class IndicatorSpec:
    id: str
    label: str
    dimension: str | None
    weight: float
    normalisation: str
    cadence_days: int
    description: str
    low: float = 0.0
    high: float = 100.0


@dataclass(frozen=True)
class DimensionSpec:
    id: str
    label: str
    weight: float
    description: str


DIMENSIONS = (
    DimensionSpec(
        "authorship",
        "Authorship",
        0.22,
        "Important commitments and discretionary time are deliberately chosen or ratified.",
    ),
    DimensionSpec(
        "alignment",
        "Life alignment",
        0.16,
        "Choices and resource allocation match explicitly ratified values rather than an inherited script.",
    ),
    DimensionSpec(
        "optionality",
        "Optionality and exit power",
        0.16,
        "Viable alternatives exist, so consent is meaningful rather than forced by a single path.",
    ),
    DimensionSpec(
        "attention",
        "Attention sovereignty",
        0.14,
        "Time and attention are directed intentionally instead of being captured by feeds, demands, or drift.",
    ),
    DimensionSpec(
        "execution",
        "Agency conversion",
        0.14,
        "Chosen intentions become actions and externally inspectable receipts.",
    ),
    DimensionSpec(
        "independence",
        "Operational independence",
        0.10,
        "Critical income, tools, administration, and capabilities remain portable or substitutable.",
    ),
    DimensionSpec(
        "recovery",
        "Reversibility and recovery",
        0.08,
        "Decisions preserve rollback and disruptions do not permanently take control of the plan.",
    ),
)

AUTHORSHIP_COMPONENTS = {
    "declared_endorsement": {
        "label": "Declared endorsement",
        "weight": 0.25,
        "indicators": {
            "chosen_major_commitments": 0.60,
            "intentional_discretionary_time": 0.40,
        },
    },
    "practical_voluntariness": {
        "label": "Practical voluntariness",
        "weight": 0.25,
        "indicators": {
            "refusal_power": 0.35,
            "credible_alternative_coverage": 0.35,
            "affordable_refusal_coverage": 0.30,
        },
    },
    "counterfactual_stability": {
        "label": "Counterfactual stability",
        "weight": 0.20,
        "indicators": {
            "counterfactual_endorsement_rate": 0.70,
            "cross_environment_stability_rate": 0.30,
        },
    },
    "reflective_stability": {
        "label": "Reflective stability",
        "weight": 0.15,
        "indicators": {
            "delayed_reendorsement_rate": 0.65,
            "preference_origin_trace_coverage": 0.35,
        },
    },
    "contradiction_free": {
        "label": "Contradiction-free behavior",
        "weight": 0.15,
        "indicators": {
            "behavioral_contradiction_rate": 1.0,
        },
    },
}

INDICATORS = (
    # Authorship
    IndicatorSpec(
        "chosen_major_commitments",
        "Chosen major commitments",
        "authorship",
        0.15,
        "ratio",
        30,
        "Share of major active commitments that were explicitly chosen or later ratified.",
    ),
    IndicatorSpec(
        "intentional_discretionary_time",
        "Intentional discretionary time",
        "authorship",
        0.10,
        "ratio",
        7,
        "Share of discretionary hours used in ways selected in advance or consciously endorsed afterwards.",
    ),
    IndicatorSpec(
        "refusal_power",
        "Practical refusal power",
        "authorship",
        0.0875,
        "score",
        30,
        "Ability to decline an unwanted demand without unacceptable damage; 0 means no viable refusal, 100 means genuine refusal power.",
    ),
    IndicatorSpec(
        "credible_alternative_coverage",
        "Credible alternative coverage",
        "authorship",
        0.0875,
        "ratio",
        30,
        "Share of major commitments for which at least one concrete, executable alternative was identified rather than merely imagined.",
    ),
    IndicatorSpec(
        "affordable_refusal_coverage",
        "Affordable refusal coverage",
        "authorship",
        0.075,
        "ratio",
        30,
        "Share of major commitments that could be rejected or renegotiated without unacceptable material, legal, safety, or dependency damage.",
    ),
    IndicatorSpec(
        "counterfactual_endorsement_rate",
        "Counterfactual endorsement",
        "authorship",
        0.14,
        "ratio",
        30,
        "Share of major commitments still endorsed after explicitly neutralising named removable pressures in a written counterfactual.",
    ),
    IndicatorSpec(
        "cross_environment_stability_rate",
        "Cross-environment stability",
        "authorship",
        0.06,
        "ratio",
        90,
        "Share of tested preferences that remained endorsed across meaningful changes in place, money, role, audience, or option availability.",
    ),
    IndicatorSpec(
        "delayed_reendorsement_rate",
        "Delayed re-endorsement",
        "authorship",
        0.0975,
        "ratio",
        30,
        "Share of eligible major commitments re-endorsed after at least 30 days and a genuine opportunity to reconsider.",
    ),
    IndicatorSpec(
        "preference_origin_trace_coverage",
        "Preference-origin trace coverage",
        "authorship",
        0.0525,
        "ratio",
        90,
        "Share of major commitments with a recorded origin, surrounding incentives or pressures, strongest alternative, and reason for rejection.",
    ),
    IndicatorSpec(
        "behavioral_contradiction_rate",
        "Behavioral contradiction rate",
        "authorship",
        0.15,
        "inverse_ratio",
        30,
        "Share of declared choices with material contrary evidence such as repeated avoidance, escape planning, recurring resentment, or inconsistent behavior.",
    ),
    # Alignment
    IndicatorSpec(
        "time_on_ratified_values",
        "Time on ratified values",
        "alignment",
        0.40,
        "ratio",
        7,
        "Share of allocatable time serving goals or values the operator has explicitly ratified.",
    ),
    IndicatorSpec(
        "value_consistent_major_decisions",
        "Value-consistent major decisions",
        "alignment",
        0.35,
        "ratio",
        30,
        "Share of major decisions whose recorded rationale is consistent with ratified values and standing decisions.",
    ),
    IndicatorSpec(
        "identity_congruence",
        "Identity congruence",
        "alignment",
        0.25,
        "score",
        30,
        "Reflective rating: how much the present life feels authored and recognisably one's own.",
    ),
    # Optionality
    IndicatorSpec(
        "financial_runway_months",
        "Financial runway",
        "optionality",
        0.30,
        "linear",
        30,
        "Months of essential expenses covered without new income; 12 months reaches the v1 ceiling.",
        high=12.0,
    ),
    IndicatorSpec(
        "viable_exit_paths",
        "Viable exit paths",
        "optionality",
        0.30,
        "linear",
        30,
        "Number of genuinely executable alternatives to the current work/living path; three reaches the v1 ceiling.",
        high=3.0,
    ),
    IndicatorSpec(
        "critical_dependency_concentration",
        "Critical dependency concentration",
        "optionality",
        0.20,
        "inverse_ratio",
        30,
        "Largest share controlled by one replaceable-but-critical provider, client, gatekeeper, or route.",
    ),
    IndicatorSpec(
        "geographic_legal_mobility",
        "Geographic and legal mobility",
        "optionality",
        0.20,
        "score",
        90,
        "Practical ability to live, work, travel, and maintain identity documents across intended locations.",
    ),
    # Attention
    IndicatorSpec(
        "intentional_attention_share",
        "Intentional attention",
        "attention",
        0.45,
        "ratio",
        7,
        "Share of tracked attention spent on deliberately selected activity.",
    ),
    IndicatorSpec(
        "compulsive_feed_share",
        "Compulsive feed capture",
        "attention",
        0.30,
        "inverse_ratio",
        7,
        "Share of discretionary attention lost to non-purposeful feeds or equivalent capture.",
    ),
    IndicatorSpec(
        "protected_unstructured_time",
        "Protected unstructured time",
        "attention",
        0.25,
        "ratio",
        7,
        "Share of the intended rest/play/exploration allowance that remained genuinely uncolonised.",
    ),
    # Execution
    IndicatorSpec(
        "chosen_commitment_receipt_rate",
        "Chosen commitment receipt rate",
        "execution",
        0.45,
        "ratio",
        30,
        "Share of due chosen commitments completed with observable evidence.",
    ),
    IndicatorSpec(
        "plan_follow_through_rate",
        "Plan follow-through",
        "execution",
        0.35,
        "ratio",
        7,
        "Share of ready, unblocked planned actions completed or explicitly renegotiated.",
    ),
    IndicatorSpec(
        "decision_to_action_days",
        "Decision-to-action latency",
        "execution",
        0.20,
        "inverse_linear",
        30,
        "Median days from a decided, ready action to first execution; 30 days reaches the v1 floor.",
        high=30.0,
    ),
    # Independence
    IndicatorSpec(
        "portable_income_share",
        "Portable income share",
        "independence",
        0.35,
        "ratio",
        90,
        "Share of income that is location-portable or not controlled by a single arbitrary gatekeeper.",
    ),
    IndicatorSpec(
        "substitutable_critical_tools",
        "Substitutable critical tools",
        "independence",
        0.35,
        "ratio",
        90,
        "Share of critical tools/providers with a tested substitute, export, or restore path.",
    ),
    IndicatorSpec(
        "administrative_control_coverage",
        "Administrative control coverage",
        "independence",
        0.30,
        "ratio",
        30,
        "Share of currently material documents, appointments, renewals, and obligations under an explicit plan.",
    ),
    # Recovery
    IndicatorSpec(
        "reversible_major_decisions",
        "Reversible major decisions",
        "recovery",
        0.35,
        "ratio",
        90,
        "Share of recent major decisions with a viable rollback, trial period, or bounded downside.",
    ),
    IndicatorSpec(
        "disruption_recovery_days",
        "Disruption recovery time",
        "recovery",
        0.35,
        "inverse_linear",
        30,
        "Median days required to resume a chosen plan after a material disruption; 14 days reaches the v1 floor.",
        high=14.0,
    ),
    IndicatorSpec(
        "slack_buffer_days",
        "Operational slack",
        "recovery",
        0.30,
        "linear",
        30,
        "Days of schedule/operational buffer before ordinary disruption forces abandonment; 30 reaches the v1 ceiling.",
        high=30.0,
    ),
    # Guardrails: deliberately outside the headline.
    IndicatorSpec(
        "create_commitments_met",
        "Create",
        None,
        1.0,
        "ratio",
        7,
        "Share of the week's deliberately chosen external-value commitments met.",
    ),
    IndicatorSpec(
        "relate_commitments_met",
        "Relate",
        None,
        1.0,
        "ratio",
        7,
        "Share of deliberately chosen relationship-care commitments met; never a rating of another person's value or affection.",
    ),
    IndicatorSpec(
        "inhabit_commitments_met",
        "Inhabit",
        None,
        1.0,
        "ratio",
        7,
        "Share of deliberately chosen body, place, beauty, play, language, and rest commitments met.",
    ),
    IndicatorSpec(
        "external_consequence_share",
        "Reality contact",
        None,
        1.0,
        "ratio",
        30,
        "Share of completed project work that produced an external user, client, employer, learner, publication, or independently verified consequence.",
    ),
    IndicatorSpec(
        "life_satisfaction",
        "Life satisfaction",
        None,
        1.0,
        "score",
        7,
        "Reflective 0–100 life evaluation, tracked separately from control.",
    ),
    IndicatorSpec(
        "life_worthwhile",
        "Life feels worthwhile",
        None,
        1.0,
        "score",
        7,
        "Reflective 0–100 rating of meaning and worthwhileness.",
    ),
    IndicatorSpec(
        "affect_balance",
        "Affect balance",
        None,
        1.0,
        "score",
        7,
        "Reflective 0–100 balance of positive versus negative lived affect for the period.",
    ),
    IndicatorSpec(
        "capacity_support_days",
        "Vital capacity",
        None,
        1.0,
        "ratio",
        7,
        "Share of days meeting the operator's own minimum sleep, movement, nutrition, and recovery protocol.",
    ),
)

INDICATOR_BY_ID = {item.id: item for item in INDICATORS}
DIMENSION_BY_ID = {item.id: item for item in DIMENSIONS}

GUARDRAILS = {
    "create_relate_inhabit": (
        "Create–Relate–Inhabit floor",
        ("create_commitments_met", "relate_commitments_met", "inhabit_commitments_met"),
        "minimum",
    ),
    "reality_contact": (
        "Reality Contact Index",
        ("external_consequence_share",),
        "mean",
    ),
    "lived_experience": (
        "Lived Experience Index",
        ("life_satisfaction", "life_worthwhile", "affect_balance"),
        "mean",
    ),
    "vital_capacity": (
        "Vital Capacity Index",
        ("capacity_support_days",),
        "mean",
    ),
}


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SovereigntyError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise SovereigntyError(f"{field} must be a finite number")
    return result


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SovereigntyError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SovereigntyError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SovereigntyError(f"{field} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise SovereigntyError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SovereigntyError(f"{field} must be an ISO date") from exc


def _measurement_score(spec: IndicatorSpec, measurement: Any) -> float:
    if not isinstance(measurement, dict):
        raise SovereigntyError(f"{spec.id}.measurement must be an object")
    if spec.normalisation in {"ratio", "inverse_ratio"}:
        if set(measurement) != {"numerator", "denominator"}:
            raise SovereigntyError(
                f"{spec.id}.measurement must contain numerator and denominator"
            )
        numerator = _number(measurement["numerator"], f"{spec.id}.numerator")
        denominator = _number(measurement["denominator"], f"{spec.id}.denominator")
        if denominator <= 0 or numerator < 0 or numerator > denominator:
            raise SovereigntyError(
                f"{spec.id} requires 0 <= numerator <= denominator and denominator > 0"
            )
        value = numerator / denominator
        if spec.normalisation == "inverse_ratio":
            value = 1.0 - value
        return value * 100.0
    if set(measurement) != {"value"}:
        raise SovereigntyError(f"{spec.id}.measurement must contain value")
    value = _number(measurement["value"], f"{spec.id}.value")
    if spec.normalisation == "score":
        if not 0 <= value <= 100:
            raise SovereigntyError(f"{spec.id}.value must be between 0 and 100")
        return value
    if not spec.low <= value <= spec.high:
        raise SovereigntyError(
            f"{spec.id}.value must be between {spec.low:g} and {spec.high:g}"
        )
    fraction = (value - spec.low) / (spec.high - spec.low)
    if spec.normalisation == "inverse_linear":
        fraction = 1.0 - fraction
    return fraction * 100.0


def _freshness(observed_at: datetime, as_of: datetime, cadence_days: int) -> float:
    age_days = (as_of - observed_at).total_seconds() / 86_400
    if age_days < 0:
        raise SovereigntyError("observation is dated after assessment as_of")
    if age_days <= cadence_days:
        return 1.0
    return max(0.0, 1.0 - ((age_days - cadence_days) / cadence_days))


def _validate_assessment(assessment: Mapping[str, Any]) -> tuple[datetime, dict[str, dict[str, Any]]]:
    required = {
        "schema_version",
        "assessment_id",
        "period_start",
        "period_end",
        "as_of",
        "observations",
    }
    optional = {"notes"}
    unknown = set(assessment) - required - optional
    missing = required - set(assessment)
    if missing or unknown:
        raise SovereigntyError(
            f"invalid assessment fields; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if assessment["schema_version"] != INPUT_SCHEMA:
        raise SovereigntyError(f"schema_version must be {INPUT_SCHEMA}")
    assessment_id = assessment["assessment_id"]
    if not isinstance(assessment_id, str) or not SAFE_ASSESSMENT_ID.fullmatch(
        assessment_id
    ):
        raise SovereigntyError(
            "assessment_id must start with an alphanumeric character and contain "
            "only letters, numbers, periods, underscores, or hyphens (max 120)"
        )
    start = _date(assessment["period_start"], "period_start")
    end = _date(assessment["period_end"], "period_end")
    as_of = _timestamp(assessment["as_of"], "as_of")
    if start > end or end > as_of.date():
        raise SovereigntyError("period must be ordered and cannot end after as_of")
    observations = assessment["observations"]
    if not isinstance(observations, list):
        raise SovereigntyError("observations must be an array")

    by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(observations):
        if not isinstance(raw, dict):
            raise SovereigntyError(f"observations[{index}] must be an object")
        required_observation = {
            "indicator",
            "observed_at",
            "evidence_class",
            "confidence",
            "source",
            "measurement",
        }
        optional_observation = {"note"}
        missing_fields = required_observation - set(raw)
        unknown_fields = set(raw) - required_observation - optional_observation
        if missing_fields or unknown_fields:
            raise SovereigntyError(
                f"invalid observation fields at index {index}; "
                f"missing={sorted(missing_fields)}, unknown={sorted(unknown_fields)}"
            )
        indicator_id = raw["indicator"]
        if indicator_id not in INDICATOR_BY_ID:
            raise SovereigntyError(f"unknown indicator: {indicator_id!r}")
        if indicator_id in by_id:
            raise SovereigntyError(f"duplicate indicator: {indicator_id}")
        evidence_class = raw["evidence_class"]
        if evidence_class not in EVIDENCE_QUALITY:
            raise SovereigntyError(
                f"{indicator_id}.evidence_class must be one of {sorted(EVIDENCE_QUALITY)}"
            )
        confidence = _number(raw["confidence"], f"{indicator_id}.confidence")
        if not 0 <= confidence <= 1:
            raise SovereigntyError(f"{indicator_id}.confidence must be between 0 and 1")
        source = raw["source"]
        if not isinstance(source, str) or not source.strip() or len(source) > 1_000:
            raise SovereigntyError(f"{indicator_id}.source must be 1–1000 characters")
        observed_at = _timestamp(raw["observed_at"], f"{indicator_id}.observed_at")
        spec = INDICATOR_BY_ID[indicator_id]
        score = _measurement_score(spec, raw["measurement"])
        freshness = _freshness(observed_at, as_of, spec.cadence_days)
        reliability = EVIDENCE_QUALITY[evidence_class] * confidence * freshness
        by_id[indicator_id] = {
            "indicator": indicator_id,
            "label": spec.label,
            "score": round(score, 2),
            "evidence_class": evidence_class,
            "confidence": confidence,
            "freshness": round(freshness, 3),
            "reliability": round(reliability, 3),
            "observed_at": observed_at.isoformat(),
            "source": source.strip(),
            "note": raw.get("note"),
        }
    return as_of, by_id


def _choice_component_result(
    component_id: str,
    observations: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    definition = AUTHORSHIP_COMPONENTS[component_id]
    indicator_weights = definition["indicators"]
    observed = [
        (indicator_id, weight, observations[indicator_id])
        for indicator_id, weight in indicator_weights.items()
        if indicator_id in observations
    ]
    coverage = sum(weight for _, weight, _ in observed)
    score = None
    reliability = 0.0
    if observed:
        score = sum(weight * value["score"] for _, weight, value in observed) / coverage
        reliability = (
            sum(weight * value["reliability"] for _, weight, value in observed) / coverage
        )
    publishable = coverage + 1e-9 >= MIN_CHOICE_COMPONENT_COVERAGE
    return {
        "id": component_id,
        "label": definition["label"],
        "weight": definition["weight"],
        "score": round(score, 2) if score is not None and publishable else None,
        "coverage": round(coverage, 3),
        "evidence_reliability": round(reliability, 3),
        "state": "observed" if publishable else "insufficient_evidence",
        "indicators": [value for _, _, value in observed],
        "missing_indicators": [
            indicator_id
            for indicator_id in indicator_weights
            if indicator_id not in observations
        ],
    }


def _authorship_result(
    dimension: DimensionSpec,
    observations: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    components = [
        _choice_component_result(component_id, observations)
        for component_id in AUTHORSHIP_COMPONENTS
    ]
    coverage = sum(item["weight"] * item["coverage"] for item in components)
    reliability = sum(
        item["weight"] * item["evidence_reliability"] for item in components
    )
    publishable = (
        coverage + 1e-9 >= MIN_DIMENSION_COVERAGE
        and all(item["score"] is not None for item in components)
    )
    score = None
    raw_score = None
    component_cap_applied = False
    if publishable:
        scored = [(float(item["score"]), item["weight"]) for item in components]
        raw_score = _weighted_geometric(scored)
        weakest = min(value for value, _ in scored)
        score = min(raw_score, weakest + BOTTLENECK_ALLOWANCE)
        component_cap_applied = score + 0.005 < raw_score

    specs = [item for item in INDICATORS if item.dimension == dimension.id]
    return {
        "id": dimension.id,
        "label": dimension.label,
        "weight": dimension.weight,
        "description": dimension.description,
        "score": round(score, 2) if score is not None else None,
        "raw_score": round(raw_score, 2) if raw_score is not None else None,
        "coverage": round(coverage, 3),
        "evidence_reliability": round(reliability, 3),
        "state": "observed" if publishable else "insufficient_evidence",
        "aggregation": "bottlenecked weighted geometric mean",
        "component_cap_applied": component_cap_applied,
        "components": components,
        "indicators": [
            observations[item.id] for item in specs if item.id in observations
        ],
        "missing_indicators": [
            item.id for item in specs if item.id not in observations
        ],
    }


def _dimension_result(
    dimension: DimensionSpec,
    observations: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    if dimension.id == "authorship":
        return _authorship_result(dimension, observations)
    specs = [item for item in INDICATORS if item.dimension == dimension.id]
    observed = [(item, observations[item.id]) for item in specs if item.id in observations]
    coverage = sum(item.weight for item, _ in observed)
    score = None
    reliability = 0.0
    if observed:
        weighted_score = sum(item.weight * value["score"] for item, value in observed)
        score = weighted_score / coverage
        reliability = (
            sum(item.weight * value["reliability"] for item, value in observed) / coverage
        )
    publishable = coverage + 1e-9 >= MIN_DIMENSION_COVERAGE
    return {
        "id": dimension.id,
        "label": dimension.label,
        "weight": dimension.weight,
        "description": dimension.description,
        "score": round(score, 2) if score is not None and publishable else None,
        "coverage": round(coverage, 3),
        "evidence_reliability": round(reliability, 3),
        "state": "observed" if publishable else "insufficient_evidence",
        "indicators": [value for _, value in observed],
        "missing_indicators": [item.id for item in specs if item.id not in observations],
    }


def _weighted_geometric(values: Sequence[tuple[float, float]]) -> float:
    return math.exp(sum(weight * math.log(max(score, 0.01) / 100.0) for score, weight in values)) * 100.0


def _effective_voluntariness(components: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    component_ids = (
        "practical_voluntariness",
        "counterfactual_stability",
        "reflective_stability",
        "contradiction_free",
    )
    total_weight = sum(
        float(AUTHORSHIP_COMPONENTS[component_id]["weight"])
        for component_id in component_ids
    )
    weighted = [
        (
            components[component_id],
            float(AUTHORSHIP_COMPONENTS[component_id]["weight"]) / total_weight,
        )
        for component_id in component_ids
    ]
    coverage = sum(weight * item["coverage"] for item, weight in weighted)
    reliability = sum(
        weight * item["evidence_reliability"] for item, weight in weighted
    )
    publishable = all(item["score"] is not None for item, _ in weighted)
    score = None
    raw_score = None
    cap_applied = False
    if publishable:
        scored = [(float(item["score"]), weight) for item, weight in weighted]
        raw_score = _weighted_geometric(scored)
        weakest = min(value for value, _ in scored)
        score = min(raw_score, weakest + BOTTLENECK_ALLOWANCE)
        cap_applied = score + 0.005 < raw_score
    state = "insufficient_evidence"
    if publishable:
        state = (
            "observed"
            if reliability >= MIN_MEASURED_RELIABILITY
            else "provisional"
        )
    return {
        "score": round(score, 2) if score is not None else None,
        "raw_score": round(raw_score, 2) if raw_score is not None else None,
        "coverage": round(coverage, 3),
        "evidence_reliability": round(reliability, 3),
        "state": state,
        "component_cap_applied": cap_applied,
    }


def _risk_band(score: float) -> str:
    if score < 15:
        return "low"
    if score < 30:
        return "watch"
    if score < 50:
        return "elevated"
    return "high"


def _choice_state(declared: float, voluntariness: float) -> str:
    declared_high = declared >= 60
    voluntariness_high = voluntariness >= 60
    if declared_high and voluntariness_high:
        return "authored_choice_supported"
    if declared_high:
        return "endorsed_necessity_possible"
    if voluntariness_high:
        return "conflicted_or_unclaimed_choice"
    return "constraint_or_captivity_possible"


def _choice_authenticity(authorship: Mapping[str, Any]) -> dict[str, Any]:
    components = {item["id"]: item for item in authorship.get("components", [])}
    required = set(AUTHORSHIP_COMPONENTS)
    if set(components) != required:
        return {
            "state": "insufficient_evidence",
            "effective_voluntariness": None,
            "self_deception_risk": None,
            "risk_band": "unknown",
            "choice_state": "unknown",
            "signals": [],
            "coverage": 0.0,
            "evidence_reliability": 0.0,
            "limitations": _choice_limitations(),
        }

    voluntariness = _effective_voluntariness(components)
    all_observed = all(item["score"] is not None for item in components.values())
    if not all_observed or voluntariness["score"] is None:
        return {
            "state": "insufficient_evidence",
            "effective_voluntariness": voluntariness,
            "self_deception_risk": None,
            "risk_band": "unknown",
            "choice_state": "unknown",
            "signals": [],
            "coverage": authorship["coverage"],
            "evidence_reliability": authorship["evidence_reliability"],
            "limitations": _choice_limitations(),
        }

    declared = float(components["declared_endorsement"]["score"])
    practical = float(components["practical_voluntariness"]["score"])
    counterfactual = float(components["counterfactual_stability"]["score"])
    reflective = float(components["reflective_stability"]["score"])
    contradiction_free = float(components["contradiction_free"]["score"])
    risk = (
        0.30 * max(0.0, declared - practical)
        + 0.25 * max(0.0, declared - counterfactual)
        + 0.20 * max(0.0, declared - reflective)
        + 0.25 * (100.0 - contradiction_free)
    )
    effective_score = float(voluntariness["score"])
    signals: list[str] = []
    if declared >= 70 and effective_score < 50:
        signals.append("high_endorsement_low_voluntariness")
    if declared >= 70 and counterfactual < 50:
        signals.append("counterfactual_instability")
    if declared >= 70 and reflective < 50:
        signals.append("delayed_endorsement_gap")
    if contradiction_free < 60:
        signals.append("material_behavioral_contradiction")

    reliability = float(authorship["evidence_reliability"])
    return {
        "state": (
            "observed"
            if reliability >= MIN_MEASURED_RELIABILITY
            else "provisional"
        ),
        "effective_voluntariness": voluntariness,
        "declared_endorsement": round(declared, 2),
        "self_deception_risk": round(risk, 2),
        "risk_band": _risk_band(risk),
        "choice_state": _choice_state(declared, effective_score),
        "signals": signals,
        "coverage": authorship["coverage"],
        "evidence_reliability": authorship["evidence_reliability"],
        "components": [_choice_component_summary(item) for item in components.values()],
        "limitations": _choice_limitations(),
    }


def _choice_component_summary(component: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: component[key]
        for key in (
            "id",
            "label",
            "weight",
            "score",
            "coverage",
            "evidence_reliability",
            "state",
            "missing_indicators",
        )
    }


def _choice_limitations() -> str:
    return (
        "Discrepancy diagnostic only: it cannot identify an unconscious true motive, "
        "and low risk does not prove authenticity."
    )


def _guardrail_state(score: float) -> str:
    if score < 30:
        return "critical"
    if score < 60:
        return "warning"
    return "healthy"


def _guardrail_results(observations: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for guardrail_id, (label, indicator_ids, aggregation) in GUARDRAILS.items():
        values = [observations.get(indicator_id) for indicator_id in indicator_ids]
        if any(value is None for value in values):
            results[guardrail_id] = {
                "label": label,
                "score": None,
                "state": "insufficient_evidence",
                "aggregation": aggregation,
                "components": [value for value in values if value is not None],
                "missing_indicators": [
                    indicator_id
                    for indicator_id, value in zip(indicator_ids, values, strict=True)
                    if value is None
                ],
            }
            continue
        complete = [value for value in values if value is not None]
        scores = [value["score"] for value in complete]
        score = min(scores) if aggregation == "minimum" else sum(scores) / len(scores)
        results[guardrail_id] = {
            "label": label,
            "score": round(score, 2),
            "state": _guardrail_state(score),
            "aggregation": aggregation,
            "components": complete,
            "missing_indicators": [],
        }
    return results


def calculate(assessment: Mapping[str, Any], previous: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Calculate a sovereignty result from an explicit observation packet."""
    as_of, observations = _validate_assessment(assessment)
    dimensions = [_dimension_result(item, observations) for item in DIMENSIONS]
    overall_coverage = sum(
        DIMENSION_BY_ID[item["id"]].weight * item["coverage"] for item in dimensions
    )
    overall_reliability = sum(
        DIMENSION_BY_ID[item["id"]].weight * item["evidence_reliability"]
        for item in dimensions
    )
    all_dimensions_observed = all(item["score"] is not None for item in dimensions)
    headline = None
    raw_headline = None
    if all_dimensions_observed and overall_coverage + 1e-9 >= MIN_HEADLINE_COVERAGE:
        scored = [
            (float(item["score"]), DIMENSION_BY_ID[item["id"]].weight)
            for item in dimensions
        ]
        raw_headline = _weighted_geometric(scored)
        bottleneck = min(score for score, _ in scored)
        headline = min(raw_headline, bottleneck + BOTTLENECK_ALLOWANCE)

    if headline is None:
        status = "insufficient_evidence"
    elif overall_reliability < MIN_MEASURED_RELIABILITY:
        status = "provisional"
    else:
        status = "measured"

    guardrails = _guardrail_results(observations)
    authorship = next(item for item in dimensions if item["id"] == "authorship")
    choice_authenticity = _choice_authenticity(authorship)
    warnings: list[str] = []
    if headline is None:
        warnings.append(
            "Headline withheld: every dimension needs at least 65% indicator coverage and total coverage must reach 75%."
        )
    elif raw_headline is not None and headline + 0.005 < raw_headline:
        warnings.append(
            "Bottleneck cap applied: strong dimensions cannot hide the weakest sovereignty dimension."
        )
    if authorship.get("component_cap_applied"):
        warnings.append(
            "Authorship component cap applied: declared choice cannot hide weak voluntariness, counterfactual stability, reflection, or contrary behavior."
        )
    if status == "provisional":
        warnings.append(
            "Score is provisional because weighted evidence reliability is below 75%; improve receipts, logs, confidence, or freshness."
        )
    if choice_authenticity["state"] == "insufficient_evidence":
        warnings.append(
            "Choice-authenticity diagnostic withheld: apparent endorsement is not treated as proof of effective choice."
        )
    elif choice_authenticity["state"] == "provisional":
        warnings.append(
            "Choice-authenticity diagnostic is provisional because its evidence reliability is below 75%; a low risk value must not be treated as reassurance."
        )
    if choice_authenticity["risk_band"] in {"elevated", "high"}:
        warnings.append(
            "Self-Deception Risk is "
            f"{choice_authenticity['risk_band']} at "
            f"{choice_authenticity['self_deception_risk']:.2f}; this is a discrepancy signal, not a diagnosis or claim about an unconscious motive."
        )
    if choice_authenticity["choice_state"] == "endorsed_necessity_possible":
        warnings.append(
            "High endorsement coexists with low effective voluntariness; classify this as possible endorsed necessity rather than fully authored choice."
        )
    for guardrail_id, guardrail in guardrails.items():
        if guardrail["state"] in {"critical", "warning"}:
            warnings.append(
                f"{guardrail['label']} is {guardrail['state']} at {guardrail['score']:.2f}; it remains separate from the sovereignty score."
            )
    if headline is not None and headline >= 70:
        critical = [
            value["label"] for value in guardrails.values() if value["state"] == "critical"
        ]
        if critical:
            warnings.append(
                "High control coexists with a collapsed life guardrail: " + ", ".join(critical)
            )

    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA,
        "model_version": MODEL_VERSION,
        "assessment_id": assessment["assessment_id"],
        "period_start": assessment["period_start"],
        "period_end": assessment["period_end"],
        "as_of": as_of.isoformat(),
        "status": status,
        "sovereignty_index": round(headline, 2) if headline is not None else None,
        "raw_geometric_score": round(raw_headline, 2) if raw_headline is not None else None,
        "evidence_coverage": round(overall_coverage, 3),
        "evidence_reliability": round(overall_reliability, 3),
        "dimensions": dimensions,
        "companion_indexes": {
            "agency_conversion": next(item for item in dimensions if item["id"] == "execution")["score"],
            "attention_sovereignty": next(item for item in dimensions if item["id"] == "attention")["score"],
            "effective_voluntariness": (
                choice_authenticity["effective_voluntariness"]["score"]
                if isinstance(choice_authenticity["effective_voluntariness"], dict)
                else None
            ),
            "optionality": next(item for item in dimensions if item["id"] == "optionality")["score"],
            "life_alignment": next(item for item in dimensions if item["id"] == "alignment")["score"],
            "operational_independence": next(item for item in dimensions if item["id"] == "independence")["score"],
            "recovery": next(item for item in dimensions if item["id"] == "recovery")["score"],
        },
        "choice_authenticity": choice_authenticity,
        "guardrails": guardrails,
        "warnings": warnings,
        "methodology": {
            "dimension_aggregation": "weighted arithmetic mean, except authorship",
            "authorship_aggregation": (
                "bottlenecked weighted geometric mean of declared endorsement, "
                "practical voluntariness, counterfactual stability, reflective "
                "stability, and contradiction-free behavior"
            ),
            "headline_aggregation": "weighted geometric mean of all seven dimensions",
            "bottleneck_cap": f"headline cannot exceed weakest dimension + {BOTTLENECK_ALLOWANCE:g}",
            "missing_data": "unknown; never imputed as zero, average, or success",
            "evidence": "quality, operator confidence, and freshness affect reliability, not the observed score",
            "self_deception": (
                "discrepancy risk derived from endorsement-versus-freedom gaps "
                "and behavioral contradiction; never an inference of a true unconscious motive"
            ),
            "meaning": "control over the shape of life; not worth, productivity, happiness, or a clinical measure",
        },
        "trend": None,
    }
    if previous is not None:
        result["trend"] = compare(previous, result)
    return result


def compare(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    """Compare compatible result snapshots without manufacturing missing deltas."""
    if (
        previous.get("schema_version") != RESULT_SCHEMA
        or previous.get("model_version") != MODEL_VERSION
    ):
        raise SovereigntyError("previous result uses an incompatible schema or model")
    previous_score = previous.get("sovereignty_index")
    current_score = current.get("sovereignty_index")
    headline_delta = None
    if isinstance(previous_score, (int, float)) and isinstance(current_score, (int, float)):
        headline_delta = round(float(current_score) - float(previous_score), 2)
    previous_dimensions = {
        item["id"]: item for item in previous.get("dimensions", []) if isinstance(item, dict)
    }
    deltas: dict[str, float | None] = {}
    for item in current.get("dimensions", []):
        old = previous_dimensions.get(item["id"], {}).get("score")
        new = item.get("score")
        deltas[item["id"]] = (
            round(float(new) - float(old), 2)
            if isinstance(old, (int, float)) and isinstance(new, (int, float))
            else None
        )
    return {
        "previous_assessment_id": previous.get("assessment_id"),
        "previous_period_end": previous.get("period_end"),
        "headline_delta": headline_delta,
        "dimension_deltas": deltas,
        "choice_authenticity_deltas": {
            "effective_voluntariness": _nested_delta(
                previous,
                current,
                ("choice_authenticity", "effective_voluntariness", "score"),
            ),
            "self_deception_risk": _nested_delta(
                previous,
                current,
                ("choice_authenticity", "self_deception_risk"),
            ),
        },
    }


def _nested_delta(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    path: Sequence[str],
) -> float | None:
    old: Any = previous
    new: Any = current
    for key in path:
        old = old.get(key) if isinstance(old, Mapping) else None
        new = new.get(key) if isinstance(new, Mapping) else None
    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        return round(float(new) - float(old), 2)
    return None


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"


def render_markdown(result: Mapping[str, Any]) -> str:
    headline = result.get("sovereignty_index")
    display = "withheld — insufficient evidence" if headline is None else f"{headline:.2f} / 100"
    lines = [
        "# Sovereignty Index",
        "",
        f"- Period: {result['period_start']} → {result['period_end']}",
        f"- Status: **{result['status']}**",
        f"- Sovereignty Index: **{display}**",
        f"- Evidence coverage: {result['evidence_coverage'] * 100:.1f}%",
        f"- Evidence reliability: {result['evidence_reliability'] * 100:.1f}%",
        "",
        "## Control dimensions",
        "",
        "| Dimension | Score | Coverage | Reliability |",
        "|---|---:|---:|---:|",
    ]
    for item in result["dimensions"]:
        score = "unknown" if item["score"] is None else f"{item['score']:.2f}"
        lines.append(
            f"| {item['label']} | {score} | {item['coverage'] * 100:.0f}% | "
            f"{item['evidence_reliability'] * 100:.0f}% |"
        )
    choice = result["choice_authenticity"]
    effective = choice.get("effective_voluntariness")
    effective_score = (
        effective.get("score") if isinstance(effective, Mapping) else None
    )
    lines.extend(
        [
            "",
            "## Choice authenticity",
            "",
            f"- Effective voluntariness: **{_display_score(effective_score)}**",
            f"- Self-Deception Risk: **{_display_score(choice.get('self_deception_risk'))}**",
            f"- Risk band: **{choice['risk_band']}**",
            f"- Choice state: **{choice['choice_state']}**",
            f"- Diagnostic state: **{choice['state']}**",
            "",
            choice["limitations"],
        ]
    )
    if choice.get("components"):
        lines.extend(
            [
                "",
                "| Choice component | Score | Coverage | Reliability |",
                "|---|---:|---:|---:|",
            ]
        )
        for item in choice["components"]:
            lines.append(
                f"| {item['label']} | {_display_score(item['score'])} | "
                f"{item['coverage'] * 100:.0f}% | "
                f"{item['evidence_reliability'] * 100:.0f}% |"
            )
    lines.extend(
        [
            "",
            "## Non-compensating guardrails",
            "",
            "| Guardrail | Score | State |",
            "|---|---:|---|",
        ]
    )
    for item in result["guardrails"].values():
        score = "unknown" if item["score"] is None else f"{item['score']:.2f}"
        lines.append(f"| {item['label']} | {score} | {item['state']} |")
    if result["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result["warnings"])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This measures evidenced control over the shape of life. It is not a measure of human worth,",
            "productivity, happiness, mental health, or the quality of other people. A rising score is",
            "good only if the separate life guardrails remain intact.",
            "",
        ]
    )
    return "\n".join(lines)


def _display_score(value: Any) -> str:
    return "unknown" if not isinstance(value, (int, float)) else f"{value:.2f}"
