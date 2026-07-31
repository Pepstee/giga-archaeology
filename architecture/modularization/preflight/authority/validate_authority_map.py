#!/usr/bin/env python3
"""Validate the Wave 0A authority/topology manifest.

Structural validity and migration readiness are intentionally different:
blocked ambiguities are valid preflight findings, but they make the acceptance
gate not ready.  ``--require-ready`` turns those blockers into a non-zero exit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANIFEST = HERE / "authority-map.v1.json"
BATCH_MANIFEST = HERE / "MIGRATION_BATCHES.v1.json"
SKILL_INVENTORY = ROOT / "outputs/skill-filesystem-inventory-2026-07-30/inventory.json"

ALLOWED_DISPOSITIONS = {
    "retain",
    "move",
    "externalize",
    "archive",
    "generated",
    "quarantine",
    "protected/no-touch",
}
ALLOWED_COMPATIBILITY = {"none", "low", "medium", "high", "critical"}
REQUIRED_ENTRY_FIELDS = {
    "source",
    "kind",
    "file_count",
    "byte_count",
    "tracked_file_count",
    "git_status_summary",
    "disposition",
    "lifecycle_status",
    "destination",
    "canonical_authority",
    "dependencies",
    "provenance_requirements",
    "compatibility",
    "migration_order",
    "wave0_move_authorized",
    "ambiguity",
}
REQUIRED_SKILL_TARGET_CLASSES = {
    "giga-owned",
    "active-personal-system",
    "external-plugin",
    "marketplace-catalog-cache",
    "historical-upstream-copy",
}


def current_top_level() -> list[str]:
    return sorted(path.name for path in ROOT.iterdir() if path.name != ".git")


def validate_payload(
    payload: dict[str, Any], *, check_live_root: bool = True
) -> tuple[list[str], list[str]]:
    """Return (errors, blockers)."""

    errors: list[str] = []
    blockers: list[str] = []

    if payload.get("schema") != "giga.modularization.authority-map.v1":
        errors.append("unexpected or missing schema")
    if payload.get("approval_state") != "authorized-target-preflight-blocked":
        errors.append("target architecture authority state is not explicit")

    scope = payload.get("scope", {})
    if scope.get("wave0_moves_authorized") is not False:
        errors.append("Wave 0 must not authorize moves")
    if scope.get("read_only_source_analysis") is not True:
        errors.append("source analysis must be declared read-only")
    if "dubbing-studio" not in scope.get("excluded", []):
        errors.append("dubbing-studio exclusion is missing")

    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return errors + ["entries must be a non-empty list"], blockers

    sources = [entry.get("source") for entry in entries]
    duplicates = sorted({source for source in sources if sources.count(source) > 1})
    if duplicates:
        errors.append(f"duplicate source entries: {duplicates}")
    if any(not isinstance(source, str) or not source for source in sources):
        errors.append("all source paths must be non-empty strings")

    if scope.get("top_level_path_count") != len(entries):
        errors.append("scope top_level_path_count does not match entries")

    name_bytes = "\n".join(sorted(sources)).encode("utf-8")
    expected_name_digest = hashlib.sha256(name_bytes).hexdigest()
    if scope.get("top_level_name_set_sha256") != expected_name_digest:
        errors.append("top-level name-set digest mismatch")

    if check_live_root:
        live = current_top_level()
        declared = sorted(sources)
        if live != declared:
            errors.append(
                "live root topology drift: "
                f"unmapped={sorted(set(live) - set(declared))}, "
                f"absent={sorted(set(declared) - set(live))}"
            )

    destinations: dict[str, str] = {}
    for entry in entries:
        source = entry.get("source", "<missing>")
        missing = sorted(REQUIRED_ENTRY_FIELDS - set(entry))
        if missing:
            errors.append(f"{source}: missing fields {missing}")
            continue
        disposition = entry["disposition"]
        if disposition not in ALLOWED_DISPOSITIONS:
            errors.append(f"{source}: invalid disposition {disposition!r}")
        if not isinstance(entry["destination"], str) or not entry["destination"]:
            errors.append(f"{source}: destination must be explicit")
        elif disposition not in {"retain", "protected/no-touch", "generated"}:
            previous = destinations.setdefault(entry["destination"], source)
            if previous != source:
                errors.append(
                    f"{source}: destination collision with {previous}: "
                    f"{entry['destination']}"
                )
        if not isinstance(entry["canonical_authority"], str) or not entry["canonical_authority"]:
            errors.append(f"{source}: canonical authority is missing")
        if not isinstance(entry["lifecycle_status"], str) or not entry["lifecycle_status"]:
            errors.append(f"{source}: lifecycle/status is missing")
        if not isinstance(entry["dependencies"], list):
            errors.append(f"{source}: dependencies must be a list")
        if not isinstance(entry["provenance_requirements"], list) or not entry[
            "provenance_requirements"
        ]:
            errors.append(f"{source}: provenance requirements must be non-empty")
        if not isinstance(entry["migration_order"], int) or entry["migration_order"] < 0:
            errors.append(f"{source}: migration order must be a non-negative integer")
        if entry["wave0_move_authorized"] is not False:
            errors.append(f"{source}: Wave 0 move authorization must be false")
        compatibility = entry["compatibility"]
        if not isinstance(compatibility, dict):
            errors.append(f"{source}: compatibility must be an object")
        elif compatibility.get("level") not in ALLOWED_COMPATIBILITY:
            errors.append(f"{source}: invalid compatibility level")
        ambiguity = entry["ambiguity"]
        if not isinstance(ambiguity, dict) or ambiguity.get("state") not in {
            "resolved",
            "blocked",
        }:
            errors.append(f"{source}: ambiguity must be resolved or blocked")
        elif ambiguity["state"] == "blocked":
            if not ambiguity.get("reason"):
                errors.append(f"{source}: blocked ambiguity needs a reason")
            else:
                blockers.append(f"{source}: {ambiguity['reason']}")
        if disposition == "protected/no-touch" and entry["compatibility"]["level"] != "critical":
            errors.append(f"{source}: protected/no-touch must have critical compatibility")

    target = payload.get("target_architecture", {})
    if target.get("status") != "authorized-for-implementation-subject-to-preflight-gates":
        errors.append("target architecture implementation status is not explicit")
    skill_module = target.get("modules", {}).get("skills", {})
    if skill_module.get("owner") != "giga-user platform":
        errors.append("modules/skills lacks explicit GIGA ownership")
    if skill_module.get("canonical_owned_source") != "modules/skills/owned":
        errors.append("modules/skills canonical owned source is missing")

    skill_section = payload.get("skills", {})
    if skill_section.get("evidence") != str(SKILL_INVENTORY.relative_to(ROOT)):
        errors.append("skills evidence path is not the exhaustive inventory")
    if skill_section.get("module", {}).get("target") != "modules/skills":
        errors.append("skills module target is not first-class modules/skills")
    if skill_section.get("module", {}).get("owner") != "giga-user platform":
        errors.append("skills module owner is missing")
    source_classes = skill_section.get("source_classes", [])
    classes = {item.get("target_class") for item in source_classes}
    missing_classes = sorted(REQUIRED_SKILL_TARGET_CLASSES - classes)
    if missing_classes:
        errors.append(f"skills topology lacks required target classes: {missing_classes}")
    if any(item.get("wave0_action") != "no-touch" for item in source_classes):
        errors.append("every skill source class must be no-touch in Wave 0")

    if SKILL_INVENTORY.exists():
        inventory = json.loads(SKILL_INVENTORY.read_text(encoding="utf-8"))
        expected_counts = inventory["summary"]["physical_manifests_by_category"]
        actual_counts = {
            item.get("source_class"): item.get("manifest_count")
            for item in source_classes
        }
        if actual_counts != expected_counts:
            errors.append("skill source-class counts drift from exhaustive inventory")
        if skill_section.get("physical_manifest_count") != inventory["summary"]["counts"][
            "physical_manifests"
        ]:
            errors.append("physical skill-manifest total mismatch")
        expected_owned = sorted(
            item["name"]
            for item in inventory["deduplicated_capabilities"]
            if "giga-owned-deploy" in item.get("categories", [])
        )
        actual_owned = sorted(
            item.get("name") for item in skill_section.get("giga_owned_skills", [])
        )
        if actual_owned != expected_owned:
            errors.append(
                f"GIGA-owned skill set mismatch: expected={expected_owned}, "
                f"actual={actual_owned}"
            )
    else:
        errors.append("exhaustive skill inventory is missing")

    lock = payload.get("root_move_lock", {})
    if lock.get("primitive") != "atomic mkdir" or lock.get("single_writer") is not True:
        errors.append("root-move lock is not an atomic single-writer contract")
    if not (HERE / lock.get("contract", "")).exists():
        errors.append("root-move lock contract file is missing")

    gate = payload.get("acceptance_gate", {})
    required_gate_flags = {
        "all_ambiguities_must_be_resolved",
        "manifest_hash_must_be_bound_to_preflight_receipt",
        "protected_sources_require_pre_and_post_hash_match",
        "moves_execute_in_declared_order",
        "compatibility_and_tests_must_pass_before_source_retirement",
        "migration_receipt_required",
        "migration_batches_must_validate",
    }
    for flag in sorted(required_gate_flags):
        if gate.get(flag) is not True:
            errors.append(f"acceptance gate flag is not true: {flag}")

    if payload.get("approval_state") == "authorized-target-preflight-blocked" and not blockers:
        errors.append(
            "approval state says preflight-blocked but no blocked ambiguity is recorded"
        )

    return errors, blockers


def _overlaps(left: str, right: str) -> bool:
    """Return whether two repository-relative path sets overlap."""

    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def validate_batches(
    payload: dict[str, Any],
    authority: dict[str, Any],
    *,
    check_live_sources: bool = True,
) -> list[str]:
    """Validate dependency order, exclusive sources and migration completeness."""

    errors: list[str] = []
    if payload.get("schema") != "giga.modularization.migration-batches.v1":
        return ["unexpected or missing migration-batch schema"]
    if "plan-only" not in payload.get("execution_authority", ""):
        errors.append("migration batches do not explicitly remain plan-only")
    if payload.get("authority_map_sha256") != hashlib.sha256(
        MANIFEST.read_bytes()
    ).hexdigest():
        errors.append("migration batches are not bound to the current authority-map hash")

    batches = payload.get("batches")
    if not isinstance(batches, list) or not batches:
        return errors + ["batches must be a non-empty list"]

    identifiers = [batch.get("id") for batch in batches]
    if len(identifiers) != len(set(identifiers)):
        errors.append("migration batch identifiers are not unique")
    orders = [batch.get("order") for batch in batches]
    if any(not isinstance(order, int) or order < 0 for order in orders):
        errors.append("every migration batch order must be a non-negative integer")
    elif orders != sorted(orders) or len(orders) != len(set(orders)):
        errors.append("migration batch orders must be unique and increasing")
    order_by_id = {
        batch.get("id"): batch.get("order")
        for batch in batches
        if isinstance(batch.get("id"), str)
    }

    all_sources: list[tuple[str, str]] = []
    all_destinations: list[tuple[str, str]] = []
    for batch in batches:
        identifier = batch.get("id", "<missing>")
        required = {
            "id",
            "order",
            "status",
            "owner",
            "depends_on",
            "lock_required",
            "source_paths",
            "source_path_set_sha256",
            "moves",
            "compatibility_updates",
            "tests",
            "rollback_checks",
            "expected_post_move_paths",
            "preconditions",
        }
        missing = sorted(required - set(batch))
        if missing:
            errors.append(f"{identifier}: missing batch fields {missing}")
            continue
        if batch["status"] != "ready-after-lock-and-preconditions":
            errors.append(f"{identifier}: batch status is not fail-closed")
        if batch["lock_required"] is not True:
            errors.append(f"{identifier}: root-move lock is not required")
        for field in ("owner",):
            if not isinstance(batch[field], str) or not batch[field]:
                errors.append(f"{identifier}: {field} must be non-empty")
        for field in (
            "source_paths",
            "moves",
            "compatibility_updates",
            "tests",
            "rollback_checks",
            "preconditions",
        ):
            if not isinstance(batch[field], list) or not batch[field]:
                errors.append(f"{identifier}: {field} must be a non-empty list")

        dependencies = batch["depends_on"]
        if not isinstance(dependencies, list):
            errors.append(f"{identifier}: depends_on must be a list")
        else:
            for dependency in dependencies:
                if dependency not in order_by_id:
                    errors.append(f"{identifier}: unknown dependency {dependency}")
                elif order_by_id[dependency] >= batch["order"]:
                    errors.append(
                        f"{identifier}: dependency {dependency} does not precede the batch"
                    )

        sources = batch["source_paths"]
        moves = batch["moves"]
        move_sources = [item.get("source") for item in moves if isinstance(item, dict)]
        destinations = [
            item.get("destination") for item in moves if isinstance(item, dict)
        ]
        if sources != move_sources:
            errors.append(f"{identifier}: source_paths do not exactly match move sources")
        if batch["expected_post_move_paths"] != destinations:
            errors.append(
                f"{identifier}: expected post-move paths do not exactly match destinations"
            )
        digest = hashlib.sha256(
            "\n".join(sorted(sources)).encode("utf-8")
        ).hexdigest()
        if digest != batch["source_path_set_sha256"]:
            errors.append(f"{identifier}: source-path-set digest mismatch")
        for item in moves:
            if not isinstance(item, dict):
                errors.append(f"{identifier}: move entry is not an object")
                continue
            source = item.get("source")
            destination = item.get("destination")
            if item.get("action") != "move":
                errors.append(f"{identifier}: unsupported action for {source}")
            if not isinstance(source, str) or not source or Path(source).is_absolute():
                errors.append(f"{identifier}: invalid source path {source!r}")
                continue
            if (
                not isinstance(destination, str)
                or not destination
                or Path(destination).is_absolute()
            ):
                errors.append(f"{identifier}: invalid destination path {destination!r}")
                continue
            if check_live_sources and not (ROOT / source).exists():
                errors.append(f"{identifier}: source path does not exist: {source}")
            all_sources.append((source, identifier))
            all_destinations.append((destination, identifier))

    for index, (source, owner) in enumerate(all_sources):
        for other, other_owner in all_sources[index + 1 :]:
            if _overlaps(source, other):
                errors.append(
                    "migration source-path overlap: "
                    f"{source} ({owner}) <-> {other} ({other_owner})"
                )
    for index, (destination, owner) in enumerate(all_destinations):
        for other, other_owner in all_destinations[index + 1 :]:
            if _overlaps(destination, other):
                errors.append(
                    "migration destination-path overlap: "
                    f"{destination} ({owner}) <-> {other} ({other_owner})"
                )

    no_touch = {
        entry["source"]
        for entry in authority["entries"]
        if entry["disposition"] == "protected/no-touch"
    }
    for source, identifier in all_sources:
        protected = sorted(
            root for root in no_touch if source == root or source.startswith(f"{root}/")
        )
        if protected:
            errors.append(
                f"{identifier}: source {source} is under protected/no-touch {protected}"
            )

    deferred = payload.get("deferred")
    if not isinstance(deferred, list):
        errors.append("deferred migration items must be a list")
        deferred_sources: set[str] = set()
    else:
        deferred_sources = {
            item.get("source") for item in deferred if isinstance(item, dict)
        }
        if any(
            not isinstance(item, dict)
            or not item.get("source")
            or not item.get("reason")
            or not item.get("required_decision")
            for item in deferred
        ):
            errors.append("every deferred item needs source, reason and required decision")

    blocked_sources = {
        entry["source"]
        for entry in authority["entries"]
        if entry["ambiguity"]["state"] == "blocked"
    }
    if deferred_sources != blocked_sources:
        errors.append(
            "deferred migration set does not equal unresolved authority blockers: "
            f"deferred={sorted(deferred_sources)}, blocked={sorted(blocked_sources)}"
        )

    migrated_sources = [source for source, _ in all_sources]
    split_roots = {"deploy", "ecc-integration", "scripts", "tests"}
    migratable = {
        entry["source"]
        for entry in authority["entries"]
        if entry["disposition"]
        in {"move", "archive", "externalize", "generated", "quarantine"}
    }
    for source in sorted(migratable - deferred_sources):
        if source in split_roots:
            children = sorted(
                str(path.relative_to(ROOT))
                for path in (ROOT / source).iterdir()
            )
            uncovered = [
                child
                for child in children
                if not any(
                    child == migrated
                    or child.startswith(f"{migrated}/")
                    or migrated.startswith(f"{child}/")
                    for migrated in migrated_sources
                )
            ]
            if uncovered:
                errors.append(f"{source}: uncovered split-root children {uncovered}")
        elif source not in migrated_sources:
            errors.append(f"{source}: resolved migratable authority entry lacks a batch")

    actual_script_routes = sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "scripts").iterdir()
        if path.is_file()
    )
    actual_test_routes = sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "tests").iterdir()
        if path.is_file()
    )
    if sorted(payload.get("script_routes", {})) != actual_script_routes:
        errors.append("script route map is not exhaustive for current source files")
    if sorted(payload.get("test_routes", {})) != actual_test_routes:
        errors.append("test route map is not exhaustive for current source files")

    skill_batch = next(
        (batch for batch in batches if batch.get("id") == "B030-specialised-skills"),
        None,
    )
    expected_owned_skill_sources = {
        "deploy/skills/librarian",
        "deploy/skills/skilltree-operator",
        "deploy/skills/librarian-workspace",
        "skilltree",
        "SKILLTREE_GIGA_USER_INTEGRATION.md",
    }
    if not skill_batch or not expected_owned_skill_sources.issubset(
        set(skill_batch.get("source_paths", []))
    ):
        errors.append("first-class specialised-skills batch is incomplete")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--batches", type=Path, default=BATCH_MANIFEST)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Fail if structurally valid blockers still prevent root moves.",
    )
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors, blockers = validate_payload(payload)
    if args.batches.exists():
        batch_payload = json.loads(args.batches.read_text(encoding="utf-8"))
        errors.extend(validate_batches(batch_payload, payload))
    else:
        errors.append("migration-batch manifest is missing")
    digest = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    print(
        json.dumps(
            {
                "schema": "giga.modularization.preflight-validation.v1",
                "manifest": str(args.manifest),
                "manifest_sha256": digest,
                "structurally_valid": not errors,
                "acceptance_ready": not errors and not blockers,
                "entry_count": len(payload.get("entries", [])),
                "migration_batch_count": (
                    len(batch_payload.get("batches", []))
                    if args.batches.exists()
                    else 0
                ),
                "errors": errors,
                "blockers": blockers,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    if errors:
        return 1
    if args.require_ready and blockers:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
