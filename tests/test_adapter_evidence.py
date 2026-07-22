from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from twin_core.adapter_evidence import (
    ADAPTER_STATES,
    AUTHORITIES,
    REQUIRED_FIELDS,
    AdapterEvidenceError,
    canonical_json,
    compile_registry,
    render_summary,
    validate_registry,
)


FIXED_TIME = "2026-07-22T16:00:00+00:00"


def _manifest() -> dict:
    return {
        "schema_version": "giga.adapter-evidence.v1",
        "id": "test-adapter",
        "state": "native",
        "authority": "read-only",
        "supported_assets": ["asset.py"],
        "unsupported_surfaces": ["session mutation"],
        "onramp": "python3 asset.py",
        "verification_commands": ["python3 -m pytest"],
        "risk_notes": ["test-only adapter"],
        "owner": "giga-user",
        "source_docs": ["source.md"],
        "evidence_paths": ["proof.json"],
        "verified_at": FIXED_TIME,
    }


@pytest.fixture()
def root() -> Path:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary)
        (path / "adapters/manifests").mkdir(parents=True)
        (path / "asset.py").write_text("print('asset')\n", encoding="utf-8")
        (path / "source.md").write_text("source\n", encoding="utf-8")
        (path / "proof.json").write_text("{}\n", encoding="utf-8")
        (path / "adapters/manifests/test.json").write_text(json.dumps(_manifest()), encoding="utf-8")
        yield path


def test_compilation_is_byte_deterministic_and_hashes_evidence(root: Path) -> None:
    first = compile_registry(root, FIXED_TIME)
    second = compile_registry(root, FIXED_TIME)
    assert canonical_json(first) == canonical_json(second)
    adapter = first["adapters"][0]
    assert adapter["verification_state"] == "verified"
    assert adapter["effective_state"] == "native"
    assert len(adapter["supported_assets"][0]["sha256"]) == 64


def test_commands_are_data_and_never_executed(root: Path) -> None:
    marker = root / "must-not-exist"
    manifest = _manifest()
    manifest["verification_commands"] = [f"touch {marker}"]
    (root / "adapters/manifests/test.json").write_text(json.dumps(manifest), encoding="utf-8")
    payload = compile_registry(root, FIXED_TIME)
    assert payload["command_execution"] is False
    assert payload["authority_granted"] is False
    assert payload["adapters"][0]["verification_commands"] == [f"touch {marker}"]
    assert not marker.exists()


def test_stale_adapter_degrades_to_reference_only(root: Path) -> None:
    manifest = _manifest()
    manifest["verified_at"] = "2026-07-20T16:00:00+00:00"
    (root / "adapters/manifests/test.json").write_text(json.dumps(manifest), encoding="utf-8")
    payload = compile_registry(root, FIXED_TIME, stale_after_seconds=60)
    adapter = payload["adapters"][0]
    assert adapter["declared_state"] == "native"
    assert adapter["effective_state"] == "reference-only"
    assert adapter["verification_state"] == "stale"


def test_future_verification_fails_closed(root: Path) -> None:
    manifest = _manifest()
    manifest["verified_at"] = "2026-07-23T16:00:00+00:00"
    (root / "adapters/manifests/test.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AdapterEvidenceError, match="verified in the future"):
        compile_registry(root, FIXED_TIME)


@pytest.mark.parametrize("field", ["supported_assets", "source_docs", "evidence_paths"])
def test_missing_evidence_file_fails_closed(root: Path, field: str) -> None:
    manifest = _manifest()
    manifest[field] = ["missing.txt"]
    (root / "adapters/manifests/test.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AdapterEvidenceError, match="does not resolve to a regular file"):
        compile_registry(root, FIXED_TIME)


@pytest.mark.parametrize("escaped", ["../outside.txt", "/tmp/outside.txt"])
def test_path_escape_and_absolute_paths_fail_closed(root: Path, escaped: str) -> None:
    manifest = _manifest()
    manifest["evidence_paths"] = [escaped]
    (root / "adapters/manifests/test.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AdapterEvidenceError, match="escapes repository|absolute paths"):
        compile_registry(root, FIXED_TIME)


def test_symlink_escape_fails_closed(root: Path) -> None:
    outside = root.parent / "adapter-evidence-outside.txt"
    outside.write_text("outside", encoding="utf-8")
    try:
        (root / "escape.txt").symlink_to(outside)
        manifest = _manifest()
        manifest["evidence_paths"] = ["escape.txt"]
        (root / "adapters/manifests/test.json").write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(AdapterEvidenceError, match="escapes repository"):
            compile_registry(root, FIXED_TIME)
    finally:
        outside.unlink(missing_ok=True)


def test_manifest_symlink_is_forbidden(root: Path) -> None:
    target = root / "real-manifest.json"
    target.write_text(json.dumps(_manifest()), encoding="utf-8")
    (root / "adapters/manifests/test.json").unlink()
    (root / "adapters/manifests/test.json").symlink_to(target)
    with pytest.raises(AdapterEvidenceError, match="manifest symlinks are forbidden"):
        compile_registry(root, FIXED_TIME)


def test_malformed_extra_and_missing_fields_fail_closed(root: Path) -> None:
    manifest_path = root / "adapters/manifests/test.json"
    manifest_path.write_text("{", encoding="utf-8")
    with pytest.raises(AdapterEvidenceError, match="malformed adapter manifest"):
        compile_registry(root, FIXED_TIME)
    manifest = _manifest()
    manifest["invented"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AdapterEvidenceError, match="invalid manifest fields"):
        compile_registry(root, FIXED_TIME)
    manifest = _manifest()
    del manifest["owner"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AdapterEvidenceError, match="invalid manifest fields"):
        compile_registry(root, FIXED_TIME)


def test_duplicate_adapter_ids_fail_closed(root: Path) -> None:
    (root / "adapters/manifests/duplicate.json").write_text(json.dumps(_manifest()), encoding="utf-8")
    with pytest.raises(AdapterEvidenceError, match="duplicate adapter id"):
        compile_registry(root, FIXED_TIME)


def test_hash_changes_when_evidence_changes(root: Path) -> None:
    first = compile_registry(root, FIXED_TIME)["adapters"][0]["evidence"][0]["sha256"]
    (root / "proof.json").write_text('{"changed":true}\n', encoding="utf-8")
    second = compile_registry(root, FIXED_TIME)["adapters"][0]["evidence"][0]["sha256"]
    assert first != second


def test_summary_and_validator_detect_tampering(root: Path) -> None:
    payload = compile_registry(root, FIXED_TIME)
    summary = render_summary(payload)
    assert "Manifest commands executed: no" in summary
    assert "Authority granted: no" in summary
    assert "test-adapter: native / verified / read-only" in summary
    payload["command_execution"] = True
    with pytest.raises(AdapterEvidenceError, match="must never execute"):
        validate_registry(payload)
    payload = compile_registry(root, FIXED_TIME)
    payload["summary"]["total"] = 2
    with pytest.raises(AdapterEvidenceError, match="summary disagrees"):
        validate_registry(payload)

    payload = compile_registry(root, FIXED_TIME)
    payload["authority_granted"] = True
    with pytest.raises(AdapterEvidenceError, match="grants no authority"):
        validate_registry(payload)


def test_published_schema_matches_compiler_contract() -> None:
    project = Path(__file__).resolve().parents[1]
    schema = json.loads((project / "contracts/adapter-evidence.v1.schema.json").read_text(encoding="utf-8"))
    assert set(schema["required"]) == REQUIRED_FIELDS
    assert tuple(schema["properties"]["state"]["enum"]) == ADAPTER_STATES
    assert tuple(schema["properties"]["authority"]["enum"]) == AUTHORITIES
    registry_schema = json.loads((project / "contracts/adapter-registry.v1.schema.json").read_text(encoding="utf-8"))
    assert registry_schema["properties"]["schema_version"]["const"] == "giga.adapter-registry.v1"
    assert registry_schema["properties"]["authority_granted"]["const"] is False
    assert registry_schema["properties"]["command_execution"]["const"] is False
    assert tuple(registry_schema["$defs"]["state"]["enum"]) == ADAPTER_STATES
    assert tuple(registry_schema["$defs"]["authority"]["enum"]) == AUTHORITIES
