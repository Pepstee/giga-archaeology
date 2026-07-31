# Gigabyte software-factory migration — completion record

**Outcome:** PASS. The Mac source trees and the canonical Gigabyte WSL trees were compared
entry-by-entry using file type, portable mode, symlink target, byte size and SHA-256. Final
comparison receipts report zero missing, zero unexpected and zero changed entries.

## Canonical WSL locations

- Factory root: `/home/gutua/software-factory`
- Orchestrator: `/home/gutua/software-factory/agentic-orchestrator`
- GIGA harness: `/home/gutua/software-factory/giga-user`
- Preserved Mac control layer: `/home/gutua/software-factory/portable-user-config`
- Original WSL control-layer backup:
  `/home/gutua/software-factory/pre-activation-user-config-20260722`
- Failed intermediate activation preserved at:
  `/home/gutua/software-factory/partial-activation-user-config-20260722`

Compatibility links under `/Users/admin` resolve preserved absolute Mac paths to the canonical
WSL trees and active WSL control directories.

## Deliberate exclusions

Only the personal export/corpus payload was excluded:

- `giga-user/corpus/`
- `giga-user/package.zip`
- `giga-user/instagram-artiom.png-2026-07-16-58GCGdnZ.zip`
- `giga-user/1916b63abd801fbb5abf9b44f98d87a68ccd5db992b2a4d30567dd8a4ed29a85-2026-07-19-08-37-41-df72519dd898472489071b0441745ac3.zip`

No Mac source data was deleted during migration.

## Verification evidence

- `agentic-orchestrator`: 210,477 included entries and 16,414,624,122 regular-file bytes.
- `giga-user`: final counts and digest are bound in `receipts/source-giga-user.json` and the
  corresponding destination manifest.
- Final receipts:
  - `receipts/comparison-agentic-orchestrator.json`
  - `receipts/comparison-giga-user.json`
- Both receipts: `passed=true`, `missing_count=0`, `unexpected_count=0`, `changed_count=0`.
- 982 detected SQLite databases passed `PRAGMA integrity_check` and
  `PRAGMA foreign_key_check`; failures: 0.
- `git fsck --no-dangling` passed for the outer orchestrator, orchestrator-v3 and JAA repos.
- WSL syntax checks passed for the four intentionally dirty Linux-isolation files and
  `run_forever.sh`.
- The skill-router inventory audit passed with 23 WSL-native active skills. The full Mac Codex
  and Claude plugin trees are preserved in `portable-user-config` but are not activated as
  Linux plugins because cached plugin binaries/configuration may be platform-specific.
- Codex, Claude Code and GitHub CLI are authenticated in WSL. No raw credential stores were
  copied from the Mac or from chat history.

## Preserved repository state

- Outer orchestrator: `main` at `07ea5aaee3531f7b5a2d42af56e3e285f79f8eac`.
- orchestrator-v3: `efficiency/e2-shadow-cache` at
  `253a9eb677ed10fe7176d6dea098ddaa9ebf4c29`, preserving exactly:
  - modified `dispatch/isolation.py`
  - modified `dispatch/runner.py`
  - modified `tests/test_container_runner_integration.py`
  - untracked `tests/test_linux_isolation_certification.py`
- JAA: clean `main` at `3679d98b1402b434e1e55c79b8b7d8a4f0a3c14a`.
- `STOP` remains armed with:
  `JAA-01 controlled certification window; factory must remain stopped.`
- `orchestrator-v3.service` and the obsolete Gigabyte
  `market-aligner-collector.service` are inactive and disabled. No factory process was launched.

## Resume order on Gigabyte

1. Read
   `agentic-orchestrator/projects/orchestrator-v3/docs/efficiency/JAA_ORCHESTRATOR_SKILLTREE_HANDOFF_2026-07-22.md`.
2. Keep `STOP` armed. Settle and certify the preserved WSL/Linux isolation changes, then verify
   that the efficiency profile is genuinely active. Address orchestrator inefficiencies first.
3. Resume JAA-01 only after the factory harness is certified. Fix and judge the three recorded
   persistence-integrity gaps: pre-lease proposal reuse, strict non-empty unique source/claim
   identifiers, and malformed present model metadata.
4. Certify JAA-01, then continue JAA-02 onward. Do not restart unattended factory work until the
   relevant gates pass and model-role configuration is explicitly chosen.

The Mac remains authoritative for the digital twin, Jarvis/personal memory and Market Aligner.
Mac-side JAA/factory cleanup and removal of the older `/home/gutua/giga` Gigabyte installation
were deliberately deferred; both are destructive follow-up operations and are not prerequisites
for using the verified canonical factory.
