from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from twin_core.knowledge_refresh import _refresh_knowledge as refresh_knowledge, _validate_knowledge_refresh as validate_knowledge_refresh


ENTRY = """---
type: fact
tags: [test]
created: 2026-08-03
status: active
---
Knowledge refresh exists.

Source: test fixture.
"""


class KnowledgeRefreshTests(unittest.TestCase):
    def test_refresh_builds_current_context_and_memory_graph(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve() / "source"
            output = root.parent / "private-projection"
            memory = root / "memory"
            (memory / "entries").mkdir(parents=True)
            (root / "CONTEXT.md").write_text("context\n", encoding="utf-8")
            (root / "CONTEXT_PROTOCOL.md").write_text("protocol\n", encoding="utf-8")
            (memory / "MEMORY_PROTOCOL.md").write_text("memory protocol\n", encoding="utf-8")
            (memory / "INDEX.md").write_text(
                "# Index\n\n- [refresh](entries/2026-08-03-refresh.md)\n", encoding="utf-8"
            )
            (memory / "entries/2026-08-03-refresh.md").write_text(ENTRY, encoding="utf-8")
            (memory / "tombstones.v1.json").write_text(
                '{"schema":"giga.memory.legacy-tombstones.v1","append_only":true,'
                '"deletion_performed":false,"entries":[]}\n', encoding="utf-8"
            )

            def fake_graphify(giga_root: Path, generated: Path) -> None:
                graph = generated / "graph.json"
                graph.parent.mkdir(parents=True, exist_ok=True)
                graph.write_text(
                    json.dumps({"nodes": [{"id": "code"}], "links": []}), encoding="utf-8"
                )

            refresh_knowledge(root, private_output=output, graphify_runner=fake_graphify)
            status = validate_knowledge_refresh(root, private_output=output)
            self.assertEqual(status["result"], "passed")
            graph = json.loads(
                (output / "graphify/graph.json").read_text(encoding="utf-8")
            )
            self.assertIn("giga-memory:2026-08-03-refresh", {
                item["id"] for item in graph["nodes"]
            })
            self.assertFalse((root / "graphify-out").exists())
            (root / "CONTEXT.md").write_text("changed context\n", encoding="utf-8")
            stale = validate_knowledge_refresh(root, private_output=output)
            self.assertEqual(stale["result"], "failed")
            self.assertIn("context-projection-stale", stale["findings"])


if __name__ == "__main__":
    unittest.main()



def test_public_refresh_refuses_before_io(tmp_path):
    from unittest.mock import patch
    import pytest
    from twin_core import knowledge_refresh as refresh
    from twin_core.constitutional_authority import AuthorityRefused
    with patch.object(Path, "open", side_effect=AssertionError("no corpus read")):
        for call in (refresh.refresh_knowledge, refresh.validate_knowledge_refresh, refresh.ensure_knowledge_current):
            with pytest.raises(AuthorityRefused):
                call(tmp_path, private_output=tmp_path / "projection")


def test_private_output_cannot_mix_with_source_or_follow_symlinks(tmp_path):
    import pytest
    from twin_core.knowledge_refresh import _graphify_paths, KnowledgeRefreshError
    root = tmp_path.resolve() / "source"
    root.mkdir()
    with pytest.raises(KnowledgeRefreshError):
        _graphify_paths(root, root / "graphify-out")
    elsewhere = tmp_path.resolve() / "elsewhere"
    elsewhere.mkdir()
    link = tmp_path.resolve() / "link"
    link.symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(KnowledgeRefreshError):
        _graphify_paths(root, link)


def test_source_identity_is_nonempty_and_independent_of_corpus_root(tmp_path):
    from twin_core.knowledge_refresh import _core_source_sha256, _code_sources
    assert len(_code_sources()) == 9
    before = _core_source_sha256(tmp_path)
    (tmp_path / "synthetic-excluded.txt").write_text("not source")
    assert _core_source_sha256(tmp_path) == before
