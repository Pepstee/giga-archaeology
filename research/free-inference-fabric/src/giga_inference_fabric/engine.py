from __future__ import annotations

import hashlib
import json
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from .evaluators import Evaluator
from .models import Candidate, Completion, Critique, ExperimentRequest, ExperimentResult, GateResult, ModelSpec
from .providers import ModelAdapter, ProviderError
from .store import ExperimentStore


SYSTEM = """You are one replaceable worker inside an evidence-gated ensemble.
Do not claim success. Produce a concrete candidate only. Objective gates, not your confidence,
decide whether it works. Preserve constraints and explicitly change strategy when instructed."""

APPROACHES = (
    "minimal_direct",
    "test_first",
    "failure_mode_first",
    "alternative_architecture",
    "simplify_then_rebuild",
    "evidence_reconstruction",
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ExperimentEngine:
    def __init__(
        self,
        *,
        adapters: dict[str, ModelAdapter],
        models: list[ModelSpec],
        store: ExperimentStore,
    ):
        self.adapters = adapters
        self.models = models
        self.store = store
        self._remote_calls = 0
        self._max_remote_calls = 0
        self._budget_lock = Lock()
        self._total_cost_usd = 0.0
        self._reserved_cost_usd = 0.0
        self._max_total_cost_usd = 0.0
        self._prior_remote_calls_today = 0
        self._daily_remote_limit = 0
        self._max_output_tokens = 4096

    def eligible_models(self, request: ExperimentRequest) -> list[ModelSpec]:
        eligible = []
        seen_model_ids = set()
        for model in self.models:
            if (
                model.model_id not in seen_model_ids
                and request.policy.allows(model)
                and request.required_capabilities.issubset(model.capabilities)
                and model.adapter in self.adapters
            ):
                eligible.append(model)
                seen_model_ids.add(model.model_id)
        return eligible

    def run(self, request: ExperimentRequest, evaluator: Evaluator) -> ExperimentResult:
        experiment_id = request.experiment_id or f"exp-{uuid.uuid4().hex}"
        self._validate_request(request)
        eligible = self.eligible_models(request)
        if not eligible:
            raise ValueError("no policy-compatible models satisfy the request")
        distinct_models = {model.model_id for model in eligible}
        if request.min_distinct_models < 1:
            raise ValueError("min_distinct_models must be positive")
        if request.min_distinct_models > request.candidates_per_round:
            raise ValueError("min_distinct_models cannot exceed candidates_per_round")
        if len(distinct_models) < request.min_distinct_models:
            raise ValueError(
                f"requested {request.min_distinct_models} distinct models but only "
                f"{len(distinct_models)} are policy-compatible"
            )
        if request.critics_per_candidate > 0 and len(distinct_models) < 2:
            raise ValueError("cross-model criticism requires at least two distinct eligible models")
        self.store.start(experiment_id, request)
        self._remote_calls = 0
        self._max_remote_calls = request.max_remote_calls
        self._total_cost_usd = 0.0
        self._reserved_cost_usd = 0.0
        self._max_total_cost_usd = request.policy.max_total_cost_usd
        self._prior_remote_calls_today = self.store.remote_calls_today()
        self._daily_remote_limit = request.daily_remote_limit
        self._max_output_tokens = request.max_output_tokens
        attempts = 0
        best: tuple[Candidate, GateResult] | None = None
        recent_scores: deque[float] = deque(maxlen=max(2, request.stagnation_rounds))
        seen_outputs: set[str] = set()
        if request.use_experience:
            experience = self.store.reusable_experience(request.workload, request.objective)
            feedback = "REUSABLE EXPERIENCE (evidence only; revalidate on this task):\n" + json.dumps(
                experience, ensure_ascii=False, sort_keys=True
            )
        else:
            feedback = "EXPERIENCE ABLATION: prior solution/failure memory is disabled for this arm."
        stop_reason = "round budget exhausted"

        for round_number in range(1, request.max_rounds + 1):
            round_results: list[tuple[Candidate, GateResult]] = []
            jobs: list[tuple[ModelSpec, str, str]] = []
            for slot in range(request.candidates_per_round):
                model = eligible[(round_number - 1 + slot) % len(eligible)]
                approach = APPROACHES[(round_number - 1 + slot) % len(APPROACHES)]
                prompt = self._candidate_prompt(request, round_number, approach, feedback, best)
                jobs.append((model, approach, prompt))

            # Independent hypotheses are sent concurrently; recording and gate evaluation stay
            # serial and deterministic in slot order.
            with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
                futures = [pool.submit(self._complete, model, prompt) for model, _, prompt in jobs]
            for (model, approach, _), future in zip(jobs, futures, strict=True):
                try:
                    completion = future.result()
                    provider_failed = False
                except ProviderError as exc:
                    # Provider failure is evidence and consumes the bounded attempt, but cannot
                    # become a model-authored success or an infinite retry.
                    completion = Completion(
                        text=f"PROVIDER_FAILURE: {exc}", model_id=model.model_id, adapter=model.adapter,
                    )
                    provider_failed = True
                if model.adapter != "local" and "budget exhausted" not in completion.text:
                    self.store.record_provider_call(
                        call_id=f"call-{uuid.uuid4().hex}", experiment_id=experiment_id,
                        purpose="candidate", requested_model_id=model.model_id, adapter=model.adapter,
                        success=not provider_failed,
                        served_model_id=completion.model_id if not provider_failed else None,
                        latency_ms=completion.latency_ms, prompt_tokens=completion.prompt_tokens,
                        completion_tokens=completion.completion_tokens, cost_usd=completion.cost_usd,
                        error=completion.text if provider_failed else None,
                    )
                attempts += 1
                output_hash = _hash(completion.text)
                candidate = Candidate(
                    candidate_id=f"candidate-{uuid.uuid4().hex}", experiment_id=experiment_id,
                    round_number=round_number, approach=approach, completion=completion,
                    output_hash=output_hash, requested_model_id=model.model_id,
                )
                self.store.record_candidate(candidate)
                gate = GateResult(False, 0.0, completion.text) if provider_failed else evaluator.evaluate(candidate)
                self.store.record_gate(candidate.candidate_id, gate)
                round_results.append((candidate, gate))

            critiques = self._cross_criticise(request, round_results, eligible)
            round_best = max(round_results, key=lambda item: (item[1].passed, item[1].score, -len(item[0].completion.text)))
            if best is None or (round_best[1].passed, round_best[1].score) >= (best[1].passed, best[1].score):
                best = round_best
            if round_best[1].passed:
                stop_reason = "objective gate passed"
                self.store.record_solution_pattern(experiment_id, request.workload, request.objective)
                self.store.finish(experiment_id, "VERIFIED", stop_reason)
                return self._result(experiment_id, "VERIFIED", best, round_number, attempts, stop_reason, request)

            repeated = all(candidate.output_hash in seen_outputs for candidate, _ in round_results)
            seen_outputs.update(candidate.output_hash for candidate, _ in round_results)
            recent_scores.append(round_best[1].score)
            stagnant = repeated or (
                len(recent_scores) == recent_scores.maxlen
                and max(recent_scores) - min(recent_scores) < request.min_score_improvement
            )
            feedback = self._feedback(round_results, stagnant, critiques)
            if stagnant and round_number >= request.stagnation_rounds:
                # Do not simply retry: the next round receives an explicit strategy-reset
                # contract and rotates to different approaches/models.
                feedback += "\nSTAGNATION DETECTED. Discard the current method and use a different decomposition."

        self.store.record_failure_pattern(experiment_id, request.workload, request.objective)
        self.store.finish(experiment_id, "UNVERIFIED", stop_reason)
        return self._result(experiment_id, "UNVERIFIED", best, request.max_rounds, attempts, stop_reason, request)

    @staticmethod
    def _validate_request(request: ExperimentRequest) -> None:
        if not request.objective.strip() or not request.prompt.strip():
            raise ValueError("objective and prompt must be non-empty")
        if request.candidates_per_round < 1 or request.max_rounds < 1:
            raise ValueError("candidate and round counts must be positive")
        if request.critics_per_candidate < 0:
            raise ValueError("critic count cannot be negative")
        if request.max_remote_calls < 0 or request.daily_remote_limit < 0:
            raise ValueError("remote-call limits cannot be negative")
        if request.stagnation_rounds < 2:
            raise ValueError("stagnation_rounds must be at least two")
        if request.max_output_tokens < 1 or request.max_output_tokens > 65536:
            raise ValueError("max_output_tokens must be between 1 and 65536")

    def _candidate_prompt(
        self,
        request: ExperimentRequest,
        round_number: int,
        approach: str,
        feedback: str,
        best: tuple[Candidate, GateResult] | None,
    ) -> str:
        prior = ""
        if best:
            prior = (
                "\nBEST PRIOR CANDIDATE (unverified):\n" + best[0].completion.text[-12000:]
                + "\nOBJECTIVE GATE FEEDBACK:\n" + best[1].summary
                + "\nOBJECTIVE GATE CHECKS:\n"
                + json.dumps(best[1].checks, ensure_ascii=False, indent=2)[-12000:]
            )
        return f"""OBJECTIVE: {request.objective}
WORKLOAD: {request.workload}
ROUND: {round_number}
MANDATORY APPROACH: {approach}
CONTEXT:\n{request.context}
TASK:\n{request.prompt}
PRIOR FEEDBACK:\n{feedback}{prior}

Return the complete candidate. Do not grade yourself and do not claim tests passed."""

    def _cross_criticise(
        self,
        request: ExperimentRequest,
        candidates: list[tuple[Candidate, GateResult]],
        eligible: list[ModelSpec],
    ) -> dict[str, list[dict[str, str]]]:
        findings: dict[str, list[dict[str, str]]] = {}
        if request.critics_per_candidate <= 0 or len(eligible) < 2:
            return findings
        for candidate, gate in candidates:
            producer_model_id = candidate.requested_model_id or candidate.completion.model_id
            independent = [model for model in eligible if model.model_id != producer_model_id]
            for model in independent[: request.critics_per_candidate]:
                prompt = f"""Critique this candidate independently against the objective and gate evidence.
Do not rewrite it and do not certify it. Identify concrete defects, missing tests, false assumptions,
security/reliability risks and a materially different correction strategy.

OBJECTIVE: {request.objective}
GATE: {gate.summary}
CANDIDATE:\n{candidate.completion.text[-16000:]}"""
                try:
                    completion = self._complete(model, prompt)
                except ProviderError as exc:
                    text = f"CRITIC_PROVIDER_FAILURE: {exc}"
                    success = False
                    completion = None
                else:
                    text = completion.text
                    success = True
                if model.adapter != "local" and "budget exhausted" not in text:
                    self.store.record_provider_call(
                        call_id=f"call-{uuid.uuid4().hex}", experiment_id=candidate.experiment_id,
                        purpose="critic", requested_model_id=model.model_id, adapter=model.adapter,
                        success=success, served_model_id=completion.model_id if completion else None,
                        latency_ms=completion.latency_ms if completion else 0,
                        prompt_tokens=completion.prompt_tokens if completion else 0,
                        completion_tokens=completion.completion_tokens if completion else 0,
                        cost_usd=completion.cost_usd if completion else 0.0,
                        error=None if success else text,
                    )
                critique = Critique(candidate.candidate_id, model.model_id, text, _hash(text))
                self.store.record_critique(critique)
                findings.setdefault(candidate.candidate_id, []).append({
                    "critic_model": model.model_id,
                    "finding": text,
                })
        return findings

    def _complete(self, model: ModelSpec, prompt: str) -> Completion:
        reservation = 0.0
        if model.adapter != "local":
            with self._budget_lock:
                if self._remote_calls >= self._max_remote_calls:
                    raise ProviderError("experiment remote-call budget exhausted")
                if self._prior_remote_calls_today + self._remote_calls >= self._daily_remote_limit:
                    raise ProviderError("daily remote-call budget exhausted")
                if model.cost_tier.value == "paid":
                    reservation = self._paid_call_reservation(model, prompt)
                    if (
                        self._max_total_cost_usd <= 0
                        or self._total_cost_usd + self._reserved_cost_usd + reservation
                        > self._max_total_cost_usd
                    ):
                        raise ProviderError("paid-model pre-call reservation exceeds admitted budget")
                    self._reserved_cost_usd += reservation
                self._remote_calls += 1
        try:
            completion = self.adapters[model.adapter].complete(
                model, system=SYSTEM, prompt=prompt, max_output_tokens=self._max_output_tokens,
            )
        except Exception:
            with self._budget_lock:
                self._reserved_cost_usd -= reservation
            raise
        with self._budget_lock:
            self._reserved_cost_usd -= reservation
            self._total_cost_usd += completion.cost_usd
        return completion

    def _paid_call_reservation(self, model: ModelSpec, prompt: str) -> float:
        pricing = model.metadata.get("pricing")
        if not isinstance(pricing, dict):
            raise ProviderError("paid model has no published pricing for pre-call reservation")
        price_rows = [pricing]
        overrides = pricing.get("overrides", [])
        if isinstance(overrides, dict):
            price_rows.extend(value for value in overrides.values() if isinstance(value, dict))
        elif isinstance(overrides, list):
            price_rows.extend(value for value in overrides if isinstance(value, dict))
        try:
            price_pairs = [
                (float(row["prompt"]), float(row["completion"])) for row in price_rows
                if "prompt" in row or "completion" in row
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("paid model pricing is invalid") from exc
        if not price_pairs or any(
            prompt_price < 0 or completion_price < 0
            for prompt_price, completion_price in price_pairs
        ):
            raise ProviderError("paid model pricing is invalid or zero")
        prompt_price = max(pair[0] for pair in price_pairs)
        completion_price = max(pair[1] for pair in price_pairs)
        if prompt_price + completion_price <= 0:
            raise ProviderError("paid model pricing is invalid or zero")
        # UTF-8 byte length is deliberately much more conservative than a normal token estimate.
        # The extra allowance covers message framing and provider-specific special tokens.
        prompt_token_bound = len((SYSTEM + prompt).encode("utf-8")) + 256
        return prompt_token_bound * prompt_price + self._max_output_tokens * completion_price

    @staticmethod
    def _feedback(
        results: list[tuple[Candidate, GateResult]],
        stagnant: bool,
        critiques: dict[str, list[dict[str, str]]],
    ) -> str:
        rows = [
            {"model": candidate.completion.model_id, "approach": candidate.approach,
             "score": gate.score, "passed": gate.passed, "gate": gate.summary,
             "gate_checks": gate.checks,
             "independent_critiques": critiques.get(candidate.candidate_id, [])}
            for candidate, gate in results
        ]
        return "ROUND EVIDENCE:\n" + json.dumps(rows, ensure_ascii=False, indent=2) + (
            "\nOutputs repeated or stopped improving." if stagnant else ""
        )

    def _result(
        self,
        experiment_id: str,
        status: str,
        best: tuple[Candidate, GateResult] | None,
        rounds: int,
        attempts: int,
        stop_reason: str,
        request: ExperimentRequest,
    ) -> ExperimentResult:
        packet = {
            "schema": "giga.frontier-escalation-packet.v1",
            "experiment_id": experiment_id,
            "objective": request.objective,
            "status": status,
            "stop_reason": stop_reason,
            "remote_calls": self._remote_calls,
            "total_cost_usd": round(self._total_cost_usd, 8),
            "attempts": self.store.experiment_attempts(experiment_id),
            "critiques": self.store.experiment_critiques(experiment_id),
            "instruction": "Use this evidence; do not restart the task from zero. Resolve the remaining gate failures.",
        }
        return ExperimentResult(
            experiment_id, status, best[0] if best else None, best[1] if best else None,
            rounds, attempts, self._remote_calls, stop_reason, packet,
        )
