#!/usr/bin/env python3
"""Build deterministic, non-executing migration batches for the authorised target.

The output is an execution contract, not permission to move files. Every batch
still requires the root-move lock, sealed preflight state, compatibility
closure, tests, and an immutable migration receipt.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
AUTHORITY_MAP = HERE / "authority-map.v1.json"
OUTPUT = HERE / "MIGRATION_BATCHES.v1.json"
EXECUTABLE_INVENTORY = (
    ROOT
    / "architecture/modularization/preflight/executable/executable-inventory.json"
)


SCRIPT_ROUTES = {
    "scripts/audit_root_layout.py": "modules/platform/scripts/audit_root_layout.py",
    "scripts/capture_machine_source_snapshot.py": "modules/platform/scripts/capture_machine_source_snapshot.py",
    "scripts/build_skill_inventory.py": "modules/skills/tooling/build_skill_inventory.py",
    "scripts/export_skilltree.py": "modules/skills/tooling/export_skilltree.py",
    "scripts/extract_skilltree_data.mjs": "modules/skills/tooling/extract_skilltree_data.mjs",
    "scripts/inventory_filesystem_skills.py": "modules/skills/tooling/inventory_filesystem_skills.py",
    "scripts/analyze_unified_memory.py": "modules/digital-twin/scripts/analyze_unified_memory.py",
    "scripts/build_instagram_pairs.py": "modules/digital-twin/scripts/build_instagram_pairs.py",
    "scripts/build_unified_memory.py": "modules/digital-twin/scripts/build_unified_memory.py",
    "scripts/chatgpt_monthly_index.py": "modules/digital-twin/scripts/chatgpt_monthly_index.py",
    "scripts/daily_personal_knowledge.py": "modules/digital-twin/scripts/daily_personal_knowledge.py",
    "scripts/evaluate_persona_lora.py": "modules/digital-twin/training/scripts/evaluate_persona_lora.py",
    "scripts/extract_chatgpt.py": "modules/digital-twin/scripts/extract_chatgpt.py",
    "scripts/extract_discord.py": "modules/digital-twin/scripts/extract_discord.py",
    "scripts/extract_instagram.py": "modules/digital-twin/scripts/extract_instagram.py",
    "scripts/extract_instagram_full.py": "modules/digital-twin/scripts/extract_instagram_full.py",
    "scripts/extract_prompts.py": "modules/digital-twin/scripts/extract_prompts.py",
    "scripts/extract_telegram.py": "modules/digital-twin/scripts/extract_telegram.py",
    "scripts/jarvis_telegram.py": "modules/digital-twin/scripts/jarvis_telegram.py",
    "scripts/load_memory_claims.py": "modules/digital-twin/scripts/load_memory_claims.py",
    "scripts/prepare_finetune_data.py": "modules/digital-twin/training/scripts/prepare_finetune_data.py",
    "scripts/prepare_persona_lora.py": "modules/digital-twin/training/scripts/prepare_persona_lora.py",
    "scripts/process_transcript.py": "modules/digital-twin/scripts/process_transcript.py",
    "scripts/profile_corpus_audit.py": "modules/digital-twin/scripts/profile_corpus_audit.py",
    "scripts/retrospective.py": "modules/digital-twin/scripts/retrospective.py",
    "scripts/run_daily_personal_knowledge.sh": "modules/digital-twin/scripts/run_daily_personal_knowledge.sh",
    "scripts/run_jarvis.sh": "modules/digital-twin/scripts/run_jarvis.sh",
    "scripts/train_casual_v0.sh": "modules/digital-twin/training/scripts/train_casual_v0.sh",
    "scripts/prediction_automation.py": "modules/calibration/scripts/prediction_automation.py",
    "scripts/sovereignty_index.py": "modules/sovereignty/scripts/sovereignty_index.py",
    "scripts/analyze_skin_evidence.py": "modules/research/scripts/analyze_skin_evidence.py",
    "scripts/elicit_evidence.py": "modules/research/scripts/elicit_evidence.py",
    "scripts/run_elicit_campaign.py": "modules/research/scripts/run_elicit_campaign.py",
    "scripts/run_scientific_campaign.py": "modules/research/scripts/run_scientific_campaign.py",
    "scripts/scientific_evidence.py": "modules/research/scripts/scientific_evidence.py",
    "scripts/scientific_pipeline.py": "modules/research/scripts/scientific_pipeline.py",
    "scripts/compile_sop.py": "modules/proof/scripts/compile_sop.py",
    "scripts/render_external_proof_deck.mjs": "modules/proof/scripts/render_external_proof_deck.mjs",
    "scripts/collect_cross_service_telemetry.py": "modules/operations/scripts/collect_cross_service_telemetry.py",
    "scripts/compile_adapter_evidence.py": "modules/operations/scripts/compile_adapter_evidence.py",
    "scripts/operator_status.py": "modules/operations/scripts/operator_status.py",
}

TEST_ROUTES = {
    "tests/test_root_layout.py": "modules/platform/tests/test_root_layout.py",
    "tests/test_machine_source_snapshot.py": "modules/platform/tests/test_machine_source_snapshot.py",
    "tests/test_skilltree_operator.py": "modules/skills/tests/test_skilltree_operator.py",
    "tests/test_analyze_unified_memory.py": "modules/digital-twin/tests/test_analyze_unified_memory.py",
    "tests/test_build_unified_memory.py": "modules/digital-twin/tests/test_build_unified_memory.py",
    "tests/test_chatgpt_monthly_index.py": "modules/digital-twin/tests/test_chatgpt_monthly_index.py",
    "tests/test_context_compiler.py": "modules/digital-twin/tests/test_context_compiler.py",
    "tests/test_daily_personal_knowledge.py": "modules/digital-twin/tests/test_daily_personal_knowledge.py",
    "tests/test_extract_chatgpt_namespace.py": "modules/digital-twin/tests/test_extract_chatgpt_namespace.py",
    "tests/test_extract_discord.py": "modules/digital-twin/tests/test_extract_discord.py",
    "tests/test_extract_instagram_full.py": "modules/digital-twin/tests/test_extract_instagram_full.py",
    "tests/test_extract_prompts_namespaces.py": "modules/digital-twin/tests/test_extract_prompts_namespaces.py",
    "tests/test_extract_telegram.py": "modules/digital-twin/tests/test_extract_telegram.py",
    "tests/test_integrity.py": "modules/digital-twin/tests/test_integrity.py",
    "tests/test_jarvis_telegram.py": "modules/digital-twin/tests/test_jarvis_telegram.py",
    "tests/test_lineage.py": "modules/digital-twin/tests/test_lineage.py",
    "tests/test_load_memory_claims.py": "modules/digital-twin/tests/test_load_memory_claims.py",
    "tests/test_memory_proposals.py": "modules/digital-twin/tests/test_memory_proposals.py",
    "tests/test_memory_validation.py": "modules/digital-twin/tests/test_memory_validation.py",
    "tests/test_prepare_finetune_data.py": "modules/digital-twin/training/tests/test_prepare_finetune_data.py",
    "tests/test_prepare_persona_lora.py": "modules/digital-twin/training/tests/test_prepare_persona_lora.py",
    "tests/test_telegram_pipeline.py": "modules/digital-twin/tests/test_telegram_pipeline.py",
    "tests/test_transcript_actions.py": "modules/digital-twin/tests/test_transcript_actions.py",
    "tests/test_twin_store.py": "modules/digital-twin/tests/test_twin_store.py",
    "tests/test_prediction_automation.py": "modules/calibration/tests/test_prediction_automation.py",
    "tests/test_sovereignty.py": "modules/sovereignty/tests/test_sovereignty.py",
    "tests/test_analyze_skin_evidence.py": "modules/research/tests/test_analyze_skin_evidence.py",
    "tests/test_scientific_campaign.py": "modules/research/tests/test_scientific_campaign.py",
    "tests/test_scientific_evidence.py": "modules/research/tests/test_scientific_evidence.py",
    "tests/test_scientific_pipeline.py": "modules/research/tests/test_scientific_pipeline.py",
    "tests/test_scientific_providers.py": "modules/research/tests/test_scientific_providers.py",
    "tests/test_scientific_review_funnel.py": "modules/research/tests/test_scientific_review_funnel.py",
    "tests/test_external_proof.py": "modules/proof/tests/test_external_proof.py",
    "tests/test_external_proof_deck.py": "modules/proof/tests/test_external_proof_deck.py",
    "tests/test_sop_compiler.py": "modules/proof/tests/test_sop_compiler.py",
    "tests/test_adapter_evidence.py": "modules/operations/tests/test_adapter_evidence.py",
    "tests/test_cross_service_monitor.py": "modules/operations/tests/test_cross_service_monitor.py",
    "tests/test_operator_status.py": "modules/operations/tests/test_operator_status.py",
}


def move(source: str, destination: str, action: str = "move") -> dict[str, str]:
    return {"source": source, "destination": destination, "action": action}


def routed(routes: dict[str, str], prefix: str) -> list[dict[str, str]]:
    return [
        move(source, destination)
        for source, destination in routes.items()
        if destination.startswith(prefix)
    ]


def make_batch(
    identifier: str,
    order: int,
    owner: str,
    moves: list[dict[str, str]],
    *,
    depends_on: list[str] | None = None,
    compatibility_updates: list[dict[str, str]],
    tests: list[str],
    rollback_checks: list[str],
) -> dict[str, Any]:
    sources = [item["source"] for item in moves]
    destinations = [item["destination"] for item in moves]
    digest = hashlib.sha256("\n".join(sorted(sources)).encode("utf-8")).hexdigest()
    return {
        "id": identifier,
        "order": order,
        "status": "ready-after-lock-and-preconditions",
        "owner": owner,
        "depends_on": depends_on or [],
        "lock_required": True,
        "source_paths": sources,
        "source_path_set_sha256": digest,
        "moves": moves,
        "compatibility_updates": compatibility_updates,
        "tests": tests,
        "rollback_checks": rollback_checks,
        "expected_post_move_paths": destinations,
        "preconditions": [
            "authority-map and migration-batch validators pass against the live root",
            "root-move lock acquired and bound to HEAD, dirty-state digest and this source-path-set hash",
            "pre-move hashes/tree digests and reference closure sealed",
            "dry-run proves destinations do not exist and rollback is possible",
        ],
    }


def build() -> dict[str, Any]:
    authority = json.loads(AUTHORITY_MAP.read_text(encoding="utf-8"))
    batches = [
        make_batch(
            "B010-historical-authority-archive",
            10,
            "GIGA architecture",
            [
                move("FABLE_V3_DESIGN_REVIEW.md", "archive/orchestrator/reviews/2026-07-18/FABLE_V3_DESIGN_REVIEW.md"),
                move("ORCHESTRATOR_AND_GIGA_USER_ARCHITECTURE.md", "archive/architecture/snapshots/2026-07/ORCHESTRATOR_AND_GIGA_USER_ARCHITECTURE.md"),
                move("V3_CONTRACT_DECISIONS.md", "archive/orchestrator/decisions/V3_CONTRACT_DECISIONS.md"),
                move("tier1-findings.md", "archive/orchestrator/findings/tier1-findings.md"),
                move("overseer_fable_exec.patch", "archive/orchestrator/patches/overseer_fable_exec.patch"),
                move("phase2_sol_exec.patch", "archive/orchestrator/patches/phase2_sol_exec.patch"),
            ],
            compatibility_updates=[
                {"path": "architecture/current-authority-index.v1.json", "change": "Point current authority to machine-readable contracts and mark all six sources historical."},
                {"path": "repository references", "change": "Rewrite historical links or install temporary read-only compatibility shims."},
            ],
            tests=[
                "python3 architecture/modularization/preflight/authority/validate_authority_map.py",
                "rg -n 'FABLE_V3_DESIGN_REVIEW|ORCHESTRATOR_AND_GIGA_USER_ARCHITECTURE|V3_CONTRACT_DECISIONS|tier1-findings|overseer_fable_exec|phase2_sol_exec' --glob '!archive/**' .",
            ],
            rollback_checks=[
                "all six archived byte hashes equal their sealed source hashes",
                "compatibility shims resolve each former root path without granting current authority",
            ],
        ),
        make_batch(
            "B020-project-registration",
            20,
            "GIGA project portfolio",
            [
                move("company-admin", "projects/company-admin"),
                move("TRAVEL_DESIGNER_GOAL.md", "projects/travel-designer/GOAL.md"),
            ],
            compatibility_updates=[
                {"path": "projects/registry.v1.json", "change": "Register company-admin and travel-designer owners, lifecycle and canonical paths."},
                {"path": "architecture/root-layout.v1.json", "change": "Replace both legacy root exceptions with project paths."},
            ],
            tests=[
                "python3 tests/test_root_layout.py",
                "python3 -m json.tool projects/registry.v1.json >/dev/null",
            ],
            rollback_checks=[
                "project registry can be reverted without losing project files",
                "company evidence and deadline ledger hashes match the source tree seal",
            ],
        ),
        make_batch(
            "B030-specialised-skills",
            30,
            "giga-user platform",
            [
                move("deploy/skills/librarian", "modules/skills/owned/librarian"),
                move("deploy/skills/skilltree-operator", "modules/skills/owned/skilltree-operator"),
                move("deploy/skills/librarian-workspace", "modules/skills/evaluations/librarian"),
                move("skilltree", "modules/skills/capability-registry"),
                move("SKILLTREE_GIGA_USER_INTEGRATION.md", "modules/skills/docs/SKILLTREE_GIGA_USER_INTEGRATION.md"),
                *routed(SCRIPT_ROUTES, "modules/skills/"),
                *routed(TEST_ROUTES, "modules/skills/"),
            ],
            compatibility_updates=[
                {"path": "AGENTS.md and deploy consumers", "change": "Rewrite owned-skill and implementation-registry paths; preserve router/install boundaries."},
                {"path": "host skill catalogs", "change": "Index only; do not copy active personal/system, plugin, marketplace, cache or upstream skills into owned source."},
            ],
            tests=[
                "python3 modules/skills/tests/test_skilltree_operator.py",
                "python3 /Users/admin/.codex/skills/skill-router/scripts/audit_skills.py --write /Users/admin/.codex/skills/skill-router/references/installed-skills.json --check --agents /Users/admin/.codex/AGENTS.md",
            ],
            rollback_checks=[
                "owned skill manifests match sealed source hashes",
                "all five skill authority classes remain distinct and no external cache became owned",
            ],
        ),
        make_batch(
            "B040-platform-foundations",
            40,
            "GIGA platform",
            [
                move("contracts", "modules/platform/contracts"),
                move("examples", "modules/platform/examples"),
                move("MODEL_AGNOSTIC_SPEC.md", "modules/platform/policies/MODEL_AGNOSTIC_SPEC.md"),
                move("adapters", "modules/integrations/adapters"),
                *routed(SCRIPT_ROUTES, "modules/platform/"),
                *routed(TEST_ROUTES, "modules/platform/"),
            ],
            depends_on=["B030-specialised-skills"],
            compatibility_updates=[
                {"path": "Python imports and shell entrypoints", "change": "Rewrite contract, adapter and platform-tool paths; retain compatibility launchers until closure."},
                {"path": "architecture/root-layout.v1.json", "change": "Register platform and integration module destinations."},
            ],
            tests=[
                "python3 -m unittest modules.platform.tests.test_root_layout modules.platform.tests.test_machine_source_snapshot",
                "python3 -m compileall -q modules/platform modules/integrations/adapters",
            ],
            rollback_checks=[
                "all platform tree digests match pre-move seals",
                "old import and CLI surfaces remain resolvable through reversible shims",
            ],
        ),
        make_batch(
            "B050-digital-twin-core",
            50,
            "GIGA virtual-twin workstream",
            [
                move("twin_core", "modules/digital-twin/core"),
                move("FINE_TUNING_READINESS.md", "modules/digital-twin/training/FINE_TUNING_READINESS.md"),
                *routed(SCRIPT_ROUTES, "modules/digital-twin/"),
                *routed(TEST_ROUTES, "modules/digital-twin/"),
            ],
            depends_on=["B040-platform-foundations"],
            compatibility_updates=[
                {"path": "all Python imports, cron/launchd commands and shell wrappers", "change": "Rewrite twin_core and script/test paths; keep compatibility package and launchers until full-suite success."},
                {"path": "00_MASTER.md and virtual-twin briefs", "change": "Update canonical implementation and training-readiness links."},
            ],
            tests=[
                "python3 -m unittest discover -s modules/digital-twin/tests -p 'test_*.py' -v",
                "python3 -m compileall -q modules/digital-twin",
            ],
            rollback_checks=[
                "canonical memory/corpus protected-source hashes remain unchanged",
                "old twin_core imports and script entrypoints still resolve before source retirement",
            ],
        ),
        make_batch(
            "B060-agency-modules",
            60,
            "GIGA calibration and sovereignty workstreams",
            [
                move("PREDICTION_AUTOMATION.md", "modules/calibration/PREDICTION_AUTOMATION.md"),
                move("SOVEREIGNTY_INDEX.md", "modules/sovereignty/README.md"),
                *routed(SCRIPT_ROUTES, "modules/calibration/"),
                *routed(SCRIPT_ROUTES, "modules/sovereignty/"),
                *routed(TEST_ROUTES, "modules/calibration/"),
                *routed(TEST_ROUTES, "modules/sovereignty/"),
            ],
            depends_on=["B040-platform-foundations", "B050-digital-twin-core"],
            compatibility_updates=[
                {"path": "05_CALIBRATION_PROMPTBANK_BRIEF.md and sovereignty consumers", "change": "Rewrite module documentation, schema and command paths."},
            ],
            tests=[
                "python3 -m unittest modules.calibration.tests.test_prediction_automation modules.sovereignty.tests.test_sovereignty",
            ],
            rollback_checks=[
                "prediction and sovereignty fixtures produce the same outputs before and after the move",
                "legacy command shims can be removed only after schedule/reference closure",
            ],
        ),
        make_batch(
            "B070-research-tooling",
            70,
            "GIGA research tooling",
            [
                *routed(SCRIPT_ROUTES, "modules/research/"),
                *routed(TEST_ROUTES, "modules/research/"),
            ],
            depends_on=["B040-platform-foundations"],
            compatibility_updates=[
                {"path": "research command references", "change": "Rewrite tooling paths without moving protected research evidence."},
            ],
            tests=[
                "python3 -m unittest discover -s modules/research/tests -p 'test_*.py' -v",
            ],
            rollback_checks=[
                "research/ evidence tree hash is unchanged",
                "tool outputs remain candidate-bound and reproducible",
            ],
        ),
        make_batch(
            "B080-proof-compiler",
            80,
            "GIGA evidence/proof compiler",
            [
                move("external_proof", "modules/proof/external"),
                *routed(SCRIPT_ROUTES, "modules/proof/"),
                *routed(TEST_ROUTES, "modules/proof/"),
            ],
            depends_on=["B050-digital-twin-core"],
            compatibility_updates=[
                {"path": "proof build commands and report links", "change": "Rewrite source, renderer and test paths while preserving output receipts."},
            ],
            tests=[
                "python3 -m unittest discover -s modules/proof/tests -p 'test_*.py' -v",
            ],
            rollback_checks=[
                "rendered proof hashes or declared nondeterminism match the sealed baseline",
                "source citations still resolve to canonical evidence",
            ],
        ),
        make_batch(
            "B090-operations-and-deployment",
            90,
            "GIGA operations and deployment",
            [
                move("migration", "modules/operations/migration"),
                move("monitoring", "modules/operations/monitoring"),
                move("deploy/chatgpt_custom_instructions.txt", "modules/deployment/surfaces/chatgpt_custom_instructions.txt"),
                move("deploy/claude_preferences.txt", "modules/deployment/surfaces/claude_preferences.txt"),
                move("deploy/v3_operator_model.md", "modules/deployment/surfaces/v3_operator_model.md"),
                move("deploy/gutua", "modules/deployment/gutua"),
                move("deploy/launchd", "modules/deployment/launchd"),
                *routed(SCRIPT_ROUTES, "modules/operations/"),
                *routed(TEST_ROUTES, "modules/operations/"),
            ],
            depends_on=["B030-specialised-skills", "B040-platform-foundations", "B050-digital-twin-core"],
            compatibility_updates=[
                {"path": "launchd/systemd/cron and Gutua deployment manifests", "change": "Rewrite commands atomically; preserve old launchers disabled-but-restorable until health checks pass."},
                {"path": "machine authority and migration receipts", "change": "Bind new module paths to Mac canonical/Gutua candidate policy."},
            ],
            tests=[
                "python3 -m unittest discover -s modules/operations/tests -p 'test_*.py' -v",
                "launchctl print gui/$(id -u) >/dev/null",
            ],
            rollback_checks=[
                "all service definitions have captured pre-move state and reversible install commands",
                "old deployment paths remain available until service health and telemetry pass",
            ],
        ),
        make_batch(
            "B100-ecc-integration",
            100,
            "GIGA integration boundary",
            [
                move("ecc-integration/COMPONENT_INVENTORY.json", "modules/integrations/ecc/COMPONENT_INVENTORY.json"),
                move("ecc-integration/DEEP_ANALYSIS.md", "modules/integrations/ecc/DEEP_ANALYSIS.md"),
                move("ecc-integration/EXTRACTION_COMPLETE.md", "modules/integrations/ecc/EXTRACTION_COMPLETE.md"),
                move("ecc-integration/FIRST_IMPLEMENTATION_DECISION.md", "modules/integrations/ecc/FIRST_IMPLEMENTATION_DECISION.md"),
                move("ecc-integration/FUTURE_WORK.md", "modules/integrations/ecc/FUTURE_WORK.md"),
                move("ecc-integration/IMPORT_LEDGER.json", "modules/integrations/ecc/IMPORT_LEDGER.json"),
                move("ecc-integration/PORTABLE_FINDINGS.json", "modules/integrations/ecc/PORTABLE_FINDINGS.json"),
                move("ecc-integration/SECURITY_REVIEW.md", "modules/integrations/ecc/SECURITY_REVIEW.md"),
                move("ecc-integration/SKILL_CLASSIFICATION.json", "modules/integrations/ecc/SKILL_CLASSIFICATION.json"),
                move("ecc-integration/UPSTREAM.json", "modules/integrations/ecc/UPSTREAM.json"),
                move("ecc-integration/UPSTREAM_SYNC.md", "modules/integrations/ecc/UPSTREAM_SYNC.md"),
                move("ecc-integration/candidate-imports", "modules/integrations/ecc/candidate-imports"),
                move("ecc-integration/scripts", "modules/integrations/ecc/scripts"),
                move("ecc-integration/tests", "modules/integrations/ecc/tests"),
            ],
            depends_on=["B030-specialised-skills", "B040-platform-foundations"],
            compatibility_updates=[
                {"path": "ECC import ledgers and upstream references", "change": "Rewrite authored integration paths; keep upstream source read-only and separately owned."},
            ],
            tests=[
                "python3 -m unittest discover -s modules/integrations/ecc/tests -p 'test_*.py' -v",
                "python3 -m json.tool modules/integrations/ecc/IMPORT_LEDGER.json >/dev/null",
            ],
            rollback_checks=[
                "candidate-import hashes and upstream provenance equal their source seals",
                "no generated Graphify content is present under the authored integration module",
            ],
        ),
        make_batch(
            "B110-external-upstreams",
            110,
            "GIGA external-workspace boundary",
            [move("upstreams", "external/upstreams")],
            depends_on=["B100-ecc-integration"],
            compatibility_updates=[
                {"path": "all upstream path references", "change": "Rewrite to external/upstreams and install a read-only compatibility path until reference closure."},
            ],
            tests=[
                "git -C external/upstreams/ECC status --short",
                "rg -n '(^|[ /])upstreams/' --glob '!external/**' .",
            ],
            rollback_checks=[
                "every upstream checkout HEAD/status/tree digest equals its pre-move seal",
                "no upstream file is promoted into GIGA-owned modules by relocation",
            ],
        ),
        make_batch(
            "B120-generated-runtime",
            120,
            "GIGA runtime",
            [
                move(".DS_Store", "runtime/cache/macos/.DS_Store"),
                move(".pytest_cache", "runtime/cache/pytest"),
                move(".ruff_cache", "runtime/cache/ruff"),
                move("graphify-out", "runtime/generated/graphify"),
                move("ecc-integration/graphify-out", "runtime/generated/ecc-graphify"),
                move("instagram_not_following_back.csv", "runtime/generated/instagram/not-following-back.csv"),
                move("instagram_unfollow_plan.json", "runtime/generated/instagram/unfollow-plan.json"),
                move("instagram_unfollow_progress.json", "runtime/state/instagram/unfollow-progress.json"),
                move("output", "runtime/generated/media"),
                move("outputs", "runtime/outputs"),
                move("tmp", "runtime/tmp"),
                move("scripts/__pycache__", "runtime/cache/python/scripts"),
                move("tests/__pycache__", "runtime/cache/python/tests"),
            ],
            depends_on=["B050-digital-twin-core", "B080-proof-compiler", "B090-operations-and-deployment", "B100-ecc-integration"],
            compatibility_updates=[
                {"path": "output producers, reports and receipts", "change": "Rewrite output/state paths; distinguish reproducible cache from evidence-bearing receipts."},
                {"path": ".gitignore", "change": "Ignore disposable runtime caches without ignoring evidence-bearing runtime outputs."},
            ],
            tests=[
                "python3 -m unittest discover -s tests -p 'test_*.py' -v",
                "python3 architecture/modularization/preflight/authority/validate_authority_map.py",
            ],
            rollback_checks=[
                "evidence-bearing output and receipt hashes equal their source seals",
                "every reproducible cache has a producer; non-reproducible output has a retention receipt",
            ],
        ),
        make_batch(
            "B130-quarantine-staging",
            130,
            "GIGA intake/quarantine",
            [move("staging", "quarantine/staging")],
            depends_on=["B090-operations-and-deployment", "B120-generated-runtime"],
            compatibility_updates=[
                {"path": "migration and candidate-bundle consumers", "change": "Rewrite staging references while preserving no-authority semantics."},
            ],
            tests=[
                "rg -n '(^|[ /])staging/' migration modules architecture",
                "python3 architecture/modularization/preflight/authority/validate_authority_map.py",
            ],
            rollback_checks=[
                "candidate bundles, receipts and schema-v3 candidate hashes match the pre-move seal",
                "quarantined presence grants no canonical authority",
            ],
        ),
    ]

    return {
        "schema": "giga.modularization.migration-batches.v1",
        "preflight_id": "wave-0d-authority-resolution-2026-07-31",
        "execution_authority": "plan-only; no move is authorised without ROOT_MOVE_LOCK.md acceptance gates",
        "root": str(ROOT),
        "authority_map": str(AUTHORITY_MAP.relative_to(ROOT)),
        "authority_map_sha256": hashlib.sha256(AUTHORITY_MAP.read_bytes()).hexdigest(),
        "executable_inventory": (
            str(EXECUTABLE_INVENTORY.relative_to(ROOT))
            if EXECUTABLE_INVENTORY.exists()
            else None
        ),
        "executable_inventory_sha256": (
            hashlib.sha256(EXECUTABLE_INVENTORY.read_bytes()).hexdigest()
            if EXECUTABLE_INVENTORY.exists()
            else None
        ),
        "root_move_lock": "ROOT_MOVE_LOCK.md",
        "source_set_semantics": "Every source path is exclusive across batches; parent paths are omitted when their children are split.",
        "script_routes": SCRIPT_ROUTES,
        "test_routes": TEST_ROUTES,
        "batches": batches,
        "deferred": [
            {
                "source": "life-admin",
                "reason": "A concurrent task created the workspace after the authority checkpoint; originating writer, ownership and reference closure are not yet reconciled.",
                "required_decision": "identify originating task, seal tree, register project, then migrate in a later isolated batch",
            },
            {
                "source": "market-aligner-artiom",
                "reason": "Machine authority identifies a candidate duplicate, but no reconciliation outcome is ratified.",
                "required_decision": "compare against canonical market-aligner, seal both trees, and ratify merge/archive/delete/quarantine outcome",
            }
        ],
        "no_touch": sorted(
            entry["source"]
            for entry in authority["entries"]
            if entry["disposition"] == "protected/no-touch"
        ),
        "retained": sorted(
            entry["source"]
            for entry in authority["entries"]
            if entry["disposition"] == "retain"
        ),
    }


def main() -> int:
    payload = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, OUTPUT)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
