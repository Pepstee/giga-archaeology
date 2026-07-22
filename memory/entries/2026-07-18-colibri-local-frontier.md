---
type: fact
tags: [local-llm, tools, virtual-artiom, strategy]
created: 2026-07-18
status: active
---
Colibri (github.com/JustVugg/colibri): pure-C, zero-dependency MoE engine running GLM-5.2
(744B params, frontier-tier) on consumer machines by keeping the ~9.9GB dense core in RAM
(int4) and streaming the 21,504 routed experts (~370GB) from NVMe with per-layer LRU cache.
Proof that frontier-scale LOCAL inference exists in July 2026 — but glacial: 0.05-1 tok/s;
Apple M5 Max ~0.25-1 tok/s reported; his M2 Air 24GB would run it (min 16GB) but needs
~370GB external SSD and would produce ~0.05-0.2 tok/s — minutes per sentence.
Verdict for GIGA: not the vehicle for the virtual twin's interactive modes (the 3B-7B LoRA
path stands, [[2026-07-18-virtual-artiom-modes]]); possibly an overnight oracle (queue one
hard question, wake to a frontier answer); mainly a TREND MARKER on the ElvUI curve
([[2026-07-16-wow-elvui-edge]]) — local frontier is arriving, watch this class of engine.
Architecture lesson mirrors the memory design: one managed hierarchy (RAM/disk = hot/cold),
stream only what routes, cache what repeats — same shape as CONTEXT/entries/corpus tiers.
Source: WebSearch 18 Jul 2026 (repo + Tom's Hardware + benchmark issue #57), filed at
operator request ("critical knowledge for the GIGA project").
