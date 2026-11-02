# Explicit project location inventory — Issue #2

The `locations-inspect`, `locations-refresh`, and `locations-query` commands record
project locations and their declared authority alongside bounded filesystem/Git
observations. This is a separate inventory from the source-content mapper: it reuses
Archaeology's sealed JSON evidence, portable Git environment, public API and CLI.
It does not populate the 22 source-map views or change their contracts.

## Inputs and scope

Supply an explicit list of roots, or one exact authority register file. There is no
discovery scan. Use absolute paths and the registered identity of the local host.
The operator is responsible for that host binding; the inventory never connects to
another host. A foreign-host declaration remains visible as an uninspected gap.

```sh
giga-archaeology locations-inspect \
  --root /absolute/project \
  --local-host example-host

giga-archaeology locations-refresh \
  --roots-file /absolute/registered-roots.json \
  --local-host example-host \
  --exclude-root /absolute/excluded-project \
  --output /absolute/evidence/locations-001.json

giga-archaeology locations-query example \
  --receipt /absolute/evidence/locations-001.json \
  --as-of 2026-09-29T12:00:00Z --max-age-seconds 86400
```

`--root` and `--exclude-root` are repeatable. Simple `--root` entries use the path's
basename as the declared project ID, with unknown owner, role and canon level.
Use a roots file for explicit identities and authority declarations:

```json
{
  "schema": "giga.archaeology.location-roots.v1",
  "roots": [{
    "project_id": "example",
    "host": "example-host",
    "path": "/absolute/project",
    "declared_owner": "example-team",
    "role": "development",
    "canon_level": "canonical_source",
    "authority_level": "project",
    "authority_source": "operator-register",
    "declared_at": "2026-09-29T09:00:00Z",
    "declared_head": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "excluded": false
  }]
}
```

The sanitized multi-level input is in `tests/fixtures/location_inventory.json`.
Its example paths are illustrative; tests do not create clones, linked worktrees,
or runnable source copies.

`--authority-register` aliases `--roots-file`. The adapter also accepts
`giga.machine-authority.v1`, with `hosts.<host>.roots[]` entries. It retains root
`id`, `path`, `owner`, `status`, `purpose`, `verified_head`, `verified_at`, and host
`role`. Project status becomes the declared canon level, purpose the declared role;
missing fields stay unknown. Input context retains only source kind, full-file
hash and schema, plus the bounded authority summaries below. The input register's
path and filename are not recorded in receipts. These summaries contain
only these allowlisted summary fields: global `canonical_host`, `promotion_host`,
and boolean `automatic_remote_promotion`; handoff `status` and `target_host` under
`handoff_summary`. Text values must be nonempty, control-free strings of at most
128 characters. Unsupported or oversized values are omitted, never truncated;
omission means unknown, not a policy decision. Nested records, prose, and all
other handoff/authority fields are not embedded. The file hash binds the complete
input without copying its unrelated operational history into location receipts.
The adapter does not resolve policy precedence or derive an owner from a hostname.

For a register containing several projects, use repeatable `--project-id` to select
exact declared IDs. Other declarations are reported as `PROJECT_NOT_SELECTED` and
receive no filesystem/Git probe. An absent selected ID is an error. Malformed input
fails before any root is probed. At most 1,000 root declarations and 4 MiB of input
are admitted; unsupported register schemas are refused.

## Observations and limits

Each record has a stable ID, a `declared` object, an `observed` object, observation
time and a nullable declared/observed HEAD comparison. Different declarations at
one host/path and multiple declarations of the same canonical level for a project
are reported as conflicts. Distinct source/runtime canon levels are retained.
No declaration wins based on scan order, path, timestamp, HEAD or remote identity.

The inspector uses ancestor/root `lstat` and requires a direct `.git` marker. It
does not search parent repositories, walk root contents, read project code, run
hooks/filters/fsmonitor, fetch objects or contact remotes. Git reads the selected
repository's direct metadata, including gitdir/common-dir dependencies of an
existing linked worktree. Listed worktree paths are evidence only; they are never
opened or added to the scan scope. Bare Git stores without a `.git` marker are
currently reported `NOT_GIT`; they are not silently treated as clean checkouts.

The fixed Git operations are HEAD, symbolic HEAD, index-versus-HEAD comparison,
`worktree list --porcelain -z`, and local remote URL configuration without includes.
Global/system Git configuration, optional locks, lazy fetch, replacement objects,
and fsmonitor are disabled. Git failures become partial evidence with named unknowns;
raw stderr is not published. A HEAD change during observation is marked `UNSTABLE`.
This is a sequential observation, not an atomic snapshot of every metadata field.

Dirty state has a deliberate scope: staged changes establish `DIRTY`. A clean
index leaves overall state `UNKNOWN`; unstaged and untracked content is not inspected.
This command cannot certify a clean working tree or equivalence between copies.
Remote identities retain host/repository only, dropping URL credentials, query and
fragment; local paths and unsupported transports are redacted. SSH host aliases are
not resolved. Local configuration and matching remotes do not prove project identity.

Excluded roots (including descendants), common broad home/system roots, sensitive
path components, and symlink paths are skipped or refused before Git execution.
Sensitive components reuse the navigation inventory policy. Every receipt reports
the exact requested, attempted and scanned roots, selected IDs, exclusions and gaps.
Unregistered locations, listed worktree path state and remote liveness remain unknown.
`global_completeness`, `authority_granted`, `cleanup_permitted`, and `safe_to_delete`
are always false. This module never relocates, deletes, merges, promotes, or certifies
a copy safe to delete.

## Refresh, query and API

Refresh publishes a new immutable JSON receipt outside every declared local root.
An existing receipt cannot be overwritten; choose a new output name on each refresh.
Inspect returns JSON without publishing. Query reads only the supplied sealed receipt,
verifies its self-hash and authority boundary, and matches declaration text
case-insensitively. A self-hash establishes internal integrity, not trusted authorship.
Query carries forward coverage and conflicts even when results are filtered.

Query reports `WITHIN_MAX_AGE`, `STALE` or `UNKNOWN`, based on recorded time and the
explicit `--as-of`/`--max-age-seconds` policy. Future or missing times are unknown;
no query claims live freshness.
Query also reports `declaration_freshness` independently; a recent observation does
not refresh an old or undated authority declaration.

`--observed-at` supplies an explicit timestamp for
reproducible inspections. The caller must supply it truthfully. Ordering, identities
and sealed output are deterministic for identical inputs, metadata and timestamp;
live invocations naturally differ when observation time or Git state changes.

The public `evidence_source` argument accepts only the documented explicit-input
kinds or the exact bounded registered-input shape. Unsupported fields, kinds,
schemas and malformed digests are rejected before any root is probed; registered
summaries are re-filtered through the same allowlists before receipt sealing.

The canonical Python API exports `load_location_roots`, `inspect_locations`,
`refresh_locations`, `query_locations`, and `LocationInventoryError` from
`modules.operations.archaeology`. Existing `archaeologist` compatibility imports
resolve to the same implementation. The release build allowlist includes the module.
This bounded increment does not claim hosted cross-platform certification or expand
the previously published beta's source-mapping validation.

## Increment verification (2026-09-29)

The focused location, public identity, map-catalog and portable OS-support suite
passed 44 tests on Linux:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider \
  tests/test_location_inventory.py tests/test_archaeology_identity.py \
  tests/test_archaeology_map_catalog.py tests/test_os_support.py
```

A live CLI refresh/query smoke check used the exact machine-authority register
with only `giga-archaeology` selected. It inspected only the registered Linux
workspace, observed the expected branch and base HEAD
`93371f9158d5c339cf050355a8203065e68f0b62`, and successfully queried the sealed
receipt without rescanning. The inactive historical location and unselected
projects remained gaps. No worktree was created or traversed. The check does not
establish global coverage, clean working-tree state, or Windows certification.

The authority-summary follow-up passed the same suite with 51 tests. Regression
coverage confirms unrelated handoff/authority records never enter receipt output,
the complete input hash remains intact, and overlong or non-scalar summary values
are omitted without truncation.

The publication-gate follow-up passed 52 focused tests. Its distinctive handoff
sentinel is absent from inspect/refresh/query API and CLI results and both saved
receipts. The real wheel builder was exercised twice entirely in memory: bytes
matched, current inventory source/documentation and the CLI entry point were
present, and every wheel RECORD hash and size validated. No package was extracted
or installed into a second execution surface.

The live Linux inspect/refresh/query smoke was repeated at
`fba2069af2514c183d52a8bf4aba986be9c21f67`. Only the canonical workspace was
inspected; fixed-time inspect and refresh results matched, query verified the
receipt without rescanning, and source context contained only the five allowlisted
authority fields plus input identity/hash/schema. The 22 unselected/remote register
entries remained explicit gaps, not claims of global coverage.

The register-path privacy correction passed the same 52-test suite, including
the in-memory wheel build. Its regression first failed on the former `path` field;
it now enforces the exact source-metadata field set and proves the distinctive
register filename and absolute path are absent from all inspect/refresh/query
API results, CLI results and saved receipts. Existing immutable receipts are not
rewritten by this source correction.
The public API evidence-source boundary follow-up passed the focused suite on
Python 3.11, 3.13 and 3.14 (55 tests per interpreter) on Linux. Regression
coverage rejects unsupported kinds/fields before any root observation. Hosted
macOS and Windows CI results remain unverified.
