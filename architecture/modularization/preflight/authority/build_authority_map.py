#!/usr/bin/env python3
"""Build the Wave 0A root-authority map from a reviewed disposition table.

This generator is deliberately non-mutating outside its own directory.  It
measures the live root, combines those measurements with explicit reviewed
decisions below, and emits the machine-readable preflight manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUTPUT = HERE / "authority-map.v1.json"
SKILL_INVENTORY = ROOT / "outputs/skill-filesystem-inventory-2026-07-30/inventory.json"


def reviewed(
    disposition: str,
    lifecycle: str,
    destination: str,
    authority: str,
    order: int,
    compatibility: str,
    *,
    dependencies: list[str] | None = None,
    provenance: list[str] | None = None,
    ambiguity: str | None = None,
    notes: str = "",
    subpath_exceptions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Return one reviewed mapping declaration."""

    default_provenance = {
        "retain": ["Preserve Git/file identity; record any later content mutation normally."],
        "move": [
            "Seal pre-move path, size and SHA-256/tree digest.",
            "Rewrite and verify all path references before promotion.",
            "Emit a source-to-destination migration receipt.",
        ],
        "externalize": [
            "Record ownership and canonical-host policy.",
            "Preserve candidate/history paths; promotion requires a separate receipt.",
        ],
        "archive": [
            "Preserve exact bytes and original path in the archive receipt.",
            "Record supersession/status before removing the live-path authority implication.",
        ],
        "generated": [
            "Identify the deterministic producer or record that output is non-reproducible.",
            "Do not delete evidence-bearing generated output without a retention decision.",
        ],
        "quarantine": [
            "Seal exact bytes/tree before relocation.",
            "Record the unresolved owner or classification; grant no authority by presence.",
        ],
        "protected/no-touch": [
            "Verify existing immutable/source hash where available.",
            "Never rewrite, normalize, delete or overwrite during modularization.",
        ],
    }
    return {
        "disposition": disposition,
        "lifecycle_status": lifecycle,
        "destination": destination,
        "canonical_authority": authority,
        "dependencies": dependencies or [],
        "provenance_requirements": provenance or default_provenance[disposition],
        "compatibility": {
            "level": compatibility,
            "required": compatibility not in {"none", "low"},
        },
        "migration_order": order,
        "wave0_move_authorized": False,
        "ambiguity": {
            "state": "blocked" if ambiguity else "resolved",
            "reason": ambiguity,
        },
        "notes": notes,
        "subpath_exceptions": subpath_exceptions or [],
    }


# One explicit declaration for every top-level path present at the reviewed
# snapshot.  Unknown new paths cause validation failure rather than inheriting
# a permissive default.
MAPPING: dict[str, dict[str, Any]] = {
    ".DS_Store": reviewed(
        "generated", "ephemeral-os-metadata", "runtime/cache/macos/.DS_Store",
        "architecture/root-layout.v1.json#ignored_root_patterns", 10, "none",
    ),
    ".gitignore": reviewed(
        "retain", "active-control", ".gitignore",
        "Git repository policy", 0, "critical",
    ),
    ".pytest_cache": reviewed(
        "generated", "ephemeral-test-cache", "runtime/cache/pytest",
        "pytest runtime convention", 10, "none",
    ),
    ".ruff_cache": reviewed(
        "generated", "ephemeral-lint-cache", "runtime/cache/ruff",
        "Ruff runtime convention", 10, "none",
    ),
    "00_MASTER.md": reviewed(
        "retain", "canonical-active", "00_MASTER.md",
        "00_MASTER.md#programme-progress", 0, "critical",
        dependencies=["SESSION_LOGS", "01_CHARTER_BRIEF.md", "CONTEXT.md"],
    ),
    "01_CHARTER_BRIEF.md": reviewed(
        "retain", "canonical-brief", "01_CHARTER_BRIEF.md",
        "architecture/root-layout.v1.json#zones.authority", 0, "critical",
        dependencies=["00_MASTER.md", "CHARTER.md", "SESSION_LOGS/01_log.md"],
    ),
    "02_MEMORY_CONTEXT_BRIEF.md": reviewed(
        "retain", "canonical-brief", "02_MEMORY_CONTEXT_BRIEF.md",
        "architecture/root-layout.v1.json#zones.authority", 0, "critical",
        dependencies=["00_MASTER.md", "CONTEXT.md", "CONTEXT_PROTOCOL.md"],
    ),
    "03_LIFE_INFRA_BRIEF.md": reviewed(
        "retain", "canonical-brief", "03_LIFE_INFRA_BRIEF.md",
        "architecture/root-layout.v1.json#zones.authority", 0, "high",
        dependencies=["00_MASTER.md"],
    ),
    "04_CORPUS_RETROSPECTIVE_BRIEF.md": reviewed(
        "retain", "canonical-brief", "04_CORPUS_RETROSPECTIVE_BRIEF.md",
        "architecture/root-layout.v1.json#zones.authority", 0, "high",
        dependencies=["00_MASTER.md", "corpus", "retrospectives"],
    ),
    "05_CALIBRATION_PROMPTBANK_BRIEF.md": reviewed(
        "retain", "canonical-brief", "05_CALIBRATION_PROMPTBANK_BRIEF.md",
        "architecture/root-layout.v1.json#zones.authority", 0, "high",
        dependencies=["00_MASTER.md", "PREDICTION_AUTOMATION.md"],
    ),
    "06_SECOND_MEMORY_BRIEF.md": reviewed(
        "retain", "canonical-brief", "06_SECOND_MEMORY_BRIEF.md",
        "architecture/root-layout.v1.json#zones.authority", 0, "critical",
        dependencies=["00_MASTER.md", "memory"],
    ),
    "07_VIRTUAL_TWIN_BRIEF.md": reviewed(
        "retain", "canonical-brief", "07_VIRTUAL_TWIN_BRIEF.md",
        "architecture/root-layout.v1.json#zones.authority", 0, "critical",
        dependencies=["00_MASTER.md", "twin_core", "memory", "corpus"],
    ),
    "1916b63abd801fbb5abf9b44f98d87a68ccd5db992b2a4d30567dd8a4ed29a85-2026-07-19-08-37-41-df72519dd898472489071b0441745ac3.zip": reviewed(
        "protected/no-touch", "immutable-source-export",
        "corpus/raw/provider-archives/chatgpt-2026.zip",
        "architecture/EXPORT_IMMUTABILITY_BASELINE.sha256", 60, "critical",
        dependencies=["corpus", "FINE_TUNING_READINESS.md", "migration"],
        notes="Target path is descriptive only; relocation is blocked until every hash and absolute reference is migrated.",
    ),
    "AGENTS.md": reviewed(
        "retain", "canonical-agent-instruction", "AGENTS.md",
        "repository instruction hierarchy", 0, "critical",
        dependencies=["00_MASTER.md", "01_CHARTER_BRIEF.md", "modules/skills"],
    ),
    "CHARTER.md": reviewed(
        "retain", "canonical-active", "CHARTER.md",
        "CHARTER.md#how-assistants-serve", 0, "critical",
        dependencies=["CONTEXT.md", "deploy"],
    ),
    "CONTEXT.md": reviewed(
        "retain", "canonical-active", "CONTEXT.md",
        "CONTEXT.md#standing-decisions", 0, "critical",
        dependencies=["CONTEXT_PROTOCOL.md", "memory", "deploy"],
    ),
    "CONTEXT_PROTOCOL.md": reviewed(
        "retain", "canonical-protocol", "CONTEXT_PROTOCOL.md",
        "CONTEXT_PROTOCOL.md", 0, "critical",
        dependencies=["CONTEXT.md", "deploy"],
    ),
    "FABLE_V3_DESIGN_REVIEW.md": reviewed(
        "archive", "historical-review",
        "archive/orchestrator/reviews/2026-07-18/FABLE_V3_DESIGN_REVIEW.md",
        "architecture/root-layout.v1.json#legacy_root_exceptions", 20, "high",
        dependencies=["TRAVEL_DESIGNER_GOAL.md", "V3_CONTRACT_DECISIONS.md"],
    ),
    "FINE_TUNING_READINESS.md": reviewed(
        "move", "active-specification",
        "modules/digital-twin/training/FINE_TUNING_READINESS.md",
        "00_MASTER.md#session-04", 40, "critical",
        dependencies=["corpus", "scripts", "tests", "outputs"],
    ),
    "MODEL_AGNOSTIC_SPEC.md": reviewed(
        "move", "active-policy-specification",
        "modules/platform/policies/MODEL_AGNOSTIC_SPEC.md",
        "CONTEXT.md#standing-decisions", 40, "high",
        dependencies=["ORCHESTRATOR_AND_GIGA_USER_ARCHITECTURE.md", "deploy"],
    ),
    "ORCHESTRATOR_AND_GIGA_USER_ARCHITECTURE.md": reviewed(
        "archive", "historical-subordinate-synthesis",
        "archive/architecture/snapshots/2026-07/ORCHESTRATOR_AND_GIGA_USER_ARCHITECTURE.md",
        "file self-declaration: synthesis subordinate to code/certificates/doctrine", 20, "high",
        dependencies=["architecture", "reports", "00_MASTER.md"],
        notes="The file identifies itself as an architectural synthesis and states that code, certificates and standing decisions outrank its prose; archive it as a dated snapshot and point the architecture index at current machine-readable authority.",
    ),
    "PREDICTION_AUTOMATION.md": reviewed(
        "move", "active-module-specification",
        "modules/calibration/PREDICTION_AUTOMATION.md",
        "05_CALIBRATION_PROMPTBANK_BRIEF.md", 40, "critical",
        dependencies=["scripts/prediction_automation.py", "tests/test_prediction_automation.py"],
    ),
    "SESSION_LOGS": reviewed(
        "retain", "canonical-historical-programme-ledger",
        "SESSION_LOGS",
        "00_MASTER.md#session-log-links", 45, "critical",
        dependencies=["00_MASTER.md", "01_CHARTER_BRIEF.md", "02_MEMORY_CONTEXT_BRIEF.md"],
        notes="The master and briefs link these logs directly. Header drift is a content-reconciliation issue, not evidence that the live ledger should be relocated.",
    ),
    "SKILLTREE_GIGA_USER_INTEGRATION.md": reviewed(
        "move", "active-module-specification",
        "modules/skills/docs/SKILLTREE_GIGA_USER_INTEGRATION.md",
        "skilltree/implementation-registry.json", 40, "high",
        dependencies=["skilltree", "deploy/skills/skilltree-operator", "outputs/skill-filesystem-inventory-2026-07-30"],
    ),
    "SOVEREIGNTY_INDEX.md": reviewed(
        "move", "active-provisional-module-specification",
        "modules/sovereignty/README.md",
        "SOVEREIGNTY_INDEX.md#promotion-test", 40, "high",
        dependencies=["scripts/sovereignty_index.py", "contracts/sovereignty-observation.v1.schema.json", "examples/sovereignty-assessment.synthetic.json"],
    ),
    "TRAVEL_DESIGNER_GOAL.md": reviewed(
        "move", "historical-project-goal",
        "projects/travel-designer/GOAL.md",
        "TRAVEL_DESIGNER_GOAL.md", 30, "medium",
        dependencies=["FABLE_V3_DESIGN_REVIEW.md"],
    ),
    "The Offer Accelerator Toolkit (4) (1).pdf": reviewed(
        "protected/no-touch", "licensed-source-document",
        "The Offer Accelerator Toolkit (4) (1).pdf",
        "job-application-automation/OFFER_ACCELERATOR_INTEGRATION_ASSESSMENT.md", 0, "critical",
        dependencies=["job-application-automation"],
        notes="Do not relocate until licence/retention policy and source citation paths are explicitly approved.",
    ),
    "V3_CONTRACT_DECISIONS.md": reviewed(
        "archive", "ratified-historical-external-decision",
        "archive/orchestrator/decisions/V3_CONTRACT_DECISIONS.md",
        "V3_CONTRACT_DECISIONS.md#ratification-condition", 99, "critical",
        dependencies=["FABLE_V3_DESIGN_REVIEW.md", "upstreams"],
        notes="The file's explicit ratification condition is satisfied by landing the file in this repository. It records external Orchestrator decisions and is preserved as historical decision evidence, not current GIGA implementation authority.",
    ),
    "adapters": reviewed(
        "move", "active-platform-source", "modules/integrations/adapters",
        "architecture/root-layout.v1.json#zones.platform", 40, "critical",
        dependencies=["contracts", "twin_core", "outputs/adapter-evidence"],
    ),
    "architecture": reviewed(
        "retain", "canonical-architecture-and-lineage", "architecture",
        "architecture/GIGA_USER_DIRECTORY_ARCHITECTURE.md", 0, "critical",
        dependencies=["00_MASTER.md", "contracts", "migration"],
        subpath_exceptions=[{
            "path": "architecture/modularization/preflight/authority",
            "handling": "Wave 0A owned preflight artefacts; not a migration target.",
        }],
    ),
    "audit-work": reviewed(
        "protected/no-touch", "mixed-external-audit-workspace", "audit-work",
        "architecture/root-layout.v1.json#zones.external_workspaces", 0, "critical",
        dependencies=["upstreams", "architecture"],
        notes="Authored probes, a virtual environment and generated Graphify material remain physically mixed. Treat the whole path as an external no-touch workspace until a separately authorised content cleanup.",
    ),
    "company-admin": reviewed(
        "move", "active-personal-company-project", "projects/company-admin",
        "company-admin/excellence-exalted/2026-dormant-company-closure.md", 30, "high",
        dependencies=["projects/registry.v1.json"],
        notes="The dormant-company closure file is an active project ledger with evidence and a statutory deadline. Register the project and root-layout path in the same migration batch.",
    ),
    "contracts": reviewed(
        "move", "active-platform-source", "modules/platform/contracts",
        "architecture/root-layout.v1.json#zones.platform", 40, "critical",
        dependencies=["twin_core", "scripts", "tests", "adapters"],
    ),
    "corpus": reviewed(
        "protected/no-touch", "canonical-evidence-store", "corpus",
        "corpus/MANIFEST.md", 0, "critical",
        dependencies=["memory", "retrospectives", "FINE_TUNING_READINESS.md"],
    ),
    "deploy": reviewed(
        "move", "active-mixed-deployment-surface", "modules/deployment",
        "architecture/root-layout.v1.json#zones.platform", 40, "critical",
        dependencies=["AGENTS.md", "CHARTER.md", "CONTEXT.md", "modules/skills"],
        subpath_exceptions=[
            {"path": "deploy/skills/librarian", "handling": "Owned exclusively by the modules/skills batch; target modules/skills/owned/librarian."},
            {"path": "deploy/skills/skilltree-operator", "handling": "Owned exclusively by the modules/skills batch; target modules/skills/owned/skilltree-operator."},
            {"path": "deploy/skills/librarian-workspace", "handling": "Owned exclusively by the modules/skills batch as evaluation/workspace evidence."},
            {"path": "deploy/gutua", "handling": "Owned by the deployment batch; preserve machine authority policy and candidate history."},
        ],
        notes="This is a split migration. MIGRATION_BATCHES.v1.json assigns deploy/skills/** to the first-class skills batch and every other child to deployment, with non-overlapping source sets.",
    ),
    "ecc-integration": reviewed(
        "move", "active-integration-candidate", "modules/integrations/ecc",
        "SKILLTREE_GIGA_USER_INTEGRATION.md", 40, "high",
        dependencies=["upstreams/ECC", "skilltree", "outputs"],
        notes="MIGRATION_BATCHES.v1.json assigns authored evidence, candidate imports, scripts and tests to modules/integrations/ecc; generated graphify-out is assigned exclusively to runtime/generated/ecc-graphify.",
    ),
    "examples": reviewed(
        "move", "active-test-fixtures", "modules/platform/examples",
        "architecture/root-layout.v1.json#zones.platform", 40, "medium",
        dependencies=["SOVEREIGNTY_INDEX.md", "tests"],
    ),
    "external_proof": reviewed(
        "move", "active-proof-compiler-input", "modules/proof/external",
        "07_VIRTUAL_TWIN_BRIEF.md", 40, "high",
        dependencies=["twin_core", "tests", "outputs/external-proof"],
    ),
    "graphify-out": reviewed(
        "generated", "derived-graph-cache", "runtime/generated/graphify",
        "graphify skill output contract", 10, "low",
        dependencies=["retrospectives/2026-07-deep-characterisation.md"],
        notes="Existing graph covers a retrospective, not the workspace topology; it grants no architecture authority.",
    ),
    "instagram-artiom.png-2026-07-16-58GCGdnZ.zip": reviewed(
        "protected/no-touch", "immutable-source-export",
        "corpus/raw/provider-archives/instagram.zip",
        "architecture/EXPORT_IMMUTABILITY_BASELINE.sha256", 60, "critical",
        dependencies=["corpus", "migration"],
        notes="Target path is descriptive only; relocation is blocked by immutable hash and reference migration requirements.",
    ),
    "instagram_not_following_back.csv": reviewed(
        "generated", "derived-personal-data", "runtime/generated/instagram/not-following-back.csv",
        "Instagram extraction workflow", 10, "medium",
        dependencies=["instagram_unfollow_plan.json", "instagram_unfollow_progress.json"],
    ),
    "instagram_unfollow_plan.json": reviewed(
        "generated", "derived-operational-plan", "runtime/generated/instagram/unfollow-plan.json",
        "Instagram unfollow workflow", 10, "medium",
        dependencies=["instagram_not_following_back.csv", "instagram_unfollow_progress.json"],
    ),
    "instagram_unfollow_progress.json": reviewed(
        "generated", "runtime-progress-state", "runtime/state/instagram/unfollow-progress.json",
        "Instagram unfollow workflow", 10, "high",
        dependencies=["instagram_unfollow_plan.json"],
    ),
    "intake": reviewed(
        "retain", "canonical-intake", "intake",
        "architecture/GIGA_USER_DIRECTORY_ARCHITECTURE.md#migration-rules", 0, "high",
    ),
    "job-application-automation": reviewed(
        "retain", "active-owned-project", "job-application-automation",
        "projects/registry.v1.json#job-application-automation", 0, "critical",
        dependencies=["market-aligner", "The Offer Accelerator Toolkit (4) (1).pdf"],
    ),
    "korean": reviewed(
        "retain", "active-owned-project", "korean",
        "projects/registry.v1.json#korean", 0, "high",
        dependencies=["CONTEXT.md"],
    ),
    "life-admin": reviewed(
        "protected/no-touch", "active-concurrent-workspace", "projects/life-admin",
        "concurrent-task handoff: top-level life-admin workspace created after the authority checkpoint",
        0,
        "critical",
        dependencies=["projects/registry.v1.json", "architecture/root-layout.v1.json"],
        ambiguity=(
            "The workspace was created by a concurrent task after the authority "
            "checkpoint; originating writer, ownership and reference closure are "
            "not yet reconciled."
        ),
        notes=(
            "The destination is descriptive only. Do not inspect, edit or move the "
            "workspace until the originating task is identified, the tree is sealed, "
            "the project is registered and a later isolated migration batch is approved."
        ),
    ),
    "life-logging": reviewed(
        "retain", "active-owned-project", "life-logging",
        "projects/registry.v1.json#life-logging", 0, "high",
    ),
    "market-aligner": reviewed(
        "protected/no-touch", "active-independent-canonical-workspace", "market-aligner",
        "architecture/machine-authority.v1.json#hosts.mac.roots.market-aligner", 0, "critical",
        dependencies=["projects/registry.v1.json", "job-application-automation"],
        notes="Logically external to GIGA platform ownership while physically retained at its stable path.",
    ),
    "market-aligner-artiom": reviewed(
        "quarantine", "candidate-duplicate-workspace", "quarantine/workspaces/market-aligner-artiom",
        "architecture/machine-authority.v1.json#hosts.mac.roots.market-aligner-artiom", 99, "critical",
        dependencies=["market-aligner", "projects/registry.v1.json"],
        ambiguity="Machine authority labels this a candidate duplicate; reconciliation outcome is not yet ratified.",
    ),
    "memory": reviewed(
        "protected/no-touch", "canonical-personal-memory", "memory",
        "memory/MEMORY_PROTOCOL.md", 0, "critical",
        dependencies=["CONTEXT.md", "corpus", "deploy/skills/librarian"],
    ),
    "migration": reviewed(
        "move", "active-migration-evidence-and-tools", "modules/operations/migration",
        "architecture/MAC_GUTUA_AUTHORITY_AND_SNAPSHOT_POLICY.md", 40, "critical",
        dependencies=["architecture/machine-authority.v1.json", "staging", "deploy/gutua"],
    ),
    "monitoring": reviewed(
        "move", "active-operations-config", "modules/operations/monitoring",
        "skilltree/implementation-registry.json#monitoring-and-alerting", 40, "critical",
        dependencies=["twin_core", "scripts", "outputs/runtime"],
    ),
    "output": reviewed(
        "generated", "generated-media-output", "runtime/generated/media",
        "tool output convention", 10, "low",
    ),
    "outputs": reviewed(
        "generated", "mixed-derived-output-and-receipts", "runtime/outputs",
        "architecture/root-layout.v1.json#zones.runtime_and_delivery", 10, "high",
        dependencies=["adapters", "external_proof", "skilltree"],
        notes="Generated does not mean disposable: receipts, registries and the skill inventory require retention policies.",
    ),
    "overseer_fable_exec.patch": reviewed(
        "archive", "historical-patch", "archive/orchestrator/patches/overseer_fable_exec.patch",
        "architecture/root-layout.v1.json#legacy_root_exceptions", 20, "medium",
        dependencies=["upstreams"],
    ),
    "package(1).zip": reviewed(
        "protected/no-touch", "immutable-source-export",
        "corpus/raw/provider-archives/discord-teen.zip",
        "reports/UNIFIED_MEMORY_SYSTEM_2026-07-26.md#source-hashes", 60, "critical",
        dependencies=["corpus", "FINE_TUNING_READINESS.md", "retrospectives"],
        notes="Not present in the five-file baseline but independently hash-recorded as old/teen Discord provenance.",
    ),
    "package.zip": reviewed(
        "protected/no-touch", "immutable-source-export",
        "corpus/raw/provider-archives/discord-primary.zip",
        "architecture/EXPORT_IMMUTABILITY_BASELINE.sha256", 60, "critical",
        dependencies=["corpus", "FINE_TUNING_READINESS.md", "tests/test_extract_discord.py"],
    ),
    "phase2_sol_exec.patch": reviewed(
        "archive", "historical-patch", "archive/orchestrator/patches/phase2_sol_exec.patch",
        "architecture/root-layout.v1.json#legacy_root_exceptions", 20, "medium",
        dependencies=["upstreams"],
    ),
    "projects": reviewed(
        "retain", "canonical-project-container-and-registry", "projects",
        "projects/registry.v1.json", 0, "critical",
        dependencies=["job-application-automation", "korean", "life-logging", "market-aligner"],
    ),
    "reports": reviewed(
        "retain", "active-mixed-knowledge-and-receipts", "reports",
        "architecture/root-layout.v1.json#zones.knowledge", 45, "critical",
        dependencies=["00_MASTER.md", "architecture", "deploy/gutua"],
        notes="The root-layout contract assigns reports to the knowledge zone and live authority documents cite report receipts. Retain the path; supersession indexing remains a content-governance task.",
    ),
    "research": reviewed(
        "protected/no-touch", "active-research-evidence", "research",
        "07_VIRTUAL_TWIN_BRIEF.md#raw-evidence-boundary", 0, "critical",
        dependencies=["twin_core", "scripts", "contracts", "reports"],
        notes="Contains source evidence and derived research state; no whole-tree move before per-subpath provenance classification.",
    ),
    "result.json": reviewed(
        "protected/no-touch", "raw-sensitive-telegram-export",
        "corpus/raw/provider-archives/telegram/result.json",
        "reports/UNIFIED_MEMORY_SYSTEM_2026-07-26.md#source-coverage", 60, "critical",
        dependencies=["corpus", "scripts/extract_telegram.py"],
        notes="Contains personal data. Target path is descriptive only until hashes, permissions and references are migrated.",
    ),
    "retrospectives": reviewed(
        "retain", "derived-interpretive-knowledge", "retrospectives",
        "04_CORPUS_RETROSPECTIVE_BRIEF.md", 0, "high",
        dependencies=["corpus", "memory", "graphify-out"],
    ),
    "scripts": reviewed(
        "move", "active-cross-module-source", "modules/*/scripts",
        "MIGRATION_BATCHES.v1.json#script_routes", 40, "critical",
        dependencies=["twin_core", "contracts", "tests", "deploy"],
        notes="Every current source file has an explicit owning-module route in MIGRATION_BATCHES.v1.json. Generated __pycache__ content is assigned to the runtime batch.",
    ),
    "skilltree": reviewed(
        "move", "active-capability-registry", "modules/skills/capability-registry",
        "skilltree/implementation-registry.json", 40, "critical",
        dependencies=["deploy/skills/skilltree-operator", "outputs/skill-filesystem-inventory-2026-07-30"],
    ),
    "staging": reviewed(
        "quarantine", "candidate-and-transfer-staging", "quarantine/staging",
        "architecture/root-layout.v1.json#zones.runtime_and_delivery", 99, "critical",
        dependencies=["migration", "deploy", "twin_core"],
        notes="Candidate presence grants no authority; preserve bundles, receipts and schema-v3 candidate until explicit disposition.",
    ),
    "tests": reviewed(
        "move", "active-cross-module-tests", "modules/*/tests",
        "MIGRATION_BATCHES.v1.json#test_routes", 40, "critical",
        dependencies=["twin_core", "scripts", "contracts"],
        notes="Every current test source has an explicit owning-module route in MIGRATION_BATCHES.v1.json. Generated __pycache__ content is assigned to the runtime batch.",
    ),
    "tier1-findings.md": reviewed(
        "archive", "historical-external-finding-ledger",
        "archive/orchestrator/findings/tier1-findings.md",
        "tier1-findings.md#evidence-scope", 20, "critical",
        dependencies=["memory", "upstreams", "migration"],
        notes="Although the file declares memory/tier1-findings.md as an intended landing path, its claims concern the external Orchestrator journal and belief pipeline. Preserve it as external-system evidence, not personal-memory authority.",
    ),
    "tmp": reviewed(
        "generated", "temporary-render-output", "runtime/tmp",
        "temporary-work convention", 10, "none",
        dependencies=["company-admin"],
    ),
    "twin_core": reviewed(
        "move", "active-shared-platform-source", "modules/digital-twin/core",
        "07_VIRTUAL_TWIN_BRIEF.md", 40, "critical",
        dependencies=["contracts", "scripts", "tests", "memory", "corpus"],
    ),
    "upstreams": reviewed(
        "externalize", "protected-upstream-checkout", "external/upstreams",
        "architecture/root-layout.v1.json#zones.external_workspaces", 50, "critical",
        dependencies=["ecc-integration", "audit-work"],
        notes="Remain read-only upstream evidence; do not absorb upstream skills into modules/skills/owned.",
    ),
}


SKILL_CLASSIFICATION = {
    "active-codex-personal-or-system": {
        "target_class": "active-personal-system",
        "ownership": "user-or-codex-runtime",
        "target": "modules/skills/catalogs/active-host-index",
        "handling": "reference-only; never copy into GIGA-owned skill source",
    },
    "active-shared-agent": {
        "target_class": "active-personal-system",
        "ownership": "shared-agent-runtime",
        "target": "modules/skills/catalogs/active-host-index",
        "handling": "reference-only",
    },
    "active-claude-personal": {
        "target_class": "active-personal-system",
        "ownership": "user-claude-configuration",
        "target": "modules/skills/catalogs/active-host-index",
        "handling": "reference-only",
    },
    "installed-codex-plugin-cache": {
        "target_class": "external-plugin",
        "ownership": "plugin-publisher-and-codex-cache",
        "target": "modules/skills/catalogs/external-plugins-index",
        "handling": "index exact version/path; do not vendor cache",
    },
    "giga-owned-deploy": {
        "target_class": "giga-owned",
        "ownership": "giga-user/modules/skills",
        "target": "modules/skills/owned",
        "handling": "future canonical source after lifecycle review and migration receipt",
    },
    "giga-staging": {
        "target_class": "candidate-copy",
        "ownership": "giga-user/staging",
        "target": "quarantine/staging/skills",
        "handling": "non-authoritative candidate; preserve exact bytes",
    },
    "claude-marketplace-checkout": {
        "target_class": "marketplace-catalog-cache",
        "ownership": "external-marketplace",
        "target": "modules/skills/catalogs/marketplaces-index",
        "handling": "reference-only; presence is not installation",
    },
    "codex-marketplace-temporary-mirror": {
        "target_class": "marketplace-catalog-cache",
        "ownership": "codex-temporary-cache",
        "target": "modules/skills/catalogs/marketplaces-index",
        "handling": "reference-only; disposable cache, not authority",
    },
    "codex-runtime-cache": {
        "target_class": "runtime-cache",
        "ownership": "codex-runtime",
        "target": "modules/skills/catalogs/runtime-index",
        "handling": "reference-only",
    },
    "claude-app-session-or-runtime": {
        "target_class": "runtime-cache",
        "ownership": "claude-runtime",
        "target": "modules/skills/catalogs/runtime-index",
        "handling": "reference-only; session copies are not source",
    },
    "claude-scheduled-automation": {
        "target_class": "active-personal-system",
        "ownership": "user-claude-automation",
        "target": "modules/skills/catalogs/active-host-index",
        "handling": "reference-only; automation status must be verified separately",
    },
    "claude-user-project-runtime": {
        "target_class": "runtime-cache",
        "ownership": "project-runtime",
        "target": "modules/skills/catalogs/runtime-index",
        "handling": "reference-only",
    },
    "orchestrator-v3-skill-corpus": {
        "target_class": "historical-upstream-copy",
        "ownership": "external-orchestrator-corpus",
        "target": "modules/skills/catalogs/upstream-history-index",
        "handling": "evidence/index only; never bulk promote",
    },
    "giga-ecc-upstream": {
        "target_class": "historical-upstream-copy",
        "ownership": "ECC-upstream",
        "target": "modules/skills/catalogs/upstream-history-index",
        "handling": "upstream evidence; import only through ECC integration receipts",
    },
    "giga-corpus-snapshot": {
        "target_class": "historical-upstream-copy",
        "ownership": "giga-evidence-corpus",
        "target": "modules/skills/catalogs/historical-snapshots-index",
        "handling": "immutable evidence snapshot; not executable authority",
    },
    "giga-vendored-runtime": {
        "target_class": "runtime-cache",
        "ownership": "vendored-dependency",
        "target": "modules/skills/catalogs/runtime-index",
        "handling": "dependency copy; not GIGA-owned skill",
    },
    "other-project-local": {
        "target_class": "external-project-skill",
        "ownership": "owning-project",
        "target": "modules/skills/catalogs/external-projects-index",
        "handling": "reference-only; project remains authority",
    },
    "kimi-runtime": {
        "target_class": "runtime-cache",
        "ownership": "kimi-runtime",
        "target": "modules/skills/catalogs/runtime-index",
        "handling": "reference-only",
    },
    "graphify-repository-cache": {
        "target_class": "marketplace-catalog-cache",
        "ownership": "graphify-repository-cache",
        "target": "modules/skills/catalogs/marketplaces-index",
        "handling": "reference-only; cache is not installation",
    },
    "package-manager-or-model-runtime": {
        "target_class": "runtime-cache",
        "ownership": "package-or-model-runtime",
        "target": "modules/skills/catalogs/runtime-index",
        "handling": "reference-only",
    },
    "other-accessible-home-path": {
        "target_class": "unclassified-external",
        "ownership": "unknown-external",
        "target": "modules/skills/catalogs/quarantine-index",
        "handling": "index only; fail closed pending ownership",
    },
}


def git_lines(*args: str) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return proc.stdout.splitlines()


def measure(path: Path, tracked: set[str], porcelain: list[str]) -> dict[str, Any]:
    rel = path.name
    if path.is_symlink():
        kind = "symlink"
        file_count = 1
        byte_count = path.lstat().st_size
    elif path.is_file():
        kind = "file"
        file_count = 1
        byte_count = path.stat().st_size
    else:
        kind = "directory"
        file_count = 0
        byte_count = 0
        for child in path.rglob("*"):
            # Avoid making the architecture measurement self-referential: the
            # generated manifest lives inside this owned preflight directory.
            if path.name == "architecture" and HERE in child.parents:
                continue
            if child.is_file() or child.is_symlink():
                file_count += 1
                try:
                    byte_count += child.lstat().st_size
                except OSError:
                    pass
    tracked_count = sum(1 for item in tracked if item == rel or item.startswith(f"{rel}/"))
    status_lines = []
    for line in porcelain:
        candidate = line[3:] if len(line) >= 4 else ""
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        if candidate == rel or candidate.startswith(f"{rel}/"):
            status_lines.append(line)
    return {
        "kind": kind,
        "file_count": file_count,
        "byte_count": byte_count,
        "tracked_file_count": tracked_count,
        "git_status_summary": {
            "dirty_path_count": len(status_lines),
            "sample": status_lines[:10],
            "sample_truncated": len(status_lines) > 10,
        },
    }


def load_skill_topology() -> dict[str, Any]:
    data = json.loads(SKILL_INVENTORY.read_text(encoding="utf-8"))
    counts = data["summary"]["physical_manifests_by_category"]
    missing = sorted(set(counts) - set(SKILL_CLASSIFICATION))
    extra = sorted(set(SKILL_CLASSIFICATION) - set(counts))
    if missing or extra:
        raise RuntimeError(
            f"Skill classification drift: missing={missing!r}, extra={extra!r}"
        )
    categories = []
    for name in sorted(counts):
        categories.append(
            {
                "source_class": name,
                "manifest_count": counts[name],
                **SKILL_CLASSIFICATION[name],
                "wave0_action": "no-touch",
            }
        )
    owned = [
        item
        for item in data["deduplicated_capabilities"]
        if "giga-owned-deploy" in item.get("categories", [])
    ]
    return {
        "evidence": str(SKILL_INVENTORY.relative_to(ROOT)),
        "evidence_generated_on": data["summary"]["generated_on"],
        "physical_manifest_count": data["summary"]["counts"]["physical_manifests"],
        "router_catalog_count": data["summary"]["counts"]["skill_router_catalog_entries"],
        "module": {
            "target": "modules/skills",
            "owner": "giga-user platform",
            "canonical_owned_source": "modules/skills/owned",
            "capability_registry": "modules/skills/capability-registry",
            "catalogues_are_reference_only": True,
            "presence_does_not_grant_authority": True,
        },
        "giga_owned_skills": [
            {
                "name": item["name"],
                "current_canonical_path": str(
                    Path(item["canonical_path"]).relative_to(ROOT)
                ),
                "copy_count": item["copy_count"],
                "content_variant_count": item["content_variant_count"],
                "catalogued_by_skill_router": item["catalogued_by_skill_router"],
                "target": f"modules/skills/owned/{item['name']}",
                "wave0_action": "no-touch",
            }
            for item in sorted(owned, key=lambda value: value["name"])
        ],
        "source_classes": categories,
    }


def build() -> dict[str, Any]:
    top_paths = sorted(
        (path for path in ROOT.iterdir() if path.name != ".git"),
        key=lambda path: path.name,
    )
    actual = {path.name for path in top_paths}
    declared = set(MAPPING)
    if actual != declared:
        raise RuntimeError(
            "Root topology changed; fail closed. "
            f"unmapped={sorted(actual - declared)!r}, absent={sorted(declared - actual)!r}"
        )

    tracked = set(git_lines("ls-files"))
    porcelain = git_lines("status", "--porcelain=v1", "--untracked-files=all")
    entries = []
    for path in top_paths:
        declaration = MAPPING[path.name]
        entries.append(
            {
                "source": path.name,
                **measure(path, tracked, porcelain),
                **declaration,
            }
        )

    root_names = "\n".join(path.name for path in top_paths).encode("utf-8")
    head = git_lines("rev-parse", "HEAD")[0]
    branch = git_lines("rev-parse", "--abbrev-ref", "HEAD")[0]
    return {
        "schema": "giga.modularization.authority-map.v1",
        "preflight_id": "wave-0a-authority-topology-2026-07-30",
        "approval_state": "authorized-target-preflight-blocked",
        "operator_authority": {
            "source": "explicit acceptance of the modularization plan followed by instruction to begin autonomously",
            "scope": "target modular architecture and specialised skills module",
            "qualification": "implementation remains subject to deterministic preflight gates and evidence-backed ambiguity resolution",
        },
        "scope": {
            "root": str(ROOT),
            "excluded": ["dubbing-studio"],
            "top_level_path_count": len(entries),
            "top_level_name_set_sha256": hashlib.sha256(root_names).hexdigest(),
            "git_head": head,
            "git_branch": branch,
            "read_only_source_analysis": True,
            "wave0_moves_authorized": False,
        },
        "authority_precedence": [
            "explicit operator decision",
            "CONTEXT.md standing-decision registry",
            "00_MASTER.md programme status",
            "CHARTER.md assistant behaviour",
            "memory/MEMORY_PROTOCOL.md personal-memory mutation",
            "projects/registry.v1.json project ownership",
            "architecture/machine-authority.v1.json host authority",
            "architecture/root-layout.v1.json directory zones",
            "candidate-bound certificates and tests",
            "reports, plans, generated output and caches",
        ],
        "target_architecture": {
            "status": "authorized-for-implementation-subject-to-preflight-gates",
            "root_entrypoints": [
                ".gitignore",
                "AGENTS.md",
                "00_MASTER.md",
                "01_CHARTER_BRIEF.md",
                "02_MEMORY_CONTEXT_BRIEF.md",
                "03_LIFE_INFRA_BRIEF.md",
                "04_CORPUS_RETROSPECTIVE_BRIEF.md",
                "05_CALIBRATION_PROMPTBANK_BRIEF.md",
                "06_SECOND_MEMORY_BRIEF.md",
                "07_VIRTUAL_TWIN_BRIEF.md",
                "CHARTER.md",
                "CONTEXT.md",
                "CONTEXT_PROTOCOL.md",
            ],
            "first_class_zones": {
                "modules": "GIGA-owned reusable implementation, contracts, deployment and specialised skills",
                "projects": "Outcome-oriented owned projects with independent lifecycle",
                "corpus-memory-research": "Protected evidence, human-auditable memory and research",
                "external": "Upstream or independently owned workspaces; reference/promotion boundary",
                "runtime": "Generated output, cache, state and temporary files",
                "archive": "Immutable historical work orders, reports, reviews, patches and receipts",
                "quarantine": "Unresolved ownership, duplicate candidates and mixed paths; no authority",
                "intake": "New material awaiting explicit ownership",
            },
            "modules": {
                "digital-twin": {"owner": "GIGA virtual-twin workstream"},
                "platform": {"owner": "GIGA platform"},
                "calibration": {"owner": "GIGA calibration workstream"},
                "sovereignty": {"owner": "GIGA sovereignty module"},
                "integrations": {"owner": "GIGA integration boundary"},
                "operations": {"owner": "GIGA operations"},
                "deployment": {"owner": "GIGA release/deployment"},
                "proof": {"owner": "GIGA evidence/proof compiler"},
                "research": {"owner": "GIGA research tooling"},
                "skills": {
                    "owner": "giga-user platform",
                    "canonical_owned_source": "modules/skills/owned",
                    "capability_registry": "modules/skills/capability-registry",
                    "external_catalogues": "modules/skills/catalogs",
                },
            },
        },
        "root_move_lock": {
            "contract": "ROOT_MOVE_LOCK.md",
            "runtime_path": "~/.giga/locks/giga-user-root-move.v1.lock",
            "primitive": "atomic mkdir",
            "single_writer": True,
            "stale_lock_deletion_is_forbidden_without_recovery_receipt": True,
        },
        "acceptance_gate": {
            "contract": "ROOT_MOVE_LOCK.md#acceptance-gate",
            "all_ambiguities_must_be_resolved": True,
            "manifest_hash_must_be_bound_to_preflight_receipt": True,
            "protected_sources_require_pre_and_post_hash_match": True,
            "moves_execute_in_declared_order": True,
            "compatibility_and_tests_must_pass_before_source_retirement": True,
            "migration_receipt_required": True,
            "migration_batches_must_validate": True,
        },
        "skills": load_skill_topology(),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write authority-map.v1.json inside this preflight directory.",
    )
    args = parser.parse_args()
    payload = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.write:
        temporary = OUTPUT.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, OUTPUT)
        print(OUTPUT)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
