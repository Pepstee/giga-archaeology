# First ECC-derived giga-user implementation decision

**Decision:** implement the staged status-field map first as a read-only
`giga.operator-status.v1` snapshot.

**Decision date:** 22 July 2026  
**Authority:** operator requested selection and subsequently authorised implementation.  
**Deployment state:** implemented as a repository-local, read-only compiler on 22 July 2026;
live runtime adapters remain intentionally unconnected.

## Why this wins

The refreshed SkillTree registry classifies **Monitoring & Alerting** as `partial`, backed by
`twin_core/health.py`, `twin_core/telegram_pipeline.py`, and `scripts/jarvis_telegram.py`, because
complete cross-service visibility is not proven. By contrast, **Agent Evaluation**, **Adversarial
Verification**, and evidence-backed report/provenance mechanisms are already `implemented`.

The status contract therefore fills a demonstrated gap instead of duplicating a strong subsystem.
It is also the safest useful first slice: it reads existing state, reports unknown signals as
unknown, and grants no authority to mutate sessions, trackers, or orchestrators.

## Comparative ranking

Scores are 1–5; higher is better. `Safety` means lower blast radius and easier rollback.

| Staged contract | Real gap | Downstream leverage | Immediate value | Safety | Testability | Total / 25 |
|---|---:|---:|---:|---:|---:|---:|
| Status/HUD field map | 5 | 5 | 5 | 5 | 5 | **25** |
| Adapter evidence contract | 4 | 5 | 4 | 5 | 5 | 23 |
| Selective deployment contract | 4 | 5 | 4 | 3 | 4 | 20 |
| Security negative-test specification | 3 | 4 | 3 | 5 | 5 | 20 |
| Evaluator negative-control contract | 2 | 4 | 3 | 5 | 5 | 19 |
| Import provenance contract | 2 | 4 | 3 | 5 | 5 | 19 |

## First implementation boundary

Build one deterministic read-only compiler with:

- module: `twin_core/operator_status.py`;
- CLI: `scripts/operator_status.py --json`;
- contract: `contracts/operator-status.v1.schema.json`;
- tests: `tests/test_operator_status.py`;
- fixture/output: `outputs/operator-status/latest.json`;
- evidence-map declaration for **Monitoring & Alerting** only after all required paths exist and
  the audit computes the intended status.

The compiler should consume existing evidence where available:

- control-plane health;
- SkillTree registry counts and evidence timestamp;
- active programme/workstream state;
- latest durable handoff/receipt state;
- ECC import/update status;
- repository dirtiness for in-scope repositories only.

## Required contract behaviour

1. Use stable sections derived from the staged map: `context`, `toolCalls`, `activeAgents`, `todos`,
   `checks`, `cost`, `risk`, `queueState`, `sessionControls`, and `sync`.
2. Every field declares `value`, `state`, `source`, and `observed_at` or uses an equivalent typed
   evidence envelope.
3. Missing data is `unknown` or `unavailable`, never `healthy` or zero.
4. `sessionControls` describes supported actions but performs none.
5. No network calls, tracker writes, process control, global config mutation, or orchestrator-repo
   writes.
6. Inputs are path-contained inside giga-user except for explicitly declared read-only external
   evidence.
7. Output is deterministic apart from an injected observation timestamp.
8. Invalid, stale, malformed, missing, or path-escaping evidence receives explicit negative tests.

## Acceptance gates

- schema validation passes;
- deterministic fixture test passes twice byte-for-byte with a fixed clock;
- missing-signal fixture renders `unknown`, not green;
- malformed and path-escape fixtures fail closed;
- existing giga-user test suite remains green;
- SkillTree audit is rerun;
- a human-readable summary and machine JSON agree on every state;
- no status is promoted solely because an installed skill, preview, or plan exists.

## What follows

The status compiler passed, and the **adapter evidence contract** was implemented second. The
adapter registry now supplies hashed, freshness-checked capability evidence to operator status
without executing manifest commands or granting authority. The selective deployment contract comes third;
it should not be implemented until status and adapter evidence can prove what an apply operation
would affect.
