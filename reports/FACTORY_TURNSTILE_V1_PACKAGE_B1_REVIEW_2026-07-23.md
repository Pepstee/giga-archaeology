# Factory Turnstile v1 — Package B1: independent review

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
Base commit: `90e37d324c4b60cfa3f4e7a7f92736fcb5dd6020`.

You are the sole writer. Do not spawn subagents, commit, touch production, DFI-05, JAA, another
worktree, or files outside:

```text
factory_control/__init__.py
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Preserve all 94 Package A tests. Implement independent review only; do not implement test
receipts, contexts, allocation certification, CLI or documentation.

## Contract

1. Extend initial state and validation with durable `reviews` and `receipts` lists. No deployed
   stage exists yet, so no migration is required; malformed/missing fields must fail closed.
2. Add `run_review(actor, command, verdict, work_weight=...)`.
3. Require:
   - a sealed candidate that still exactly matches the worktree;
   - a successful writer ledger entry for that exact candidate;
   - reviewer actor (`sonnet` or `codex`) different from that writer;
   - verdict exactly `pass` or `changes-requested`;
   - valid direct non-empty argv and positive finite weight;
   - no existing lease.
4. Record a UUID lease with actor/provider/role=`reviewer`, PID/start identity/PGID, command,
   candidate-before and intended verdict. Execute direct argv in the governed worktree, never via
   a shell, and preserve the real child exit code. Reuse Package A's safe launch, stop and recovery
   semantics rather than creating a weaker second process path.
5. Hash the candidate before and after review. Any mutation is a concurrency violation:
   record exact before/after hashes and exit code, seal the mutated candidate, clear only the
   matching lease, transition to `paused`, accept no review/ledger entry, and raise
   `TurnstileError`.
6. A non-zero review process pauses the stage and accepts no review or ledger entry. Return the
   exact non-zero exit code.
7. On exit zero with unchanged candidate:
   - append a durable review record bound to candidate, reviewer, writer, command, verdict,
     timestamp, lease UUID and exit code;
   - append one weighted reviewer work-ledger entry;
   - verdict `pass` transitions to `reviewed`;
   - verdict `changes-requested` transitions to `changes_requested`; a new writer turn must reseal
     before any later review or test.
8. `run_worker()` success must continue sealing a fresh candidate; historical review records may
   remain but never authorise a different candidate.
9. `status()` must report review count and the latest review verdict without mutating state.
10. Expand phase/state validation for `reviewed` and `changes_requested`; only `running` may carry
    a lease.

## Required tests

- reviewer must differ from exact candidate writer;
- no writer record, unsealed candidate, changed candidate, invalid verdict/argv/weight all refuse;
- live writer blocks review;
- review exit zero + pass records and transitions;
- exit zero + changes-requested records and requires reseal;
- non-zero preserves exact code and pauses without accepted review;
- review-time mutation records violation, accepts no review and pauses;
- review launch failure leaves no stranded lease;
- stop/recover work against a real review child;
- historical review never authorises a changed candidate;
- corrupt review/receipt state fails closed;
- all 94 Package A tests remain green.

Use Python 3.14 standard library only. Keep the complete controller under the 1,500-line ceiling
and its ratified feature boundary. Run only the focused unittest module, py_compile and
`git diff --check`. Report exact results, line count and unresolved risks; do not self-certify.
