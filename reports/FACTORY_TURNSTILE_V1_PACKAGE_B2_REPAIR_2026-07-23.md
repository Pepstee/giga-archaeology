# Factory Turnstile v1 — Package B2 focused repair

Work only in:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Base commit remains:

`c95dd91f69c20e2acfea0c2de351e28be710bccc`

The current uncommitted B2 candidate passes 233 tests. Preserve it. You are the sole writer for
this repair. Do not spawn subagents, commit, touch production, DFI-05, JAA, another worktree, or
files outside:

```text
factory_control/__init__.py
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Fix only the independently identified B2 gaps below. Add direct regressions for every fix.

## R1 — canonical receipt evidence is not authenticated

Current reuse checks that the receipt path is a regular file, but it never reads the canonical
receipt file or compares its bytes/content with the persisted receipt record. A replaced or
tampered receipt file can therefore still be reused when the output log is intact.

Before reuse, require both:

- the receipt file is canonical JSON for the exact in-state receipt record; and
- its complete bytes/content exactly match the expected canonical representation.

Missing, malformed, non-canonical, tampered, or symlinked receipt evidence must cause a fresh test
execution, never reuse. Do not silently repair or rewrite the old evidence.

Deep state validation must also:

- require `key` and `output_sha256` to be lowercase 64-character hexadecimal digests;
- recompute the canonical key from candidate, suite ID, suite kind, argv and runtime and require an
  exact match;
- require `ts_end >= ts_start`;
- require tester leases to have actor/provider `host`;
- reject duplicate evidence paths or otherwise ambiguous receipt identities if they can make
  evidence binding non-unique.

Keep validation proportional and deterministic; do not create a general persistence framework.

## R2 — full-suite authorisation is truthy rather than exact

`suite_kind="full"` must require `authorize_full is True`. Values such as `1`, non-empty strings,
or arbitrary truthy objects must be rejected.

## R3 — post-launch failures can strand the lease

After `Popen` succeeds, failures while recording PID metadata, flushing/fsyncing/hashing evidence,
writing the canonical receipt, or persisting the final state must not leave a running child or a
stranded `running` tester lease.

Implement bounded fail-closed cleanup:

- if the child may still be alive, terminate its exact process group and reap it;
- under the lock, clear only the matching lease, seal the current candidate when computable, and
  leave the controller paused;
- append a truthful failure event;
- preserve and re-raise the original exception;
- never clear or mutate a replacement lease.

Exercise at least PID-record failure, output fsync/hash failure, and receipt-write/state-write
failure through injected failures. Tests must prove no live child and no matching stranded lease.

## R4 — explicit stop must deterministically leave paused

The current stop/test race allows `reviewed` when test finalisation wins the final lock. That
contradicts `stop()`'s public contract: an explicit successful stop leaves the stage paused.

Resolve the race without adding a scheduler or queue. If the original lease completed and cleared
before `stop()` reacquires the lock, and no replacement lease exists, `stop()` must still seal the
current candidate and persist `paused`. If a replacement lease exists, continue to fail closed as
a concurrency violation. The test caller may return a non-zero receipt or a preempted empty
receipt, but final durable controller state after successful `stop()` must be paused with no live
lease.

Add deterministic race coverage for both final-lock orderings.

## Gates

Run only:

```bash
python3 -m unittest tests.test_factory_turnstile
python3 -m py_compile factory_control/turnstile.py tests/test_factory_turnstile.py
git diff --check
```

Report exact test count, changed line count, production physical line count, and residual risks.
Do not self-certify and do not commit.
