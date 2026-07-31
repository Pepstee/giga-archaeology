# Factory Turnstile v1 — Package C2 allocation and certification

Work only in:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Base commit:

`5f57e59ce08691d2fb42426c9846fe39572e0870`

You are the sole writer. Do not spawn subagents, commit, touch production, DFI-05, JAA, another
worktree, or files outside:

```text
factory_control/__init__.py
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Preserve all 319 tests. Implement weighted allocation reporting and the explicit certification gate
only. Do not implement CLI, autonomous scheduling, retries, routing, prompt generation, model
selection or documentation.

## Public API

Add:

```python
allocation_report() -> dict

certify(required_suite_ids: list[str]) -> dict
```

`allocation_report()` must return a stable JSON-compatible report with at least:

```text
claude_weight
codex_weight
total_weight
claude_basis_points
codex_basis_points
target_claude_basis_points
tolerance_basis_points
within_policy
```

For a zero total, both basis-point fields must be `None` and `within_policy` must be `False`.

`certify()` must return a stable summary containing at least:

```text
candidate
certificate_path
required_suite_ids
review_lease_uuids
receipt_keys
allocation
reused
```

## Allocation contract

- Calculate from the persisted successful writer/reviewer ledger only. Host tester receipts are not
  model work and never enter the allocation denominator.
- Provider `claude` is Sonnet work and provider `codex` is Codex work.
- Sum the persisted positive finite `weight` values. Do not infer work from token estimates, elapsed
  time, file counts, commits or prose.
- Count the full stage ledger because the user requires a 30/70 split over substantive collaboration,
  including repair and review work across candidate revisions.
- Compute deterministic integer basis points summing to exactly 10,000 when total weight is nonzero.
- Policy is Claude 7,000 basis points with a ±1,000 basis-point tolerance, inclusive. Certification
  therefore accepts 6,000 through 8,000 Claude basis points.
- Label these values as declared weighted work; do not imply that the controller measured tokens or
  cognitive effort.
- Unknown providers or malformed ledger data fail closed through state validation.

## Certification contract

Hold the controller lock continuously for the complete certification decision and persistence.
Certification must fail unless all of the following are true at the same locked decision:

1. the stage is initialized, has no lease and is in `reviewed` phase (or already `certified` for an
   exact idempotent replay);
2. the on-disk candidate exactly matches the sealed current candidate;
3. at least one accepted `pass` review exists for that exact candidate and is independent from the
   successful writer it reviewed;
4. `required_suite_ids` is a non-empty list of unique, non-empty strings;
5. every required suite ID has an exit-zero, valid receipt bound to the exact current candidate;
6. every selected receipt's canonical receipt bytes and complete output evidence still exist and
   verify descriptor-bound against their persisted hashes;
7. allocation is within the inclusive 6,000–8,000 Claude basis-point policy.

For multiple passing receipts with one suite ID, select deterministically by sorted canonical
receipt key. Do not silently accept a receipt for an older candidate, another suite ID, invalid or
nonzero execution.

Create canonical compact certificate JSON containing only:

- schema version and stage;
- exact candidate hash;
- sorted required suite IDs;
- deterministically selected receipt keys;
- sorted accepted current-candidate pass-review lease UUIDs;
- the exact allocation report.

Do not include timestamps, absolute paths, command text, model prose or mutable host metadata.
Compute the certificate SHA-256 over the exact canonical bytes and install it durably under
`control_dir/evidence/` with an fsynced same-directory temporary file and atomic no-clobber
semantics. An exact existing certificate is reused; a symlinked/tampered/mismatched collision fails
closed and is never overwritten.

Only after verified certificate persistence:

- transition state to `phase="certified"`;
- append a truthful `certification_success` or `certification_reused` event;
- return the summary.

Any failed gate or persistence error must not leave `phase="certified"`, a success event, or a
referenced partial certificate. A crash may leave an unreferenced exact content-addressed artifact;
the next call may verify and reuse it.

Extend deep state validation so:

- `certified` is a valid phase requiring a non-null candidate and no lease;
- malformed/unknown ledger providers fail closed;
- existing phase/lease/candidate invariants remain intact.

## Required tests

Cover at least:

1. zero, exact 70/30, inclusive 60/40 and 80/20 boundary, and outside-policy allocation;
2. deterministic basis-point sum and host-test exclusion;
3. success with independent review and all exact current-candidate suite evidence;
4. deterministic ordering and exact certificate-content/hash binding;
5. idempotent exact certificate reuse without rewrite;
6. invalid/empty/duplicate required suite IDs;
7. wrong phase, active lease, candidate drift, absent/non-pass/non-independent review;
8. missing, invalid, nonzero, old-candidate or wrong-suite receipt;
9. missing/tampered/symlinked/swapped receipt or output evidence;
10. allocation outside policy;
11. collision mismatch/symlink and injected write/link/fsync failure;
12. no false certified state/event or temporary file after failure;
13. corrupt provider/weight/phase rejection;
14. all previous 319 tests remain green.

## Budget and gates

Complete production after C2 must be at most **2,000 physical lines** across:

```text
factory_control/*.py
scripts/factory_turnstile.py
```

Do not hide production logic in tests. Prefer factoring the existing receipt-evidence verification
into one private helper reused by both `run_test()` and `certify()` over duplicating it.

Run only:

```bash
python3 -m unittest tests.test_factory_turnstile
python3 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  tests/test_factory_turnstile.py
git diff --check
```

Report the exact test count, production line count, changed files and residual risks. Do not
self-certify or commit.
