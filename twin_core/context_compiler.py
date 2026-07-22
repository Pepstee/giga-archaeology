"""Deterministic, bounded memory context for provider-neutral model calls."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


TOKEN = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)
LINK = re.compile(r"\[\[([^\]]+)\]\]")
MAX_PACKET_CHARS = 120_000
MAX_PRIMARY_ENTRIES = 10
MAX_LINKED_ENTRIES = 8


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokens(text: str) -> set[str]:
    return {token.casefold().replace("_", "-") for token in TOKEN.findall(text)}


def _document(path: str, text: str, role: str) -> dict[str, str]:
    return {"path": path, "role": role, "sha256": _sha256(text), "content": text}


def compile_context(giga_root: Path, query: str) -> dict[str, Any]:
    """Compile canon + relevant entries without exposing a filesystem tool to the model."""
    giga_root = giga_root.resolve()
    memory = giga_root / "memory"
    required = [
        (giga_root / "CONTEXT.md", "CONTEXT.md", "standing-context"),
        (memory / "MEMORY_PROTOCOL.md", "memory/MEMORY_PROTOCOL.md", "memory-policy"),
        (memory / "INDEX.md", "memory/INDEX.md", "memory-index"),
    ]
    documents: list[dict[str, str]] = []
    for path, relative, role in required:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"required context source missing or unsafe: {relative}")
        documents.append(_document(relative, path.read_text(encoding="utf-8"), role))

    query_tokens = _tokens(query)
    candidates: dict[str, tuple[Path, str, int]] = {}
    today = date.today().isoformat()
    for path in sorted((memory / "entries").glob("*.md")):
        if path.is_symlink():
            raise ValueError(f"memory entry is a symlink: {path.name}")
        text = path.read_text(encoding="utf-8")
        searchable = f"{path.stem} {text}".casefold()
        overlap = sum(1 for token in query_tokens if token in searchable)
        reminder = "\ntype: reminder\n" in f"\n{text}" or text.startswith("---\ntype: reminder\n")
        due = reminder and today in text
        trigger_match = reminder and overlap > 0
        score = overlap * 10 + (30 if due else 0) + (5 if trigger_match else 0)
        if score > 0:
            candidates[path.stem] = (path, text, score)

    selected = sorted(
        candidates.items(), key=lambda item: (-item[1][2], item[0])
    )[:MAX_PRIMARY_ENTRIES]
    included = {slug for slug, _ in selected}
    linked: list[tuple[str, Path, str]] = []
    for _, (_, text, _) in selected:
        for slug in LINK.findall(text):
            path = memory / "entries" / f"{slug}.md"
            if slug not in included and path.is_file() and not path.is_symlink():
                linked.append((slug, path, path.read_text(encoding="utf-8")))
                included.add(slug)
                if len(linked) >= MAX_LINKED_ENTRIES:
                    break
        if len(linked) >= MAX_LINKED_ENTRIES:
            break

    for slug, (path, text, _) in selected:
        documents.append(_document(f"memory/entries/{path.name}", text, "query-match"))
    for slug, path, text in linked:
        documents.append(_document(f"memory/entries/{path.name}", text, "linked-neighbour"))

    # Preserve the control documents. If a pathological entry breaches the cap, omit complete
    # lowest-priority entry documents rather than slicing Markdown into ambiguous fragments.
    while len(json.dumps(documents, ensure_ascii=False)) > MAX_PACKET_CHARS and len(documents) > 3:
        documents.pop()
    return {
        "schema_version": 1,
        "query_sha256": _sha256(query),
        "selection": {
            "algorithm": "lexical-overlap+dated-reminder+one-hop-v1",
            "primary_limit": MAX_PRIMARY_ENTRIES,
            "linked_limit": MAX_LINKED_ENTRIES,
            "packet_char_limit": MAX_PACKET_CHARS,
        },
        "documents": documents,
    }
