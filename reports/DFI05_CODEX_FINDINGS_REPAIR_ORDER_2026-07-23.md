# DFI-05 repair order after Codex independent review

You are the sole DFI-05 writer. Do not commit or run the complete suite.

The prior candidate
`420519090abe9ec9195bc90ae222156d2fd498dc559ba90d0093a18640446eb6`
passed its named tests but failed independent review. Repair all four findings
below without weakening any DFI-05 contract.

## Finding 1 — cohort enforcement is not production logic

`control/scope_admission.py` accepts any non-empty `cohort_id` and any
hash-shaped `cohort_seal_id`. It does not validate the canonical seal, bind the
declared cohort, reject `issued_at < sealed_at`, or enforce denominator/minimum/
ceiling semantics.

Repair with the leanest complete canonical cohort-seal verifier used by
admission. Bind the complete seal identity, reject pre-seal/foreign-cohort
admission, and expose deterministic production eligibility/rate evaluation for
both controlled-canary and forward-shadow minima and ceilings. Hard failures
must fail the gate, never enter the rate.

## Finding 2 — exact fallback is not checked before model invocation

`agents/task_manager.py` validates only fallback schema/version before calling
the model. A stale/cross-parent/cross-project/cross-epoch/over-broad runtime
authorization can therefore make the model reachable.

Before prompt construction/model invocation, call the admission verifier and
compare every fallback binding to the task's admitted parent, project, epoch,
intent, manifest, certificate, programme position, slice, and maximum
authority. Any mismatch returns `llm_invoked=false`. Keep proposal validation
as a second gate.

## Finding 3 — repository claim misses embedded bindings

`dispatch/repository.py` checks the outer decision parent but does not require
the embedded fallback's `parent_task_id`, `project`, or `intent_receipt_id` to
match the admitted task.

Require all three, in addition to the current epoch/profile/manifest/
certificate/position/slice/authority checks. Add cross-parent/project/intent
negative tests.

## Finding 4 — replay verifier does not bind full scope/task bytes

`infra/scope_admission.py` ignores `task_contract_hash`; does not recompute the
current-slice hash; and does not validate/bind instruction registry, assurance
contract, findings, and untrusted-data references.

Reconstruct and verify `task_contract_hash`, require a complete closed scope
shape, recompute the slice hash, and verify all listed bindings before
returning scope. Add replay-tampering negatives.

## Non-negotiable gates

- Preserve base, default-off behavior, JSONL authorities, STOP/JAA isolation,
  no side store/config/cache, and all Fable conditions.
- Net counted production additions must remain at most 350. Achieve this by
  consolidating/deleting redundancy; never move production behavior into
  tests/docs. If the complete repair genuinely cannot fit, exit nonzero with
  exact line delta for architecture re-adjudication.
- Run direct focused/affected tests only, Ruff, and `git diff --check`; no
  pipelines and no complete suite.
- Add tests that would fail on each prior defect.
- Report exact tests and production numstat.
