# Factory Turnstile v1 — Package C2 independent Sonnet review

Read only:

```text
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/factory_control/turnstile.py
/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile/tests/test_factory_turnstile.py
```

Do not edit, run tests, spawn agents, commit, or inspect another worktree. Review the exact candidate:

```text
81a04a543551b2dd8303722874b6151be94cebccefa94192c5490e20b91635f9  factory_control/turnstile.py
6e00d36e2e03c5de746681dcf7c8aabf6f9184269efc826b56553d0e8ca8374b  tests/test_factory_turnstile.py
```

Base commit: `5f57e59ce08691d2fb42426c9846fe39572e0870`.

Host evidence: 380 tests passed; compile and diff checks passed; production is 1,986 physical
lines against a 2,000-line cap.

Independently assess every C2 requirement in:

`/mnt/c/Users/gutua/FACTORY_TURNSTILE_V1_PACKAGE_C2_ALLOCATION_CERTIFICATION_2026-07-23.md`

Inspect the full relevant implementation and tests, not only the diff. Explicitly resolve these
Codex review hypotheses:

1. whether ledger validation must bind `actor="sonnet"` to `provider="claude"` and
   `actor="codex"` to `provider="codex"` so allocation cannot be silently inverted;
2. whether accepted pass reviews must be linked to matching successful writer and reviewer ledger
   entries, rather than trusting review records in isolation;
3. whether cumulative finite weights can overflow to infinity and make allocation reporting
   non-total or nondeterministic;
4. whether `certify()` must recompute the candidate after evidence verification and immediately
   before certificate persistence to detect an external mid-decision mutation;
5. whether an `_append_event()` failure after `_write_state(phase="certified")` violates the
   fail-closed persistence contract, and what bounded repair is possible without pretending that
   separate files are one transaction;
6. whether returning caller-order `required_suite_ids` violates the stable-summary contract when
   certificate content is sorted;
7. whether a `certified` state with no durable pointer to its certificate is sufficiently
   observable/auditable, or requires a bounded state reference;
8. path/symlink/identity safety of receipt and certificate evidence, including intermediate
   components;
9. deterministic receipt choice when the lexically first candidate has bad evidence but another
   valid receipt exists;
10. any untested crash window, false certification, policy bypass, scope creep or regression not
    listed above.

Treat the line cap as binding. Do not recommend broad abstractions or a second orchestrator.

Return:

- `PASS` only if no correctness/contract gap exists; otherwise `CHANGES REQUIRED`;
- each finding ranked critical/high/medium/low, with exact code location and a minimal regression;
- the smallest bounded repair strategy;
- any honest residual that cannot be closed under the separate state/event/artifact files.
