"""Compile repeated, approved workflow evidence into a draft operating procedure."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OBSERVATION_SCHEMA = "giga-sop-observations/v1"
SOP_SCHEMA = "giga-sop/v1"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(root: Path, relative: str) -> Path:
    candidate = root / relative
    if candidate.is_symlink():
        raise ValueError("evidence path must not be a symlink")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("evidence path escapes evidence root") from exc
    if not resolved.is_file():
        raise ValueError("evidence path must be a regular file")
    return resolved


def _evidence_record(root: Path, item: dict[str, Any]) -> dict[str, Any]:
    evidence = item.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("every observation requires evidence")
    relative = evidence.get("path")
    if not isinstance(relative, str) or not relative:
        raise ValueError("evidence path is required")
    path = _inside(root, relative)
    raw = path.read_bytes()
    expected = evidence.get("sha256")
    if expected != _sha(raw):
        raise ValueError(f"evidence hash mismatch: {relative}")
    lines = raw.decode("utf-8").splitlines()
    start, end = evidence.get("line_start"), evidence.get("line_end")
    if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
        raise ValueError("invalid evidence line range")
    if end > len(lines):
        raise ValueError("evidence line range exceeds source")
    excerpt = "\n".join(lines[start - 1 : end])
    return {
        "path": relative,
        "sha256": expected,
        "line_start": start,
        "line_end": end,
        "excerpt_sha256": _sha(excerpt.encode("utf-8")),
    }


def compile_sop(spec_path: Path, evidence_root: Path, output_dir: Path) -> dict[str, Any]:
    """Compile only steps repeated across two or more approved successful runs."""
    spec_path = spec_path.resolve()
    evidence_root = evidence_root.resolve()
    output_dir = output_dir.resolve()
    if not spec_path.is_file() or spec_path.is_symlink():
        raise ValueError("observation spec must be a regular file")
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes)
    if spec.get("schema") != OBSERVATION_SCHEMA:
        raise ValueError("unsupported observation schema")
    observations = spec.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("observations are required")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in observations:
        if not isinstance(item, dict):
            raise ValueError("observation must be an object")
        required = ("run_id", "step_key", "instruction", "approved_by")
        if any(not isinstance(item.get(key), str) or not item[key].strip() for key in required):
            raise ValueError("observation identity, instruction and approval are required")
        if item.get("outcome") != "success":
            raise ValueError("only successful observations may enter an SOP")
        if not isinstance(item.get("sequence"), int) or item["sequence"] < 1:
            raise ValueError("positive integer sequence is required")
        enriched = dict(item)
        enriched["evidence"] = _evidence_record(evidence_root, item)
        grouped[item["step_key"]].append(enriched)

    steps = []
    for step_key, records in grouped.items():
        run_ids = sorted({record["run_id"] for record in records})
        if len(run_ids) < 2:
            raise ValueError(f"step {step_key!r} lacks two independent successful runs")
        instructions = {record["instruction"].strip() for record in records}
        sequences = {record["sequence"] for record in records}
        if len(instructions) != 1 or len(sequences) != 1:
            raise ValueError(f"step {step_key!r} is inconsistent across runs")
        steps.append({
            "step_key": step_key,
            "sequence": sequences.pop(),
            "instruction": instructions.pop(),
            "successful_runs": run_ids,
            "approvers": sorted({record["approved_by"].strip() for record in records}),
            "evidence": [record["evidence"] for record in records],
        })
    steps.sort(key=lambda step: (step["sequence"], step["step_key"]))
    if [step["sequence"] for step in steps] != list(range(1, len(steps) + 1)):
        raise ValueError("SOP step sequence must be contiguous and unique")

    packet = {
        "schema": SOP_SCHEMA,
        "authority": "draft-only",
        "human_release_required": True,
        "workflow_id": spec.get("workflow_id"),
        "title": spec.get("title"),
        "scope": spec.get("scope"),
        "source_spec_sha256": _sha(spec_bytes),
        "steps": steps,
    }
    if any(not isinstance(packet[key], str) or not packet[key].strip()
           for key in ("workflow_id", "title", "scope")):
        raise ValueError("workflow_id, title and scope are required")

    output_dir.mkdir(parents=True, exist_ok=True)
    packet_bytes = (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode("utf-8")
    packet_path = output_dir / "sop.json"
    packet_path.write_bytes(packet_bytes)
    markdown = [f"# {packet['title']}", "", f"Scope: {packet['scope']}", "",
                "> Draft only. Operator release is required.", ""]
    for step in steps:
        markdown += [f"## {step['sequence']}. {step['instruction']}", "",
                     f"Verified successful runs: {', '.join(step['successful_runs'])}", ""]
    markdown_path = output_dir / "sop.md"
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")
    manifest = {
        "schema": "giga-sop-build-manifest/v1",
        "outputs": {
            "sop.json": _sha(packet_bytes),
            "sop.md": _sha(markdown_path.read_bytes()),
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return packet


def release_sop(output_dir: Path, approved_by: str, receipt_path: Path) -> dict[str, Any]:
    """Issue a named release receipt without mutating the compiled SOP."""
    if not approved_by.strip():
        raise ValueError("approved_by is required")
    output_dir = output_dir.resolve()
    manifest_bytes = (output_dir / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    for name, digest in manifest.get("outputs", {}).items():
        if _sha((output_dir / name).read_bytes()) != digest:
            raise ValueError(f"compiled SOP output changed: {name}")
    packet = json.loads((output_dir / "sop.json").read_bytes())
    if packet.get("schema") != SOP_SCHEMA or packet.get("authority") != "draft-only":
        raise ValueError("unsupported SOP packet")
    receipt = {
        "schema": "giga-sop-release/v1",
        "approved_by": approved_by.strip(),
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": _sha(manifest_bytes),
        "workflow_id": packet["workflow_id"],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt
