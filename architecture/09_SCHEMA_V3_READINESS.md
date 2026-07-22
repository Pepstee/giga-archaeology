# Schema v3 migration readiness

Date: 2026-07-22

## Decision

The isolated schema-v3 candidate is safe to advance to a controlled implementation window.
This is not authorization to modify the live database. The live code, schema-v2 database, and
Telegram daemon remained in place throughout this build.

## Candidate safety controls

- Existing v1/v2 databases fail closed when opened by v3 code; migration is never implicit.
- A fresh empty database is initialized as one unambiguous schema: metadata v3 and
  `PRAGMA user_version=3`.
- The explicit v2-to-v3 migrator acquires `BEGIN IMMEDIATE` before backup and holds the writer
  lock across backup and migration. The backup is therefore the immediate pre-migration state.
- Backup paths must be new and distinct; backup files are mode `0600`.
- Migration DDL, metadata, user version, and migration-ledger insertion share one transaction.
- Four exact-definition triggers prevent deletion, payload mutation, invalid status reversal,
  and insertion of already-superseded artifact revisions.
- An entropy check verifies both version markers, exact trigger definitions, the migration
  ledger, current-revision uniqueness, projection equality, orphan links, and cycles.
- These controls protect against accidental or application-level corruption. They do not
  protect against a malicious owner who can replace the SQLite file or drop its triggers.

## Verification evidence

- Candidate compile check: pass.
- Candidate regression and migration suite: 59 passed plus 4 injected-failure subtests.
- Live unchanged regression suite: 54 passed.
- Fault injection: rollback passed after lock, after backup, after DDL, and before commit.
- Writer contention: clean timeout, no backup and no partial schema.
- Production SQLite-backup clone: v2 to v3 passed.
- Clone postconditions: integrity `ok`; zero foreign-key violations; metadata v3;
  `user_version=3`; one migration-ledger row; four triggers.
- Clone entropy checks: all passed.
- Core table counts and logical row digests: preserved.
- Restore drill: backup restored as v2 with matching core counts and logical digest.
- Live database SHA-256 before/after clone drills:
  `fb44a96e6ea70d865fca2596114524743d0f307187e4baf6a761f88d8eee3230`.
- Live Telegram daemon remained active as PID 40224.

## Existing, unrelated drift

The read-only artifact audit reports two sources changed before this candidate is installed:
`memory/INDEX.md` and `skilltree/IMPLEMENTATION_REPORT.md`. This does not alter migration
correctness or database reversibility, but the controlled implementation must reconcile the
lineage ledger after installing the reviewed code. It must not silently relabel those changes.

## Required implementation-window gates

1. Stop and verify the Telegram daemon is stopped; do not kill it blindly.
2. Re-run v2 integrity, foreign-key, schema-version, and writer-lock preflight.
3. Record live database and WAL/SHM state, then run the explicit migrator with a new durable
   backup path.
4. Verify backup hash and permissions before installing candidate code.
5. Install the reviewed patch, run entropy, integrity, foreign-key, and full regression tests.
6. Start the daemon, run a smoke event/replay check, and verify no duplicate receipt.
7. Reconcile the two pre-existing source changes and the intentional v3 code changes through
   the existing operator-authorized lineage workflow.
8. If any gate fails, keep the daemon stopped and restore the verified v2 backup before
   reinstalling v2 code.

## Artifacts

- Isolated candidate: `staging/schema-v3-candidate/`
- Deterministic review patch: `architecture/schema-v3/CANDIDATE.patch`
- Patch SHA-256: `16706e0a8ffd0fe1453b337d5a0e8ff970b6a1684e02dd5917dd48e1174572c3`
- Migration module SHA-256: `7f765235ab8b21c11e2e881021c815f3efb57d24cc8ffbf9ef30ae82a6360c9f`
