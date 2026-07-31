# Factory Turnstile pre-activation repair — Codex review

Review only. Do not edit, commit, spawn agents, or inspect another worktree.

Starting head:

`938b42d392ff4ac4df39492ff28f5dc398192d45`

Controller-sealed candidate:

`c628dd60bc368b3ace98abf9a34c68bedd0d7466a2e7a1966dc25d83e2106abb`

Exact file hashes:

```text
15f4661ea42f6b3f363fa95870d18c54d4d928f8344bdf6989baf393bf650011  factory_control/turnstile.py
4d6ca7b334ff4cc43b96ab7e63a22752ab0bef83951bb47a56428fa76023b14e  scripts/factory_turnstile.py
b6ace5cb38a1c36fcf573ec64b64e6cd02519fd96377d565cf43a3b24ec3cfbb  tests/test_factory_turnstile.py
979f91e519be5cc7bc662b6968ec8c6b2e4cc014a29769396e2ef5eef3fd06eb  tests/test_factory_turnstile_cli.py
ea4e4fafe969c9086b5d95d47390464ba343d3eaf35469b141792bafc86e0f53  FACTORY_TURNSTILE.md
```

Read the Fable ruling and repair order already present in `reports/`, then review the entire diff
and relevant surrounding code/tests.

Verify:

1. F1 only forces `paused` when the original lease has become `None`; a replacement lease remains
   completely untouched;
2. stale-branch candidate/event ordering is truthful and agrees with the final-lock branch;
3. no live/ambiguous process can be cleared or reported stopped;
4. `OSError` handling does not swallow unexpected programming errors and core launch failure still
   fails closed;
5. worker/review/test stdout retains raw negative child return while CLI status maps `-N` to
   `128+N`;
6. ordinary 0–255 returns, controller error 1 and argparse 2 remain truthful and distinguishable;
7. the nonexistent-executable test uses a real Turnstile and proves state/lease cleanup;
8. documentation matches code and does not overstate ignored-file, process-group, runtime identity,
   lock-inode or event durability guarantees;
9. all changes stay within the controller's immutable non-goal boundary and 2,200-line ceiling;
10. any regression or missing test not listed above.

The first Codex attempt correctly found that the manual grouped `--help` with argparse error exit 2.
That finding has been repaired: help is documented as exit 0 and usage/parsing errors as exit 2.
Verify the correction.

The second Codex attempt correctly found two additional gaps. Sonnet has now narrowed expected
`OSError` normalization so stdout-write failures propagate, added that regression, and strengthened
the real nonexistent-executable test to prove durable `paused` state, `lease is None`, the
`worker_launch_failed` event, and candidate state. Sonnet reports the complete controller suites at
439 passing tests. Verify both repairs independently rather than trusting this report.

Return schema-valid JSON only. Use `PASS` only if no required change remains. Otherwise use
`CHANGES_REQUIRED` and provide precise findings.
