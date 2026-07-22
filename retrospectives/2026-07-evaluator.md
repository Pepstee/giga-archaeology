# Retrospective Evaluator Output

Generated: 2026-07-19 09:42 UTC
Window: corpus start to corpus end

## Method and limits

- Counts all eligible records in the three landed, human-authored views. The prompt and transcript views overlap; they are reported separately and never summed.
- ChatGPT follows each conversation's exported canonical branch; abandoned response branches are excluded. Binary/image-only turns remain in the raw export but are absent from text counts.
- Keyword signals and message length are review queues, not behavioural findings. They cannot establish intent, outcome quality, or causal change.
- The evaluator never emits raw message text. Qualitative findings require a human reviewer to return to the source conversation and quote it with context.

## Census

| View | Eligible records |
|---|---:|
| Canonical prompt corpus | 20,107 |
| Claude transcript human turns | 2,115 |
| Claude transcript total text turns | 4,301 |
| ChatGPT transcript human text turns | 17,109 |
| ChatGPT transcript total text turns | 35,678 |
| Instagram operator messages | 13,295 |

## Review signals

| Signal | Result | Interpretation boundary |
|---|---:|---|
| Median human-turn length | 60 characters | Register-dependent; not a quality score. |
| Human turns under 80 characters | 60.1% | A proxy for prompts likely to need context, not proof of under-specification. |
| Evidence/verification vocabulary | 3.6% | A review queue for epistemic standards, not evidence of correctness. |
| Challenge-seeking vocabulary | 0.8% | Does not measure whether challenge changed a decision. |
| Reconsideration vocabulary | 0.4% | English-only lower bound; does not prove a decision reversal. |
| Exact repeated substantive turns | 193 | Duplicate/retry signal only; semantic repetition needs review. |
| Possible secret-bearing records | 427 | Security review required; this count does not disclose content. |

## Human-turn volume by month

| Month | Turns |
|---|---:|
| 2023-09 | 2 |
| 2023-10 | 186 |
| 2023-11 | 100 |
| 2023-12 | 1,116 |
| 2024-01 | 229 |
| 2024-02 | 393 |
| 2024-03 | 178 |
| 2024-04 | 387 |
| 2024-05 | 714 |
| 2024-06 | 485 |
| 2024-07 | 88 |
| 2024-08 | 64 |
| 2024-09 | 201 |
| 2024-10 | 292 |
| 2024-11 | 233 |
| 2024-12 | 789 |
| 2025-01 | 769 |
| 2025-02 | 689 |
| 2025-03 | 687 |
| 2025-04 | 1,325 |
| 2025-05 | 715 |
| 2025-06 | 1,333 |
| 2025-07 | 2,182 |
| 2025-08 | 1,878 |
| 2025-09 | 764 |
| 2025-10 | 1,287 |
| 2025-11 | 1,119 |
| 2025-12 | 414 |
| 2026-01 | 186 |
| 2026-02 | 2 |
| 2026-03 | 38 |
| 2026-04 | 78 |
| 2026-05 | 80 |
| 2026-06 | 33 |
| 2026-07 | 188 |

## Most iterative reasoning conversations

| Conversation | Human turns | Human characters | Turns at least 5,000 characters |
|---|---:|---:|---:|
| Анализ чатов участников | 317 | 32,276 | 1 |
| Deutsch lernen A2 | 215 | 52,343 | 1 |
| Turisti a Venezia | 191 | 14,046 | 0 |
| Jordan Peterson schedule review | 184 | 26,840 | 0 |
| Глубокие посты и шутки | 176 | 274,113 | 19 |
| Map the shadow domains | 171 | 38,577 | 1 |
| Психологический портрет Арта | 153 | 73,317 | 4 |
| Blackpill texter mode | 152 | 9,199 | 0 |
| Blackpill mode activation | 149 | 15,178 | 0 |
| Программа для достижения C1 | 133 | 13,624 | 0 |
| Wardrobe assessment and feedback | 131 | 26,420 | 0 |
| Честный разговор о прошлом | 109 | 89,934 | 3 |

## Required manual checks

1. Sample high-signal conversations from different months before stating any longitudinal claim. Do not use long pasted material as evidence of a personal preoccupation.
2. Separate private/casual register from work/reasoning register; neither predicts the other reliably.
3. Inspect every possible-secret hit locally; rotate exposed credentials and redact only derived artefacts, preserving raw provenance under access control.
4. Record each report hypothesis as confirmed, refined, or discarded by the operator before changing standing context.
