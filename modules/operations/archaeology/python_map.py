"""Deterministic, non-importing Python fact extraction for mapper M02/M03."""

from __future__ import annotations

import ast
import hashlib
import os
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from .cleanup_map import extract_python_structural_fingerprints
from .evidence import canonical_bytes, sha256_bytes


class PythonMapError(ValueError):
    """Python facts cannot be extracted without drifting from inventory evidence."""


@dataclass(frozen=True)
class PythonFragment:
    files: tuple[Mapping[str, Any], ...]
    project_entrypoints: tuple[Mapping[str, Any], ...]
    failures: tuple[Mapping[str, Any], ...]


def _name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return _name(node.value)
    return ""


def _unparse(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except (RecursionError, ValueError):
        return None


def _span(node: ast.AST) -> dict[str, int]:
    return {
        "line_start": int(getattr(node, "lineno", 0)),
        "column_start": int(getattr(node, "col_offset", 0)),
        "line_end": int(getattr(node, "end_lineno", getattr(node, "lineno", 0))),
        "column_end": int(
            getattr(node, "end_col_offset", getattr(node, "col_offset", 0))
        ),
    }


def _expression_facts(node: ast.AST | None) -> dict[str, Any]:
    if node is None:
        return {"expression": None, "names": [], "calls": [], "literal": None}
    names = sorted(
        {
            item.id
            for item in ast.walk(node)
            if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Load)
        }
    )
    calls = sorted(
        (
            {
                "expression": _name(item.func) or (_unparse(item.func) or ""),
                "span": _span(item),
            }
            for item in ast.walk(node)
            if isinstance(item, ast.Call)
        ),
        key=lambda item: (
            item["span"]["line_start"],
            item["span"]["column_start"],
            item["expression"],
        ),
    )
    literal = node.value if isinstance(node, ast.Constant) else None
    if not isinstance(literal, (str, int, float, bool, type(None))):
        literal = None
    return {
        "expression": _unparse(node),
        "names": names,
        "calls": calls,
        "literal": literal,
    }


def read_exact_artifact(root: Path, record: Mapping[str, Any]) -> bytes:
    """Read an inventory-bound regular artifact with stable identity checks."""

    relative = record["path"]
    path = root / relative
    try:
        before = path.lstat()
    except OSError as exc:
        raise PythonMapError(f"Python source is unavailable: {relative}") from exc
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise PythonMapError(f"Python source is not a real regular file: {relative}")
    expected = (
        record["device"],
        record["inode"],
        record["size_bytes"],
        record["mtime_ns"],
        record["ctime_ns"],
        record["mode"],
        record["uid"],
        record["gid"],
        record["nlink"],
    )

    def identity(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
            stat.S_IMODE(value.st_mode),
            value.st_uid,
            value.st_gid,
            value.st_nlink,
        )

    from .navigation_inventory import open_scoped_regular
    descriptor = open_scoped_regular(root, relative)
    try:
        opened = os.fstat(descriptor)
        if identity(before) != expected or identity(opened) != expected:
            raise PythonMapError(f"Python source drifted before read: {relative}")
        digest = hashlib.sha256()
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
            digest.update(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if identity(after) != expected:
        raise PythonMapError(f"Python source changed during read: {relative}")
    content = b"".join(chunks)
    if digest.hexdigest() != record.get("content_sha256"):
        raise PythonMapError(f"Python source hash drifted from inventory: {relative}")
    return content


def python_module_name(path: str, package_directories: frozenset[str]) -> str:
    """Return a deterministic module name using explicit ``__init__.py`` packages."""

    pure = PurePosixPath(path)
    parent = pure.parent
    packages: list[str] = []
    current = parent
    while current != PurePosixPath(".") and current.as_posix() in package_directories:
        packages.append(current.name)
        current = current.parent
    packages.reverse()
    if pure.stem == "__init__":
        if packages:
            return ".".join(packages)
        return parent.as_posix().replace("/", ".")
    if packages:
        return ".".join([*packages, pure.stem])
    return pure.with_suffix("").as_posix().replace("/", ".")


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, path: str, module: str) -> None:
        self.path = path
        self.module = module
        self.scopes: list[tuple[str, str]] = [(module, "MODULE")]
        self.definitions: list[dict[str, Any]] = []
        self.references: list[dict[str, Any]] = []
        self.imports: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.data_flows: list[dict[str, Any]] = []
        self.entrypoints: list[dict[str, Any]] = []
        self.annotations: list[dict[str, Any]] = []

    @property
    def scope(self) -> str:
        return self.scopes[-1][0]

    def _qualified(self, name: str) -> str:
        return f"{self.scope}.{name}" if self.scope else name

    def _definition(
        self,
        node: ast.AST,
        *,
        name: str,
        kind: str,
        attributes: Mapping[str, Any] | None = None,
    ) -> str:
        qualified = self._qualified(name)
        payload = {
            "name": name,
            "qualified_name": qualified,
            "kind": kind,
            "scope": self.scope,
            "span": _span(node),
            "attributes": dict(attributes or {}),
        }
        self.definitions.append(payload)
        return qualified

    def _parameters(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, function: str
    ) -> list[dict[str, Any]]:
        arguments: list[tuple[ast.arg, str]] = [
            *((item, "POSITIONAL_ONLY") for item in node.args.posonlyargs),
            *((item, "POSITIONAL_OR_KEYWORD") for item in node.args.args),
            *((item, "KEYWORD_ONLY") for item in node.args.kwonlyargs),
        ]
        if node.args.vararg is not None:
            arguments.append((node.args.vararg, "VAR_POSITIONAL"))
        if node.args.kwarg is not None:
            arguments.append((node.args.kwarg, "VAR_KEYWORD"))
        result = []
        for argument, parameter_kind in arguments:
            qualified = f"{function}.{argument.arg}"
            result.append(
                {
                    "name": argument.arg,
                    "qualified_name": qualified,
                    "kind": "PARAMETER",
                    "scope": function,
                    "span": _span(argument),
                    "attributes": {
                        "parameter_kind": parameter_kind,
                        "annotation": _unparse(argument.annotation),
                    },
                }
            )
        return result

    def _function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, asynchronous: bool
    ) -> None:
        parent_kind = self.scopes[-1][1]
        kind = "METHOD" if parent_kind == "CLASS" else "FUNCTION"
        if asynchronous:
            kind = "ASYNC_METHOD" if kind == "METHOD" else "ASYNC_FUNCTION"
        decorators = [_unparse(item) for item in node.decorator_list]
        attributes = {
            "decorators": [item for item in decorators if item is not None],
            "returns": _unparse(node.returns),
            "signature": _unparse(node.args),
        }
        qualified = self._definition(
            node, name=node.name, kind=kind, attributes=attributes
        )
        self.definitions.extend(self._parameters(node, qualified))
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)
        self.scopes.append((qualified, "FUNCTION"))
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node, asynchronous=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node, asynchronous=True)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [item for base in node.bases if (item := _unparse(base)) is not None]
        decorators = [
            item
            for decorator in node.decorator_list
            if (item := _unparse(decorator)) is not None
        ]
        qualified = self._definition(
            node,
            name=node.name,
            kind="CLASS",
            attributes={
                "bases": bases,
                "decorators": decorators,
                "is_protocol": any(
                    base.rsplit(".", 1)[-1] == "Protocol" for base in bases
                ),
                "type_parameters": [
                    item
                    for parameter in getattr(node, "type_params", ())
                    if (item := _unparse(parameter)) is not None
                ],
            },
        )
        for base in node.bases:
            self.visit(base)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.scopes.append((qualified, "CLASS"))
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    def _assigned_names(self, node: ast.AST) -> Iterable[ast.Name]:
        if isinstance(node, ast.Name):
            yield node
        elif isinstance(node, (ast.Tuple, ast.List)):
            for item in node.elts:
                yield from self._assigned_names(item)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            for name in self._assigned_names(target):
                constant = name.id.isupper()
                target_name = self._qualified(name.id)
                self._definition(
                    name,
                    name=name.id,
                    kind="CONSTANT" if constant else "VARIABLE",
                    attributes={"annotation": None},
                )
                self.data_flows.append(
                    {
                        "kind": "ASSIGNMENT",
                        "owner": self.scope,
                        "target": target_name,
                        "value": _expression_facts(node.value),
                        "span": _span(node),
                    }
                )
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        for name in self._assigned_names(node.target):
            constant = name.id.isupper()
            annotation = _unparse(node.annotation)
            target_name = self._qualified(name.id)
            self._definition(
                name,
                name=name.id,
                kind="CONSTANT" if constant else "VARIABLE",
                attributes={"annotation": annotation},
            )
            self.annotations.append(
                {
                    "subject": self._qualified(name.id),
                    "annotation": annotation,
                    "span": _span(node.annotation),
                }
            )
            if node.value is not None:
                self.data_flows.append(
                    {
                        "kind": "ASSIGNMENT",
                        "owner": self.scope,
                        "target": target_name,
                        "value": _expression_facts(node.value),
                        "span": _span(node),
                    }
                )
        if node.value is not None:
            self.visit(node.value)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.references.append(
                {
                    "name": node.id,
                    "expression": node.id,
                    "scope": self.scope,
                    "span": _span(node),
                }
            )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        expression = _name(node)
        self.references.append(
            {
                "name": node.attr,
                "expression": expression or node.attr,
                "scope": self.scope,
                "span": _span(node),
            }
        )
        self.visit(node.value)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                {
                    "module": alias.name,
                    "imported_name": None,
                    "alias": alias.asname or alias.name.split(".", 1)[0],
                    "level": 0,
                    "span": _span(node),
                }
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.imports.append(
                {
                    "module": node.module or "",
                    "imported_name": alias.name,
                    "alias": alias.asname or alias.name,
                    "level": node.level,
                    "span": _span(node),
                }
            )

    def visit_If(self, node: ast.If) -> None:
        test = _unparse(node.test) or ""
        if "__name__" in test and "__main__" in test:
            self.entrypoints.append(
                {
                    "kind": "PYTHON_MODULE_MAIN_GUARD",
                    "name": self.module,
                    "target": self.module,
                    "handler": None,
                    "span": _span(node),
                }
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        called = _name(node.func)
        self.calls.append(
            {
                "caller": self.scope,
                "expression": called or (_unparse(node.func) or ""),
                "name": called.rsplit(".", 1)[-1] if called else "",
                "span": _span(node),
                "dynamic": not bool(called),
                "arguments": {
                    "positional": [_expression_facts(item) for item in node.args],
                    "keywords": [
                        {
                            "name": item.arg,
                            **_expression_facts(item.value),
                        }
                        for item in node.keywords
                    ],
                },
            }
        )
        leaf = called.rsplit(".", 1)[-1]
        if leaf == "add_parser" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                self.entrypoints.append(
                    {
                        "kind": "ARGPARSE_COMMAND",
                        "name": first.value,
                        "target": called,
                        "handler": None,
                        "span": _span(node),
                    }
                )
        elif leaf == "add_argument":
            names = [
                item.value
                for item in node.args
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
            if names:
                self.entrypoints.append(
                    {
                        "kind": "ARGPARSE_OPTION",
                        "name": names[0],
                        "target": called,
                        "handler": None,
                        "option_strings": names,
                        "span": _span(node),
                    }
                )
        elif leaf == "set_defaults":
            for keyword in node.keywords:
                if keyword.arg == "func":
                    self.entrypoints.append(
                        {
                            "kind": "ARGPARSE_HANDLER",
                            "name": _name(keyword.value)
                            or (_unparse(keyword.value) or ""),
                            "target": called,
                            "handler": _name(keyword.value) or None,
                            "span": _span(node),
                        }
                    )
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        self.data_flows.append(
            {
                "kind": "RETURN",
                "owner": self.scope,
                "target": self.scope,
                "value": _expression_facts(node.value),
                "span": _span(node),
            }
        )
        if node.value is not None:
            self.visit(node.value)


_TERMINAL_STATEMENTS = (ast.Return, ast.Raise)


class _ControlFlowBuilder:
    """Build a deterministic, source-level CFG for one Python callable.

    The graph is exact for explicit structured branches and terminal statements. Exception edges
    from arbitrary operations and runtime dispatch remain unsupported and are reported in map
    coverage rather than inferred.
    """

    def __init__(self, owner: str, definition_span: Mapping[str, int]) -> None:
        self.owner = owner
        self.definition_span = dict(definition_span)
        self.flow_key = ":".join(
            (
                owner,
                "definition",
                str(definition_span["line_start"]),
                str(definition_span["column_start"]),
                str(definition_span["line_end"]),
                str(definition_span["column_end"]),
            )
        )
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self._key_occurrences: dict[str, int] = {}

    def _key(self, node: ast.AST | None, kind: str) -> str:
        if node is None:
            return f"{self.flow_key}:{kind}"
        span = _span(node)
        return ":".join(
            (
                self.flow_key,
                kind,
                str(span["line_start"]),
                str(span["column_start"]),
                str(span["line_end"]),
                str(span["column_end"]),
            )
        )

    def _node(
        self,
        node: ast.AST | None,
        kind: str,
        *,
        attributes: Mapping[str, Any] | None = None,
    ) -> str:
        base_key = self._key(node, kind)
        occurrence = self._key_occurrences.get(base_key, 0)
        self._key_occurrences[base_key] = occurrence + 1
        key = base_key if occurrence == 0 else f"{base_key}:occurrence:{occurrence}"
        self.nodes.append(
            {
                "node_key": key,
                "owner": self.owner,
                "kind": kind,
                "span": None if node is None else _span(node),
                "attributes": dict(attributes or {}),
            }
        )
        return key

    def _edge(
        self,
        source: str,
        predicate: str,
        target: str | None,
        *,
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        if target is None:
            return
        self.edges.append(
            {
                "source_key": source,
                "predicate": predicate,
                "target_key": target,
                "attributes": dict(attributes or {}),
            }
        )

    def _statement_node(self, statement: ast.stmt) -> str:
        attributes: dict[str, Any] = {}
        if isinstance(statement, (ast.If, ast.While, ast.Assert)):
            attributes["condition"] = _unparse(statement.test)
        elif isinstance(statement, (ast.For, ast.AsyncFor)):
            attributes.update(
                {
                    "target": _unparse(statement.target),
                    "iterator": _unparse(statement.iter),
                }
            )
        elif isinstance(statement, (ast.With, ast.AsyncWith)):
            attributes["contexts"] = [
                _unparse(item.context_expr) for item in statement.items
            ]
        elif isinstance(statement, ast.Match):
            attributes["subject"] = _unparse(statement.subject)
        elif isinstance(statement, ast.Raise):
            attributes["exception"] = _unparse(statement.exc)
        elif isinstance(statement, ast.Return):
            attributes["value"] = _unparse(statement.value)
        return self._node(
            statement, type(statement).__name__.upper(), attributes=attributes
        )

    def _block(
        self,
        statements: Sequence[ast.stmt],
        next_key: str,
        *,
        break_target: str | None = None,
        continue_target: str | None = None,
    ) -> str:
        current = next_key
        for statement in reversed(statements):
            node_key = self._statement_node(statement)
            if isinstance(statement, ast.If):
                true_entry = self._block(
                    statement.body,
                    current,
                    break_target=break_target,
                    continue_target=continue_target,
                )
                false_entry = self._block(
                    statement.orelse,
                    current,
                    break_target=break_target,
                    continue_target=continue_target,
                )
                self._edge(node_key, "BRANCH_TRUE", true_entry)
                self._edge(node_key, "BRANCH_FALSE", false_entry)
            elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                normal_exit = self._block(
                    statement.orelse,
                    current,
                    break_target=break_target,
                    continue_target=continue_target,
                )
                body_entry = self._block(
                    statement.body,
                    node_key,
                    break_target=current,
                    continue_target=node_key,
                )
                self._edge(node_key, "LOOP_BODY", body_entry)
                self._edge(node_key, "LOOP_EXIT", normal_exit)
            elif isinstance(statement, ast.Break):
                self._edge(node_key, "BREAKS_TO", break_target)
            elif isinstance(statement, ast.Continue):
                self._edge(node_key, "CONTINUES_TO", continue_target)
            elif isinstance(statement, (ast.With, ast.AsyncWith)):
                body_entry = self._block(
                    statement.body,
                    current,
                    break_target=break_target,
                    continue_target=continue_target,
                )
                self._edge(node_key, "ENTERS_BODY", body_entry)
            elif isinstance(statement, (ast.Try, ast.TryStar)):
                final_entry = self._block(
                    statement.finalbody,
                    current,
                    break_target=break_target,
                    continue_target=continue_target,
                )
                else_entry = self._block(
                    statement.orelse,
                    final_entry,
                    break_target=break_target,
                    continue_target=continue_target,
                )
                body_entry = self._block(
                    statement.body,
                    else_entry,
                    break_target=break_target,
                    continue_target=continue_target,
                )
                self._edge(node_key, "TRY_BODY", body_entry)
                for index, handler in enumerate(statement.handlers):
                    handler_entry = self._block(
                        handler.body,
                        final_entry,
                        break_target=break_target,
                        continue_target=continue_target,
                    )
                    self._edge(
                        node_key,
                        "EXCEPTION_HANDLER",
                        handler_entry,
                        attributes={
                            "index": index,
                            "exception": _unparse(handler.type),
                            "name": handler.name,
                        },
                    )
                if statement.finalbody:
                    self._edge(node_key, "FINALLY", final_entry)
            elif isinstance(statement, ast.Match):
                irrefutable = False
                for index, case in enumerate(statement.cases):
                    case_entry = self._block(
                        case.body,
                        current,
                        break_target=break_target,
                        continue_target=continue_target,
                    )
                    self._edge(
                        node_key,
                        "MATCH_CASE",
                        case_entry,
                        attributes={
                            "index": index,
                            "pattern": _unparse(case.pattern),
                            "guard": _unparse(case.guard),
                        },
                    )
                    irrefutable = irrefutable or (
                        isinstance(case.pattern, ast.MatchAs)
                        and case.pattern.pattern is None
                        and case.guard is None
                    )
                if not irrefutable:
                    self._edge(node_key, "MATCH_NO_CASE", current)
            elif isinstance(statement, _TERMINAL_STATEMENTS):
                pass
            else:
                self._edge(node_key, "NEXT", current)
            current = node_key
        return current

    def build(self, body: Sequence[ast.stmt]) -> Mapping[str, Any]:
        entry = self._node(None, "FUNCTION_ENTRY")
        exit_ = self._node(None, "FUNCTION_EXIT")
        first = self._block(body, exit_)
        self._edge(entry, "NEXT", first)
        return {
            "owner": self.owner,
            "definition_span": self.definition_span,
            "nodes": sorted(self.nodes, key=lambda item: item["node_key"]),
            "edges": sorted(
                self.edges,
                key=lambda item: (
                    item["source_key"],
                    item["predicate"],
                    item["target_key"],
                    repr(sorted(item["attributes"].items())),
                ),
            ),
        }


class _FunctionControlVisitor(ast.NodeVisitor):
    def __init__(self, module: str) -> None:
        self.scopes = [module]
        self.flows: list[Mapping[str, Any]] = []

    @property
    def scope(self) -> str:
        return self.scopes[-1]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes.append(f"{self.scope}.{node.name}")
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        owner = f"{self.scope}.{node.name}"
        self.flows.append(_ControlFlowBuilder(owner, _span(node)).build(node.body))
        self.scopes.append(owner)
        for statement in node.body:
            if isinstance(
                statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                self.visit(statement)
        self.scopes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)


def _project_entrypoints(
    path: str, content: bytes
) -> tuple[list[dict[str, Any]], Mapping[str, Any] | None]:
    try:
        parsed = tomllib.loads(content.decode("utf-8", "strict"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return [], {
            "path": path,
            "status": "FAILED_PARSE",
            "error_class": type(exc).__name__,
            "error_sha256": sha256_bytes(str(exc).encode("utf-8", "replace")),
            "maps": ["api_events"],
        }
    project = parsed.get("project", {})
    if not isinstance(project, dict):
        return [], {
            "path": path,
            "status": "FAILED_SCHEMA",
            "error_class": "ProjectTableType",
            "error_sha256": sha256_bytes(canonical_bytes(project)),
            "maps": ["api_events"],
        }
    scripts = project.get("scripts", {})
    if not isinstance(scripts, dict):
        return [], {
            "path": path,
            "status": "FAILED_SCHEMA",
            "error_class": "ProjectScriptsType",
            "error_sha256": sha256_bytes(canonical_bytes(scripts)),
            "maps": ["api_events"],
        }
    return (
        [
            {
                "path": path,
                "kind": "PYTHON_PROJECT_SCRIPT",
                "name": name,
                "target": target,
                "handler": target.split(":", 1)[1] if ":" in target else None,
                "span": None,
            }
            for name, target in sorted(scripts.items())
            if isinstance(name, str) and isinstance(target, str)
        ],
        None,
    )


def extract_python_file_fragment(
    root: Path,
    record: Mapping[str, Any],
    package_directories: frozenset[str],
) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None]:
    """Extract one inventory-bound Python file without importing target code.

    Keeping this boundary source-local allows the mapper to cache an authenticated
    fragment for an unchanged file.  The caller must bind the package context because
    adding or removing an ``__init__.py`` can change the module name even when this
    file's own bytes are unchanged.
    """

    path = record["path"]
    content = read_exact_artifact(root, record)
    module = python_module_name(path, package_directories)
    try:
        text = content.decode("utf-8", "strict")
        tree = ast.parse(text, filename=path, type_comments=True)
    except (UnicodeDecodeError, SyntaxError) as exc:
        return None, {
            "path": path,
            "status": "FAILED_PARSE",
            "error_class": type(exc).__name__,
            "error_sha256": sha256_bytes(str(exc).encode("utf-8", "replace")),
            "maps": [
                "symbols",
                "dependencies",
                "types",
                "api_events",
                "calls",
                "control_flow",
                "data_flow_taint",
                "security_capabilities",
            ],
        }
    visitor = _PythonVisitor(path, module)
    visitor.visit(tree)
    control_visitor = _FunctionControlVisitor(module)
    control_visitor.visit(tree)
    structural_similarity = extract_python_structural_fingerprints(
        path=path,
        module=module,
        content_sha256=record["content_sha256"],
        tree=tree,
    )
    unique_data_flows = {canonical_bytes(flow): flow for flow in visitor.data_flows}
    entrypoints = list(visitor.entrypoints)
    if PurePosixPath(path).name == "__main__.py":
        entrypoints.append(
            {
                "kind": "PYTHON_MODULE_MAIN",
                "name": module,
                "target": module,
                "handler": None,
                "span": None,
            }
        )
    if record["mode"] & 0o111:
        entrypoints.append(
            {
                "kind": "PYTHON_EXECUTABLE_FILE",
                "name": path,
                "target": path,
                "handler": None,
                "span": None,
            }
        )
    return {
        "path": path,
        "content_sha256": record["content_sha256"],
        "module": module,
        "definitions": sorted(
            visitor.definitions,
            key=lambda item: (
                item["span"]["line_start"],
                item["span"]["column_start"],
                item["qualified_name"],
                item["kind"],
            ),
        ),
        "references": sorted(
            visitor.references,
            key=lambda item: (
                item["span"]["line_start"],
                item["span"]["column_start"],
                item["expression"],
            ),
        ),
        "imports": sorted(
            visitor.imports,
            key=lambda item: (
                item["span"]["line_start"],
                item["span"]["column_start"],
                item["module"],
                item["imported_name"] or "",
            ),
        ),
        "calls": sorted(
            visitor.calls,
            key=lambda item: (
                item["span"]["line_start"],
                item["span"]["column_start"],
                item["expression"],
            ),
        ),
        "data_flows": sorted(
            unique_data_flows.values(),
            key=lambda item: (
                item["span"]["line_start"],
                item["span"]["column_start"],
                item["kind"],
                item["target"],
            ),
        ),
        "control_flows": sorted(
            control_visitor.flows,
            key=lambda item: item["owner"],
        ),
        "structural_similarity": structural_similarity,
        "entrypoints": sorted(
            entrypoints,
            key=lambda item: (
                0 if item["span"] is None else item["span"]["line_start"],
                item["kind"],
                item["name"],
            ),
        ),
        "annotations": sorted(
            visitor.annotations,
            key=lambda item: (
                item["span"]["line_start"],
                item["subject"],
            ),
        ),
        "ast_sha256": sha256_bytes(
            canonical_bytes(
                ast.dump(tree, annotate_fields=True, include_attributes=True)
            )
        ),
    }, None


def extract_project_file_fragment(
    root: Path, record: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Mapping[str, Any] | None]:
    """Extract one inventory-bound project manifest's Python entrypoints."""

    content = read_exact_artifact(root, record)
    entries, failure = _project_entrypoints(record["path"], content)
    return tuple(
        sorted(entries, key=lambda item: (item["path"], item["kind"], item["name"]))
    ), failure


def extract_python_fragment(
    root: Path,
    python_records: Sequence[Mapping[str, Any]],
    project_records: Sequence[Mapping[str, Any]],
) -> PythonFragment:
    """Extract exact Python facts without importing or executing target code."""

    package_directories = frozenset(
        str(PurePosixPath(record["path"]).parent)
        for record in python_records
        if PurePosixPath(record["path"]).name == "__init__.py"
    )
    files: list[Mapping[str, Any]] = []
    failures: list[Mapping[str, Any]] = []
    for record in python_records:
        file_fragment, failure = extract_python_file_fragment(
            root, record, package_directories
        )
        if file_fragment is not None:
            files.append(file_fragment)
        if failure is not None:
            failures.append(failure)
    project_entrypoints: list[Mapping[str, Any]] = []
    for record in project_records:
        entries, failure = extract_project_file_fragment(root, record)
        project_entrypoints.extend(entries)
        if failure is not None:
            failures.append(failure)
    return PythonFragment(
        files=tuple(sorted(files, key=lambda item: item["path"])),
        project_entrypoints=tuple(
            sorted(
                project_entrypoints,
                key=lambda item: (item["path"], item["kind"], item["name"]),
            )
        ),
        failures=tuple(sorted(failures, key=lambda item: item["path"])),
    )
