from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

from giga_inference_fabric.benchmarks import build_benchmark_contract, verify_benchmark_contract
from giga_inference_fabric.catalogue import (
    harvest_experiment_id,
    harvest_targets,
    load_profiles,
    model_window_diff,
)
from giga_inference_fabric.cli import _select_explicit_free_models, harvest_next, study_next
from giga_inference_fabric.evaluators import CommandEvaluator, evaluator_from_contract
from giga_inference_fabric.models import Candidate, Completion, CostTier, ModelSpec
from giga_inference_fabric.providers import (
    OpenAICompatibleAdapter,
    OpenCodeOpenRouterAdapter,
    ProviderError,
    discover_local_models,
)
from giga_inference_fabric.store import ExperimentStore
from giga_inference_fabric.studies import (
    expand_study_cells,
    load_studies,
    next_pending_study_cell,
    resolve_study_arm,
    study_catalogue_hash,
    unschedulable_study_cells,
)


ROOT = Path(__file__).resolve().parents[1]


def _register_test_harvest_benchmark(store: ExperimentStore, tmp_path: Path) -> None:
    fixture = tmp_path / "harvest-benchmark"
    fixture.mkdir()
    manifest = {
        "benchmark_id": "harvest-bench", "project": "fabric", "workload": "model-benchmark",
        "objective": "return locked artifact", "prompt": "return the locked artifact",
    }
    (fixture / "benchmark.json").write_text(json.dumps(manifest), encoding="utf-8")
    (fixture / "verify_candidate.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    binding = build_benchmark_contract(str(fixture), "python3 verify_candidate.py")
    assert store.register_benchmark(
        "harvest-bench", "fabric", "model-benchmark", "return locked artifact",
        str(fixture), "python3 verify_candidate.py", {"binding": binding},
    )


def test_free_window_harvest_prioritises_preview_and_has_stable_identity():
    binding = {"fixture_sha256": "fixture", "evaluator_sha256": "evaluator"}
    models = [
        ModelSpec("free/z", "openrouter", CostTier.FREE),
        ModelSpec("preview/b", "openrouter", CostTier.FREE, preview=True),
        ModelSpec("preview/a", "openrouter", CostTier.FREE, preview=True),
        ModelSpec("paid/a", "openrouter", CostTier.PAID, preview=True),
    ]
    targets = harvest_targets(
        models, binding, max_rounds=1, excluded_model_ids=set(), claimed_experiment_ids=set(),
    )
    assert [target.model_id for target in targets] == ["preview/a", "preview/b", "free/z"]
    assert targets[0].experiment_id == harvest_experiment_id(
        binding, "preview/a", max_rounds=1,
    )
    assert harvest_experiment_id(binding, "preview/a", max_rounds=1) != harvest_experiment_id(
        binding, "preview/a", max_rounds=2,
    )
    assert harvest_targets(
        models, binding, max_rounds=1, excluded_model_ids={"preview/a"},
        claimed_experiment_ids={targets[1].experiment_id},
    )[0].model_id == "free/z"


def test_harvest_next_refuses_before_provider_discovery_when_budget_is_exhausted(
    tmp_path: Path, capsys,
):
    db = tmp_path / "experiments.sqlite3"
    store = ExperimentStore(db)
    try:
        _register_test_harvest_benchmark(store, tmp_path)
        store.observe_models([
            ModelSpec("preview/model", "openrouter", CostTier.FREE, preview=True),
        ])
    finally:
        store.close()
    args = SimpleNamespace(
        db=db, benchmark_id="harvest-bench", rounds=1, daily_remote_limit=0,
        execute=False,
    )
    assert harvest_next(args) == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "BUDGET_WAIT"
    assert payload["model_id"] == "preview/model" and payload["preview"] is True
    store = ExperimentStore(db)
    try:
        assert store.experiment_ids() == set()
        assert store.remote_calls_today() == 0
    finally:
        store.close()


def test_explicit_free_model_selection_preserves_declared_order_and_fails_closed():
    models = [
        ModelSpec("free/a", "openrouter", CostTier.FREE),
        ModelSpec("paid/x", "openrouter", CostTier.PAID),
        ModelSpec("free/b", "openrouter", CostTier.FREE),
    ]
    selected = _select_explicit_free_models(models, ["free/b", "free/a", "free/b"])
    assert [model.model_id for model in selected] == ["free/b", "free/a"]

    try:
        _select_explicit_free_models(models, ["free/missing"])
    except SystemExit as exc:
        assert "not currently free/available" in str(exc)
    else:
        raise AssertionError("missing explicit free model was accepted")


def test_study_next_refuses_before_discovery_when_daily_budget_cannot_cover_cell(
    tmp_path: Path, capsys,
):
    db = tmp_path / "experiments.sqlite3"
    args = SimpleNamespace(
        db=db, study_catalogue=ROOT / "config" / "studies-v2.json",
        study_id="weak-model-orchestration-v2", daily_remote_limit=0,
        free_model=["thinkingmachines/inkling-small:free"], execute=False,
    )
    assert study_next(args) == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "BUDGET_WAIT"
    assert payload["worst_case_remote_calls"] == 1
    store = ExperimentStore(db)
    try:
        assert store.experiment_ids() == set()
        assert store.remote_calls_today() == 0
    finally:
        store.close()


def test_study_next_reports_one_ready_deterministic_cell_without_executing(
    tmp_path: Path, capsys,
):
    db = tmp_path / "experiments.sqlite3"
    args = SimpleNamespace(
        db=db, study_catalogue=ROOT / "config" / "studies-v2.json",
        study_id="weak-model-orchestration-v2", daily_remote_limit=20,
        free_model=["thinkingmachines/inkling-small:free"], execute=False,
    )
    assert study_next(args) == 0
    payload = json.loads(capsys.readouterr().out)
    expected = expand_study_cells(
        ROOT / "config" / "studies-v2.json", "weak-model-orchestration-v2",
    )[0]
    assert payload["status"] == "READY"
    assert payload["experiment_id"] == expected.experiment_id
    assert payload["repeat_index"] == 1


def test_workload_catalogue_covers_requested_background_work():
    profiles = load_profiles(ROOT / "config" / "workloads.json")
    ids = {profile.id for profile in profiles}
    assert {
        "test-generation", "bug-hunt", "technical-debt", "refactoring", "documentation",
        "codebase-research", "architecture-map", "code-review", "security-review",
        "dependency-config-audit", "alternative-implementation", "legacy-reaudit",
        "frontier-context-preparation", "model-benchmark", "free-window-harvest",
    }.issubset(ids)
    assert all(profile.objective_gate for profile in profiles)


def test_controlled_study_catalogue_has_locked_ablation_and_tradeoff_arms():
    path = ROOT / "config" / "studies.json"
    assert study_catalogue_hash(path) == "23abca74b47971c508d2310960a68357b0a6ac1a5ae617df0a54a37f671cfb2f"
    studies = {study.id: study for study in load_studies(path)}
    assert set(studies) == {
        "weak-model-orchestration-v1", "free-ensemble-vs-frontier-v1", "cheap-attempt-pareto-v1",
    }
    weak = studies["weak-model-orchestration-v1"]
    assert {arm.id for arm in weak.arms} == {
        "single-shot-no-memory", "repair-no-memory", "repair-with-memory", "ensemble-with-critics",
    }
    _, frontier = resolve_study_arm(
        path, "free-ensemble-vs-frontier-v1", "paid-frontier-single-shot",
    )
    assert frontier.cost_tier == CostTier.PAID
    assert frontier.max_rounds == 1 and not frontier.use_experience


def test_superseding_comparative_studies_use_strong_benchmark_and_fit_daily_budget():
    path = ROOT / "config" / "studies-comparative-v2.json"
    assert study_catalogue_hash(path) == "42642ae140495c1fcb20a56e19dc8bc0752cbaa8fa8c5f41fd099bc67f86eb24"
    studies = {study.id: study for study in load_studies(path)}
    assert set(studies) == {"free-ensemble-vs-frontier-v2", "cheap-attempt-pareto-v2"}
    assert all(study.benchmark_id == "fabric-json-test-plan-002" for study in studies.values())
    assert not unschedulable_study_cells(path, "free-ensemble-vs-frontier-v2", 40)
    assert not unschedulable_study_cells(path, "cheap-attempt-pareto-v2", 40)

    ensemble_cells = expand_study_cells(path, "free-ensemble-vs-frontier-v2")
    assert {cell.worst_case_remote_calls for cell in ensemble_cells} == {1, 36}
    pareto = expand_study_cells(path, "cheap-attempt-pareto-v2")
    arm_budgets = {}
    for cell in pareto:
        arm_budgets.setdefault(cell.arm_id, cell.worst_case_remote_calls)
    assert arm_budgets == {
        "free-one-attempt": 1,
        "free-four-attempts": 4,
        "free-twelve-attempts": 12,
        "paid-frontier-one-attempt": 1,
    }


def test_study_budget_audit_exposes_unschedulable_cells_without_altering_contract():
    path = ROOT / "config" / "studies-v2.json"
    blocked = unschedulable_study_cells(path, "weak-model-orchestration-v2", 20)
    assert len(blocked) == 3
    assert {cell.arm_id for cell in blocked} == {"ensemble-with-critics"}
    assert not unschedulable_study_cells(path, "weak-model-orchestration-v2", 40)


def test_model_observations_preserve_preview_and_capabilities(tmp_path: Path):
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        store.observe_models([
            ModelSpec("preview/free", "openrouter", CostTier.FREE, preview=True, capabilities=frozenset({"text", "image"}))
        ])
        assert store.latest_model_ids("free") == {"preview/free"}
        row = store.connection.execute(
            "SELECT cost_tier,preview,capabilities_json FROM model_observations WHERE model_id='preview/free'"
        ).fetchone()
        assert row[0] == "free"
        assert row[1] == 1
        assert json.loads(row[2]) == ["image", "text"]
        assert store.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        store.close()


def test_model_window_diff_and_durable_events(tmp_path: Path):
    previous = [
        ModelSpec("free/closed", "openrouter", CostTier.FREE, preview=True),
        ModelSpec("paid/becomes-free", "openrouter", CostTier.PAID),
    ]
    current = [
        ModelSpec("free/opened", "openrouter", CostTier.FREE, preview=True),
        ModelSpec("paid/becomes-free", "openrouter", CostTier.FREE),
    ]
    changes = model_window_diff(previous, current)
    assert changes == {
        "newly_free": ["free/opened", "paid/becomes-free"],
        "no_longer_free": ["free/closed"],
        "preview_opened": ["free/opened"],
        "preview_closed": ["free/closed"],
    }
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        assert store.record_catalogue_events(changes) == 5
        assert store.connection.execute("SELECT count(*) FROM catalogue_events").fetchone()[0] == 5
        store.observe_models(previous)
        store.observe_models(current)
        assert {model.model_id for model in store.latest_models()} == {"free/opened", "paid/becomes-free"}
    finally:
        store.close()


def test_background_queue_is_idempotent_bounded_and_leased_once(tmp_path: Path):
    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        kwargs = dict(
            work_id="work-1", idempotency_key="same-job", project="orchestrator-v3",
            workload="bug-hunt", objective="find a reproducible bug", prompt="inspect bounded files",
            context="", evaluator={"required": ["reproducer"], "forbidden": []}, max_attempts=1,
        )
        assert store.enqueue(**kwargs)
        assert not store.enqueue(**{**kwargs, "work_id": "work-duplicate"})
        leased = store.lease_next()
        assert leased and leased["work_id"] == "work-1" and leased["status"] == "LEASED"
        store.finish_work("work-1", verified=False, experiment_id="exp-1")
        status = store.connection.execute("SELECT status FROM work_queue WHERE work_id='work-1'").fetchone()[0]
        assert status == "EXHAUSTED"
        assert store.lease_next() is None
    finally:
        store.close()


def test_command_evaluator_uses_candidate_artifact_and_real_exit_code(tmp_path: Path):
    candidate = Candidate(
        "candidate-1", "experiment-1", 1, "test-first",
        Completion("EXPECTED CONTENT", "fixture", "fake"), "hash",
    )
    command = (
        "python3", "-c",
        "import os,pathlib,sys; sys.exit(0 if pathlib.Path(os.environ['GIGA_CANDIDATE_PATH']).read_text() == 'EXPECTED CONTENT' else 1)",
    )
    result = CommandEvaluator((command,), tmp_path).evaluate(candidate)
    assert result.passed
    assert result.score == 1.0
    assert result.checks[0]["exit_code"] == 0


def test_versioned_composite_contract_runs_text_and_command_gates(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-reach-objective-gate")
    candidate = Candidate(
        "candidate-1", "experiment-1", 1, "test-first",
        Completion("EXPECTED CONTENT", "fixture", "fake"), "hash",
    )
    contract = {
        "schema": "giga.evaluator-contract.v1",
        "required": ["EXPECTED"],
        "forbidden": ["FORBIDDEN"],
        "commands": [[
            "python3", "-c",
            "import os,sys; sys.exit(0 if 'OPENROUTER_API_KEY' not in os.environ else 1)",
        ]],
        "cwd": str(tmp_path),
        "timeout_seconds": 10,
    }
    result = evaluator_from_contract(contract).evaluate(candidate)
    assert result.passed
    assert len(result.checks) == 1


def test_evaluator_contract_rejects_unknown_fields_and_missing_cwd():
    try:
        evaluator_from_contract({"schema": "giga.evaluator-contract.v1", "required": ["x"], "extra": True})
    except ValueError as exc:
        assert "unknown evaluator" in str(exc)
    else:
        raise AssertionError("unknown fields must fail closed")

    try:
        evaluator_from_contract({"schema": "giga.evaluator-contract.v1", "commands": [["true"]]})
    except ValueError as exc:
        assert "requires cwd" in str(exc)
    else:
        raise AssertionError("command gate without a working directory must fail closed")


def test_benchmark_binding_detects_fixture_drift_and_registry_is_immutable(tmp_path: Path):
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    source = fixture / "case.txt"
    source.write_text("locked", encoding="utf-8")
    binding = build_benchmark_contract(str(fixture), "python3 verify.py")
    evaluator_contract = verify_benchmark_contract(binding)
    assert evaluator_contract["commands"] == [["python3", "verify.py"]]
    cache = fixture / "__pycache__"
    cache.mkdir()
    (cache / "verify.cpython-314.pyc").write_bytes(b"runtime cache")
    assert verify_benchmark_contract(binding)["commands"] == [["python3", "verify.py"]]

    store = ExperimentStore(tmp_path / "experiments.sqlite3")
    try:
        metadata = {"binding": binding}
        assert store.register_benchmark(
            "bench-1", "project", "bug-hunt", "objective", str(fixture),
            "python3 verify.py", metadata,
        )
        assert not store.register_benchmark(
            "bench-1", "project", "bug-hunt", "objective", str(fixture),
            "python3 verify.py", metadata,
        )
        try:
            store.register_benchmark(
                "bench-1", "other", "bug-hunt", "objective", str(fixture),
                "python3 verify.py", metadata,
            )
        except ValueError as exc:
            assert "immutable" in str(exc)
        else:
            raise AssertionError("benchmark ID must not be silently rebound")
    finally:
        store.close()

    source.write_text("drifted", encoding="utf-8")
    try:
        verify_benchmark_contract(binding)
    except ValueError as exc:
        assert "fixture drift" in str(exc)
    else:
        raise AssertionError("changed benchmark fixture must fail closed")


def test_local_openai_compatible_model_discovery(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        @staticmethod
        def read():
            return json.dumps({
                "data": [
                    {"id": "local/b", "owned_by": "operator"},
                    {"id": "local/a", "owned_by": "operator"},
                ]
            }).encode("utf-8")

    monkeypatch.setattr(
        "giga_inference_fabric.providers.urllib.request.urlopen",
        lambda _request, timeout: Response(),
    )
    models = discover_local_models("http://127.0.0.1:11434/v1")
    assert [model.model_id for model in models] == ["local/a", "local/b"]
    assert all(model.cost_tier == CostTier.LOCAL and model.adapter == "local" for model in models)


def test_openai_compatible_adapter_prefers_final_content_and_labels_reasoning_fallback(
    monkeypatch,
):
    responses = iter([
        ({
            "model": "local/reasoner", "choices": [{
                "message": {"content": "FINAL", "reasoning": "PRIVATE DRAFT"},
                "finish_reason": "stop",
            }],
        }, 12),
        ({
            "model": "local/reasoner", "choices": [{
                "message": {"content": "", "reasoning": "ONLY REASONING"},
                "finish_reason": "length",
            }],
        }, 34),
    ])
    monkeypatch.setattr(
        "giga_inference_fabric.providers._post_json", lambda *_args, **_kwargs: next(responses),
    )
    adapter = OpenAICompatibleAdapter("local", "http://127.0.0.1:9999/v1")
    model = ModelSpec("local/reasoner", "local", CostTier.LOCAL)

    final = adapter.complete(model, system="system", prompt="prompt")
    assert final.text == "FINAL"
    assert final.raw["text_source"] == "content"

    fallback = adapter.complete(model, system="system", prompt="prompt")
    assert fallback.text == "ONLY REASONING"
    assert fallback.raw["text_source"] == "reasoning_fallback"
    assert fallback.raw["finish_reason"] == "length"


def test_openai_compatible_adapter_rejects_truly_empty_completion(monkeypatch):
    monkeypatch.setattr(
        "giga_inference_fabric.providers._post_json",
        lambda *_args, **_kwargs: ({"choices": [{"message": {"content": " "}}]}, 1),
    )
    adapter = OpenAICompatibleAdapter("local", "http://127.0.0.1:9999/v1")
    try:
        adapter.complete(ModelSpec("local/empty", "local", CostTier.LOCAL), system="s", prompt="p")
    except ProviderError as exc:
        assert "no reasoning fallback" in str(exc)
    else:
        raise AssertionError("empty local completion was accepted")


def test_opencode_adapter_parses_zero_cost_events_without_accessing_a_key(monkeypatch):
    class Result:
        returncode = 0
        stdout = "\n".join([
            json.dumps({"type": "text", "part": {"text": "READY"}}),
            json.dumps({
                "type": "step_finish",
                "part": {"cost": 0, "tokens": {"input": 10, "output": 1, "reasoning": 2}},
            }),
        ])

    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr("giga_inference_fabric.providers.subprocess.run", fake_run)
    completion = OpenCodeOpenRouterAdapter(binary="/usr/local/bin/opencode").complete(
        ModelSpec("free/model", "opencode-openrouter", CostTier.FREE),
        system="system", prompt="prompt", max_output_tokens=100,
    )
    assert completion.text == "READY"
    assert completion.cost_usd == 0
    assert completion.prompt_tokens == 10 and completion.completion_tokens == 3
    assert "--pure" in observed["command"] and "--dir" in observed["command"]
    assert "OPENROUTER_API_KEY" not in " ".join(observed["command"])
    assert observed["kwargs"]["check"] is False


def test_opencode_adapter_rejects_paid_models_before_execution(monkeypatch):
    called = False

    def fake_run(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("giga_inference_fabric.providers.subprocess.run", fake_run)
    try:
        OpenCodeOpenRouterAdapter(binary="opencode").complete(
            ModelSpec("paid/model", "opencode-openrouter", CostTier.PAID),
            system="system", prompt="prompt",
        )
    except ProviderError as exc:
        assert "restricted to free-tier" in str(exc)
    else:
        raise AssertionError("paid model must be rejected before OpenCode execution")
    assert not called


def test_committed_live_transport_evidence_is_self_consistent_and_secret_free():
    evidence_path = ROOT / "evidence" / "live-free-transport-2026-08-24.json"
    raw = evidence_path.read_text(encoding="utf-8")
    evidence = json.loads(raw)
    assert evidence["schema"] == "giga.live-free-transport-evidence.v1"
    assert evidence["status"] == "VERIFIED"
    assert evidence["provider_reported_cost_usd"] == 0.0
    assert evidence["gate"]["passed"] is True
    assert hashlib.sha256(evidence["output"].encode("utf-8")).hexdigest() == evidence["output_sha256"]
    assert "sk-or-" not in raw and "OPENROUTER_API_KEY=" not in raw

    comparison_raw = (
        ROOT / "evidence" / "live-benchmark-comparison-2026-08-24.json"
    ).read_text(encoding="utf-8")
    comparison = json.loads(comparison_raw)
    assert comparison["verdict"] == "VERIFIED_DIFFERENTIAL_UTILITY"
    assert comparison["winner"]["verified_candidates"] == 1
    assert comparison["comparison"]["verified_candidates"] == 0
    assert comparison["batch"]["provider_reported_total_cost_usd"] == 0.0
    assert "sk-or-" not in comparison_raw and "OPENROUTER_API_KEY=" not in comparison_raw

    local_raw = (
        ROOT / "evidence" / "live-local-negative-results-2026-08-24.json"
    ).read_text(encoding="utf-8")
    local = json.loads(local_raw)
    assert local["verdict"] == "LOCAL_TRANSPORT_PROVEN_MODEL_UTILITY_NOT_PROVEN"
    assert local["remote_calls"] == 0
    assert not any(result["status"] == "VERIFIED" for result in local["results"])
    assert "sk-or-" not in local_raw and "OPENROUTER_API_KEY=" not in local_raw

    supersession_raw = (
        ROOT / "evidence" / "benchmark-v1-cross-critic-supersession-2026-08-24.json"
    ).read_text(encoding="utf-8")
    supersession = json.loads(supersession_raw)
    assert supersession["false_positive"]["old_gate_verdict"] == "PASS"
    assert len(supersession["false_positive"]["independent_critic_evidence"]) == 2
    assert supersession["superseding_benchmark"]["benchmark_id"] == "fabric-json-test-plan-002"
    assert "SUPERSEDED" in supersession["verdict"]
    assert "sk-or-" not in supersession_raw and "OPENROUTER_API_KEY=" not in supersession_raw

    baseline_raw = (
        ROOT / "evidence" / "live-study-v2-baseline-2026-08-24.json"
    ).read_text(encoding="utf-8")
    baseline = json.loads(baseline_raw)
    assert baseline["verdict"] == "VERIFIED_SINGLE_SHOT_NO_MEMORY_BASELINE"
    assert baseline["experience_enabled"] is False
    assert baseline["candidates"] == 1 and baseline["critics"] == 0
    assert baseline["objective_gate"]["exit_code"] == 0
    assert "sk-or-" not in baseline_raw and "OPENROUTER_API_KEY=" not in baseline_raw


def test_bundled_real_benchmark_accepts_valid_plan_and_rejects_false_control():
    fixture = ROOT / "benchmarks" / "fabric-json-test-plan-001"
    evaluator = CommandEvaluator((("python3", "verify_candidate.py"),), fixture)
    valid = Candidate(
        "valid", "exp", 1, "test-first",
        Completion(json.dumps({
            "schema": "giga.test-plan.v1",
            "tests": [
                {"id": "p1", "kind": "positive", "input": "valid", "expected": "accept"},
                {"id": "n1", "kind": "negative_control", "input": "invalid", "expected": "reject"},
            ],
        }), "fixture", "fake"), "hash",
    )
    assert evaluator.evaluate(valid).passed

    invalid = Candidate(
        "invalid", "exp", 1, "test-first",
        Completion(json.dumps({
            "schema": "giga.test-plan.v1",
            "tests": [
                {"id": "p1", "kind": "positive", "input": "valid", "expected": "accept"},
                {"id": "n1", "kind": "negative_control", "input": "invalid", "expected": "accept"},
            ],
        }), "fixture", "fake"), "hash",
    )
    result = evaluator.evaluate(invalid)
    assert not result.passed
    assert "negative control" in result.checks[0]["output"]


def test_v2_benchmark_rejects_cross_critic_false_positive_and_vague_outcomes():
    fixture = ROOT / "benchmarks" / "fabric-json-test-plan-002"
    evaluator = CommandEvaluator((("python3", "verify_candidate.py"),), fixture)
    same_input = Candidate(
        "same-input", "exp", 1, "test-first",
        Completion(json.dumps({
            "schema": "giga.test-plan.v1",
            "tests": [
                {"id": "p1", "kind": "positive", "input": "same", "expected": "accepted"},
                {"id": "n1", "kind": "negative_control", "input": "same", "expected": "rejected"},
            ],
        }), "fixture", "fake"), "hash",
    )
    result = evaluator.evaluate(same_input)
    assert not result.passed
    assert "disjoint" in result.checks[0]["output"]

    vague = Candidate(
        "vague", "exp", 1, "test-first",
        Completion(json.dumps({
            "schema": "giga.test-plan.v1",
            "tests": [
                {"id": "p1", "kind": "positive", "input": "valid", "expected": "above baseline"},
                {"id": "n1", "kind": "negative_control", "input": "invalid", "expected": "should reject"},
            ],
        }), "fixture", "fake"), "hash",
    )
    assert not evaluator.evaluate(vague).passed

    valid = Candidate(
        "valid-v2", "exp", 1, "test-first",
        Completion(json.dumps({
            "schema": "giga.test-plan.v1",
            "tests": [
                {"id": "p1", "kind": "positive", "input": "valid", "expected": "accepted"},
                {"id": "n1", "kind": "negative_control", "input": "invalid", "expected": "error INVALID_INPUT"},
            ],
        }), "fixture", "fake"), "hash",
    )
    assert evaluator.evaluate(valid).passed

    v2_path = ROOT / "config" / "studies-v2.json"
    assert study_catalogue_hash(v2_path) == "f6e66e2b9cb392996004c7ddbc670cde2d87df338a59d51e34654f58f8cf6c8c"
    study, arm = resolve_study_arm(v2_path, "weak-model-orchestration-v2", "ensemble-with-critics")
    assert study.benchmark_id == "fabric-json-test-plan-002"
    assert arm.min_distinct_models == 3

    cells = expand_study_cells(v2_path, "weak-model-orchestration-v2")
    assert len(cells) == 12
    ensemble = next(cell for cell in cells if cell.arm_id == "ensemble-with-critics")
    assert ensemble.worst_case_remote_calls == 36
    assert next_pending_study_cell(v2_path, "weak-model-orchestration-v2", set()) == cells[0]
    assert next_pending_study_cell(
        v2_path, "weak-model-orchestration-v2", {cells[0].experiment_id},
    ) == cells[1]
