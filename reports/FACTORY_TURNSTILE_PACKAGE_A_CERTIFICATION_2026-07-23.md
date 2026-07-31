# Factory Turnstile v1 — Package A certification

**Verdict:** Package A certified and may freeze. This is not certification of the complete
Factory Turnstile.

## Scope certified

- durable canonical state and append-only event writes;
- exact Git candidate identity;
- exclusive writer lease and real process exit status;
- fail-closed launch failure and explicit orphan recovery;
- pause and bounded process-group stop;
- PID/start-identity/PGID reuse guards;
- state/lease invariants and control-directory isolation.

## Sealed evidence

- pre-review candidate:
  `d58dc0b60453df6318a056a8a25825c6ba6d06276c92097d34baed3dc6b313c2`
- production source:
  `factory_control/turnstile.py`
  SHA-256 `7dfa6792f2387ace9e78dc4f9a7388c801d21db7174b6d840857e1e7e197980f`
- focused tests:
  `tests/test_factory_turnstile.py`
  SHA-256 `166d447e072b67791395db38ff91cbdf447dfde854ff0d93b1fd205293913fe9`
- independent host suite: **94 passed**, 0 failed
- independent `py_compile`: passed
- production size including exports: **845 physical lines**
- source hashes were unchanged across the independent test gate.

## Inter-model evidence

Sonnet implemented the first pass and two bounded repair packages. Codex performed independent
read-only reviews, named defects, implemented one narrow correction after hash-checking the sealed
source, and reran the complete focused suite. Sonnet then counter-reviewed the final candidate
with read/search tools only and returned **PASS**, no blocking findings, and explicit authority to
freeze Package A and begin Package B.

## Accepted non-blocking limitations

1. A `stop(timeout=0)` call made during the tiny pending-PGID window may fail without altering
   state; a later stop succeeds.
2. A directory-fsync I/O failure after successful atomic replacement can report failure even
   though the new state file is already present. Re-reading remains authoritative.

## Excluded

Independent review execution, single-flight test receipts, bounded context packs, allocation
certification, CLI and full controller documentation remain Package B/C work. Production STOP,
DFI-05 and JAA were untouched.
