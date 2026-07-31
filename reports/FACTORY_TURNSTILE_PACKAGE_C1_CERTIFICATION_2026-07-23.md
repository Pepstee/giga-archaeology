# Factory Turnstile v1 — Package C1 functional certification

Date: 2026-07-23  
Worktree: `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`  
Branch: `factory/turnstile-v1`  
Base commit: `895c2a8318de6d98cdccb03a58e0284d6433d37f`

## Verdict

**C1 is functionally certified for deterministic, bounded and immutable context packs.**

This is not certification of the complete Factory Turnstile. Allocation reporting, the
certification gate, CLI/documentation, authoritative installation and the end-to-end adversarial
gate remain.

## Certified candidate

```text
226cc4af2dd630033c6fcbf7781dd50845851059e42bb199b3191bd1f404c8e2  factory_control/turnstile.py
6b0d69cd4624ef6f7a680065861cde749dbeec35e9d8a15dc87d570e466ee57d  tests/test_factory_turnstile.py
```

Production physical lines before commit:

```text
17    factory_control/__init__.py
1822  factory_control/turnstile.py
1839  total
```

The ratified C1 ceiling is 1,840 production physical lines. The candidate is one line below it.

## Evidence

- Independent host suite: **319 tests passed**, zero failures/errors.
- `python3 -m py_compile factory_control/turnstile.py tests/test_factory_turnstile.py`: passed.
- `git diff --check`: passed.
- Final read-only Sonnet review read both source and test files in full and returned **PASS** on all
  ten contract clauses.
- The review was bound to the two hashes above; a separate hash check confirmed that the candidate
  did not move while the reviewer was active.
- Codex performed a deletion/refinement pass and added the standalone interior-traversal regression.
- No writer and reviewer ran concurrently.
- Production orchestrator remained stopped, STOP remained armed, and DFI-05/JAA were untouched.

## Certified behaviour

- The caller supplies an explicit, non-empty file list and a positive non-boolean byte ceiling.
- The context root must be a real, non-symlink directory.
- Absolute paths, every `..` component, normalized aliases, symlinked components/finals,
  non-regular files and identity-changing files fail closed.
- The controller lock is held continuously from lease exclusion through all reads, pack
  installation and the terminal event.
- Reads are descriptor-bound, no-follow, identity-checked, byte-bounded and strict UTF-8.
- Canonical JSON is independent of caller order and contains only version, normalized relative
  path, exact source SHA-256, decoded text and total UTF-8 bytes.
- Pack identity is SHA-256 over the exact canonical bytes.
- Installation uses an fsynced same-directory temporary file and an atomic no-clobber hard link.
- An exact pre-existing or concurrently-created pack is reused; a symlinked, tampered or
  mismatched collision is never overwritten.
- Failure cannot emit a false success/reuse event or leave a referenced partial pack.
- The package adds no provider, model, prompt, token, scheduler, queue, retry, routing or daemon
  policy.

## Honest residuals

- External processes not governed by the controller can still race filesystem namespace changes.
  Descriptor and identity checks make such races fail closed, while controller-governed operations
  are excluded by the continuously held lock.
- Context packs and controller state are separate durable artifacts, not one filesystem
  transaction. A crash after pack installation but before the event can leave an unreferenced,
  content-addressed pack; a later identical request verifies and reuses it.
- Persistent filesystem or fsync failure prevents success and requires operator repair; the
  controller does not claim a pack was built.

## Efficiency relevance

C1 replaces repeated broad repository ingestion with explicit, content-addressed, byte-capped
context packs. It preserves exact provenance while making model context small, reproducible and
reusable across independent Sonnet and Codex stages.
