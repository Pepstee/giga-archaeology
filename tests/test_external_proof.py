from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from twin_core.external_proof import ProofValidationError, compile_proof
from twin_core.store import TwinStore


class ExternalProofTests(unittest.TestCase):
    def make_fixture(self, base: Path) -> tuple[Path, Path, Path, TwinStore, dict]:
        root = base / "giga"
        source = root / "architecture" / "proof.md"
        source.parent.mkdir(parents=True)
        source.write_text("# Proof\nThe event replay is idempotent.\n", encoding="utf-8")
        manifest = {
            "schema_version": "1.0",
            "slug": "proof-test",
            "title": "Evidence-backed test",
            "summary": "A deterministic local draft from verified evidence.",
            "mode": "draft",
            "authority_level": "A1",
            "claims": [{
                "id": "C1",
                "kind": "fact",
                "statement": "The test source states that event replay is idempotent.",
                "evidence": [{
                    "path": "architecture/proof.md",
                    "needles": ["The event replay is idempotent."],
                }],
            }],
            "case_study": {
                "problem_claim_ids": ["C1"],
                "intervention_claim_ids": ["C1"],
                "limitation_claim_ids": ["C1"],
            },
            "report_sections": [{"heading": "Result", "claim_ids": ["C1"]}],
            "slides": [{"title": "Result", "claim_ids": ["C1"]}],
        }
        manifest_path = root / "external_proof" / "manifests" / "test.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        output = root / "outputs" / "external-proof" / "proof-test"
        store = TwinStore(root / "private" / "twin.sqlite3")
        return root, manifest_path, output, store, manifest

    def compile(self, root: Path, manifest: Path, output: Path, store: TwinStore):
        return compile_proof(root=root, manifest=manifest, output=output, store=store)

    def test_compile_registers_six_artifacts_and_replay_does_not_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, output, store, _ = self.make_fixture(Path(folder))
            first = self.compile(root, manifest, output, store)
            self.assertFalse(first["replay"])
            self.assertEqual({path.name for path in output.iterdir()}, {
                "case-study.md", "technical-report.md", "presentation-outline.md",
                "qa.json", "build-manifest.json", "trust-receipt.json",
            })
            self.assertIn("Claim C1", (output / "case-study.md").read_text(encoding="utf-8"))
            before = {item.name: item.stat().st_mtime_ns for item in output.iterdir()}
            second = self.compile(root, manifest, output, store)
            after = {item.name: item.stat().st_mtime_ns for item in output.iterdir()}
            self.assertTrue(second["replay"])
            self.assertEqual(first["event_id"], second["event_id"])
            self.assertEqual(before, after)
            counts = store.counts()
            self.assertEqual(counts["events"], 1)
            self.assertEqual(counts["receipts"], 1)
            self.assertEqual(counts["derived_artifacts"], 6)
            self.assertTrue(store.audit_artifacts(root)["ok"])

    def test_deck_sidecars_survive_replay_and_unknown_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, output, store, _ = self.make_fixture(Path(folder))
            self.compile(root, manifest, output, store)
            names = ["deck-qa.json", "proof-test.pptx", "proof-test-montage.png",
                     "proof-test.pptx.inspect.ndjson", "proof-test.pptx.receipt.json",
                     "proof-test/slide-1.png"]
            for name in names:
                p = output / name
                p.parent.mkdir(exist_ok=True)
                p.write_bytes(b"synthetic sidecar")
            self.assertTrue(self.compile(root, manifest, output, store)["replay"])
            for name in names:
                self.assertEqual((output / name).read_bytes(), b"synthetic sidecar")
            (output / "unexpected.txt").write_text("preserve")
            with self.assertRaises(ProofValidationError):
                self.compile(root, manifest, output, store)
            self.assertEqual((output / "unexpected.txt").read_text(), "preserve")

    def test_source_mutation_invalidates_lineage_and_creates_new_run(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, output, store, _ = self.make_fixture(Path(folder))
            first = self.compile(root, manifest, output, store)
            source = root / "architecture" / "proof.md"
            source.write_text(source.read_text(encoding="utf-8") + "More proof.\n", encoding="utf-8")
            self.assertFalse(store.audit_artifacts(root)["ok"])
            second = self.compile(root, manifest, output, store)
            self.assertNotEqual(first["event_id"], second["event_id"])
            self.assertEqual(store.counts()["events"], 2)
            self.assertTrue(store.audit_artifacts(root)["ok"])

    def test_publish_mode_and_higher_authority_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, output, store, document = self.make_fixture(Path(folder))
            for field, value in (("mode", "publish"), ("authority_level", "A2")):
                changed = copy.deepcopy(document)
                changed[field] = value
                manifest.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaisesRegex(ProofValidationError, "draft mode at A1"):
                    self.compile(root, manifest, output, store)

    def test_private_source_and_path_escape_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, output, store, document = self.make_fixture(Path(folder))
            private = root / "memory" / "secret.md"
            private.parent.mkdir()
            private.write_text("Private proof.", encoding="utf-8")
            document["claims"][0]["evidence"] = [{
                "path": "memory/secret.md", "needles": ["Private proof."]
            }]
            manifest.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ProofValidationError, "prohibited source"):
                self.compile(root, manifest, output, store)

            outside = root.parent / "outside.md"
            outside.write_text("Outside proof.", encoding="utf-8")
            document["claims"][0]["evidence"] = [{
                "path": "../outside.md", "needles": ["Outside proof."]
            }]
            manifest.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ProofValidationError, "escapes"):
                self.compile(root, manifest, output, store)

    def test_secret_text_missing_evidence_and_unknown_claim_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, output, store, document = self.make_fixture(Path(folder))
            secret = copy.deepcopy(document)
            secret["claims"][0]["statement"] = "Contact owner@example.com for details."
            manifest.write_text(json.dumps(secret), encoding="utf-8")
            with self.assertRaisesRegex(ProofValidationError, "email address"):
                self.compile(root, manifest, output, store)

            missing = copy.deepcopy(document)
            missing["claims"][0]["evidence"][0]["needles"] = ["Not in source"]
            manifest.write_text(json.dumps(missing), encoding="utf-8")
            with self.assertRaisesRegex(ProofValidationError, "needle not found"):
                self.compile(root, manifest, output, store)

            unknown = copy.deepcopy(document)
            unknown["slides"][0]["claim_ids"] = ["C404"]
            manifest.write_text(json.dumps(unknown), encoding="utf-8")
            with self.assertRaisesRegex(ProofValidationError, "unknown claim"):
                self.compile(root, manifest, output, store)

    def test_unexpected_output_file_is_not_overwritten_or_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, output, store, _ = self.make_fixture(Path(folder))
            output.mkdir(parents=True)
            sentinel = output / "operator-note.md"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ProofValidationError, "unexpected files"):
                self.compile(root, manifest, output, store)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_cli_compiles_the_same_contract(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, manifest, output, store, _ = self.make_fixture(Path(folder))
            result = subprocess.run(
                [
                    sys.executable, "-m", "twin_core",
                    "--root", str(root),
                    "--database", str(store.database),
                    "compile-proof", str(manifest.relative_to(root)),
                    "--output", str(output.relative_to(root)),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "committed")
            self.assertTrue((output / "case-study.md").is_file())


if __name__ == "__main__":
    unittest.main()
