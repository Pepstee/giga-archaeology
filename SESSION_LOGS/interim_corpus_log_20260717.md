# Interim log — corpus landings, 16–17 Jul 2026

*Not a numbered workstream session; operator-directed work executed alongside Session 01.
Everything here is groundwork Session 04 would otherwise redo.*

## Landed (durable artefacts)

1. **Instagram all-time export processed** → `corpus/raw/instagram_20260717.jsonl`
   (13,295 operator messages, Oct 2023–Jul 2026, mojibake fixed, system lines dropped) via
   new `scripts/extract_instagram.py`. All-time superseded the earlier 1-year extraction.
2. **Casual-mode training pairs** → `corpus/training/instagram_pairs.jsonl` (7,062 chat-format
   context→reply pairs; call-logs and auto-messages cleaned) via new
   `scripts/build_instagram_pairs.py`. Fine-tune-ready (local LoRA target: M2/24GB, MLX,
   3B–7B multilingual base — RU/EN/KR present in data).
3. **Claude.ai export processed** → `corpus/transcripts/claude_conversations.jsonl` (4,301
   two-sided turns, 301 conversations, Jun 2024–Jul 2026) — enables ask-vs-accept
   retrospectives.
4. **`corpus/MANIFEST.md`** — full inventory, schemas, counting rules, pending-source table.
5. **`scripts/extract_discord.py`** — ready for the Discord export (era-tagging built in).
6. Telegram librarian (Session 06 surface) set up and verified end-to-end; master table updated.

## Decisions

- `raw/prompts_20260716.jsonl` (2,584 records) is the **canonical** prompt corpus — it already
  contained the claude-web prompts; a freshly-extracted duplicate file was found 100% redundant
  and truncated to 0 bytes (`raw/claude_20260716.jsonl`) — **deletion awaits operator approval**.
- Discord: harvest ratified (volume + longitudinal uniqueness + perishability), with the
  era-tag rule to protect current-mode training. Official export = his half only; full-thread
  scraping via DiscordChatExporter breaches Discord ToS — operator's call, deferred.
- Virtual-Artiom "modes" design (work / casual / flirty) recorded; casual is now the first
  trainable mode.

## Open

- Operator to file Discord + ChatGPT export requests (and Telegram desktop export any time).
- 628 MB Instagram zip in folder root — archive off-folder when cleanup chat is done.
- Deletion approval for the 0-byte deprecated file.
