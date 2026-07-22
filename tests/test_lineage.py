from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from twin_core.integrity import sha256_file
from twin_core.lineage import LineageReconciliationError, reconcile_lineage
from twin_core.store import TwinStore


class LineageReconciliationTests(unittest.TestCase):
    def fixture(self, folder: str) -> tuple[Path, TwinStore, Path]:
        root = Path(folder)
        (root / "architecture").mkdir()
        artifact = root / "architecture" / "map.md"
        source = root / "source.md"
        artifact.write_text("# Map\n\nold\n", encoding="utf-8")
        source.write_text("old source\n", encoding="utf-8")
        store = TwinStore(root / "private" / "twin.sqlite3")
        store.register_artifact(
            path="architecture/map.md",
            artifact_sha256=sha256_file(artifact),
            source_refs=[{"path": "source.md", "sha256": sha256_file(source)}],
            build_command="legacy build",
            built_at="2026-07-20T00:00:00Z",
        )
        artifact.write_text("# Map\n\ncurrent\n", encoding="utf-8")
        source.write_text("current source\n", encoding="utf-8")
        manifest = root / "architecture" / "LINEAGE_RECONCILIATION_POLICY.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "authority": {
                        "actor": "operator",
                        "confirmed_at": "2026-07-22T10:00:00Z",
                        "basis": "Operator explicitly requested graceful reconciliation.",
                    },
                    "artifacts": [
                        {
                            "path": "architecture/map.md",
                            "sources": ["source.md"],
                            "required_headings": ["# Map"],
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return root, store, manifest

    @patch("twin_core.lineage.validate_memory", return_value={"ok": True, "errors": []})
    @patch("twin_core.lineage.verify_hash_baseline", return_value={"ok": True, "files": []})
    @patch(
        "twin_core.lineage._run_canonical_tests",
        return_value={
            "ok": True,
            "command": ["python3", "-W", "error", "-m", "pytest", "-q", "tests"],
            "returncode": 0,
            "output_sha256": "a" * 64,
            "summary": "50 passed",
        },
    )
    def test_adopts_current_state_and_retains_previous_revision(self, *_: object) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, store, manifest = self.fixture(folder)
            report = reconcile_lineage(
                root=root,
                manifest=manifest,
                store=store,
                report_json=root / "architecture" / "receipt.json",
                report_markdown=root / "architecture" / "receipt.md",
            )
            self.assertTrue(report["ok"])
            self.assertEqual(report["semantics"], "verified current-state adoption; not a rebuild")
            history = store.artifact_history("architecture/map.md")
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["provenance_mode"], "reconciled")
            self.assertEqual(history[1]["status"], "superseded")
            self.assertTrue(store.audit_artifacts(root)["ok"])
            self.assertTrue((root / "architecture" / "receipt.json").is_file())
            self.assertIn("not a claim", (root / "architecture" / "receipt.md").read_text())
            receipt_count = store.counts()["receipts"]
            receipt = store.latest_receipt(report["authority_event_id"], "lineage.reconcile")
            assert receipt is not None
            self.assertTrue(all("lineage-reconciliation/" in item["path"] for item in receipt["artifacts"]))
            (root / "architecture" / "receipt.json").write_text("{}", encoding="utf-8")
            (root / "architecture" / "receipt.md").write_text("changed", encoding="utf-8")
            replay = reconcile_lineage(
                root=root,
                manifest=manifest,
                store=store,
                report_json=root / "architecture" / "receipt.json",
                report_markdown=root / "architecture" / "receipt.md",
            )
            self.assertTrue(replay["replay"])
            self.assertEqual(len(store.artifact_history("architecture/map.md")), 2)
            self.assertEqual(store.counts()["receipts"], receipt_count)
            self.assertIn("not a claim", (root / "architecture" / "receipt.md").read_text())

    @patch("twin_core.lineage.validate_memory", return_value={"ok": True})
    @patch("twin_core.lineage.verify_hash_baseline", return_value={"ok": True})
    @patch(
        "twin_core.lineage._run_canonical_tests",
        return_value={"ok": False, "output_sha256": "a" * 64, "summary": "failed"},
    )
    def test_failed_gate_cannot_promote_a_revision(self, *_: object) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root, store, manifest = self.fixture(folder)
            with self.assertRaises(LineageReconciliationError):
                reconcile_lineage(
                    root=root,
                    manifest=manifest,
                    store=store,
                    report_json=root / "architecture" / "receipt.json",
                    report_markdown=root / "architecture" / "receipt.md",
                )
            self.assertEqual(len(store.artifact_history("architecture/map.md")), 1)


if __name__ == "__main__":
    unittest.main()
