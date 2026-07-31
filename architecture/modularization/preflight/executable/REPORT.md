# GIGA executable modularisation preflight

Generated: 2026-07-30T15:05:58.261105+00:00

This is a read-only architectural preflight. Dubbing Studio was excluded. Existing repository
files, Git state, services, and skills were not edited, moved, staged, committed, stopped, or
restarted.

## Recovery seal

- HEAD: `82cb47ef82d6973c08513686bcca6ed0469418a7`
- Branch: `main`
- Stable during capture: `true`
- Tracked binary patch: 90,992 bytes (`f8b8c05593e81b989b4767a3f201f08f60795744f8daa6a1f3a5b09dc825f90d`)
- Staged binary patch: 0 bytes (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`)
- Untracked files: 561, 444,729,552 bytes
- Large raw archives: 0 hashed but not copied
- Git refs bundle created: `true`
- Private backup: `/Users/admin/.giga/backups/giga-modularization-preflight-20260730`

## Executable surface

- Scanned text/config files: 720
- Executable surfaces: 314
- Entrypoint declarations: 303
- Import declarations: 1,929
- Possible writer sites: 1,044
- Absolute/tilde path references: 667
- Environment references: 188
- Schedule directives: 24,388
- Service directives: 61
- Python parse errors: 0

The scanner is deliberately conservative: writer sites include explicit filesystem mutations and
possible cwd-relative writes. Each record carries source, line, expression, and target-scope
classification in `executable-inventory.json`.

## Specialised skills packaging

Repository skill code and discovery metadata are separate:

- Repository deploy skill bundles: 2
- Staging copies: 2
- Active personal/system installs observed: 23
- Plugin-cache skill entries observed: 45

`AGENTS.md` and the skill-router registry are routing/discovery metadata; neither activates
`deploy/skills/**`. A first-class specialised-skills module requires a promotion/install boundary,
a complete-bundle digest, an immutable source/version pin, an activation/discovery refresh rule,
one active copy per canonical id, cache invalidation, compatibility metadata, and rollback. No
`SKILL.md` was changed in this wave.

## Start-prevention result

There are 9 uncleared critical/high findings across all gate scopes. 1 of them blocks root
movement in this executable preflight; the remaining findings block only their named activation,
certification, deployment, packaging, or release lane and may be carried through structural
migration as explicit unresolved debt. Root movement must also wait for the separate authority-map,
active-writer, and export-integrity preflights. The authoritative machine list is
`START_PREVENTION_BLOCKERS.json`.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3   architecture/modularization/preflight/executable/verify_preflight.py
```

The verifier checks both manifests, every sealed artifact hash/size, and owner-only permissions
on the private backup.
