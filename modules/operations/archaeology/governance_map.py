"""Strict, metadata-bounded adapters for governed documents and evidence receipts."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from .evidence import EvidenceError, canonical_bytes, sha256_bytes, validate_self_hash


GOVERNANCE_POLICY_VERSION = "giga.archaeologist.governance-map-policy.v4"
MAX_GOVERNED_DOCUMENT_BYTES = 4 * 1024 * 1024
MAX_GOVERNED_HEADINGS = 2_000
MAX_GOVERNED_HEADING_CHARACTERS = 512
MAX_GOVERNED_PATH_REFERENCES = 5_000
MAX_GOVERNED_PATH_CHARACTERS = 1_024
MAX_GOVERNED_JSON_PATH_REFERENCES = 10_000
HASH = re.compile(r"[0-9a-f]{64}")
EXPLICIT_DECLARATION = re.compile(
    r"^(#{1,6})[ \t]+((?:ADR|JSR|WO|REQ|LAW|DECISION|R|L)-[A-Za-z0-9._-]+)(?:[ \t]+(.+))?$"
)
ATX_HEADING = re.compile(r"^[ ]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*$")
FENCE_START = re.compile(r"^[ ]{0,3}(`{3,}|~{3,}).*$")
INLINE_CODE = re.compile(r"(?<!`)`([^`\r\n]+)`(?!`)")
MARKDOWN_LINK_DESTINATION = re.compile(r"!?\[[^\]\r\n]*\]\(([^()\s]+)\)")
SAFE_PATH = re.compile(r"[A-Za-z0-9_@+.-]+(?:/[A-Za-z0-9_@+.-]+)*")
ROOT_PATH_SUFFIXES = frozenset(
    {
        ".css",
        ".html",
        ".js",
        ".json",
        ".jsx",
        ".lock",
        ".md",
        ".py",
        ".sh",
        ".sql",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".yaml",
        ".yml",
    }
)
SAFE_PREFIXES = (
    "architecture/",
    "contracts/",
    "programme/",
    "receipts/",
    "work_orders/",
)
GOVERNANCE_POLICY: Mapping[str, Any] = {
    "authority_granted": False,
    "document_prefixes": list(SAFE_PREFIXES),
    "evidence_filename_is_proof": False,
    "explicit_identifier_required_for_declaration": True,
    "hash_links": "exact-64-lowercase-hex-only",
    "markdown_headings": "atx-outside-fenced-code-exact-line-only",
    "max_governed_heading_characters": MAX_GOVERNED_HEADING_CHARACTERS,
    "max_governed_headings": MAX_GOVERNED_HEADINGS,
    "markdown_path_references": "inline-code-or-link-destination-outside-fenced-code",
    "json_path_references": "exact-path-or-suffixed-path-field-values",
    "max_governed_json_path_references": MAX_GOVERNED_JSON_PATH_REFERENCES,
    "max_governed_path_characters": MAX_GOVERNED_PATH_CHARACTERS,
    "max_governed_path_references": MAX_GOVERNED_PATH_REFERENCES,
    "max_document_bytes": MAX_GOVERNED_DOCUMENT_BYTES,
    "prose_similarity_links": False,
    "status_is_document_claim_not_verified_outcome": True,
}
GOVERNANCE_POLICY_SHA256 = sha256_bytes(canonical_bytes(GOVERNANCE_POLICY))


class GovernanceMapError(ValueError):
    """A governed document cannot be projected under the closed policy."""


def strict_json_object(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_GOVERNED_DOCUMENT_BYTES:
        raise GovernanceMapError("governed JSON exceeds the byte ceiling")

    def pairs(items: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise GovernanceMapError(f"duplicate governed JSON key: {key}")
            value[key] = item
        return value

    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GovernanceMapError("governed document is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise GovernanceMapError("governed JSON root must be an object")
    return value


def governed_document_kind(path: str, value: Mapping[str, Any]) -> str:
    schema = str(value.get("schema", "")).casefold()
    lower = path.casefold()
    if lower.startswith("contracts/") or "schema" in schema:
        return "CONTRACT"
    if lower.startswith("work_orders/") or "work-order" in schema:
        return "WORK_ORDER"
    if lower.startswith("receipts/") or any(
        marker in schema
        for marker in ("receipt", "attestation", "completion", "preflight", "milestone")
    ):
        return "EVIDENCE_DOCUMENT"
    if "decision" in lower or "decision" in schema:
        return "DECISION_DOCUMENT"
    if any(
        marker in lower or marker in schema
        for marker in ("law", "policy", "requirement")
    ):
        return "REQUIREMENT_POLICY_DOCUMENT"
    return "GOVERNED_DOCUMENT"


def self_hash_state(value: Mapping[str, Any]) -> str:
    if "receipt_sha256" not in value:
        return "NOT_DECLARED"
    try:
        validate_self_hash(value)
    except EvidenceError:
        return "INVALID"
    return "VALID"


def exact_hash_links(value: Mapping[str, Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []

    def visit(item: Any, path: tuple[str, ...]) -> None:
        if isinstance(item, Mapping):
            for key in sorted(item):
                child = item[key]
                child_path = (*path, str(key))
                if (
                    isinstance(child, str)
                    and str(key).casefold().endswith("sha256")
                    and HASH.fullmatch(child)
                ):
                    links.append({"field": ".".join(child_path), "sha256": child})
                visit(child, child_path)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, (*path, str(index)))

    visit(value, ())
    return links


def exact_json_path_references(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Extract safe repository-relative values from explicit JSON path fields."""

    references: list[dict[str, Any]] = []

    def pointer(parts: tuple[str, ...]) -> str:
        return "/" + "/".join(
            part.replace("~", "~0").replace("/", "~1") for part in parts
        )

    def path_field(key: str) -> bool:
        normalized = key.casefold()
        return normalized == "path" or normalized.endswith(("_path", "_paths"))

    def admit(literal: str, parts: tuple[str, ...], field: str) -> None:
        if len(literal) > MAX_GOVERNED_PATH_CHARACTERS:
            raise GovernanceMapError("governed JSON path reference exceeds the ceiling")
        target = literal[2:] if literal.startswith("./") else literal
        target, separator, fragment = target.partition("#")
        if (
            not target
            or target.startswith(("/", "~"))
            or "://" in target
            or "\\" in target
            or "?" in target
            or SAFE_PATH.fullmatch(target) is None
            or any(part in {"", ".", ".."} for part in target.split("/"))
            or (
                "/" not in target
                and not any(
                    target.casefold().endswith(suffix) for suffix in ROOT_PATH_SUFFIXES
                )
            )
        ):
            return
        if len(references) >= MAX_GOVERNED_JSON_PATH_REFERENCES:
            raise GovernanceMapError(
                "governed JSON path reference count exceeds the ceiling"
            )
        references.append(
            {
                "field": field,
                "fragment": fragment if separator else "",
                "json_pointer": pointer(parts),
                "literal": literal,
                "normalized_path": target,
                "ordinal": len(references),
                "syntax": "JSON_PATH_FIELD",
            }
        )

    def visit(item: Any, parts: tuple[str, ...]) -> None:
        if isinstance(item, Mapping):
            for key in sorted(item):
                child = item[key]
                child_parts = (*parts, str(key))
                if path_field(str(key)):
                    if isinstance(child, str):
                        admit(child, child_parts, str(key))
                    elif isinstance(child, list):
                        for index, member in enumerate(child):
                            if isinstance(member, str):
                                admit(
                                    member,
                                    (*child_parts, str(index)),
                                    str(key),
                                )
                visit(child, child_parts)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, (*parts, str(index)))

    visit(value, ())
    return references


def explicit_markdown_declarations(raw: bytes) -> list[dict[str, Any]]:
    if len(raw) > MAX_GOVERNED_DOCUMENT_BYTES:
        raise GovernanceMapError("governed Markdown exceeds the byte ceiling")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise GovernanceMapError("governed Markdown is not strict UTF-8") from exc
    declarations = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = EXPLICIT_DECLARATION.fullmatch(line)
        if match is None:
            continue
        identifier = match.group(2)
        declarations.append(
            {
                "id": identifier,
                "kind": identifier.split("-", 1)[0],
                "heading_level": len(match.group(1)),
                "title": match.group(3) or "",
                "line": line_number,
            }
        )
    return declarations


def governed_markdown_headings(raw: bytes) -> list[dict[str, Any]]:
    """Extract bounded ATX headings and hierarchy without parsing prose bodies."""

    if len(raw) > MAX_GOVERNED_DOCUMENT_BYTES:
        raise GovernanceMapError("governed Markdown exceeds the byte ceiling")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise GovernanceMapError("governed Markdown is not strict UTF-8") from exc

    headings: list[dict[str, Any]] = []
    hierarchy: list[tuple[int, int]] = []
    fence_character: str | None = None
    fence_length = 0
    byte_offset = 0
    for line_number, line_with_ending in enumerate(
        text.splitlines(keepends=True), start=1
    ):
        line = line_with_ending.rstrip("\r\n")
        line_bytes = line.encode("utf-8")
        if fence_character is not None:
            if re.fullmatch(
                rf"[ ]{{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
                line,
            ):
                fence_character = None
                fence_length = 0
            byte_offset += len(line_with_ending.encode("utf-8"))
            continue
        fence = FENCE_START.fullmatch(line)
        if fence is not None:
            fence_character = fence.group(1)[0]
            fence_length = len(fence.group(1))
            byte_offset += len(line_with_ending.encode("utf-8"))
            continue
        match = ATX_HEADING.fullmatch(line)
        if match is not None:
            title = re.sub(r"[ \t]+#+[ \t]*$", "", match.group(2)).strip()
            if not title:
                byte_offset += len(line_with_ending.encode("utf-8"))
                continue
            if len(title) > MAX_GOVERNED_HEADING_CHARACTERS:
                raise GovernanceMapError(
                    "governed Markdown heading exceeds the ceiling"
                )
            if len(headings) >= MAX_GOVERNED_HEADINGS:
                raise GovernanceMapError(
                    "governed Markdown heading count exceeds the ceiling"
                )
            level = len(match.group(1))
            while hierarchy and hierarchy[-1][0] >= level:
                hierarchy.pop()
            parent_ordinal = hierarchy[-1][1] if hierarchy else None
            ordinal = len(headings)
            headings.append(
                {
                    "heading_level": level,
                    "line": line_number,
                    "ordinal": ordinal,
                    "parent_ordinal": parent_ordinal,
                    "span": {
                        "byte_start": byte_offset,
                        "byte_end": byte_offset + len(line_bytes),
                        "line_start": line_number,
                        "line_end": line_number,
                        "column_start": 1,
                        "column_end": len(line) + 1,
                    },
                    "title": title,
                }
            )
            hierarchy.append((level, ordinal))
        byte_offset += len(line_with_ending.encode("utf-8"))
    return headings


def explicit_markdown_path_references(raw: bytes) -> list[dict[str, Any]]:
    """Extract explicit local path literals without interpreting surrounding prose."""

    if len(raw) > MAX_GOVERNED_DOCUMENT_BYTES:
        raise GovernanceMapError("governed Markdown exceeds the byte ceiling")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise GovernanceMapError("governed Markdown is not strict UTF-8") from exc

    references: list[dict[str, Any]] = []
    fence_character: str | None = None
    fence_length = 0
    byte_offset = 0
    patterns = (
        ("INLINE_CODE", INLINE_CODE),
        ("MARKDOWN_LINK_DESTINATION", MARKDOWN_LINK_DESTINATION),
    )
    for line_number, line_with_ending in enumerate(
        text.splitlines(keepends=True), start=1
    ):
        line = line_with_ending.rstrip("\r\n")
        if fence_character is not None:
            if re.fullmatch(
                rf"[ ]{{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
                line,
            ):
                fence_character = None
                fence_length = 0
            byte_offset += len(line_with_ending.encode("utf-8"))
            continue
        fence = FENCE_START.fullmatch(line)
        if fence is not None:
            fence_character = fence.group(1)[0]
            fence_length = len(fence.group(1))
            byte_offset += len(line_with_ending.encode("utf-8"))
            continue

        matches = []
        for syntax, pattern in patterns:
            for match in pattern.finditer(line):
                matches.append((match.start(1), match.end(1), syntax, match.group(1)))
        for start, end, syntax, literal in sorted(matches):
            if len(literal) > MAX_GOVERNED_PATH_CHARACTERS:
                raise GovernanceMapError(
                    "governed Markdown path reference exceeds the ceiling"
                )
            target = literal[2:] if literal.startswith("./") else literal
            target, separator, fragment = target.partition("#")
            if (
                not target
                or target.startswith(("/", "~"))
                or "://" in target
                or "\\" in target
                or "?" in target
                or SAFE_PATH.fullmatch(target) is None
                or any(part in {"", ".", ".."} for part in target.split("/"))
                or (
                    "/" not in target
                    and not any(
                        target.casefold().endswith(suffix)
                        for suffix in ROOT_PATH_SUFFIXES
                    )
                )
            ):
                continue
            if len(references) >= MAX_GOVERNED_PATH_REFERENCES:
                raise GovernanceMapError(
                    "governed Markdown path reference count exceeds the ceiling"
                )
            byte_start = byte_offset + len(line[:start].encode("utf-8"))
            byte_end = byte_offset + len(line[:end].encode("utf-8"))
            references.append(
                {
                    "fragment": fragment if separator else "",
                    "line": line_number,
                    "literal": literal,
                    "normalized_path": target,
                    "ordinal": len(references),
                    "span": {
                        "byte_start": byte_start,
                        "byte_end": byte_end,
                        "line_start": line_number,
                        "line_end": line_number,
                        "column_start": start + 1,
                        "column_end": end + 1,
                    },
                    "syntax": syntax,
                }
            )
        byte_offset += len(line_with_ending.encode("utf-8"))
    return references
