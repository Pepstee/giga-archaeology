from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def reject(reason: str) -> None:
    print(reason)
    raise SystemExit(1)


candidate_path = os.environ.get("GIGA_CANDIDATE_PATH")
if not candidate_path:
    reject("GIGA_CANDIDATE_PATH is absent")

try:
    payload = json.loads(Path(candidate_path).read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    reject(f"candidate is not readable strict JSON: {exc}")

if not isinstance(payload, dict) or set(payload) != {"schema", "tests"}:
    reject("top-level fields must be exactly schema and tests")
if payload["schema"] != "giga.test-plan.v1":
    reject("unsupported schema")
tests = payload["tests"]
if not isinstance(tests, list) or not tests:
    reject("tests must be a non-empty array")

allowed_fields = {"id", "kind", "input", "expected"}
seen_ids = set()
kinds = set()
for test in tests:
    if not isinstance(test, dict) or set(test) != allowed_fields:
        reject("every test must contain exactly id, kind, input and expected")
    if not all(isinstance(test[key], str) and test[key].strip() for key in allowed_fields):
        reject("every test field must be a non-empty string")
    if test["id"] in seen_ids:
        reject("test IDs must be unique")
    seen_ids.add(test["id"])
    kinds.add(test["kind"])
    if test["kind"] == "negative_control" and not any(
        word in test["expected"].lower() for word in ("reject", "fail", "error")
    ):
        reject("negative control expected result must explicitly reject or fail")

if "positive" not in kinds or "negative_control" not in kinds:
    reject("plan must include positive and negative_control cases")

print("VERIFIED giga.test-plan.v1")
sys.exit(0)
