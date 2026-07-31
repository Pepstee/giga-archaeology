# Memory Truth Contract v2

Status: **preflight only**. This contract does not migrate or mutate the live memory.

## 1. Authority boundary

Memory v2 is an append-only evidence system, not a bag of prose. A stored statement is not
automatically current truth. The canonical validator input is
`giga.memory.snapshot.v2`, defined by `MEMORY_SCHEMA_V2.json`.

The system exposes three distinct views:

1. **History** — every accepted revision, claim, contradiction and tombstone, including claims
   later found false.
2. **Review** — unresolved, legacy-unreviewed, disputed and model-inferred claims.
3. **Active truth** — only current, eligible claims that survive lifecycle, temporal,
   contradiction, tombstone and derivation checks.

Context, proposals, commits and scheduled jobs may consume the active-truth view. They may
consult history only when explicitly labelled as history. They must never silently mix the two.

## 2. Deterministic identities

All hashes use SHA-256 over UTF-8 canonical JSON (`sort_keys=true`, compact separators, no
ASCII escaping).

- `entry_id = "mem:" + sha256(canonical({"legacy_path", "legacy_sha256"}))`
- `revision_id = "rev:" + sha256(canonical({"entry_id", "parent_revision_id",
  "content_sha256", "created_at"}))`
- `claim_id = "clm:" + sha256(canonical({"revision_id", "ordinal",
  "statement_sha256"}))`
- `tombstone_id = "tmb:" + sha256(canonical({"target_type", "target_id",
  "target_sha256", "reason_code", "effective_at", "authorized_by"}))`

The ordinal is the claim's zero-based position in the immutable revision. Reordering claims
therefore creates a new revision; IDs are never recycled.

`snapshot_sha256` is the hash of exactly `schema_version`, `evaluated_at`,
`source_manifest`, `entries`, and `tombstones`. `active_truth_sha256` is the hash of the sorted list of active
`claim_id`, `revision_id`, and `statement_sha256` triples. Derived artifacts and migration
workflow state are deliberately excluded from `snapshot_sha256` to avoid a self-referential
hash.

## 3. Source precedence

Precedence resolves authority, not meaning. It is applied only after temporal scopes overlap
and the claims genuinely contradict.

| Rank | Authority |
|---:|---|
| 1 | Authenticated operator correction or retraction naming the affected claim |
| 2 | Authenticated operator confirmation of a current statement or decision |
| 3 | Evidence-verified primary-source observation with a content hash and locator |
| 4 | Source observation whose provenance is intact but has not been independently verified |
| 5 | Model inference with explicit parent claims |
| 6 | Legacy-unreviewed material |

Ties are resolved by: explicit correction edge; narrower valid-time interval; later
`observed_at`; then lexical `claim_id`. A later timestamp alone never proves a claim true.
Third-party claims never outrank an operator claim about the operator's own preference or
decision, but the operator cannot override independently verifiable external facts merely by
asserting them.

Unknown values remain the explicit object
`{"state":"unknown","reason":"not-recorded|not-applicable|ambiguous|requires-review"}`.
Migration must not replace an unknown with a guessed default.

## 4. Claim lifecycle and contradictions

A claim is eligible for active truth only when all conditions hold:

- it belongs to the head revision of its entry;
- the head revision and claim both have lifecycle `active`;
- epistemic status is `operator-confirmed` or `evidence-verified`;
- its valid-time interval includes the evaluation time, or the interval is explicitly
  unknown and the claim is not time-sensitive;
- no tombstone targets its entry, revision, claim, or any ancestor claim;
- every `derived_from_claim_ids` parent remains active-truth eligible;
- no unresolved overlapping contradiction remains.

Contradictions are symmetrical: if A lists B, B must list A. Non-overlapping temporal claims
may coexist. For overlapping claims:

- a higher-precedence, explicit correction keeps the losing claim in history and creates a
  supersession tombstone or superseding revision;
- equal-precedence or otherwise unresolved claims are both excluded from active truth and
  routed to review;
- models may propose a contradiction edge but cannot resolve it;
- no claim is deleted or rewritten to hide the conflict.

Archived, superseded, retracted, disputed, tombstoned, legacy-unreviewed, source-observed and
model-inferred claims are excluded from active truth. They remain queryable as labelled
history or review evidence.

## 5. Migration rules

The legacy Markdown files remain immutable migration evidence.

1. Hash every legacy control and entry before projection.
2. Create one entry and one root revision per Markdown file; preserve the complete original
   content and original frontmatter byte-for-byte in that revision.
3. Preserve the legacy lifecycle value. Do not convert `archived` or `superseded-by` into
   active state.
4. Until semantic review, create one `legacy-entry-assertion` claim per entry, mark it
   `legacy-unreviewed`, set confidence and temporal gaps to explicit unknowns, and exclude it
   from active truth.
5. Convert a legacy supersession pointer into a relation/tombstone only when its target exists
   and the source hash remains bound. Never discard the superseded file.
6. Semantic claim splitting creates a child revision. The root legacy assertion remains in
   history, and every normalized claim cites it through `derived_from_claim_ids`.
7. No migration inference may invent a subject, confidence, date, authority or evidence
   locator. Missing means unknown.
8. Cutover requires a complete manifest, zero validator errors, an operator-reviewed active
   set, a restore drill, downstream rebuild receipts, and a rollback image.

## 6. Derived-artifact invalidation

Every context packet, proposal, commit receipt, daily report, graph, profile and training
dataset records:

- `memory_snapshot_sha256`;
- `active_truth_sha256`;
- exact claim and revision dependencies;
- validator and schema versions.

A new revision, contradiction resolution or tombstone computes the transitive closure of
affected claims. Any artifact depending on that closure must transition from `current` to
`stale` or `superseded`, record the invalidating tombstone/revision, and be rebuilt before use.
Invalidation is append-only; stale artifacts are never relabelled current in place.

## 7. Mandatory enforcement and rollback

The rules in `MANDATORY_VALIDATION_GATE.json` run before context compilation, before proposal
generation, immediately before commit, after staged commit, and before/after scheduled daily
work. A red gate means no model call, no memory write, no success receipt, and no daily cursor
advance.

Commit is a transaction over a staged snapshot:

1. validate the current snapshot and bind both hashes;
2. apply the proposal to an isolated copy;
3. validate the projected snapshot and active-truth view;
4. compare-and-swap against the bound source hash;
5. atomically promote or restore the untouched source;
6. emit a signed/hash-bound receipt only after post-commit validation.

Partial per-file success is not success. On any failure, restore the exact pre-commit snapshot,
mark the attempt retryable, retain diagnostic receipts, and leave scheduled cursors unchanged.

## 8. Compatibility

During migration, a read-only legacy adapter may project Markdown into a v2 snapshot. Dual
write is forbidden. Before cutover, legacy remains authoritative and v2 is shadow-only. At
cutover, v2 becomes authoritative only after acceptance gates and hash comparison pass; the
legacy tree becomes a read-only rollback source. A consumer that cannot verify v2 hashes must
fail closed rather than fall back silently to unvalidated legacy context.
