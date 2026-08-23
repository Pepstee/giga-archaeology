from __future__ import annotations

import hashlib
import json
import os
import tempfile
import types
from pathlib import Path


PACKET_SHA256 = "cbb53200fa16401afcd5f7151e1baf16764e945d747c7e3940fae33af18206d3"
PROJECT = "giga-free-inference-fabric"
SOURCE_PATH = "src/giga_inference_fabric/source_packets.py"
PACKET_PATH = Path(__file__).with_name("source-packet.json")


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
if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("path") != SOURCE_PATH:
    reject("frozen source packet contains the wrong module")
row = rows[0]
SOURCE_LINES = row.get("lines")
if not isinstance(SOURCE_LINES, list) or not all(isinstance(line, str) for line in SOURCE_LINES):
    reject("frozen source lines are malformed")
SOURCE = "\n".join(SOURCE_LINES) + ("\n" if row.get("trailing_newline") else "")
source_bytes = SOURCE.encode("utf-8")
if row.get("bytes") != len(source_bytes) or row.get("sha256") != hashlib.sha256(source_bytes).hexdigest():
    reject("frozen module content hash is invalid")

module = types.ModuleType("source_packets_bug_hunt_reference")
module.__file__ = "<source_packets_bug_hunt_reference>"
exec(compile(SOURCE, module.__file__, "exec"), module.__dict__)


def exact_fields(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        reject(f"{label} fields must be exactly {sorted(fields)}")
    return value


def substantive(value: object, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) < 20:
        reject(f"{label} must be a trimmed concrete string of at least 20 characters")
    return value


def resolve_anchor(value: object) -> tuple[int, str]:
    if not isinstance(value, str) or not value.startswith(SOURCE_PATH + ":"):
        reject(f"source anchor is outside the frozen module: {value}")
    number_text = value.removeprefix(SOURCE_PATH + ":")
    if not number_text.isdigit() or int(number_text) < 1 or int(number_text) > len(SOURCE_LINES):
        reject(f"source anchor line is invalid: {value}")
    number = int(number_text)
    return number, SOURCE_LINES[number - 1]


def external_packet(payload_text: str) -> dict:
    data = payload_text.encode("utf-8")
    row = {
        "path": "probe.txt",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "line_count": 1,
        "trailing_newline": False,
        "lines": [payload_text],
    }
    payload = {
        "schema": "giga.source-packet.v1",
        "project": "bug-hunt-probe",
        "total_source_bytes": len(data),
        "files": [row],
    }
    return {**payload, "packet_sha256": canonical_hash(payload)}


candidate_path = os.environ.get("GIGA_CANDIDATE_PATH")
if not candidate_path:
    reject("GIGA_CANDIDATE_PATH is absent")
candidate = Path(candidate_path)
if not candidate.is_file() or candidate.stat().st_size > 65_536:
    reject("candidate must be a regular JSON file no larger than 65536 bytes")
try:
    candidate_payload = json.loads(candidate.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    reject(f"candidate is not strict UTF-8 JSON: {exc}")
exact_fields(candidate_payload, {"schema", "project", "source_packet_sha256", "findings"}, "top-level")
if candidate_payload["schema"] != "giga.source-packet-bug-report.v1":
    reject("unsupported bug-report schema")
if candidate_payload["project"] != PROJECT or candidate_payload["source_packet_sha256"] != PACKET_SHA256:
    reject("candidate is not bound to the frozen project and source packet")
findings = candidate_payload["findings"]
if not isinstance(findings, list) or len(findings) != 2:
    reject("findings must contain exactly two differential reproductions")

seen_ids: set[str] = set()
seen_kinds: set[str] = set()
for index, finding in enumerate(findings):
    exact_fields(
        finding,
        {"id", "defect", "impact", "confidence", "sources", "reproducer", "expected", "observed"},
        f"findings[{index}]",
    )
    finding_id = finding["id"]
    if not isinstance(finding_id, str) or not finding_id.strip() or finding_id in seen_ids:
        reject("finding IDs must be unique non-empty strings")
    seen_ids.add(finding_id)
    substantive(finding["defect"], f"findings[{index}].defect")
    substantive(finding["impact"], f"findings[{index}].impact")
    substantive(finding["expected"], f"findings[{index}].expected")
    substantive(finding["observed"], f"findings[{index}].observed")
    if finding["confidence"] != "certain":
        reject("differentially reproduced findings must have confidence=certain")
    sources = finding["sources"]
    if not isinstance(sources, list) or not 2 <= len(sources) <= 8 or len(set(sources)) != len(sources):
        reject("each finding needs two to eight unique source anchors")
    resolved = [resolve_anchor(anchor) for anchor in sources]
    builder_evidence = any(
        number in range(59, 70) and ("unsupported binary/CR" in line or "split" in line)
        for number, line in resolved
    )
    verifier_evidence = any(number == 162 and r'"\n".join' in line for number, line in resolved)
    if not builder_evidence or not verifier_evidence:
        reject("finding must anchor both builder normalization/rejection and verifier reconstruction")
    reproducer = exact_fields(finding["reproducer"], {"kind", "payload"}, f"findings[{index}].reproducer")
    kind = reproducer["kind"]
    payload_text = reproducer["payload"]
    if kind not in {"embedded_newline", "unsupported_control"} or kind in seen_kinds:
        reject("reproducer kinds must be unique embedded_newline and unsupported_control")
    seen_kinds.add(kind)
    if not isinstance(payload_text, str) or not 3 <= len(payload_text) <= 200:
        reject("reproducer payload must be a bounded string")
    if kind == "embedded_newline" and (
        "\n" not in payload_text or "\r" in payload_text or "\x00" in payload_text
    ):
        reject("embedded_newline payload must contain newline but no CR/NUL")
    if kind == "unsupported_control" and "\r" not in payload_text and "\x00" not in payload_text:
        reject("unsupported_control payload must contain CR or NUL")

    probe = external_packet(payload_text)
    try:
        module.verify_source_packet(probe)
    except Exception as exc:
        reject(f"frozen verifier did not reproduce acceptance for {kind}: {exc}")

    with tempfile.TemporaryDirectory(prefix="giga-bug-hunt-") as temp:
        root = Path(temp)
        (root / "probe.txt").write_text(payload_text, encoding="utf-8", newline="")
        try:
            built = module.build_source_packet(root, "bug-hunt-probe", ["probe.txt"])
        except ValueError as exc:
            if kind != "unsupported_control" or "unsupported binary/CR" not in str(exc):
                reject(f"builder differential is not the admitted {kind} defect: {exc}")
        else:
            if kind != "embedded_newline":
                reject("builder unexpectedly accepted an unsupported control payload")
            built_row = built["files"][0]
            if built_row["line_count"] <= 1 or built_row["lines"] == [payload_text]:
                reject("builder did not demonstrate canonical newline splitting")

if seen_kinds != {"embedded_newline", "unsupported_control"}:
    reject("both differential defect classes are required")

print("VERIFIED giga.source-packet-bug-report.v1 differential_defects=2/2")
