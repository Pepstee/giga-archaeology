import hashlib
import json
from pathlib import Path

import pytest

from twin_core.sop_compiler import compile_sop, release_sop


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "evidence"
    root.mkdir(parents=True)
    for run in ("run-a", "run-b"):
        (root / f"{run}.txt").write_text("Open source\nVerify result\n", encoding="utf-8")
    observations = []
    for run in ("run-a", "run-b"):
        path = root / f"{run}.txt"
        for sequence, (key, instruction) in enumerate(
            (("open", "Open the authoritative source"), ("verify", "Verify the result")), 1
        ):
            observations.append({
                "run_id": run, "step_key": key, "sequence": sequence,
                "instruction": instruction, "outcome": "success", "approved_by": "operator",
                "evidence": {"path": path.name, "sha256": _sha(path),
                             "line_start": sequence, "line_end": sequence},
            })
    spec = tmp_path / "observations.json"
    spec.write_text(json.dumps({
        "schema": "giga-sop-observations/v1", "workflow_id": "source-check",
        "title": "Source check", "scope": "Verify one factual result",
        "observations": observations,
    }), encoding="utf-8")
    return spec, root


def test_compiles_only_repeated_successful_evidence(tmp_path: Path) -> None:
    spec, root = _fixture(tmp_path)
    output = tmp_path / "output"
    packet = compile_sop(spec, root, output)
    assert packet["authority"] == "draft-only"
    assert [step["sequence"] for step in packet["steps"]] == [1, 2]
    assert all(len(step["successful_runs"]) == 2 for step in packet["steps"])
    assert set(json.loads((output / "manifest.json").read_text())["outputs"]) == {
        "sop.json", "sop.md"
    }


def test_rejects_single_run_tamper_and_escape(tmp_path: Path) -> None:
    spec, root = _fixture(tmp_path)
    data = json.loads(spec.read_text())
    data["observations"] = [item for item in data["observations"] if item["run_id"] == "run-a"]
    spec.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="two independent"):
        compile_sop(spec, root, tmp_path / "one")

    spec, root = _fixture(tmp_path / "fresh")
    (root / "run-a.txt").write_text("tampered\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        compile_sop(spec, root, tmp_path / "tampered")

    data = json.loads(spec.read_text())
    data["observations"][0]["evidence"]["path"] = "../observations.json"
    spec.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="escapes"):
        compile_sop(spec, root, tmp_path / "escape")


def test_release_is_separate_and_detects_changed_output(tmp_path: Path) -> None:
    spec, root = _fixture(tmp_path)
    output = tmp_path / "output"
    compile_sop(spec, root, output)
    receipt = release_sop(output, "Artiom", tmp_path / "release.json")
    assert receipt["approved_by"] == "Artiom"
    (output / "sop.md").write_text("changed")
    with pytest.raises(ValueError, match="output changed"):
        release_sop(output, "Artiom", tmp_path / "bad.json")
