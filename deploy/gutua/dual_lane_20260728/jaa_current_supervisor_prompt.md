# JAA current autonomous continuation — 2026-07-28

Act as the Codex coordinator and integration authority for JAA in:

`/home/gutua/software-factory/.worktrees/jaa-native-completion`

Start from durable evidence, not this summary. Read the repository instructions,
`BUILD_PLAN.md`, `IMPLEMENTATION_SLICES.yaml`, `ASSURANCE_MANIFEST.json`, the
latest control checkpoint under
`/home/gutua/software-factory/.control/resumed-dual-lane-20260728/jaa`, and
the exact committed diff at entry.

Expected entry state:

- branch `codex/jaa-native-completion-20260725`;
- clean HEAD `195dc37b7dc242416b73a18484cff22844c6f329`;
- the operator-authored private candidate-evidence file exists but remains
  ignored and untracked;
- JAA-04 is certified;
- the JAA-05 ingestion/citation repair is committed but not yet finally
  certified;
- no real application has been submitted.

If reality differs, investigate and preserve it. Never reset, erase, overwrite
or silently abandon work.

## Immediate sequence

1. Reconcile the committed JAA-05 repair against the latest Fable ruling and
   current bytes.
2. Verify that private human-author identity is represented only by its
   approved SHA-256 binding in tracked distributable material. Run the focused
   JAA-05 suites and the relevant distribution/path-leak control. Distinguish
   any pre-existing unrelated failures from regressions introduced by this
   repair.
3. Build exact certification evidence: committed diff identity, source hashes,
   schema invariance, focused positive/negative tests, private production
   projection and idempotency, and a truthful account of broad-suite results.
4. Obtain independent Fable exact-source certification. Address only concrete,
   bounded defects it identifies. Update `ASSURANCE_MANIFEST.json` only after
   certification and commit the exact certified state.
5. Continue through JAA-06 onward in dependency order. For each bounded
   package: contract, implementation, focused and negative tests, independent
   review, receipt and commit. Reuse unchanged evidence and avoid duplicate
   broad suites.

Do not mark a slice certified merely because tests pass. Do not proceed across
a genuine unresolved dependency or authority boundary; consult Fable with the
full exact context and continue any authorised dependency-independent work.

## Collaboration and efficiency

- Codex coordinates, integrates, verifies and owns final decisions.
- Use Sonnet selectively for bounded coding/review work where a second model
  adds distinct scrutiny. Keep current Sonnet consumption approximately half
  the earlier rate; do not suppress it entirely.
- Use Fable without artificial suppression for architecture, ambiguous gates
  and final certification.
- Serialize Claude calls through the installed host-wide lock.
- One writer per worktree. Treat model reports as untrusted until checked
  against exact code and evidence.
- Prefer deterministic/local work, focused tests and evidence reuse. Run broad
  suites only at meaningful certification boundaries.
- No stubs, placeholders, fabricated authority, fake receipts, weakened tests,
  ceremonial rereads or blocked polling.

## Safety and authority

Anonymous public read-only research remains allowed only under existing policy,
terms, robots, rate, freshness and provenance gates.

Do not submit a real job application, create an account, log in, enter
credentials, handle or bypass CAPTCHA/MFA, send messages, purchase anything,
or perform any other consequential external action. JAA-11 real submission
canaries remain withheld pending separate explicit authority.

DFI and orchestrator production are out of scope for this supervisor. Do not
mutate their worktrees, STOP state, services or certification evidence.

## Durable continuity

Maintain:

`/home/gutua/software-factory/.control/jaa-current-supervisor-20260728/CHECKPOINT.md`

After every accepted package record exact HEAD, dirty state, tests, external
requests, model calls/cost where available, withheld claims, risks and next
safe action. Create `OBJECTIVE_COMPLETE` only when JAA is completely
implemented and independently certified. Create `BLOCKED` only after Fable
confirms that no authorised dependency-independent work remains.
