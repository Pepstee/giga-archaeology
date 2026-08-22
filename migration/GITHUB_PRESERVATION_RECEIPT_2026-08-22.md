# Gigabyte GitHub preservation receipt

Status: **COMPLETE — deletion gate satisfied**

Verified at: `2026-08-22T07:39:44Z`

GitHub account: `Pepstee` (`Artiom Gutu`)

Commit identity used for new preservation commits: `Artiom <gutu.artiom444@gmail.com>`

## Scope and decision

This receipt covers the material software histories involved in retiring the old Gigabyte
Windows/Ubuntu working environment, plus the canonical Mac working trees used to reconcile
and publish those histories. No Gigabyte deletion was permitted until the GitHub checks below
passed.

The remaining live `C:\Users\gutua` cutover plan contains only two Windows activity/notification
SQLite databases. Their archived copies were already hash-matched in ArtVault; neither file is a
source repository. The retired Ubuntu export remains intact in ArtVault and was not deleted by
this GitHub operation.

Temporary Mac-only staging trees such as `.codex-tmp`, `.playwright-cli`, and `.work` were not
treated as independent product repositories and were not added to GitHub. They remain on the Mac,
outside the Gigabyte deletion scope. Their canonical source repositories and relevant committed
branches are covered below.

## Existing GitHub repositories advanced

All pushes were ordinary fast-forwards; no force push or history rewrite was used.

| Repository | Branch | Verified GitHub commit |
|---|---|---|
| `Pepstee/deal-sniper` | `main` | `2779295d40b66924d71e4bbd8b95e44c75b96119` |
| `Pepstee/digital-twin` | `main` | `4d48453ee58d6a2fedbc925eaf67e62d7f0ef9c5` |
| `Pepstee/situation-monitor` | `main` | `ff47715011c42198466ad487088a0911bbeef5c6` |
| `Pepstee/learning-accelerator` | `main` | `598eab50ba1e4357279e8adddfd495ed1930841b` |
| `Pepstee/local-llm-stack` | `main` | `15d746268c357bca1e93f5254f3002b6a941eb8d` |
| `Pepstee/travel-designer` | `main` | `1fd630fdc57b488842b3417a9ef332d7b1737e67` |
| `Pepstee/writing-assistant` | `main` | `b7a6d88e5f2b46adcc9f88e619b48c4fc9c02bda` |

Local worktree branch labels whose commits were already reachable on GitHub were also published
for `Orchestrator`, `digital-twin`, `learning-accelerator`, `local-llm-stack`,
`travel-designer`, and `writing-assistant`.

## New private preservation repositories

The following repositories were created as **PRIVATE** and verified after push:

| Repository | Representative preserved ref | Verified GitHub commit |
|---|---|---|
| `Pepstee/orchestrator-v3` | `efficiency/e2-shadow-cache` | `85bd10a8a02c413b15ccb939a66f162a5f7df5e8` |
| `Pepstee/prediction-ledger-canary` | `main` | `84f7930c3eb9e50ca12585643c6ae58931f9ad6e` |
| `Pepstee/giga-user-v2` | `codex/jsr-002-baseline-r3` | `a4b2d5ac3ecd0a5d69f77ee95fd925df8e54d801` |
| `Pepstee/giga-user` | `codex/giga-modularization-20260731` | `faf653b666d6d0de8ecc820d284f5bd8d883d378` |
| `Pepstee/job-application-automation` | `codex/jaa-assurance-gutua-handoff-20260805` | `e6d4035cf541c2da57f2c326d772cbd549f7fdcd` |
| `Pepstee/p-gigabyte-archive` | `main` | `e33ca3bc4ed95b87ca893c033736b3a5af1b9a05` |
| `Pepstee/transitvpn2-gigabyte-archive` | `main` | `0ebd48b4b82e6350fed1db2d31ef59095d3c5a8e` |

`job-application-automation` contains 52 local heads from the clean nested repository and the
active runtime repository. The sorted local and GitHub ref manifests both hash to
`de83b5977861fc79a312d0a233dcad43e220f3d9de74886c6d7f2c5a180d2297`.

## Recovered Ubuntu-only histories

The retired Ubuntu archive exposed four tips that were not reachable from the current Mac clones.
Only their Git databases were recovered for inspection. Credential-pattern and 100 MB object
checks passed before publication.

| GitHub repository/ref | Verified GitHub commit |
|---|---|
| `Pepstee/Orchestrator` — `archive/gigabyte-ubuntu-20260821/main` | `32efb0797905078a6917d748ce93efd46f7527be` |
| `Pepstee/Orchestrator` — `archive/gigabyte-ubuntu-20260821/feature-local-llm` | `4db38efd70c39f00d3d77f3599109618d50810dc` |
| `Pepstee/situation-monitor` — `archive/gigabyte-ubuntu-20260821/main` | `9f70488ebe9f1572fbf7e0f6879b13aeaa4ad12a` |
| `Pepstee/situation-monitor` — `archive/gigabyte-ubuntu-20260821/wt-7c2f873da4a7` | `4053cac0e5fd5e656c19e37d350633b96326a542` |

The other archived canonical tips (`deal-sniper`, `digital-twin`, `learning-accelerator`,
`local-llm-stack`, `travel-designer`, `writing-assistant`, and `orchestrator-v3`) were verified as
ancestors of GitHub remote branches.

Recovery bundles remain in ArtVault with these SHA-256 hashes:

- `edge-ubuntu-20260821.bundle`: `94b4974aab511a3508ccae5f1c94fc90376304ba77f91e4c308e31a12b785d76`
- `orchestrator-ubuntu-20260821.bundle`: `ba867f761bcfbf7d0c475195bb120e819cf0e8999d5d512779d035b5df2647a9`
- `p-ubuntu-20260821.bundle`: `fbd55a20fe632b6c818c924285fa8665d9791bf108be82ff63b25047d6bfc06b`
- `transitvpn2-ubuntu-20260821.bundle`: `73a5fcd6c2b6187a8107198b165fa5021478afd819623b36a98a7f3c24e39afb`

## Safety checks and commit identity

- Outgoing histories were checked for private-key blocks, GitHub/provider/cloud token forms,
  JWTs, credential-like filenames, and blobs over 100 MB.
- Apparent matches were inspected without emitting their values. They were deliberate redaction
  test fixtures, CSS class names, or long file paths—not live credentials.
- New commits created during this preservation pass are authored by
  `Artiom <gutu.artiom444@gmail.com>`:
  - `85bd10a8a02c413b15ccb939a66f162a5f7df5e8`
  - `e6d4035cf541c2da57f2c326d772cbd549f7fdcd`
  - `7990ad470872dd72abac0bd2e31002a19a9f45a9`
  - `faf653b666d6d0de8ecc820d284f5bd8d883d378`
- Four temporary repository-scoped GitHub deploy keys were used to publish archive-only commits.
  All four were revoked immediately after exact remote SHA verification.
- Tests relevant to the newly committed isolation and gate work passed (`17 passed, 1 skipped`
  and `28 passed, 2 skipped`). Other pre-existing suites with optional/provider dependencies were
  preserved honestly rather than rewritten during this backup operation.

## Gate result

The software preservation prerequisite is satisfied. The already-approved Windows cutover,
remote-recovery setup, Tailscale repair, and Serge wallpaper task may now proceed. Any destructive
step must still use the exact precomputed Windows deletion plan and verify the resulting state.
