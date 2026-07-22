"""Local, evidence-bound transcript-to-actions compiler.

The compiler produces review candidates, never autonomous facts. Every candidate carries
an exact source line and hash; approval is a separate explicit operator action.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = "giga-transcript-actions/v1"
PATTERNS = {
    "action": re.compile(r"\b(?:need to|needs to|must|should|will|todo|action item)\b", re.I),
    "decision": re.compile(r"\b(?:decided|agreed|decision|we will|i will)\b", re.I),
    "learning_gap": re.compile(
        r"\b(?:do not understand|don't understand|did not know|didn't know|need to learn|weak at)\b",
        re.I,
    ),
}
SPEAKER = re.compile(r"^\s*(?:\[([^\]]+)\]|([^:]{1,60}):)\s*(.*)$")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    kind: str
    text: str
    speaker: str | None
    line_number: int
    evidence_sha256: str
    status: str = "needs_review"


def _candidate(kind: str, text: str, speaker: str | None, line_number: int) -> Candidate:
    evidence = f"{line_number}\0{speaker or ''}\0{text}".encode("utf-8")
    digest = _sha(evidence)
    return Candidate(f"{kind}-{digest[:12]}", kind, text, speaker, line_number, digest)


def parse_lines(text: str) -> list[tuple[int, str | None, str]]:
    rows = []
    for number, raw in enumerate(text.splitlines(), 1):
        clean = raw.strip()
        if not clean:
            continue
        match = SPEAKER.match(clean)
        if match:
            speaker = (match.group(1) or match.group(2)).strip()
            body = match.group(3).strip()
        else:
            speaker, body = None, clean
        if body:
            rows.append((number, speaker, body))
    return rows


def derive_candidates(text: str) -> list[Candidate]:
    found: dict[str, Candidate] = {}
    for line_number, speaker, body in parse_lines(text):
        kinds = [kind for kind, pattern in PATTERNS.items() if pattern.search(body)]
        if body.endswith("?"):
            kinds.append("open_question")
        for kind in kinds:
            item = _candidate(kind, body, speaker, line_number)
            found[item.candidate_id] = item
    return sorted(found.values(), key=lambda item: (item.line_number, item.kind))


def compile_transcript(source: Path, output_dir: Path) -> dict:
    source = source.resolve()
    output_dir = output_dir.resolve()
    if not source.is_file():
        raise ValueError("transcript source must be a regular file")
    if output_dir == source:
        raise ValueError("output directory cannot be the transcript source")
    raw = source.read_bytes()
    text = raw.decode("utf-8")
    candidates = derive_candidates(text)
    packet = {
        "schema": SCHEMA,
        "authority": "draft-candidates-only",
        "human_approval_required": True,
        "source": {"name": source.name, "sha256": _sha(raw), "bytes": len(raw)},
        "candidate_count": len(candidates),
        "candidates": [asdict(item) for item in candidates],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    packet_bytes = (json.dumps(packet, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
    packet_path = output_dir / "review-packet.json"
    packet_path.write_bytes(packet_bytes)
    lines = ["# Transcript review", "", "All items are unapproved candidates.", ""]
    for item in candidates:
        lines += [f"- [ ] `{item.candidate_id}` **{item.kind}** (line {item.line_number}): {item.text}"]
    review_path = output_dir / "review.md"
    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "schema": "giga-transcript-actions-manifest/v1",
        "source_sha256": packet["source"]["sha256"],
        "outputs": {packet_path.name: _sha(packet_bytes), review_path.name: _sha(review_path.read_bytes())},
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return packet


def approve(packet_path: Path, candidate_ids: list[str], approved_by: str, output: Path) -> dict:
    if not approved_by.strip():
        raise ValueError("approved_by is required")
    packet_bytes = packet_path.read_bytes()
    packet = json.loads(packet_bytes)
    if packet.get("schema") != SCHEMA or packet.get("authority") != "draft-candidates-only":
        raise ValueError("unsupported review packet")
    known = {item["candidate_id"]: item for item in packet["candidates"]}
    missing = sorted(set(candidate_ids) - set(known))
    if missing:
        raise ValueError(f"unknown candidate ids: {missing}")
    receipt = {
        "schema": "giga-transcript-approval/v1",
        "packet_sha256": _sha(packet_bytes),
        "approved_by": approved_by.strip(),
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approved": [known[item] for item in candidate_ids],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return receipt
