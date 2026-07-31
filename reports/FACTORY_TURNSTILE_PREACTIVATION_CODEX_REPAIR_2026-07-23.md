# Factory Turnstile pre-activation Codex repair

Work only in the current `giga-user-turnstile-preactivation` worktree. Do not
commit. Preserve the sealed collaboration design and repair exactly the two
medium findings from the independent Codex review of candidate
`6df56fafb3ced89931f93dc7c4fa2f67bdec552fa14a97b3e28c474edeaad5f5`.

## Required repairs

1. Narrow CLI `OSError` normalization in `scripts/factory_turnstile.py`.
   Only operational errors from Turnstile construction/core-operation
   boundaries may be converted to the canonical controller exit `1`.
   `OSError` raised by command-result formatting, stdout writes, or other CLI
   plumbing/programming logic must propagate normally. Preserve
   `TurnstileError` handling. Add a regression proving a non-core `OSError` is
   not normalized.

2. Strengthen the real-Turnstile nonexistent-executable regression in
   `tests/test_factory_turnstile_cli.py`. After launch failure, reload/query
   durable state and prove:
   - phase is `paused`;
   - lease is `None`;
   - the expected launch-failure event and candidate state are present.

## Verification

- Run the complete controller suites:
  `python3 -m unittest -q tests.test_factory_turnstile tests.test_factory_turnstile_cli`
- Preserve all prior Fable repairs and documentation.
- Do not broaden scope or touch unrelated files.
- Exit successfully only if all tests pass.
