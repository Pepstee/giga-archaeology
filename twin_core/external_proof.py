"""Deterministic, draft-only compilation of evidence-linked public proof artefacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .integrity import sha256_file
from .store import TwinStore, utc_now


COMPILER_VERSION = "1.0.0"
OUTPUT_NAMES = {
    "case-study.md",
    "technical-report.md",
    "presentation-outline.md",
    "qa.json",
    "build-manifest.json",
    "trust-receipt.json",
}
PROHIBITED_SOURCE_ROOTS = {
    "corpus",
    "memory",
    "market-aligner",
    "market-aligner-artiom",
    "graphify-out",
}
CLAIM_ID = re.compile(r"^[A-Z][A-Z0-9_-]{0,31}$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PUBLIC_SECRET_PATTERNS = {
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "provider token": re.compile(r"\b(?:sk|gh[pousr])_[A-Za-z0-9_-]{20,}\b"),
    "credential assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|password|secret|bearer|token)\b\s*[:=]\s*[^\s]{8,}"
    ),
}


class ProofValidationError(ValueError):
    """Raised when an input cannot pass the deterministic draft-release gate."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
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


def _json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _relative_file(root: Path, value: str, field: str) -> tuple[Path, str]:
    if not isinstance(value, str) or not value.strip():
        raise ProofValidationError(f"{field} must be a non-empty relative path")
    raw = Path(value)
    if raw.is_absolute():
        raise ProofValidationError(f"{field} must stay inside the giga-user root")
    candidate = (root / raw).resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ProofValidationError(f"{field} escapes the giga-user root: {value}") from exc
    if not candidate.is_file():
        raise ProofValidationError(f"{field} is not a regular file: {value}")
    return candidate, relative.as_posix()


def _output_directory(root: Path, value: Path) -> tuple[Path, str]:
    candidate = value.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ProofValidationError("output directory must stay inside the giga-user root") from exc
    parts = relative.parts
    if len(parts) < 3 or parts[:2] != ("outputs", "external-proof"):
        raise ProofValidationError("output directory must be under outputs/external-proof/<run>")
    if candidate.exists():
        unexpected = [
            item.relative_to(candidate).as_posix()
            for item in candidate.rglob("*")
            if item.is_file() and item.relative_to(candidate).as_posix() not in OUTPUT_NAMES
        ]
        if unexpected:
            raise ProofValidationError(f"output directory contains unexpected files: {unexpected}")
    return candidate, relative.as_posix()


def _check_public_text(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProofValidationError(f"{label} must be non-empty text")
    for pattern_name, pattern in PUBLIC_SECRET_PATTERNS.items():
        if pattern.search(value):
            raise ProofValidationError(f"{label} contains a prohibited {pattern_name}")


def _line_span(text: str, needle: str) -> tuple[int, int]:
    offset = text.find(needle)
    if offset < 0:
        raise ProofValidationError(f"evidence needle not found: {needle!r}")
    start = text.count("\n", 0, offset) + 1
    end = start + needle.count("\n")
    return start, end


def _claim_line(claim: Mapping[str, Any]) -> str:
    label = "Inference" if claim["kind"] == "inference" else (
        "Limitation" if claim["kind"] == "limitation" else "Claim"
    )
    return f"- **{label} {claim['id']}:** {claim['statement']}"


def _source_note(claim: Mapping[str, Any]) -> str:
    notes = []
    for evidence in claim["resolved_evidence"]:
        spans = ", ".join(
            f"L{item['line_start']}" if item["line_start"] == item["line_end"]
            else f"L{item['line_start']}-L{item['line_end']}"
            for item in evidence["matches"]
        )
        notes.append(f"`{evidence['path']}` ({spans}; sha256 `{evidence['sha256']}`)")
    return "; ".join(notes)


def _validate_manifest(root: Path, manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProofValidationError("manifest must be valid UTF-8 JSON") from exc
    if not isinstance(document, dict) or document.get("schema_version") != "1.0":
        raise ProofValidationError("manifest schema_version must be 1.0")
    if document.get("mode") != "draft" or document.get("authority_level") != "A1":
        raise ProofValidationError("external-proof compilation is restricted to draft mode at A1")
    slug = document.get("slug")
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise ProofValidationError("slug must be lowercase hyphen-case")
    for field in ("title", "summary"):
        _check_public_text(field, document.get(field))

    claims = document.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ProofValidationError("manifest needs at least one claim")
    by_id: dict[str, dict[str, Any]] = {}
    source_refs: dict[str, dict[str, str]] = {}
    for index, raw_claim in enumerate(claims):
        if not isinstance(raw_claim, dict):
            raise ProofValidationError(f"claim {index} must be an object")
        claim_id = raw_claim.get("id")
        if not isinstance(claim_id, str) or not CLAIM_ID.fullmatch(claim_id):
            raise ProofValidationError(f"invalid claim id: {claim_id!r}")
        if claim_id in by_id:
            raise ProofValidationError(f"duplicate claim id: {claim_id}")
        kind = raw_claim.get("kind")
        if kind not in {"fact", "inference", "limitation"}:
            raise ProofValidationError(f"invalid claim kind for {claim_id}")
        _check_public_text(f"claim {claim_id}", raw_claim.get("statement"))
        evidence_items = raw_claim.get("evidence")
        if not isinstance(evidence_items, list) or not evidence_items:
            raise ProofValidationError(f"claim {claim_id} has no evidence")
        resolved = []
        for item in evidence_items:
            if not isinstance(item, dict):
                raise ProofValidationError(f"claim {claim_id} evidence must be an object")
            path, relative = _relative_file(root, item.get("path"), f"claim {claim_id} evidence")
            parts = Path(relative).parts
            if parts[0].casefold() in PROHIBITED_SOURCE_ROOTS or any(
                part.casefold().startswith(".env") for part in parts
            ):
                raise ProofValidationError(f"claim {claim_id} uses a prohibited source: {relative}")
            needles = item.get("needles")
            if not isinstance(needles, list) or not needles or not all(
                isinstance(needle, str) and needle for needle in needles
            ):
                raise ProofValidationError(f"claim {claim_id} needs exact evidence needles")
            text = path.read_text(encoding="utf-8")
            matches = []
            for needle in needles:
                start, end = _line_span(text, needle)
                matches.append({"needle_sha256": _digest_text(needle), "line_start": start, "line_end": end})
            digest = sha256_file(path)
            source_refs[relative] = {"path": relative, "sha256": digest}
            resolved.append({"path": relative, "sha256": digest, "matches": matches})
        claim = {**raw_claim, "resolved_evidence": resolved}
        by_id[claim_id] = claim

    def references(values: Any, label: str) -> list[dict[str, Any]]:
        if not isinstance(values, list) or not values:
            raise ProofValidationError(f"{label} must be a non-empty list")
        result = []
        for value in values:
            if not isinstance(value, str) or value not in by_id:
                raise ProofValidationError(f"{label} references unknown claim: {value!r}")
            result.append(by_id[value])
        return result

    case = document.get("case_study")
    if not isinstance(case, dict):
        raise ProofValidationError("case_study must be an object")
    document["resolved_case_study"] = {
        key: references(case.get(key), f"case_study.{key}")
        for key in ("problem_claim_ids", "intervention_claim_ids", "limitation_claim_ids")
    }
    for collection_name, heading_field in (("report_sections", "heading"), ("slides", "title")):
        collection = document.get(collection_name)
        if not isinstance(collection, list) or not collection:
            raise ProofValidationError(f"{collection_name} must be a non-empty list")
        resolved_collection = []
        for item in collection:
            if not isinstance(item, dict):
                raise ProofValidationError(f"{collection_name} entries must be objects")
            _check_public_text(f"{collection_name} {heading_field}", item.get(heading_field))
            resolved_collection.append({
                **item,
                "claims": references(item.get("claim_ids"), f"{collection_name}.claim_ids"),
            })
        document[f"resolved_{collection_name}"] = resolved_collection
    document["claims_by_id"] = by_id
    return document, sorted(source_refs.values(), key=lambda item: item["path"])


def _render_case_study(document: Mapping[str, Any]) -> str:
    case = document["resolved_case_study"]
    lines = [
        f"# {document['title']}", "",
        "> **DRAFT · A1 advisory authority · not approved for publication**", "",
        document["summary"], "", "## Problem", "",
    ]
    lines.extend(_claim_line(item) for item in case["problem_claim_ids"])
    lines.extend(["", "## What was built", ""])
    lines.extend(_claim_line(item) for item in case["intervention_claim_ids"])
    lines.extend(["", "## Current limits", ""])
    lines.extend(_claim_line(item) for item in case["limitation_claim_ids"])
    lines.extend(["", "## Evidence lineage", "", "| Claim | Type | Source |", "|---|---|---|"])
    for claim in document["claims"]:
        resolved = document["claims_by_id"][claim["id"]]
        lines.append(f"| {claim['id']} | {claim['kind']} | {_source_note(resolved)} |")
    lines.extend(["", "Human review remains required before any external use.", ""])
    return "\n".join(lines)


def _render_report(document: Mapping[str, Any]) -> str:
    lines = [
        f"# Technical report: {document['title']}", "",
        "> **VERIFIED LOCAL DRAFT · publication authority not granted**", "",
        document["summary"], "", "## Evidence flow", "", "```mermaid",
        "flowchart LR", '    A["Approved source"] --> B["Exact evidence match"]',
        '    B --> C["Evidence-linked claim"]', '    C --> D["Draft artefacts"]',
        '    D --> E["Human release gate"]', "```", "",
    ]
    for section in document["resolved_report_sections"]:
        lines.extend([f"## {section['heading']}", ""])
        lines.extend(_claim_line(item) for item in section["claims"])
        lines.append("")
    lines.extend(["## Claim audit", "", "| Claim | Kind | Evidence |", "|---|---|---|"])
    for claim in document["claims"]:
        resolved = document["claims_by_id"][claim["id"]]
        lines.append(f"| {claim['id']} | {claim['kind']} | {_source_note(resolved)} |")
    lines.append("")
    return "\n".join(lines)


def _render_presentation(document: Mapping[str, Any]) -> str:
    lines = [
        f"# Presentation outline: {document['title']}", "",
        "> **DRAFT · content outline only · no publication authority**", "",
    ]
    for number, slide in enumerate(document["resolved_slides"], 1):
        lines.extend([f"## Slide {number} — {slide['title']}", ""])
        lines.extend(_claim_line(item) for item in slide["claims"])
        lines.extend(["", "**Speaker-source notes:**"])
        for claim in slide["claims"]:
            lines.append(f"- {claim['id']}: {_source_note(claim)}")
        lines.append("")
    return "\n".join(lines)


def _valid_receipt_artifacts(root: Path, artifacts: Any) -> bool:
    if not isinstance(artifacts, list) or not artifacts:
        return False
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            return False
        candidate = (root / item["path"]).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return False
        if not candidate.is_file() or sha256_file(candidate) != item.get("sha256"):
            return False
    return True


def compile_proof(
    *, root: Path, manifest: Path, output: Path, store: TwinStore
) -> dict[str, Any]:
    """Compile and receipt a verified local draft; identical replays do not rewrite files."""
    root = root.resolve()
    try:
        manifest_value = manifest.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise ProofValidationError("manifest must stay inside the giga-user root") from exc
    manifest_path, manifest_relative = _relative_file(root, manifest_value, "manifest")
    output_path, output_relative = _output_directory(root, output)
    document, source_refs = _validate_manifest(root, manifest_path)
    manifest_digest = sha256_file(manifest_path)
    compiler_path = Path(__file__).resolve()
    compiler_digest = sha256_file(compiler_path)
    try:
        compiler_relative: str | None = compiler_path.relative_to(root).as_posix()
    except ValueError:
        compiler_relative = None
    compiler_ref = {
        "path": compiler_relative or "runtime:twin_core/external_proof.py",
        "sha256": compiler_digest,
        "version": COMPILER_VERSION,
    }
    run_material = {
        "compiler": compiler_ref,
        "manifest_sha256": manifest_digest,
        "sources": source_refs,
        "output": output_relative,
    }
    run_key = _digest_text(_canonical(run_material))
    event_id, _ = store.record_event(
        idempotency_key=f"external-proof:{run_key}",
        kind="external_proof.compile",
        observed_at=utc_now(),
        source=manifest_relative,
        actor="operator",
        trust_class="operator_confirmed",
        sensitivity="internal",
        payload={**run_material, "mode": "draft", "authority_level": "A1"},
        content_ref=manifest_relative,
    )
    previous = store.latest_receipt(event_id, "external_proof.compile")
    if previous and _valid_receipt_artifacts(root, previous["artifacts"]):
        return {
            "status": "committed",
            "replay": True,
            "event_id": event_id,
            "receipt_id": previous["id"],
            "output": output_relative,
            "artifacts": previous["artifacts"],
        }

    attempt_id, _ = store.start_attempt(event_id, "external-proof-compiler")
    state = "claimed"
    try:
        store.transition_attempt(attempt_id, "staged")
        state = "staged"
        output_path.mkdir(parents=True, exist_ok=True)
        rendered = {
            "case-study.md": _render_case_study(document),
            "technical-report.md": _render_report(document),
            "presentation-outline.md": _render_presentation(document),
        }
        qa = {
            "schema_version": "1.0",
            "status": "passed",
            "mode": "draft",
            "authority_level": "A1",
            "claims": len(document["claims"]),
            "sources": len(source_refs),
            "gates": {
                "manifest_schema": "passed",
                "draft_authority": "passed",
                "source_boundaries": "passed",
                "exact_evidence_matches": "passed",
                "claim_references": "passed",
                "public_text_scan": "passed",
            },
        }
        rendered["qa.json"] = _json_text(qa)
        for name, content in rendered.items():
            _check_public_text(f"rendered {name}", content)
            _write_atomic(output_path / name, content)
        primary_artifacts = [
            {"path": f"{output_relative}/{name}", "sha256": sha256_file(output_path / name)}
            for name in sorted(rendered)
        ]
        build_manifest = {
            "schema_version": "1.0",
            "compiler": compiler_ref,
            "mode": "draft",
            "authority_level": "A1",
            "run_key": run_key,
            "manifest": {"path": manifest_relative, "sha256": manifest_digest},
            "sources": source_refs,
            "artifacts": primary_artifacts,
        }
        _write_atomic(output_path / "build-manifest.json", _json_text(build_manifest))
        trust_receipt = {
            "schema_version": "1.0",
            "status": "verified_local_draft",
            "event_id": event_id,
            "run_key": run_key,
            "authority_level": "A1",
            "external_action_authorised": False,
            "build_manifest_sha256": sha256_file(output_path / "build-manifest.json"),
        }
        _write_atomic(output_path / "trust-receipt.json", _json_text(trust_receipt))
        artifacts = [
            {"path": f"{output_relative}/{name}", "sha256": sha256_file(output_path / name)}
            for name in sorted(OUTPUT_NAMES)
        ]
        if not _valid_receipt_artifacts(root, artifacts):
            raise ProofValidationError("written artefacts failed independent hash verification")
        store.transition_attempt(attempt_id, "validated")
        state = "validated"
        all_sources = [{"path": manifest_relative, "sha256": manifest_digest}, *source_refs]
        if compiler_relative is not None:
            all_sources.append({"path": compiler_relative, "sha256": compiler_digest})
        command = (
            f"python3 -m twin_core --root {root} compile-proof {manifest_relative} "
            f"--output {output_relative}"
        )
        for artifact in artifacts:
            store.register_artifact(
                path=artifact["path"], artifact_sha256=artifact["sha256"],
                source_refs=all_sources, build_command=command,
            )
        receipt_id = store.record_receipt(
            event_id=event_id,
            operation="external_proof.compile",
            status="committed",
            artifacts=artifacts,
            details={"run_key": run_key, "mode": "draft", "authority_level": "A1"},
        )
        store.transition_attempt(attempt_id, "committed")
        return {
            "status": "committed",
            "replay": False,
            "event_id": event_id,
            "receipt_id": receipt_id,
            "output": output_relative,
            "artifacts": artifacts,
        }
    except Exception:
        if state in {"claimed", "staged", "validated"}:
            try:
                store.transition_attempt(attempt_id, "retry")
            except (KeyError, ValueError):
                pass
        raise
