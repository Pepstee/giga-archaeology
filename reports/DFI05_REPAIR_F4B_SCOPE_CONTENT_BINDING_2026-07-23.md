# DFI-05 replay repair F4B — bind full scope contents

You are the sole writer. Correct one remaining mechanism from F4. Do not
commit.

The current verifier validates the closed scope and several identities, but
`freeze_marker` still hashes only manifest ID + epoch. Therefore schema-valid
changes to `findings` or `untrusted_data` list contents are not cryptographically
bound to host admission.

Make the existing freeze marker bind the complete closed `scope` bytes plus
factory epoch in both:

- `control/scope_admission.py` when issuing admission;
- `infra/scope_admission.py` when replay-verifying it.

Use the existing canonical helper and domain/version; substitute the current
reduced freeze payload rather than adding a parallel field or validator.

Add two negatives that change a valid findings list item and a valid
untrusted-data list item while preserving list shape; both must be rejected.

Run the focused test file, Ruff on changed files, and `git diff --check`.
Production must remain at most 350 net lines against `dcf5097`; this should be
line-neutral. Do not touch any other finding or commit.
