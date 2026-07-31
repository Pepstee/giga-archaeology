# Factory Turnstile v1 — Package B1 certification

**Verdict:** B1 independent-review enforcement certified. B2 may begin.

## Frozen scope

- state extensions for reviews and future receipts;
- reviewer must differ from the exact candidate's successful writer;
- exact sealed-candidate precondition;
- direct, exclusive reviewer child lifecycle;
- review-time mutation detection and fail-closed pause;
- truthful non-zero/interruption handling;
- accepted `pass` and `changes-requested` records;
- weighted reviewer ledger entries;
- review-aware status and phase validation;
- deep candidate, ledger and accepted-review state validation;
- shared child launch/wait/failure helpers.

## Sealed evidence

- pre-review candidate:
  `e035870fd6979a2dc50a70aed65ec861c18ffdefda54dcb99b02dd18d9282fc3`
- source SHA-256:
  `b8fc2f79df2cdacdcc6fab9c78c256ab0d497068cf8949b7e5bc28a77c1eab9a`
- test SHA-256:
  `f5dbb260ea1f5011c2324346546c7b63a578c228753a2630a31c385e152d8319`
- independent final suite: **183 passed**, 0 failed
- `py_compile` and `git diff --check`: passed
- production size: **1,067 physical lines** including exports
- hashes stable across independent execution.

## Collaboration evidence

Sonnet implemented B1, then completed separate persisted-state validation and lifecycle
deduplication packages. Codex independently reviewed each candidate, added three bounded
type-consistency corrections and regression tests, and reran the focused suite. Sonnet reviewed
the final sealed candidate read-only, reported **PASS**, found no blockers, and explicitly
authorised freezing B1 and beginning B2.

## Deferred

Truthful single-flight test receipts, exact evidence reuse and full-suite authorisation remain B2.
Contexts, allocation certification, CLI and documentation remain Package C. Production STOP,
DFI-05 and JAA remain untouched.
