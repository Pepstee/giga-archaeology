from __future__ import annotations

import argparse
import json
import os
import hashlib
import shlex
import uuid
from dataclasses import asdict
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from .benchmarks import build_benchmark_contract, verify_benchmark_contract
from .catalogue import harvest_targets, load_profiles, model_window_diff
from .engine import ExperimentEngine
from .evaluators import evaluator_from_contract
from .models import CostTier, ExperimentRequest, ModelPolicy, ModelSpec, PrivacyClass
from .providers import (
    discover_local_models,
    discover_openrouter_models,
    local_adapter,
    OpenCodeOpenRouterAdapter,
    openrouter_adapter,
)
from .store import ExperimentStore
from .studies import (
    expand_study_cells,
    load_studies,
    next_pending_study_cell,
    resolve_study_arm,
    study_catalogue_hash,
    study_experiment_id,
    unschedulable_study_cells,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "state" / "experiments.sqlite3"
DEFAULT_PROFILES = ROOT / "config" / "workloads.json"
DEFAULT_STUDIES = ROOT / "config" / "studies.json"


def _evaluator_contract(args: argparse.Namespace) -> dict:
    commands = [shlex.split(command) for command in getattr(args, "check_command", [])]
    if any(not command for command in commands):
        raise SystemExit("--check-command cannot be empty")
    cwd = getattr(args, "evaluator_cwd", None)
    if commands and cwd is None:
        raise SystemExit("--check-command requires --evaluator-cwd")
    required = list(args.require)
    forbidden = list(args.forbid)
    if not required and not forbidden and not commands:
        required = [r"."]
    contract = {
        "schema": "giga.evaluator-contract.v1",
        "required": required,
        "forbidden": forbidden,
        "commands": commands,
        "cwd": str(cwd.resolve(strict=True)) if cwd is not None else None,
        "timeout_seconds": getattr(args, "command_timeout", 300),
    }
    # Compile at admission time so malformed or unavailable gates never poison the queue.
    evaluator_from_contract(contract)
    return contract


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (set, frozenset, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _select_explicit_free_models(
    models: list[ModelSpec], requested_ids: list[str],
) -> list[ModelSpec]:
    """Select available free models in operator-declared order, failing closed on drift."""
    free_by_id = {
        model.model_id: model for model in models if model.cost_tier == CostTier.FREE
    }
    if not requested_ids:
        return list(free_by_id.values())
    ordered_ids = list(dict.fromkeys(requested_ids))
    missing = [model_id for model_id in ordered_ids if model_id not in free_by_id]
    if missing:
        raise SystemExit(
            "requested model is not currently free/available: " + ", ".join(missing)
        )
    return [free_by_id[model_id] for model_id in ordered_ids]


def _select_explicit_paid_models(
    models: list[ModelSpec], requested_ids: list[str], *, adapter: str | None = None,
) -> list[ModelSpec]:
    """Admit only named models still published as paid, preserving declared order."""
    paid_by_id = {
        model.model_id: model for model in models if model.cost_tier == CostTier.PAID
    }
    ordered_ids = list(dict.fromkeys(requested_ids))
    missing = [model_id for model_id in ordered_ids if model_id not in paid_by_id]
    if missing:
        raise SystemExit(
            "requested paid model is absent from the live paid catalogue: " + ", ".join(missing)
        )
    selected = [paid_by_id[model_id] for model_id in ordered_ids]
    return [replace(model, adapter=adapter) for model in selected] if adapter else selected


def discover(args: argparse.Namespace) -> int:
    models = discover_openrouter_models()
    free = [model for model in models if model.cost_tier == CostTier.FREE]
    store = ExperimentStore(args.db)
    try:
        previous_free = store.latest_model_ids("free")
        store.observe_models(models)
    finally:
        store.close()
    current_free = {model.model_id for model in free}
    payload = {
        "observed": len(models),
        "free": len(free),
        "preview_free": [model.model_id for model in free if model.preview],
        "newly_free_since_previous_snapshot": sorted(current_free - previous_free) if previous_free else [],
        "no_longer_free_since_previous_snapshot": sorted(previous_free - current_free) if previous_free else [],
        "free_models": [_jsonable(model) for model in free],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def discover_local(args: argparse.Namespace) -> int:
    models = discover_local_models(args.local_base_url)
    print(json.dumps({
        "observed": len(models), "models": [_jsonable(model) for model in models],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def monitor_once(args: argparse.Namespace) -> int:
    current = discover_openrouter_models()
    store = ExperimentStore(args.db)
    try:
        previous = store.latest_models()
        changes = model_window_diff(previous, current) if previous else {
            "newly_free": [], "no_longer_free": [], "preview_opened": [], "preview_closed": [],
        }
        store.observe_models(current)
        event_count = store.record_catalogue_events(changes)
    finally:
        store.close()
    payload = {
        "schema": "giga.model-window-monitor-receipt.v1",
        "observed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "baseline_created": not bool(previous),
        "observed_models": len(current),
        "free_models": sum(model.cost_tier == CostTier.FREE for model in current),
        "changes": changes,
        "event_count": event_count,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 10 if event_count else 0


def profiles(args: argparse.Namespace) -> int:
    rows = load_profiles(args.profiles)
    print(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2))
    return 0


def studies(args: argparse.Namespace) -> int:
    rows = load_studies(args.study_catalogue)
    print(json.dumps(_jsonable(rows), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def study_plan(args: argparse.Namespace) -> int:
    rows = load_studies(args.study_catalogue)
    selected = [study for study in rows if study.id == args.study_id]
    if not selected:
        raise SystemExit(f"unknown study: {args.study_id}")
    study = selected[0]
    expanded = {
        (cell.arm_id, cell.repeat_index): cell for cell in expand_study_cells(args.study_catalogue, study.id)
    }
    cells = []
    for arm in study.arms:
        for repeat in range(1, arm.repeats + 1):
            cell = expanded[(arm.id, repeat)]
            cells.append({
                "study_id": study.id, "arm_id": arm.id, "repeat_index": repeat,
                "benchmark_id": study.benchmark_id, "experiment_id": cell.experiment_id,
                "worst_case_remote_calls": cell.worst_case_remote_calls,
                "cost_tier": arm.cost_tier.value,
                "candidates_per_round": arm.candidates_per_round,
                "critics_per_candidate": arm.critics_per_candidate,
                "min_distinct_models": arm.min_distinct_models,
                "max_rounds": arm.max_rounds, "use_experience": arm.use_experience,
                "schedulable_within_daily_limit": (
                    cell.worst_case_remote_calls <= args.daily_remote_limit
                ),
            })
    unschedulable = unschedulable_study_cells(
        args.study_catalogue, study.id, args.daily_remote_limit,
    )
    print(json.dumps({
        "schema": "giga.study-plan.v1", "study_id": study.id,
        "study_contract_sha256": study_catalogue_hash(args.study_catalogue),
        "question": study.question, "daily_remote_limit": args.daily_remote_limit,
        "unschedulable_cells": [cell.experiment_id for cell in unschedulable],
        "cells": cells,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def study_scoreboard(args: argparse.Namespace) -> int:
    store = ExperimentStore(args.db)
    try:
        rows = store.study_scoreboard(args.study_id)
    finally:
        store.close()
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _load_registered_benchmark(
    store: ExperimentStore, benchmark_id: str,
) -> tuple[dict, dict, dict]:
    try:
        benchmark = store.get_benchmark(benchmark_id)
    except KeyError as exc:
        raise SystemExit(f"unknown or inactive benchmark: {benchmark_id}") from exc
    metadata = json.loads(benchmark["metadata_json"])
    binding = metadata.get("binding")
    if not isinstance(binding, dict):
        raise SystemExit("benchmark has no immutable v1 binding")
    try:
        verify_benchmark_contract(binding)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    manifest_path = Path(benchmark["fixture_ref"]) / "benchmark.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("benchmark_id") != benchmark["benchmark_id"]
        or manifest.get("objective") != benchmark["objective"]
        or manifest.get("workload") != benchmark["workload"]
        or not isinstance(manifest.get("prompt"), str)
    ):
        raise SystemExit("benchmark manifest does not match its immutable registration")
    return benchmark, manifest, binding


def study_next(args: argparse.Namespace) -> int:
    store = ExperimentStore(args.db)
    try:
        try:
            cell = next_pending_study_cell(
                args.study_catalogue, args.study_id, store.experiment_ids(),
            )
        except KeyError as exc:
            raise SystemExit(str(exc)) from exc
        used_today = store.remote_calls_today()
        if cell is None:
            print(json.dumps({
                "schema": "giga.study-next.v1", "study_id": args.study_id,
                "status": "COMPLETE", "remote_calls_today": used_today,
            }, indent=2, sort_keys=True))
            return 0
        study, arm = resolve_study_arm(args.study_catalogue, cell.study_id, cell.arm_id)
        remaining = max(0, args.daily_remote_limit - used_today)
        payload = {
            "schema": "giga.study-next.v1", "study_id": cell.study_id,
            "study_arm_id": cell.arm_id, "repeat_index": cell.repeat_index,
            "experiment_id": cell.experiment_id, "benchmark_id": cell.benchmark_id,
            "cost_tier": arm.cost_tier.value,
            "worst_case_remote_calls": cell.worst_case_remote_calls,
            "remote_calls_today": used_today, "daily_remote_limit": args.daily_remote_limit,
            "remaining_remote_calls": remaining,
        }
        if cell.worst_case_remote_calls > remaining:
            payload["status"] = "BUDGET_WAIT"
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 4
        if arm.cost_tier == CostTier.FREE and len(dict.fromkeys(args.free_model)) < arm.min_distinct_models:
            raise SystemExit(
                f"next arm requires {arm.min_distinct_models} explicit distinct --free-model values"
            )
        if not args.execute:
            payload["status"] = "READY"
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        benchmark, manifest, _binding = _load_registered_benchmark(store, study.benchmark_id)
    finally:
        store.close()

    run_args = argparse.Namespace(
        db=args.db, objective=benchmark["objective"], prompt=manifest["prompt"], context="",
        workload=benchmark["workload"], benchmark_id=study.benchmark_id,
        study_id=study.id, study_arm=arm.id, repeat_index=cell.repeat_index,
        study_catalogue=args.study_catalogue, no_experience=False,
        require=[], forbid=[], check_command=[], evaluator_cwd=None, command_timeout=300,
        candidates=arm.candidates_per_round, critics=arm.critics_per_candidate,
        min_distinct_models=arm.min_distinct_models, rounds=arm.max_rounds,
        max_remote_calls=cell.worst_case_remote_calls, daily_remote_limit=args.daily_remote_limit,
        max_output_tokens=args.max_output_tokens, stagnation_rounds=2,
        privacy=args.privacy, require_zdr=args.require_zdr, local_only=False,
        use_opencode_auth=args.use_opencode_auth, free_model=args.free_model,
        local_model=[], local_base_url="http://127.0.0.1:11434/v1",
        include_paid=args.include_paid, paid_model=args.paid_model,
        max_cost_usd=args.max_cost_usd,
        output=args.output_dir / cell.study_id / f"{cell.arm_id}-r{cell.repeat_index}.json",
    )
    return run(run_args)


def harvest_next(args: argparse.Namespace) -> int:
    """Select and optionally benchmark one unmeasured free model; preview models come first."""
    store = ExperimentStore(args.db)
    try:
        benchmark, manifest, binding = _load_registered_benchmark(store, args.benchmark_id)
        models = store.latest_models()
        if not models:
            print(json.dumps({
                "schema": "giga.free-window-harvest.v1", "status": "NO_SNAPSHOT",
                "benchmark_id": args.benchmark_id,
            }, indent=2, sort_keys=True))
            return 3
        targets = harvest_targets(
            models, binding, max_rounds=args.rounds,
            excluded_model_ids=store.benchmark_attempted_model_ids(args.benchmark_id),
            claimed_experiment_ids=store.experiment_ids(),
        )
        used_today = store.remote_calls_today()
        if not targets:
            print(json.dumps({
                "schema": "giga.free-window-harvest.v1", "status": "COMPLETE",
                "benchmark_id": args.benchmark_id, "remote_calls_today": used_today,
            }, indent=2, sort_keys=True))
            return 0
        target = targets[0]
        remaining = max(0, args.daily_remote_limit - used_today)
        payload = {
            "schema": "giga.free-window-harvest.v1", "benchmark_id": args.benchmark_id,
            "model_id": target.model_id, "preview": target.preview,
            "experiment_id": target.experiment_id, "worst_case_remote_calls": args.rounds,
            "remote_calls_today": used_today, "daily_remote_limit": args.daily_remote_limit,
            "remaining_remote_calls": remaining,
        }
        if args.rounds > remaining:
            payload["status"] = "BUDGET_WAIT"
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 4
        if not args.execute:
            payload["status"] = "READY"
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
    finally:
        store.close()

    run_args = argparse.Namespace(
        db=args.db, objective=benchmark["objective"], prompt=manifest["prompt"], context="",
        workload=benchmark["workload"], benchmark_id=args.benchmark_id,
        study_id=None, study_arm=None, repeat_index=None, study_catalogue=DEFAULT_STUDIES,
        experiment_id=target.experiment_id, no_experience=True,
        require=[], forbid=[], check_command=[], evaluator_cwd=None, command_timeout=300,
        candidates=1, critics=0, min_distinct_models=1, rounds=args.rounds,
        max_remote_calls=args.rounds, daily_remote_limit=args.daily_remote_limit,
        max_output_tokens=args.max_output_tokens, stagnation_rounds=2,
        privacy=args.privacy, require_zdr=args.require_zdr, local_only=False,
        use_opencode_auth=args.use_opencode_auth, free_model=[target.model_id],
        local_model=[], local_base_url="http://127.0.0.1:11434/v1",
        include_paid=False, paid_model=[], max_cost_usd=0.0,
        output=args.output_dir / args.benchmark_id / f"{target.experiment_id}.json",
    )
    return run(run_args)


def _bind_study_arm(args: argparse.Namespace) -> tuple[object | None, str | None, str | None]:
    if not args.study_id and not args.study_arm:
        return None, None, None
    if not args.study_id or not args.study_arm or args.repeat_index is None:
        raise SystemExit("study runs require --study-id, --study-arm and --repeat-index")
    try:
        study, arm = resolve_study_arm(args.study_catalogue, args.study_id, args.study_arm)
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    if args.repeat_index < 1 or args.repeat_index > arm.repeats:
        raise SystemExit(f"repeat index must be between 1 and {arm.repeats}")
    if args.benchmark_id and args.benchmark_id != study.benchmark_id:
        raise SystemExit("study arm benchmark cannot be overridden")
    args.benchmark_id = study.benchmark_id
    args.candidates = arm.candidates_per_round
    args.critics = arm.critics_per_candidate
    args.min_distinct_models = arm.min_distinct_models
    args.rounds = arm.max_rounds
    args.no_experience = not arm.use_experience
    if arm.cost_tier == CostTier.PAID and not args.include_paid:
        raise SystemExit("paid study arm requires explicit --include-paid admission and cost budget")
    if arm.cost_tier == CostTier.FREE and args.include_paid:
        raise SystemExit("free study arm cannot include paid models")
    contract_hash = study_catalogue_hash(args.study_catalogue)
    return arm, study_experiment_id(
        contract_hash, study.id, arm.id, args.repeat_index, study.benchmark_id,
    ), contract_hash


def benchmark_register(args: argparse.Namespace) -> int:
    binding = build_benchmark_contract(args.fixture_ref, args.evaluator_ref)
    store = ExperimentStore(args.db)
    try:
        inserted = store.register_benchmark(
            args.benchmark_id, args.project, args.workload, args.objective,
            binding["fixture_ref"], args.evaluator_ref,
            {"notes": args.notes, "binding": binding},
        )
    finally:
        store.close()
    print(json.dumps({
        "registered": args.benchmark_id, "inserted": inserted,
        "fixture_sha256": binding["fixture_sha256"],
        "evaluator_sha256": binding["evaluator_sha256"],
    }, indent=2))
    return 0


def scoreboard(args: argparse.Namespace) -> int:
    store = ExperimentStore(args.db)
    try:
        rows = store.scoreboard(args.benchmark_id)
    finally:
        store.close()
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def queue_add(args: argparse.Namespace) -> int:
    idempotency_key = args.idempotency_key or hashlib.sha256(
        f"{args.project}\0{args.workload}\0{args.objective}\0{args.prompt}".encode("utf-8")
    ).hexdigest()
    work_id = args.work_id or f"work-{uuid.uuid4().hex}"
    store = ExperimentStore(args.db)
    try:
        inserted = store.enqueue(
            work_id=work_id, idempotency_key=idempotency_key, project=args.project,
            workload=args.workload, objective=args.objective, prompt=args.prompt,
            context=args.context, evaluator=_evaluator_contract(args),
            priority=args.priority, max_attempts=args.max_attempts,
        )
    finally:
        store.close()
    print(json.dumps({"work_id": work_id, "inserted": inserted, "idempotency_key": idempotency_key}, indent=2))
    return 0


def queue_next(args: argparse.Namespace) -> int:
    store = ExperimentStore(args.db)
    try:
        item = store.lease_next(args.lease_minutes)
    finally:
        store.close()
    print(json.dumps(item, ensure_ascii=False, indent=2))
    return 0 if item else 3


def queue_finish(args: argparse.Namespace) -> int:
    store = ExperimentStore(args.db)
    try:
        store.finish_work(args.work_id, verified=args.verified, experiment_id=args.experiment_id)
    finally:
        store.close()
    print(json.dumps({"work_id": args.work_id, "verified": args.verified}, indent=2))
    return 0


def escalate(args: argparse.Namespace) -> int:
    """Bind one paid successor to canonical failed evidence; never restart from an empty prompt."""
    if args.source_result.is_symlink() or not args.source_result.is_file():
        raise SystemExit("source result must be a regular non-symlink file")
    source_bytes = args.source_result.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    try:
        source = json.loads(source_bytes)
    except json.JSONDecodeError as exc:
        raise SystemExit("source result is not valid JSON") from exc
    packet = source.get("escalation_packet")
    experiment_id = source.get("experiment_id")
    best_gate = source.get("best_gate")
    if (
        source.get("status") != "UNVERIFIED"
        or not isinstance(packet, dict)
        or packet.get("schema") != "giga.frontier-escalation-packet.v1"
        or packet.get("status") != "UNVERIFIED"
        or packet.get("experiment_id") != experiment_id
        or not isinstance(best_gate, dict)
        or best_gate.get("passed") is not False
    ):
        raise SystemExit("only an objectively UNVERIFIED canonical result may be escalated")
    if args.max_cost_usd <= 0 or args.max_output_tokens < 1 or args.max_output_tokens > 65536:
        raise SystemExit("escalation requires positive bounded cost and output-token admission")
    if not isinstance(packet.get("attempts"), list) or not packet["attempts"]:
        raise SystemExit("escalation source has no failed attempt evidence")
    if not isinstance(packet.get("critiques"), list):
        raise SystemExit("escalation source has malformed critique evidence")

    store = ExperimentStore(args.db)
    try:
        try:
            record = store.experiment_record(experiment_id)
        except KeyError as exc:
            raise SystemExit("source experiment is absent from the canonical database") from exc
        request = json.loads(record["request_json"])
        if (
            record["status"] != "UNVERIFIED"
            or record["objective"] != packet.get("objective")
            or request.get("objective") != record["objective"]
            or request.get("workload") != record["workload"]
            or request.get("benchmark_id") != record["benchmark_id"]
            or packet["attempts"] != store.experiment_attempts(experiment_id)
            or packet["critiques"] != store.experiment_critiques(experiment_id)
        ):
            raise SystemExit("source result drifted from canonical experiment evidence")
        benchmark_id = record["benchmark_id"]
        if not benchmark_id:
            raise SystemExit("automatic frontier escalation requires an immutable registered benchmark")
        benchmark, manifest, _binding = _load_registered_benchmark(store, benchmark_id)
        successor_id = "escalation-" + hashlib.sha256(
            (
                source_sha256 + "\0" + args.paid_model + "\0" + str(args.max_cost_usd)
                + "\0" + str(args.max_output_tokens)
            ).encode("utf-8")
        ).hexdigest()[:24]
        if store.experiment_exists(successor_id):
            raise SystemExit("deterministic escalation successor already exists")
    finally:
        store.close()

    prompt = (
        "Resolve the remaining objective-gate failures using the complete prior evidence below. "
        "Do not restart analysis from zero and do not claim success; return only the corrected candidate.\n\n"
        "SOURCE RESULT SHA256: " + source_sha256 + "\n"
        "SOURCE EXPERIMENT: " + experiment_id + "\n"
        "ESCALATION PACKET:\n" + json.dumps(packet, ensure_ascii=False, sort_keys=True)
    )
    run_args = argparse.Namespace(
        db=args.db, objective=benchmark["objective"], prompt=prompt,
        context=json.dumps({
            "source_experiment_id": experiment_id,
            "source_result_sha256": source_sha256,
        }, sort_keys=True),
        workload=benchmark["workload"], benchmark_id=benchmark_id,
        study_id=None, study_arm=None, repeat_index=None, study_catalogue=DEFAULT_STUDIES,
        experiment_id=successor_id, no_experience=True,
        require=[], forbid=[], check_command=[], evaluator_cwd=None, command_timeout=300,
        candidates=1, critics=0, min_distinct_models=1, rounds=1,
        max_remote_calls=1, daily_remote_limit=args.daily_remote_limit,
        max_output_tokens=args.max_output_tokens, stagnation_rounds=2,
        privacy=args.privacy, require_zdr=args.require_zdr, local_only=False,
        use_opencode_auth=args.use_opencode_auth, free_model=[], local_model=[],
        local_base_url="http://127.0.0.1:11434/v1", include_paid=True,
        paid_model=[args.paid_model], max_cost_usd=args.max_cost_usd,
        output=args.output_dir / f"{successor_id}.json",
        source_experiment_id=experiment_id, source_result_sha256=source_sha256,
    )
    # The benchmark manifest prompt is intentionally not reused: the frontier receives the prior
    # attempts, objective failures and critiques. The same immutable evaluator remains authoritative.
    assert manifest["benchmark_id"] == benchmark_id
    return run(run_args)


def worker_once(args: argparse.Namespace) -> int:
    """Lease and execute exactly one background item; never become an unbounded daemon."""
    store = ExperimentStore(args.db)
    item = store.lease_next(args.lease_minutes)
    if not item:
        store.close()
        print(json.dumps({"status": "IDLE"}, indent=2))
        return 3
    try:
        evaluator_contract = json.loads(item["evaluator_json"])
        models = [] if args.local_only else _select_explicit_free_models(
            discover_openrouter_models(), args.free_model,
        )
        if args.use_opencode_auth:
            models = [replace(model, adapter="opencode-openrouter") for model in models]
        adapters = {} if args.local_only else (
            {"opencode-openrouter": OpenCodeOpenRouterAdapter()}
            if args.use_opencode_auth else {"openrouter": openrouter_adapter()}
        )
        for model_id in args.local_model:
            models.append(ModelSpec(model_id=model_id, adapter="local", cost_tier=CostTier.LOCAL))
        if args.local_model:
            adapters["local"] = local_adapter(args.local_base_url)
        policy = ModelPolicy(
            allowed_tiers=frozenset({CostTier.FREE, CostTier.LOCAL}),
            allowed_adapters=frozenset(adapters),
            privacy_class=PrivacyClass(args.privacy),
            require_zdr=args.require_zdr,
        )
        request = ExperimentRequest(
            objective=item["objective"], prompt=item["prompt"], workload=item["workload"],
            context=item["context"], candidates_per_round=args.candidates,
            critics_per_candidate=args.critics, max_rounds=args.rounds,
            min_distinct_models=args.min_distinct_models,
            max_remote_calls=args.max_remote_calls, daily_remote_limit=args.daily_remote_limit,
            max_output_tokens=args.max_output_tokens,
            policy=policy,
        )
        evaluator = evaluator_from_contract(evaluator_contract)
        result = ExperimentEngine(adapters=adapters, models=models, store=store).run(request, evaluator)
        store.finish_work(item["work_id"], verified=result.status == "VERIFIED", experiment_id=result.experiment_id)
    except Exception:
        # Preserve the lease until expiry. Another worker can retry only after the bounded lease,
        # and the queue's max_attempts prevents a permanent poison item from looping forever.
        raise
    finally:
        store.close()
    print(json.dumps({
        "work_id": item["work_id"], "experiment_id": result.experiment_id,
        "status": result.status, "stop_reason": result.stop_reason,
    }, ensure_ascii=False, indent=2))
    return 0 if result.status == "VERIFIED" else 2


def run(args: argparse.Namespace) -> int:
    study_arm, study_experiment_id, study_contract_hash = _bind_study_arm(args)
    explicit_experiment_id = getattr(args, "experiment_id", None)
    if study_experiment_id and explicit_experiment_id:
        raise SystemExit("experiment identity cannot override a controlled study cell")
    experiment_id = study_experiment_id or explicit_experiment_id
    if args.include_paid and (not args.paid_model or args.max_cost_usd <= 0):
        raise SystemExit("--include-paid requires at least one --paid-model and a positive --max-cost-usd")
    discovered = discover_openrouter_models() if not args.local_only else []
    models = _select_explicit_free_models(discovered, args.free_model)
    if args.use_opencode_auth:
        models = [replace(model, adapter="opencode-openrouter") for model in models]
    adapters = {}
    if not args.local_only:
        if args.use_opencode_auth:
            adapters["opencode-openrouter"] = OpenCodeOpenRouterAdapter(allow_paid=args.include_paid)
        else:
            adapters["openrouter"] = openrouter_adapter()
    for model_id in args.local_model:
        models.append(ModelSpec(model_id=model_id, adapter="local", cost_tier=CostTier.LOCAL))
    if args.local_model:
        adapters["local"] = local_adapter(args.local_base_url)
    if args.include_paid:
        models.extend(_select_explicit_paid_models(
            discovered, args.paid_model,
            adapter="opencode-openrouter" if args.use_opencode_auth else None,
        ))
    if not models:
        raise SystemExit("no free or local models discovered")
    allowed_tiers = (
        frozenset({study_arm.cost_tier}) if study_arm is not None
        else frozenset({CostTier.FREE, CostTier.LOCAL, *([CostTier.PAID] if args.include_paid else [])})
    )
    policy = ModelPolicy(
        allowed_tiers=allowed_tiers,
        allowed_adapters=frozenset(adapters),
        privacy_class=PrivacyClass(args.privacy),
        require_zdr=args.require_zdr,
        allow_paid_escalation=args.include_paid,
        max_total_cost_usd=args.max_cost_usd,
    )
    request = ExperimentRequest(
        objective=args.objective,
        prompt=args.prompt,
        workload=args.workload,
        candidates_per_round=args.candidates,
        critics_per_candidate=args.critics,
        min_distinct_models=args.min_distinct_models,
        max_rounds=args.rounds,
        max_remote_calls=args.max_remote_calls,
        daily_remote_limit=args.daily_remote_limit,
        max_output_tokens=args.max_output_tokens,
        stagnation_rounds=args.stagnation_rounds,
        policy=policy,
        context=args.context,
        benchmark_id=args.benchmark_id,
        study_id=args.study_id,
        study_arm_id=args.study_arm,
        study_contract_sha256=study_contract_hash,
        repeat_index=args.repeat_index,
        use_experience=not args.no_experience,
        source_experiment_id=getattr(args, "source_experiment_id", None),
        source_result_sha256=getattr(args, "source_result_sha256", None),
        experiment_id=experiment_id,
    )
    store = ExperimentStore(args.db)
    try:
        if experiment_id and store.experiment_exists(experiment_id):
            raise SystemExit("deterministic experiment identity already exists")
        if args.benchmark_id:
            try:
                benchmark = store.get_benchmark(args.benchmark_id)
            except KeyError as exc:
                raise SystemExit(f"unknown or inactive benchmark: {args.benchmark_id}") from exc
            metadata = json.loads(benchmark["metadata_json"])
            binding = metadata.get("binding")
            if not isinstance(binding, dict):
                raise SystemExit("benchmark has no immutable v1 binding")
            if args.objective != benchmark["objective"] or args.workload != benchmark["workload"]:
                raise SystemExit("run objective/workload must exactly match the registered benchmark")
            try:
                evaluator = evaluator_from_contract(verify_benchmark_contract(binding))
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
        else:
            evaluator = evaluator_from_contract(_evaluator_contract(args))
        result = ExperimentEngine(adapters=adapters, models=models, store=store).run(request, evaluator)
    finally:
        store.close()
    output = _jsonable(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result.status, "experiment_id": result.experiment_id, "output": str(args.output)}, indent=2))
    return 0 if result.status == "VERIFIED" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="giga-inference")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    discover_parser = sub.add_parser("discover", help="snapshot OpenRouter model availability")
    discover_parser.set_defaults(func=discover)

    local_discover_parser = sub.add_parser(
        "discover-local", help="discover a local OpenAI-compatible model pool",
    )
    local_discover_parser.add_argument(
        "--local-base-url",
        default=os.environ.get("LOCAL_OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
    )
    local_discover_parser.set_defaults(func=discover_local)

    monitor_parser = sub.add_parser(
        "monitor-once", help="record one bounded free/preview-window check",
    )
    monitor_parser.add_argument(
        "--output", type=Path, default=ROOT / "state" / "last-monitor-receipt.json",
    )
    monitor_parser.set_defaults(func=monitor_once)

    harvest_parser = sub.add_parser(
        "harvest-next", help="benchmark exactly one unmeasured free/preview model",
    )
    harvest_parser.add_argument("--benchmark-id", default="fabric-json-test-plan-002")
    harvest_parser.add_argument("--rounds", type=int, default=1)
    harvest_parser.add_argument(
        "--daily-remote-limit", type=int,
        default=int(os.environ.get("OPENROUTER_FREE_DAILY_LIMIT", "50")),
    )
    harvest_parser.add_argument("--execute", action="store_true")
    harvest_parser.add_argument("--use-opencode-auth", action="store_true")
    harvest_parser.add_argument("--max-output-tokens", type=int, default=512)
    harvest_parser.add_argument(
        "--privacy", choices=[item.value for item in PrivacyClass], default="internal",
    )
    harvest_parser.add_argument("--require-zdr", action="store_true")
    harvest_parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "state" / "harvest",
    )
    harvest_parser.set_defaults(func=harvest_next)

    profiles_parser = sub.add_parser("profiles", help="list reusable background workloads")
    profiles_parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    profiles_parser.set_defaults(func=profiles)

    studies_parser = sub.add_parser("studies", help="list immutable controlled-study contracts")
    studies_parser.add_argument("--study-catalogue", type=Path, default=DEFAULT_STUDIES)
    studies_parser.set_defaults(func=studies)

    study_plan_parser = sub.add_parser("study-plan", help="expand one controlled study into fixed cells")
    study_plan_parser.add_argument("--study-id", required=True)
    study_plan_parser.add_argument("--study-catalogue", type=Path, default=DEFAULT_STUDIES)
    study_plan_parser.add_argument(
        "--daily-remote-limit", type=int,
        default=int(os.environ.get("OPENROUTER_FREE_DAILY_LIMIT", "50")),
    )
    study_plan_parser.set_defaults(func=study_plan)

    study_scoreboard_parser = sub.add_parser("study-scoreboard", help="score completed controlled-study arms")
    study_scoreboard_parser.add_argument("--study-id", required=True)
    study_scoreboard_parser.set_defaults(func=study_scoreboard)

    study_next_parser = sub.add_parser(
        "study-next", help="select and optionally execute exactly one pending study cell",
    )
    study_next_parser.add_argument("--study-id", required=True)
    study_next_parser.add_argument("--study-catalogue", type=Path, default=DEFAULT_STUDIES)
    study_next_parser.add_argument(
        "--daily-remote-limit", type=int,
        default=int(os.environ.get("OPENROUTER_FREE_DAILY_LIMIT", "50")),
    )
    study_next_parser.add_argument("--execute", action="store_true")
    study_next_parser.add_argument("--use-opencode-auth", action="store_true")
    study_next_parser.add_argument("--free-model", action="append", default=[])
    study_next_parser.add_argument("--include-paid", action="store_true")
    study_next_parser.add_argument("--paid-model", action="append", default=[])
    study_next_parser.add_argument("--max-cost-usd", type=float, default=0.0)
    study_next_parser.add_argument("--max-output-tokens", type=int, default=512)
    study_next_parser.add_argument(
        "--privacy", choices=[item.value for item in PrivacyClass], default="internal",
    )
    study_next_parser.add_argument("--require-zdr", action="store_true")
    study_next_parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "state" / "studies",
    )
    study_next_parser.set_defaults(func=study_next)

    register_parser = sub.add_parser("benchmark-register", help="register a locked real-project benchmark")
    register_parser.add_argument("--benchmark-id", required=True)
    register_parser.add_argument("--project", required=True)
    register_parser.add_argument("--workload", required=True)
    register_parser.add_argument("--objective", required=True)
    register_parser.add_argument("--fixture-ref", required=True)
    register_parser.add_argument("--evaluator-ref", required=True)
    register_parser.add_argument("--notes", default="")
    register_parser.set_defaults(func=benchmark_register)

    scoreboard_parser = sub.add_parser("scoreboard", help="rank observed utility in this workflow")
    scoreboard_parser.add_argument("--benchmark-id")
    scoreboard_parser.set_defaults(func=scoreboard)

    queue_add_parser = sub.add_parser("queue-add", help="idempotently queue useful idle-capacity work")
    queue_add_parser.add_argument("--work-id")
    queue_add_parser.add_argument("--idempotency-key")
    queue_add_parser.add_argument("--project", required=True)
    queue_add_parser.add_argument("--workload", required=True)
    queue_add_parser.add_argument("--objective", required=True)
    queue_add_parser.add_argument("--prompt", required=True)
    queue_add_parser.add_argument("--context", default="")
    queue_add_parser.add_argument("--require", action="append", default=[])
    queue_add_parser.add_argument("--forbid", action="append", default=[])
    queue_add_parser.add_argument("--check-command", action="append", default=[])
    queue_add_parser.add_argument("--evaluator-cwd", type=Path)
    queue_add_parser.add_argument("--command-timeout", type=int, default=300)
    queue_add_parser.add_argument("--priority", type=int, default=0)
    queue_add_parser.add_argument("--max-attempts", type=int, default=3)
    queue_add_parser.set_defaults(func=queue_add)

    queue_next_parser = sub.add_parser("queue-next", help="lease one bounded background item")
    queue_next_parser.add_argument("--lease-minutes", type=int, default=30)
    queue_next_parser.set_defaults(func=queue_next)

    queue_finish_parser = sub.add_parser("queue-finish", help="record objective result of leased work")
    queue_finish_parser.add_argument("--work-id", required=True)
    queue_finish_parser.add_argument("--experiment-id", required=True)
    queue_finish_parser.add_argument("--verified", action="store_true")
    queue_finish_parser.set_defaults(func=queue_finish)

    escalate_parser = sub.add_parser(
        "escalate", help="send one canonical failed evidence packet to one budgeted paid model",
    )
    escalate_parser.add_argument("--source-result", type=Path, required=True)
    escalate_parser.add_argument("--paid-model", required=True)
    escalate_parser.add_argument("--max-cost-usd", type=float, required=True)
    escalate_parser.add_argument("--max-output-tokens", type=int, default=4096)
    escalate_parser.add_argument("--daily-remote-limit", type=int, default=50)
    escalate_parser.add_argument("--use-opencode-auth", action="store_true")
    escalate_parser.add_argument(
        "--privacy", choices=[item.value for item in PrivacyClass], default="public",
    )
    escalate_parser.add_argument("--require-zdr", action="store_true")
    escalate_parser.add_argument("--output-dir", type=Path, default=ROOT / "state/escalations")
    escalate_parser.set_defaults(func=escalate)

    worker_parser = sub.add_parser("worker-once", help="execute one leased background item and exit")
    worker_parser.add_argument("--lease-minutes", type=int, default=30)
    worker_parser.add_argument("--candidates", type=int, default=3)
    worker_parser.add_argument("--critics", type=int, default=2)
    worker_parser.add_argument("--min-distinct-models", type=int, default=2)
    worker_parser.add_argument("--rounds", type=int, default=4)
    worker_parser.add_argument("--max-remote-calls", type=int, default=50)
    worker_parser.add_argument("--daily-remote-limit", type=int, default=int(os.environ.get("OPENROUTER_FREE_DAILY_LIMIT", "50")))
    worker_parser.add_argument("--max-output-tokens", type=int, default=4096)
    worker_parser.add_argument("--privacy", choices=[item.value for item in PrivacyClass], default="internal")
    worker_parser.add_argument("--require-zdr", action="store_true")
    worker_parser.add_argument("--local-only", action="store_true")
    worker_parser.add_argument("--use-opencode-auth", action="store_true")
    worker_parser.add_argument("--free-model", action="append", default=[])
    worker_parser.add_argument("--local-model", action="append", default=[])
    worker_parser.add_argument("--local-base-url", default=os.environ.get("LOCAL_OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"))
    worker_parser.set_defaults(func=worker_once)

    run_parser = sub.add_parser("run", help="run an evidence-gated cheap-model ensemble")
    run_parser.add_argument("--objective", required=True)
    run_parser.add_argument("--prompt", required=True)
    run_parser.add_argument("--context", default="")
    run_parser.add_argument("--workload", default="implementation")
    run_parser.add_argument("--benchmark-id")
    run_parser.add_argument("--study-id")
    run_parser.add_argument("--study-arm")
    run_parser.add_argument("--repeat-index", type=int)
    run_parser.add_argument("--study-catalogue", type=Path, default=DEFAULT_STUDIES)
    run_parser.add_argument("--no-experience", action="store_true")
    run_parser.add_argument("--require", action="append", default=[])
    run_parser.add_argument("--forbid", action="append", default=[])
    run_parser.add_argument("--check-command", action="append", default=[])
    run_parser.add_argument("--evaluator-cwd", type=Path)
    run_parser.add_argument("--command-timeout", type=int, default=300)
    run_parser.add_argument("--candidates", type=int, default=3)
    run_parser.add_argument("--critics", type=int, default=2)
    run_parser.add_argument("--min-distinct-models", type=int, default=2)
    run_parser.add_argument("--rounds", type=int, default=4)
    run_parser.add_argument("--max-remote-calls", type=int, default=50)
    run_parser.add_argument("--daily-remote-limit", type=int, default=int(os.environ.get("OPENROUTER_FREE_DAILY_LIMIT", "50")))
    run_parser.add_argument("--max-output-tokens", type=int, default=4096)
    run_parser.add_argument("--stagnation-rounds", type=int, default=2)
    run_parser.add_argument("--privacy", choices=[item.value for item in PrivacyClass], default="internal")
    run_parser.add_argument("--require-zdr", action="store_true")
    run_parser.add_argument("--local-only", action="store_true")
    run_parser.add_argument("--use-opencode-auth", action="store_true")
    run_parser.add_argument("--free-model", action="append", default=[])
    run_parser.add_argument("--local-model", action="append", default=[])
    run_parser.add_argument("--local-base-url", default=os.environ.get("LOCAL_OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"))
    run_parser.add_argument("--include-paid", action="store_true", help="explicitly admit named paid models")
    run_parser.add_argument("--paid-model", action="append", default=[])
    run_parser.add_argument("--max-cost-usd", type=float, default=0.0)
    run_parser.add_argument("--output", type=Path, default=ROOT / "state" / "last-result.json")
    run_parser.set_defaults(func=run)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
