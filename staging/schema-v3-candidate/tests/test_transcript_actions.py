import json
from pathlib import Path

import pytest

from twin_core.transcript_actions import approve, compile_transcript, derive_candidates


def test_compiles_evidence_bound_review_packet(tmp_path: Path) -> None:
    source = tmp_path / "input" / "lesson.txt"
    source.parent.mkdir()
    source.write_text(
        "Tutor: You need to practise past tense.\n"
        "Artiom: I don't understand conditionals.\n"
        "Tutor: What will you review tomorrow?\n"
        "Artiom: I will complete exercise five.\n"
    )
    output = tmp_path / "output"
    packet = compile_transcript(source, output)
    assert packet["authority"] == "draft-candidates-only"
    assert packet["human_approval_required"] is True
    assert {item["kind"] for item in packet["candidates"]} >= {
        "action", "learning_gap", "open_question", "decision"
    }
    assert all(item["line_number"] > 0 and len(item["evidence_sha256"]) == 64 for item in packet["candidates"])
    manifest = json.loads((output / "manifest.json").read_text())
    assert set(manifest["outputs"]) == {"review-packet.json", "review.md"}


def test_approval_is_explicit_and_rejects_unknown_ids(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("Me: I need to send the follow-up.\n")
    packet = compile_transcript(source, tmp_path / "out")
    packet_path = tmp_path / "out" / "review-packet.json"
    candidate_id = packet["candidates"][0]["candidate_id"]
    receipt = approve(packet_path, [candidate_id], "operator", tmp_path / "approved.json")
    assert receipt["approved_by"] == "operator"
    assert receipt["approved"][0]["status"] == "needs_review"
    with pytest.raises(ValueError, match="unknown candidate"):
        approve(packet_path, ["made-up"], "operator", tmp_path / "bad.json")


def test_fail_closed_boundaries(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    with pytest.raises(ValueError, match="regular file"):
        compile_transcript(missing, tmp_path / "out")
    source = tmp_path / "source" / "meeting.txt"
    source.parent.mkdir()
    source.write_text("No commitments here.\n")
    with pytest.raises(ValueError, match="cannot be"):
        compile_transcript(source, source)
    assert derive_candidates("ordinary statement") == []
