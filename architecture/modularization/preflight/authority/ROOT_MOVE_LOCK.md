# Root-move single-writer and acceptance contract

**Schema:** `giga.modularization.root-move-lock.v1`  
**Applies to:** any rename, relocation, split, archival, externalisation or
compatibility-shim change involving a top-level path in `giga-user`  
**Wave 0A state:** definition only; no lock acquisition and no move is authorised
by this file

## Authority and boundary

The target modular architecture is authorised by the operator, subject to the
deterministic preflight gates below. The Mac is the canonical host under
`architecture/machine-authority.v1.json`. Gutua, staging trees, upstreams and
other copies are candidate or evidence sources and never acquire authority from
timestamp, size or apparent completeness.

This contract cannot authorise a move whose entry in `authority-map.v1.json`
has a blocked ambiguity. It cannot mutate or reconcile Dubbing Studio.

## Lock primitive

The single-writer lock is an atomically created directory:

```text
~/.giga/locks/giga-user-root-move.v1.lock/
├── owner.json
├── heartbeat
└── preflight-receipt.json
```

Acquisition uses one `mkdir` operation. Failure with `EEXIST` means another
writer or an unresolved stale lock exists; the contender must stop without
editing the repository.

`owner.json` binds:

- schema and random 256-bit nonce;
- canonical repository realpath, filesystem device and root inode;
- hostname, boot identity, PID and process start time;
- actor/task identifier;
- Git HEAD, branch and porcelain-status digest;
- exact SHA-256 of `authority-map.v1.json`;
- acquisition time, 15-second heartbeat interval and 120-second stale threshold;
- authorised migration-order interval and exact source paths.

The owner creates `preflight-receipt.json` before its first repository mutation.
The heartbeat is updated atomically by writing a sibling temporary file and
renaming it over `heartbeat`.

## Stale-lock recovery

A missing heartbeat is not permission to delete the lock.

Recovery requires all of:

1. the recorded host and boot identity match the current machine;
2. the PID is absent **and** its recorded process-start identity cannot belong
   to a recycled PID;
3. heartbeat age exceeds 120 seconds;
4. the repository status digest still matches the preflight receipt, proving no
   unaccounted partial move occurred;
5. an explicit recovery receipt records the old owner, nonce, timestamps,
   checks and disposition.

If any condition is unknown, preserve the lock and stop. Cross-host stale-lock
recovery requires an operator-authorised receipt; it is never automatic.

## Acceptance gate

The root-move worker may acquire the lock only when every gate is true:

1. **Manifest validity:** `validate_authority_map.py` passes against the live
   root, exact exhaustive skill inventory and current authority contracts.
2. **No blocked ambiguity in the batch:** entries may remain blocked globally,
   but the requested batch contains only `ambiguity.state=resolved` entries and
   all of their dependencies are resolved or deliberately retained.
3. **Bound candidate:** the manifest SHA-256, Git HEAD, dirty-state digest,
   target paths, migration order and compatibility plan are sealed in the
   preflight receipt.
4. **Protected evidence:** every affected protected or provenance-bearing path
   has a verified pre-move hash/tree digest. Raw exports, `corpus/`, `memory/`,
   research evidence, independent Market Aligner and candidate/upstream trees
   are never rewritten in place.
5. **Reference closure:** tracked files, untracked candidate files, launch
   agents, systemd units, tests, manifests, hashes, absolute paths and external
   schedules have been searched. Every reference has an explicit rewrite,
   compatibility shim or verified no-impact ruling.
6. **Skills boundary:** GIGA-owned skill sources, active personal/system skills,
   external plugins, caches/catalogues and historical/upstream copies retain
   their distinct ownership classes. No cache or upstream copy is promoted by
   physical presence. Skill mutation requires the separate skill lifecycle.
7. **Single candidate branch/worktree:** the move runs on a named Mac branch or
   isolated worktree. No second root-move worker, background organiser or
   synchroniser is active.
8. **Ordered dry run:** the exact batch has passed a no-write simulation in the
   manifest's `migration_order`; target collisions and case-folding conflicts
   are zero.
9. **Rollback:** source paths remain recoverable until the new paths,
   compatibility layer and relevant tests pass. No destructive cleanup is part
   of the move transaction.

## Execution and release

For each order group:

1. re-verify the lock nonce, heartbeat, Git/status digest and source hashes;
2. apply only the sealed path set;
3. install declared compatibility shims before changing callers;
4. run focused tests, reference audit, root-layout audit and relevant full
   regression suite;
5. verify protected hashes and immutable evidence baselines again;
6. emit a migration receipt binding old path, new path, pre/post hashes, commit,
   tests and any compatibility period;
7. stop on the first mismatch; do not advance to the next order group.

Release requires a candidate-bound review, a clean validator result for the new
root, and a promotion receipt. Source retirement or compatibility-shim removal
is a later operation with its own reference proof. The lock is released only
after the final receipt is durable; release renames the lock directory into a
timestamped receipt directory rather than deleting its evidence.
