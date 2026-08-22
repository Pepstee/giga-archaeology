#!/usr/bin/env python3
"""extract_prompts.py — harvest YOUR prompts from local AI chat stores into the corpus.

Session 04's capture backbone (provenance rule applied): hand-authored prompts only;
machine-authored (the orchestrator's headless sessions) excluded by cwd; raw output is
immutable JSONL with full provenance metadata; derived/filtered views come later.

Modes:
  python3 scripts/extract_prompts.py --inventory
      Recon only: list transcript files, sizes, and a schema sample. RUN THIS FIRST —
      the parser was written defensively against an unconfirmed schema; the inventory
      tells us whether it needs adapting before you trust an extraction.

  python3 scripts/extract_prompts.py --extract
      Parse everything, keep human-authored user messages, write:
        corpus/raw/prompts_<date>.jsonl   (one record per prompt, full metadata)
        corpus/raw/prompts_<date>.md      (readable digest, newest first)

Exclusion rules (edit EXCLUDE_CWD_PATTERNS to taste):
  - sessions whose cwd is under the orchestrator repos or its projects/ (machine prompts);
  - user-role entries that are tool results, system reminders, or non-text payloads.

Privacy: output lands in corpus/raw/ inside this folder. Review before anything ingests it —
exports may contain sensitive threads (the no-secrets law: triage is a human act).
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
# Cowork ONLY (operator decision, 16 Jul): Claude Code's store (~/.claude/projects) is
# excluded — on this machine it is dominated by the orchestrator's headless machine sessions,
# so Cowork-only is the cleaner provenance cut. The cwd-exclusion filter below stays as
# belt-and-braces for any orchestrator-adjacent Cowork session.
STORES = [
    HOME / "Library/Application Support/Claude/local-agent-mode-sessions",  # Cowork
]
CODEX_STORE = HOME / ".codex" / "sessions"
CODEX_INDEX = HOME / ".codex" / "session_index.jsonl"
EXCLUDE_CWD_PATTERNS = (
    "agentic-orchestrator", "claude-orchestrator-main", ".worktrees",
)
OUT = Path(__file__).resolve().parent.parent / "corpus" / "raw"
CHATGPT_NAMESPACE_POLICY = OUT.parent / "CHATGPT_NAMESPACE_POLICY.json"


def _iter_files():
    """Canonical transcripts only (schema confirmed by inventory, 16 Jul): the per-session
    `audit.jsonl` and its numeric-suffixed rotations. Nested `.claude/projects/` files are the
    agent-loop's INNER sessions — overlapping content under different session ids (a
    double-count trap) plus machine turns; excluded."""
    for store in STORES:
        if not store.exists():
            continue
        for p in store.rglob("audit.jsonl*"):
            if "/.claude/" not in str(p):
                yield p


def _is_machine(path: Path, cwd: str) -> bool:
    hay = (str(path) + " " + (cwd or "")).lower()
    return any(p in hay for p in EXCLUDE_CWD_PATTERNS)


def _extract_text(msg) -> str | None:
    """Human text from a user-role message; None for tool results / non-text payloads."""
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        text = "\n".join(p for p in parts if p).strip()
        return text or None
    return None


def _looks_injected(text: str) -> bool:
    """Skip harness-injected user turns (system reminders, replay wrappers, UI state).

    Codex persists several machine-authored envelopes as ``role=user`` response items.  They
    can contain a verbatim operator objective, but they are not a new operator utterance and
    must not be re-dated or multiplied in the personal corpus.  The original utterance remains
    available elsewhere in the same task, so these wrappers fail closed here.
    """
    t = text.lstrip()
    return t.startswith((
        "<system-reminder>", "<command-", "<local-command", "Caveat:",
        "<recommended_plugins>", "<environment_context>", "<app-context>",
        "<permissions instructions>", "# AGENTS.md instructions",
        "[[task:", "<scheduled-task", "<codex_internal_context",
        "<codex_delegation>", "<in-app-browser-context", "<heartbeat>",
        "<subagent_notification>", "<turn_aborted>", "<skill>",
    ))


def _codex_titles() -> dict[str, str]:
    """Task titles are stored separately from rollout transcripts."""
    titles: dict[str, str] = {}
    if not CODEX_INDEX.exists():
        return titles
    for line in CODEX_INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("id"):
            titles[item["id"]] = item.get("thread_name") or "Untitled Codex task"
    return titles


def _extract_codex(records: list) -> int:
    """Extract human turns from native Codex desktop rollouts.

    `codex_exec` sessions are machine/headless work and are excluded. Claude Cowork tasks
    imported into Codex may continue receiving new turns here; they are included, then
    de-duplicated against the original Cowork transcript by timestamp + exact text.
    """
    if not CODEX_STORE.exists():
        return 0
    titles, n = _codex_titles(), 0
    for path in CODEX_STORE.rglob("rollout-*.jsonl"):
        try:
            events = [json.loads(line) for line in path.read_text(
                encoding="utf-8", errors="replace").splitlines()]
        except (OSError, json.JSONDecodeError):
            continue
        metas = [e.get("payload", {}) for e in events if e.get("type") == "session_meta"]
        if not metas:
            continue
        meta = metas[-1]
        originator = meta.get("originator")
        if originator not in {"Codex Desktop", "Claude Cowork"}:
            continue
        cwd = meta.get("cwd", "")
        if _is_machine(path, cwd):
            continue
        session_id = meta.get("session_id") or meta.get("id")
        title = titles.get(session_id, "Untitled Codex task")
        for event in events:
            if event.get("type") != "response_item":
                continue
            payload = event.get("payload", {})
            if payload.get("type") != "message" or payload.get("role") != "user":
                continue
            parts = [block.get("text", "") for block in payload.get("content", [])
                     if isinstance(block, dict) and block.get("type") == "input_text"]
            text = "\n".join(part for part in parts if part).strip()
            if not text or _looks_injected(text):
                continue
            records.append({
                "ts": event.get("timestamp"),
                "text": text,
                "source": f"codex-desktop:{title[:60]}",
                "session": session_id,
                "channel": "codex-desktop",
            })
            n += 1
    return n


def inventory() -> int:
    total = 0
    for store in STORES:
        print(f"\n== {store} {'(exists)' if store.exists() else '(MISSING)'}")
        if not store.exists():
            continue
        files = sorted(store.rglob("*.jsonl"), key=lambda p: -p.stat().st_size)
        others = [p for p in store.rglob("*") if p.is_file() and p.suffix != ".jsonl"]
        print(f"   {len(files)} .jsonl files, {len(others)} other files "
              f"(suffixes: {sorted({p.suffix for p in others})[:8]})")
        for p in files[:5]:
            print(f"   {p.stat().st_size/1024:8.0f} KB  {p.relative_to(store)}")
        if files:
            print("   --- schema sample (first parseable line keys) ---")
            for ln in files[0].read_text(encoding="utf-8", errors="replace").splitlines()[:8]:
                try:
                    d = json.loads(ln)
                    print(f"   keys={sorted(d.keys())[:10]} type={d.get('type')} "
                          f"role={(d.get('message') or {}).get('role') if isinstance(d.get('message'), dict) else d.get('role')}")
                except json.JSONDecodeError:
                    print("   (unparseable line)")
        total += len(files)
    print(f"\ninventory total: {total} transcript files")
    return 0


def _extract_claude_export(records: list) -> int:
    """Web-Claude account export (schema confirmed 16 Jul: 301 conversations, 2024-06 → now).
    conversations.json: chat_messages[].sender == 'human', .text. design_chats/*.json:
    messages[].role == 'user'. Channel provenance: 'claude-web'."""
    n = 0
    export_root = OUT.parent / "claude-export"
    for cj in export_root.glob("*/conversations.json"):
        for conv in json.loads(cj.read_text(encoding="utf-8", errors="replace")):
            cname = conv.get("name", "")
            for m in conv.get("chat_messages") or []:
                if m.get("sender") != "human":
                    continue
                text = (m.get("text") or "").strip()
                if not text or _looks_injected(text):
                    continue
                records.append({"ts": m.get("created_at"), "text": text,
                                "source": f"claude-web:{cname[:50]}",
                                "session": conv.get("uuid"), "channel": "claude-web"})
                n += 1
    for dj in export_root.glob("*/design_chats/*.json"):
        d = json.loads(dj.read_text(encoding="utf-8", errors="replace"))
        for m in d.get("messages") or []:
            if (m.get("role") or (m.get("content") or {}).get("role")) != "user":
                continue
            c = m.get("content")
            text = (c.get("content") if isinstance(c, dict) else c if isinstance(c, str) else "") or ""
            text = text.strip()
            if text and not _looks_injected(text):
                records.append({"ts": d.get("created_at"), "text": text,
                                "source": f"claude-design:{(d.get('project') or {}).get('name','')[:40]}",
                                "session": d.get("uuid"), "channel": "claude-web"})
                n += 1
    return n


def _allowed_chatgpt_namespaces() -> set[str]:
    """Return namespaces approved for the operator-authored canonical prompt corpus.

    Unknown namespaces fail closed. Account ownership is not message authorship: shared
    accounts require conversation-level triage before their prompts can enter this corpus.
    """
    if not CHATGPT_NAMESPACE_POLICY.exists():
        return {"default"}
    policy = json.loads(CHATGPT_NAMESPACE_POLICY.read_text(encoding="utf-8"))
    namespaces = policy.get("namespaces", {}) if isinstance(policy, dict) else {}
    return {
        name for name, config in namespaces.items()
        if isinstance(config, dict) and config.get("include_in_operator_prompt_corpus") is True
    }


def _extract_chatgpt_snapshot(
        records: list, allowed_namespaces: set[str] | None = None) -> int:
    """Append the newest snapshot from every separately named ChatGPT export namespace.

    ``extract_chatgpt.py`` owns the account-export schema and canonical-branch logic.
    Keeping that parser separate lets the daily local harvester consume a stable JSONL
    view without reopening large exports on every run. The unnamespaced first account is
    namespace ``default``; files such as ``chatgpt_prompts_gpt2_2026_20260719.jsonl`` form
    independent namespaces. Selecting one latest file globally would silently replace the
    first account when a second export lands.
    """
    snapshots = sorted(OUT.glob("chatgpt_prompts_*.jsonl"))
    if not snapshots:
        return 0
    latest_by_namespace: dict[str, Path] = {}
    for snapshot in snapshots:
        stem = snapshot.stem.removeprefix("chatgpt_prompts_")
        parts = stem.rsplit("_", 1)
        if len(parts) == 1 and len(parts[0]) == 8 and parts[0].isdigit():
            namespace, stamp = "default", parts[0]
        elif len(parts) == 2 and len(parts[1]) == 8 and parts[1].isdigit():
            namespace, stamp = parts
        else:
            continue
        incumbent = latest_by_namespace.get(namespace)
        if incumbent is None or snapshot.name > incumbent.name:
            latest_by_namespace[namespace] = snapshot
    allowed = (_allowed_chatgpt_namespaces()
               if allowed_namespaces is None else allowed_namespaces)
    n = 0
    for namespace, snapshot in sorted(latest_by_namespace.items()):
        if namespace not in allowed:
            continue
        for line in snapshot.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict) or not isinstance(record.get("text"), str):
                continue
            record.setdefault("export_namespace", namespace)
            records.append(record)
            n += 1
    return n


def _deduplicate_records(records: list[dict]) -> list[dict]:
    """Remove capture duplicates without erasing distinct ChatGPT account provenance.

    Two separately namespaced account exports can contain the same text at the same timestamp
    (for example after a shared/imported conversation).  Those records are separate evidence
    even when their contents match, so the namespace participates in the identity key.
    """
    seen, unique = set(), []
    prior_channel_texts: set[str] = set()
    for record in records:
        # Codex can import an entire Claude Cowork task and then continue it. Prefer the
        # original source for any exact overlap while retaining genuinely new continuations.
        if (record.get("channel") == "codex-desktop"
                and record["text"] in prior_channel_texts):
            continue
        if record.get("channel") == "chatgpt-web":
            # The account extractor already removes abandoned branches. Preserve distinct
            # exported conversations even when shared/imported chats have identical text and
            # timestamps; conversation provenance is part of the evidence identity.
            key = (
                record.get("export_namespace"),
                record.get("session"),
                record.get("ts"),
                record["text"],
            )
        else:
            key = ((record.get("ts"), record["text"]) if record.get("ts")
                   else (record.get("session"), record["text"]))
        if key not in seen:
            seen.add(key)
            unique.append(record)
            if record.get("channel") != "codex-desktop":
                prior_channel_texts.add(record["text"])
    return unique


def extract() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    records, skipped_machine = [], 0
    for f in _iter_files():
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for ln in lines:
            try:
                d = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "user":
                continue
            if d.get("isReplay"):          # session-resume replays — duplicates at source
                continue
            if d.get("parent_tool_use_id"):  # sub-agent loop turns — not his typing
                continue
            msg = d.get("message") if isinstance(d.get("message"), dict) else d
            if msg.get("role") != "user":
                continue
            cwd = d.get("cwd", "")
            if _is_machine(f, cwd):
                skipped_machine += 1
                continue
            text = _extract_text(msg)
            if not text or _looks_injected(text):
                continue
            records.append({
                "ts": d.get("timestamp") or d.get("_audit_timestamp"),
                "text": text,
                "source": str(f),
                "session": d.get("session_id") or d.get("sessionId"),
                "channel": "cowork",
            })
    web_n = _extract_claude_export(records)
    chatgpt_n = _extract_chatgpt_snapshot(records)
    codex_n = _extract_codex(records)
    # De-duplicate retries and Cowork tasks imported into Codex. Timestamp + exact text
    # preserves repeated short replies sent at genuinely different times.
    unique = _deduplicate_records(records)
    jl = OUT / f"prompts_{stamp}.jsonl"
    jl.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in unique) + "\n",
                  encoding="utf-8")
    md = OUT / f"prompts_{stamp}.md"
    md.write_text("\n\n---\n\n".join(
        f"**{r['ts'] or 'undated'}** · `{Path(r['source']).parent.name}`\n\n{r['text']}"
        for r in sorted(unique, key=lambda r: str(r["ts"] or ""), reverse=True)),
        encoding="utf-8")
    by_channel = {}
    for r in unique:
        by_channel[r.get("channel", "?")] = by_channel.get(r.get("channel", "?"), 0) + 1
    print(f"extracted {len(unique)} human prompts by channel {by_channel} "
        f"({skipped_machine} machine-session entries excluded; claude-web raw {web_n}; "
        f"chatgpt-web raw {chatgpt_n}; codex-desktop raw {codex_n}) "
          f"-> {jl.name}, {md.name}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", action="store_true")
    ap.add_argument("--extract", action="store_true")
    a = ap.parse_args()
    raise SystemExit(inventory() if a.inventory or not a.extract else extract())
