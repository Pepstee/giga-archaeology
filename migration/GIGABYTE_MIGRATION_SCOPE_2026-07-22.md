# Gigabyte software-factory migration scope — 2026-07-22

## Decision

The Gigabyte becomes the authoritative development host for the autonomous software factory,
orchestrator-v3, JAA and later factory-built projects. The Mac remains the authoritative active
host for Jarvis/personal memory, the digital twin and Market Aligner. The Mac keeps a usable copy
of the generic orchestrator harness, but it must not continue developing JAA or retain the active
JAA runtime/project payload after verified cutover.

The transfer is deliberately loss-averse: copy both project trees in their current state, including
hidden files, Git history, uncommitted changes, worktrees, reports, skills, knowledge graphs,
assurance evidence, receipts, databases, logs, caches and virtual environments. Do not clean,
normalise or rebuild before transfer.

## Source and destination

| Material | Mac source | Gigabyte WSL2 destination |
|---|---|---|
| Orchestrator tree | `/Users/admin/Documents/agentic-orchestrator` | `/home/gutua/software-factory/agentic-orchestrator` |
| GIGA control plane | `/Users/admin/Documents/giga-user` | `/home/gutua/software-factory/giga-user` |
| Codex skills | `/Users/admin/.codex/skills` | `/home/gutua/.codex/skills` |
| Agent skills | `/Users/admin/.agents/skills` | `/home/gutua/.agents/skills` |
| Claude skills | `/Users/admin/.claude/skills` | `/home/gutua/.claude/skills` |
| Portable user rules | selected files under `/Users/admin/.codex` and `/Users/admin/.claude` | versioned snapshot plus active WSL paths |

The destination is Windows 10.0.26200.8875 with Ubuntu under WSL2. WSL user `gutua` has
`/home/gutua` and approximately 929 GB free at discovery time.

## Only project-tree exclusions

These are personal platform exports or their canonical extracted corpus and must remain on the Mac:

1. `giga-user/corpus/`
2. `giga-user/package.zip` — Discord account export
3. `giga-user/instagram-artiom.png-2026-07-16-58GCGdnZ.zip` — Instagram export
4. `giga-user/1916b63abd801fbb5abf9b44f98d87a68ccd5db992b2a4d30567dd8a4ed29a85-2026-07-19-08-37-41-df72519dd898472489071b0441745ac3.zip` — ChatGPT export

No other source-tree path is excluded. In particular, preserve `reports/`, `architecture/`,
`skilltree/`, `deploy/skills/`, every `graphify-out/`, `runtime_evidence/`, `state/`, `staging/`,
all nested `.git` directories, all dirty files and the complete orchestrator project tree.

## External control-layer inclusion

Transfer and activate the portable rules/skills layer:

- `~/.codex/AGENTS.md`, `~/.codex/config.toml`, `~/.codex/rules/` and `~/.codex/skills/`;
- `~/.agents/skills/`;
- `~/.claude/CLAUDE.md` and `~/.claude/skills/`;
- `~/.graphify/` external repository cache used by the knowledge-graph workflow;
- installed plugin trees as a preserved snapshot, not as trusted Linux-ready executables.

Do not transfer personal chat/session databases, browser sessions, Jarvis state, `~/.jarvis`,
Codex/Claude authentication stores or API tokens. Re-authenticate providers on Gigabyte. This is
not data loss: those remain authoritative on the Mac and are outside the factory control plane.

## Machine authority after cutover

| Domain | Authoritative host | Gigabyte copy policy |
|---|---|---|
| Orchestrator and deterministic assurance | Gigabyte | Active |
| JAA and future factory projects | Gigabyte | Active; sole writer |
| GIGA laws, gates, reports, skills and graphs | Gigabyte for factory operation; Mac retained | Active factory control plane |
| Digital twin | Mac | Dormant/reference copy only |
| Jarvis and personal memory | Mac | No personal state transferred |
| Personal corpora and exports | Mac | Excluded |
| Market Aligner | Mac | Dormant/reference copy only |

## Cutover safety rule

Nothing is deleted from the Mac during transfer. Mac-side JAA/project payload removal is a separate,
explicit cleanup after the remote file manifest, Git/dirty-state comparison, SQLite checks, STOP
check and selected test probes all pass. The cleanup must preserve the generic Mac harness and use
a recoverable archive or trash operation.
