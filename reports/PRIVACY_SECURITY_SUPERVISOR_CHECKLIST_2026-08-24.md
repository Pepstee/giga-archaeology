# Privacy and Security Supervisor — Durable Control Checklist

**State:** RUNNING; OX JSR-025A SESSION ACTIVE

**Supervisor:** Codex, policy/architecture/review/integration authority

**Implementation engine requested:** `openrouter/stealth/ox-alpha`, variant `max`

**Architecture-control task:** `(8) End result architecture (2)` (`01a02463-6b93-70e0-87cd-950c0ea52d24`)

**Prepared:** 2026-08-24 KST / 2026-08-23T18:10Z

## Why this artefact is new

No existing file in the canonical `giga-user` scope owns the lifecycle of a cross-cutting
Privacy and Security supervisor. The architecture and blueprint define the target, and the
ArtVault deployment receipts cover one device, but neither is a durable execution checklist
for Vault gating, compartments, capability grants, secrets, audit, recovery, bypass detection,
and privacy enforcement. This file has that distinct responsibility. It does not replace or
rewrite either architecture source.

## Persistent objective

Finish cross-cutting Vault gating, compartmentalisation, capability grants, secrets boundaries,
audit, recovery, bypass detection, and privacy enforcement to the highest standard while
preserving the operator's accepted-risk rule when Vault is explicitly connected.

The task goal service currently contains an earlier, unfinished ArtVault goal in `paused` state.
The service refused creation of this new goal because only one unfinished goal may exist. The
objective above is therefore the durable continuation authority until the operator resumes or
completes the earlier task goal. This is a continuity limitation, not permission to weaken any
gate.

## Bound architecture authority

| Source | SHA-256 | Role |
|---|---|---|
| `architecture/11_JARVIS_SOVEREIGN_RUNTIME_PROPOSED_ARCHITECTURE.md` | `fc65e8221416178eb3c7ef2801b4e631269853926a648683648dc7cc293dc245` | Requirements and sovereign-runtime laws |
| `architecture/12_JARVIS_SOVEREIGN_RUNTIME_IMPLEMENTATION_BLUEPRINT.md` | `eebb08490dcba120f793f4a5c513a71accefa0d4871c2b05f24d8d1d6a3ae6a8` | Dependency order, slices, and objective gates |
| `giga-user-v2/CONSTITUTION.md` | Git identity `396c34c92e5add3a63e41c66217613a9368e267a` | Current protected implementation authority |
| `giga-user-v2/contracts/constitution/development-stewardship.v2.json` | policy SHA-256 `9329b98efaba7d429ab4b93d8c4fb86ce95236241f62475fbad7aafe88e00799` | Work-order admission and isolated-lane rules |

The following architecture doctrine is binding:

1. **Faceless is the default.** A disconnected Vault means no private-personal context is
   available, while non-personal autonomy may continue.
2. **Connection is explicit accepted risk.** A locally authorised Vault connection may release
   broad private context. The system must describe this honestly as accepted privacy risk; it
   must not claim the connected mode is private from its authorised model consumer.
3. **Accepted risk is not a bypass.** Integrity, provenance, purpose, consumer, scope, expiry,
   access audit, and revocation remain mandatory while connected.
4. **Data authority and action authority are orthogonal.** A Vault grant can release context but
   cannot authorise an email, message, purchase, file write, credential use, or other external
   action.
5. **Mounting releases nothing.** A mounted Vault is only an availability state. A separate,
   short-lived, purpose-bound grant is required for every context release.
6. **Compartments remain distinct.** Email, calendar, messages, identity, memory, credentials,
   and future sources carry their own owner, sensitivity, retention, purpose, and query policy.
7. **No shadow path.** Official consumers use the broker. Direct reads, alternate adapters,
   debug hooks, stale compiled policy, and emergency routes must be denied or emit bypass
   telemetry and fail closed.
8. **No private plaintext in control evidence.** Receipts contain identities, versions, purpose,
   scope descriptors, hashes, decision reasons, and timestamps—not released content, secrets,
   tokens, or recovery material.

## Repository sync receipt

### `giga-user`

- Current branch: `codex/giga-modularization-20260731`
- Current HEAD at receipt: `b3cc2d854f38eb1754860ff02e04a10d10ec60a1`
- Upstream: `origin/codex/giga-modularization-20260731`
- Cached upstream relation: `0 behind / 1 ahead`
- Worktree: 112 untracked operator entries; they were not staged, moved, reset, stashed, or
  deleted.
- Git author already configured as `Artiom <gutu.artiom444@gmail.com>`.
- Fetch outcome: unavailable. The managed task cannot write `.git/FETCH_HEAD`, and outbound DNS
  to `github.com` is unavailable. No pull was attempted because fresh remote state could not be
  established and the cached state was not strictly behind.

### `giga-user-v2`

- Current branch: clean `main`
- Current HEAD: `396c34c92e5add3a63e41c66217613a9368e267a`
- `main` has no configured upstream.
- Cached `origin/main`: `50c714959a0fabf853be461cda8f2910d94ce778`
- Cached relation: `0 behind / 29 ahead`
- Fetch outcome: unavailable for the same `.git/FETCH_HEAD` and network restrictions.
- No pull was applicable. The shared checkout remained read-only; no isolated checkout was
  edited.

These are cached-local observations, not claims about current GitHub state.

## Ox lane/session receipt

Requested lane: `/Users/admin/Documents/ox-alpha-giga-workspace/lanes/privacy-security`

- The Ox workspace exists and binds `openrouter/stealth/ox-alpha` at `max` reasoning.
- It currently contains a broad portfolio session and a source-only `giga-user-v2` snapshot.
- The requested `lanes/` hierarchy does not exist.
- This managed task has read-only access to the Ox workspace. Creating the requested lane locally
  failed with `Operation not permitted`.
- The existing broad Ox session was deliberately not reused: doing so would conflict with its
  active portfolio scope and violate the requested non-conflicting lane boundary.
- On 2026-08-24 KST, creation, seeding, and session startup were delegated to the architecture-
  control task (`01a02463-6b93-70e0-87cd-950c0ea52d24`) with the exact first-slice contract below.
  That task owns only lane/session provisioning; this supervisor retains privacy policy, diff
  review, acceptance, and integration recommendation authority.
- Provisioned source repository:
  `/Users/admin/Documents/ox-alpha-giga-workspace/lanes/privacy-security/source/giga-user-v2`.
- Source capture: clean canonical `main` commit
  `396c34c92e5add3a63e41c66217613a9368e267a`, tree
  `f81261d96d328bc189d04c812f0a2b5d7befb2a9`, exported without canonical `.git` metadata.
- Independent lane baseline: commit `47237c24a0e1a7321bbda9531a312228d3aa6343`, tree
  `a26e30a81f5a344410740f354632f07e3d53c4d1`, author and committer
  `Artiom <gutu.artiom444@gmail.com>`.
- Independent comparison found all 187 canonical tracked entries present with identical Git
  modes and blob identities. The lane baseline has exactly four additions: this slice contract,
  the lane manifest, and the two hash-bound architecture authorities.
- Dedicated Ox session: `ses_fd02a6feaffeQZb4PWjr6uWNPG`. After a narrow confinement correction,
  this supervisor independently observed the resumed sole-writer process as PID `54300`, cwd-bound
  to the exact Privacy lane, using `openrouter/stealth/ox-alpha` with `variant=max`.
- First Ox status: authority sources read, bounded todo created, and the correct sequence selected:
  search, check, exact work order, scope ratification, admit, then mutate. No integration or
  completion claim has been made.

## Baseline receipt

Executed against clean `giga-user-v2` `main` at `396c34c`:

| Probe | Result | Interpretation |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -m giga_control check` | PASS | Constitution 2.1.0, stewardship 2.0.0, ten lanes, and fifteen protected paths are internally consistent. |
| Full `pytest` without cache/bytecode writes | 137 passed; 5 failed; 68 subtests passed | All five failures require a nested macOS sandbox. They are not classified as product regressions or passes in this execution environment. |
| Direct `/usr/bin/sandbox-exec` probe | `sandbox_apply: Operation not permitted` | The outer managed sandbox prevents the inner confinement layer from starting. Timeout, child-process, and sandbox-read assertions are therefore unverified here. |

The five unverified cases are:

1. caller `PATH` injection and external-effect confinement;
2. detached-descendant termination and structured spawn handling;
3. timeout and output-limit result classification;
4. selected-pass/inapplicable structured reporting;
5. out-of-scope read denial in the current-state sandbox.

A native macOS lane outside this outer sandbox must rerun the complete suite. Until then, the
quality boundary is **not fully satisfied** even though the core Constitution gate passes.

## Current capability/gap map

| Control family | Current evidence | State |
|---|---|---|
| Immutable architecture bindings | Hash-bound architecture sources and Constitution lock | PRESENT |
| Work-order admission | `giga-v2.work-order.v2` stewardship gate | PRESENT |
| Current-state privacy posture | Aggregate-only observation; Vault and external-write authority false | PRESENT, narrow |
| Deterministic policy compiler | JSR-025 | NOT BUILT |
| Capability registry | JSR-026 | NOT BUILT |
| Request/kernel contracts | JSR-027/028 | NOT BUILT |
| Bypass audit/telemetry | JSR-030/081 | NOT BUILT |
| Faceless context broker | JSR-033 | NOT BUILT |
| Compartment registry | JSR-034 | NOT BUILT |
| Vault format and local encryption | JSR-037 | NOT BUILT |
| Explicit mount session | JSR-038 | NOT BUILT |
| Purpose-bound ContextGrant | JSR-082 | NOT BUILT |
| Access ledger without plaintext | JSR-039 | NOT BUILT |
| Canonical memory/privacy writer | JSR-040/083 | NOT BUILT |
| Backup, restore, and drill evidence | JSR-041/093 | NOT BUILT |
| Credential lifecycle/secrets boundary | JSR-058 | NOT BUILT |

The existing Gigabyte ArtVault is useful deployment evidence but is not proof that the future
Personal Vault controls above exist in `giga-user-v2`.

## Dependency-ordered durable checklist

Status vocabulary: `DONE`, `READY`, `BLOCKED`, `NOT STARTED`.

### P0 — authority and supervision

- [x] **PS-000 — Bind architecture and accepted-risk doctrine.** `DONE` in this receipt.
- [x] **PS-001 — Inspect live repositories without disturbing operator work.** `DONE`; fresh
  remote fetch is blocked and reported rather than guessed.
- [x] **PS-002 — Establish current test truth.** `DONE`; five nested-sandbox gates remain
  explicitly unverified.
- [x] **PS-003 — Start isolated Ox privacy-security lane.** `DONE`; the lane receipt, source
  identities, exclusions, Ox session identifier, and first bounded status are recorded above.
- [ ] **PS-004 — Rerun native full verification.** `BLOCKED` in this outer sandbox; objective gate
  is zero failures and a full-quality PASS.

### P1 — unavoidable policy/kernel substrate

- [ ] **JSR-025 — Deterministic policy compiler.** `READY FOR ARCHITECTURE-CONTROL REVIEW` as the
  first candidate slice below.
- [ ] **JSR-026 — Capability registry.** `NOT STARTED`; must distinguish observe, context-read,
  credential-use, write, execute, external-side-effect, and recovery capabilities.
- [ ] **JSR-027/028 — Request and observe-only kernel.** `NOT STARTED`; every access path must
  present a typed request and receive a deterministic decision/receipt.
- [ ] **JSR-030/081 — Bypass inventory and telemetry.** `NOT STARTED`; enumerate official and
  alternate paths before Vault code exists.

### P2 — faceless context and compartments

- [ ] **JSR-033 — Faceless context broker.** `NOT STARTED`; disconnected mode must remain useful
  without inspecting personal sources.
- [ ] **JSR-034 — Compartment registry.** `NOT STARTED`; unknown sources and cross-compartment
  joins fail closed.
- [ ] **Least-context compiler / provider privacy registry.** `NOT STARTED`; route only necessary
  fields to a named consumer and record the privacy class.

### P3 — Vault and grants

- [ ] **JSR-037 — Versioned encrypted Vault format.** `NOT STARTED`; do not begin before P1/P2
  controls exist.
- [ ] **JSR-038 — Explicit local mount session.** `NOT STARTED`; timeout, lock, revoke, and crash
  semantics required.
- [ ] **JSR-082 — ContextGrant.** `NOT STARTED`; bind purpose, consumer, compartments, scopes,
  versions, expiry, and revocation. Mount alone releases no data.
- [ ] **JSR-039 — Privacy-preserving access ledger.** `NOT STARTED`; every release has an audit
  receipt with no private plaintext.
- [ ] **JSR-040/083 — Canonical memory/privacy writers.** `NOT STARTED`; derived memory and
  persistent personal profile writes require provenance and policy.

### P4 — secrets, recovery, and assurance

- [ ] **JSR-058 — Credential lifecycle.** `NOT STARTED`; credentials are separately encrypted,
  never model context, never Git content, and usable only through named capabilities.
- [ ] **JSR-041 — Backup/restore.** `NOT STARTED`; encrypted, versioned, integrity-bound, and
  isolated from live credentials.
- [ ] **JSR-093 — Restore drills.** `NOT STARTED`; a backup is not accepted until a clean-room
  restore passes and produces a receipt.
- [ ] **Bypass and revocation assurance.** `NOT STARTED`; direct reads, stale grants, clock skew,
  policy rollback, crash recovery, debug routes, and administrative override receive adversarial
  tests.
- [ ] **Cross-cutting privacy review.** `NOT STARTED`; no claim is complete until Codex independently
  reviews the Ox diff, reproduces its tests, scans for secrets/private fixtures, and submits the
  candidate to architecture control.

## First bounded Ox candidate — JSR-025A privacy decision contract

**State:** WORK ORDER VALIDATED AND EXACT PATHS RATIFIED; admission/implementation pending.

**Purpose:** create the smallest deterministic end-to-end policy path capable of expressing
faceless operation, explicit Vault connection, purpose-bound context release, and separate
action authority. It is a prerequisite, not a Vault implementation.

**Candidate owners:** Constitution & Enforcement primary; Vault & Context consulted;
Verification & Assurance independent review.

**Proposed write surface (architecture control must ratify exact paths):**

- one versioned policy-decision contract under `contracts/`;
- one pure compiler module under `src/`;
- focused unit/property tests under `tests/`;
- admitted work order, verification receipt, and slice-registry evidence required by the current
  Constitution.

**Inputs:** operation, capability, data compartment, consumer, purpose, Vault connection state,
grant identity/version/expiry/revocation state, action authority, policy version, and request
time supplied by the deterministic caller.

**Outputs:** `ALLOW` or `DENY`, stable reason code, required audit obligations, risk class,
policy identity, and a canonical decision digest. Never include private content or credentials.

**Objective tests:**

1. disconnected Vault + personal scope → deterministic deny;
2. disconnected Vault + permitted faceless observation → allow without personal context;
3. mounted Vault without ContextGrant → deny and zero release obligation;
4. expired, revoked, wrong-purpose, wrong-consumer, wrong-version, or cross-compartment grant →
   deterministic deny;
5. valid explicit grant in connected mode → allow with `accepted_privacy_risk=true` and mandatory
   access-ledger obligation;
6. valid context grant without separate action capability → context may be released, external
   action remains denied;
7. unknown operation, capability, compartment, policy version, or malformed input → fail closed;
8. identical canonical input → byte-identical decision and digest across replay;
9. policy/compiler version mismatch or rollback attempt → deny and bypass/audit obligation;
10. fixtures and receipts contain no Vault plaintext, tokens, private keys, recovery material, or
    personal corpus excerpts;
11. current Constitution admission/check/verify/attest lifecycle passes in an isolated worktree;
12. full native test inventory passes, including confinement tests that are blocked in this task.

**Explicit non-goals:** encryption format, a mount daemon, live provider credentials, personal
data ingestion, memory writes, external actions, emergency/break-glass authority, UI, and remote
deployment.

### JSR-025A pre-mutation review receipt

- Ox reran `python3 -m giga_control check` after architecture control granted read-only access to
  only the two hash-bound public architecture files. The gate passed without policy mutation.
- Ox stopped before repository mutation and returned a complete
  `giga-v2.work-order.v2` proposal for `WO-JSR-025A-PRIVACY-DECISION`.
- This supervisor extracted the proposal directly from the OpenCode session database and passed
  it through `giga_control.gate.validate_work_order` in memory against the isolated lane.
- Exact ratified implementation paths:
  `giga_control/extensions/privacy_decision.py` and
  `tests/constitution/test_privacy_decision.py`.
- Gate-owned lifecycle paths are limited to the matching work order and receipt directory. No
  protected file, canonical checkout, policy binding, JSR-026 capability registry, or JSR-027
  canonical request schema is authorised.
- Ratification requires a pure deterministic evaluator, strict version identifiers, stable
  fail-closed decisions for every untrusted malformed input, orthogonal context/action authority,
  honest `accepted_privacy_risk` only for valid explicit personal-context release, content-bound
  decision digests, actual-candidate fixture hygiene checks, and native confinement verification.
- Implementation remains unaccepted until admission, candidate diff, all twelve objective gates,
  secret/private-data scan, candidate commit/tree, verification, and attestation are independently
  reviewed.

## Ox lane bootstrap handoff

When `/Users/admin/Documents/ox-alpha-giga-workspace` is writable, the dedicated supervisor must:

1. create only `lanes/privacy-security` and a non-conflicting candidate checkout/snapshot;
2. bind the exact live source revisions and copy no `.git`, secrets, personal data, Vault files,
   credentials, or recovery material into Ox;
3. configure `openrouter/stealth/ox-alpha` with `variant=max` using the existing confined launcher;
4. feed only the first bounded candidate above;
5. require Ox to produce a diff, objective test transcript, limitations, and rollback statement;
6. let Codex inspect every changed line and rerun every applicable test independently;
7. send the reviewed candidate to `(8) End result architecture (2)` for admission/integration;
8. never edit that task's active isolated checkout concurrently.

## Completion rule

This programme is complete only when every required checklist item is `DONE`, the full native
verification quality boundary passes, recovery is demonstrated rather than documented, bypass
tests fail closed, privacy evidence contains no private plaintext or secrets, architecture control
has integrated the admitted candidates, and connected-Vault receipts honestly record accepted
privacy risk. Time spent, an Ox claim, a passing narrow test, or a configured mount is not
completion evidence.
