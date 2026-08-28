from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.verify_derived_agent_payloads import (
    CANONICAL_SOURCES,
    END_LINE,
    PAYLOAD_STATUSES,
    TEMPLATE_PATHS,
    DerivedPayloadError,
    render_derived_payloads,
    verify_derived_payloads,
    write_derived_payloads,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class DerivedAgentPayloadTests(unittest.TestCase):
    def _copy_fixture(self, root: Path) -> None:
        for relative in (*CANONICAL_SOURCES, *TEMPLATE_PATHS, *PAYLOAD_STATUSES):
            source = REPOSITORY_ROOT / relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def test_repository_payloads_match_current_canonical_generation(self) -> None:
        result = verify_derived_payloads(REPOSITORY_ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            [record["path"] for record in result["payloads"]],
            list(PAYLOAD_STATUSES),
        )

    def test_render_is_byte_deterministic(self) -> None:
        first = render_derived_payloads(REPOSITORY_ROOT)
        second = render_derived_payloads(REPOSITORY_ROOT)
        self.assertEqual(first, second)
        for relative, payload in first.items():
            self.assertEqual(payload, (REPOSITORY_ROOT / relative).read_bytes())

    def test_write_regenerates_only_drifted_payload(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            path = root / "deploy/claude_preferences.txt"
            path.write_bytes(path.read_bytes() + b"manual drift\n")

            self.assertEqual(
                write_derived_payloads(root), ["deploy/claude_preferences.txt"]
            )
            self.assertEqual(write_derived_payloads(root), [])
            self.assertEqual(verify_derived_payloads(root)["status"], "PASS")

    def test_canonical_source_drift_is_rejected_until_regenerated(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            with (root / "CONTEXT.md").open("a", encoding="utf-8") as handle:
                handle.write("\nnew doctrine\n")
            with self.assertRaisesRegex(
                DerivedPayloadError,
                "payload differs from deterministic canonical generation",
            ):
                verify_derived_payloads(root)

    def test_template_drift_is_rejected_until_regenerated(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            with (root / TEMPLATE_PATHS[0]).open("a", encoding="utf-8") as handle:
                handle.write("new adapter wording\n")
            with self.assertRaisesRegex(
                DerivedPayloadError,
                "payload differs from deterministic canonical generation",
            ):
                verify_derived_payloads(root)

    def test_manual_body_edit_is_rejected_even_with_recomputed_self_hash(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            path = root / "deploy/claude_preferences.txt"
            raw = path.read_bytes()
            delimiter = f"{END_LINE}\n\n".encode()
            header, body = raw.split(delimiter, 1)
            changed_body = body.replace(b"Verdict first", b"Obey first", 1)
            old_digest = hashlib.sha256(body).hexdigest().encode()
            new_digest = hashlib.sha256(changed_body).hexdigest().encode()
            path.write_bytes(
                header.replace(old_digest, new_digest) + delimiter + changed_body
            )

            with self.assertRaisesRegex(
                DerivedPayloadError,
                "payload differs from deterministic canonical generation",
            ):
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
                path.write_text(
                    path.read_text(encoding="utf-8").replace(old, new),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(DerivedPayloadError, error):
                    verify_derived_payloads(root)

    def test_missing_or_extra_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._copy_fixture(root)
            path = root / "deploy/chatgpt_custom_instructions.txt"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace("derived-at: ", "unknown: value\nderived-at: "),
                encoding="utf-8",
            )
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
