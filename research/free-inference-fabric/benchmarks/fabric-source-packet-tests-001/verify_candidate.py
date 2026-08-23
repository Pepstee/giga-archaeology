from __future__ import annotations

import hashlib
import json
import os
import tempfile
import types
from pathlib import Path, PurePosixPath


PACKET_SHA256 = "cbb53200fa16401afcd5f7151e1baf16764e945d747c7e3940fae33af18206d3"
PROJECT = "giga-free-inference-fabric"
PACKET_PATH = Path(__file__).with_name("source-packet.json")
MUTATIONS = {
    "path_traversal": (
        'if not value or path.is_absolute() or path == PurePosixPath(".") or ".." in path.parts:',
        'if not value or path.is_absolute() or path == PurePosixPath("."):  # seeded mutant',
    ),
    "symlink_traversal": (
        "if cursor.is_symlink():",
        "if False:  # seeded mutant",
    ),
    "per_file_cap": (
        "if len(data) > max_file_bytes:",
        "if False:  # seeded mutant",
    ),
    "binary_cr": (
        'if "\\x00" in text or "\\r" in text:',
        "if False:  # seeded mutant",
    ),
    "secret_detection": (
        "if any(pattern.search(text) for pattern in SECRET_PATTERNS):",
        "if False:  # seeded mutant",
    ),
    "project_identity": (
        "if not isinstance(project, str) or not project.strip():",
        "if False:  # seeded mutant",
    ),
    "duplicate_inputs": (
        "if len(set(relative_files)) != len(relative_files):",
        "if False:  # seeded mutant",
    ),
}


def reject(reason: str) -> None:
    print(reason)
    raise SystemExit(1)


def canonical_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


try:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"frozen source packet is unreadable: {exc}")
if not isinstance(packet, dict) or packet.get("packet_sha256") != PACKET_SHA256:
    reject("frozen source packet identity is invalid")
without_hash = {key: value for key, value in packet.items() if key != "packet_sha256"}
if canonical_hash(without_hash) != PACKET_SHA256:
    reject("frozen source packet binding hash is invalid")
rows = packet.get("files")
if not isinstance(rows, list) or len(rows) != 1:
    reject("frozen source packet must contain exactly one module")
row = rows[0]
if not isinstance(row, dict) or row.get("path") != "src/giga_inference_fabric/source_packets.py":
    reject("frozen source packet contains the wrong module")
if not isinstance(row.get("lines"), list) or not all(isinstance(line, str) for line in row["lines"]):
    reject("frozen source packet lines are malformed")
SOURCE = "\n".join(row["lines"]) + ("\n" if row.get("trailing_newline") else "")
source_bytes = SOURCE.encode("utf-8")
if row.get("bytes") != len(source_bytes) or row.get("sha256") != hashlib.sha256(source_bytes).hexdigest():
    reject("frozen module content hash is invalid")


def load_module(source: str, name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"<{name}>"
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


reference = load_module(SOURCE, "source_packets_reference")
mutants: dict[str, types.ModuleType] = {}
for mutant_id, (needle, replacement) in MUTATIONS.items():
    if SOURCE.count(needle) < 1:
        reject(f"seeded mutation target drifted: {mutant_id}")
    mutated = SOURCE.replace(needle, replacement, 1)
    mutants[mutant_id] = load_module(mutated, f"source_packets_mutant_{mutant_id}")


def exact_fields(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        reject(f"{label} fields must be exactly {sorted(fields)}")
    return value


def bounded_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 160:
        reject(f"{label} must be a bounded relative path string")
    path = PurePosixPath(value)
    if path.is_absolute() or path == PurePosixPath(".") or ".." in path.parts:
        reject(f"{label} escapes the test fixture")
    return path.as_posix()


candidate_path = os.environ.get("GIGA_CANDIDATE_PATH")
if not candidate_path:
    reject("GIGA_CANDIDATE_PATH is absent")
candidate = Path(candidate_path)
if not candidate.is_file() or candidate.stat().st_size > 131_072:
    reject("candidate must be a regular JSON file no larger than 131072 bytes")
try:
    payload = json.loads(candidate.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"candidate is not strict UTF-8 JSON: {exc}")
exact_fields(payload, {"schema", "project", "source_packet_sha256", "tests"}, "top-level")
if payload["schema"] != "giga.executable-source-packet-tests.v1":
    reject("unsupported executable-test schema")
if payload["project"] != PROJECT or payload["source_packet_sha256"] != PACKET_SHA256:
    reject("candidate is not bound to the frozen project and source packet")
tests = payload["tests"]
if not isinstance(tests, list) or not 9 <= len(tests) <= 24:
    reject("tests must contain 9 to 24 executable cases")

seen_ids: set[str] = set()
normalised_tests: list[dict] = []
accepted = 0
rejected = 0
for index, test in enumerate(tests):
    exact_fields(
        test,
        {"id", "project", "requested_files", "setup", "max_total_bytes", "max_file_bytes", "expected"},
        f"tests[{index}]",
    )
    test_id = test["id"]
    if not isinstance(test_id, str) or not test_id.strip() or test_id in seen_ids:
        reject("test IDs must be unique non-empty strings")
    seen_ids.add(test_id)
    if not isinstance(test["project"], str) or len(test["project"]) > 100:
        reject(f"tests[{index}].project is malformed")
    requested = test["requested_files"]
    if not isinstance(requested, list) or not requested or len(requested) > 12 or not all(
        isinstance(item, str) and len(item) <= 160 for item in requested
    ):
        reject(f"tests[{index}].requested_files is malformed")
    setup = test["setup"]
    if not isinstance(setup, list) or not setup or len(setup) > 12:
        reject(f"tests[{index}].setup is malformed")
    setup_paths: set[str] = set()
    total_fixture_bytes = 0
    for setup_index, item in enumerate(setup):
        exact_fields(item, {"path", "kind", "content", "target"}, f"tests[{index}].setup[{setup_index}]")
        relative = bounded_relative(item["path"], f"tests[{index}].setup[{setup_index}].path")
        if relative in setup_paths:
            reject(f"tests[{index}] repeats a setup path")
        setup_paths.add(relative)
        if item["kind"] == "file":
            if not isinstance(item["content"], str) or item["target"] is not None:
                reject(f"tests[{index}] file setup is malformed")
            total_fixture_bytes += len(item["content"].encode("utf-8"))
        elif item["kind"] == "symlink":
            if item["content"] is not None:
                reject(f"tests[{index}] symlink content must be null")
            bounded_relative(item["target"], f"tests[{index}].setup[{setup_index}].target")
        else:
            reject(f"tests[{index}] setup kind must be file or symlink")
    if total_fixture_bytes > 50_000:
        reject(f"tests[{index}] fixture exceeds byte cap")
    for key in ("max_total_bytes", "max_file_bytes"):
        if not isinstance(test[key], int) or isinstance(test[key], bool) or not 1 <= test[key] <= 100_000:
            reject(f"tests[{index}].{key} must be an integer between 1 and 100000")
    expected = exact_fields(
        test["expected"], {"status", "error_pattern", "file_count", "total_source_bytes"},
        f"tests[{index}].expected",
    )
    if expected["status"] == "ok":
        accepted += 1
        if (
            expected["error_pattern"] is not None
            or not isinstance(expected["file_count"], int)
            or isinstance(expected["file_count"], bool)
            or expected["file_count"] < 1
            or not isinstance(expected["total_source_bytes"], int)
            or isinstance(expected["total_source_bytes"], bool)
            or expected["total_source_bytes"] < 0
        ):
            reject(f"tests[{index}] accepted expectation is malformed")
    elif expected["status"] == "reject":
        rejected += 1
        if (
            not isinstance(expected["error_pattern"], str)
            or len(expected["error_pattern"].strip()) < 3
            or expected["file_count"] is not None
            or expected["total_source_bytes"] is not None
        ):
            reject(f"tests[{index}] rejected expectation is malformed")
    else:
        reject(f"tests[{index}] expected status must be ok or reject")
    normalised_tests.append(test)
if accepted < 2 or rejected < 7:
    reject("suite requires at least two accepted and seven rejected cases")


def execute_case(module: types.ModuleType, test: dict) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="giga-generated-test-") as temp:
        root = Path(temp)
        for item in test["setup"]:
            destination = root / PurePosixPath(item["path"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            if item["kind"] == "file":
                destination.write_text(item["content"], encoding="utf-8", newline="")
        for item in test["setup"]:
            if item["kind"] == "symlink":
                destination = root / PurePosixPath(item["path"])
                target = root / PurePosixPath(item["target"])
                if not target.is_file():
                    return False, "symlink target is not a setup file"
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.symlink_to(target)
        try:
            result = module.build_source_packet(
                root, test["project"], test["requested_files"],
                max_total_bytes=test["max_total_bytes"],
                max_file_bytes=test["max_file_bytes"],
            )
        except Exception as exc:
            observed_status = "reject"
            observed_error = str(exc)
            observed_count = None
            observed_bytes = None
        else:
            observed_status = "ok"
            observed_error = None
            observed_count = len(result["files"])
            observed_bytes = result["total_source_bytes"]
    expected = test["expected"]
    if observed_status != expected["status"]:
        return False, f"expected {expected['status']} but observed {observed_status}"
    if observed_status == "reject":
        if expected["error_pattern"].lower() not in observed_error.lower():
            return False, f"error did not contain {expected['error_pattern']!r}: {observed_error}"
    elif observed_count != expected["file_count"] or observed_bytes != expected["total_source_bytes"]:
        return False, (
            f"expected count/bytes {expected['file_count']}/{expected['total_source_bytes']} "
            f"but observed {observed_count}/{observed_bytes}"
        )
    return True, "matched"


reference_failures = []
for test in normalised_tests:
    passed, detail = execute_case(reference, test)
    if not passed:
        reference_failures.append(f"{test['id']}: {detail}")
if reference_failures:
    reject("generated suite fails the frozen reference: " + "; ".join(reference_failures[:6]))

killed: dict[str, list[str]] = {}
for mutant_id, mutant in mutants.items():
    killers = []
    for test in normalised_tests:
        passed, _detail = execute_case(mutant, test)
        if not passed:
            killers.append(test["id"])
    if killers:
        killed[mutant_id] = killers
survivors = sorted(set(mutants) - set(killed))
if survivors:
    reject("generated suite left seeded mutants alive: " + ", ".join(survivors))

print(
    "VERIFIED giga.executable-source-packet-tests.v1 "
    f"reference={len(normalised_tests)}/{len(normalised_tests)} mutants={len(killed)}/{len(mutants)}"
)
