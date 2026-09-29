---
type: "path_query"
date: "2026-09-29T09:55:51.799064+00:00"
question: "Path from archaeology.py to run_navigation_retention() after CLI integration"
contributor: "graphify"
source_nodes: ["archaeology.py", "main()", "run_navigation_retention()"]
---

# Q: Path from archaeology.py to run_navigation_retention() after CLI integration

## Answer

Current source graph at commit aafe486bcdf34a1ebd680f6a1bac379eb8ceefb7 returns archaeology.py --contains [EXTRACTED]--> main() --calls [EXTRACTED]--> run_navigation_retention(). The dispatch edge is modules/operations/scripts/archaeology.py:L1262 and the implementation is modules/operations/archaeology/retention.py:L7977. This confirms source-graph wiring, not runtime certification. Graph SHA-256 60026e2f5e31c579c369a6b22979171b400a5e0b90817b09d44af1c49e0d52ec.

## Source Nodes

- archaeology.py
- main()
- run_navigation_retention()