"""Independent assurance for the evidence-linked Deck Production capability."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "outputs/external-proof/virtual-twin-trust-kernel"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_deck_receipt_binds_manifest_renderer_and_editable_pptx() -> None:
    qa = json.loads((PACK / "deck-qa.json").read_text(encoding="utf-8"))
    assert qa["status"] == "passed"
    assert qa["authority_level"] == "A1"
    assert qa["publication_authority"] is False
    assert qa["manifest_sha256"] == sha256(
        ROOT / "external_proof/manifests/virtual-twin-trust-kernel.json"
    )
    assert qa["renderer_sha256"] == sha256(ROOT / "scripts/render_external_proof_deck.mjs")
    deck = PACK / "virtual-twin-trust-kernel.pptx"
    assert qa["pptx_sha256"] == sha256(deck)

    with zipfile.ZipFile(deck) as archive:
        names = set(archive.namelist())
        slides = sorted(
            name for name in names
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )
        notes = sorted(
            name for name in names
            if name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml")
        )
        assert len(slides) == qa["slides"] == 6
        assert len(notes) == qa["slides"]
        note_text = b"\n".join(archive.read(name) for name in notes)
        for claim_id in (b"C1", b"C2", b"C3", b"C4", b"L1"):
            assert claim_id in note_text
        assert b"Human review is required before external use" in note_text


def test_every_rendered_slide_is_bound_by_the_qa_record() -> None:
    qa = json.loads((PACK / "deck-qa.json").read_text(encoding="utf-8"))
    rendered = PACK / "virtual-twin-trust-kernel"
    observed = [sha256(path) for path in sorted(rendered.glob("slide-*.png"))]
    assert len(observed) == qa["slides"]
    assert observed == qa["rendered_slide_sha256"]
    assert all(value == "passed" for value in qa["gates"].values())
