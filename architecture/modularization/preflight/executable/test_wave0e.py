from __future__ import annotations

import copy
import json
import unittest

from build_wave0e import ALLOWLIST, WRITER_GATE
from validate_wave0e import validate


class Wave0ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.allowlist = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
        cls.gate = json.loads(WRITER_GATE.read_text(encoding="utf-8"))

    def test_live_manifests_validate(self) -> None:
        self.assertEqual(validate(self.allowlist, self.gate), [])

    def test_every_path_is_allowed_or_denied_once(self) -> None:
        allow = set(self.allowlist["safe_to_promote"])
        deny = set(self.allowlist["deny"])
        records = {item["path"] for item in self.allowlist["records"]}
        self.assertFalse(allow & deny)
        self.assertEqual(allow | deny, records)

    def test_raw_export_is_never_promotable(self) -> None:
        record = next(
            item for item in self.allowlist["records"] if item["path"] == "result.json"
        )
        self.assertEqual(record["category"], "private_raw")
        self.assertFalse(record["promotable"])

    def test_unknown_category_fails(self) -> None:
        candidate = copy.deepcopy(self.allowlist)
        candidate["records"][0]["category"] = "wishful"
        self.assertIn(
            "unknown classification category",
            validate(candidate, self.gate, check_live=False),
        )

    def test_writer_decision_fails_closed(self) -> None:
        gate = copy.deepcopy(self.gate)
        gate["repo_bound_processes"] = [{"pid": 1, "command": "writer"}]
        gate["ready_for_root_move"] = True
        self.assertIn(
            "live-writer decision does not match observed processes",
            validate(self.allowlist, gate, check_live=False),
        )


if __name__ == "__main__":
    unittest.main()
