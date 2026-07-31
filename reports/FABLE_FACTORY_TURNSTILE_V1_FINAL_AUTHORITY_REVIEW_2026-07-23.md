# Fable authority gate — Factory Turnstile v1 complete candidate

You are the milestone authority. Perform an adversarial, deletion-focused, whole-system review.
Read only; do not edit, run tests, spawn agents, commit, install, or inspect unrelated worktrees.

Candidate worktree:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Branch/head:

`factory/turnstile-v1 @ 938b42d392ff4ac4df39492ff28f5dc398192d45`

Read completely:

```text
factory_control/__init__.py
factory_control/turnstile.py
scripts/factory_turnstile.py
tests/test_factory_turnstile.py
tests/test_factory_turnstile_cli.py
FACTORY_TURNSTILE.md
reports/FACTORY_TURNSTILE_PACKAGE_A_CERTIFICATION_2026-07-23.md
reports/FACTORY_TURNSTILE_PACKAGE_B1_CERTIFICATION_2026-07-23.md
reports/FACTORY_TURNSTILE_PACKAGE_B2_CERTIFICATION_2026-07-23.md
reports/FACTORY_TURNSTILE_PACKAGE_C1_CERTIFICATION_2026-07-23.md
reports/FACTORY_TURNSTILE_PACKAGE_C2_CERTIFICATION_2026-07-23.md
reports/FACTORY_TURNSTILE_PACKAGE_C3_CERTIFICATION_2026-07-23.md
reports/FACTORY_TURNSTILE_V1_SCOPE_BUDGET_ADDENDUM_2_2026-07-23.md
```

Verified host evidence:

- 431 post-commit tests pass;
- core/CLI/tests compile;
- diff check and worktree cleanliness pass;
- production physical lines:
  - `factory_control/__init__.py`: 17
  - `factory_control/turnstile.py`: 1,983
  - `scripts/factory_turnstile.py`: 151
  - total: 2,151 against final hard ceiling 2,200;
- CLI mode `0755`;
- production orchestrator-v3 remains STOP-armed and systemd inactive;
- no package writer and reviewer ran concurrently.

## Purpose and boundary

This controller is intended to solve the observed inter-model concurrency failure before resuming
orchestrator-v3 DFI work:

- exactly one model/test operation at a time;
- immutable candidate hand-off;
- independent Sonnet/Codex review;
- truthful exact test reuse;
- bounded deterministic context packs;
- declared weighted 70% Claude / 30% Codex policy with 60–80% acceptance band;
- explicit certification and crash recovery;
- no scheduler, planner, retries, routing, prompts, token policy, daemon or autonomous loop.

It will be fast-forwarded into the authoritative but dirty
`/home/gutua/software-factory/giga-user` checkout only if this gate passes. That checkout's unrelated
dirty memory/reports must remain untouched. It will then govern the isolated DFI-05 worktree before
production activation.

## Required assessment

Assess the implementation, not the certificates' prose. Look for:

1. any path that allows two live writers/reviewers/testers or clears a live/ambiguous lease;
2. PID/start-identity/PGID reuse, stop/recover races, launch/finalisation crash windows and process
   group escape;
3. candidate mutation between stages or during review/test/certification;
4. false or unauthenticated test reuse, incomplete output, receipt/path swaps or stale runtime keys;
5. context traversal, symlink/identity races, unbounded reads, nondeterministic packs or overwrite;
6. forged/malformed ledger/review state, inaccurate 30/70 accounting or certification bypass;
7. certificate collision, partial persistence, misleading state/event ordering and audit gaps;
8. CLI shell injection, argv loss, exit-code lies, unsupported options or documentation mismatch;
9. corruption handling, state invariants, event truthfulness and WSL/Linux assumptions;
10. redundant branches/helpers/tests, code that can be deleted safely, and whether the 2,151 lines
    indicate hidden entropy;
11. tests that assert mocks instead of real behaviour, missing adversarial drills, and the mocked
    file `ResourceWarning`;
12. whether installing into dirty authoritative `giga-user` by a fast-forward from common base
    `82cb47ef82d6973c08513686bcca6ed0469418a7` is safe when all candidate paths are new there;
13. whether this controller is sufficient to settle DFI-05 sequentially without silently becoming
    a second orchestrator.

Cybersecurity attacks by an external adversary are not the current priority. Prioritise accidental
agent damage, concurrency, false evidence, crash consistency, observability, auditability and
quality loss.

## Verdict format

Return one:

- `PASS FOR CONTROLLED INSTALLATION`
- `CHANGES REQUIRED`
- `STOP`

For each finding, provide severity, exact location, concrete failure mechanism, minimum regression
and smallest safe repair. Distinguish:

- installation blockers;
- pre-activation blockers;
- honest residuals;
- optional future improvements.

End with the exact safe next sequence. Do not waive a defect because tests pass. Do not recommend
scope expansion unless the existing boundary cannot safely meet its purpose.
