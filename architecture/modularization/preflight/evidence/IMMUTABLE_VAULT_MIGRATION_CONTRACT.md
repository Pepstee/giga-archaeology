# Immutable-vault migration and restore-drill contract

## 1. Purpose

This contract defines the conditions under which GIGA User's source exports
may be copied into an immutable vault, restored independently, and eventually
referenced from a cleaner workspace layout. It authorises no current move,
deletion, extraction, permission change, or cutover.

The vault protects evidence. It does not become a normal working directory,
training dataset, database, or synchronisation target.

## 2. Authority set

The initial vault set is exactly the nine `authority_role =
immutable_original` assets in `RAW_SOURCE_EXPORT_LEDGER.json`:

- seven provider exports: two ChatGPT, one Claude, two Discord, Instagram, and
  Telegram;
- two UK-laptop intake archives: Claude local-agent and Codex state.

Extracted trees are not independent authorities:

- the unpacked Claude account export is a verified mirror;
- UK Claude trees are working copies with unmanifested generated files;
- the extracted UK Codex snapshot is drifted.

When archive bytes and an extracted tree disagree, the archive hash plus its
source manifest wins. Derived JSONL, SQLite, training data, adapters, reports,
and delivery archives never supersede source evidence.

## 3. Vault object model

The implementation must expose this logical structure, regardless of storage
backend:

```text
vault/
  objects/sha256/<first-two>/<full-sha256>
  manifests/evidence-ledger/<ledger-sha256>.json
  restore-maps/<map-sha256>.json
  receipts/ingest/<receipt-id>.json
  receipts/restore/<receipt-id>.json
```

Every object record must contain:

- source asset ID and original relative path;
- byte length and SHA-256;
- provider and account namespace;
- acquisition/export date when known;
- archive format and structural-integrity observation;
- source-manifest references;
- sensitivity class;
- ingest timestamp, tool version, and destination object path;
- prior object ID if an export is superseded by a later provider export.

Objects are append-only. A later export creates a new object; it never replaces
or mutates an earlier object.

## 4. Storage requirements

1. Encryption at rest is mandatory. Encryption keys must not be stored only
   beside the vault.
2. There must be at least two independently failure-prone copies: one primary
   local copy and one offline or remote copy.
3. At least one copy must not be continuously writable by the normal GIGA
   runtime account.
4. Object paths must be content-addressed by full SHA-256.
5. Ingest uses a new temporary object, byte verification, durable flush, and
   atomic promotion. Partial objects are never visible as complete.
6. Vault files are owner-readable only and non-executable. The implementation
   must use the strongest practical read-only/immutable control available on
   the filesystem after ingest.
7. No archive is extracted inside the vault.
8. Cloud synchronisation is prohibited unless its encryption, retention,
   deletion, and account-recovery behaviour are explicitly accepted.
9. The ledger, restore maps, and receipts are versioned alongside but never
   embedded into source archives.

## 5. Ingest acceptance gates

An asset is `INGESTED` only if all gates pass:

1. The source path resolves beneath the declared repository root and is not a
   symlink.
2. Current size and SHA-256 equal the ratified ledger.
3. ZIPs pass central-directory inspection, full member CRC, root-escape checks,
   encryption checks, duplicate-name checks, and symlink checks.
4. The UK Claude ZIP matches all 358 source-manifest records.
5. The UK Codex ZIP matches all 64 source-manifest records; its extra embedded
   `CODEX_SOURCE_SHA256.csv` is recorded.
6. The destination object is written under its hash-derived path.
7. Destination size and SHA-256 are recomputed from destination bytes.
8. A second process independently rechecks the destination object.
9. The receipt binds source path, source hash, destination object, destination
   hash, ledger hash, and verifier result.
10. Failure leaves the current source and any prior vault object untouched.

No extracted working tree is ingested as an original source object in Wave 0.

## 6. Restore map

A restore map is a separate immutable document. Each entry contains:

- asset ID and vault object SHA-256;
- intended restored relative path;
- required owner/group/mode;
- whether the result is an authority file or a disposable extracted mirror;
- consumer references that must be rebound at cutover;
- permitted extraction rules, if any;
- prohibited generated paths, including the two unmanifested UK Claude
  `.pyc` files;
- source-manifest validation required after restore.

The first restore map must preserve current names to prove recovery. A later
clean-layout map may place authorities beneath a proposed
`corpus/source-vault/` namespace, but only after every consumer has been
identified and tested.

## 7. Restore-drill acceptance gates

A drill is `RESTORED` only when run into a newly created disposable directory,
never over the live workspace, and all gates pass:

1. The restore target is empty, outside the vault, and outside every current
   source directory.
2. All nine objects are restored using only the vault, ledger, restore map, and
   documented key-recovery procedure.
3. Restored file count is exactly nine before any optional mirror extraction.
4. Every restored byte length and SHA-256 matches the ratified ledger.
5. All eight restored ZIPs pass full structural validation again.
6. The Telegram JSON hash matches; semantic parsing is deferred to its existing
   extractor.
7. UK Claude and Codex member-manifest checks pass exactly.
8. Optional Claude account extraction, if tested, yields the eleven-file tree
   hash recorded in the ledger.
9. Optional UK extractions contain only manifest-authorised source members.
   Generated `.pyc`, SQLite sidecars, or other runtime mutations created during
   the drill make the mirror test fail.
10. Restored permissions are owner-only; no restored evidence is executable.
11. A secret-safe directory listing and verifier output are captured without
    message content.
12. The live repository's nine authority hashes are rechecked before and after
    the drill and must be unchanged.
13. The second vault copy is sampled independently, including at least one
    large archive, one UK intake archive, and Telegram.
14. A restore receipt binds the vault ledger hash, restore-map hash, all object
    hashes, verifier version, target identity, start/end time, and gate results.

## 8. Derived rebuild proof

Restore of raw bytes is necessary but not sufficient for operational recovery.
Before cutover, the drill must run existing extractors only against the
disposable restored paths and prove:

- both Discord raw-manifest source hashes;
- Telegram raw-manifest source hash;
- Instagram full raw-manifest source hash;
- both ChatGPT namespace outputs;
- the Claude transcript source;
- the declared unified-memory database and portable chronological export,
  subject to any documented non-byte-determinism.

Where a derived byte hash is not reproducible, the drill must compare a
canonical record count plus a deterministic content/table hash and record why
the file-container hash differs. No derived mismatch may be hidden by updating
the expected hash in place.

Training datasets and adapters are outside the raw-evidence restore gate. Their
own manifests must point back to restored source/derived hashes.

## 9. Cutover acceptance

Workspace relocation is a separate authorised change. It requires:

1. A passed ingest receipt and restore receipt.
2. A complete consumer map for every old path.
3. Tests proving all consumers accept the new path or a declared compatibility
   mapping.
4. A pre/post authority hash receipt.
5. A rollback map restoring every old path without downloading from a
   provider.
6. No deletion of original current paths until the operator explicitly accepts
   the restore drill and retention policy.
7. Recoverable quarantine, not destructive deletion, for obsolete mirrors.

The cutover fails closed if any unregistered source-like archive is discovered.

## 10. Required evidence states

| State | Meaning |
|---|---|
| `DISCOVERED` | Path, type, size, and provisional role recorded |
| `RATIFIED` | Operator accepts the asset as an evidence authority |
| `INGESTED` | Content-addressed primary vault object and receipt pass |
| `REPLICATED` | Independent second copy verified |
| `RESTORED` | Disposable restore drill passes |
| `CUTOVER_READY` | Consumers, rollback, and permissions pass |
| `SUPERSEDED` | A later provider export exists; old object remains retained |

Current state is `DISCOVERED`, not `INGESTED`.

## 11. Current blockers

The acceptance validator must remain red while:

- the global baseline omits four file authorities;
- a two-copy encrypted vault and key-recovery process are unverified;
- source permissions remain broader than the future contract;
- the Codex extracted snapshot is mistaken for an authority;
- UK Claude generated `.pyc` files are not excluded by restore policy;
- no consumer cutover and rollback map has passed.

