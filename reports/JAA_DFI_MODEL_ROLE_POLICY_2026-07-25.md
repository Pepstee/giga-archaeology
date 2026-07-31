# JAA and DFI model-role policy

Date: 25 July 2026  
Scope: Gigabyte software-factory work only

## Verdict

Use one durable Codex coordinator and a risk-routed Claude worker pool. Do not ask every model
to repeat every task and do not force a fixed provider percentage. Independence belongs at
review boundaries; duplication everywhere is cost without corresponding assurance.

## Roles

| Actor | Default role | Use when | Do not use for |
|---|---|---|---|
| Codex frontier coordinator | Programme state, decomposition, integration, deterministic evidence, final cross-provider review | Every JAA and DFI stage | Duplicating a Claude implementation merely to satisfy a ratio |
| Codex fast/read-heavy worker | Repository mapping, logs, test clustering, bounded research | Independent non-writing sidecars | Final certification or ambiguous architecture |
| Claude Sonnet 5 | Primary implementation worker | Normal feature work, refactors, debugging and tests | Final review of its own work |
| Claude Haiku 4.5 | Fast triage worker | Mechanical inspection, classification and simple bounded tasks | Architecture authority or consequential acceptance |
| Claude Opus 5 | High-risk specialist and independent reviewer | Difficult architecture, subtle debugging, large refactors and milestone code review | Routine coding at maximum effort |
| Claude Fable 5 | Rare highest-risk authority | Long-horizon rescue, disputed milestone ruling and release-level assessment | Ordinary implementation or repeated re-review |

Anthropic describes Sonnet 5 as its speed/intelligence balance for coding and agents, Opus 5
for complex agentic coding, Fable 5 for the highest-capability long-running work, and Haiku 4.5
for fast economical sub-agent work. The provider also recommends workload-specific evaluation
and effort tuning rather than assuming a larger model is always required:

- <https://platform.claude.com/docs/en/about-claude/models/overview>
- <https://platform.claude.com/docs/en/about-claude/models/choosing-a-model>
- <https://platform.claude.com/docs/en/about-claude/models/whats-new-opus-5>
- <https://www.anthropic.com/news/claude-sonnet-5>

Codex sub-agents are used only for independent, bounded work. The main coordinator retains
requirements, decisions, evidence and final outputs. Parallelism favours read-heavy or disjoint
work; two write-heavy agents do not share a candidate.

## Cross-model review law

- Claude-authored code receives Codex review against exact candidate bytes.
- Material Codex-authored implementation receives an independent Opus or Fable review.
- No model certifies its own prose or self-report.
- Model verdicts are findings, not certificates. Deterministic tests, negative controls,
  runtime evidence and exact hashes make or withhold certification.
- Review context includes the bounded changed closure, contracts and receipts—not recursive
  logs, unrelated repository history or giant controller state.

## Effort routing

- Haiku: low effort, short bounded tasks.
- Sonnet: low or medium for normal packages; increase only after an observed capability gap.
- Opus: high by default for admitted hard work; xhigh only for a defined difficult gate.
- Fable: high for rare milestone rulings; no standing continuous loop.

Maximum effort is not a quality ritual. It is admitted only when the task's risk or a failed
lower-effort evaluation justifies the extra latency and tokens.

## Quota routing

Provider allocation follows remaining quota and comparative value, not a ceremonial 30/70
split. Sonnet remains the default coder, but Codex can absorb coordination, integration,
deterministic test work and bounded repairs when Claude quota is scarcer. The ledger records
accepted work, not call count.

## Concurrency law

JAA and DFI may operate concurrently because their repositories, worktrees and certificates are
independent. Claude invocations across both lanes are serialised through:

`/home/gutua/software-factory/.control/claude-global.lock`

This protects the shared OAuth credential from refresh races. Codex work, deterministic tests
and read-only analysis may continue in the other lane while one Claude worker owns the lock.

## Promotion

A cheaper/faster model becomes the default for a task class only after it matches the current
model on a representative locked evaluation. A stronger model is promoted only after a
measured failure, risk gate or evaluation advantage. Model reputation alone does not change
routing.
