# DFI-06 scope-entropy intervention — 2026-07-24

Checkpoint: `2026-07-24T09:30:44+01:00`

## Verdict

DFI-06 made substantial progress and reached a committed candidate, but its
post-commit recertification escaped the ratified stage boundary. The live
writer was stopped and its lease recovered before the expansion could be
accepted or carried into later stages.

## Progress proved since the prior check-in

- Quota-aware collaboration replaced the misleading fixed-ratio operating
  policy.
- Sonnet became the implementation/repair owner; Codex remained the
  independent reviewer.
- One exhaustive Codex review returned ten findings together instead of
  forcing ten full-review cycles.
- Sonnet repaired the complete set; bounded delta reviews reduced the open set
  from ten to four, then two.
- Deterministic DFI-06 evidence reached five passing valid receipts under the
  pre-commit controller.
- The shadow delta-review harness was committed as:
  `4be0741 Add shadow delta review economics harness`.

## Scope breach found during status verification

The original DFI-06 work order states:

- stage ceiling: 180 net production lines;
- shadow-only observational harness;
- no persistence, side store, cache, certificate authority, activation,
  daemon, STOP, or JAA changes.

The post-commit recertification worktree instead accumulated:

- signed journal and signed-head machinery;
- crash/pending-record recovery;
- protected directory-FD writes and fsync behavior;
- a host-controller journal writer;
- Ed25519 support;
- multiple new production modules.

Measured untracked production alone:

- `infra/ed25519_sig.py`: 87 lines;
- `validation/delta_obs_support.py`: 129 lines;
- `validation/delta_review_telemetry.py`: 5 lines;
- `validation/evidence_journal.py`: 634 lines;
- `host_controller/journal_writer.py`: 540 lines;
- total: **1,395 lines**, before tracked production changes.

The tracked test delta was also approximately 1,794 net lines and
`tests/test_delta_economics.py` had reached 2,310 physical lines. This was not
a valid interpretation of a 180-line observational stage.

## Safety intervention

- Stopped `codex-gigabyte-coordinator-20260724.service`.
- Confirmed no Claude or Codex child remained.
- Recovered the dead Sonnet lease through the certified turnstile.
- Preserved every dirty file in place; nothing was discarded.
- Recertification controller is paused with no live lease.
- Current dirty candidate hash:
  `04c51570027c7372b69e650b9df91922d7685bf92582747f7af0df281a92a947`.
- Worktree HEAD remains committed DFI-06 candidate `4be0741`.
- Production orchestrator remains clean on `efficiency/e2-shadow-cache`.
- Production STOP hash remains
  `b9fd288d7acdf65e8169f99ffb64e8ffc587e91cdfe4ac59c900c782878c13d7`.
- JAA path has no new Git status changes.

## Next safe sequence

1. Preserve the dirty expansion as evidence/quarantine; do not accept or erase
   it.
2. Create a fresh worktree from `4be0741`; do not reuse the dirty recertification
   worktree.
3. Reconcile the committed candidate against the **original** DFI-06 work
   order and total production budget.
4. Any legitimate need for signed persistent journals belongs in its planned
   later infrastructure stage with its own budget, tests, threat boundary, and
   certification—not hidden inside DFI-06.
5. Recertify only the bounded DFI-06 observational candidate.
6. Resume DFI-07 onward only after that certificate exists.
7. Keep production STOP armed and JAA untouched until the complete efficient
   profile is certified, activated in a controlled window, and proves real
   savings without quality loss.
