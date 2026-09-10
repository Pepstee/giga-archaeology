from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.verify_derived_agent_payloads import (
    CANONICAL_SOURCES,
    PAYLOAD_STATUSES,
    DerivedPayloadError,
    verify_derived_payloads,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class DerivedAgentPayloadTests(unittest.TestCase):
    def _copy_fixture(self, root: Path) -> None:
        for relative in CANONICAL_SOURCES:
            (root / relative).write_text("*Version 1.0 — 2026-09-10.*\nSynthetic governance.\n")
        lines = [f"canonical-source: {name} sha256={hashlib.sha256((root / name).read_bytes()).hexdigest()}" for name in CANONICAL_SOURCES]
        for relative, status in PAYLOAD_STATUSES.items():
            body = b"Synthetic derived instructions.\n"
            header = ["=== GIGA DERIVED PAYLOAD v1 ===", *lines, "derived-at: 2026-09-10",
                      f"deployment-status: {status}",
                      "authority: DERIVED_ONLY; this payload cannot override either canonical source",
                      f"payload-body-sha256: {hashlib.sha256(body).hexdigest()}",
                      "=== END GIGA DERIVED PAYLOAD METADATA ==="]
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes("\n".join(header).encode() + b"\n\n" + body)

    def test_generated_payloads_match_canonical_sources(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            result = verify_derived_payloads(root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual([record["path"] for record in result["payloads"]], list(PAYLOAD_STATUSES))

    def test_canonical_source_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            with (root / "CONTEXT.md").open("a", encoding="utf-8") as handle:
                handle.write("\nnew doctrine\n")
            with self.assertRaisesRegex(DerivedPayloadError, "canonical source identity"):
                verify_derived_payloads(root)

    def test_payload_body_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            with (root / "deploy/claude_preferences.txt").open("a", encoding="utf-8") as handle:
                handle.write("\nunrecorded broadening\n")
            with self.assertRaisesRegex(DerivedPayloadError, "payload body differs"):
                verify_derived_payloads(root)

    def test_authority_or_status_drift_is_rejected(self) -> None:
        replacements = (
            ("DERIVED_ONLY", "AUTHORITATIVE", "derived-only authority"),
            ("UNVERIFIED_REPASTE", "DEPLOYED", "deployment status"),
        )
        for old, new, error in replacements:
            with self.subTest(field=old), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self._copy_fixture(root)
                path = root / "deploy/claude_preferences.txt"
                path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
                with self.assertRaisesRegex(DerivedPayloadError, error):
                    verify_derived_payloads(root)

    def test_missing_or_extra_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            path = root / "deploy/chatgpt_custom_instructions.txt"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("derived-at: ", "unknown: value\nderived-at: "), encoding="utf-8")
            with self.assertRaisesRegex(DerivedPayloadError, "field count"):
                verify_derived_payloads(root)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            (root / "deploy/v3_operator_model.md").unlink()
            with self.assertRaisesRegex(DerivedPayloadError, "missing required file"):
                verify_derived_payloads(root)


if __name__ == "__main__":
    unittest.main()


def _staged_fixture(root):
    from scripts.verify_derived_agent_payloads import PAYLOAD_SPECS
    DerivedAgentPayloadTests()._copy_fixture(root)
    for spec in PAYLOAD_SPECS.values():
        path = root / spec.template
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Synthetic {{CHARTER_VERSION}} {{CONTEXT_VERSION}} {{DERIVED_AT}}\n')


def test_staged_generation_is_deterministic_without_activation_reads(tmp_path):
    from unittest.mock import patch
    from scripts import verify_derived_agent_payloads as module
    _staged_fixture(tmp_path)
    with patch.object(module, '_verify_activation_evidence', side_effect=AssertionError('activation read')):
        assert len(module.write_derived_payloads(tmp_path)) == 3
        first = module.verify_derived_payloads(tmp_path, mode='staged-v2')
        assert module.write_derived_payloads(tmp_path) == []
        assert module.verify_derived_payloads(tmp_path, mode='staged-v2') == first
    assert first['verification_mode'] == 'staged-v2'
    assert all(p['deployment_status'] != 'DEPLOYED' for p in first['payloads'])


def test_staged_template_drift_and_unknown_placeholder_refuse(tmp_path):
    import pytest
    from scripts import verify_derived_agent_payloads as module
    _staged_fixture(tmp_path)
    module.write_derived_payloads(tmp_path)
    path = tmp_path / next(iter(module.PAYLOAD_SPECS.values())).template
    path.write_text('Changed template\n')
    with pytest.raises(module.DerivedPayloadError, match='deterministic canonical generation'):
        module.verify_derived_payloads(tmp_path, mode='staged-v2')
    path.write_text('{{UNKNOWN}}\n')
    with pytest.raises(module.DerivedPayloadError, match='unknown or incomplete'):
        module.write_derived_payloads(tmp_path)


def test_historical_mode_requires_evidence_and_never_writes(tmp_path):
    import pytest
    from scripts import verify_derived_agent_payloads as module
    _staged_fixture(tmp_path)
    module.write_derived_payloads(tmp_path)
    before = {p: (tmp_path / p).read_bytes() for p in module.PAYLOAD_STATUSES}
    with pytest.raises(module.DerivedPayloadError, match='missing required file'):
        module.verify_derived_payloads(tmp_path, mode='historical-activation')
    assert before == {p: (tmp_path / p).read_bytes() for p in module.PAYLOAD_STATUSES}


def test_historical_json_rejects_ambiguous_values():
    import pytest
    from scripts.verify_derived_agent_payloads import _strict_json
    for raw in (b'{"actor":"a","actor":"b"}', b'{"value":NaN}', b'[]'):
        with pytest.raises(DerivedPayloadError):
            _strict_json(raw)


def test_historical_source_pin_cannot_be_relabelled(tmp_path):
    import json
    import pytest
    from scripts import verify_derived_agent_payloads as module
    _staged_fixture(tmp_path)
    raw = {"schema": "giga.agent-payload-activation.v2", "actor": "Artiom Gutu",
           "recorded_at_utc": "2026-09-10T00:00:00Z", "source_commit": "0" * 40,
           "self_sha256": "0" * 64, "platforms": {}}
    (tmp_path / module.ACTIVATION_EVIDENCE_PATH).write_text(json.dumps(raw))
    with pytest.raises(DerivedPayloadError, match='source commit differs'):
        module.verify_derived_payloads(tmp_path, mode='historical-activation')


def test_staged_first_install_creates_outputs_without_activation(tmp_path):
    from scripts import verify_derived_agent_payloads as module
    _staged_fixture(tmp_path)
    for relative in module.PAYLOAD_STATUSES:
        (tmp_path / relative).unlink()
    assert len(module.write_derived_payloads(tmp_path)) == 3
    assert module.verify_derived_payloads(tmp_path, mode='staged-v2')['status'] == 'PASS'


def test_first_install_refuses_dangling_output_symlink(tmp_path):
    import pytest
    from scripts import verify_derived_agent_payloads as module
    _staged_fixture(tmp_path)
    path = tmp_path / next(iter(module.PAYLOAD_STATUSES))
    path.unlink()
    path.symlink_to(tmp_path / 'absent')
    with pytest.raises(module.DerivedPayloadError, match='regular non-symlink'):
        module.write_derived_payloads(tmp_path)
    assert not (tmp_path / 'absent').exists()
