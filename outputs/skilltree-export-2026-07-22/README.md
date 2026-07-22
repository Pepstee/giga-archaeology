# SkillTree offline export

Captured from the public preview on 2026-07-22T07:51:43.190379+00:00.

## What is included

- `7` departments, `34` functions, and `137` mapped jobs
- `137` playbook entries with prerequisites, ladders, human roles, notes, and file references
- `78` skill metadata records and `78` complete preview excerpts
- `570` normalized graph nodes and `832` directed edges
- `116` distinct first- and third-party links with source provenance
- Raw first-party HTML/JavaScript, a static offline map, CSV tables, JSON, and a rendered screenshot

## Entry points

- `EVERY_SKILL.md` — exhaustive inventory of all 79 named skill files, 291 atomic capabilities, and 137 graph jobs
- `data/all_skills.json`, `data/skills.csv`, `data/capabilities.csv`, and `data/jobs.csv` — machine-readable skill inventories and mappings
- `SKILLTREE_CORPUS.md` — all readable page content in one searchable document
- `data/inventory.json` — counts, scope, and limitations
- `data/graph.json` — exact normalized graph
- `data/nodes.csv` and `data/edges.csv` — spreadsheet-ready graph tables
- `data/links.json` — every discovered link and where it appears
- `offline/index.html` — the original interactive map; serve this folder with a local HTTP server
- `raw/` — source-faithful capture and observed API responses
- `graphify-out/graph.html` — Graphify's interactive knowledge graph
- `graphify-out/GRAPH_REPORT.md` and `graphify-out/graph.json` — clustered audit report and GraphRAG-ready graph
- `SHA256SUMS.txt` — integrity hashes for every artifact

## Boundary

The public page ships preview excerpts, not the paid full runnable skill files. The exporter records those file references and every delivered preview, but does not bypass the site’s access controls. The supplied preview token and email are not stored.
