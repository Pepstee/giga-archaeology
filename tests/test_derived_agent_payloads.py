from __future__ import annotations

import shutil
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
        for relative in (*CANONICAL_SOURCES, *PAYLOAD_STATUSES):
            source = REPOSITORY_ROOT / relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def test_repository_payloads_match_current_canonical_sources(self) -> None:
        result = verify_derived_payloads(REPOSITORY_ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            [record["path"] for record in result["payloads"]],
            list(PAYLOAD_STATUSES),
        )

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
