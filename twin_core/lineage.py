"""Operator-authorized adoption of verified current derived-artifact state.

This is deliberately distinct from a rebuild.  It preserves the old registration as a
superseded revision and records why the present file/source combination was accepted.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts.verify_derived_agent_payloads import (
    DerivedPayloadError,
    verify_derived_payloads,
)

from .integrity import sha256_file, verify_hash_baseline
from .memory_validation import validate_memory
from .store import TwinStore


class LineageReconciliationError(ValueError):
    """The requested adoption did not pass its deterministic gates."""


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _inside(root: Path, relative: str, *, field: str) -> tuple[str, Path]:
    if not isinstance(relative, str) or not relative.strip():
        raise LineageReconciliationError(f"{field} must be a non-empty relative path")
    candidate = (root / relative).resolve()
    try:
        normalised = str(candidate.relative_to(root))
    except ValueError as exc:
        raise LineageReconciliationError(
            f"{field} escapes the GIGA root: {relative}"
        ) from exc
    return normalised, candidate


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _write_immutable(path: Path, content: str) -> None:
    encoded = content.encode("utf-8")
    if path.exists():
        if path.read_bytes() != encoded:
            raise LineageReconciliationError(f"immutable report collision: {path}")
        return
    _write_atomic(path, content)


def _run_canonical_tests(root: Path) -> dict[str, Any]:
    try:
        derived_payloads = verify_derived_payloads(root)
    except DerivedPayloadError as exc:
        return {
            "ok": False,
            "command": [
                ["python3", "scripts/verify_derived_agent_payloads.py"],
                ["python3", "-W", "error", "-m", "pytest", "-q", "tests"],
            ],
            "returncode": 1,
            "output_sha256": hashlib.sha256(str(exc).encode("utf-8")).hexdigest(),
            "summary": f"derived-payload governance gate failed: {exc}",
            "derived_payloads": {"status": "FAIL", "error": str(exc)},
        }
    command = [sys.executable, "-W", "error", "-m", "pytest", "-q", "tests"]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    output = (completed.stdout + completed.stderr).strip()
    return {
        "ok": derived_payloads["status"] == "PASS" and completed.returncode == 0,
        "command": [
            ["python3", "scripts/verify_derived_agent_payloads.py"],
            ["python3", "-W", "error", "-m", "pytest", "-q", "tests"],
        ],
        "returncode": completed.returncode,
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "summary": output[-2_000:],
        "derived_payloads": derived_payloads,
    }


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Derived-artifact lineage reconciliation",
        "",
        f"*Operator-authorized current-state adoption · {report['confirmed_at']}*",
        "",
        "This receipt is **not a claim that the architecture files were rebuilt**. The current",
        "files and their current sources passed the declared gates, so they were adopted as new",
        "`reconciled` revisions. Every prior registration remains stored as `superseded` history.",
        "",
        "## Gates",
        "",
        f"- Derived deployment payloads: {report['gates']['tests']['derived_payloads']['status']}",
        f"- Canonical tests: PASS — `{report['gates']['tests']['summary'].splitlines()[-1]}`",
        f"- Immutable exports: {'PASS' if report['gates']['exports']['ok'] else 'FAIL'}",
        f"- Memory validation: {'PASS' if report['gates']['memory']['ok'] else 'FAIL'}",
        f"- Uncovered failing registrations before adoption: {len(report['uncovered_failures'])}",
        "",
        "## Revision transitions",
        "",
        "| Artefact | Previous revision | Current revision | Action |",
        "|---|---|---|---|",
    ]
    for item in report["artifacts"]:
        lines.append(
            f"| `{item['path']}` | `{item['previous_revision_id'] or 'none'}` | "
            f"`{item['current_revision_id']}` | {item['action']} |"
        )
    lines.extend(
        [
            "",
            "## Result",
            "",
            f"- Active registrations: {report['after']['lineage']['active']}",
            f"- Stored revisions: {report['after']['lineage']['revisions']}",
            f"- Superseded revisions retained: {report['after']['lineage']['superseded']}",
            f"- Aggregate current-lineage audit: {'PASS' if report['after']['ok'] else 'FAIL'}",
            f"- Authority event: `{report['authority_event_id']}`",
            f"- Policy SHA-256: `{report['policy_sha256']}`",
            f"- Immutable JSON receipt: `{report['immutable_reports']['json']}`",
            f"- Immutable Markdown receipt: `{report['immutable_reports']['markdown']}`",
            *(
                [
                    f"- Recovery backup: `{report['recovery']['backup']}` "
                    f"(`{report['recovery']['sha256']}`)"
                ]
                if report.get("recovery")
                else []
            ),
            "",
        ]
    )
    return "\n".join(lines)


def reconcile_lineage(
    *,
    root: Path,
    manifest: Path,
    store: TwinStore,
    report_json: Path,
    report_markdown: Path,
) -> dict[str, Any]:
    """Validate, adopt and receipt a bounded set of current artefact/source states."""
    root = root.resolve()
    manifest = manifest.resolve()
    try:
        manifest.relative_to(root)
    except ValueError as exc:
        raise LineageReconciliationError(
            "manifest must be inside the GIGA root"
        ) from exc
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise LineageReconciliationError("lineage manifest schema_version must be 1")
    authority = raw.get("authority")
    artifacts = raw.get("artifacts")
    if (
        not isinstance(authority, dict)
        or not isinstance(artifacts, list)
        or not artifacts
    ):
        raise LineageReconciliationError(
            "manifest requires authority and non-empty artifacts"
        )
    if authority.get("actor") != "operator":
        raise LineageReconciliationError(
            "lineage adoption authority must be the operator"
        )
    confirmed_at = authority.get("confirmed_at")
    basis = authority.get("basis")
    if (
        not isinstance(confirmed_at, str)
        or not isinstance(basis, str)
        or not basis.strip()
    ):
        raise LineageReconciliationError("authority requires confirmed_at and basis")

    recovery_result: dict[str, Any] | None = None
    recovery = raw.get("recovery")
    if recovery is not None:
        if not isinstance(recovery, dict):
            raise LineageReconciliationError("recovery must be an object")
        backup_value, expected_backup_sha = (
            recovery.get("backup"),
            recovery.get("sha256"),
        )
        if not isinstance(backup_value, str) or not isinstance(
            expected_backup_sha, str
        ):
            raise LineageReconciliationError("recovery requires backup and sha256")
        backup = Path(backup_value).expanduser().resolve()
        if not backup.is_file():
            raise LineageReconciliationError(f"recovery backup is missing: {backup}")
        actual_backup_sha = sha256_file(backup)
        if actual_backup_sha != expected_backup_sha:
            raise LineageReconciliationError(
                "recovery backup hash does not match the policy"
            )
        recovery_result = {
            "backup": str(backup),
            "sha256": actual_backup_sha,
            "owner_only": (backup.stat().st_mode & 0o777) == 0o600,
        }
        if not recovery_result["owner_only"]:
            raise LineageReconciliationError("recovery backup must be owner-only")

    policy_sha256 = sha256_file(manifest)
    try:
        json_relative = str(report_json.resolve().relative_to(root))
        markdown_relative = str(report_markdown.resolve().relative_to(root))
    except ValueError as exc:
        raise LineageReconciliationError(
            "reports must be inside the GIGA root"
        ) from exc
    json_relative, report_json_path = _inside(root, json_relative, field="JSON report")
    markdown_relative, report_markdown_path = _inside(
        root, markdown_relative, field="Markdown report"
    )
    tests = _run_canonical_tests(root)
    exports = verify_hash_baseline(
        root, root / "architecture" / "EXPORT_IMMUTABILITY_BASELINE.sha256"
    )
    memory = validate_memory(root / "memory")
    if not tests["ok"] or not exports["ok"] or not memory["ok"]:
        raise LineageReconciliationError(
            "lineage gates failed: "
            + _canonical(
                {"tests": tests["ok"], "exports": exports["ok"], "memory": memory["ok"]}
            )
        )

    prepared: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, specification in enumerate(artifacts):
        if not isinstance(specification, dict):
            raise LineageReconciliationError(f"artifacts[{index}] must be an object")
        relative, artifact_path = _inside(
            root, specification.get("path"), field="artifact path"
        )
        if relative in seen:
            raise LineageReconciliationError(f"duplicate artifact path: {relative}")
        seen.add(relative)
        if not artifact_path.is_file():
            raise LineageReconciliationError(f"artifact is missing: {relative}")
        text = artifact_path.read_text(encoding="utf-8")
        headings = specification.get("required_headings")
        if not isinstance(headings, list) or not headings:
            raise LineageReconciliationError(
                f"required_headings missing for {relative}"
            )
        missing_headings = [
            heading for heading in headings if f"{heading}\n" not in f"{text}\n"
        ]
        if missing_headings:
            raise LineageReconciliationError(
                f"required headings missing from {relative}: {missing_headings}"
            )
        source_specs = specification.get("sources")
        if not isinstance(source_specs, list) or not source_specs:
            raise LineageReconciliationError(f"sources missing for {relative}")
        sources: list[dict[str, str]] = []
        for source in source_specs:
            source_relative, source_path = _inside(
                root, source, field=f"source for {relative}"
            )
            if not source_path.is_file():
                raise LineageReconciliationError(
                    f"source is missing: {source_relative}"
                )
            sources.append(
                {"path": source_relative, "sha256": sha256_file(source_path)}
            )
        prepared.append(
            {
                "path": relative,
                "artifact_sha256": sha256_file(artifact_path),
                "source_refs": sources,
                "build_command": specification.get(
                    "adoption_statement",
                    "operator-authorized current-state lineage reconciliation",
                ),
            }
        )

    before = store.audit_artifacts(root)
    failing_before = [item["path"] for item in before["artifacts"] if not item["ok"]]
    uncovered = sorted(set(failing_before) - seen)
    if uncovered:
        raise LineageReconciliationError(
            f"uncovered failing registrations must be resolved first: {uncovered}"
        )

    state = {
        "policy_sha256": policy_sha256,
        "recovery": recovery_result,
        "artifacts": [
            {
                "path": item["path"],
                "artifact_sha256": item["artifact_sha256"],
                "source_refs": item["source_refs"],
            }
            for item in prepared
        ],
        "gates": {
            "tests_command": tests["command"],
            "tests_ok": tests["ok"],
            "derived_payloads_ok": tests["derived_payloads"]["status"] == "PASS",
            "exports_ok": exports["ok"],
            "memory_ok": memory["ok"],
        },
    }
    fingerprint = hashlib.sha256(_canonical(state).encode("utf-8")).hexdigest()
    archive_directory = report_json_path.parent / "lineage-reconciliation"
    archive_json_path = archive_directory / f"{fingerprint}.json"
    archive_markdown_path = archive_directory / f"{fingerprint}.md"
    archive_json_relative = str(archive_json_path.relative_to(root))
    archive_markdown_relative = str(archive_markdown_path.relative_to(root))
    event_payload = {
        "authority_basis": basis,
        "scope": [item["path"] for item in prepared],
        "state_fingerprint": fingerprint,
        "policy_sha256": policy_sha256,
        "recovery": recovery_result,
        "adoption_semantics": "verified current state; not represented as a rebuild",
    }
    event_id, event_created = store.record_event(
        idempotency_key=f"lineage-reconciliation:v1:{fingerprint}",
        kind="lineage.reconciliation.authorized",
        observed_at=confirmed_at,
        source="operator-request",
        actor="operator",
        trust_class="operator_confirmed",
        sensitivity="internal",
        payload=event_payload,
        content_ref=str(manifest.relative_to(root)),
    )
    if not event_created:
        receipt = store.latest_receipt(event_id, "lineage.reconcile")
        if (
            receipt is not None
            and archive_json_path.is_file()
            and archive_markdown_path.is_file()
        ):
            recorded = {item["path"]: item["sha256"] for item in receipt["artifacts"]}
            reports_match = all(
                recorded.get(relative) == sha256_file(path)
                for relative, path in (
                    (archive_json_relative, archive_json_path),
                    (archive_markdown_relative, archive_markdown_path),
                )
            )
            saved = json.loads(archive_json_path.read_text(encoding="utf-8"))
            if reports_match and saved.get("state_fingerprint") == fingerprint:
                _write_atomic(
                    report_json_path, archive_json_path.read_text(encoding="utf-8")
                )
                _write_atomic(
                    report_markdown_path,
                    archive_markdown_path.read_text(encoding="utf-8"),
                )
                return {**saved, "replay": True, "receipt_id": receipt["id"]}

    transitions: list[dict[str, Any]] = []
    verification = {
        "ok": True,
        "method": "operator-authorized-current-state-adoption",
        "not_a_rebuild": True,
        "policy_sha256": policy_sha256,
        "tests_command": tests["command"],
        "canonical_tests_ok": True,
        "derived_payloads_ok": True,
        "exports_ok": True,
        "memory_ok": True,
    }
    for item in prepared:
        current = next(
            (
                entry
                for entry in store.artifact_history(item["path"])
                if entry["status"] == "current"
            ),
            None,
        )
        current_audit = next(
            entry for entry in before["artifacts"] if entry["path"] == item["path"]
        )
        if current_audit["ok"] and current is not None:
            revision_id = current["id"]
            action = "retained"
        else:
            revision_id = store.reconcile_artifact(
                **item,
                authority_event_id=event_id,
                verification=verification,
                built_at=confirmed_at,
            )
            action = "reconciled"
        transitions.append(
            {
                "path": item["path"],
                "action": action,
                "previous_revision_id": current["id"] if current else None,
                "previous_artifact_sha256": current["artifact_sha256"]
                if current
                else None,
                "current_revision_id": revision_id,
                "current_artifact_sha256": item["artifact_sha256"],
                "source_refs": item["source_refs"],
            }
        )

    after = store.audit_artifacts(root)
    if not after["ok"]:
        raise RuntimeError("post-reconciliation artifact audit failed")
    report = {
        "ok": True,
        "semantics": "verified current-state adoption; not a rebuild",
        "confirmed_at": confirmed_at,
        "authority_event_id": event_id,
        "policy": str(manifest.relative_to(root)),
        "policy_sha256": policy_sha256,
        "recovery": recovery_result,
        "state_fingerprint": fingerprint,
        "immutable_reports": {
            "json": archive_json_relative,
            "markdown": archive_markdown_relative,
        },
        "before_failing_paths": failing_before,
        "uncovered_failures": uncovered,
        "gates": {"tests": tests, "exports": exports, "memory": memory},
        "artifacts": transitions,
        "after": {"ok": after["ok"], "lineage": after["lineage"]},
    }
    json_content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    markdown_content = _markdown_report(report)
    _write_immutable(archive_json_path, json_content)
    _write_immutable(archive_markdown_path, markdown_content)
    _write_atomic(report_json_path, json_content)
    _write_atomic(report_markdown_path, markdown_content)
    store.record_receipt(
        event_id=event_id,
        operation="lineage.reconcile",
        status="committed",
        artifacts=[
            {"path": archive_json_relative, "sha256": sha256_file(archive_json_path)},
            {
                "path": archive_markdown_relative,
                "sha256": sha256_file(archive_markdown_path),
            },
        ],
        details={
            "state_fingerprint": fingerprint,
            "reconciled_paths": [item["path"] for item in transitions],
            "current_audit_ok": True,
            "latest_report_aliases": [json_relative, markdown_relative],
        },
    )
    return report
