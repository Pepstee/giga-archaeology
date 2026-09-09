# ECC extraction boundary and deferred deterministic enforcement

## Deferred until extraction is complete

Repository-wide deterministic enforcement is necessary if “deterministic first” is to become a
guarantee rather than a convention. It is deliberately deferred until the useful ECC extraction
is complete.

The later enforcement slice should require every official execution path to:

1. resolve a registered deterministic adapter before considering an LLM;
2. validate current evidence, freshness and authority;
3. treat model output as a proposal rather than verified evidence;
4. refuse unavailable or unauthorised work instead of bypassing the registry;
5. emit a deterministic receipt for every accepted transition;
6. fail CI when an official entry point bypasses the execution gate.

## Freeze during extraction

Until the extraction-complete decision is recorded:

- do not rewire all giga-user CLIs, scheduled jobs, Jarvis or external adapters;
- do not introduce a global execution gateway;
- do not claim the current adapter registry universally enforces deterministic routing;
- stage portable ECC findings only under `ecc-integration/`;
- allow only validation and documentation changes needed to prove the extraction itself.

## Extraction-complete gate

The freeze can be lifted only after the pinned ECC source has:

- complete file and skill disposition coverage;
- a portable-finding ledger with source hashes and explicit import/defer/reject decisions;
- staged artifacts for every imported finding;
- tests proving staged contracts are internally consistent and non-executable;
- an explicit list of remaining on-demand material rather than an undefined “more to inspect.”

Lifting the freeze authorises design review, not automatic deployment.

## Skills/ECC supervisor checklist

### 2026-08-24 — Slice 1: deterministic SkillTree truth replay

- [x] Objective: make the existing SkillTree registry and canonical human status reproducible and
  fail closed on drift without changing any of the 137 capability decisions.
- [x] Keep `skilltree/IMPLEMENTATION_STATUS.md` as the single generated human status surface and
  preserve `skilltree/IMPLEMENTATION_REPORT.md` as a relative compatibility symlink.
- [x] Add a read-only evidence-root boundary so the isolated source lane can verify ignored live
  evidence without copying it or writing to it.
- [x] Add mandatory check mode for the registry, status file and compatibility symlink.
- [x] Make normal registry/status generation a same-directory staged pair with restoration on a
  failed replacement; surface incomplete rollback instead of claiming false success.
- [x] Preserve immutable export hashes and exact decisions: 137 total; 7 implemented, 2 external,
  1 partial, 5 available, 2 blocked and 120 documented.
- [x] Non-goals preserved: no ECC pin/import decision, routing, live service, architecture-control,
  product-code or upstream-ECC byte change.

Acceptance evidence:

- `python3 -m pytest -q tests/test_skilltree_operator.py` — 14 passed.
- `python3 ecc-integration/scripts/validate_extraction.py` — pass; 3,330 inventory hashes, 278
  canonical skills, 12 ledger entries, 15 portable findings and 10 staged specifications.
- `python3 ecc-integration/candidate-imports/governance-kit/validate_contracts.py` — pass.
- `python3 -m pytest -q tests/test_skilltree_operator.py ecc-integration/tests
  tests/test_operator_status.py tests/test_adapter_evidence.py tests/test_cross_service_monitor.py`
  — 54 passed.
- Real check using the isolated source root plus read-only `/Users/admin/Documents/giga-user`
  evidence root — pass with the exact pinned counts above.
- `skilltree/implementation-registry.json` SHA-256 remains
  `cd39dfe4167c34a0b0a6fb986d9e9e0144e088575505e8c017aa4dd63c32773a`;
  `skilltree/IMPLEMENTATION_STATUS.md` remains
  `f12a6f82ef180477964bdf44da919583e00705b3a5ac6c97de5012abd8ebcd6c`.

Changed paths are exactly:

- `deploy/skills/skilltree-operator/SKILL.md`
- `deploy/skills/skilltree-operator/references/status-contract.md`
- `deploy/skills/skilltree-operator/scripts/audit_tree.py`
- `skilltree/IMPLEMENTATION_REPORT.md` (regular-file compatibility copy to relative symlink)
- `tests/test_skilltree_operator.py`
- `ecc-integration/FUTURE_WORK.md` (this existing checklist)

Slice 1 was independently reviewed, committed as Artiom in `487819b326dfed2431f3df4d913fe871d8c18204`
and pushed to `origin/codex/skills-ecc-supervisor-20260824`.

Blocker: this Codex thread still owns an earlier blocked ChallengeLab goal, so the goal API refuses
creation of the requested Skills/ECC persistent goal. Repository work and checkpointing continue;
the goal record must be reconciled separately without falsely completing the older objective.

### 2026-08-24 — Slice 2: mandatory combined Skills/ECC verification

- [x] Reuse `ecc-integration/scripts/validate_extraction.py`, the existing extraction-completion
  verifier, instead of creating a parallel verification component.
- [x] Make the Slice 1 SkillTree registry/status/compatibility replay mandatory on every successful
  extraction validation; there is no flag that bypasses the capability-truth check.
- [x] Accept one explicit read-only evidence root, default it to the source root and fail closed when
  ignored live evidence is unavailable rather than trusting tracked generated files.
- [x] Invoke the canonical audit through a fixed argument list with no shell, contained source and
  governed paths, a bounded timeout and stable structured failure codes.
- [x] Bind the successful combined verdict to all 3,330 ECC source hashes, the pinned ECC commit,
  all 137 SkillTree decisions, both canonical generated hashes and the exact relative compatibility
  target.
- [x] Detect changes to the registry, status or compatibility target during replay instead of
  emitting a mixed-state success receipt.
- [x] Preserve non-goals: no capability decision, evidence map, ECC pin/finding/import decision,
  routing, service, product, architecture-control or upstream-ECC change.

Acceptance evidence:

- `python3 -m pytest -q ecc-integration/tests/test_validate_extraction.py` — 9 passed, including
  missing evidence, registry drift, status drift, compatibility drift, child-contract failure,
  timeout, spawn failure and replay-race controls.
- `python3 -m pytest -q tests/test_skilltree_operator.py ecc-integration/tests
  tests/test_operator_status.py tests/test_adapter_evidence.py tests/test_cross_service_monitor.py`
  — 60 passed.
- `python3 ecc-integration/candidate-imports/governance-kit/validate_contracts.py` — pass.
- Two real combined validations using the isolated source root, pinned lane ECC checkout and
  read-only `/Users/admin/Documents/giga-user` evidence root emitted byte-identical JSON.
- The combined result preserves 3,330 verified ECC hashes, 278 canonical ECC skills, 11 adaptation
  candidates, 15 portable findings, 10 staged specifications and 12 ledger entries. It also binds
  the unchanged 137-job counts plus registry SHA-256
  `cd39dfe4167c34a0b0a6fb986d9e9e0144e088575505e8c017aa4dd63c32773a` and status SHA-256
  `f12a6f82ef180477964bdf44da919583e00705b3a5ac6c97de5012abd8ebcd6c`.
- The same command without the external evidence root exits 2 with stable reason code
  `skilltree-replay-failed`; tracked generated files alone cannot satisfy the gate.

Changed paths are exactly:

- `ecc-integration/scripts/validate_extraction.py`
- `ecc-integration/tests/test_validate_extraction.py`
- `ecc-integration/FUTURE_WORK.md` (this existing checklist)

Next smallest slice after promotion: perform a read-only decision review of the existing staged
deterministic-execution-gate finding, select one already-official no-mutation entry point, and turn
only that path into an evidence-backed deterministic-first vertical slice. Do not claim universal
routing or widen to a second entry point until the first path has stable receipts and negative
controls.

### 2026-08-24 — Slice 3: deterministic admission on one no-write onramp

- [x] Reuse the existing adapter registry, operator-status compiler and official
  `python3 scripts/operator_status.py --no-write` entry point; no second router or receipt system
  was created.
- [x] Admit exactly one `operator-status-local` adapter before compiling the no-write snapshot and
  bind its registry, record, implementation, source-document and test-evidence hashes.
- [x] Require the adapter to remain native, verified, read-only, no-authority and no-command-
  execution with the exact declared onramp.
- [x] Re-hash the selected adapter's current files without following declared symlinks and reject
  malformed records, drift, races, stale evidence, duplicate IDs and registry identity changes
  with stable reason codes.
- [x] Recompute the admission receipt inside the compiler, require an exact field set and reject
  caller-forged or replayed receipts that differ from current evidence.
- [x] Keep the mutating operator-status path available but give it no adapter admission; the
  no-write path ignores `--output` and preserves both requested and default output files.
- [x] Preserve non-goals: no manifest command execution, LLM routing, second onramp, service,
  product, capability decision, ECC extraction decision or universal-routing claim.

Acceptance evidence:

- `python3 -m pytest -q tests/test_operator_status.py tests/test_adapter_evidence.py` — 46 passed.
- `python3 -m pytest -q tests/test_skilltree_operator.py ecc-integration/tests
  tests/test_operator_status.py tests/test_adapter_evidence.py tests/test_cross_service_monitor.py`
  — 77 passed.
- `python3 ecc-integration/candidate-imports/governance-kit/validate_contracts.py` — pass.
- Two combined Skills/ECC validations were byte-identical with SHA-256
  `b05a414a5e8b4a068581097edbb0377275000f7dca7461e1f959c630510ece6f`; they preserve the
  3,330-file ECC pin and exact 137-job SkillTree truth.
- Two real no-write status runs were byte-identical with SHA-256
  `0635035b2a3d5698c64923f530f908a3670dd3fa41a35be7a0260e71907a45e4`; the receipt records
  `commands_executed=false`, registry SHA-256
  `f25e6d3193fae76756eeedbed6ba7dbd28ffdd409dc7b821824d2e94fa4a288e` and selected adapter
  record SHA-256 `0c1ab925413205ea379db75d85830ff6aa0b120277f2dff2781791d91db2be3e`.
- The isolated real run used read-only copies of the four existing ignored scientific-evidence
  receipts required by the pre-existing adapter registry; they were removed after verification
  and are not part of this change set. Portable CLI tests use a complete isolated fixture.
- Canonical registry regeneration also rebound two already-changed scientific-adapter file hashes
  (`research/elicit/README.md` and `twin_core/scientific_pipeline_cli.py`). No adapter ID, declared
  or effective state, authority, command-execution flag or capability decision changed.

Next smallest slice after promotion: select one existing proposal-producing path and design a
deterministic route-decision receipt that can prefer a verified adapter or hold safely, without
executing the proposal, granting mutation authority or widening beyond that single consumer.

### 2026-08-24 — Slice 4: Telegram proposal route in observe-only mode

- [x] Reuse the selected boundary in `architecture/10_DETERMINISTIC_EXECUTION_BOUNDARY.md` and the
  existing Telegram proposal lifecycle; no provider, proposal validator, commit path or database
  schema was replaced.
- [x] Add one canonical execution-capability registry and one in-process policy kernel. These are
  new files because execution routing has a distinct authority lifecycle: the existing adapter
  registry is evidence-only and must never become execution authority.
- [x] Register exactly one capability, `telegram-memory-proposal`, for the exact
  `scripts.jarvis_telegram:_process_update` caller and bind eight implementation/test evidence
  files by current size and SHA-256.
- [x] Validate closed request and registry fields, strict JSON without duplicate/non-finite values,
  contained non-symlink paths, unique sorted IDs/evidence, current bytes, budgets, authority,
  caller, target, receipt type and registry version.
- [x] Emit a deterministic decision bound to the request, registry, capability record and evidence;
  both matching and refusal decisions set `execution_authorized=false`,
  `authority_granted=false` and `command_execution=false`.
- [x] Record the shadow decision before the existing Telegram worker through the existing
  TwinStore receipt mechanism. A committed memory replay returns before both routing and provider
  work, so it creates no extra receipt or token call.
- [x] Preserve Phase 1 semantics honestly: a shadow refusal does **not** block the legacy provider
  yet, and its receipt explicitly records `provider_execution_governed=false`. No live service was
  restarted or deployed from this branch.

Acceptance evidence:

- `python3 -m pytest -q tests/test_execution_policy.py tests/test_telegram_pipeline.py
  tests/test_jarvis_telegram.py` — 16 passed; provider calls were faked and no real model ran.
- Broad Skills/ECC/operator/Telegram suite — 93 passed.
- The governance-kit validator passed, and two combined Skills/ECC validations remained
  byte-identical with SHA-256
  `b05a414a5e8b4a068581097edbb0377275000f7dca7461e1f959c630510ece6f`.
- Real registry SHA-256:
  `a14561ffbf9c1b1ad9f78341e0153d9a528950ff163620ffa26a5110a2cb5863`;
  capability-record SHA-256:
  `dc193c7daf9453bda4a69594ab32d1447d9682c929f60fdddc4d8b956c851c13`.
- Two fixed real-registry decisions were equal. Canonical decision SHA-256:
  `b26d9121ef60f5ea9fe54a3be7f3772685df5b97b4a266cb91153b0b6401e4c3`.
- The database receipt's bound `shadow_decision` is deterministic; TwinStore's outer receipt ID
  and recorded timestamp are intentionally operational metadata and are not byte-identical.

Known limitation found without widening this slice: the current canonical memory tree has an
entry absent from `memory/INDEX.md`, so the actual no-operation memory-validation tail can fail
after the shadow receipt and patched test worker run. This slice records that downstream condition
but does not repair memory canon or claim Telegram execution success.

Next smallest slice after promotion: add a static bypass audit for this one official Telegram
surface and shadow telemetry comparison. Enforcement must remain off until the audit proves the
only provider call is the registered provider boundary and the pre-existing memory-index drift is
resolved independently.

### 2026-08-24 — Slice 5: static bypass audit for the staged Telegram seam

- [x] Reuse the canonical execution registry and policy kernel from Slice 4. The new auditor has a
  distinct lifecycle because it verifies source wiring for CI/evidence and never decides or
  executes a request.
- [x] Audit exactly `scripts/jarvis_telegram.py` and `twin_core/telegram_pipeline.py` for the one
  registered `telegram-memory-proposal` capability and approved
  `scripts.jarvis_telegram:_process_update` caller.
- [x] Require one exact unaliased provider-boundary import, one provider call only inside `_worker`,
  one policy call only inside `_shadow_route`, and one `process_event` call binding `_worker` and
  the `_shadow_route` observer.
- [x] Require the pipeline to import no provider adapter, call the route observer and worker exactly
  once, and place the shadow receipt syntactically between those calls.
- [x] Bind the auditor and its adversarial tests into the existing capability evidence, revalidate
  all evidence before parsing, reject non-canonical/symlinked/drifted/racing sources and emit a
  deterministic hash-bound no-authority receipt.
- [x] Preserve Phase 1 semantics: the audit does not run the provider, does not grant authority,
  does not block a shadow refusal at runtime and does not claim coverage of dynamic imports,
  monkeypatching, arbitrary owner scripts, other providers or any second official surface.

Acceptance evidence:

- `python3 -m pytest -q tests/test_execution_bypass.py tests/test_execution_policy.py
  tests/test_telegram_pipeline.py tests/test_jarvis_telegram.py` — 27 passed.
- Broad Skills/ECC/operator/Telegram suite — 104 passed.
- Governance-kit validation passed. Two combined Skills/ECC validations remained byte-identical
  with SHA-256 `b05a414a5e8b4a068581097edbb0377275000f7dca7461e1f959c630510ece6f`;
  the 3,330-file ECC pin and all 137 SkillTree decisions are unchanged.
- Two real static audits were byte-identical. Canonical CLI output SHA-256:
  `9107610678941e8673595945c68c012b3ed27fcb7954065bf508a17351fe9781`; embedded receipt
  SHA-256: `825fa0bcccc0b0603b7cd44eecf9844ad883b5cb13ced9ca933c18f475e7eb81`.
- Registry SHA-256:
  `4f7201fe8b121e7d3438ad9f072625ebe7e210f395417a54450e6ed7e65747ca`; capability-record
  SHA-256: `48e62ea8a78d4ce5d57613e5f8c3f0b49896704212c2ea94ce72a94de69f4293`.
- Negative fixtures prove a second provider call, aliased provider boundary, changed worker
  binding, provider import in the pipeline, worker-before-receipt order, symlink and evidence drift
  all block deterministically. No real provider or live service was used.

Next smallest slice after promotion: compare shadow route receipts with actual provider-attempt and
completion receipts for this same seam using local fixtures, and separately reconcile the existing
memory entry/index drift. Do not turn enforcement on until both are verified; do not widen to a
second caller.

### 2026-08-24 — Slice 6: local shadow-versus-legacy receipt comparison

- [x] Reuse TwinStore receipts and the existing Telegram pipeline; no new database, schema,
  telemetry service, report store or execution gateway was created.
- [x] Add one generic read-only TwinStore query for the latest operation receipt of any status so a
  failed completion remains evidence rather than disappearing behind the committed-only replay
  query.
- [x] Record one observe-only provider-boundary receipt after the shadow receipt and immediately
  before the legacy worker call. Bind it to the exact shadow-decision hash and processing-attempt
  number.
- [x] Compute a deterministic read-only comparison from the shadow, provider-boundary and final
  completion receipts. Missing records return `incomplete`; malformed hashes, contradictory attempt
  numbers and decision-binding drift fail closed with stable reason codes.
- [x] Mark a shadow refusal followed by the legacy boundary as `mismatch`; keep provider failures
  visible as `LEGACY_COMPLETION_NOT_COMMITTED`; never convert either into enforcement readiness.
- [x] Extend the existing AST audit to require the exact source order: observer, shadow receipt,
  provider-boundary receipt, worker.
- [x] Preserve limitations: the pre-call boundary receipt proves local control reached that point,
  not that an external provider process actually started or completed; comparisons are computed on
  demand and are not an enforcement authority; no live service or provider was used.

Acceptance evidence:

- Focused execution, store, Telegram and bypass suite — 40 passed.
- Broad Skills/ECC/operator/Telegram/store suite — 117 passed.
- Governance-kit validation passed. Two combined Skills/ECC validations remained byte-identical
  with SHA-256 `b05a414a5e8b4a068581097edbb0377275000f7dca7461e1f959c630510ece6f`;
  the ECC pin and 137 SkillTree decisions remain unchanged.
- Two static audits were byte-identical. Canonical CLI output SHA-256:
  `77784095e06088df8591de9270af22ad90305f9ade038bf8a7b66c69cf7486c9`; embedded audit
  receipt SHA-256: `a94f92ee664b75bd8ad2a21d36c55dd4ec74c746c3dbe58a192c1ce32a9edf49`.
- A fixed local success fixture produced byte-identical comparison output with file SHA-256
  `3a046f9bbecda3b3c3acfce1bf2c20b5e72613fcbf950a5dda992fed08d5c670` and embedded
  comparison SHA-256 `0d4a7094a450af032d19370effacc2ec8401ac30e70be437c1dc3640d9b29125`.
- Registry SHA-256:
  `155f3e79d531a35a1e69a2bd612dc0f0bdc7366c5eaebb89fb69ea2b90a0f53f`; capability-record
  SHA-256: `4c913cc8cad2bfed7c372f3024a512153f746a979678f00e7d89c629db30fa70`.
- Negative fixtures prove shadow-refusal mismatch, missing telemetry, failed completion, wrong
  decision binding, telemetry race, missing boundary receipt and wrong source order. All
  workers/providers were local fakes.

Next smallest slice after promotion: reconcile the pre-existing memory entry/index drift as its own
canon-maintenance checkpoint, then define the bounded operator-authorised live shadow sample needed
before any enforcement decision. Do not collect live provider telemetry or enable enforcement from
this branch.

### 2026-08-24 — Slice 7: canonical memory-index reconciliation

- [x] Reuse the existing `memory/INDEX.md`, memory protocol and canonical validator; no second
  index, repair script, memory entry or report surface was created.
- [x] Preserve the existing memory entry byte-for-byte and replace only its unresolvable legacy
  wikilink with the repository's canonical relative Markdown-link representation.
- [x] Capture the failing pre-repair receipt: 70 entries, 69 indexed entries, one
  `index-coverage` error and two pre-existing provenance warnings.
- [x] Prove the repaired source branch has 70 entries, 70 indexed entries, zero errors and the same
  two warnings. Do not hide or mislabel the warnings as resolved.
- [x] Preserve execution evidence: no capability record, registry, Telegram source, provider,
  service, database or SkillTree decision changed.
- [x] Preserve limitations: this is a local source-branch repair, not a live deployment, service
  restart, provider execution or enforcement promotion.

Acceptance evidence:

- The pre-repair validator receipt exited 1 with SHA-256
  `677304fd0093744e5f8d706ee0c8e425e3b0a206ca8d92c3b3015dbef4929ea0`.
- Two post-repair canonical validator receipts were byte-identical with SHA-256
  `c82118daada757c6258812ea09a34563e1590da68affffb9aa27c9d035701a40`; the repaired
  `memory/INDEX.md` SHA-256 is
  `c00db899142193e6ca55d68a786536fb6ad64dbc5f54f74593abac3633e0a568`.
- Focused memory, context and Telegram regression suite — 20 passed.
- Broad Skills/ECC/operator/Telegram/store/memory suite — 123 passed.
- Governance-kit validation passed. Two combined Skills/ECC validations remained byte-identical
  with SHA-256 `b05a414a5e8b4a068581097edbb0377275000f7dca7461e1f959c630510ece6f`;
  the 3,330-file ECC pin and all 137 SkillTree decisions remain unchanged.
- Two static execution audits remained byte-identical with SHA-256
  `77784095e06088df8591de9270af22ad90305f9ade038bf8a7b66c69cf7486c9`; registry SHA-256
  `155f3e79d531a35a1e69a2bd612dc0f0bdc7366c5eaebb89fb69ea2b90a0f53f` and capability
  SHA-256 `4c913cc8cad2bfed7c372f3024a512153f746a979678f00e7d89c629db30fa70`
  are unchanged.

Next smallest slice after promotion: write the bounded operator-authorised live-shadow protocol for
this one Telegram seam, including sample size, provider-cost ceiling, expiry, stop conditions,
receipt requirements and rollback. Do not deploy, invoke a provider or collect live telemetry until
that separate authority is explicit and bound to the exact staged hashes.

### 2026-08-24 — Slice 8: closed inert live-shadow policy

- [x] Reuse the existing execution capability record and policy loader; no second registry,
  gateway, authority file, database, collector or report surface was created.
- [x] Bind one exact canonical-JSON contract for a future live-shadow grant: 20 existing operator
  events, 20 provider attempts, at most two observations per minute, a one-hour collection window,
  one-day grant validity and retention, aggregate ceilings of $1 and 81,920 tokens, and an opaque
  hash-bound target selector.
- [x] Restrict future sampling to first eligible existing events with no synthetic provider calls,
  local TwinStore receipt metadata and hashes only, an exact telemetry-field allowlist and the four
  existing shadow/boundary/completion/comparison receipts.
- [x] Require future grant fields for exact registry/capability/source hashes, operator identity and
  authentication receipt, issue/expiry, target, limits, data-handling policy, escalation,
  revocation and justification.
- [x] Fix the stop set to expiry/hash drift, comparison failure, cost/token evidence or ceiling,
  data-scope/rate/receipt failure, revocation, provider failure, sample completion, target mismatch
  and raw/secret detection.
- [x] Keep telemetry collection, raw-message capture, secret capture, external export, new provider
  execution and enforcement promotion explicitly false. There is no grant-consumption path.
- [x] Reject numeric and type drift byte-for-byte. Adversarial fixtures prove one million samples,
  a one-year window, Boolean-as-cost and float-as-integer encodings all fail closed.
- [x] Preserve limitations: this is an inert prerequisite declaration. It does not authenticate an
  operator, admit a grant, enforce rate/retention at runtime, deploy a collector, invoke a provider
  or prove a live sample.

Acceptance evidence:

- Focused policy and bypass suite — 21 passed.
- Broad Skills/ECC/operator/Telegram/store/memory suite — 125 passed.
- Independent read-only red-team certification passed after two earlier defects were blocked and
  repaired: registry-controlled widening and Python numeric type coercion.
- Two static audits were byte-identical with output SHA-256
  `d9d55f231375093e633e80ad6ddaa45d853b52ac0a5f7a1498006bee434bd773`; registry SHA-256
  `309e8744c1ba41a0958cb79d4faa75d98d4adb1e13c31293a6c803263a2a6a99`, capability SHA-256
  `6d91414f35a0c427c9ea6110fcb3ba5a0fdc234179de79b96bdb9f4c759bc53c` and embedded audit
  receipt SHA-256 `c69eabf49bc411003f89b10a78185c0cce560fcec314b0209aa2a05fea19e3d8`.
- Governance-kit validation passed. Two combined Skills/ECC validations remained byte-identical
  with SHA-256 `b05a414a5e8b4a068581097edbb0377275000f7dca7461e1f959c630510ece6f`;
  the 3,330-file ECC pin and all 137 SkillTree decisions remain unchanged.

Next smallest slice after promotion: select or define the operator-authentication receipt mechanism
and add a deterministic grant loader that validates the exact required fields and ceilings but
still cannot start a provider or collector. Runtime sampling remains a later, separately authorised
checkpoint.
