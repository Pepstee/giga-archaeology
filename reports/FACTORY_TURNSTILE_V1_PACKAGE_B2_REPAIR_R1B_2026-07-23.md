# Factory Turnstile B2 repair R1b — descriptor-bound evidence identity

Work only in `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`.
Preserve the current uncommitted 250-test candidate. You are the sole writer. Do not commit, spawn
subagents, or touch production, DFI-05, JAA, another worktree, or files outside:

```text
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Independent review rejected one residual-risk claim from the preceding repair. The reuse path still
does `lstat(path)` and later reopens by pathname. A concurrent swap can replace the checked regular
file with a symlink to a target containing the expected bytes/hash. Byte equality then passes even
though the governed evidence path is a symlink, violating the contract.

Implement a small standard-library helper that reads/hashes evidence through a file descriptor
whose identity is bound to the checked path:

- `lstat` the path and require a regular file;
- open without following a final symlink where the platform supports it;
- `fstat` the open descriptor and require a regular file;
- require device/inode identity to match the pre-open `lstat`;
- read/hash only through that descriptor;
- re-`lstat` after the read and require the path still names the same regular device/inode;
- close the descriptor on every path.

Use it for both complete output-log hashing and canonical receipt-byte reading during reuse. A
missing path, symlink, unsupported type, identity swap, or I/O error means no reuse and a fresh
test run. Do not convert a malformed persisted state into a soft miss.

Add deterministic tests that inject a swap between the initial `lstat` and open/read for both the
receipt and output paths. Prove reuse is refused and the child reruns. Preserve all 250 tests.

Run:

```bash
python3 -m unittest tests.test_factory_turnstile
python3 -m py_compile factory_control/turnstile.py tests/test_factory_turnstile.py
git diff --check
```

Report exact count and risks. Do not self-certify.
