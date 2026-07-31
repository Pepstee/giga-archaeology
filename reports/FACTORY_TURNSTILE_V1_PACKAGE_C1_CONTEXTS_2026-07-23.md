# Factory Turnstile v1 — Package C1 bounded context packs

Work only in:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Base commit:

`895c2a8318de6d98cdccb03a58e0284d6433d37f`

You are the sole writer. Do not spawn subagents, commit, touch production, DFI-05, JAA, another
worktree, or files outside:

```text
factory_control/__init__.py
factory_control/turnstile.py
tests/test_factory_turnstile.py
```

Preserve all 271 tests. Implement bounded context packs only. Do not implement allocation,
certification, CLI or documentation.

## Public API

Add:

```python
build_context(
    root: str | Path,
    relative_files: list[str],
    byte_ceiling: int,
) -> dict
```

Return a stable summary containing at least:

```text
hash
path
file_count
utf8_bytes
reused
```

## Contract

- Require an initialized stage and reject context building while any lease is recorded.
- `root` must be an existing real directory, not a symlink.
- Require a non-empty explicit list of unique, non-empty relative file paths.
- Reject absolute paths, traversal, directories, special files, final symlinks and symlinks in any
  intermediate path component.
- Every selected path must remain inside the explicit root.
- Read each file through the existing descriptor-bound regular-file mechanism; reject identity
  changes during reading.
- Decode bytes as strict UTF-8. Binary/invalid UTF-8 input fails closed.
- `byte_ceiling` must be a finite positive integer, not `bool`.
- Enforce the ceiling against the sum of the selected files' UTF-8 bytes before writing anything.
  Exact equality is allowed; one byte over is refused.
- Sort entries by normalized relative path so caller order cannot change the pack.
- Emit canonical compact JSON containing only versioned file entries with relative path, SHA-256
  and exact text content, plus the total UTF-8 byte count. Do not include absolute root paths,
  timestamps, host identity, conversation history or unrelated state.
- Compute the pack SHA-256 over the exact canonical JSON bytes.
- Write `control_dir/contexts/context_<hash>.json` atomically with tempfile, file fsync,
  `os.replace` and directory fsync.
- If the exact canonical pack already exists as a regular non-symlink file with identical bytes,
  return it with `reused=True` and do not rewrite. A tampered/symlinked collision fails closed; do
  not overwrite it.
- Append a canonical `context_built` or `context_reused` event under the controller lock only after
  successful evidence verification/write.
- Any failure leaves no temporary or partial context pack.

No shell, provider logic, prompt generation, token estimation, model call, scheduler or queue.

## Required tests

Cover at least:

1. deterministic success and caller-order independence;
2. exact content/path/hash binding;
3. exact byte ceiling success and one-byte-over refusal;
4. absolute path, traversal and duplicate refusal;
5. root, intermediate and final symlink refusal;
6. directory/special/nonexistent path refusal;
7. invalid UTF-8 refusal;
8. identity swap during read refusal;
9. exact pack reuse without rewrite;
10. missing/tampered/symlinked collision refusal;
11. active lease refusal;
12. no temp/partial pack after injected write/replace/fsync failure;
13. all previous 271 tests remain green.

## Budget and gates

Complete production after C1 must be at most **1,840 physical lines** across
`factory_control/*.py` and `scripts/factory_turnstile.py`. Do not hide logic in tests.

Run only:

```bash
python3 -m unittest tests.test_factory_turnstile
python3 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  tests/test_factory_turnstile.py
git diff --check
```

Report exact count, production line count and residual risks. Do not self-certify or commit.
