# DFI-06 operator scope ratification and corrective action

Date: 2026-07-24

## Operator decision

Artiom explicitly authorises preserving the signed, host-authoritative review-evidence
journal inside DFI-06 and polishing it to certification. This supersedes the original
180-net-production-line ceiling for this stage only. It does not authorise changes to
production activation, STOP, JAA, daemon behaviour, dispatch, scheduling, or later DFI
stages.

The expanded DFI-06 now owns two connected responsibilities:

1. compare the economics and finding recall of full and delta semantic reviews; and
2. prove that the observations being compared came from the stated candidate, review
   operation, scope, receipts, model-call attempts, and host-controlled evidence stream.

## Why the exception exists

The original comparator could calculate an answer from supplied observations but could
not prove that an agent had not fabricated, rebound, omitted, or altered those
observations. Independent review correctly exposed that trust gap. The repair then
expanded without pausing for operator authorisation, eventually introducing a signed
append-only journal, host-only writer, sealed heads, crash recovery, provenance binding,
and filesystem hardening.

The trust infrastructure is useful and is now deliberately retained. The way it entered
the stage was not acceptable.

## Authorised implementation boundary

Production changes are limited to:

- `host_controller/__init__.py`
- `host_controller/journal_writer.py`
- `infra/ed25519_sig.py`
- `infra/schema_registry.py`
- `validation/delta_economics.py`
- `validation/delta_obs_support.py`
- `validation/delta_review_telemetry.py`
- `validation/evidence_journal.py`
- the minimum necessary changes in `validation/findings.py` and
  `validation/host_assurance.py`

Tests and DFI-06 documentation may change where they directly verify this boundary.
No other subsystem may be modified without another explicit scope decision.

The warning threshold is 1,800 net new production lines over commit `4be0741`. The hard
stop is 2,200. If correctness appears to require crossing the hard stop, work pauses for
an architecture decision rather than hiding code in helpers, tests, generated files, or
side stores.

## Certification bar

DFI-06 is certified only when all of the following are true:

- every original DFI-06 acceptance and negative-control test passes;
- all signed-journal, crash-recovery, tamper, wrong-key, symlink, descriptor, exact-schema,
  scope-substitution, and failed-model-call tests pass;
- the complete orchestrator-v3 test suite passes from a clean candidate;
- public comparison cannot accept manually constructed, unsigned, optionally identified,
  or provenance-incomplete observations;
- the host controller is the sole journal writer and private signing material never
  enters worker or validator authority;
- interrupted append recovery proves both the prior-state and proposed-state branches;
- missing usage remains unknown and never becomes zero or eligible savings;
- an independent Codex review returns an exact `VERDICT: PASS`;
- the candidate is committed with a certificate containing hashes, commands, results,
  rollback instructions, and the remaining limitations.

No production activation is implied by certification.

## Corrective action — the orchestrator's slap on the wrist

The review loop violated scope governance even though individual findings were technically
reasonable. From this checkpoint onward:

1. A reviewer finding that requires a new persistence authority, cryptographic trust root,
   controller, public API, or more than 25% of the remaining stage budget is labelled
   `ARCHITECTURE_EXPANSION`, not an ordinary defect.
2. An `ARCHITECTURE_EXPANSION` halts automatic repair until the operator or named design
   authority ratifies a new work order.
3. Coders may repair only the current finding ledger. They may not follow a chain of
   adjacent improvements that was absent from that ledger.
4. One exhaustive independent review is followed by bounded delta reviews. A new
   exhaustive review requires a candidate-bound reason.
5. A passing self-report, large test count, or reviewer enthusiasm is not certification.
   Scope, candidate hash, full-suite evidence, and an independent verdict remain mandatory.

DFI-07 may begin only after the expanded DFI-06 certificate exists and this corrective
record is included in its inherited context.
