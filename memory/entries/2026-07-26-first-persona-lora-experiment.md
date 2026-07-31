---
type: fact
tags: [virtual-artiom, lora, corpus, evaluation]
created: 2026-07-26
status: active
---
The first explicitly authorised local persona-LoRA experiment completed on
`mlx-community/Qwen2.5-3B-Instruct-4bit`, using the evidence authority in
[[2026-07-26-unified-corpus-memory-authority]] and preserving the mode separation required by
[[2026-07-18-virtual-artiom-modes]].

The validation-selected speech adapter at iteration 200 reduced 50-batch locked-test loss
from 6.311 to 2.973. It transferred brevity and natural Russian/English private-reply style,
but invented an unspecified deployment cause in a professional boundary case. It remains
unpromoted.

The validation-selected reasoning-steering adapter at iteration 100 reduced locked-test loss
from 5.833 to 3.113, but behavioural evaluation showed that it learned terse questioning
rather than dependable evidence-sensitive reasoning. It failed the current reasoning
promotion suite and is retained only as a research artefact. Model-answer→operator-next-turn
data is therefore evidence for correction cadence, not a thinking clone.

No private corpus or adapter was uploaded. Promotion remains a separate operator-reviewed
decision.

Source: `corpus/training/LORA_PLAN_AND_RUN_20260726.md`;
`corpus/training/adapters/*-best-*/run_manifest.json`.
