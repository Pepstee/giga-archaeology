# Factory Turnstile v1 — Package C2 bounded repair

Work only in:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

You are the sole writer. Do not spawn agents, commit, touch production, DFI-05, JAA, another
worktree, or files outside:

```text
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Preserve the current 380 passing tests and the complete C2 contract. Repair only the independently
reviewed gaps below. The production ceiling remains **2,000 physical lines** across
`factory_control/*.py`; current production is 1,986, so delete/refactor duplication if needed.
Do not hide logic in tests and do not add an abstraction layer.

Exact starting candidate:

```text
81a04a543551b2dd8303722874b6151be94cebccefa94192c5490e20b91635f9  factory_control/turnstile.py
6e00d36e2e03c5de746681dcf7c8aabf6f9184269efc826b56553d0e8ca8374b  tests/test_factory_turnstile.py
```

## Required repairs

1. Return `required_suite_ids` in the same sorted canonical order stored in the certificate. Add a
   regression that directly compares the unsorted-call return to certificate content.
2. Deep state validation must restrict ledger actors to `sonnet|codex` and bind:
   `sonnet -> claude`, `codex -> codex`. Add inverted-pair and unknown-actor regressions.
3. Deep state validation must bind every persisted review to:
   - a matching reviewer ledger entry by UUID, role, actor, candidate and weight; and
   - a successful writer ledger entry for the review's recorded writer and candidate.
   Add missing/mismatched reviewer-ledger and missing writer-ledger regressions. Preserve valid
   historical candidate reviews.
4. Cumulative allocation overflow must fail closed with `CorruptStateError`, never return
   `Infinity`, `NaN`, or leak `ValueError`. Add a two-very-large-finite-weights regression.
5. Recompute the on-disk candidate after receipt/allocation verification and immediately before
   certificate construction/persistence. Refuse if it moved. Add a deterministic injected
   mid-decision mutation regression.
6. Add a regression for `_append_event()` failing after certificate and certified-state
   persistence. Do not pretend separate files are transactional:
   - the first call must raise loudly;
   - the complete content-addressed certificate and `phase="certified"` remain truthful;
   - no success event may be asserted by the injected pre-write failure;
   - an exact retry must verify/reuse the certificate and append `certification_reused`.
   Keep this as an explicitly tested crash-recovery residual, not a rollback that can create a
   false event or destroy a valid certificate.
7. Replace the trivial single-receipt “multi-receipt selection” test with a real state containing
   two distinct valid receipts for the same suite and prove the lexically lowest key is selected.
8. Correct any mislabeled no-pass-review test so it reaches the intended guard.

Do not add certificate pointers, state schema fields, schedulers, retries, routing, provider
selection, token logic, CLI or documentation in this package.

Run only:

```bash
python3 -m unittest tests.test_factory_turnstile
python3 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  tests/test_factory_turnstile.py
git diff --check
```

Report exact tests, production lines, hashes and residual risks. Do not self-certify or commit.
