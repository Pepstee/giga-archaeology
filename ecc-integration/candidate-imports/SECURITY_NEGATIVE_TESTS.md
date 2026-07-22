# Security negative tests to port (staged specification)

These are test cases, not imported runtime hooks. Each must fail closed in the eventual local
implementation and pass a clean control fixture.

- Reject dependency manifests containing known compromised package/version pairs; avoid matching a
  package name and unrelated version from different records.
- Reject `pull_request_target` or `workflow_run` jobs that check out attacker-controlled refs.
- Reject dependency-cache restore in privileged workflows and checkout credentials persisted under
  write permissions.
- Reject package installs that allow lifecycle scripts in CI unless explicitly isolated and
  justified.
- Reject shared caches in jobs with OIDC `id-token: write`.
- Reject install-state destinations that escape their owned root through `..` or symlinks.
- Reject executable inline shell assembled with `eval`; require argv-form subprocess execution.
- Reject secrets placed in command-line arguments or persisted raw in governance receipts.
- Reject silent overwrite of existing harness configuration.
- Reject an evaluator promotion without at least one accepted candidate, one rejected negative
  control, named verification and rollback evidence.

Derived from ECC's supply-chain, workflow-security, secret-safe, path-safety and installer test
families at commit `96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`. Before deployment, each item
must be implemented against giga-user's own schemas and tested with local fixtures.
