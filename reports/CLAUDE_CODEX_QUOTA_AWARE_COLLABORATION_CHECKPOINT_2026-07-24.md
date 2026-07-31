# Claude–Codex quota-aware collaboration checkpoint — 2026-07-24

## Verdict

The certified turnstile prevents concurrent writers, but its synthetic
allocation weights do not measure real provider consumption. DFI-05 and the
opening of DFI-06 proved that repeated Codex full reviews can dominate actual
usage even while the ledger reports a nominal 70/30 Sonnet/Codex split.

Artiom reports approximately 90% Claude weekly headroom and 40% Codex weekly
headroom remaining. New work must therefore favour Claude materially while
retaining Codex as an independent gate.

## Observed failure mode

The DFI-06 Codex review prompt required only the single highest-severity
finding. That produced sequential full reviews:

1. missing full/delta `legacy_evidence_ref` identity binding;
2. after repair, omitted `diagnostic_sha256` and `byte_cut` bindings;
3. a third full review began immediately after the second Sonnet repair.

This is safe but economically defective: each review deliberately withholds
additional findings, forcing another full-context model call.

## Safe intervention

- The standalone Gigabyte coordinator was stopped during the third **read-only**
  Codex review.
- No writer was live.
- The DFI-06 candidate remained at
  `82d717c91d5f6d8e0dfabaa32d4ba4d21f1e3be822b43af787ae52b61779dd39`.
- The dead review lease was recovered through the certified turnstile.
- Production STOP remains armed and JAA remains untouched.

## Runtime policy from this checkpoint

1. Sonnet owns implementation, diagnosis, repairs, routine testing, and
   candidate-coherence checks.
2. Codex performs one exhaustive bounded independent review after the candidate
   settles.
3. An exhaustive review reports all material findings, ordered by severity.
4. Sonnet repairs the complete accepted finding set together.
5. Subsequent Codex work is delta review: exact changed hunks, finding closure,
   and affected invariants.
6. Full re-review is permitted only after a material authority/public-contract/
   evidence-semantics change or a demonstrated inability to bound the delta.
7. Failed, rejected, and interrupted calls count as consumption. Missing token
   telemetry is `unknown`, not zero.
8. Synthetic turnstile weights remain admission metadata only and must never be
   presented as actual provider usage.
9. Actual routing follows remaining subscription headroom. With the current
   reported headroom, Claude receives the clear majority of new model work and
   Codex capacity is reserved for coordination and high-value independent
   gates.

## Resume point

Resume DFI-06 from the recovered candidate above. First run deterministic
Sonnet/local coherence checks. Then issue one corrected exhaustive Codex review
of the settled candidate. Do not revive the old “single highest defect” prompt.
All subsequent review must follow the delta protocol above.
