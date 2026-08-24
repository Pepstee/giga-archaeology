from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src/giga_inference_fabric/source_packets.py"
RELATED_TESTS = (
    ROOT / "tests/test_source_packets.py",
    ROOT / "tests/test_source_packet_generation_benchmark.py",
)
BENCHMARK_ID = "fabric-source-packet-tests-001"
SOURCE_PACKET = ROOT / "benchmarks/fabric-source-packet-tests-001/source-packet.json"
OBJECTIVE = (
    "Generate a data-only executable test suite that passes the frozen source-packet builder "
    "and kills all hidden seeded mutants"
)
PROMPT = (
    "Return only strict JSON using the benchmark executable-test schema. Generate a compact "
    "suite that passes the frozen reference and kills every hidden seeded mutant without "
    "returning executable code. Use the attached measured coverage gap only to prioritise cases."
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def coverage_observation(report: dict) -> dict:
    files = report.get("files")
    if not isinstance(files, dict):
        raise ValueError("coverage report has no files object")
    matches = [value for key, value in files.items() if key.endswith("/source_packets.py")]
    if len(matches) != 1:
        raise ValueError("coverage report must contain exactly one source_packets.py result")
    row = matches[0]
    summary = row.get("summary")
    missing = row.get("missing_lines")
    if (
        not isinstance(summary, dict)
        or not isinstance(missing, list)
        or not all(isinstance(line, int) and line > 0 for line in missing)
    ):
        raise ValueError("coverage result is malformed")
    required = ("covered_lines", "missing_lines", "num_statements", "percent_covered")
    if any(key not in summary for key in required):
        raise ValueError("coverage summary is incomplete")
    observation = {
        "schema": "giga.coverage-gap.v1",
        "target": "src/giga_inference_fabric/source_packets.py",
        "target_sha256": digest(TARGET),
        "test_sha256": {str(path.relative_to(ROOT)): digest(path) for path in RELATED_TESTS},
        "covered_lines": int(summary["covered_lines"]),
        "missing_lines": sorted(set(missing)),
        "num_statements": int(summary["num_statements"]),
        "percent_covered": float(summary["percent_covered"]),
    }
    canonical = json.dumps(observation, sort_keys=True, separators=(",", ":")).encode()
    return {**observation, "fingerprint": hashlib.sha256(canonical).hexdigest()}


def measure() -> dict:
    with tempfile.TemporaryDirectory(prefix="giga-coverage-") as temporary:
        temporary_path = Path(temporary)
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        environment["COVERAGE_FILE"] = str(temporary_path / "data")
        test = subprocess.run(
            [sys.executable, "-m", "coverage", "run", "--source=src/giga_inference_fabric", "-m", "pytest", "-q"],
            cwd=ROOT, env=environment, text=True, capture_output=True, check=False,
        )
        if test.returncode != 0:
            raise RuntimeError("coverage test command failed closed: " + (test.stdout + test.stderr)[-4000:])
        report_path = temporary_path / "report.json"
        rendered = subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", str(report_path)],
            cwd=ROOT, env=environment, text=True, capture_output=True, check=False,
        )
        if rendered.returncode != 0 or not report_path.is_file():
            raise RuntimeError("coverage report command failed closed: " + (rendered.stdout + rendered.stderr)[-4000:])
        return coverage_observation(json.loads(report_path.read_text(encoding="utf-8")))


def read_state(path: Path) -> dict:
    if not path.exists():
        return {"schema": "giga.coverage-feeder-state.v1", "last_observed": None, "last_enqueued": None, "work_id": None}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if set(payload) != {"schema", "last_observed", "last_enqueued", "work_id"} or payload["schema"] != "giga.coverage-feeder-state.v1":
        raise ValueError("coverage feeder state is malformed")
    return payload


def active_work(db: Path) -> str | None:
    connection = sqlite3.connect(db)
    try:
        row = connection.execute(
            "SELECT work_id FROM work_queue WHERE benchmark_id=? AND status IN ('QUEUED','LEASED') ORDER BY priority DESC,created_at LIMIT 1",
            (BENCHMARK_ID,),
        ).fetchone()
    finally:
        connection.close()
    return str(row[0]) if row else None


def benchmark_matches_target() -> bool:
    packet = json.loads(SOURCE_PACKET.read_text(encoding="utf-8"))
    rows = packet.get("files")
    if not isinstance(rows, list):
        raise ValueError("coverage benchmark source packet is malformed")
    matches = [
        row for row in rows
        if isinstance(row, dict) and row.get("path") == "src/giga_inference_fabric/source_packets.py"
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("sha256"), str):
        raise ValueError("coverage benchmark does not bind exactly one target module")
    return matches[0]["sha256"] == digest(TARGET)


def write_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=ROOT / "state/experiments.sqlite3")
    parser.add_argument("--state", type=Path, default=ROOT / "state/coverage/feeder.json")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    observation = measure()
    state = read_state(args.state)
    pending = active_work(args.db)
    if not benchmark_matches_target():
        status = "BENCHMARK_REFRESH_REQUIRED"
    elif state["last_observed"] == observation["fingerprint"]:
        status = "NO_CHANGE"
    elif pending:
        status = "BOUND_TO_PENDING" if state["last_enqueued"] is None else "DEFER_PENDING"
        if status == "BOUND_TO_PENDING":
            state["last_enqueued"] = observation["fingerprint"]
            state["work_id"] = pending
    else:
        status = "READY_TO_ENQUEUE"
    state["last_observed"] = observation["fingerprint"]

    work_id = state["work_id"]
    if status == "READY_TO_ENQUEUE" and args.execute:
        work_id = "work-coverage-source-packets-" + observation["fingerprint"][:16]
        command = [
            sys.executable, "-m", "giga_inference_fabric.cli", "--db", str(args.db),
            "queue-add", "--work-id", work_id, "--project", "giga-free-inference-fabric",
            "--workload", "test-generation", "--benchmark-id", BENCHMARK_ID,
            "--objective", OBJECTIVE, "--prompt", PROMPT,
            "--context", json.dumps(observation, sort_keys=True),
            "--source-packet", str(SOURCE_PACKET), "--priority", "70", "--max-attempts", "3",
        ]
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        queued = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
        if queued.returncode != 0:
            raise RuntimeError("coverage queue admission failed closed: " + (queued.stdout + queued.stderr)[-4000:])
        state["last_enqueued"] = observation["fingerprint"]
        state["work_id"] = work_id
        status = "ENQUEUED"
    if args.execute:
        write_state(args.state, state)
    print(json.dumps({
        "schema": "giga.coverage-feeder-receipt.v1",
        "recorded_at": datetime.now(UTC).isoformat(),
        "status": status,
        "execute": args.execute,
        "observation": observation,
        "pending_work_id": pending,
        "work_id": work_id,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
