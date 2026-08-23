from __future__ import annotations

import json
import hashlib
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .models import Candidate, CostTier, Critique, ExperimentRequest, GateResult, ModelSpec


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS experiments(
 experiment_id TEXT PRIMARY KEY, objective TEXT NOT NULL, workload TEXT NOT NULL,
 benchmark_id TEXT, request_json TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 finished_at TEXT, stop_reason TEXT);
CREATE TABLE IF NOT EXISTS attempts(
 candidate_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
 round_number INTEGER NOT NULL, approach TEXT NOT NULL, adapter TEXT NOT NULL, model_id TEXT NOT NULL,
 output_hash TEXT NOT NULL, output_text TEXT NOT NULL, prompt_tokens INTEGER NOT NULL,
 completion_tokens INTEGER NOT NULL, latency_ms INTEGER NOT NULL, cost_usd REAL NOT NULL,
 gate_passed INTEGER, gate_score REAL, gate_summary TEXT, gate_checks_json TEXT NOT NULL DEFAULT '[]',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS critiques(
 candidate_id TEXT NOT NULL REFERENCES attempts(candidate_id), critic_model_id TEXT NOT NULL,
 findings_hash TEXT NOT NULL, critique_text TEXT NOT NULL,
 PRIMARY KEY(candidate_id,critic_model_id,findings_hash));
CREATE TABLE IF NOT EXISTS provider_calls(
 call_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
 purpose TEXT NOT NULL, requested_model_id TEXT NOT NULL, served_model_id TEXT,
 adapter TEXT NOT NULL, success INTEGER NOT NULL, latency_ms INTEGER NOT NULL DEFAULT 0,
 prompt_tokens INTEGER NOT NULL DEFAULT 0,completion_tokens INTEGER NOT NULL DEFAULT 0,
 cost_usd REAL NOT NULL DEFAULT 0,error TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS model_observations(
 observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, model_id TEXT NOT NULL, adapter TEXT NOT NULL,
 cost_tier TEXT NOT NULL, preview INTEGER NOT NULL, available INTEGER NOT NULL,
 context_length INTEGER NOT NULL, capabilities_json TEXT NOT NULL, metadata_json TEXT NOT NULL,
 PRIMARY KEY(observed_at,model_id,adapter));
CREATE TABLE IF NOT EXISTS catalogue_events(
 event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, model_id TEXT NOT NULL,
 details_json TEXT NOT NULL, observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS solution_patterns(
 pattern_id TEXT PRIMARY KEY, workload TEXT NOT NULL, problem_fingerprint TEXT NOT NULL,
 approach TEXT NOT NULL, model_id TEXT NOT NULL, evidence_json TEXT NOT NULL,
 success_count INTEGER NOT NULL DEFAULT 1, last_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS failure_patterns(
 failure_id TEXT PRIMARY KEY, workload TEXT NOT NULL, failure_fingerprint TEXT NOT NULL,
 model_id TEXT NOT NULL, approach TEXT NOT NULL, correction TEXT NOT NULL,
 evidence_json TEXT NOT NULL, occurrence_count INTEGER NOT NULL DEFAULT 1,
 last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS benchmarks(
 benchmark_id TEXT PRIMARY KEY, project TEXT NOT NULL, workload TEXT NOT NULL,
 objective TEXT NOT NULL, fixture_ref TEXT NOT NULL, evaluator_ref TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1, metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_queue(
 work_id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE, project TEXT NOT NULL,
 workload TEXT NOT NULL, objective TEXT NOT NULL, prompt TEXT NOT NULL, context TEXT NOT NULL,
 evaluator_json TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL CHECK(status IN ('QUEUED','LEASED','VERIFIED','FAILED','EXHAUSTED')),
 attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
 lease_until TEXT, result_experiment_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS attempts_by_experiment ON attempts(experiment_id,round_number,gate_score);
CREATE INDEX IF NOT EXISTS calls_by_day ON provider_calls(adapter,created_at);
CREATE INDEX IF NOT EXISTS observations_by_model ON model_observations(model_id,observed_at);
CREATE INDEX IF NOT EXISTS failures_by_fingerprint ON failure_patterns(failure_fingerprint,occurrence_count);
CREATE INDEX IF NOT EXISTS queue_by_readiness ON work_queue(status,priority,created_at);
"""


class ExperimentStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(SCHEMA)
        attempt_columns = {
            row[1] for row in self.connection.execute("PRAGMA table_info(attempts)")
        }
        if "gate_checks_json" not in attempt_columns:
            self.connection.execute(
                "ALTER TABLE attempts ADD COLUMN gate_checks_json TEXT NOT NULL DEFAULT '[]'"
            )
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def start(self, experiment_id: str, request: ExperimentRequest) -> None:
        payload = asdict(request)
        payload["required_capabilities"] = sorted(request.required_capabilities)
        payload["policy"]["allowed_tiers"] = sorted(str(item) for item in request.policy.allowed_tiers)
        payload["policy"]["allowed_adapters"] = sorted(request.policy.allowed_adapters)
        payload["policy"]["privacy_class"] = str(request.policy.privacy_class)
        self.connection.execute(
            "INSERT INTO experiments(experiment_id,objective,workload,benchmark_id,request_json,status) VALUES(?,?,?,?,?,?)",
            (experiment_id, request.objective, request.workload, request.benchmark_id, json.dumps(payload, sort_keys=True), "RUNNING"),
        )
        self.connection.commit()

    def record_candidate(self, candidate: Candidate) -> None:
        c = candidate.completion
        self.connection.execute(
            """INSERT INTO attempts(candidate_id,experiment_id,round_number,approach,adapter,model_id,
               output_hash,output_text,prompt_tokens,completion_tokens,latency_ms,cost_usd)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (candidate.candidate_id, candidate.experiment_id, candidate.round_number, candidate.approach,
             c.adapter, c.model_id, candidate.output_hash, c.text, c.prompt_tokens,
             c.completion_tokens, c.latency_ms, c.cost_usd),
        )
        self.connection.commit()

    def record_gate(self, candidate_id: str, result: GateResult) -> None:
        self.connection.execute(
            """UPDATE attempts SET gate_passed=?,gate_score=?,gate_summary=?,gate_checks_json=?
                 WHERE candidate_id=?""",
            (int(result.passed), result.score, result.summary,
             json.dumps(result.checks, ensure_ascii=False, sort_keys=True), candidate_id),
        )
        self.connection.commit()

    def record_critique(self, critique: Critique) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO critiques VALUES(?,?,?,?)",
            (critique.candidate_id, critique.critic_model_id, critique.findings_hash, critique.text),
        )
        self.connection.commit()

    def record_provider_call(
        self, *, call_id: str, experiment_id: str, purpose: str, requested_model_id: str,
        adapter: str, success: bool, served_model_id: str | None = None, latency_ms: int = 0,
        prompt_tokens: int = 0, completion_tokens: int = 0, cost_usd: float = 0.0,
        error: str | None = None,
    ) -> None:
        self.connection.execute(
            "INSERT INTO provider_calls VALUES(?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (call_id, experiment_id, purpose, requested_model_id, served_model_id, adapter,
             int(success), latency_ms, prompt_tokens, completion_tokens, cost_usd, error),
        )
        self.connection.commit()

    def remote_calls_today(self) -> int:
        return int(self.connection.execute(
            "SELECT count(*) FROM provider_calls "
            "WHERE adapter!='local' "
            "AND date(created_at, 'localtime')=date('now', 'localtime')"
        ).fetchone()[0])

    def observe_models(self, models: list[ModelSpec]) -> None:
        observed_at = datetime.now(UTC).isoformat(timespec="microseconds")
        rows = [(
            observed_at, model.model_id, model.adapter, str(model.cost_tier), int(model.preview), int(model.available),
            model.context_length, json.dumps(sorted(model.capabilities)), json.dumps(model.metadata, sort_keys=True),
        ) for model in models]
        self.connection.executemany(
            """INSERT OR REPLACE INTO model_observations(observed_at,model_id,adapter,cost_tier,preview,available,
               context_length,capabilities_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        self.connection.commit()

    def latest_models(self, adapter: str = "openrouter") -> list[ModelSpec]:
        latest = self.connection.execute(
            "SELECT max(observed_at) FROM model_observations WHERE adapter=?", (adapter,)
        ).fetchone()[0]
        if not latest:
            return []
        rows = self.connection.execute(
            """SELECT model_id,adapter,cost_tier,preview,available,context_length,
                      capabilities_json,metadata_json
                 FROM model_observations WHERE adapter=? AND observed_at=? ORDER BY model_id""",
            (adapter, latest),
        )
        return [ModelSpec(
            model_id=row[0], adapter=row[1], cost_tier=CostTier(row[2]), preview=bool(row[3]),
            available=bool(row[4]), context_length=row[5],
            capabilities=frozenset(json.loads(row[6])), metadata=json.loads(row[7]),
        ) for row in rows]

    def latest_model_ids(self, cost_tier: str) -> set[str]:
        return {model.model_id for model in self.latest_models() if str(model.cost_tier) == cost_tier}

    def record_catalogue_events(self, changes: dict[str, list[str]]) -> int:
        rows = []
        observed_at = datetime.now(UTC).isoformat(timespec="microseconds")
        for event_type, model_ids in sorted(changes.items()):
            for model_id in model_ids:
                event_id = hashlib.sha256(
                    f"{observed_at}\0{event_type}\0{model_id}".encode("utf-8")
                ).hexdigest()
                rows.append((event_id, event_type, model_id, "{}", observed_at))
        self.connection.executemany("INSERT INTO catalogue_events VALUES(?,?,?,?,?)", rows)
        self.connection.commit()
        return len(rows)

    def finish(self, experiment_id: str, status: str, reason: str) -> None:
        self.connection.execute(
            "UPDATE experiments SET status=?,stop_reason=?,finished_at=CURRENT_TIMESTAMP WHERE experiment_id=?",
            (status, reason, experiment_id),
        )
        self.connection.commit()

    def register_benchmark(
        self, benchmark_id: str, project: str, workload: str, objective: str,
        fixture_ref: str, evaluator_ref: str, metadata: dict | None = None,
    ) -> bool:
        values = (
            benchmark_id, project, workload, objective, fixture_ref, evaluator_ref,
            json.dumps(metadata or {}, sort_keys=True),
        )
        existing = self.connection.execute(
            """SELECT benchmark_id,project,workload,objective,fixture_ref,evaluator_ref,metadata_json
                 FROM benchmarks WHERE benchmark_id=?""",
            (benchmark_id,),
        ).fetchone()
        if existing:
            if tuple(existing) == values:
                return False
            raise ValueError(f"benchmark {benchmark_id} already exists and is immutable")
        self.connection.execute(
            "INSERT INTO benchmarks VALUES(?,?,?,?,?,?,1,?)", values,
        )
        self.connection.commit()
        return True

    def get_benchmark(self, benchmark_id: str) -> dict:
        self.connection.row_factory = sqlite3.Row
        row = self.connection.execute(
            "SELECT * FROM benchmarks WHERE benchmark_id=? AND active=1", (benchmark_id,)
        ).fetchone()
        if not row:
            raise KeyError(benchmark_id)
        return dict(row)

    def record_solution_pattern(self, experiment_id: str, workload: str, objective: str) -> None:
        row = self.connection.execute(
            """SELECT approach,model_id,gate_score,gate_summary,candidate_id FROM attempts
               WHERE experiment_id=? AND gate_passed=1 ORDER BY gate_score DESC LIMIT 1""",
            (experiment_id,),
        ).fetchone()
        if not row:
            return
        problem = hashlib.sha256(f"{workload}\0{objective}".encode()).hexdigest()
        pattern_id = hashlib.sha256(f"{problem}\0{row[0]}\0{row[1]}".encode()).hexdigest()
        evidence = json.dumps({"experiment_id": experiment_id, "candidate_id": row[4], "score": row[2], "gate": row[3]}, sort_keys=True)
        self.connection.execute(
            """INSERT INTO solution_patterns(pattern_id,workload,problem_fingerprint,approach,model_id,evidence_json)
               VALUES(?,?,?,?,?,?) ON CONFLICT(pattern_id) DO UPDATE SET
               success_count=success_count+1,last_used_at=CURRENT_TIMESTAMP,evidence_json=excluded.evidence_json""",
            (pattern_id, workload, problem, row[0], row[1], evidence),
        )
        self.connection.commit()

    def record_failure_pattern(self, experiment_id: str, workload: str, objective: str) -> None:
        row = self.connection.execute(
            """SELECT approach,model_id,gate_summary,candidate_id,output_hash,gate_checks_json FROM attempts
               WHERE experiment_id=? ORDER BY gate_score DESC,round_number DESC LIMIT 1""",
            (experiment_id,),
        ).fetchone()
        if not row:
            return
        correction = json.dumps({
            "summary": row[2] or "unknown gate failure",
            "checks": json.loads(row[5] or "[]"),
        }, ensure_ascii=False, sort_keys=True)
        failure = hashlib.sha256(f"{workload}\0{objective}\0{correction}".encode()).hexdigest()
        failure_id = hashlib.sha256(f"{failure}\0{row[1]}\0{row[0]}".encode()).hexdigest()
        evidence = json.dumps({"experiment_id": experiment_id, "candidate_id": row[3], "output_hash": row[4]}, sort_keys=True)
        self.connection.execute(
            """INSERT INTO failure_patterns(failure_id,workload,failure_fingerprint,model_id,approach,correction,evidence_json)
               VALUES(?,?,?,?,?,?,?) ON CONFLICT(failure_id) DO UPDATE SET
               occurrence_count=occurrence_count+1,last_seen_at=CURRENT_TIMESTAMP,evidence_json=excluded.evidence_json""",
            (failure_id, workload, failure, row[1], row[0], correction, evidence),
        )
        self.connection.commit()

    def reusable_experience(self, workload: str, objective: str, limit: int = 5) -> dict:
        problem = hashlib.sha256(f"{workload}\0{objective}".encode()).hexdigest()
        solutions = [dict(zip(
            ("approach", "model_id", "success_count", "evidence_json"), row
        )) for row in self.connection.execute(
            """SELECT approach,model_id,success_count,evidence_json FROM solution_patterns
               WHERE problem_fingerprint=? ORDER BY success_count DESC,last_used_at DESC LIMIT ?""",
            (problem, limit),
        )]
        failures = [dict(zip(
            ("approach", "model_id", "correction", "occurrence_count", "evidence_json"), row
        )) for row in self.connection.execute(
            """SELECT approach,model_id,correction,occurrence_count,evidence_json FROM failure_patterns
               WHERE workload=? ORDER BY occurrence_count DESC,last_seen_at DESC LIMIT ?""",
            (workload, limit),
        )]
        return {"successful_patterns": solutions, "failure_patterns": failures}

    def scoreboard(self, benchmark_id: str | None = None) -> list[dict]:
        self.connection.row_factory = sqlite3.Row
        rows = self.connection.execute(
            """SELECT a.model_id,a.adapter,count(*) AS candidate_attempts,
                      sum(CASE WHEN a.gate_passed=1 THEN 1 ELSE 0 END) AS verified_candidates,
                      round(avg(coalesce(a.gate_score,0)),4) AS mean_gate_score,
                      round(avg(a.latency_ms),1) AS mean_latency_ms,
                      sum(a.prompt_tokens+a.completion_tokens) AS total_tokens,
                      round(sum(a.cost_usd),6) AS total_cost_usd,
                      count(DISTINCT a.experiment_id) AS experiments
                 FROM attempts a JOIN experiments e USING(experiment_id)
                WHERE (? IS NULL OR e.benchmark_id=?)
                GROUP BY a.model_id,a.adapter
                ORDER BY mean_gate_score DESC,verified_candidates DESC,total_cost_usd ASC""",
            (benchmark_id, benchmark_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def experiment_exists(self, experiment_id: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM experiments WHERE experiment_id=?", (experiment_id,)
        ).fetchone() is not None

    def study_scoreboard(self, study_id: str) -> list[dict]:
        self.connection.row_factory = sqlite3.Row
        experiment_rows = self.connection.execute(
            """SELECT e.*,
                      count(a.candidate_id) AS candidate_attempts,
                      max(coalesce(a.gate_score,0)) AS best_gate_score,
                      sum(a.prompt_tokens+a.completion_tokens) AS total_tokens,
                      sum(a.cost_usd) AS candidate_cost_usd,
                      sum(a.latency_ms) AS candidate_latency_ms
                 FROM experiments e LEFT JOIN attempts a USING(experiment_id)
                GROUP BY e.experiment_id ORDER BY e.started_at,e.experiment_id"""
        ).fetchall()
        groups: dict[str, dict] = {}
        for row in experiment_rows:
            request = json.loads(row["request_json"])
            if request.get("study_id") != study_id:
                continue
            arm_id = request.get("study_arm_id")
            group = groups.setdefault(arm_id, {
                "study_id": study_id, "arm_id": arm_id, "runs": 0, "verified_runs": 0,
                "candidate_attempts": 0, "remote_calls": 0, "total_tokens": 0,
                "total_cost_usd": 0.0, "candidate_latency_ms": 0,
                "best_gate_scores": [], "models": set(),
            })
            group["runs"] += 1
            group["verified_runs"] += int(row["status"] == "VERIFIED")
            group["candidate_attempts"] += int(row["candidate_attempts"] or 0)
            group["total_tokens"] += int(row["total_tokens"] or 0)
            group["total_cost_usd"] += float(row["candidate_cost_usd"] or 0.0)
            group["candidate_latency_ms"] += int(row["candidate_latency_ms"] or 0)
            group["best_gate_scores"].append(float(row["best_gate_score"] or 0.0))
            call_row = self.connection.execute(
                "SELECT count(*),coalesce(sum(cost_usd),0) FROM provider_calls WHERE experiment_id=?",
                (row["experiment_id"],),
            ).fetchone()
            group["remote_calls"] += int(call_row[0])
            group["models"].update(model_row[0] for model_row in self.connection.execute(
                "SELECT DISTINCT model_id FROM attempts WHERE experiment_id=?", (row["experiment_id"],)
            ))
        result = []
        for arm_id in sorted(groups):
            group = groups[arm_id]
            scores = group.pop("best_gate_scores")
            group["mean_best_gate_score"] = round(sum(scores) / max(len(scores), 1), 4)
            group["verification_rate"] = round(group["verified_runs"] / max(group["runs"], 1), 4)
            group["total_cost_usd"] = round(group["total_cost_usd"], 8)
            group["models"] = sorted(group["models"])
            result.append(group)
        return result

    def enqueue(
        self, *, work_id: str, idempotency_key: str, project: str, workload: str,
        objective: str, prompt: str, context: str, evaluator: dict,
        priority: int = 0, max_attempts: int = 3,
    ) -> bool:
        cursor = self.connection.execute(
            """INSERT OR IGNORE INTO work_queue(
               work_id,idempotency_key,project,workload,objective,prompt,context,evaluator_json,
               priority,status,max_attempts) VALUES(?,?,?,?,?,?,?,?,?,'QUEUED',?)""",
            (work_id, idempotency_key, project, workload, objective, prompt, context,
             json.dumps(evaluator, sort_keys=True), priority, max_attempts),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def lease_next(self, lease_minutes: int = 30) -> dict | None:
        self.connection.execute("BEGIN IMMEDIATE")
        self.connection.row_factory = sqlite3.Row
        row = self.connection.execute(
            """SELECT * FROM work_queue
               WHERE (status='QUEUED' OR (status='FAILED' AND attempts<max_attempts)
                      OR (status='LEASED' AND lease_until<CURRENT_TIMESTAMP))
               ORDER BY priority DESC,created_at,work_id LIMIT 1"""
        ).fetchone()
        if not row:
            self.connection.commit()
            return None
        self.connection.execute(
            """UPDATE work_queue SET status='LEASED',attempts=attempts+1,
               lease_until=datetime('now',?),updated_at=CURRENT_TIMESTAMP WHERE work_id=?""",
            (f"+{lease_minutes} minutes", row["work_id"]),
        )
        self.connection.commit()
        return dict(self.connection.execute("SELECT * FROM work_queue WHERE work_id=?", (row["work_id"],)).fetchone())

    def finish_work(self, work_id: str, *, verified: bool, experiment_id: str) -> None:
        row = self.connection.execute("SELECT attempts,max_attempts FROM work_queue WHERE work_id=?", (work_id,)).fetchone()
        if not row:
            raise KeyError(work_id)
        status = "VERIFIED" if verified else ("EXHAUSTED" if row[0] >= row[1] else "FAILED")
        self.connection.execute(
            """UPDATE work_queue SET status=?,result_experiment_id=?,lease_until=NULL,
               updated_at=CURRENT_TIMESTAMP WHERE work_id=?""",
            (status, experiment_id, work_id),
        )
        self.connection.commit()

    def experiment_attempts(self, experiment_id: str) -> list[dict]:
        self.connection.row_factory = sqlite3.Row
        attempts = []
        for row in self.connection.execute(
            "SELECT * FROM attempts WHERE experiment_id=? ORDER BY round_number,candidate_id", (experiment_id,)
        ):
            item = dict(row)
            item["gate_checks"] = json.loads(item.pop("gate_checks_json") or "[]")
            attempts.append(item)
        return attempts

    def experiment_critiques(self, experiment_id: str) -> list[dict]:
        self.connection.row_factory = sqlite3.Row
        return [dict(row) for row in self.connection.execute(
            """SELECT c.candidate_id,c.critic_model_id,c.findings_hash,c.critique_text
                 FROM critiques c JOIN attempts a USING(candidate_id)
                WHERE a.experiment_id=?
                ORDER BY a.round_number,c.candidate_id,c.critic_model_id,c.findings_hash""",
            (experiment_id,),
        )]
