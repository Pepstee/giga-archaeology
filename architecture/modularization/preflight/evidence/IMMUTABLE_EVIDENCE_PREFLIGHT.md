# Immutable-evidence preflight

**Observed:** 2026-07-30  
**Outcome:** inventory complete; immutable-vault migration **not ready**  
**Mutation boundary:** no source export was moved, extracted, normalised, chmodded,
or rewritten.

## Inventory result

The source estate has three different classes which must not be conflated:

1. **Nine immutable file authorities:** the seven known provider exports plus
   two UK-laptop intake ZIPs.
2. **Five extracted-original roots:** useful working copies and mirrors, but
   subordinate to their archive authorities.
3. **Six other archive-like files:** a derived memory export, two deliveries,
   one migration tarball, and two Git bundles. They are valid archives but are
   not personal source-export authorities.

Fourteen archive-like files were found in the repository-wide extension scan.
The non-archive Telegram `result.json` makes fifteen individually inventoried
file objects across the discovery and evidence sets.

All eight source ZIPs pass full member CRC. Each has zero unsafe paths, encrypted
entries, duplicate names, and symlink entries. Every recorded SHA-256 was
recomputed from current bytes.

| Authority | Bytes | SHA-256 prefix | Structure | Mode | Global baseline |
|---|---:|---|---|---|---|
| ChatGPT separate account | 1,171,034,822 | `f766b446d9a7` | ZIP CRC pass, 1,988 files | `0644` | yes |
| ChatGPT pre-2026 account | 642,795,764 | `dfec969741f5` | ZIP CRC pass, 2,431 files | `0644` | yes |
| Claude account export | 9,096,664 | `754e30a5d4c1` | ZIP CRC pass, 11 files | `0644` | yes |
| Discord primary | 173,231,569 | `6fdf33df674d` | ZIP CRC pass, 1,100 files | `0644` | yes |
| Discord teen | 483,666,368 | `c9396462fb02` | ZIP CRC pass, 1,118 files | `0644` | **no** |
| Instagram primary | 628,369,284 | `e800bfcd4b9e` | ZIP CRC pass, 1,976 files | `0644` | yes |
| Telegram primary | 44,833,962 | `cb4d6dfd1ed4` | byte hash only; semantic JSON parse not run | `0644` | **no** |
| UK Claude intake | 921,429 | `2c398e8860ca` | ZIP CRC pass; 358/358 manifest hashes | `0600` | **no** |
| UK Codex intake | 391,104 | `61b030f6d342` | ZIP CRC pass; 64/64 manifest hashes | `0600` | **no** |

The older baseline at
`architecture/EXPORT_IMMUTABILITY_BASELINE.sha256` therefore protects only
five of the nine current file authorities. The 26 July unified-memory report
records the seven provider hashes, while the two UK archives have separate
intake manifests. There is no single complete authority ledger before this
preflight.

## Extracted-original findings

### Claude provider export

The unpacked eleven-file Claude tree is a byte-exact mirror of the ZIP member
set. Both have deterministic tree hash
`4b4868610ff9ac9ebbca667f29113eca6b50177b18c6a27aa7384d62541237ae`.
Its existing `0700` directory and `0600` files are appropriate, but the ZIP
must remain the primary authority.

### UK Claude intake

The source manifest describes 355 local-agent files plus three restricted
configuration files. All 358 manifest hashes still match the transfer ZIP and
the corresponding incoming files.

Both Claude working-copy trees also contain the same two unmanifested
`__pycache__/*.pyc` paths. The `.pyc` bytes differ between incoming and landed
trees. Consequently:

- the claim “355 byte-preserved files” remains true only for the
  manifest-covered subset;
- neither 357-file tree is itself an immutable source authority;
- the generated `.pyc` files must be excluded from a future restore map, not
  silently blessed as evidence;
- the valid UK Claude transfer ZIP remains the restore authority.

### UK Codex intake

The transfer ZIP still matches all 64 source-manifest hashes. The extracted
snapshot does not: `logs_2.sqlite-shm` has the expected size but a different
hash. SQLite shared-memory files are mutable runtime state and unsafe as
standalone immutable authorities.

Do not repair this tree in place. A restore drill must materialise the archived
member into a disposable destination and prove the manifest there. The current
working copy should remain quarantined and explicitly marked drifted.

## Consumer map

- ChatGPT archives feed `scripts/extract_chatgpt.py`, namespace-specific prompt
  and transcript views, and the unified-memory builder.
- Claude's provider archive/unpacked mirror feeds `scripts/extract_prompts.py`,
  the two-sided Claude transcript, and unified memory.
- Discord archives feed `scripts/extract_discord.py`, their adjacent raw
  manifests, and unified memory.
- Instagram feeds both extraction generations, reply-pair preparation, and
  unified memory.
- Telegram feeds `scripts/extract_telegram.py`, its raw manifest, unified
  memory, and the Telegram pipeline.
- UK Claude and Codex intake archives currently feed provenance documents and
  manifests only. They are not part of canonical prompt counts or unified
  memory.

The complete path-level consumer list is recorded per asset in
`RAW_SOURCE_EXPORT_LEDGER.json`.

## Blocking findings

1. **P0 — incomplete global baseline.** Discord teen, Telegram, and both UK
   archives are missing.
2. **P0 — no vault proof.** There is no verified encrypted,
   content-addressed, two-copy vault and no independent restore receipt.
3. **P0 — broad permissions.** Seven provider originals are `0644`; none of
   the nine authorities has a filesystem immutable flag.
4. **P0 — extracted Codex drift.** One SQLite SHM file differs from its source
   manifest, although the intake ZIP remains intact.
5. **P1 — generated-file contamination.** Two unmanifested `.pyc` files sit in
   each UK Claude working tree and differ across copies.
6. **P1 — no cutover map.** Consumers still refer to scattered current paths;
   no replayed relocation/restore map exists.

## Safe next sequence

1. Ratify the nine file authorities and the rule that archives outrank
   extracted mirrors.
2. Ingest copies into a content-addressed encrypted vault without touching the
   originals.
3. Recompute hashes and archive tests from the vault copy.
4. Produce a restore map and materialise a disposable restore.
5. Re-run all source and member-manifest checks against the restore.
6. Rebuild declared deterministic derived views and compare their hashes.
7. Only after the restore receipt passes, migrate consumer paths and harden
   permissions in a separately authorised change.

The exact acceptance rules are in
`IMMUTABLE_VAULT_MIGRATION_CONTRACT.md`.

## Audit-boundary incident

An early broad provenance search accidentally matched raw JSON and emitted
message payload text into the local terminal output. It was stopped and
replaced with path-only enumeration and manifest allowlists. No source file was
changed, but this means the process was not perfectly metadata-only from the
reader's perspective. No message semantics were used in this ledger or report.

