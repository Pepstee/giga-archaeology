from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_finetune_data import prepare_pairs, transcript_candidates


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")


class PrepareFineTuneDataTests(unittest.TestCase):
    def test_pairs_are_deduplicated_quarantined_and_context_coalesced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "pairs.jsonl"
            base = {"messages": [
                {"role": "user", "content": "same prompt"},
                {"role": "assistant", "content": "reply"}],
                "meta": {"thread": "a", "ts": "2026-01-01T00:00:00Z"}}
            write_jsonl(source, [
                base,
                base,
                {"messages": [
                    {"role": "user", "content": "same prompt"},
                    {"role": "assistant", "content": "different reply"}],
                    "meta": {"thread": "b", "ts": "2026-02-01T00:00:00Z"}},
                {"messages": [
                    {"role": "user", "content": "api_key = abcdefghijk"},
                    {"role": "assistant", "content": "do not train this"}],
                    "meta": {"thread": "c", "ts": "2026-03-01T00:00:00Z"}},
            ])
            output = root / "out"
            args = argparse.Namespace(input=source, output=output, privacy="local", seed="test",
                                      valid_fraction=0.2, test_fraction=0.2, force=False,
                                      mode_map=None, only_mode=None)
            prepare_pairs(args)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["exact_duplicates_removed"], 1)
            self.assertEqual(manifest["quarantined_possible_credentials"], 1)
            locations = {}
            for split in ("train", "valid", "test"):
                for line in (output / f"{split}.jsonl").read_text().splitlines():
                    record = json.loads(line)
                    prompt = record["messages"][0]["content"]
                    locations.setdefault(prompt, set()).add(split)
            self.assertEqual(len(locations["same prompt"]), 1)

    def test_cloud_profile_redacts_contact_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "pairs.jsonl"
            write_jsonl(source, [{"messages": [
                {"role": "user", "content": "mail me at a@example.com via https://example.com"},
                {"role": "assistant", "content": "call +44 7700 900123"}],
                "meta": {"thread": "a", "ts": "2026-01-01T00:00:00Z"}}])
            output = root / "out"
            args = argparse.Namespace(input=source, output=output, privacy="cloud", seed="test",
                                      valid_fraction=0.0, test_fraction=0.0, force=False,
                                      mode_map=None, only_mode=None)
            prepare_pairs(args)
            text = (output / "train.jsonl").read_text()
            self.assertIn("<EMAIL>", text)
            self.assertIn("<URL>", text)
            self.assertIn("<PHONE>", text)
            self.assertNotIn("a@example.com", text)

    def test_mode_map_labels_and_filters_threads(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "pairs.jsonl"
            write_jsonl(source, [
                {"messages": [{"role": "user", "content": "one"},
                              {"role": "assistant", "content": "reply one"}],
                 "meta": {"thread": "general", "ts": "2026-01-01T00:00:00Z"}},
                {"messages": [{"role": "user", "content": "two"},
                              {"role": "assistant", "content": "reply two"}],
                 "meta": {"thread": "private", "ts": "2026-01-01T00:00:00Z"}},
            ])
            mode_map = root / "modes.json"
            mode_map.write_text(json.dumps({"default_mode": "unassigned", "threads": {
                "general": "casual-general", "private": "partner-intimate"}}))
            output = root / "out"
            args = argparse.Namespace(input=source, output=output, privacy="local", seed="test",
                                      valid_fraction=0.0, test_fraction=0.0, force=False,
                                      mode_map=mode_map, only_mode="casual-general")
            prepare_pairs(args)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["mode_counts"], {"casual-general": 1})
            self.assertEqual(manifest["excluded_by_mode_policy"], 1)

    def test_transcript_roles_are_inverted_for_operator_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "transcript.jsonl"
            write_jsonl(source, [
                {"sender": "human", "text": "initial task", "conv_uuid": "c", "ts": "1"},
                {"sender": "assistant", "text": "model answer", "conv_uuid": "c", "ts": "2"},
                {"sender": "human", "text": "you missed the constraint", "conv_uuid": "c", "ts": "3"},
            ])
            output = root / "candidates.jsonl"
            args = argparse.Namespace(input=source, output=output, mode="reasoning-steering",
                                      context_turns=6, force=False)
            transcript_candidates(args)
            candidate = json.loads(output.read_text().strip())
            self.assertEqual(candidate["messages"], [
                {"role": "user", "content": "model answer"},
                {"role": "assistant", "content": "you missed the constraint"},
            ])
            self.assertIn("correction", candidate["meta"]["quality_flags"])


if __name__ == "__main__":
    unittest.main()
