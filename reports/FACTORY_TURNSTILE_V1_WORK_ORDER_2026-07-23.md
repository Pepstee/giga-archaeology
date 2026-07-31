# Factory Turnstile v1 — bounded Sonnet work order

**Purpose:** Eliminate inter-model write concurrency, duplicate test execution, masked test
failures, unbounded context carry-over and unmeasured model-work allocation.

**Implementation worktree:**
`/home/gutua/software-factory/.worktrees/giga-user-factory-turnstile`

**Branch/base:** `factory/turnstile-v1` from
`82cb47ef82d6973c08513686bcca6ed0469418a7`

## Authority and exclusions

You are the exclusive first-pass writer. No Codex writer is active while this order runs.

Do not:

- touch orchestrator-v3, DFI-05, JAA, production, STOP, services or any other worktree;
- modify pre-existing giga-user files;
- spawn subagents;
- commit;
- run the whole giga-user test suite;
- use shell pipelines to decide command success;
- add third-party dependencies.

Create only:

```text
factory_control/__init__.py
factory_control/turnstile.py
scripts/factory_turnstile.py
tests/test_factory_turnstile.py
docs/FACTORY_TURNSTILE.md
```

Use Python 3.12+ standard library only. Keep production implementation
(`factory_control/*.py` and `scripts/factory_turnstile.py`) at or below 750 lines total. Tests and
documentation do not count.

## Required architecture

Implement one CLI-backed deterministic stage controller.

### Durable state

For a configured control directory, maintain:

```text
lock
state.json
events.jsonl
evidence/
contexts/
```

- Serialise every state transition with `fcntl.flock`.
- Write `state.json` atomically using temporary file, `fsync`, `os.replace` and directory `fsync`.
- Append canonical, one-line JSON events under the lock and `fsync` them.
- State and events must use stable JSON (`sort_keys=True`, compact separators, UTF-8).
- Reject malformed/corrupt state rather than silently resetting it.

### Candidate identity

Bind evidence to an exact Git worktree snapshot:

- resolved worktree path;
- current `HEAD`;
- all tracked and non-ignored untracked paths;
- path, file type, executable mode and SHA-256/content or symlink-target identity.

Do not rely only on `git diff` or status text. Reject paths escaping the worktree and unsupported
special files. Candidate identity must change after any relevant byte, mode, symlink or path
change.

### Exclusive work lease

`run-worker` must:

- permit only one active model process;
- record actor (`sonnet` or `codex`), provider family, role, PID, process-start identity, process
  group, lease UUID, command and candidate-before hash;
- execute an argv directly with `subprocess`, never through a shell;
- launch the child in its own process group;
- reject a second writer/reviewer/test while the child is alive;
- on exit, seal the resulting candidate hash and append a work-ledger entry;
- preserve the real child exit code;
- leave a failed/interrupted worker paused, not silently ready.

An explicit recovery command may clear an orphaned lease only after proving the recorded process
is dead or has a different process-start identity. Recovery captures the current candidate and
leaves the stage paused.

### Independent review

`run-review` must:

- require a sealed candidate and a different actor from its writer;
- execute a direct argv read-only review command;
- verify the candidate hash before and after;
- treat any review-time worktree mutation as a concurrency violation and pause;
- accept an explicit intended verdict (`pass` or `changes-requested`) only when the review command
  exits zero;
- record the reviewer and weighted work package;
- require a new writer turn and reseal after `changes-requested`.

### Single-flight truthful tests

`run-test` must:

- require an independently reviewed, unchanged candidate;
- allow only one active test;
- execute argv directly, preserving the test process's exact exit code;
- write complete stdout/stderr to an evidence log, then display/report separately;
- create a canonical receipt binding candidate hash, suite ID, suite kind, argv, selected runtime
  identity, timestamps, exit code and output SHA-256;
- consider a suite passing only when the real process exit code is zero;
- reuse an existing passing receipt for the exact same candidate/suite/argv/runtime key;
- never reuse failures;
- reject `full` suites unless the caller supplies an explicit gate authorisation flag;
- detect any candidate mutation during a test, invalidate the receipt and pause.

No implementation may use `pytest | tail`, shell pipelines or parsed summary text as the source of
truth.

### Bounded context packs

`build-context` must:

- accept an explicit root and explicit relative files;
- reject absolute paths, traversal, symlinks and files outside the root;
- bind each path and SHA-256;
- emit a deterministic JSON context pack containing only those files;
- enforce a caller-supplied UTF-8 byte ceiling before writing;
- write atomically and report its content hash.

This is the input to fresh model sessions; historical conversation transcripts are not included.

### Work allocation

Maintain accepted weighted model work packages:

- Sonnet belongs to provider family `claude`.
- Codex belongs to provider family `codex`.
- Deterministic host test execution is excluded from the model ratio.
- Report total weight and Claude/Codex basis points.
- `certify` requires Claude to be within 7,000 ± 1,000 basis points, at least one independent
  review, an unchanged candidate and caller-named passing suite receipts.
- Fable milestone rulings are authority evidence, not artificial work used to manipulate the
  ratio.

### Stop and status

- `status` is read-only and reports active lease, phase, candidate, receipts and allocation.
- `pause` refuses while a live operation exists.
- `stop` sends SIGINT to the active process group, waits for a bounded timeout, then SIGTERM if
  needed; it records the outcome, seals the current candidate and leaves the stage paused.
- No command may automatically resume a paused stage.

## Minimum CLI surface

The thin `scripts/factory_turnstile.py` entry point must expose:

```text
init
status
build-context
run-worker
run-review
run-test
recover
pause
stop
certify
```

Use `--` followed by argv for executed commands. Reject empty commands.

## Mandatory tests

Use temporary Git repositories and `unittest`. Cover at least:

1. stable candidate identity and mutation/path/mode/symlink sensitivity;
2. a live writer blocks a second writer, review and test;
3. writer exit seals the candidate and preserves non-zero exit;
4. orphan recovery refuses a live PID and accepts a dead lease;
5. reviewer must differ from writer;
6. review mutation causes a violation/pause;
7. test process non-zero remains non-zero even when output looks successful;
8. exact passing test receipt is reused without rerunning the command;
9. failed receipts are not reused;
10. full suite requires explicit authorisation;
11. test-time mutation invalidates evidence;
12. context pack traversal/symlink/oversize refusal and deterministic success;
13. candidate changes invalidate earlier review/test eligibility;
14. work allocation calculation and certification tolerance;
15. stop interrupts a real child process group and leaves the stage paused;
16. corrupt state fails closed;
17. event log/state transition evidence is deterministic and append-only.

## Verification allowed in this turn

Run only:

```text
python3.12 -m unittest -v tests.test_factory_turnstile
python3.14 -m unittest -v tests.test_factory_turnstile
python3.14 -m py_compile factory_control/__init__.py factory_control/turnstile.py \
  scripts/factory_turnstile.py tests/test_factory_turnstile.py
git diff --check
```

If Python 3.12 is unavailable, report it honestly and run the focused suite with the available
system Python; do not install packages.

Finish with exact files, line counts, commands/results and unresolved risks. Do not self-certify.
