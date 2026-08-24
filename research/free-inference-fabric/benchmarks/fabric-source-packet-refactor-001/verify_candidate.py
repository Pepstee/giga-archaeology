from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
import types
from pathlib import Path


PACKET_SHA256 = "cbb53200fa16401afcd5f7151e1baf16764e945d747c7e3940fae33af18206d3"
PROJECT = "giga-free-inference-fabric"
PACKET_PATH = Path(__file__).with_name("source-packet.json")
INSERT_AFTER = '        text = "\\n".join(row["lines"]) + ("\\n" if row["trailing_newline"] else "")'
ALLOWED_AST = {
    ast.Module, ast.If, ast.BoolOp, ast.Or, ast.And, ast.Compare, ast.In, ast.NotIn,
    ast.Constant, ast.Name, ast.Load, ast.Store, ast.Subscript, ast.Call, ast.GeneratorExp,
    ast.comprehension, ast.Raise,
}
ALLOWED_NAMES = {"text", "row", "line", "any", "ValueError"}
ALLOWED_CALLS = {"any", "ValueError"}


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
if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("path") != "src/giga_inference_fabric/source_packets.py":
    reject("frozen source packet contains the wrong module")
row = rows[0]
if not isinstance(row.get("lines"), list) or not all(isinstance(line, str) for line in row["lines"]):
    reject("frozen source lines are malformed")
SOURCE = "\n".join(row["lines"]) + ("\n" if row.get("trailing_newline") else "")
source_bytes = SOURCE.encode("utf-8")
if row.get("bytes") != len(source_bytes) or row.get("sha256") != hashlib.sha256(source_bytes).hexdigest():
    reject("frozen module content hash is invalid")
if SOURCE.count(INSERT_AFTER) != 1:
    reject("frozen refactor insertion point drifted")


def exact_fields(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        reject(f"{label} fields must be exactly {sorted(fields)}")
    return value


candidate_path = os.environ.get("GIGA_CANDIDATE_PATH")
if not candidate_path:
    reject("GIGA_CANDIDATE_PATH is absent")
candidate = Path(candidate_path)
if not candidate.is_file() or candidate.stat().st_size > 16_384:
    reject("candidate must be a regular JSON file no larger than 16384 bytes")
try:
    candidate_payload = json.loads(candidate.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"candidate is not strict UTF-8 JSON: {exc}")
exact_fields(candidate_payload, {"schema", "project", "source_packet_sha256", "refactor"}, "top-level")
if candidate_payload["schema"] != "giga.restricted-refactor.v1":
    reject("unsupported restricted-refactor schema")
if candidate_payload["project"] != PROJECT or candidate_payload["source_packet_sha256"] != PACKET_SHA256:
    reject("candidate is not bound to the frozen project and source packet")
refactor = exact_fields(
    candidate_payload["refactor"], {"target", "rationale", "validation_block"}, "refactor",
)
if refactor["target"] != "verify_source_packet":
    reject("restricted refactor target must be verify_source_packet")
if (
    not isinstance(refactor["rationale"], str)
    or refactor["rationale"] != refactor["rationale"].strip()
    or not 30 <= len(refactor["rationale"]) <= 1000
):
    reject("refactor rationale must be a bounded concrete explanation")
block = refactor["validation_block"]
if not isinstance(block, str) or not block.strip() or len(block) > 2000:
    reject("validation_block must be a bounded Python string")
if block != block.strip("\n") or any(line.startswith((" ", "\t")) for line in block.splitlines()[:1]):
    reject("validation_block must be unindented and have no surrounding blank lines")
try:
    block_tree = ast.parse(block, mode="exec")
except SyntaxError as exc:
    reject(f"validation_block is invalid Python: {exc}")
if len(block_tree.body) != 1 or not isinstance(block_tree.body[0], ast.If):
    reject("validation_block must contain exactly one top-level if")
if_node = block_tree.body[0]
if len(if_node.body) != 1 or not isinstance(if_node.body[0], ast.Raise) or if_node.orelse:
    reject("validation_block if must contain exactly one raise and no else")
for node in ast.walk(block_tree):
    if type(node) not in ALLOWED_AST:
        reject(f"validation_block contains forbidden AST node: {type(node).__name__}")
    if isinstance(node, ast.Name) and node.id not in ALLOWED_NAMES:
        reject(f"validation_block contains forbidden name: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_CALLS:
            reject("validation_block contains a forbidden call")
raise_node = if_node.body[0]
if (
    raise_node.exc is None
    or not isinstance(raise_node.exc, ast.Call)
    or not isinstance(raise_node.exc.func, ast.Name)
    or raise_node.exc.func.id != "ValueError"
):
    reject("validation_block must raise ValueError")

indented_block = "\n".join("        " + line for line in block.splitlines())
patched_source = SOURCE.replace(INSERT_AFTER, INSERT_AFTER + "\n" + indented_block, 1)
patched = types.ModuleType("source_packets_restricted_refactor")
patched.__file__ = "<source_packets_restricted_refactor>"
try:
    exec(compile(patched_source, patched.__file__, "exec"), patched.__dict__)
except Exception as exc:
    reject(f"patched frozen module did not compile: {exc}")


def external_packet(lines: list[str], trailing_newline: bool = False) -> dict:
    text = "\n".join(lines) + ("\n" if trailing_newline else "")
    data = text.encode("utf-8")
    row = {
        "path": "probe.txt",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "line_count": len(lines),
        "trailing_newline": trailing_newline,
        "lines": lines,
    }
    payload = {
        "schema": "giga.source-packet.v1",
        "project": "refactor-probe",
        "total_source_bytes": len(data),
        "files": [row],
    }
    return {**payload, "packet_sha256": canonical_hash(payload)}


for valid in (
    external_packet(["ordinary text"]),
    external_packet(["first", "second"]),
    external_packet(["first", "second"], trailing_newline=True),
):
    try:
        result = patched.verify_source_packet(valid)
    except Exception as exc:
        reject(f"refactor breaks canonical valid packets: {exc}")
    if result is not valid:
        reject("refactor changed the verify_source_packet return contract")

invalid = (
    external_packet(["first\nsecond"]),
    external_packet(["first\rsecond"]),
    external_packet(["first\x00second"]),
)
for packet_value in invalid:
    try:
        patched.verify_source_packet(packet_value)
    except ValueError:
        pass
    else:
        reject("refactor failed a hidden non-canonical/control-content regression")

with tempfile.TemporaryDirectory(prefix="giga-refactor-regression-") as temp:
    root = Path(temp)
    (root / "probe.txt").write_text("first\nsecond\n", encoding="utf-8")
    built = patched.build_source_packet(root, "refactor-probe", ["probe.txt"])
    try:
        patched.verify_source_packet(built)
    except Exception as exc:
        reject(f"refactor rejects builder-produced canonical packet: {exc}")

print("VERIFIED giga.restricted-refactor.v1 valid=4 invalid=3 ast_restricted=true")
