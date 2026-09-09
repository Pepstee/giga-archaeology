#!/usr/bin/env python3
"""Validate ECC extraction coverage, provenance and staged destinations."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class ExtractionError(ValueError):
    pass


class CodedExtractionError(ExtractionError):
    """Extraction failure carrying a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


SKILLTREE_LAYOUT = {
    "audit": "deploy/skills/skilltree-operator/scripts/audit_tree.py",
    "export": "outputs/skilltree-export-2026-07-22",
    "evidence_map": "deploy/skills/skilltree-operator/references/evidence-map.json",
    "output": "skilltree/implementation-registry.json",
    "report": "skilltree/IMPLEMENTATION_STATUS.md",
    "compat_report": "skilltree/IMPLEMENTATION_REPORT.md",
}
SKILLTREE_TIMEOUT_SECONDS = 120


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"cannot read valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ExtractionError(f"JSON root must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(root: Path, relative: str, label: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ExtractionError(f"{label} must be relative: {relative}")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ExtractionError(f"{label} escapes its root: {relative}") from exc
    return resolved


def validate(root: Path, upstream: Path, findings_path: Path) -> dict[str, Any]:
    root = root.resolve()
    upstream = upstream.resolve()
    findings = _load(findings_path)
    inventory = _load(root / "ecc-integration/COMPONENT_INVENTORY.json")
    classification = _load(root / "ecc-integration/SKILL_CLASSIFICATION.json")
    upstream_pin = _load(root / "ecc-integration/UPSTREAM.json")
    import_ledger = _load(root / "ecc-integration/IMPORT_LEDGER.json")

    if findings.get("schema") != "giga.ecc-portable-findings.v1":
        raise ExtractionError("unsupported portable-findings schema")
    commit = findings.get("upstream_commit")
    if not isinstance(commit, str) or commit != upstream_pin.get("commit"):
        raise ExtractionError("portable-findings commit disagrees with upstream pin")
    if (
        inventory.get("commit") != commit
        or classification.get("commit") != commit
        or import_ledger.get("commit") != commit
    ):
        raise ExtractionError("inventory, classification or import ledger commit drift")
    if findings.get("extraction_status") != "complete-for-pinned-commit":
        raise ExtractionError("extraction is not marked complete for the pinned commit")

    source_files = inventory.get("files")
    skills = classification.get("skills")
    if not isinstance(source_files, list) or len(source_files) != inventory.get(
        "counts", {}
    ).get("files"):
        raise ExtractionError("component inventory file count mismatch")
    if not isinstance(skills, list) or len(skills) != inventory.get("counts", {}).get(
        "skills"
    ):
        raise ExtractionError("canonical skill count mismatch")
    for record in source_files:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise ExtractionError("component inventory contains an invalid file record")
        source_path = _contained(upstream, record["path"], "inventory source")
        if not source_path.is_file():
            raise ExtractionError(f"inventoried source is missing: {record['path']}")
        if source_path.stat().st_size != record.get("bytes") or _sha256(
            source_path
        ) != record.get("sha256"):
            raise ExtractionError(f"inventoried source changed: {record['path']}")
    candidates = {
        row.get("name") for row in skills if row.get("disposition") == "adapt_candidate"
    }
    coverage = findings.get("candidate_skill_coverage")
    if not isinstance(coverage, dict) or set(coverage) != candidates:
        missing = sorted(candidates - set(coverage or {}))
        extra = sorted(set(coverage or {}) - candidates)
        raise ExtractionError(
            f"adaptation-candidate coverage mismatch; missing={missing}, extra={extra}"
        )

    portable = findings.get("portable_findings")
    if not isinstance(portable, list) or not portable:
        raise ExtractionError("portable findings must be a non-empty array")
    ids = [item.get("id") for item in portable if isinstance(item, dict)]
    if (
        len(ids) != len(portable)
        or any(not isinstance(item, str) or not item for item in ids)
        or len(ids) != len(set(ids))
    ):
        raise ExtractionError("portable finding ids must be non-empty and unique")
    finding_ids = set(ids)
    decisions = {
        "implemented-read-only",
        "staged-specification",
        "already-covered",
        "deferred-on-demand",
        "deferred-until-enforcement",
    }
    source_pairs: set[tuple[str, str]] = set()
    staged = 0
    for item in portable:
        decision = item.get("decision")
        if decision not in decisions:
            raise ExtractionError(f"invalid portable finding decision: {decision}")
        destination = item.get("destination")
        if decision != "deferred-on-demand":
            if not isinstance(destination, str) or not destination:
                raise ExtractionError(f"finding {item['id']} lacks a destination")
            target = _contained(root, destination, "destination")
            if not target.is_file():
                raise ExtractionError(f"finding destination is missing: {destination}")
        if decision == "staged-specification":
            staged += 1
        sources = item.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ExtractionError(f"finding {item['id']} has no sources")
        for source in sources:
            if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
                raise ExtractionError(
                    f"finding {item['id']} has an invalid source record"
                )
            source_path = _contained(upstream, source["path"], "source")
            if not source_path.is_file():
                raise ExtractionError(f"source is missing: {source['path']}")
            if _sha256(source_path) != source["sha256"]:
                raise ExtractionError(f"source hash mismatch: {source['path']}")
            source_pairs.add((source["path"], source["sha256"]))

    for name, record in coverage.items():
        if not isinstance(record, dict) or record.get("finding_id") not in finding_ids:
            raise ExtractionError(f"candidate {name} points to an unknown finding")
        source_path = _contained(
            upstream, record.get("source_path", ""), "candidate source"
        )
        if not source_path.is_file() or _sha256(source_path) != record.get(
            "source_sha256"
        ):
            raise ExtractionError(f"candidate source hash mismatch: {name}")

    if import_ledger.get("deployed") is not False:
        raise ExtractionError("ECC import ledger must remain globally undeployed")
    for entry in import_ledger.get("entries", []):
        pair = (entry.get("source_path"), entry.get("source_sha256"))
        if pair not in source_pairs:
            raise ExtractionError(
                f"import-ledger source is absent from portable findings: {entry.get('id')}"
            )

    scope = findings.get("scope", {})
    expected = {
        "source_files_in_inventory": len(source_files),
        "canonical_skills": len(skills),
        "canonical_skills_with_disposition": len(skills),
        "adaptation_candidates": len(candidates),
    }
    for key, value in expected.items():
        if scope.get(key) != value:
            raise ExtractionError(f"scope count mismatch: {key}")
    return {
        "status": "pass",
        "commit": commit,
        "source_files": len(source_files),
        "inventory_hashes_verified": len(source_files),
        "canonical_skills": len(skills),
        "adaptation_candidates": len(candidates),
        "portable_findings": len(portable),
        "staged_specifications": staged,
        "ledger_entries": len(import_ledger.get("entries", [])),
    }


def _run_child(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        timeout=SKILLTREE_TIMEOUT_SECONDS,
    )


def validate_skilltree_truth(root: Path, evidence_root: Path) -> dict[str, Any]:
    """Replay the exact read-only SkillTree status check on every invocation.

    The audit script runs as a fixed argument-list subprocess (no shell). Every
    canonical source-authority and output path is pre-contained under the
    resolved source root; ``evidence_root`` is read-only and only decides
    whether declared repository-relative evidence exists.
    """
    root = root.resolve()
    evidence_root = evidence_root.resolve()
    if not evidence_root.is_dir():
        raise CodedExtractionError(
            "skilltree-invalid-input",
            f"skilltree evidence root is not a directory: {evidence_root}",
        )

    paths: dict[str, Path] = {}
    try:
        for label, relative in SKILLTREE_LAYOUT.items():
            unresolved = root / relative
            contained = _contained(root, relative, f"skilltree {label}")
            if label == "export":
                if not contained.is_dir():
                    raise ExtractionError(f"skilltree export is missing: {relative}")
            elif not contained.is_file():
                raise ExtractionError(f"skilltree {label} is missing: {relative}")
            elif label != "compat_report" and unresolved.is_symlink():
                raise ExtractionError(
                    f"skilltree {label} must not be a symlink: {relative}"
                )
            paths[label] = contained
        skill_root = _contained(root, "deploy/skills", "skilltree skill root")
        if not skill_root.is_dir():
            raise ExtractionError("skilltree skill root is missing: deploy/skills")
    except ExtractionError as exc:
        raise CodedExtractionError("skilltree-invalid-input", str(exc)) from exc

    compatibility = root / SKILLTREE_LAYOUT["compat_report"]
    authority_paths = {
        "audit": paths["audit"],
        "evidence_map": paths["evidence_map"],
        "tree": paths["export"] / "data/tree.json",
        "playbook": paths["export"] / "data/playbook.json",
    }
    try:
        pre_authority_hashes = {
            label: _sha256(path) for label, path in authority_paths.items()
        }
        pre_registry_hash = _sha256(paths["output"])
        pre_status_hash = _sha256(paths["report"])
        pre_compatibility_target = (
            str(compatibility.readlink()) if compatibility.is_symlink() else None
        )
    except OSError as exc:
        raise CodedExtractionError(
            "skilltree-invalid-input",
            f"skilltree tracked surface cannot be read: {exc}",
        ) from exc

    command = [
        sys.executable,
        str(paths["audit"]),
        "--root",
        str(root),
        "--export",
        str(root / SKILLTREE_LAYOUT["export"]),
        "--evidence-map",
        str(root / SKILLTREE_LAYOUT["evidence_map"]),
        "--evidence-root",
        str(evidence_root),
        "--skill-root",
        str(skill_root),
        "--output",
        str(root / SKILLTREE_LAYOUT["output"]),
        "--report",
        str(root / SKILLTREE_LAYOUT["report"]),
        "--compat-report",
        str(root / SKILLTREE_LAYOUT["compat_report"]),
        "--check",
    ]
    try:
        completed = _run_child(command)
    except subprocess.TimeoutExpired as exc:
        raise CodedExtractionError(
            "skilltree-timeout", "skilltree capability replay timed out"
        ) from exc
    except UnicodeError as exc:
        raise CodedExtractionError(
            "skilltree-child-unreadable",
            "skilltree capability replay produced non-UTF-8 output",
        ) from exc
    except OSError as exc:
        raise CodedExtractionError(
            "skilltree-spawn-error", f"skilltree audit could not start: {exc}"
        ) from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise CodedExtractionError(
            "skilltree-replay-failed",
            f"skilltree capability replay failed: {detail}",
        )
    try:
        verdict = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CodedExtractionError(
            "skilltree-child-unreadable",
            "skilltree capability replay produced unreadable output",
        ) from exc
    if not isinstance(verdict, dict):
        raise CodedExtractionError(
            "skilltree-child-unreadable",
            "skilltree capability replay returned a non-object verdict",
        )
    counts = verdict.get("counts")
    valid_counts = isinstance(counts, dict) and all(
        isinstance(key, str)
        and isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
        for key, value in counts.items()
    )
    if verdict.get("check") != "ok" or not valid_counts:
        raise CodedExtractionError(
            "skilltree-child-unreadable",
            "skilltree capability replay refused the tracked surfaces",
        )
    assert isinstance(counts, dict)
    expected_child_paths = {
        "output": str(root / SKILLTREE_LAYOUT["output"]),
        "report": str(root / SKILLTREE_LAYOUT["report"]),
        "compat_report": str(compatibility),
    }
    if any(verdict.get(key) != value for key, value in expected_child_paths.items()):
        raise CodedExtractionError(
            "skilltree-child-unreadable",
            "skilltree capability replay returned mismatched governed paths",
        )
    try:
        post_authority_hashes = {
            label: _sha256(path) for label, path in authority_paths.items()
        }
        post_registry_hash = _sha256(paths["output"])
        post_status_hash = _sha256(paths["report"])
        post_compatibility_target = (
            str(compatibility.readlink()) if compatibility.is_symlink() else None
        )
    except OSError as exc:
        raise CodedExtractionError(
            "skilltree-replay-raced",
            f"skilltree tracked surface changed during replay: {exc}",
        ) from exc
    if (
        pre_authority_hashes != post_authority_hashes
        or pre_registry_hash != post_registry_hash
        or pre_status_hash != post_status_hash
        or pre_compatibility_target != post_compatibility_target
    ):
        raise CodedExtractionError(
            "skilltree-replay-raced",
            "skilltree tracked surfaces changed during capability replay",
        )
    if post_compatibility_target != "IMPLEMENTATION_STATUS.md":
        raise CodedExtractionError(
            "skilltree-replay-failed",
            "skilltree compatibility surface must use the canonical relative target",
        )
    return {
        "status": "pass",
        "jobs_total": sum(int(value) for value in counts.values()),
        "counts": counts,
        "authority_sha256": post_authority_hashes,
        "registry_sha256": post_registry_hash,
        "status_sha256": post_status_hash,
        "compatibility_target": post_compatibility_target,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--upstream", type=Path, default=default_root / "upstreams/ECC")
    parser.add_argument(
        "--findings",
        type=Path,
        default=default_root / "ecc-integration/PORTABLE_FINDINGS.json",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=None,
        help="read-only root resolving declared repository-relative SkillTree evidence "
        "(defaults to --root; a clean clone without ignored evidence fails closed)",
    )
    args = parser.parse_args()
    try:
        report = validate(args.root, args.upstream, args.findings)
        report["skilltree"] = validate_skilltree_truth(
            args.root, args.evidence_root or args.root
        )
        print(json.dumps(report, sort_keys=True))
        return 0
    except ExtractionError as exc:
        print(
            json.dumps(
                {
                    "status": "fail",
                    "error": {
                        "code": getattr(exc, "code", "extraction-invalid"),
                        "message": str(exc),
                    },
                },
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
