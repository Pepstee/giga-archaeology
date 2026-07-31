# Factory Turnstile C1 — final read-only Sonnet review

Review only. Worktree:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Base commit:

`895c2a8318de6d98cdccb03a58e0284d6433d37f`

Expected exact hashes:

```text
226cc4af2dd630033c6fcbf7781dd50845851059e42bb199b3191bd1f404c8e2  factory_control/turnstile.py
6b0d69cd4624ef6f7a680065861cde749dbeec35e9d8a15dc87d570e466ee57d  tests/test_factory_turnstile.py
```

Independent host evidence: 319 tests passed; py_compile and `git diff --check` passed.
Production accounting: 1,839 physical lines across `factory_control/*.py`, under the 1,840 C1
ceiling.

Do not edit, commit, run the complete suite, spawn subagents, or touch production, DFI-05, JAA or
another worktree.

Review the complete C1 delta and the Codex deletion/refinement pass. Required contract:

- explicit, unique normalized relative UTF-8 files under a real non-symlink root;
- reject absolute paths, every `..` traversal component, symlink components/finals, non-regular
  files and identity changes;
- hold the controller lock from lease check through terminal pack event so no governed operation
  starts during assembly;
- enforce a positive non-bool byte ceiling during descriptor-bound reads, with exact equality
  allowed;
- stable caller-order-independent canonical JSON containing only version, relative path, SHA-256,
  exact text and total UTF-8 bytes;
- SHA-256 over exact canonical pack bytes;
- atomic fsynced same-directory temporary write and no-clobber installation;
- exact existing or concurrently created matching pack may be reused;
- missing/tampered/symlinked/mismatched collision never overwritten;
- failure leaves no partial pack and no false success event;
- no provider/model/prompt/token/scheduler/queue logic.

Inspect especially normalized aliases, lock ordering/deadlock, tempfile/hard-link crash windows,
collision races, large-file memory use, UTF-8 byte accounting, event truthfulness, and whether the
deletion pass weakened cleanup.

Return `PASS` or `CHANGES REQUIRED` with precise evidence. This is review, not certification.
