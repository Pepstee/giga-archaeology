# Factory Turnstile B2 repair R3a — bounded descriptor hashing

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
Preserve the current uncommitted 252-test candidate. Sole writer; no subagents, commits, production,
DFI-05, JAA, other worktrees, or files outside `factory_control/turnstile.py` and
`tests/test_factory_turnstile.py`.

Implement only:

1. Reuse output-log validation must compute SHA-256 through the already descriptor-bound regular
   file in fixed 65,536-byte chunks. Never concatenate or allocate the complete log.
2. Canonical receipt reading through the descriptor-bound helper must accept an exact maximum byte
   count. The caller knows the expected canonical receipt bytes; refuse if the evidence is longer
   than that bound.
3. Fresh test output must be opened for read/write. After child exit, flush and fsync, rewind the
   same open descriptor, stream SHA-256 from it, and prove the evidence pathname still identifies
   that exact regular device/inode before closing. Do not reopen fresh output by pathname.

Preserve existing device/inode, regular-file, `O_NOFOLLOW`, post-read identity and close-on-all-path
checks. Add regressions proving:

- a multi-megabyte output is read in bounded chunks;
- oversized receipt evidence refuses reuse;
- swapping the fresh output pathname before hashing fails closed and does not produce a receipt.

Do not implement lease cleanup or stop-race changes in this package.

Run focused unittest, py_compile and `git diff --check`; report exact results and risks. Do not
self-certify.
