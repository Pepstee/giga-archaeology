import hashlib
import json
import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import constitutional_gate as constitutional_gate_module

from gate_admission import (
    WriterLeaseUnavailable,
    decide,
    exclusive_worktree_lease,
    run_writer_command,
)
from constitutional_gate import (
    COMPLETION_SCHEMA,
    CONFINEMENT_EXECUTION_SCHEMA,
    CONFINEMENT_PLAN_SCHEMA,
    WORK_ORDER_SCHEMA,
    build_confinement_plan,
    capture_git_state,
    confinement_bwrap_argv,
    digest,
    preflight,
    prepare_confinement_execution,
    record_override,
    run_completion_proofs,
    self_bound,
    verify_completion,
)


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def make_repository(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "worktree"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "fixture@giga.invalid")
    git(root, "config", "user.name", "GIGA fixture")
    (root / "allowed.txt").write_text("preserved\n", encoding="utf-8")
    git(root, "add", "allowed.txt")
    git(root, "commit", "-m", "fixture baseline")
    constitution = tmp_path / "CHARTER.md"
    constitution.write_text(
        "# Constitution\n\n*Version 1.3 — fixture. The canonical policy.*\n",
        encoding="utf-8",
    )
    return root, constitution


def make_work_order(root: Path, constitution: Path) -> dict:
    starting_state = capture_git_state(root)
    return {
        "schema": WORK_ORDER_SCHEMA,
        "id": "fixture-bounded-1",
        "constitution": {"version": "1.3", "sha256": digest(constitution)},
        "increment": {
            "id": "increment-1",
            "objective": "Verify the preserved fixture through one real acceptance command.",
            "non_goals": ["Do not modify any product repository."],
        },
        "scope": {
            "repository": str(root.resolve()),
            "allowed_paths": ["allowed.txt", ".giga/OBJECTIVE_COMPLETE"],
            "allowed_actions": ["read_files", "run_tests", "modify_files"],
        },
        "starting_state": starting_state,
        "acceptance": [
            {
                "id": "fixture-proof",
                "command": [
                    "python3",
                    "-c",
                    "from pathlib import Path; assert Path('allowed.txt').read_text() == 'preserved\\n'; print('fixture-ok')",
                ],
                "cwd": ".",
                "expected_exit_code": 0,
                "timeout_seconds": 30,
            }
        ],
        "rollback": {
            "kind": "git_commit",
            "reference": starting_state["commit"],
            "starting_state_sha256": starting_state["state_sha256"],
        },
        "authority": {"external_actions": [], "irreversible_actions": []},
        "semantic_review": {"required": False, "policy": "bounded-read-only-v1"},
        "completion": {
            "claim_marker": ".giga/OBJECTIVE_COMPLETE",
            "required_proof_ids": ["fixture-proof"],
            "required_receipt_schema": COMPLETION_SCHEMA,
        },
    }


def make_executable(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def attach_wait_chain(
    value: dict,
    launcher: Path,
    wait_wrapper: Path,
    unit_file: Path,
    *,
    unit_name: str = "giga-fixture-wait-chain.service",
    unit_file_state: str = "enabled",
) -> None:
    value["launcher"] = {
        "path": str(launcher.resolve()),
        "sha256": digest(launcher),
    }
    value["wait_to_worker"] = {
        "wait_wrapper": {
            "path": str(wait_wrapper.resolve()),
            "sha256": digest(wait_wrapper),
        },
        "worker_unit": {
            "manager": "user",
            "name": unit_name,
            "fragment_path": str(unit_file.resolve()),
            "sha256": digest(unit_file),
            "exec_start": str(wait_wrapper.resolve()),
            "unit_file_state": unit_file_state,
        },
    }


def make_confinement_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, Path, dict]:
    root, constitution = make_repository(tmp_path)
    allowed = root / "allowed"
    allowed.mkdir()
    (allowed / ".keep").write_text("preserved\n", encoding="utf-8")
    (root / "disallowed-tracked.txt").write_text("protected\n", encoding="utf-8")
    (root / ".gitignore").write_text("transient/\n", encoding="utf-8")
    transient = root / "transient"
    transient.mkdir()
    (transient / "cache.txt").write_text("ignored-protected\n", encoding="utf-8")
    (allowed / "escape-link").symlink_to("../disallowed-tracked.txt")
    git(root, "add", ".gitignore", "allowed", "disallowed-tracked.txt")
    git(root, "commit", "-m", "confinement fixture")

    value = make_work_order(root, constitution)
    value["id"] = "fixture-confinement-2"
    value["increment"]["id"] = "increment-2"
    value["scope"]["allowed_paths"] = ["allowed"]
    value["completion"]["claim_marker"] = "allowed/OBJECTIVE_COMPLETE"
    value["acceptance"] = [
        {
            "id": "fixture-proof",
            "command": [
                "python3",
                "-c",
                "from pathlib import Path; assert Path('allowed/.keep').read_text() == 'preserved\\n'; print('fixture-ok')",
            ],
            "cwd": ".",
            "expected_exit_code": 0,
            "timeout_seconds": 30,
        }
    ]
    value["starting_state"] = capture_git_state(root)
    value["rollback"]["reference"] = value["starting_state"]["commit"]
    value["rollback"]["starting_state_sha256"] = value["starting_state"][
        "state_sha256"
    ]
    work_order = write_json(tmp_path / "work-order.json", value)
    preflight_path = write_json(
        tmp_path / "preflight.json",
        preflight(work_order, constitution, root),
    )
    fake_bwrap = make_executable(
        tmp_path / "bwrap",
        "#!/bin/sh\nprintf 'bubblewrap 0.11.1\\n'\n",
    )
    fake_worker = make_executable(
        tmp_path / "fixture-worker",
        "#!/bin/sh\nexit 0\n",
    )
    plan = build_confinement_plan(
        work_order,
        constitution,
        root,
        preflight_path,
        fake_worker,
        bwrap_path=fake_bwrap,
        trusted_bwrap_owner=os.getuid(),
    )
    return root, constitution, work_order, preflight_path, fake_worker, plan


def test_no_expansion_is_admitted(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {"findings": [{"id": "F-1", "classification": "DEFECT", "status": "open"}]},
    )
    assert decide(findings, None, None)[0] is True


def test_expansion_without_fable_is_refused(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {
            "findings": [
                {
                    "id": "F-2",
                    "classification": "ARCHITECTURE_EXPANSION",
                    "status": "open",
                }
            ]
        },
    )
    admitted, reason = decide(findings, None, None)
    assert admitted is False
    assert "Fable" in reason


def test_non_approving_fable_ruling_is_refused(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {
            "findings": [
                {
                    "id": "F-3",
                    "classification": "ARCHITECTURE_EXPANSION",
                    "status": "open",
                }
            ]
        },
    )
    ruling = write_json(
        tmp_path / "ruling.json",
        {"decision": "REDIRECT", "ratified_finding_ids": ["F-3"]},
    )
    receipt = write_json(
        tmp_path / "receipt.json",
        {
            "schema": "giga.fable-gate-receipt.v1",
            "ruling_sha256": hashlib.sha256(ruling.read_bytes()).hexdigest(),
        },
    )
    assert decide(findings, ruling, receipt)[0] is False


def test_exact_hash_bound_fable_ratification_is_admitted(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {
            "findings": [
                {
                    "id": "F-4",
                    "classification": "ARCHITECTURE_EXPANSION",
                    "status": "open",
                }
            ]
        },
    )
    ruling = write_json(
        tmp_path / "ruling.json",
        {
            "decision": "APPROVE_SCOPE_EXCEPTION",
            "ratified_finding_ids": ["F-4"],
        },
    )
    receipt = write_json(
        tmp_path / "receipt.json",
        {
            "schema": "giga.fable-gate-receipt.v1",
            "ruling_sha256": hashlib.sha256(ruling.read_bytes()).hexdigest(),
        },
    )
    assert decide(findings, ruling, receipt)[0] is True


def test_wrong_ruling_hash_is_refused(tmp_path: Path) -> None:
    findings = write_json(
        tmp_path / "findings.json",
        {
            "findings": [
                {
                    "id": "F-5",
                    "classification": "ARCHITECTURE_EXPANSION",
                    "status": "open",
                }
            ]
        },
    )
    ruling = write_json(
        tmp_path / "ruling.json",
        {
            "decision": "APPROVE_SCOPE_EXCEPTION",
            "ratified_finding_ids": ["F-5"],
        },
    )
    receipt = write_json(
        tmp_path / "receipt.json",
        {
            "schema": "giga.fable-gate-receipt.v1",
            "ruling_sha256": "0" * 64,
        },
    )
    assert decide(findings, ruling, receipt)[0] is False


def test_compliant_bounded_work_order_passes_end_to_end(tmp_path: Path) -> None:
    root, constitution = make_repository(tmp_path)
    work_order = write_json(tmp_path / "work-order.json", make_work_order(root, constitution))
    preflight_receipt = preflight(work_order, constitution, root)
    assert preflight_receipt["verdict"] == "PASS"
    preflight_path = write_json(tmp_path / "preflight.json", preflight_receipt)

    completion = run_completion_proofs(
        work_order,
        constitution,
        root,
        preflight_path,
        tmp_path / "evidence",
    )
    assert completion["technical_correctness"] == "PASS"
    assert completion["constitutional_compliance"] == "PASS"
    assert completion["verdict"] == "PASS"
    completion_path = write_json(tmp_path / "completion.json", completion)
    verification = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
    )
    assert verification["verdict"] == "PASS"
    assert verification["work_order_sha256"] == digest(work_order)
    assert verification["starting_state"] == make_work_order(root, constitution)["starting_state"]


def test_underspecified_one_shot_contract_is_mechanically_blocked(tmp_path: Path) -> None:
    root, constitution = make_repository(tmp_path)
    value = make_work_order(root, constitution)
    value["increment"]["non_goals"] = []
    value["acceptance"] = []
    value["completion"]["required_proof_ids"] = []
    value["rollback"]["reference"] = ""
    work_order = write_json(tmp_path / "one-shot.json", value)

    receipt = preflight(work_order, constitution, root)
    assert receipt["verdict"] == "REJECT"
    assert {
        "INCREMENT_NON_GOALS_MISSING",
        "PROOF_REQUIREMENTS_MISSING",
        "ROLLBACK_REFERENCE_INVALID",
    } <= set(receipt["reason_codes"])


def test_scope_escape_and_missing_proof_are_blocked(tmp_path: Path) -> None:
    root, constitution = make_repository(tmp_path)
    work_order = write_json(tmp_path / "work-order.json", make_work_order(root, constitution))
    preflight_path = write_json(
        tmp_path / "preflight.json",
        preflight(work_order, constitution, root),
    )
    (root / "outside-scope.txt").write_text("escape\n", encoding="utf-8")
    completion = run_completion_proofs(
        work_order,
        constitution,
        root,
        preflight_path,
        tmp_path / "evidence",
    )
    assert completion["verdict"] == "REJECT"
    assert "SCOPE_PATH_UNAUTHORIZED" in completion["reason_codes"]

    # A claimed completion without its named evidence cannot be replayed as PASS.
    completion_path = write_json(tmp_path / "completion.json", completion)
    for evidence in (tmp_path / "evidence").glob("*"):
        evidence.unlink()
    verification = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
    )
    assert verification["verdict"] == "REJECT"
    assert "PROOF_MISSING" in verification["reason_codes"] or not completion["proofs"]


def test_replay_is_byte_deterministic(tmp_path: Path) -> None:
    root, constitution = make_repository(tmp_path)
    work_order = write_json(tmp_path / "work-order.json", make_work_order(root, constitution))
    first = preflight(work_order, constitution, root)
    second = preflight(work_order, constitution, root)
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(
        second, sort_keys=True, separators=(",", ":")
    )
    preflight_path = write_json(tmp_path / "preflight.json", first)
    completion = run_completion_proofs(
        work_order,
        constitution,
        root,
        preflight_path,
        tmp_path / "evidence",
    )
    completion_path = write_json(tmp_path / "completion.json", completion)
    replay_one = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
    )
    replay_two = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
    )
    assert json.dumps(replay_one, sort_keys=True, separators=(",", ":")) == json.dumps(
        replay_two, sort_keys=True, separators=(",", ":")
    )
    assert replay_one["receipt_sha256"] == replay_two["receipt_sha256"]


def test_stylistic_preference_is_not_a_hard_gate(tmp_path: Path) -> None:
    root, constitution = make_repository(tmp_path)
    value = make_work_order(root, constitution)
    value["increment"]["objective"] = "Use an unfashionable but valid implementation style."
    work_order = write_json(tmp_path / "work-order.json", value)
    receipt = preflight(work_order, constitution, root)
    assert receipt["verdict"] == "PASS"
    assert receipt["reason_codes"] == []


def test_semantic_review_holds_without_rejecting_and_override_is_explicit(tmp_path: Path) -> None:
    root, constitution = make_repository(tmp_path)
    value = make_work_order(root, constitution)
    value["semantic_review"]["required"] = True
    work_order = write_json(tmp_path / "work-order.json", value)
    held = preflight(work_order, constitution, root)
    assert held["verdict"] == "HELD_FOR_REVIEW"
    assert held["reasons"] == [
        {
            "code": "SEMANTIC_REVIEW_HELD",
            "hard": False,
            "message": "a bounded semantic-review receipt is required",
        }
    ]

    expiry = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat()
    ledger = tmp_path / "overrides.jsonl"
    override = record_override(
        work_order,
        ledger,
        "operator-fixture",
        "Allow this exact fixture to proceed without a semantic call.",
        ["SEMANTIC_REVIEW_HELD"],
        value["scope"]["allowed_paths"],
        value["scope"]["allowed_actions"],
        expiry,
    )
    override_path = write_json(tmp_path / "override.json", override)
    admitted = preflight(
        work_order,
        constitution,
        root,
        override_path=override_path,
        override_ledger_path=ledger,
    )
    assert admitted["verdict"] == "PASS"
    assert admitted["override"]["identity"] == "operator-fixture"


def test_bounded_semantic_warning_cannot_mutate_or_hard_reject(tmp_path: Path) -> None:
    root, constitution = make_repository(tmp_path)
    value = make_work_order(root, constitution)
    value["semantic_review"]["required"] = True
    work_order = write_json(tmp_path / "work-order.json", value)
    review = self_bound(
        {
            "confidence": 0.7,
            "mutation_authority": False,
            "reasons": ["The increment is valid but could use a clearer name."],
            "reviewer": "fixture-reviewer",
            "schema": "giga.constitution-semantic-review.v1",
            "verdict": "WARN",
            "work_order_sha256": digest(work_order),
        }
    )
    review_path = write_json(tmp_path / "semantic-review.json", review)
    receipt = preflight(work_order, constitution, root, semantic_review_path=review_path)
    assert receipt["verdict"] == "WARN"
    assert receipt["reasons"] == [
        {"code": "SEMANTIC_REVIEW_WARN", "hard": False, "message": "reviewer returned a warning"}
    ]


def test_secret_and_constitution_mismatch_fail_closed(tmp_path: Path) -> None:
    root, constitution = make_repository(tmp_path)
    value = make_work_order(root, constitution)
    value["increment"]["objective"] = "Never copy sk-abcdefghijklmnopqrstuvwxyz123456"
    value["constitution"]["sha256"] = "0" * 64
    work_order = write_json(tmp_path / "tainted.json", value)
    receipt = preflight(work_order, constitution, root)
    assert receipt["verdict"] == "REJECT"
    assert {"SECRET_EXPOSURE", "CONSTITUTION_HASH_MISMATCH"} <= set(receipt["reason_codes"])


def test_launcher_authority_binds_preflight_confinement_and_completion(
    tmp_path: Path,
) -> None:
    root, constitution, work_order, _, fake_worker, original_plan = (
        make_confinement_fixture(tmp_path)
    )
    launcher = make_executable(
        tmp_path / "selected-launcher",
        "#!/bin/sh\nexit 0\n",
    )
    value = json.loads(work_order.read_text(encoding="utf-8"))
    value["launcher"] = {
        "path": str(launcher.resolve()),
        "sha256": digest(launcher),
    }
    write_json(work_order, value)

    omitted = preflight(work_order, constitution, root)
    assert omitted["verdict"] == "REJECT"
    assert "LAUNCHER_BINDING_REQUIRED" in omitted["reason_codes"]

    other_launcher = make_executable(
        tmp_path / "other-launcher",
        "#!/bin/sh\nexit 1\n",
    )
    wrong = preflight(
        work_order,
        constitution,
        root,
        required_launcher_path=other_launcher,
    )
    assert wrong["verdict"] == "REJECT"
    assert {"LAUNCHER_HASH_MISMATCH", "LAUNCHER_PATH_MISMATCH"} <= set(
        wrong["reason_codes"]
    )

    admitted = preflight(
        work_order,
        constitution,
        root,
        required_launcher_path=launcher,
    )
    assert admitted["verdict"] == "PASS"
    assert admitted["launcher"]["path"] == str(launcher.resolve())
    assert admitted["launcher"]["sha256"] == digest(launcher)
    preflight_path = write_json(tmp_path / "launcher-preflight.json", admitted)

    fake_bwrap = Path(original_plan["bubblewrap"]["resolved"])
    plan = build_confinement_plan(
        work_order,
        constitution,
        root,
        preflight_path,
        fake_worker,
        bwrap_path=fake_bwrap,
        trusted_bwrap_owner=os.getuid(),
        required_launcher_path=launcher,
    )
    assert plan["verdict"] == "PASS"
    assert plan["launcher"] == admitted["launcher"]
    plan_path = write_json(tmp_path / "launcher-plan.json", plan)

    execution, argv = prepare_confinement_execution(
        plan_path,
        work_order,
        preflight_path,
        root,
        [str(fake_worker)],
        required_launcher_path=launcher,
    )
    assert execution["verdict"] == "PASS"
    assert execution["launcher"] == admitted["launcher"]
    assert argv is not None
    execution_path = write_json(tmp_path / "launcher-execution.json", execution)

    (root / "allowed" / "OBJECTIVE_COMPLETE").write_text(
        "complete\n", encoding="utf-8"
    )
    completion = run_completion_proofs(
        work_order,
        constitution,
        root,
        preflight_path,
        tmp_path / "launcher-evidence",
        plan_path,
        execution_path,
    )
    assert completion["verdict"] == "PASS"
    assert completion["launcher"] == admitted["launcher"]
    completion_path = write_json(tmp_path / "launcher-completion.json", completion)
    first = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
        plan_path,
        execution_path,
    )
    second = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
        plan_path,
        execution_path,
    )
    assert first == second
    assert first["verdict"] == "PASS"
    assert first["launcher"] == admitted["launcher"]


def test_wait_chain_binds_preflight_confinement_completion_and_replay(
    tmp_path: Path,
) -> None:
    root, constitution, work_order, _, fake_worker, original_plan = (
        make_confinement_fixture(tmp_path)
    )
    launcher = make_executable(tmp_path / "chain-launcher", "#!/bin/sh\nexit 0\n")
    wait_wrapper = make_executable(tmp_path / "wait-wrapper", "#!/bin/sh\nexit 0\n")
    unit_file = tmp_path / "giga-fixture-wait-chain.service"
    unit_file.write_text(
        "[Service]\nExecStart=" + str(wait_wrapper.resolve()) + "\n",
        encoding="utf-8",
    )
    unit_file.chmod(0o644)
    value = json.loads(work_order.read_text(encoding="utf-8"))
    attach_wait_chain(value, launcher, wait_wrapper, unit_file)
    write_json(work_order, value)

    omitted = preflight(
        work_order,
        constitution,
        root,
        required_launcher_path=launcher,
    )
    assert omitted["verdict"] == "REJECT"
    assert "WAIT_CHAIN_BINDING_REQUIRED" in omitted["reason_codes"]

    admitted = preflight(
        work_order,
        constitution,
        root,
        required_launcher_path=launcher,
        required_wait_wrapper_path=wait_wrapper,
        required_worker_unit="giga-fixture-wait-chain.service",
        required_worker_unit_file=unit_file,
    )
    assert admitted["verdict"] == "PASS"
    assert admitted["wait_to_worker"]["wait_wrapper"]["sha256"] == digest(wait_wrapper)
    assert admitted["wait_to_worker"]["worker_unit"]["sha256"] == digest(unit_file)
    assert admitted["wait_to_worker"]["downstream_launcher"] == admitted["launcher"]
    preflight_path = write_json(tmp_path / "chain-preflight.json", admitted)

    fake_bwrap = Path(original_plan["bubblewrap"]["resolved"])
    plan = build_confinement_plan(
        work_order,
        constitution,
        root,
        preflight_path,
        fake_worker,
        bwrap_path=fake_bwrap,
        trusted_bwrap_owner=os.getuid(),
        required_launcher_path=launcher,
        required_wait_wrapper_path=wait_wrapper,
        required_worker_unit="giga-fixture-wait-chain.service",
        required_worker_unit_file=unit_file,
    )
    assert plan["verdict"] == "PASS"
    assert plan["wait_to_worker"] == admitted["wait_to_worker"]
    plan_path = write_json(tmp_path / "chain-plan.json", plan)

    execution, argv = prepare_confinement_execution(
        plan_path,
        work_order,
        preflight_path,
        root,
        [str(fake_worker)],
        required_launcher_path=launcher,
        required_wait_wrapper_path=wait_wrapper,
        required_worker_unit="giga-fixture-wait-chain.service",
        required_worker_unit_file=unit_file,
    )
    assert execution["verdict"] == "PASS"
    assert execution["wait_to_worker"] == admitted["wait_to_worker"]
    assert argv is not None
    execution_path = write_json(tmp_path / "chain-execution.json", execution)

    (root / "allowed" / "OBJECTIVE_COMPLETE").write_text("complete\n", encoding="utf-8")
    completion = run_completion_proofs(
        work_order,
        constitution,
        root,
        preflight_path,
        tmp_path / "chain-evidence",
        plan_path,
        execution_path,
    )
    assert completion["verdict"] == "PASS"
    assert completion["wait_to_worker"] == admitted["wait_to_worker"]
    completion_path = write_json(tmp_path / "chain-completion.json", completion)
    first = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
        plan_path,
        execution_path,
    )
    second = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
        plan_path,
        execution_path,
    )
    assert first == second
    assert first["verdict"] == "PASS"
    assert first["wait_to_worker"] == admitted["wait_to_worker"]


def test_wait_chain_hashes_and_runtime_identity_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, constitution = make_repository(tmp_path)
    launcher = make_executable(tmp_path / "chain-launcher", "#!/bin/sh\nexit 0\n")
    wait_wrapper = make_executable(tmp_path / "wait-wrapper", "#!/bin/sh\nexit 0\n")
    unit_file = tmp_path / "giga-fixture-wait-chain.service"
    unit_file.write_text(
        "[Service]\nExecStart=" + str(wait_wrapper.resolve()) + "\n",
        encoding="utf-8",
    )
    unit_file.chmod(0o644)
    value = make_work_order(root, constitution)
    attach_wait_chain(value, launcher, wait_wrapper, unit_file)

    wrong_wrapper = json.loads(json.dumps(value))
    wrong_wrapper["wait_to_worker"]["wait_wrapper"]["sha256"] = "0" * 64
    wrong_wrapper_path = write_json(tmp_path / "wrong-wrapper.json", wrong_wrapper)
    wrapper_receipt = preflight(
        wrong_wrapper_path,
        constitution,
        root,
        required_launcher_path=launcher,
        required_wait_wrapper_path=wait_wrapper,
        required_worker_unit="giga-fixture-wait-chain.service",
        required_worker_unit_file=unit_file,
    )
    assert "WAIT_WRAPPER_HASH_MISMATCH" in wrapper_receipt["reason_codes"]

    wrong_unit = json.loads(json.dumps(value))
    wrong_unit["wait_to_worker"]["worker_unit"]["sha256"] = "0" * 64
    wrong_unit_path = write_json(tmp_path / "wrong-unit.json", wrong_unit)
    unit_receipt = preflight(
        wrong_unit_path,
        constitution,
        root,
        required_launcher_path=launcher,
        required_wait_wrapper_path=wait_wrapper,
        required_worker_unit="giga-fixture-wait-chain.service",
        required_worker_unit_file=unit_file,
    )
    assert "WORKER_UNIT_HASH_MISMATCH" in unit_receipt["reason_codes"]

    work_order = write_json(tmp_path / "chain-work-order.json", value)
    monkeypatch.setattr(constitutional_gate_module, "_launcher_parent_matches", lambda _: True)
    monkeypatch.setattr(constitutional_gate_module, "_current_user_unit_matches", lambda _: False)
    monkeypatch.setattr(
        constitutional_gate_module,
        "_user_unit_properties",
        lambda _: {
            "Id": "giga-fixture-wait-chain.service",
            "LoadState": "loaded",
            "UnitFileState": "enabled",
            "FragmentPath": str(unit_file.resolve()),
            "ExecStart": "{ path=" + str(wait_wrapper.resolve()) + " ; }",
        },
    )
    caller_receipt = preflight(
        work_order,
        constitution,
        root,
        required_launcher_path=launcher,
        require_launcher_caller=True,
        required_wait_wrapper_path=wait_wrapper,
        required_worker_unit="giga-fixture-wait-chain.service",
        required_worker_unit_file=unit_file,
    )
    assert caller_receipt["verdict"] == "REJECT"
    assert "WORKER_UNIT_CALLER_MISMATCH" in caller_receipt["reason_codes"]


@pytest.mark.skipif(sys.platform != "linux", reason="launcher ancestry uses Linux /proc")
def test_launcher_cli_requires_the_selected_script_as_actual_parent(tmp_path: Path) -> None:
    root, constitution = make_repository(tmp_path)
    gate = Path(__file__).parent / "constitutional_gate.py"
    launcher = make_executable(
        tmp_path / "bound-launcher",
        "#!/bin/sh\n"
        'python3 "$1" preflight --work-order "$2" --constitution "$3" '
        '--worktree "$4" --required-launcher "$0" --receipt-out "$5" >/dev/null\n',
    )
    value = make_work_order(root, constitution)
    value["launcher"] = {
        "path": str(launcher.resolve()),
        "sha256": digest(launcher),
    }
    work_order = write_json(tmp_path / "launcher-work-order.json", value)
    receipt = tmp_path / "parent-bound-preflight.json"
    result = subprocess.run(
        [
            str(launcher),
            str(gate),
            str(work_order),
            str(constitution),
            str(root),
            str(receipt),
        ],
        check=False,
        capture_output=True,
    )
    assert result.returncode == 0
    assert json.loads(receipt.read_text(encoding="utf-8"))["verdict"] == "PASS"

    direct = subprocess.run(
        [
            sys.executable,
            str(gate),
            "preflight",
            "--work-order",
            str(work_order),
            "--constitution",
            str(constitution),
            "--worktree",
            str(root),
            "--required-launcher",
            str(launcher),
        ],
        check=False,
        capture_output=True,
    )
    assert direct.returncode == 42
    assert "LAUNCHER_CALLER_MISMATCH" in json.loads(direct.stdout)["reason_codes"]


def test_confinement_plan_is_minimal_hash_bound_and_replayable(tmp_path: Path) -> None:
    root, _, work_order, preflight_path, fake_worker, plan = make_confinement_fixture(
        tmp_path
    )
    assert plan["schema"] == CONFINEMENT_PLAN_SCHEMA
    assert plan["verdict"] == "PASS"
    assert plan["work_order_sha256"] == digest(work_order)
    assert plan["preflight_receipt_sha256"] == digest(preflight_path)
    assert [mount["relative"] for mount in plan["writable_mounts"]] == ["allowed"]
    assert {mount["purpose"] for mount in plan["read_only_mounts"]} >= {"worktree"}
    assert plan["namespace"]["root"] == "read-only"
    assert plan["namespace"]["network"] == "host"

    plan_path = write_json(tmp_path / "confinement-plan.json", plan)
    command = [str(fake_worker), "--fixture"]
    first, first_argv = prepare_confinement_execution(
        plan_path,
        work_order,
        preflight_path,
        root,
        command,
    )
    second, second_argv = prepare_confinement_execution(
        plan_path,
        work_order,
        preflight_path,
        root,
        command,
    )
    assert first["schema"] == CONFINEMENT_EXECUTION_SCHEMA
    assert first["verdict"] == "PASS"
    assert first == second
    assert first_argv == second_argv == confinement_bwrap_argv(plan, command)
    assert first_argv is not None
    assert first_argv[-len(command) :] == command
    assert ["--ro-bind", "/", "/"] == first_argv[
        first_argv.index("--ro-bind") : first_argv.index("--ro-bind") + 3
    ]
    writable = str((root / "allowed").resolve())
    bind_index = first_argv.index("--bind")
    assert first_argv[bind_index : bind_index + 3] == ["--bind", writable, writable]
    assert "--unshare-net" not in first_argv


def test_missing_bubblewrap_blocks_before_worker_launch(tmp_path: Path) -> None:
    root, constitution, work_order, preflight_path, fake_worker, _ = (
        make_confinement_fixture(tmp_path)
    )
    receipt = build_confinement_plan(
        work_order,
        constitution,
        root,
        preflight_path,
        fake_worker,
        bwrap_path=tmp_path / "missing-bwrap",
        trusted_bwrap_owner=os.getuid(),
    )
    assert receipt["verdict"] == "REJECT"
    assert "BUBBLEWRAP_UNAVAILABLE" in receipt["reason_codes"]


def test_unrepresentable_and_symlink_mount_roots_fail_closed(tmp_path: Path) -> None:
    root, constitution, work_order, _, fake_worker, original_plan = (
        make_confinement_fixture(tmp_path)
    )
    fake_bwrap = Path(original_plan["bubblewrap"]["resolved"])

    value = json.loads(work_order.read_text(encoding="utf-8"))
    value["scope"]["allowed_paths"] = ["not-created"]
    value["completion"]["claim_marker"] = "not-created/OBJECTIVE_COMPLETE"
    write_json(work_order, value)
    missing_preflight = write_json(
        tmp_path / "missing-preflight.json",
        preflight(work_order, constitution, root),
    )
    missing = build_confinement_plan(
        work_order,
        constitution,
        root,
        missing_preflight,
        fake_worker,
        bwrap_path=fake_bwrap,
        trusted_bwrap_owner=os.getuid(),
    )
    assert missing["verdict"] == "REJECT"
    assert "MOUNT_PATH_UNREPRESENTABLE" in missing["reason_codes"]

    (root / "allowed-link").symlink_to("allowed", target_is_directory=True)
    git(root, "add", "allowed-link")
    git(root, "commit", "-m", "add symlink mount root")
    value["starting_state"] = capture_git_state(root)
    value["rollback"]["reference"] = value["starting_state"]["commit"]
    value["rollback"]["starting_state_sha256"] = value["starting_state"][
        "state_sha256"
    ]
    value["scope"]["allowed_paths"] = ["allowed-link"]
    value["completion"]["claim_marker"] = "allowed-link/OBJECTIVE_COMPLETE"
    write_json(work_order, value)
    symlink_preflight = write_json(
        tmp_path / "symlink-preflight.json",
        preflight(work_order, constitution, root),
    )
    symlink = build_confinement_plan(
        work_order,
        constitution,
        root,
        symlink_preflight,
        fake_worker,
        bwrap_path=fake_bwrap,
        trusted_bwrap_owner=os.getuid(),
    )
    assert symlink["verdict"] == "REJECT"
    assert "MOUNT_SYMLINK_UNSAFE" in symlink["reason_codes"]


def test_git_mutation_and_stale_mount_identity_are_blocked(tmp_path: Path) -> None:
    root, constitution, work_order, preflight_path, fake_worker, plan = (
        make_confinement_fixture(tmp_path)
    )
    fake_bwrap = Path(plan["bubblewrap"]["resolved"])
    value = json.loads(work_order.read_text(encoding="utf-8"))
    value["scope"]["allowed_actions"].append("git_commit")
    write_json(work_order, value)
    git_preflight = write_json(
        tmp_path / "git-preflight.json",
        preflight(work_order, constitution, root),
    )
    git_plan = build_confinement_plan(
        work_order,
        constitution,
        root,
        git_preflight,
        fake_worker,
        bwrap_path=fake_bwrap,
        trusted_bwrap_owner=os.getuid(),
    )
    assert git_plan["verdict"] == "REJECT"
    assert "MOUNT_ACTION_UNREPRESENTABLE" in git_plan["reason_codes"]

    value["scope"]["allowed_actions"].remove("git_commit")
    write_json(work_order, value)
    preflight_path = write_json(
        preflight_path,
        preflight(work_order, constitution, root),
    )
    plan = build_confinement_plan(
        work_order,
        constitution,
        root,
        preflight_path,
        fake_worker,
        bwrap_path=fake_bwrap,
        trusted_bwrap_owner=os.getuid(),
    )
    assert plan["verdict"] == "PASS"
    plan_path = write_json(tmp_path / "stale-plan.json", plan)
    (root / "allowed" / "changed-after-plan.txt").write_text(
        "changed\n", encoding="utf-8"
    )
    execution, argv = prepare_confinement_execution(
        plan_path,
        work_order,
        preflight_path,
        root,
        [str(fake_worker)],
    )
    assert execution["verdict"] == "REJECT"
    assert "MOUNT_IDENTITY_MISMATCH" in execution["reason_codes"]
    assert argv is None


def test_completion_is_bound_to_confinement_receipts(tmp_path: Path) -> None:
    root, constitution, work_order, preflight_path, fake_worker, plan = (
        make_confinement_fixture(tmp_path)
    )
    plan_path = write_json(tmp_path / "confinement-plan.json", plan)
    execution, argv = prepare_confinement_execution(
        plan_path,
        work_order,
        preflight_path,
        root,
        [str(fake_worker)],
    )
    assert execution["verdict"] == "PASS"
    assert argv is not None
    execution_path = write_json(tmp_path / "confinement-execution.json", execution)
    (root / "allowed" / "OBJECTIVE_COMPLETE").write_text("complete\n", encoding="utf-8")
    completion = run_completion_proofs(
        work_order,
        constitution,
        root,
        preflight_path,
        tmp_path / "evidence",
        plan_path,
        execution_path,
    )
    assert completion["verdict"] == "PASS"
    assert completion["write_confinement"] == {
        "execution_receipt_sha256": digest(execution_path),
        "plan_receipt_sha256": digest(plan_path),
    }
    completion_path = write_json(tmp_path / "completion.json", completion)
    first = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
        plan_path,
        execution_path,
    )
    second = verify_completion(
        work_order,
        constitution,
        root,
        preflight_path,
        completion_path,
        plan_path,
        execution_path,
    )
    assert first == second
    assert first["verdict"] == "PASS"


def test_installed_lane_path_requires_gate_then_turnstile_without_bypass() -> None:
    script = Path(__file__).parent / "dual_lane_20260726" / "run_native_lane.sh"
    source = script.read_text(encoding="utf-8")
    assert "work-order.json" in source
    assert "constitution preflight" in source
    assert "constitution plan-confinement" in source
    assert "constitution run-confined" in source
    assert "factory_turnstile.py" in source
    assert source.index("constitution preflight") < source.index("worker --actor codex")
    assert source.index("constitution plan-confinement") < source.index(
        "worker --actor codex"
    )
    assert source.index("worker --actor codex") < source.index(
        "constitution run-confined"
    )
    assert "--sandbox workspace-write" in source
    assert "--ephemeral" in source
    assert "--ignore-user-config" in source
    assert "--ignore-rules" in source
    assert "dangerously-bypass" not in source


def test_selected_successor_launcher_requires_bound_preflight_and_confinement() -> None:
    source_launcher = (
        Path(__file__).parents[2]
        / ".work"
        / "majaa-gigabyte-bootstrap-20260810"
        / "remote-control"
        / "run_agent_loop.sh"
    )
    script = Path(os.environ.get("GIGA_SUCCESSOR_LAUNCHER_PATH", source_launcher))
    source = script.read_text(encoding="utf-8")
    assert "--required-launcher" in source
    assert "gate_admission.py" in source
    assert "factory_turnstile.py" in source
    assert "constitution preflight" in source
    assert "worker --actor codex" in source
    assert "preflight-receipt.json" in source
    assert "write-confinement-plan.json" in source
    assert "run-confined" in source
    assert "OBJECTIVE_COMPLETE_VERIFIED" in source
    assert "COMPLETION_REJECTED" in source
    assert source.index('"$gate" constitution preflight') < source.index("worker_command=(")
    assert source.index('"$gate" constitution plan-confinement') < source.index("worker_command=(")
    assert source.index("worker_command=(") < source.index('"$gate" constitution run-confined')
    assert source.index('"$turnstile"') < source.index('"$gate" constitution run-confined')
    assert "--sandbox workspace-write" in source
    assert "--ephemeral" in source
    assert "LAUNCHER_SESSION_RESUME_UNREPRESENTABLE" in source
    assert "--required-wait-wrapper" in source
    assert "--required-worker-unit" in source
    assert "--required-worker-unit-file" in source
    assert "WAIT_CHAIN_INPUT_INCOMPLETE" in source
    assert "MAJAA_WORKER_EXECUTABLE" in source
    assert "dangerously-bypass" not in source
    loop_start = source.index("while ((")
    round_plan = source.index('round_confinement_plan="$round_dir/write-confinement-plan.json"')
    confined_run = source.index('"$gate" constitution run-confined')
    assert loop_start < round_plan < confined_run
    assert source.count('--confinement-plan "$round_confinement_plan"') == 3
    assert "reusing a stale filesystem identity" in source
    completion_rejected = source.index("printf 'COMPLETION_REJECTED")
    assert source.index("exit 42", completion_rejected) > completion_rejected


def test_selected_wait_wrapper_uses_bound_constitutional_launcher_only() -> None:
    root = Path(__file__).parent
    wrapper = root / "dual_lane_20260730" / "run_jaa_successor3_wait.sh"
    unit = root / "dual_lane_20260730" / "giga-jaa-single-codex-successor3.service"
    source = wrapper.read_text(encoding="utf-8")
    unit_source = unit.read_text(encoding="utf-8")
    assert "GIGA_REQUIRED_WAIT_WRAPPER" in source
    assert "GIGA_REQUIRED_WORKER_UNIT" in source
    assert "GIGA_REQUIRED_WORKER_UNIT_FILE" in source
    assert "MAJAA_WORK_ORDER_PATH" in source
    assert ".control/majaa-24h-20260810/bin/run_agent_loop.sh" in source
    assert "run_jaa_single_codex_supervisor.sh" not in source
    assert '"$downstream_launcher" "$lane" "$worktree" "$prompt" "$total_seconds"' in source
    assert "exec \"$downstream_launcher\"" not in source
    assert "RestartPreventExitStatus=42" in unit_source


def test_second_writer_for_same_worktree_fails_closed(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    leases = tmp_path / "leases"
    with exclusive_worktree_lease(worktree, lease_root=leases):
        with pytest.raises(WriterLeaseUnavailable):
            with exclusive_worktree_lease(worktree, lease_root=leases):
                pass


def test_distinct_worktrees_have_distinct_writer_leases(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    leases = tmp_path / "leases"
    with exclusive_worktree_lease(first, lease_root=leases):
        with exclusive_worktree_lease(second, lease_root=leases):
            pass


@pytest.mark.skipif(sys.platform != "linux", reason="process liveness uses Linux /proc")
def test_writer_timeout_terminates_owned_process_group(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    leases = tmp_path / "leases"
    child_pid = tmp_path / "child.pid"
    run_dir = tmp_path / "run"
    script = (
        "import pathlib,subprocess,sys,time;"
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
        f"pathlib.Path({str(child_pid)!r}).write_text(str(p.pid));"
        "time.sleep(60)"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        run_writer_command(
            worktree,
            [sys.executable, "-c", script],
            timeout_seconds=0.2,
            lease_root=leases,
            run_dir=run_dir,
        )
    for _ in range(50):
        if child_pid.exists():
            break
        time.sleep(0.01)
    pid = int(child_pid.read_text())
    for _ in range(100):
        stat_path = Path(f"/proc/{pid}/stat")
        if not stat_path.exists() or stat_path.read_text().split()[2] == "Z":
            break
        time.sleep(0.01)
    else:
        os.kill(pid, 0)
        pytest.fail("writer child survived process-group termination")
    invocation = json.loads((run_dir / "invocation.json").read_text())
    launched = json.loads((run_dir / "launched.json").read_text())
    timeout = json.loads((run_dir / "timeout.json").read_text())
    termination = json.loads((run_dir / "termination.json").read_text())
    settlement = json.loads((run_dir / "settlement.json").read_text())
    assert invocation["invocation_id"] == launched["invocation_id"] == timeout["invocation_id"]
    assert termination["invocation_id"] == settlement["invocation_id"] == invocation["invocation_id"]
    assert timeout["reason"] == "TIMEOUT"
    assert settlement["outcome"] == "INTERRUPTED"
    assert settlement["usage"]["status"] == "UNKNOWN"


def test_writer_completion_captures_output_and_usage(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    run_dir = tmp_path / "run"
    result = run_writer_command(
        worktree,
        [
            sys.executable,
            "-c",
            "import json;print(json.dumps({'total_cost_usd':0.125,'session_id':'s-1'}))",
        ],
        timeout_seconds=5,
        lease_root=tmp_path / "leases",
        run_dir=run_dir,
    )
    assert result == 0
    assert "total_cost_usd" in (run_dir / "stdout.jsonl").read_text()
    settlement = json.loads((run_dir / "settlement.json").read_text())
    assert settlement["usage"] == {
        "session_id": "s-1",
        "status": "KNOWN",
        "total_cost_usd": 0.125,
    }


def test_supervisor_sigkill_preserves_invocation_and_partial_output(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    run_dir = tmp_path / "run"
    driver = (
        "import pathlib,sys;"
        f"sys.path.insert(0,{str(Path(__file__).parent)!r});"
        "from gate_admission import run_writer_command;"
        f"run_writer_command(pathlib.Path({str(worktree)!r}),"
        "[sys.executable,'-c',\"import sys,time;print('partial',flush=True);time.sleep(60)\"],"
        f"timeout_seconds=60,lease_root=pathlib.Path({str(tmp_path / 'leases')!r}),"
        f"run_dir=pathlib.Path({str(run_dir)!r}))"
    )
    supervisor = subprocess.Popen([sys.executable, "-c", driver], start_new_session=True)
    for _ in range(200):
        if (run_dir / "launched.json").exists() and (run_dir / "stdout.jsonl").exists():
            if "partial" in (run_dir / "stdout.jsonl").read_text():
                break
        time.sleep(0.01)
    else:
        pytest.fail("durable launch/partial-output evidence was not created")
    launched = json.loads((run_dir / "launched.json").read_text())
    os.kill(supervisor.pid, 9)
    assert supervisor.wait(timeout=5) == -9
    assert (run_dir / "invocation.json").exists()
    assert "partial" in (run_dir / "stdout.jsonl").read_text()
    os.killpg(launched["pid"], 9)
