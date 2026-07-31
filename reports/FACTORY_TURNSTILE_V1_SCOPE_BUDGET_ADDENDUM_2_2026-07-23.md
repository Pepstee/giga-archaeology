# Factory Turnstile v1 — final scope and budget addendum

Date: 2026-07-23  
Certified base for remaining work: `0146bb23cb5665b520e4b4a91c263ebb9880edd2`

## Verdict

The complete-controller production ceiling is revised once, finally, from 1,500 to **2,200
physical lines** across:

```text
factory_control/*.py
scripts/factory_turnstile.py
```

This is a ceiling, not a target. No further upward revision is permitted without a new independent
architecture review and explicit stop.

## Evidence for revision

The 1,500-line estimate was set before B2 adversarial review. B2 reached 1,706 production lines only
after direct regressions proved and repaired seven correctness/safety gaps:

1. canonical receipt-file authentication;
2. literal-boolean full-suite authorisation;
3. post-launch evidence and state cleanup;
4. deterministic paused state after stop/finalisation races;
5. descriptor/path swap resistance;
6. bounded streaming of large output evidence;
7. PID/start-identity/PGID reuse and unkillable-child handling.

Removing those checks to satisfy an estimate would weaken the reason the controller exists. Moving
them into tests or scripts would be dishonest accounting.

The remaining original contract is bounded context packs, weighted work-allocation certification
and a thin CLI. A 494-line remainder is sufficient when implemented without new orchestration.

## Package ceilings

| Package | Outcome | Complete production ceiling after package |
|---|---|---:|
| C1 | Deterministic bounded context packs | 1,840 |
| C2 | Allocation reporting and certification gate | 2,000 |
| C3 | Thin CLI and documentation | 2,200 |

Exceeding any package ceiling is a stop-and-review event. Deletions and shared helpers count
normally; production logic may not be displaced into tests, generated files or documentation.

## Immutable scope boundary

The controller may do only:

- one stage at a time;
- one exclusive model/test operation at a time;
- exact candidate sealing and hand-off;
- independent review;
- truthful single-flight test receipts;
- bounded context packs;
- weighted Claude/Codex work reporting;
- explicit certification, pause, stop and recovery;
- thin command-line exposure of those operations.

It must not acquire queues, autonomous scheduling, retries, task decomposition, model routing,
prompt generation, daemon loops, project planning, plugin systems, provider selection, token
optimisation policy or general orchestration. Those remain orchestrator-v3 responsibilities.

## Final entropy gate

After C3, perform one deletion-focused review before installation. It may remove duplication but
must preserve all behavioural tests. The final certificate must report physical lines, public
commands, state fields and every remaining non-goal so this controller cannot quietly become a
second orchestrator.
