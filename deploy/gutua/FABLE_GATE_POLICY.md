# Fable gate escalation policy

## Verdict

A recoverable gate must not terminate an unattended software-factory window.
The coordinator sends a complete, hashed evidence packet to the actual Claude
`fable` model and follows its structured ruling. The ruling itself grants no
certificate: every required proof must still pass.

## Gate flow

```text
gate raised
  → freeze the affected writer
  → preserve candidate and recompute hashes
  → build complete context/evidence packet
  → obtain structured Fable ruling
  → verify ruling preconditions
  → continue, repair, grant bounded scope exception, quarantine, or redirect
  → append packet/ruling/receipt hashes to the stage journal
```

Fable receives:

- `00_MASTER.md`, `CHARTER.md` and `CONTEXT.md`;
- the deterministic-infrastructure and commercial-readiness roadmaps;
- the original Fable assessment and every durable Fable ruling;
- the exact gate report and relevant logs;
- candidate HEAD, status, complete textual diff and diff statistics;
- production HEAD, status and STOP evidence;
- any stage-specific work order, certificate or checkpoint named by the gate.

The broker invokes the real `fable` model alias. It does not call Sonnet or Opus
and rename the result. Each call is stateless so app-chat memory cannot silently
affect a ruling; all relevant context is reconstructed from durable evidence.

## Decisions

- `CONTINUE`: the gate is satisfied or non-blocking.
- `REPAIR_WITHIN_SCOPE`: fix the named defect and rerun the named proofs.
- `APPROVE_SCOPE_EXCEPTION`: allow only the exact files/actions in the ruling.
- `QUARANTINE_AND_CONTINUE`: isolate the blocked artefact and continue
  independent work.
- `REDIRECT`: move to another authorised productive stage while preserving the
  blocked candidate.
- `HARD_STOP`: immediate irreversible danger, containment loss, corrupted
  evidence, or genuinely non-delegable authority.

Ordinary test failures, missing fixtures, reversible build metadata, provider
quota and architecture proposals are escalation events, not automatic stops.
Provider failure triggers bounded retry and safe independent work; it must not
be interpreted as permission to fabricate Fable's ruling.

## Non-negotiable boundaries

- Fable advice cannot certify a failing candidate.
- No weakening or deleting tests to obtain a pass.
- No production or JAA mutation unless the active work order authorises it.
- One mutable model worker per worktree.
- Candidate, packet, ruling and proof hashes are retained.
- STOP and repository-integrity changes are escalated immediately.
- If Fable orders `HARD_STOP`, the coordinator preserves state, alerts the
  operator and continues only work explicitly identified as isolated and safe.

## Constitutional semantic-review boundary

For a v1 constitutional work order, deterministic code owns schema, hashes,
Git state, path/action authority, rollback binding, proof presence and receipt
verification. Fable receives the work order, canonical Constitution and a
read-only Git summary with no tools and no mutation authority. It may return
only `PASS`, `WARN` or `HELD_FOR_REVIEW`, structured reasons and confidence.

Fable does not hard-reject implementation style, decide technical correctness
or certify completion. Ambiguous contextual judgment is held for the operator.
An override is exact-scope, expiring and hash-chained and cannot waive a
mechanical safety or evidence failure.
