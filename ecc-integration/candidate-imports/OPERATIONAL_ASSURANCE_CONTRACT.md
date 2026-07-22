# Operational assurance contract (staged, not deployed)

## Evidence before a readiness claim

A readiness assessment names the exact release surface and records, when applicable:

- build, type, lint and test results;
- deterministic security and secret checks;
- changed-file/diff review;
- migration, retry, idempotency and recovery evidence;
- startup, health, observability and incident-owner paths;
- rollout and rollback instructions;
- critical user-path or end-to-end evidence;
- evidence checked and evidence still missing.

Checks are `pass`, `fail`, `unavailable` or `not-applicable` with source and timestamp. Missing
evidence is never converted to a passing score.

## Score caps

- Any unresolved sensitive authorization, exposed secret, unsafe destructive migration,
  non-idempotent high-impact webhook or missing high-impact rollback caps readiness below release.
- Non-green CI or an untested launch-critical path caps readiness below an unconditional “ready.”
- A numeric score prioritises work; it does not override a failed cap.

## Current-lane rule

A project lane is current only when it has all three:

1. one owner artifact;
2. one current evidence source;
3. one concrete next action.

Public queues, external trackers, local handoffs and repository roadmaps remain separate surfaces.
Sync records completed receipts; it does not manufacture activity or release authority.

Sources: ECC `production-audit`, `verification-loop`, progress-sync and observability-readiness
documents at commit `96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`. No remote scanner or release
command is imported.
