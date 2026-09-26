"""Deterministic JavaScript/TypeScript syntax extraction for the canonical mapper.

The language grammar is a distinct parser lifecycle, so it has a separate extractor
module.  It is not a second mapper: it reads one already-admitted inventory artifact,
never executes source, and returns closed syntax facts for the shared evidence graph.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib import metadata
from pathlib import Path
from typing import Any, Mapping


JAVASCRIPT_SUFFIXES = frozenset({".cjs", ".js", ".jsx", ".mjs", ".ts", ".tsx"})


class JavaScriptMapError(ValueError):
    """JavaScript facts cannot be extracted with the declared backend."""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _binding_identity(module: Any, package: str) -> Mapping[str, str]:
    root = Path(module.__file__).resolve().parent
    bindings = sorted(root.glob("_binding*"))
    if len(bindings) != 1 or not bindings[0].is_file():
        raise JavaScriptMapError(f"{package} binding identity is ambiguous")
    return {
        "binding_name": bindings[0].name,
        "binding_sha256": _file_sha256(bindings[0]),
        "grammar_version": metadata.version(package),
    }


@lru_cache(maxsize=1)
def javascript_backend_identity() -> Mapping[str, Any]:
    """Return exact parser and grammar identities used by this process."""

    try:
        import tree_sitter_javascript
        import tree_sitter_typescript
        from tree_sitter import Language, Parser

        javascript = _binding_identity(tree_sitter_javascript, "tree-sitter-javascript")
        typescript = _binding_identity(tree_sitter_typescript, "tree-sitter-typescript")
        Parser(Language(tree_sitter_javascript.language()))
        Parser(Language(tree_sitter_typescript.language_typescript()))
        Parser(Language(tree_sitter_typescript.language_tsx()))
    except (ImportError, metadata.PackageNotFoundError) as exc:
        raise JavaScriptMapError(
            "tree-sitter JavaScript/TypeScript backend is unavailable"
        ) from exc
    except (AttributeError, TypeError, ValueError) as exc:
        raise JavaScriptMapError(
            "tree-sitter JavaScript/TypeScript backend cannot initialize"
        ) from exc
    return {
        "backend": "tree-sitter-javascript-typescript",
        "tree_sitter_version": metadata.version("tree-sitter"),
        "javascript": javascript,
        "typescript": typescript,
    }


@lru_cache(maxsize=3)
def _parser(language: str) -> Any:
    try:
        import tree_sitter_javascript
        import tree_sitter_typescript
        from tree_sitter import Language, Parser

        if language == "javascript":
            binding = tree_sitter_javascript.language()
        elif language == "typescript":
            binding = tree_sitter_typescript.language_typescript()
        elif language == "tsx":
            binding = tree_sitter_typescript.language_tsx()
        else:
            raise JavaScriptMapError(f"unsupported JavaScript language: {language}")
        return Parser(Language(binding))
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        raise JavaScriptMapError(
            "tree-sitter JavaScript/TypeScript backend cannot initialize"
        ) from exc


def _language(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".tsx":
        return "tsx"
    if suffix == ".ts":
        return "typescript"
    if suffix in JAVASCRIPT_SUFFIXES:
        return "javascript"
    raise JavaScriptMapError(f"unsupported JavaScript suffix: {path}")


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
        raise JavaScriptMapError("JavaScript syntax contains non-UTF-8 text") from exc


def _walk(root: Any) -> tuple[Any, ...]:
    ordered: list[Any] = []
    stack = [root]
    while stack:
        node = stack.pop()
        ordered.append(node)
        stack.extend(reversed(node.named_children))
    return tuple(ordered)


def _ancestor(node: Any, node_type: str) -> Any | None:
    current = node.parent
    while current is not None:
        if current.type == node_type:
            return current
        current = current.parent
    return None


def _scope(node: Any, content: bytes) -> str:
    current = node.parent
    while current is not None:
        if current.type == "method_definition":
            name = current.child_by_field_name("name")
            owner = _ancestor(current, "class_declaration")
            owner_name = (
                owner.child_by_field_name("name") if owner is not None else None
            )
            if name is not None:
                prefix = (
                    _text(content, owner_name) if owner_name is not None else "CLASS"
                )
                return f"{prefix}.{_text(content, name)}"
        if current.type == "function_declaration":
            name = current.child_by_field_name("name")
            if name is not None:
                return _text(content, name)
        if current.type == "variable_declarator":
            value = current.child_by_field_name("value")
            if value is not None and value.type in {
                "arrow_function",
                "function_expression",
            }:
                name = current.child_by_field_name("name")
                if name is not None:
                    return _text(content, name)
        current = current.parent
    return "MODULE"


def _string_literal(content: bytes, node: Any | None) -> str | None:
    if node is None or node.type != "string":
        return None
    value = _text(content, node)
    if len(value) < 2 or value[0] not in {"'", '"'} or value[-1] != value[0]:
        return None
    return value[1:-1]


def _import_bindings(content: bytes, node: Any) -> list[dict[str, str]]:
    clause = next(
        (child for child in node.named_children if child.type == "import_clause"),
        None,
    )
    if clause is None:
        return []
    bindings: list[dict[str, str]] = []
    for child in _walk(clause):
        if child.type == "import_specifier":
            imported = child.child_by_field_name("name")
            alias = child.child_by_field_name("alias")
            if imported is not None:
                bindings.append(
                    {
                        "imported_name": _text(content, imported),
                        "local_name": _text(content, alias or imported),
                    }
                )
        elif child.type == "namespace_import":
            identifier = next(
                (item for item in child.named_children if item.type == "identifier"),
                None,
            )
            if identifier is not None:
                bindings.append(
                    {
                        "imported_name": "*",
                        "local_name": _text(content, identifier),
                    }
                )
    direct = [child for child in clause.named_children if child.type == "identifier"]
    for identifier in direct:
        bindings.append(
            {
                "imported_name": "default",
                "local_name": _text(content, identifier),
            }
        )
    return sorted(
        {
            (item["local_name"], item["imported_name"]): item for item in bindings
        }.values(),
        key=lambda item: (item["local_name"], item["imported_name"]),
    )


def _member_parts(content: bytes, node: Any | None) -> tuple[str, ...] | None:
    if node is None:
        return None
    if node.type == "identifier":
        return (_text(content, node),)
    if node.type != "member_expression":
        return None
    object_node = node.child_by_field_name("object")
    property_node = node.child_by_field_name("property")
    prefix = _member_parts(content, object_node)
    if (
        prefix is None
        or property_node is None
        or property_node.type not in {"identifier", "property_identifier"}
    ):
        return None
    return (*prefix, _text(content, property_node))


def _call_expression(
    content: bytes, node: Any
) -> tuple[str, str | None, str | None, str | None]:
    function = node.child_by_field_name("function")
    if function is None:
        return "", None, None, None
    expression = _text(content, function)
    direct = _text(content, function) if function.type == "identifier" else None
    parts = _member_parts(content, function)
    if parts is not None and len(parts) == 2:
        return expression, direct, parts[0], parts[1]
    return expression, direct, None, None


def _require_specifier(content: bytes, node: Any | None) -> str | None:
    if node is None or node.type != "call_expression":
        return None
    function = node.child_by_field_name("function")
    arguments = node.child_by_field_name("arguments")
    if (
        function is None
        or function.type != "identifier"
        or _text(content, function) != "require"
        or arguments is None
        or len(arguments.named_children) != 1
    ):
        return None
    return _string_literal(content, arguments.named_children[0])


def _commonjs_import(
    content: bytes, node: Any
) -> tuple[dict[str, Any], tuple[int, int]] | None:
    """Return one conservative module-scope CommonJS binding declaration."""

    declaration = node.parent
    if (
        node.type != "variable_declarator"
        or _scope(node, content) != "MODULE"
        or declaration is None
        or declaration.type not in {"lexical_declaration", "variable_declaration"}
        or declaration.parent is None
        or declaration.parent.type != "program"
    ):
        return None
    name = node.child_by_field_name("name")
    value = node.child_by_field_name("value")
    if name is None or value is None:
        return None
    require_call = value
    imported_name = "*"
    if value.type == "member_expression":
        object_node = value.child_by_field_name("object")
        property_node = value.child_by_field_name("property")
        if (
            object_node is None
            or property_node is None
            or property_node.type != "property_identifier"
        ):
            return None
        require_call = object_node
        imported_name = _text(content, property_node)
    specifier = _require_specifier(content, require_call)
    if specifier is None:
        return None

    bindings: list[dict[str, str]] = []
    if name.type == "identifier":
        bindings.append(
            {
                "imported_name": imported_name,
                "local_name": _text(content, name),
            }
        )
    elif name.type == "object_pattern" and imported_name == "*":
        for child in name.named_children:
            if child.type == "pair_pattern":
                key = child.child_by_field_name("key")
                target = child.child_by_field_name("value")
                if (
                    key is None
                    or target is None
                    or key.type not in {"identifier", "property_identifier"}
                    or target.type != "identifier"
                ):
                    return None
                bindings.append(
                    {
                        "imported_name": _text(content, key),
                        "local_name": _text(content, target),
                    }
                )
            elif child.type == "shorthand_property_identifier_pattern":
                value_name = _text(content, child)
                bindings.append({"imported_name": value_name, "local_name": value_name})
            else:
                return None
    else:
        return None
    return (
        {
            "bindings": sorted(
                bindings,
                key=lambda item: (item["local_name"], item["imported_name"]),
            ),
            "specifier": specifier,
            "span": _span(node),
            "syntax": "COMMONJS_REQUIRE",
        },
        (int(require_call.start_byte), int(require_call.end_byte)),
    )


def _direct_export_name(node: Any) -> str | None:
    statement = _ancestor(node, "export_statement")
    if statement is None:
        return None
    if any(child.type == "default" for child in statement.children):
        return "default"
    return "DECLARED_NAME"


def _explicit_exports(content: bytes, nodes: tuple[Any, ...]) -> list[dict[str, Any]]:
    exports: list[dict[str, Any]] = []
    for node in nodes:
        if node.type != "export_specifier":
            continue
        statement = _ancestor(node, "export_statement")
        if statement is None or statement.child_by_field_name("source") is not None:
            continue
        name = node.child_by_field_name("name")
        alias = node.child_by_field_name("alias")
        if name is not None:
            exports.append(
                {
                    "exported_name": _text(content, alias or name),
                    "local_name": _text(content, name),
                    "span": _span(node),
                    "syntax": "ESM",
                }
            )
    return exports


def _commonjs_exports(content: bytes, nodes: tuple[Any, ...]) -> list[dict[str, Any]]:
    assignments: list[Any] = []
    for node in nodes:
        if (
            node.type != "assignment_expression"
            or node.parent is None
            or node.parent.type != "expression_statement"
            or node.parent.parent is None
            or node.parent.parent.type != "program"
        ):
            continue
        parts = _member_parts(content, node.child_by_field_name("left"))
        if parts == ("module", "exports") or (
            parts is not None
            and (
                (len(parts) == 2 and parts[0] == "exports")
                or (len(parts) == 3 and parts[:2] == ("module", "exports"))
            )
        ):
            assignments.append(node)
    whole_assignments = [
        node
        for node in assignments
        if _member_parts(content, node.child_by_field_name("left"))
        == ("module", "exports")
    ]
    # Mixed whole-object and property mutation has order/alias semantics that are
    # not safe to collapse into a static export table. Preserve it as unresolved.
    if whole_assignments and len(assignments) != 1:
        return []

    exports: list[dict[str, Any]] = []
    for node in assignments:
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        parts = _member_parts(content, left)
        if parts is None or right is None:
            continue
        if parts == ("module", "exports"):
            if right.type == "identifier":
                exports.append(
                    {
                        "exported_name": "default",
                        "local_name": _text(content, right),
                        "span": _span(node),
                        "syntax": "COMMONJS_EXPORT",
                    }
                )
            elif right.type == "object":
                for child in right.named_children:
                    if child.type == "shorthand_property_identifier":
                        value_name = _text(content, child)
                        exports.append(
                            {
                                "exported_name": value_name,
                                "local_name": value_name,
                                "span": _span(child),
                                "syntax": "COMMONJS_EXPORT",
                            }
                        )
                    elif child.type == "pair":
                        key = child.child_by_field_name("key")
                        value = child.child_by_field_name("value")
                        if (
                            key is not None
                            and value is not None
                            and key.type in {"identifier", "property_identifier"}
                            and value.type == "identifier"
                        ):
                            exports.append(
                                {
                                    "exported_name": _text(content, key),
                                    "local_name": _text(content, value),
                                    "span": _span(child),
                                    "syntax": "COMMONJS_EXPORT",
                                }
                            )
            continue
        exported_name: str | None = None
        if len(parts) == 2 and parts[0] == "exports":
            exported_name = parts[1]
        elif len(parts) == 3 and parts[:2] == ("module", "exports"):
            exported_name = parts[2]
        if exported_name is not None and right.type == "identifier":
            exports.append(
                {
                    "exported_name": exported_name,
                    "local_name": _text(content, right),
                    "span": _span(node),
                    "syntax": "COMMONJS_EXPORT",
                }
            )
    return exports


def _parameter_names(content: bytes, parameters: Any | None) -> set[str]:
    if parameters is None:
        return set()
    names: set[str] = set()
    parameter_nodes = (
        (parameters,)
        if parameters.type == "identifier"
        else tuple(parameters.named_children)
    )
    for parameter in parameter_nodes:
        target = parameter
        if parameter.type in {
            "assignment_pattern",
            "required_parameter",
            "optional_parameter",
        }:
            target = (
                parameter.child_by_field_name("left")
                or parameter.child_by_field_name("pattern")
                or parameter.named_children[0]
            )
        if target.type == "rest_pattern" and target.named_children:
            target = target.named_children[0]
        if target.type == "identifier":
            names.add(_text(content, target))
        elif target.type in {"array_pattern", "object_pattern"}:
            names.update(
                _text(content, item)
                for item in _walk(target)
                if item.type == "identifier"
            )
    return names


def _is_definition_identifier(node: Any) -> bool:
    parent = node.parent
    if parent is None:
        return False
    if (
        parent.type
        in {
            "class_declaration",
            "enum_declaration",
            "function_declaration",
            "interface_declaration",
            "method_definition",
            "type_alias_declaration",
            "variable_declarator",
        }
        and parent.child_by_field_name("name") == node
    ):
        return True
    if _ancestor(node, "import_statement") is not None:
        return True
    if _ancestor(node, "object_pattern") is not None:
        return True
    if parent.type in {"formal_parameters", "required_parameter", "optional_parameter"}:
        return True
    if parent.type == "pair" and parent.child_by_field_name("key") == node:
        return True
    return False


def extract_javascript_file_fragment(path: str, content: bytes) -> Mapping[str, Any]:
    """Parse one JS/TS artifact into exact, non-executing syntax facts."""

    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JavaScriptMapError(f"JavaScript source is not UTF-8: {path}") from exc
    language = _language(path)
    tree = _parser(language).parse(content)
    root = tree.root_node
    if root.has_error:
        raise JavaScriptMapError(f"tree-sitter JavaScript parse failed: {path}")
    nodes = _walk(root)
    definitions: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    exports: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    scope_bindings: dict[str, set[str]] = {}
    dependency_call_spans: set[tuple[int, int]] = set()

    module_declared_names = {
        _text(content, name)
        for node in nodes
        if node.type
        in {
            "class_declaration",
            "enum_declaration",
            "function_declaration",
            "interface_declaration",
            "type_alias_declaration",
            "variable_declarator",
        }
        and _scope(node, content) == "MODULE"
        and (name := node.child_by_field_name("name")) is not None
        and name.type == "identifier"
    }
    for node in nodes:
        if node.type == "import_statement":
            module_declared_names.update(
                binding["local_name"] for binding in _import_bindings(content, node)
            )
    commonjs_require_available = "require" not in module_declared_names
    commonjs_exports_available = not ({"module", "exports"} & module_declared_names)

    declaration_kinds = {
        "class_declaration": "CLASS",
        "enum_declaration": "ENUM",
        "function_declaration": "FUNCTION",
        "interface_declaration": "INTERFACE",
        "type_alias_declaration": "TYPE_ALIAS",
    }
    for node in nodes:
        if node.type in declaration_kinds:
            name = node.child_by_field_name("name")
            if name is None:
                raise JavaScriptMapError(f"JavaScript declaration has no name: {path}")
            scope = _scope(node, content)
            value = _text(content, name)
            definitions.append(
                {
                    "exported": _ancestor(node, "export_statement") is not None,
                    "name": value,
                    "scope": scope,
                    "span": _span(node),
                    "symbol_kind": declaration_kinds[node.type],
                }
            )
            export_name = _direct_export_name(node)
            if export_name is not None:
                statement = _ancestor(node, "export_statement")
                exports.append(
                    {
                        "exported_name": (
                            value if export_name == "DECLARED_NAME" else export_name
                        ),
                        "local_name": value,
                        "span": _span(statement or node),
                        "syntax": "ESM",
                    }
                )
            scope_bindings.setdefault(scope, set()).add(value)
            if node.type == "function_declaration":
                scope_bindings.setdefault(value, set()).update(
                    _parameter_names(content, node.child_by_field_name("parameters"))
                )
        elif node.type == "method_definition":
            name = node.child_by_field_name("name")
            if name is not None:
                owner = _ancestor(node, "class_declaration")
                owner_name = (
                    owner.child_by_field_name("name") if owner is not None else None
                )
                scope = (
                    _text(content, owner_name) if owner_name is not None else "CLASS"
                )
                value = _text(content, name)
                definitions.append(
                    {
                        "exported": False,
                        "name": value,
                        "scope": scope,
                        "span": _span(node),
                        "symbol_kind": "METHOD",
                    }
                )
                scope_bindings.setdefault(scope, set()).add(value)
                method_scope = f"{scope}.{value}"
                scope_bindings.setdefault(method_scope, set()).update(
                    _parameter_names(content, node.child_by_field_name("parameters"))
                )
        elif node.type == "variable_declarator":
            commonjs = (
                _commonjs_import(content, node) if commonjs_require_available else None
            )
            if commonjs is not None:
                imported, require_span = commonjs
                imports.append(imported)
                dependency_call_spans.add(require_span)
                for binding in imported["bindings"]:
                    scope_bindings.setdefault("MODULE", set()).add(
                        binding["local_name"]
                    )
            name = node.child_by_field_name("name")
            if name is None or name.type != "identifier":
                continue
            if commonjs is not None:
                continue
            value_node = node.child_by_field_name("value")
            scope = _scope(node, content)
            value = _text(content, name)
            definitions.append(
                {
                    "exported": _ancestor(node, "export_statement") is not None,
                    "name": value,
                    "scope": scope,
                    "span": _span(node),
                    "symbol_kind": (
                        "FUNCTION_VARIABLE"
                        if value_node is not None
                        and value_node.type in {"arrow_function", "function_expression"}
                        else "VARIABLE"
                    ),
                }
            )
            export_name = _direct_export_name(node)
            if export_name is not None:
                statement = _ancestor(node, "export_statement")
                exports.append(
                    {
                        "exported_name": (
                            value if export_name == "DECLARED_NAME" else export_name
                        ),
                        "local_name": value,
                        "span": _span(statement or node),
                        "syntax": "ESM",
                    }
                )
            scope_bindings.setdefault(scope, set()).add(value)
            if value_node is not None and value_node.type in {
                "arrow_function",
                "function_expression",
            }:
                scope_bindings.setdefault(value, set()).update(
                    _parameter_names(
                        content,
                        value_node.child_by_field_name("parameters")
                        or value_node.child_by_field_name("parameter"),
                    )
                )
        elif node.type == "import_statement":
            source = node.child_by_field_name("source")
            specifier = _string_literal(content, source)
            if specifier is None:
                raise JavaScriptMapError(f"JavaScript import is not literal: {path}")
            bindings = _import_bindings(content, node)
            imports.append(
                {
                    "bindings": bindings,
                    "specifier": specifier,
                    "span": _span(node),
                    "syntax": "ESM",
                }
            )
            for binding in bindings:
                scope_bindings.setdefault("MODULE", set()).add(binding["local_name"])
        elif node.type == "call_expression":
            if (int(node.start_byte), int(node.end_byte)) in dependency_call_spans:
                continue
            expression, direct, member_object, member_property = _call_expression(
                content, node
            )
            calls.append(
                {
                    "callee_name": direct,
                    "expression": expression,
                    "member_object": member_object,
                    "member_property": member_property,
                    "scope": _scope(node, content),
                    "span": _span(node),
                }
            )
        elif node.type == "identifier" and not _is_definition_identifier(node):
            call_ancestor = _ancestor(node, "call_expression")
            if (
                call_ancestor is not None
                and (int(call_ancestor.start_byte), int(call_ancestor.end_byte))
                in dependency_call_spans
            ):
                continue
            references.append(
                {
                    "name": _text(content, node),
                    "scope": _scope(node, content),
                    "span": _span(node),
                }
            )

    exports.extend(_explicit_exports(content, nodes))
    if commonjs_exports_available:
        exports.extend(_commonjs_exports(content, nodes))
    exports = list(
        {
            (
                item["exported_name"],
                item["local_name"],
                item["syntax"],
                item["span"]["byte_start"],
                item["span"]["byte_end"],
            ): item
            for item in exports
        }.values()
    )

    first_line = content.splitlines()[0].decode("utf-8") if content else ""
    return {
        "path": path,
        "language": language,
        "shebang": first_line if first_line.startswith("#!") else None,
        "tree_root_type": root.type,
        "tree_descendant_count": int(root.descendant_count),
        "definitions": sorted(
            definitions,
            key=lambda item: (
                item["span"]["byte_start"],
                item["scope"],
                item["name"],
            ),
        ),
        "imports": sorted(imports, key=lambda item: item["span"]["byte_start"]),
        "exports": sorted(
            exports,
            key=lambda item: (
                item["span"]["byte_start"],
                item["exported_name"],
                item["local_name"],
            ),
        ),
        "calls": sorted(calls, key=lambda item: item["span"]["byte_start"]),
        "references": sorted(
            references,
            key=lambda item: (item["span"]["byte_start"], item["name"]),
        ),
        "scope_bindings": {
            scope: sorted(names) for scope, names in sorted(scope_bindings.items())
        },
    }
