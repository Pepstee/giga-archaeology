# Factory Turnstile connectivity checkpoint

**Recorded:** 2026-07-23 14:21 BST  
**Reason:** Gigabyte became unreachable during the sole Sonnet Package A repair.

## Last proved state

- Factory Turnstile worktree:
  `/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`
- Branch: `factory/turnstile-v1`
- Base: `82cb47ef82d6973c08513686bcca6ed0469418a7`
- Package A first pass existed as uncommitted files:
  `factory_control/__init__.py`, `factory_control/turnstile.py`,
  `tests/test_factory_turnstile.py`.
- Independent focused rerun before repair: 27 tests passed.
- Production orchestrator STOP was armed and its user service inactive.
- DFI-05 and JAA remained untouched.
- Repair order existed on both machines with SHA-256:
  `fc6562eb0a66213d5e911a087aacf9ccc13e94b5ca1580dbbdc88e20131a1a1d`.

## Interrupted operation

One and only one writer was launched:

```text
claude -p --model sonnet --effort medium
  --name factory-turnstile-a-repair
  < reports/FACTORY_TURNSTILE_V1_PACKAGE_A_REPAIR_2026-07-23.md
```

The SSH transport timed out without a terminal result. Gigabyte then stopped answering ICMP and
SSH for more than five minutes. The remote Claude process and worktree contents are therefore
**unknown**, not failed and not accepted. No replacement worker was launched.

## Mandatory resume sequence

1. Restore Gigabyte connectivity.
2. Inspect Claude, Codex and test PIDs before launching anything.
3. Inspect exact worktree status, mtimes and diff.
4. If the original Sonnet process is alive, allow only that process to settle.
5. If it is dead, preserve any partial diff before deciding whether to resume or rerun the same
   repair order.
6. Rerun the focused test gate independently only after the candidate stops changing.
7. Do not begin Package B, DFI-05, JAA or production activation until Package A is accepted.

The cancelled Fable handoff remains non-authoritative.
