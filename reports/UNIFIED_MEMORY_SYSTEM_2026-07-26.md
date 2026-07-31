# Unified memory system — 26 July 2026

## Outcome

The full retained corpus is now queryable as one local SQLite authority:

- `corpus/derived/unified_memory_20260726.sqlite3`
- 532,274 exact message/event observations
- 504,498 text-bearing observations
- 399,995 text-bearing operator messages used in the language census
- 5,176 conversations/channels
- 23,702 deterministic conversation sessions
- 92 represented calendar months
- 28 interpretive claims linked through 103 message-level evidence edges
- SQLite integrity check: `ok`

The companion `unified_memory_chronological_20260726.jsonl.gz` is a portable chronological
Tier-1 export. The SQLite file is the one-file memory authority because it can retain exact
evidence, chronology, search, sessions and interpretations without flattening their
provenance.

No provider export was edited, extracted in place or rewritten. All source archives and
provider JSON remain the read-only evidence layer; everything named above is derived.

## Source coverage

| Source view | Records | Coverage |
|---|---:|---|
| Teen Discord account `vstee` / `B L Λ D E` | 248,752 | Account-owner messages only; June 2018–May 2026, concentrated in 2020–2022 |
| Primary Discord account `qstee` / `Λstee` | 83,779 | Account-owner messages only; August 2022–July 2026 |
| Telegram | 99,411 | Two-sided messages and service events |
| Instagram DMs | 45,103 | Two-sided messages, including media/action references |
| Instagram comments | 36 | Operator comments not duplicated by the full DM view |
| ChatGPT pre-2026 export | 35,678 | Two-sided human/model turns |
| Second ChatGPT export (`gpt2`) | 15,214 | Two-sided human/model turns, principally 2026 |
| Claude | 4,301 | Two-sided human/model turns |

Discord timestamps are preserved as provider-naive wall-clock times because the export does
not supply a timezone. Telegram, Instagram, Claude and ChatGPT timestamps are normalised to
UTC where the provider supplies enough information.

## The three memory tiers

### Tier 1 — exact evidence

SQLite view: `tier1_evidence`

This is the non-interpretive layer. Every row includes:

- a stable unified record ID;
- exact message text;
- platform, account namespace, conversation and author role;
- timestamp and timezone basis;
- source file/archive member and source position;
- content hashes;
- direction and whether reciprocal context is available.

Full-text search is available through `messages_fts`. Tier 1 is where “who said what and
when?” is answered. A later interpretation cannot override a Tier-1 message.

### Tier 2 — deterministic structure

SQLite view: `tier2_episodes`; tables: `sessions`, `session_messages`, `monthly_map`.

Messages in the same conversation are grouped into sessions separated by a twelve-hour gap.
This gives reproducible episodes without asking a model to invent event boundaries. Monthly
maps preserve volume, platform, thread and character counts. The whole-corpus signal file
adds reproducible speech, topic, value and affect retrieval signals:

- `corpus/derived/unified_memory_signals_20260726.json`
- 399,995 operator-authored text messages
- nine calendar years and 92 months
- median message: 17 characters / three words
- 319,499 Discord, 38,316 Telegram, 24,665 ChatGPT, 15,400 Instagram and 2,115 Claude
  operator messages

The lexical signals are review queues, not psychological facts. “Anger” means a broad
anger/contempt vocabulary match; it does not mean a month has been clinically classified.

### Tier 3 — evidence-linked interpretation

SQLite view: `tier3_memory_map`; source ledger:
`corpus/derived/tier3_memory_claims_20260726.json`.

Tier 3 currently contains 28 hypotheses:

- eight cross-era behavioural/cognitive patterns;
- relationship and value patterns;
- eight developmental stages;
- strongest documented low and happiness candidates;
- two speech-development claims;
- the Sovereign Architect archetype.

Every claim has:

- type, date range and confidence;
- method and review status;
- exact supporting record IDs;
- an explicit boundary between retained evidence and interpretation.

All claims remain `hypothesis_operator_review`. A high confidence score means that the claim
fits the retained corpus well; it is not a clinical probability and does not bypass Artiom's
right to correct the record.

## Integrity and reconciliation

The database was checked for:

- exact agreement between ingested message count and manifest counts;
- one session membership for every message;
- FTS row count equal to message row count;
- no duplicate stable record IDs;
- foreign-key-safe evidence links;
- successful `PRAGMA integrity_check`.

Current database SHA-256:
`d732e088aaf966e72469caa006198b487a0efc0a415df2bb3d342ef16c9e0e6b`.

Current chronological gzip SHA-256:
`ce117ecbc84127952d5437ad7e2802744d5dc0b401aeb5b51aa364f757ddc756`.

The chronological export contains Tier 1. Tier-3 insertion changes the SQLite hash but does
not change any message row or the chronological export.

## Query examples

Exact evidence:

```sql
SELECT timestamp, platform, thread_title, author_name, text, source_path, source_position
FROM tier1_evidence
WHERE record_id = 'message:discord:teen_vstee:850117460459257896:996579589105139752';
```

All evidence for a claim:

```sql
SELECT claim_id, label, confidence, evidence_role, timestamp, thread_title, text
FROM tier3_memory_map
WHERE claim_id = 'state:strongest-documented-low'
ORDER BY timestamp;
```

Full-text retrieval:

```sql
SELECT m.timestamp, t.title, m.text
FROM messages_fts f
JOIN messages m ON m.message_pk = f.rowid
JOIN threads t ON t.thread_pk = m.thread_pk
WHERE messages_fts MATCH '"неопределенность"'
ORDER BY m.timestamp;
```

## Known limits

1. Both Discord exports are one-sided. They can establish what Artiom sent and when, but not
   what an interlocutor said between those messages.
2. The teen Discord account contains pasted text, copypasta, code, logs, forwards and roleplay.
   Selection is a sign of attention or group performance; it is not automatically an
   autobiographical statement.
3. AI chat exports overrepresent problems, optimisation and questions. They are not a random
   sample of daily life.
4. AI output pasted back by Artiom can be mislabelled by provider role alone. Fine-tuning
   preparation therefore excludes exact reuse of any model-authored text.
5. Absence of messages is not proof of absence of life or emotion.
6. “All memories” means every retained export record is indexed. It does not mean every event
   in Artiom's life was recorded by a platform.

## Original-source recheck

The provider archives were re-hashed after all derived work. Their 26 July SHA-256 values are:

| Original source | SHA-256 |
|---|---|
| Old Discord `package(1).zip` | `c9396462fb02dbb4ed75161582c0c9d07c707dcb597d0613291754850cceef4f` |
| Primary Discord `package.zip` | `6fdf33df674d77badc830d8720b63f0ad9ebab3412f39ebcaf304c78c9050583` |
| Telegram `result.json` | `cb4d6dfd1ed475a5e531853e6a1e8d8f760a8ac2e3ee96d64fe01a640f9cb4c8` |
| Instagram export ZIP | `e800bfcd4b9ede0fb23ff0edfc96001b189e8c34db99a870fe3ec95de0ca01e1` |
| Pre-2026 ChatGPT export ZIP | `dfec969741f549c876db53bbd8f9ee71d5f4d1b4116311f54ae8ce1268a23a2b` |
| Second ChatGPT export ZIP | `f766b446d9a7deb7e5e3b833fe968b44db94102190128959b9c9612d8e586652` |
| Claude export ZIP | `754e30a5d4c1b8781c560687838810724062cb5309a07ecae795dd0e78cd640b` |

These match the previously recorded hashes wherever an adjacent source manifest already
existed. No original source was rewritten.

## Rebuild path

The system is reproducible through:

- `scripts/extract_discord.py`
- `scripts/extract_instagram_full.py`
- `scripts/extract_telegram.py`
- `scripts/build_unified_memory.py`
- `scripts/analyze_unified_memory.py`
- `scripts/load_memory_claims.py`

The original archives remain the authority; the derived database can be rebuilt or superseded
when the next export arrives.
