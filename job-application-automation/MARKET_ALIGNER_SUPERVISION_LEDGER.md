# Market Aligner and JAA supervision ledger

Updated: 2026-08-24  
Supervisor: Codex  
Implementation engine: Ox Alpha, `openrouter/stealth/ox-alpha`, reasoning variant `max`  
Purpose: durable execution state and anti-repetition authority for the Market Aligner product and its internal JAA subsystem.

This is a distinct execution ledger rather than an extension of
`JAA_MARKET_ALIGNER_BASELINE_COMPREHENSION_2026-08-18.md`: the earlier file is a point-in-time
architecture assessment, while this file owns resumable supervisor state, slice disposition,
verification evidence, and the next authorized action.

## Persistent objective

Finish Market Aligner with internal JAA to the highest production standard through verified,
recoverable increments: official vacancy ingestion, evidence-bound eligibility and fit, cited
employer research, ATS inventory and filling, explicit deterministic/model boundaries, a production
coordinator, one-use release authority, one certified final-click primitive, crash recovery, and
forensic provider receipts. A submission is successful only when the provider supplies evidence
that the system independently verifies. After one truthful canary, prove a bounded three-application
cohort before claiming operational readiness.

## Recovery and synchronization receipt

| Identity | Canonical copy | Independent Ox copy |
|---|---|---|
| Path | `/Users/admin/Projects/market-aligner` | `/Users/admin/Documents/ox-alpha-giga-workspace/projects/market-aligner` |
| Branch | `codex/reconciliation-20260801` | `ox-alpha-work` |
| Commit | `246e9cf55c376b6dd92bbfe394d0db73187c33d9` | `acf57e05feca284ed767754a3c0cb7320d26077d` |
| Tree | `7596ee2be4ed01c1511cc9718d5d3fb57576b4bd` | `7596ee2be4ed01c1511cc9718d5d3fb57576b4bd` |
| Status | clean | clean |
| Upstream | none | none |
| Remotes | none | none |
| Worktrees | one, its own root | one, its own root |

Disposition:

- No fetch or prune could be performed because neither repository has a remote.
- No pull was attempted because neither branch has an upstream. A fast-forward pull was therefore
  neither necessary nor safe to infer.
- The repositories intentionally have independent Git histories. Their source trees are exactly
  equal at the recorded tree hash. The only non-Git directory differences observed were ignored
  Python and pytest caches in the canonical copy.
- The Ox copy was not linked to the canonical `.git` and was not rewritten. Refresh was unnecessary.

## Verified baseline

Both copies were tested independently with the same cache-free command:

```text
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 TMPDIR=/private/tmp \
  python3 -m unittest discover -s tests -p 'test_*.py'
```

Canonical result: `Ran 51 tests in 3.540s`, `OK (skipped=2)`.  
Ox result: `Ran 51 tests in 3.527s`, `OK (skipped=2)`.

Graphify structural baseline: 119 supported source files, approximately 39,804 words, with 1,456
AST nodes and 4,614 AST edges. No repository-owned `graphify-out/graph.json` existed at recovery.
The structural extraction was kept outside the read-only source checkout; a semantic rebuild remains
required after the first accepted recovery increment.

## Current capability truth

Implemented in the recovered source tree:

- 34 registered collection adapters, uncapped parallel collection, durable resume state, and the
  Scrapling protocol boundary;
- opaque external profiles and evidence ledgers;
- persistence, normalisation, deduplication, viability and hard-eligibility gates;
- versioned semantic extraction and evidence-alignment contracts with content-bound receipts;
- deterministic opportunity and explicitly uncalibrated fit scoring;
- research admission, leased workers, cited dossier contracts, and profile-scoped reports;
- a local assessment service and a provisional versioned JAA handoff/event protocol.

Not operational in this lineage:

- collection, normalisation, research, reporting, or handoff as supported public commands;
- a concrete model/research provider;
- a concrete Market Aligner-to-JAA client/consumer;
- a generic current-vacancy JAA production authority;
- ATS inventory/fill, release, final-click, recovery, and provider-confirmed receipt flow inside this
  repository.

The repository's sealed-import gate explicitly forbids importing the protected Gutua JAA
implementation until its frozen archive, commit, manifest, and certification receipts exist. The
first slice must not bypass that gate or claim JAA integration prematurely.

## Ox execution identity

- Workspace: `/Users/admin/Documents/ox-alpha-giga-workspace`
- Declared persistent session: `ses_fd069841affepp0wt0Gu32ia3k`
- Observed active log session during recovery: `ses_fd03cf3b5ffeDcBpwqEH0pJTMu`
- Model: `openrouter/stealth/ox-alpha`
- Variant: `max`
- Ox remains the implementation engine; Codex owns scope, review, acceptance, and integration.
- At recovery time the active Ox session was executing a different admitted GIGA portfolio slice.
  Market Aligner work must not race it in the same workspace.

Dedicated isolated worktrees created for this goal:

- builder: `/Users/admin/Documents/ox-alpha-giga-workspace/worktrees/market-aligner-ingest-001`,
  branch `ox/market-aligner-ingest-001`;
- adversarial reviewer: `/Users/admin/Documents/ox-alpha-giga-workspace/worktrees/market-aligner-ingest-review`,
  branch `ox/market-aligner-ingest-review`;
- capability/gap analyst: `/Users/admin/Documents/ox-alpha-giga-workspace/worktrees/market-aligner-gap-map`,
  branch `ox/market-aligner-gap-map`.

Multiple Ox agents are permitted only through isolated worktrees and non-overlapping roles. The
reviewer and analyst do not modify or integrate the builder's candidate. The first dedicated
builder launch attempts exited before session creation with OpenCode's generic `Unexpected` error;
the bounded session-start operation was delegated back to the parent supervisor task for recovery.

## Anti-repetition protocol

Before selecting or resuming any slice, the supervisor must:

1. Match the proposed objective and exact input identities against every row below.
2. Search canonical code, tests, migration ledger, and declared upstream evidence before creating a
   parallel mechanism.
3. If a matching row is `accepted`, do not repeat it unless a named input hash changed; record the
   changed identity and start a successor row.
4. If a row is `rejected`, reuse its evidence and address the recorded falsifier; do not replay the
   rejected approach.
5. If a row is `blocked`, recheck only the named blocker. Preserve unrelated operator work and do
   not reset, force, stash, discard, or silently clean.
6. A worker commit is only a candidate. Codex independently reviews the diff, runs acceptance and
   adversarial tests against the exact commit, and integrates only accepted work authored as
   `Artiom Gutu <gutu.artiom444@gmail.com>`.
7. Provider submission success requires provider-confirmed evidence. A click, HTTP success code,
   model assertion, or local state transition is not sufficient.

## Slice register

| Slice | Objective | Reuse/absence evidence | Acceptance | Status | Next action |
|---|---|---|---|---|---|
| RECOVERY-001 | Safely reconcile canonical and Ox copies | Same tree hash; no remotes/upstreams; independent histories retained | Exact Git evidence plus identical cache-free baseline | accepted | Do not repeat unless either tree or remote configuration changes |
| INGEST-001 | Expose one official, bounded collection cycle through the canonical CLI using the existing `Collector`, config loader, and external data-home boundary | Collector, YAML loader, SQLite resume, and raw cache already exist; public CLI had no collection command | No duplicate collector; exact config/data-home; one-cycle result as canonical JSON; durable content-bound operation receipt; idempotent replay/no second fetch for same operation; fixture official-adapter positive; config/path/hash/replay substitution negatives; existing baseline remains green | repair-required | Canonical `e8f8c8f` preserves the R4 tree as an intermediate; independently accept and integrate one forward R5 repair for the live claim-publication race before starting FIT-001 |
| JAA-IMPORT-001 | Reconcile and import sealed JAA authority/contracts | Current migration report says protected upstream is not frozen or sealed | Frozen archive, commit, manifest, licence/provenance, independent certification, field-by-field compatibility matrix | blocked | Recheck only when sealed upstream evidence exists |

## First bounded Ox slice: INGEST-001

Work only in the independent Ox Market Aligner repository. Reuse `market_aligner.cli`,
`config_loader.load_config`, `collectors.engine.Collector`, `ProductPaths`, and the existing vacancy
database. Do not create another collector, service, state database, or config system.

Required behavior:

- add one public command that runs one bounded official collection cycle;
- accept an exact configuration file and the established external data-home boundary;
- make the operation identity explicit and stable so a retry cannot cause an untracked second live
  fetch;
- emit canonical JSON and a durable content-bound receipt recording configuration identity,
  operation identity, source scope, collector result, and terminal disposition;
- preserve the last good database/raw cache on provider failure and make crash/replay state explicit;
- keep all irreversible application/release/submission capabilities out of scope.

Acceptance must include the existing baseline plus positive, replay, partial-provider-failure,
config substitution, operation substitution, receipt tamper, and interrupted-run tests. The slice is
not accepted merely because mocked CLI parsing works; at least one fixture adapter must traverse the
real Collector persistence path.

## Active INGEST-001 execution evidence

- Dedicated session: `ses_fd01f0ce2ffe1qs5qKy9nTE4iv`.
- Launch process at admission: PID `55977`, model `openrouter/stealth/ox-alpha`, variant `max`.
- Exact cwd: `/Users/admin/Documents/ox-alpha-giga-workspace/worktrees/market-aligner-ingest-001`.
- Branch/base: `ox/market-aligner-ingest-001` at
  `acf57e05feca284ed767754a3c0cb7320d26077d`; initial porcelain was clean.
- Durable session log:
  `/Users/admin/Documents/ox-alpha-giga-workspace/logs/market-aligner-ingest-001.jsonl`.
- The central portfolio Ox process has a different cwd and an explicit non-collision rule; it does
  not own or write this Market Aligner worktree.
- Two failed launcher attempts preceded the admitted session: first a confined temp-directory
  `EPERM`, then missing read-only access to the root OpenCode configuration. Both failed before
  session creation and repository mutation. The retry changed only the launcher confinement.

## INGEST-001 R1 rejection

- Rejected candidate: `53c4726e87b4fb9cf006f52d4f5216b5f64cb612`, tree
  `f8b5d02b549ebefc7cfdfffe95ed299cbee64a96`, authored as Artiom Gutu. Its own suite and the
  independent exact-tree rerun both reported 60 passed and 2 skipped.
- Falsifier 1: operation identity was derived solely from configuration and source scope. The first
  run exited 0, every later intentional run of the unchanged configuration exited 2, and the CLI
  exposed no operation-id input. The surface could not perform periodic ingestion.
- Falsifier 2: while one owner was blocked inside its real cycle, a contender rewrote the owner's
  `in_flight` record to `indeterminate`; the original owner later overwrote that record to
  `completed`. The contender's interruption claim was false and the journal had no owner/CAS rule.
- Falsifier 3: `io.database`, `io.job_urls`, and `io.raw_cache` values containing `..` escaped the
  explicit data-home. The command exited 0 and created all three outputs outside the boundary.
- Falsifier 4: a record with an unknown authority field and forged fetched count was accepted after
  recomputing its public record hash. The schema, types, receipt identity, and stored result were not
  exact authority.
- Static durability gap: journal creation and replacement fsynced the file but not its parent; a
  crash could lose the durable claim around provider access. Finalization had no expected-prior or
  owner compare-and-swap.
- Disposition: reject without integration. Preserve R1 as evidence. A bounded R2 was delegated to
  the same logical session; it must add explicit repeatable operation identity, exact successful
  terminal replay, live-owner isolation, same-scope unresolved blocking, strict under-data-home
  paths, exact typed receipts, and crash-durable publication.

## Current blocker and next supervisor action

- R2 is preserved uncommitted in the same builder worktree and logical session. Its five-file diff
  currently touches `README.md`, `cli.py`, `collectors/engine.py`, `state/operations.py`, and
  `test_ingest_cli.py`; HEAD remains rejected R1 `53c4726e`. The repository suite over the preserved
  diff reports 69 passed and 2 skipped, and `compileall` plus `git diff --check` pass. These green
  gates do not authorize integration.
- Independent review reproduced a same-operation race: two callers can both load an absent record
  before the scope lock; the winner performs exactly one provider cycle and seals `completed`, but
  the loser waits until after that seal and then falsely returns `in_progress/in_flight` instead of
  reloading and replaying the terminal receipt. The terminal record bytes remain intact.
- The R2 overlap test is not yet an authority because its set-based active-operation guard can drop
  a tag when one of several same-operation parallel fetches exits while another is still active;
  its thread-local operation tag also does not propagate into the Collector's provider thread pools.
  It must use exact operation-tagged adapters or an equivalent whole-cycle proof plus per-operation
  reference counts before it can prove cross-operation exclusion.
- Locking and blocker scans currently compare the complete source-scope list for equality. An
  executable barrier probe proved that scopes `[fixtureboard]` and
  `[fixtureboard, otherboard]` on the same data home enter their collection cycles concurrently.
  An unresolved superset likewise does not block a subset retry. R2 must hold sorted per-board locks
  for the whole operation and treat any scope intersection as an unresolved blocker.
- Claim publication is not atomic: `claim` writes directly into the final O_EXCL JSON path. Process
  death during that write can leave a partial final record and permanently block an operation even
  though no provider ran. The claim must be fully written and fsynced privately, published
  no-replace as one directory-entry transition, and parent-fsynced before provider access; a
  pre-publish/partial-write failure must leave no final record and permit the same ID to retry.
- Two further ordering/binding defects are recorded for the same repair: configured path containment
  currently runs only after `ProductPaths.ensure()` and journal construction, so an escaping config
  creates/chmods state before refusal; and the semantic config and raw-file hash come from separate
  uncoordinated reads, allowing a changed file to bind incoherent identities. Both must fail before
  journal/provider access with exact zero-call tests.
- `boards.enabled` is not type-checked before constructing the operation scope; a scalar string is
  silently converted into a sorted list of characters. Require an exact nonempty list of unique,
  bounded, nonempty board names in the shared Collector/config seam before journal/provider access.
- Provider-error sealing is not total: a provider exception whose rendered text exceeds the
  record's 4,096-byte limit causes terminal verification itself to raise, emits no structured
  refusal, and leaves the operation `in_flight`. Normalize a bounded error projection and bind the
  complete original error SHA-256 so long or hostile provider text still produces an exact failed
  receipt and zero-call replay.
- The receipt is a canonical unkeyed content identity inside a same-user private directory, not a
  signature or root-owned authentication boundary. A same-UID actor can alter a structurally valid
  counter and recompute both hashes. R2 documentation must state this limitation explicitly rather
  than calling the local hash cryptographic authority; a stronger admission boundary is deferred.
- The shared free Ox provider reached its enforced daily quota after the session stopped at a safe
  dirty boundary; reset is 09:00 Korea time. No paid/weaker model substitution and no competing
  Market writer are authorized. Resume the same logical session
  `ses_fd01f0ce2ffe1qs5qKy9nTE4iv` after reset, close only the recorded falsifiers, run the full
  gates, and create one separate Artiom-authored R2 commit. Then independently rerun the original
  four R1 falsifiers plus the new same-ID, reference-count, intersecting-scope, atomic-claim,
  preflight-order, config-coherence, scope-type, long-error, crash/CAS/path/replay matrix before
  deciding acceptance. Do not integrate or select another slice first. The preserved diff's full
  69-test suite also passes with `DeprecationWarning` elevated to an error; this remains regression
  evidence only, not acceptance evidence for the reproduced defects above.

## INGEST-001 R2 terminal review and R3 repair

- R2 candidate `6214363a696e9fecc0fc17da9d8492a459269426`, tree
  `55549f568781a174c7e5673ce8cb17a3f8aa40f6`, parent rejected R1 `53c4726e`, is rejected pending a
  narrow follow-up. It is authored and committed as `Artiom Gutu <gutu.artiom444@gmail.com>` and
  the worktree is clean. An earlier same-tree/same-parent commit `e32c7b28a...` used the shortened
  name `Artiom`; Ox replaced the branch ref with `6214363a` via `commit-tree`/`update-ref` before the
  supervisor could stop it. The unreachable commit remains visible to `git fsck` and the reflog.
  This disclosed ref-replacement is candidate-preparation provenance, not an accepted integration.
- Independent lane-first full baseline with `DeprecationWarning` elevated to an error reports
  78 passed and 2 expected skips; `compileall` and `git diff --check` pass. The original R1
  operation-identity, owner/CAS, under-data-home, strict receipt, long-error, and provider overlap
  defects are materially repaired. These gates do not override the new executable falsifier.
- Exact R2 falsifier: a valid configuration with `boards.enabled` ordered as
  `['secondboard', 'fixtureboard']` reaches claim construction with the unsorted source scope.
  `verify_record` raises an uncaught `OperationRefused('tampered_receipt')`, the fresh data home has
  already been created, and providers remain uncalled. R2 validates that receipts are sorted but
  never performs the contract-required canonical sort. The command must canonicalize the operation
  scope once before bindings, locks, claim and receipt while leaving Collector board semantics
  intact; a deterministic reversed-order positive must prove both boards are contacted exactly once
  and the stored/output scope is sorted.
- R2 documentation also gives an unusable ingest command without required `--operation-id` and
  describes one whole-scope lock despite the implementation's per-board intersection locks.
  `cli.py` contains duplicate definitions of `_emit_refusal`, `_emit_ingest`, and
  `_binding_refusals`; remove the dead duplicates without changing behavior.
- The same Ox logical session is authorized for exactly one separate R3 repair commit. It must not
  amend, reset, replace refs, integrate or push. After its own gates, Codex will rerun the entire
  consolidated R1/R2/R3 adversarial matrix before accepting INGEST-001 or selecting the next
  abandonment-safe production-coordinator/JAA submission slice.

## INGEST-001 R3 rejection and R4 repair

- R3 candidate `b994e2e29bacdf44ae22270e176a5f487105f7f1`, tree
  `17a5043293c7233c1b31f817d78ee086278e498a`, parent rejected R2 `6214363a`, is rejected pending one
  narrow follow-up. Author and committer are exactly `Artiom Gutu <gutu.artiom444@gmail.com>` and
  the worktree was clean after commit. The worker reported 82 passed with 2 expected skips,
  repeated focused concurrency passes, `compileall`, and `git diff --check`; these remain candidate
  evidence, not acceptance.
- R3 materially closes canonical board ordering, structured board/operation-lock substitution
  refusal before provider access, same-ID post-wait reload with a caller-owned operation lock,
  explicit provider-thread operation tags, usable documentation, and the duplicated CLI helpers.
- Exact terminal falsifier: the simultaneous same-operation-ID/disjoint-scope test was weakened to
  accept either `binding_config_source` or `binding_source_scope`, while `_binding_refusals` still
  checks the config locator before the consequential source-scope boundary. The required result is
  exact: after operation-lock serialization the loser must report `binding_source_scope`, never a
  generic or alternate binding reason, and must perform zero second provider cycles.
- Preserve R3 unchanged. Resume the same logical Ox session for one separate R4 commit atop R3:
  check `source_scope` before config path/file/semantic bindings, restore an exact
  `binding_source_scope` assertion, rerun the full suite plus repeated provider-authority races,
  `compileall`, and `git diff --check`, then stop. No amend, ref rewrite, reset, integration, push or
  competing Market writer is authorized.

## INGEST-001 R4 provisional integration and retracted acceptance

- Provisionally accepted Ox candidate: `9e92a0f918c4cb7a5c05ecb24307b0e36a8db71d`, tree
  `45f4224dff77de269b4287a7d31a5d539c48b6e1`, parent rejected R3 `b994e2e`. Author and committer
  are exactly `Artiom Gutu <gutu.artiom444@gmail.com>`; the lane worktree was clean.
- Independent acceptance on the exact candidate: 82 repository tests passed with
  `DeprecationWarning` elevated to an error; the seven-test concurrency/lock set passed 12
  consecutive runs; 13 targeted crash/config/journal/replay tests passed; `compileall`,
  `git diff --check`, and clean status passed.
- Independent executable probes proved: malformed scope leaves a fresh data home absent; unsafe
  pre-existing operation locks refuse before claim with null disposition and zero provider calls;
  reversed board order canonicalizes; forced same-ID/disjoint scopes both observe absence but run
  exactly one provider cycle and return exact `binding_source_scope`; forced identical same-ID
  twins both observe absence and return one success plus one byte-identical replay. Negative-control
  removal of board locks made both provider-overlap tests fail, proving their zero-overlap positives
  are non-vacuous.
- Canonical repository `/Users/admin/Projects/market-aligner` was clean at
  `246e9cf55c376b6dd92bbfe394d0db73187c33d9` with tree
  `7596ee2be4ed01c1511cc9718d5d3fb57576b4bd`, exactly matching the independent Ox base tree. The
  accepted final tree was integrated without importing rejected intermediate history as canonical
  commit `e8f8c8fe8bc0ff2c41f1c9208ee09ffcfe8459c1`, authored and committed as Artiom Gutu. Its tree is
  exactly the accepted `45f4224d...`; the post-integration suite again reports 82 passed, 2 skipped,
  and the canonical worktree is clean.
- No remote exists, so no push or pull occurred. No live provider, model, browser, application,
  release, final-click, or submission action occurred.

The terminal acceptance above was retracted after stronger independent assurance reproduced a
low-frequency race on the exact same tree. Preserve all of the passing evidence as regression
coverage, but do not treat it as sufficient acceptance evidence:

- Claim publication links a private temp inode to the final operation path and then unlinks the
  temp name. A concurrent pre-operation-lock `load()` can enter `_repair_own_claim_temp` during
  that two-link publication window and unlink the live publisher's temp name.
- The publisher then receives `ENOENT` while unlinking its temp and reports
  `claim_publication_failed`, although the final authoritative record already exists as
  `in_flight`. A second reproduced interleaving lets the contender observe a transient
  `unsafe_journal_file` instead of the required exact same-ID/scope disposition.
- Independent warning-strict full-suite assurance failed 1 of 82 tests and stress reproduced the
  race around iterations 76--78. The earlier twelve consecutive focused passes do not falsify a
  lower-frequency interleaving.
- Canonical commit `e8f8c8f...` is therefore a repair-required historical intermediate. Do not
  reset, rewrite, revert, or conceal it; integrate a separate forward repair after terminal review.
- The same sole-writer Ox session is authorized for R5 only. Readers must not mutate a live claim
  publication. Recovery may remove a temp only with proof, under the appropriate lock, that the
  publication is abandoned. Deterministic link-window and high-count stress tests must prove one
  winner completion, one exact loser disposition, one provider cycle, and no leaked temp.
- Preserve all R4 source-scope precedence and unsafe pre-claim lock semantics, including retained
  operation ID and null disposition. Run the complete warning-strict suite and repeated stress,
  create one separate Artiom Gutu commit, then stop for fresh independent assurance.
- FIT-001 and every later JAA/coordinator slice are stopped until the R5 repair is accepted and a
  forward canonical repair commit is integrated.
