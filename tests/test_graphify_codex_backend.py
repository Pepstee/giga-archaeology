from __future__ import annotations

import errno
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import graphify_codex_backend
from twin_core import provider_adapters


class CodexStructuredTests(unittest.TestCase):
    @patch("twin_core.provider_adapters.subprocess.run")
    def test_worker_is_ephemeral_read_only_and_schema_bound(self, run) -> None:
        def complete(command, **kwargs):
            output = Path(command[command.index("-o") + 1])
            output.write_text('{"status":"PASS"}', encoding="utf-8")
            stdout = (
                '{"type":"turn.completed","usage":{"input_tokens":12,'
                '"cached_input_tokens":3,"output_tokens":4}}\n'
            )
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        run.side_effect = complete
        result = provider_adapters.codex_structured(
            "bounded prompt",
            schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["status"],
                "properties": {"status": {"const": "PASS"}},
            },
            model="gpt-5.6-luna",
        )
        self.assertEqual(result, {"status": "PASS"})
        command = run.call_args.args[0]
        self.assertIn("--ephemeral", command)
        self.assertIn("read-only", command)
        self.assertIn("--output-schema", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--json", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        measured = provider_adapters.codex_structured_with_usage(
            "bounded prompt",
            schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["status"],
                "properties": {"status": {"type": "string", "const": "PASS"}},
            },
        )
        self.assertEqual(measured, ({"status": "PASS"}, {
            "cached_input_tokens": 3, "input_tokens": 12, "output_tokens": 4
        }))


    @patch("twin_core.provider_adapters.subprocess.run")
    def test_proposal_without_usage_retains_response_but_measured_call_refuses(self, run) -> None:
        def complete(command, **kwargs):
            output = Path(command[command.index("-o") + 1])
            output.write_text('{"status":"PASS"}', encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        run.side_effect = complete
        self.assertEqual(provider_adapters.codex_proposal("bounded prompt"), {"status": "PASS"})
        self.assertIsNone(provider_adapters.codex_structured_with_usage(
            "bounded prompt", schema={"type": "object"}
        ))


class ExclusivePublicationTests(unittest.TestCase):
    def test_platform_exclusive_rename_and_collision(self) -> None:
        for platform, symbol, flag in (("darwin", "renameatx_np", 4), ("linux", "renameat2", 1)):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as folder:
                parent = Path(folder)
                staged = parent / "staging" / "result"
                staged.mkdir(parents=True)
                destination = parent / "result"
                rename = Mock(return_value=0)
                libc = Mock(spec=[symbol])
                setattr(libc, symbol, rename)
                with patch.object(graphify_codex_backend.sys, "platform", platform), patch.object(
                    graphify_codex_backend.ctypes, "CDLL", return_value=libc
                ):
                    graphify_codex_backend._publish_no_replace(staged, destination)
                    self.assertEqual(rename.call_args.args[1], b"staging/result")
                    self.assertEqual(rename.call_args.args[3:], (b"result", flag))
                    rename.return_value = -1
                    with patch.object(graphify_codex_backend.ctypes, "get_errno", return_value=errno.EEXIST):
                        with self.assertRaises(graphify_codex_backend.GraphifyCodexRefusal):
                            graphify_codex_backend._publish_no_replace(staged, destination)

    def test_missing_exclusive_primitive_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            staged = parent / "staging" / "result"
            staged.mkdir(parents=True)
            with patch.object(graphify_codex_backend.sys, "platform", "linux"), patch.object(
                graphify_codex_backend.ctypes, "CDLL", return_value=Mock(spec=[])
            ):
                with self.assertRaises(graphify_codex_backend.GraphifyCodexRefusal):
                    graphify_codex_backend._publish_no_replace(staged, parent / "result")
            self.assertTrue(staged.is_dir())
            self.assertFalse((parent / "result").exists())


class SemanticValidationTests(unittest.TestCase):
    def valid_result(self) -> dict:
        return {
            "nodes": [
                {
                    "id": "evidence_checkpoint",
                    "label": "Checkpoint",
                    "file_type": "document",
                    "source_file": "checkpoint.md",
                    "source_location": "line 1",
                    "source_url": None,
                    "captured_at": None,
                    "author": None,
                    "contributor": None,
                },
                {
                    "id": "evidence_policy",
                    "label": "Policy",
                    "file_type": "concept",
                    "source_file": "checkpoint.md",
                    "source_location": "line 1",
                    "source_url": None,
                    "captured_at": None,
                    "author": None,
                    "contributor": None,
                },
            ],
            "edges": [
                {
                    "source": "evidence_checkpoint",
                    "target": "evidence_policy",
                    "relation": "references",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": "checkpoint.md",
                    "source_location": "line 1",
                    "weight": 1.0,
                }
            ],
            "hyperedges": [],
        }

    def test_accepts_closed_admitted_graph(self) -> None:
        value = graphify_codex_backend.validate_semantic_result(
            self.valid_result(),
            admitted_sources={"checkpoint.md"},
            line_counts={"checkpoint.md": 1},
        )
        self.assertEqual(value["nodes"][0]["id"], "evidence_checkpoint")

    def test_rejects_unadmitted_source_and_unknown_edge_node(self) -> None:
        value = self.valid_result()
        value["nodes"][0]["source_file"] = "private-vault.txt"
        with self.assertRaises(graphify_codex_backend.GraphifyCodexRefusal):
            graphify_codex_backend.validate_semantic_result(
                value,
                admitted_sources={"checkpoint.md"},
                line_counts={"checkpoint.md": 1},
            )
        value = self.valid_result()
        value["edges"][0]["target"] = "invented"
        with self.assertRaises(graphify_codex_backend.GraphifyCodexRefusal):
            graphify_codex_backend.validate_semantic_result(
                value,
                admitted_sources={"checkpoint.md"},
                line_counts={"checkpoint.md": 1},
            )

    def test_source_boundary_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.md"
            source.write_text("safe", encoding="utf-8")
            link = root / "link.md"
            link.symlink_to(source)
            with self.assertRaises(graphify_codex_backend.GraphifyCodexRefusal):
                graphify_codex_backend._source_paths([link], root)

    def test_code_symlink_refuses_without_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            source = parent / "source"
            source.mkdir()
            external = parent / "external"
            external.mkdir()
            (external / "module.py").write_text("def escaped():\n    return True\n", encoding="utf-8")
            (source / "linked").symlink_to(external, target_is_directory=True)
            output = parent / "result"
            with self.assertRaises(graphify_codex_backend.GraphifyCodexRefusal):
                graphify_codex_backend.build_graph(
                    source, output, model="gpt-5.6-luna", deep_mode=False
                )
            self.assertFalse(output.exists())

    def test_code_only_graph_manifest_binds_all_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            source = parent / "source"
            source.mkdir()
            (source / "module.py").write_text(
                "def working_increment():\n    return 'PASS'\n", encoding="utf-8"
            )
            output = parent / "result"
            with patch.object(
                graphify_codex_backend, "_command_version",
                side_effect=AssertionError("code-only extraction must not require Codex"),
            ):
                manifest = graphify_codex_backend.build_graph(
                    source, output, model="gpt-5.6-luna", deep_mode=False
                )
            graph_dir = output / "graphify-out"
            self.assertTrue((graph_dir / "graph.html").is_file())
            self.assertTrue((graph_dir / ".graphify_extract.json").is_file())
            self.assertIn("extraction_sha256", manifest["graph"])
            self.assertIn("script_sha256", manifest["implementation"])
            self.assertEqual(manifest["token_usage"]["input_tokens"], 0)
            self.assertEqual(manifest["backend"]["name"], "graphify-ast")
            self.assertIsNone(manifest["implementation"]["codex_cli_version"])
            extraction = json.loads(
                (graph_dir / ".graphify_extract.json").read_text(encoding="utf-8")
            )
            source_files = {
                item["source_file"]
                for collection in ("nodes", "edges")
                for item in extraction[collection]
                if item.get("source_file")
            }
            self.assertEqual(source_files, {"module.py"})

    def test_concurrent_destination_is_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            source = parent / "source"
            source.mkdir()
            (source / "module.py").write_text("def admitted():\n    return True\n", encoding="utf-8")
            output = parent / "result"
            publish = graphify_codex_backend._publish_no_replace

            def race(staged: Path, destination: Path) -> None:
                destination.mkdir()
                (destination / "owner.txt").write_text("existing", encoding="utf-8")
                publish(staged, destination)

            with patch.object(graphify_codex_backend, "_publish_no_replace", race):
                with self.assertRaises(graphify_codex_backend.GraphifyCodexRefusal):
                    graphify_codex_backend.build_graph(
                        source, output, model="gpt-5.6-luna", deep_mode=False
                    )
            self.assertEqual((output / "owner.txt").read_text(encoding="utf-8"), "existing")


if __name__ == "__main__":
    unittest.main()
