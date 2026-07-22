#!/usr/bin/env python3
"""Process newly collected vacancies and admit only new immutable score snapshots."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--market-root", type=Path, required=True)
    result.add_argument("--jaa-root", type=Path, required=True)
    result.add_argument("--career-database", type=Path, required=True)
    result.add_argument("--config", default="skeleton/config.overnight.yaml")
    result.add_argument("--skip-processing", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    market_root = args.market_root.resolve()
    jaa_root = args.jaa_root.resolve()
    database_path = args.career_database.resolve()
    scored_path = market_root / "skeleton/data_overnight/jobs_scored.jsonl"

    if not args.skip_processing:
        command = [
            str(market_root / ".venv/bin/python"),
            str(market_root / "scripts/process_collected_jobs.py"),
            "--config",
            args.config,
        ]
        subprocess.run(command, cwd=market_root, check=True)

    if not scored_path.is_file():
        raise RuntimeError(f"scored vacancy stream is missing: {scored_path}")
    sys.path.insert(0, str(jaa_root))
    from career_automation import CareerDatabase, OpportunityGate  # noqa: PLC0415
    from career_automation.engine import read_scored_jsonl  # noqa: PLC0415

    database = CareerDatabase(database_path)
    with database.connection() as connection:
        existing = {
            str(row["job_key"]): str(row["payload_hash"])
            for row in connection.execute("SELECT job_key,payload_hash FROM pipeline_jobs")
        }

    new_jobs = []
    unchanged = 0
    changed = []
    for job in read_scored_jsonl(scored_path):
        old_hash = existing.get(job.key)
        if old_hash is None:
            new_jobs.append(job)
        elif old_hash == job.payload_hash:
            unchanged += 1
        else:
            # JAA's immutable score ledger intentionally refuses in-place replacement. Keep the
            # old authoritative version until JAA ships its explicit version-transition event.
            changed.append({
                "job_key": job.key,
                "authoritative_hash": old_hash,
                "observed_hash": job.payload_hash,
            })

    gate = OpportunityGate(database)
    imported = passed = rejected = 0
    for job in new_jobs:
        if not database.upsert_scored_job(job):
            continue
        imported += 1
        with database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM pipeline_jobs WHERE job_key=?", (job.key,),
            ).fetchone()
        if row is None:
            raise RuntimeError(f"newly imported job disappeared: {job.key}")
        decision = gate.decide(row)
        is_pass = decision.decision.value == "pass"
        database.apply_opportunity_result(
            job_key=decision.job_key,
            passed=is_pass,
            reason=decision.reason,
            policy_hash=gate.policy.policy_hash,
            priority=decision.research_priority,
        )
        passed += int(is_pass)
        rejected += int(not is_pass)
    with database.connection() as connection:
        queued = int(connection.execute(
            "SELECT COUNT(*) FROM employer_research_queue WHERE status='queued'"
        ).fetchone()[0])
    report = {
        "scored_rows": unchanged + len(changed) + len(new_jobs),
        "unchanged": unchanged,
        "version_changes_deferred": len(changed),
        "deferred_examples": changed[:20],
        "new_import": {
            "imported": imported,
            "passed": passed,
            "rejected": rejected,
            "research_queued_total": queued,
        },
        "database": database.stats(),
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
