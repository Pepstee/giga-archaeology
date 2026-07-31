# Fable authority result — Factory Turnstile v1

Date: 2026-07-23
Reviewed head: `938b42d392ff4ac4df39492ff28f5dc398192d45`
Production lines: 2,151
Host suite: 431 passed

## Verdict

**PASS FOR CONTROLLED INSTALLATION**

Fable found no path that admits two live model/test operations, clears a live or ambiguous lease,
silently accepts candidate mutation, reuses unauthenticated evidence, or bypasses certification.
The controller is sufficient for sequential DFI-05 settlement without becoming a second
orchestrator.

## Required before activation

### F1 — deterministic stop phase

Low severity. In the pre-signal stale-lease branch of `stop()`, a concurrently finalized operation
can clear its lease and leave `sealed` while `stop()` returns success. The final-lock branch forces
`paused`, so identical races have inconsistent terminal phases. Add a race regression and make the
stale branch mirror the final branch when the original lease has become `None`.

### F2 — truthful CLI operational errors and signal exits

Low severity. A child launch `OSError` escapes the CLI as a traceback rather than canonical stderr
JSON. A signal-killed child returns a negative Python return code which `sys.exit()` maps
implicitly, contradicting “exact exit code forwarded”. Catch operational `OSError`, map negative
child returns to `128 + signal`, and document how stdout/stderr JSON distinguishes child exit 1/2
from controller/argparse exit 1/2.

## Accepted residuals

- Candidate identity covers git-visible files, not ignored caches/build artifacts.
- Descendants that call `setsid()` can escape process-group signalling; later candidate gates still
  catch git-visible mutations.
- Test reuse trusts the caller-declared runtime identity and deterministic test behaviour.
- A crash before PID/PGID recording creates an intentionally manual-recovery lease.
- The flock is per lock-file inode; control directories must never be cleaned or recreated in use.
- State, events and evidence are separately durable; state is authoritative and events are
  best-effort audit.
- The suite's mocked-file `ResourceWarning` is harness hygiene, not a production leak.
- A deterministic stop can demote concurrently finalized state to `paused` without deleting its
  ledger/evidence.

## Optional later deletion work

- Consider sharing four process-escalation loops only under the complete test harness.
- Comment why certification recomputes the candidate twice.
- Consider sharing content-collision verification.
- Remove dead first invocations in two CLI tests.

None of these optional deletions may delay controlled installation or pre-activation repairs.
