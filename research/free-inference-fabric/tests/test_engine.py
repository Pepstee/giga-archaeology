from __future__ import annotations

from pathlib import Path

from giga_inference_fabric.engine import ExperimentEngine
from giga_inference_fabric.evaluators import TextContractEvaluator
from giga_inference_fabric.models import (
    Completion,
    CostTier,
    ExperimentRequest,
    GateResult,
    ModelPolicy,
    ModelSpec,
    PrivacyClass,
)
from giga_inference_fabric.providers import ProviderError
from giga_inference_fabric.store import ExperimentStore


class ScriptedAdapter:
    name = "fake"

    def __init__(self, scripts: dict[str, list[str]]):
        self.scripts = scripts
        self.calls: list[tuple[str, str]] = []

    def complete(self, model, *, system, prompt, max_output_tokens=4096, timeout=180):
        self.calls.append((model.model_id, prompt))
        outputs = self.scripts[model.model_id]
        if not outputs:
            raise ProviderError("fixture exhausted")
        return Completion(outputs.pop(0), model.model_id, self.name)


def model(model_id: str, *, tier: CostTier = CostTier.FREE, adapter: str = "fake", zdr: bool = False):
    return ModelSpec(model_id, adapter, tier, zero_data_retention=zdr)


def test_independent_candidates_cross_critics_and_repairs_until_gate_passes(tmp_path: Path):
    # Candidate calls and critic calls share the script. Round 1 fails; a materially
    # different round-2 candidate passes the objective gate.
    adapter = ScriptedAdapter({
        "free/a": ["bad-a", "critique-a1", "GOOD implementation", "critique-a2"],
        "free/b": ["bad-b", "critique-b1", "critique-b2", "critique-b3"],
    })
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="produce a verified candidate", prompt="solve it", candidates_per_round=2,
            critics_per_candidate=1, max_rounds=2,
            policy=ModelPolicy(allowed_tiers=frozenset({CostTier.FREE}), allowed_adapters=frozenset({"fake"})),
        )
        result = ExperimentEngine(
            adapters={"fake": adapter}, models=[model("free/a"), model("free/b")], store=store,
        ).run(request, TextContractEvaluator((r"GOOD",)))
        assert result.status == "VERIFIED"
        assert result.rounds == 2
        assert result.attempts == 4
        assert result.best_gate and result.best_gate.passed
        assert len(store.experiment_attempts(result.experiment_id)) == 4
        critique_count = store.connection.execute("SELECT count(*) FROM critiques").fetchone()[0]
        assert critique_count == 4
        assert store.connection.execute("SELECT count(*) FROM provider_calls").fetchone()[0] == 8
        assert store.connection.execute("SELECT count(*) FROM solution_patterns").fetchone()[0] == 1
        assert store.reusable_experience(request.workload, request.objective)["successful_patterns"]
        scoreboard = store.scoreboard()
        assert sum(row["candidate_attempts"] for row in scoreboard) == 4
        assert any("BEST PRIOR CANDIDATE" in prompt for _, prompt in adapter.calls)
        assert any("independent_critiques" in prompt for _, prompt in adapter.calls)
        assert result.escalation_packet["critiques"]
    finally:
        store.close()


def test_provider_failure_cannot_pass_a_weak_text_gate(tmp_path: Path):
    adapter = ScriptedAdapter({"free/a": []})
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=1, critics_per_candidate=0, max_rounds=1,
            min_distinct_models=1,
            policy=ModelPolicy(allowed_tiers=frozenset({CostTier.FREE}), allowed_adapters=frozenset({"fake"})),
        )
        result = ExperimentEngine(adapters={"fake": adapter}, models=[model("free/a")], store=store).run(
            request, TextContractEvaluator((r".",))
        )
        assert result.status == "UNVERIFIED"
        assert result.best_gate and result.best_gate.score == 0.0
        assert "PROVIDER_FAILURE" in result.best_gate.summary
    finally:
        store.close()


def test_provider_failure_rotates_to_a_different_free_model(tmp_path: Path):
    adapter = ScriptedAdapter({"free/a": [], "free/b": ["GOOD"]})
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=1, critics_per_candidate=0,
            min_distinct_models=1, max_rounds=2,
            policy=ModelPolicy(
                allowed_tiers=frozenset({CostTier.FREE}), allowed_adapters=frozenset({"fake"}),
            ),
        )
        result = ExperimentEngine(
            adapters={"fake": adapter}, models=[model("free/a"), model("free/b")], store=store,
        ).run(request, TextContractEvaluator((r"GOOD",)))
        assert result.status == "VERIFIED"
        assert [model_id for model_id, _ in adapter.calls] == ["free/a", "free/b"]
        assert result.rounds == 2
    finally:
        store.close()


def test_exact_objective_check_output_reaches_repair_prompt(tmp_path: Path):
    class EvidenceEvaluator:
        def evaluate(self, candidate):
            if candidate.completion.text == "fixed":
                return GateResult(True, 1.0, "passed")
            return GateResult(
                False, 0.0, "objective commands passed 0/1",
                ({"exit_code": 1, "output": "missing schema field"},),
            )

    adapter = ScriptedAdapter({"free/a": ["broken", "fixed"]})
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=1, critics_per_candidate=0,
            min_distinct_models=1, max_rounds=2,
            policy=ModelPolicy(
                allowed_tiers=frozenset({CostTier.FREE}), allowed_adapters=frozenset({"fake"}),
            ),
        )
        result = ExperimentEngine(
            adapters={"fake": adapter}, models=[model("free/a")], store=store,
        ).run(request, EvidenceEvaluator())
        assert result.status == "VERIFIED"
        assert "missing schema field" in adapter.calls[1][1]
        assert "OBJECTIVE GATE CHECKS" in adapter.calls[1][1]
        attempts = result.escalation_packet["attempts"]
        assert attempts[0]["gate_checks"][0]["output"] == "missing schema field"
    finally:
        store.close()


def test_memory_ablation_really_excludes_reusable_experience(tmp_path: Path):
    adapter = ScriptedAdapter({"free/a": ["pass"]})
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=1, critics_per_candidate=0,
            min_distinct_models=1, max_rounds=1, use_experience=False,
            study_id="study", study_arm_id="no-memory", repeat_index=1,
            policy=ModelPolicy(
                allowed_tiers=frozenset({CostTier.FREE}), allowed_adapters=frozenset({"fake"}),
            ),
        )
        result = ExperimentEngine(
            adapters={"fake": adapter}, models=[model("free/a")], store=store,
        ).run(request, TextContractEvaluator((r"pass",)))
        assert result.status == "VERIFIED"
        assert "EXPERIENCE ABLATION" in adapter.calls[0][1]
        assert "REUSABLE EXPERIENCE" not in adapter.calls[0][1]
        scoreboard = store.study_scoreboard("study")
        assert scoreboard[0]["arm_id"] == "no-memory"
        assert scoreboard[0]["verification_rate"] == 1.0
    finally:
        store.close()


def test_stagnation_changes_strategy_instead_of_unbounded_identical_retry(tmp_path: Path):
    adapter = ScriptedAdapter({"free/a": ["same", "same", "same"]})
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=1, critics_per_candidate=0,
            min_distinct_models=1, max_rounds=3, stagnation_rounds=2,
            policy=ModelPolicy(allowed_tiers=frozenset({CostTier.FREE}), allowed_adapters=frozenset({"fake"})),
        )
        result = ExperimentEngine(adapters={"fake": adapter}, models=[model("free/a")], store=store).run(
            request, TextContractEvaluator((r"never-present",))
        )
        assert result.status == "UNVERIFIED"
        assert result.attempts == 3
        assert store.connection.execute("SELECT count(*) FROM failure_patterns").fetchone()[0] == 1
        assert "STAGNATION DETECTED" in adapter.calls[-1][1]
        approaches = [row[0] for row in store.connection.execute(
            "SELECT approach FROM attempts WHERE experiment_id=? ORDER BY round_number", (result.experiment_id,)
        )]
        assert len(set(approaches)) == 3
    finally:
        store.close()


def test_vault_policy_rejects_non_zdr_remote_but_allows_local():
    policy = ModelPolicy(
        allowed_tiers=frozenset({CostTier.FREE, CostTier.LOCAL}),
        allowed_adapters=frozenset({"openrouter", "local"}),
        privacy_class=PrivacyClass.VAULT,
    )
    assert not policy.allows(model("remote/free", adapter="openrouter", zdr=False))
    assert policy.allows(model("local/model", tier=CostTier.LOCAL, adapter="local"))
    assert policy.allows(model("remote/zdr", adapter="openrouter", zdr=True))


def test_remote_call_budget_caps_candidates_and_critics(tmp_path: Path):
    adapter = ScriptedAdapter({"free/a": ["bad"] * 10, "free/b": ["bad"] * 10})
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=2, critics_per_candidate=2,
            max_rounds=2, max_remote_calls=3,
            policy=ModelPolicy(allowed_tiers=frozenset({CostTier.FREE}), allowed_adapters=frozenset({"fake"})),
        )
        # fake is counted as remote because only the canonical local adapter is quota-free.
        result = ExperimentEngine(adapters={"fake": adapter}, models=[model("free/a"), model("free/b")], store=store).run(
            request, TextContractEvaluator((r"pass",))
        )
        assert result.remote_calls == 3
        assert len(adapter.calls) == 3
    finally:
        store.close()


def test_daily_remote_budget_survives_across_experiments(tmp_path: Path):
    adapter = ScriptedAdapter({"free/a": ["bad", "bad"]})
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        engine = ExperimentEngine(adapters={"fake": adapter}, models=[model("free/a")], store=store)
        policy = ModelPolicy(allowed_tiers=frozenset({CostTier.FREE}), allowed_adapters=frozenset({"fake"}))
        first = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=1, critics_per_candidate=0,
            min_distinct_models=1, max_rounds=1, daily_remote_limit=1, policy=policy,
        )
        second = ExperimentRequest(
            objective="y", prompt="y", candidates_per_round=1, critics_per_candidate=0,
            min_distinct_models=1, max_rounds=1, daily_remote_limit=1, policy=policy,
        )
        engine.run(first, TextContractEvaluator((r"pass",)))
        result = engine.run(second, TextContractEvaluator((r"pass",)))
        assert len(adapter.calls) == 1
        assert result.remote_calls == 0
        assert store.remote_calls_today() == 1
        assert result.best_gate and "daily remote-call budget exhausted" in result.best_gate.summary
    finally:
        store.close()


def test_multi_model_claim_fails_closed_when_diversity_is_unavailable(tmp_path: Path):
    adapter = ScriptedAdapter({"free/a": ["pass"]})
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=2, critics_per_candidate=0,
            min_distinct_models=2, max_rounds=1,
            policy=ModelPolicy(
                allowed_tiers=frozenset({CostTier.FREE}),
                allowed_adapters=frozenset({"fake"}),
            ),
        )
        try:
            ExperimentEngine(adapters={"fake": adapter}, models=[model("free/a")], store=store).run(
                request, TextContractEvaluator((r"pass",))
            )
        except ValueError as exc:
            assert "distinct models" in str(exc)
        else:
            raise AssertionError("single-model pool must not satisfy a two-model contract")
        assert not adapter.calls
    finally:
        store.close()


def test_duplicate_model_entries_do_not_fake_diversity(tmp_path: Path):
    adapter = ScriptedAdapter({"free/a": ["pass"]})
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        engine = ExperimentEngine(
            adapters={"fake": adapter},
            models=[model("free/a"), model("free/a")],
            store=store,
        )
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=2, critics_per_candidate=0,
            min_distinct_models=2, max_rounds=1,
            policy=ModelPolicy(
                allowed_tiers=frozenset({CostTier.FREE}), allowed_adapters=frozenset({"fake"}),
            ),
        )
        assert len(engine.eligible_models(request)) == 1
        try:
            engine.run(request, TextContractEvaluator((r"pass",)))
        except ValueError as exc:
            assert "distinct models" in str(exc)
        else:
            raise AssertionError("duplicate catalogue rows must not satisfy diversity")
    finally:
        store.close()


def test_paid_call_is_reserved_before_provider_execution(tmp_path: Path):
    adapter = ScriptedAdapter({"paid/a": ["pass"]})
    paid = ModelSpec(
        "paid/a", "fake", CostTier.PAID,
        metadata={"pricing": {"prompt": "0.000001", "completion": "0.001"}},
    )
    policy = ModelPolicy(
        allowed_tiers=frozenset({CostTier.PAID}), allowed_adapters=frozenset({"fake"}),
        allow_paid_escalation=True, max_total_cost_usd=0.01,
    )
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=1, critics_per_candidate=0,
            min_distinct_models=1, max_rounds=1, max_output_tokens=100,
            policy=policy,
        )
        result = ExperimentEngine(adapters={"fake": adapter}, models=[paid], store=store).run(
            request, TextContractEvaluator((r"pass",))
        )
        assert result.status == "UNVERIFIED"
        assert not adapter.calls
        assert result.best_gate and "pre-call reservation" in result.best_gate.summary
    finally:
        store.close()


def test_paid_call_with_sufficient_reservation_reaches_provider(tmp_path: Path):
    adapter = ScriptedAdapter({"paid/a": ["pass"]})
    paid = ModelSpec(
        "paid/a", "fake", CostTier.PAID,
        metadata={"pricing": {"prompt": "0.000001", "completion": "0.000001"}},
    )
    policy = ModelPolicy(
        allowed_tiers=frozenset({CostTier.PAID}), allowed_adapters=frozenset({"fake"}),
        allow_paid_escalation=True, max_total_cost_usd=1.0,
    )
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=1, critics_per_candidate=0,
            min_distinct_models=1, max_rounds=1, max_output_tokens=100,
            policy=policy,
        )
        result = ExperimentEngine(adapters={"fake": adapter}, models=[paid], store=store).run(
            request, TextContractEvaluator((r"pass",))
        )
        assert result.status == "VERIFIED"
        assert len(adapter.calls) == 1
    finally:
        store.close()


def test_paid_reservation_uses_highest_published_pricing_override(tmp_path: Path):
    adapter = ScriptedAdapter({"paid/a": ["pass"]})
    paid = ModelSpec(
        "paid/a", "fake", CostTier.PAID,
        metadata={"pricing": {
            "prompt": "0.000001", "completion": "0.000001",
            "overrides": [{"prompt": "0.000001", "completion": "0.01"}],
        }},
    )
    policy = ModelPolicy(
        allowed_tiers=frozenset({CostTier.PAID}), allowed_adapters=frozenset({"fake"}),
        allow_paid_escalation=True, max_total_cost_usd=0.1,
    )
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        request = ExperimentRequest(
            objective="x", prompt="x", candidates_per_round=1, critics_per_candidate=0,
            min_distinct_models=1, max_rounds=1, max_output_tokens=20, policy=policy,
        )
        result = ExperimentEngine(adapters={"fake": adapter}, models=[paid], store=store).run(
            request, TextContractEvaluator((r"pass",))
        )
        assert result.status == "UNVERIFIED"
        assert not adapter.calls
        assert result.best_gate and "pre-call reservation" in result.best_gate.summary
    finally:
        store.close()
