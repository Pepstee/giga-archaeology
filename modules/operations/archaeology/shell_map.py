"""Deterministic Bash fact extraction backed by the maintained tree-sitter grammar.

This module is deliberately an extractor, not a second mapper.  It converts one
inventory-bound Bash artifact into syntax facts that the canonical mapper stores
in its shared evidence graph.  It never executes or sources the script.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib import metadata
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


class ShellMapError(ValueError):
    """Bash facts cannot be extracted with the declared deterministic backend."""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def shell_backend_identity() -> Mapping[str, Any]:
    """Return the exact installed parser identity used by this process."""

    try:
        import tree_sitter_bash
        from tree_sitter import Language, Parser

        tree_sitter_version = metadata.version("tree-sitter")
        grammar_version = metadata.version("tree-sitter-bash")
    except (ImportError, metadata.PackageNotFoundError) as exc:
        raise ShellMapError("tree-sitter Bash backend is unavailable") from exc
    grammar_root = Path(tree_sitter_bash.__file__).resolve().parent
    bindings = sorted(grammar_root.glob("_binding*"))
    if len(bindings) != 1 or not bindings[0].is_file():
        raise ShellMapError("tree-sitter Bash binding identity is ambiguous")
    try:
        Parser(Language(tree_sitter_bash.language()))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ShellMapError("tree-sitter Bash backend cannot initialize") from exc
    return {
        "backend": "tree-sitter-bash",
        "tree_sitter_version": tree_sitter_version,
        "grammar_version": grammar_version,
        "binding_name": bindings[0].name,
        "binding_sha256": _file_sha256(bindings[0]),
    }


@lru_cache(maxsize=1)
def _parser() -> Any:
    try:
        import tree_sitter_bash
        from tree_sitter import Language, Parser

        return Parser(Language(tree_sitter_bash.language()))
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        raise ShellMapError("tree-sitter Bash backend cannot initialize") from exc


def _span(node: Any) -> dict[str, int]:
    return {
        "byte_start": int(node.start_byte),
        "byte_end": int(node.end_byte),
        "line_start": int(node.start_point.row) + 1,
        "column_start": int(node.start_point.column),
        "line_end": int(node.end_point.row) + 1,
        "column_end": int(node.end_point.column),
    }


def _text(content: bytes, node: Any) -> str:
    try:
        return content[node.start_byte : node.end_byte].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ShellMapError("Bash syntax contains non-UTF-8 text") from exc


def _walk(root: Any) -> tuple[Any, ...]:
    ordered: list[Any] = []
    stack = [root]
    while stack:
        node = stack.pop()
        ordered.append(node)
        stack.extend(reversed(node.named_children))
    return tuple(ordered)


def _function_ancestor(node: Any, content: bytes) -> str | None:
    current = node.parent
    while current is not None:
        if current.type == "function_definition":
            name = current.child_by_field_name("name")
            return _text(content, name) if name is not None else None
        current = current.parent
    return None


def _literal_argument(content: bytes, node: Any) -> str | None:
    if node.type not in {"word", "string", "raw_string"}:
        return None
    value = _text(content, node)
    if node.type in {"string", "raw_string"} and len(value) >= 2:
        value = value[1:-1]
    if not value or any(marker in value for marker in ("$", "`", "*", "?", "[")):
        return None
    return value


def _script_dependencies(content: bytes, command: Any, name: str) -> list[str]:
    literals = [
        value
        for child in command.named_children
        if child != command.child_by_field_name("name")
        if (value := _literal_argument(content, child)) is not None
    ]
    candidates: list[str] = []
    if name in {".", "source", "bash", "sh", "zsh", "python", "python3"}:
        candidates.extend(literals)
    if "/" in name:
        candidates.append(name)
    return sorted(
        {
            value
            for value in candidates
            if PurePosixPath(value).suffix in {".bash", ".py", ".sh", ".zsh"}
        }
    )


def extract_shell_file_fragment(path: str, content: bytes) -> Mapping[str, Any]:
    """Parse one Bash file into exact, non-executing syntax facts."""

    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ShellMapError(f"Bash source is not UTF-8: {path}") from exc
    tree = _parser().parse(content)
    root = tree.root_node
    if root.has_error:
        raise ShellMapError(f"tree-sitter Bash parse failed: {path}")
    nodes = _walk(root)
    functions: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []

    for node in nodes:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node is None:
                raise ShellMapError(f"Bash function has no name: {path}")
            functions.append({"name": _text(content, name_node), "span": _span(node)})
        elif node.type == "variable_assignment":
            name_node = node.child_by_field_name("name")
            if name_node is None:
                raise ShellMapError(f"Bash assignment has no name: {path}")
            parent = node.parent
            assignments.append(
                {
                    "name": _text(content, name_node),
                    "scope": _function_ancestor(node, content) or "SCRIPT",
                    "assignment_kind": (
                        "COMMAND_ENVIRONMENT"
                        if parent is not None and parent.type == "command"
                        else "SHELL_ASSIGNMENT"
                    ),
                    "span": _span(node),
                }
            )
        elif node.type == "variable_name":
            parent = node.parent
            if (
                parent is not None
                and parent.type == "variable_assignment"
                and parent.child_by_field_name("name") == node
            ):
                continue
            references.append(
                {
                    "name": _text(content, node),
                    "scope": _function_ancestor(node, content) or "SCRIPT",
                    "span": _span(node),
                }
            )
        elif node.type == "command":
            name_node = node.child_by_field_name("name")
            if name_node is None:
                continue
            name = _text(content, name_node)
            commands.append(
                {
                    "name": name,
                    "dynamic": any(marker in name for marker in ("$", "`")),
                    "scope": _function_ancestor(node, content) or "SCRIPT",
                    "script_dependencies": _script_dependencies(content, node, name),
                    "span": _span(node),
                }
            )

    first_line = content.splitlines()[0].decode("utf-8") if content else ""
    return {
        "path": path,
        "language": "bash",
        "shebang": first_line if first_line.startswith("#!") else None,
        "tree_root_type": root.type,
        "tree_descendant_count": int(root.descendant_count),
        "functions": sorted(
            functions, key=lambda item: (item["span"]["byte_start"], item["name"])
        ),
        "assignments": sorted(
            assignments, key=lambda item: (item["span"]["byte_start"], item["name"])
        ),
        "references": sorted(
            references, key=lambda item: (item["span"]["byte_start"], item["name"])
        ),
        "commands": sorted(
            commands, key=lambda item: (item["span"]["byte_start"], item["name"])
        ),
    }
