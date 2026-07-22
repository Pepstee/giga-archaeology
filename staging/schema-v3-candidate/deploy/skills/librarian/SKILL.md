---
name: librarian
description: >
  Artiom's second memory — file thoughts into it, surface collisions, and raise due
  reminders. Use this skill whenever he says "remember this", "file this", "note this",
  "remind me", "add to memory", "what did I say about X", "what do I know about X", asks
  for the weekly memory sweep, or simply throws out an idea, decision, fact, or reminder
  worth keeping — even mid-task in an unrelated conversation. Also use it when starting
  substantial work for him: check the index for reminders and relevant entries first.
---

# Librarian — the second memory

## The one store (non-negotiable)

The memory lives in exactly one place: the **`memory/` directory of the giga-user folder**
(`/Users/admin/Documents/giga-user/memory/` — in sandboxed shells it may be mounted under a
different root; resolve the giga-user folder first). Layout: `INDEX.md` (always read first),
`MEMORY_PROTOCOL.md` (the full contract — read it before your first write in a session),
`entries/` (one thought per file).

If this folder is not reachable from the current session, **request folder access or refuse
loudly**. Never file into a local improvisation, a different memory system, or plain chat
text — a second store silently forks the memory and corrupts the single-source-of-truth
this system exists to provide.

## The three duties (every invocation, in order)

1. **FILE** — classify the thought (`idea | decision | fact | reminder | question`), write
   `entries/YYYY-MM-DD-<slug>.md` with the frontmatter format defined in
   `MEMORY_PROTOCOL.md`, link related entries `[[by-slug]]`, and regenerate that entry's
   line in `INDEX.md`. One thought per file — split compound thoughts.
2. **COLLIDE** — filing is never passive. Check the new entry against the index: does it
   contradict, extend, duplicate, or unlock an existing entry? Say so out loud. The
   connections he hasn't made himself are the entire point of this memory. If a new thought
   contradicts a standing `decision` entry, challenge before filing — silent contradiction
   is corruption.
3. **REMIND** — scan `type: reminder` entries whose trigger (a date, or "when discussing
   <topic>") matches the current conversation, and surface them unprompted. A reminder
   surfaced twice without action gets flagged for a decision: act, reschedule, or archive.

## Laws (from the protocol — it is canonical if this summary ever drifts)

- Never delete; supersede or archive with a pointer. History is data.
- No secrets: no credentials, tokens, or anything he wouldn't keep in plaintext.
- Retrieval questions ("what did I say about…") answer from entries, cited by slug.
- The weekly sweep, when asked: resurface due reminders; find one non-obvious connection
  between a recent entry and a dormant one; propose archiving stale actives; ≤10 lines.
- Use only file operations and shell — no environment-specific tools — so this skill
  behaves identically in Cowork, Claude Code, and orchestrator-v3.
