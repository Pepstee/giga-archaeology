# Factory Turnstile v1 — Package C3 thin CLI and operator documentation

Work only in:

`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

Base commit:

`3d49db36f565c8511645d3417d08fe3b839f48fe`

You are the sole writer. Do not spawn agents, commit, touch production, DFI-05, JAA, another
worktree, or files outside:

```text
scripts/factory_turnstile.py
tests/test_factory_turnstile_cli.py
FACTORY_TURNSTILE.md
```

Preserve all 388 core tests. Implement only a thin deterministic CLI over the certified API and
concise operator documentation. Do not modify `factory_control/`, duplicate controller logic, or add
scheduling, retries, routing, prompt generation, model/provider selection, token policy, daemon
loops or autonomous behaviour.

## CLI contract

Create executable:

`scripts/factory_turnstile.py`

Use only the Python standard library and `factory_control.Turnstile`. Global required arguments:

```text
--control-dir PATH
--worktree PATH
```

Expose exactly these subcommands:

```text
init       --stage NAME
status
worker     --actor {sonnet,codex} [--weight FLOAT] -- COMMAND [ARG...]
review     --actor {sonnet,codex} --verdict {pass,changes-requested}
           [--weight FLOAT] -- COMMAND [ARG...]
test       --suite-id ID --suite-kind {focused,full} --runtime ID
           [--authorize-full] -- COMMAND [ARG...]
context    --root PATH --byte-ceiling BYTES --file RELATIVE [--file RELATIVE ...]
allocation
certify    --suite-id ID [--suite-id ID ...]
recover
pause
stop       [--timeout SECONDS]
```

Requirements:

- Direct argv only; never invoke a shell or evaluate command text.
- Require a non-empty command after `--` for worker/review/test.
- `worker` always calls role `writer`; expose no arbitrary role/provider/model field.
- Pass the literal parsed boolean from `--authorize-full` to `run_test()`. The core must continue
  enforcing that full suites require `True`.
- Default work weight is `1.0`; core validation remains authoritative.
- Print exactly one canonical compact sorted-key JSON object to stdout for every successful command.
- Void core methods return a small truthful object containing command and `ok=true`.
- Worker/review print actor, command type and child exit code, then return the child's exact exit
  code when representable as a process exit status.
- Test prints the exact core result and returns its exact child exit code when not reused/passing.
- Expected `TurnstileError` subclasses produce one canonical JSON error object on stderr and exit 1.
- `argparse` usage/shape errors retain exit 2.
- Do not catch unexpected programming errors as successful/normal results.
- Import must work when invoked from the repository root with
  `python3 scripts/factory_turnstile.py ...`; no installation step may be assumed.
- `main(argv=None) -> int` must be importable for isolated tests.

## Required CLI tests

Use isolated temporary repositories/control directories and mocks where command dispatch—not core
behaviour—is the subject. Cover at least:

1. every listed subcommand dispatches to the exact core method and emits valid canonical JSON;
2. worker/review/test preserve direct argv elements containing spaces/metacharacters without shell
   interpretation;
3. missing command is argparse exit 2;
4. full test without authorization is rejected by the core; with flag forwards literal `True`;
5. multiple context files and suite IDs preserve the intended list;
6. expected controller errors produce stderr JSON and exit 1 with no stdout success;
7. child nonzero exit propagation;
8. no undocumented subcommand, provider/model/scheduler/retry option exists;
9. help works and contains the non-goal boundary;
10. all 388 core tests remain green.

## Documentation contract

Create `FACTORY_TURNSTILE.md` documenting:

- purpose: a deterministic single-flight safety controller, not another orchestrator;
- the complete command reference and copyable examples;
- the required sequential Sonnet/Codex workflow;
- 30/70 declared-weight policy and what it does **not** measure;
- bounded context packs and exact test reuse;
- certification prerequisites and evidence artifacts;
- STOP/isolation preconditions before touching orchestrator-v3;
- crash recovery, `pause`, `stop`, `recover`, and the tested state/event residual;
- exit codes;
- explicit non-goals;
- current installation status: candidate worktree only, not yet authoritative/activated.

Do not claim performance savings before controlled measurement.

## Budget and gates

Complete production after C3 must be at most **2,200 physical lines** across:

```text
factory_control/*.py
scripts/factory_turnstile.py
```

Current production is 2,000 lines, so the CLI has at most 200 physical lines. Documentation and
tests do not count as production, but must not contain hidden executable logic.

Run only:

```bash
python3 -m unittest tests.test_factory_turnstile tests.test_factory_turnstile_cli
python3 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  scripts/factory_turnstile.py tests/test_factory_turnstile.py tests/test_factory_turnstile_cli.py
git diff --check
```

Report exact test counts, production lines, changed files and residual risks. Do not self-certify or
commit.
