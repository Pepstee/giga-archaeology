# DFI-05 mechanical repair F4 — full replay bindings

You are the sole writer. Fix only Codex finding 4 in the current fresh
worktree. Do not commit.

`infra/scope_admission.py::verify_scope_admission` must reject replayed or
hand-authored scope bytes that differ from what the host admitted.

Required:

- require the exact closed scope shape;
- validate/bind instruction registry;
- validate/bind assurance contract;
- validate/bind findings and untrusted-data references;
- recompute and bind `current_slice_hash`;
- reconstruct the original pre-admission task contract by removing only the
  host-added admission/scope keys from a copy, then verify
  `admission["task_contract_hash"]`;
- preserve every existing project/epoch/manifest/certificate/position/freeze
  check.

Add focused replay-tampering negatives for task contract, slice,
instruction-registry, assurance, findings, and untrusted-data changes.

The whole stage is already exactly 350 net production lines. This repair must
be substitution/deletion-funded: consolidate duplicated validation between
admission issue and replay verification, reuse existing canonical/schema
helpers, and remove redundancy. Do not move logic to tests/docs.

You may inspect only the relevant `infra/scope_admission.py` hunk in the
read-only overflow patch as a correctness reference; do not apply the patch or
copy the whole file.

Run the smallest focused tests, Ruff, and `git diff --check`. Report exact net
production against `dcf5097`. Exit nonzero if the complete repair cannot remain
at or below 350.
