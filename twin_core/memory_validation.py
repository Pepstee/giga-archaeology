"""Deterministic validation for GIGA's Markdown memory store."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ENTRY_LINK = re.compile(r"\[\[([^\]]+)\]\]")
INDEX_LINK = re.compile(r"\(entries/([^)]+)\.md\)")
DATED_SLUG = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")
REQUIRED_FIELDS = {"type", "tags", "created", "status"}
ALLOWED_TYPES = {"idea", "decision", "fact", "reminder", "question"}
SENSITIVE_PATTERNS = {
    "booking reference": re.compile(r"\b(?:PNR|ticket number|booking reference)\b", re.I),
    "date of birth": re.compile(r"\b(?:DOB|date of birth)\b", re.I),
    "credential": re.compile(r"\b(?:api[_ -]?key|password|private key|bot token)\b", re.I),
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str


def _frontmatter(text: str) -> tuple[dict[str, str], str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values, text[end + 5 :]


def validate_memory(root: Path) -> dict[str, object]:
    root = root.resolve()
    entries_dir = root / "entries"
    index_path = root / "INDEX.md"
    findings: list[Finding] = []
    entries: dict[str, tuple[Path, dict[str, str], str]] = {}

    for path in sorted(entries_dir.glob("*.md")):
        parsed = _frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        if parsed is None:
            findings.append(Finding("error", "frontmatter", str(path), "missing or malformed frontmatter"))
            continue
        fields, body = parsed
        missing = sorted(REQUIRED_FIELDS - fields.keys())
        if missing:
            findings.append(Finding("error", "required-field", str(path), f"missing fields: {', '.join(missing)}"))
        if fields.get("type") not in ALLOWED_TYPES:
            findings.append(Finding("error", "entry-type", str(path), f"invalid type: {fields.get('type')!r}"))
        if fields.get("type") == "reminder" and "trigger" not in fields:
            findings.append(Finding("error", "reminder-trigger", str(path), "reminder has no trigger"))
        slug = path.stem
        if slug in entries:
            findings.append(Finding("error", "duplicate-slug", str(path), f"duplicate slug {slug}"))
        entries[slug] = (path, fields, body)

    if not index_path.exists():
        findings.append(Finding("error", "index-missing", str(index_path), "memory index does not exist"))
        indexed: set[str] = set()
        index_text = ""
    else:
        index_text = index_path.read_text(encoding="utf-8", errors="replace")
        indexed = {Path(value).stem for value in INDEX_LINK.findall(index_text)}
        for slug in sorted(entries.keys() - indexed):
            findings.append(Finding("error", "index-coverage", str(index_path), f"entry missing from index: {slug}"))
        for slug in sorted(indexed - entries.keys()):
            findings.append(Finding("error", "index-orphan", str(index_path), f"index references missing entry: {slug}"))
        for label, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(index_text):
                findings.append(Finding("warning", "hot-index-sensitive", str(index_path), f"always-loaded index mentions {label}"))

    for slug, (path, fields, body) in entries.items():
        targets = ENTRY_LINK.findall(body + "\n" + fields.get("status", ""))
        for target in targets:
            if DATED_SLUG.fullmatch(target) and target not in entries:
                findings.append(Finding("error", "broken-entry-link", str(path), f"missing linked entry: {target}"))
        status = fields.get("status", "")
        if status.startswith("superseded-by"):
            match = ENTRY_LINK.search(status)
            if match is None or match.group(1) not in entries:
                findings.append(Finding("error", "supersession", str(path), "supersession target is missing"))
        if fields.get("type") in {"fact", "decision"} and not re.search(r"(?im)^Source:", body):
            findings.append(Finding("warning", "provenance", str(path), "fact/decision has no explicit Source: line"))
        if "auto-ingest" in fields.get("tags", "") and "unreviewed" not in fields.get("tags", ""):
            findings.append(Finding("error", "auto-review", str(path), "auto-ingested entry is not marked unreviewed"))

    counts = {"error": 0, "warning": 0, "info": 0}
    for item in findings:
        counts[item.severity] = counts.get(item.severity, 0) + 1
    return {
        "entries": len(entries),
        "indexed_entries": len(indexed),
        "counts": counts,
        "ok": counts["error"] == 0,
        "findings": [asdict(item) for item in findings],
    }


def render_report(result: dict[str, object]) -> str:
    counts = result["counts"]
    assert isinstance(counts, dict)
    lines = [
        f"memory: {result['entries']} entries; {counts['error']} errors; {counts['warning']} warnings"
    ]
    for finding in result["findings"]:
        assert isinstance(finding, dict)
        lines.append(
            f"{str(finding['severity']).upper()} {finding['code']} {finding['path']}: {finding['message']}"
        )
    return "\n".join(lines)

