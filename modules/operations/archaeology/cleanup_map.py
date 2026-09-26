"""Closed policy for duplicate and static-reachability navigation maps.

This module does not read source and does not classify anything for deletion.  It
defines the safe projection boundary used by the shared mapper.  Exact file
duplicates come from the authenticated navigation inventory; normalized Python
structure is derived from the already-parsed, inventory-bound AST; reachability
comes from already-produced deterministic entrypoint/import/call facts.
"""

from __future__ import annotations

import ast
import copy
from typing import Any, Mapping, Sequence

from .evidence import canonical_bytes, sha256_bytes


PYTHON_STRUCTURE_POLICY_VERSION = (
    "giga.archaeologist.python-structural-fingerprint-policy.v1"
)
PYTHON_STRUCTURE_POLICY: Mapping[str, Any] = {
    "authority_granted": False,
    "cleanup_permitted": False,
    "deletion_permitted": False,
    "semantic_equivalence_claimed": False,
    "language": "python",
    "normalization": {
        "function_name": "OMITTED",
        "leading_docstring": "OMITTED",
        "locations": "OMITTED",
        "parameters_and_local_bindings": "ALPHA_RENAMED_BY_FIRST_BINDING_ORDER",
        "global_and_free_names": "PRESERVED_EXACT",
        "attributes_keywords_literals_operators": "PRESERVED_EXACT",
        "annotations_decorators_defaults": "PRESERVED_EXACT",
    },
    "minimum_ast_nodes": 20,
    "minimum_statements": 3,
    "unsupported": [
        "dynamic-namespace-access",
        "global-or-nonlocal-declarations",
        "nested-definitions-or-lambdas-in-parent-fingerprint",
    ],
    "truth_class": "OBSERVED",
}
PYTHON_STRUCTURE_POLICY_SHA256 = sha256_bytes(canonical_bytes(PYTHON_STRUCTURE_POLICY))

CLEANUP_POLICY_VERSION = "giga.archaeologist.cleanup-map-policy.v3"
CLEANUP_POLICY: Mapping[str, Any] = {
    "authority_granted": False,
    "cleanup_permitted": False,
    "deletion_permitted": False,
    "duplicate_tiers": {
        "exact_content": "PROVEN",
        "structural": "OBSERVED_NORMALIZED_PYTHON_AST_EXACT",
        "semantic": "UNSUPPORTED",
    },
    "python_structure_policy": PYTHON_STRUCTURE_POLICY_VERSION,
    "python_structure_policy_sha256": PYTHON_STRUCTURE_POLICY_SHA256,
    "reachability": {
        "positive": "REACHED_FROM_SUPPORTED_STATIC_ROOT",
        "negative": "NOT_REACHED_BY_SUPPORTED_STATIC_ROOTS",
        "negative_truth_class": "INFERRED",
        "runtime_reachability": "NOT_OBSERVED",
        "usage_counterevidence": {
            "exact": [
                "RESOLVED_REFERENCE",
                "RESOLVED_CALL",
                "RESOLVED_IMPORT",
            ],
            "observed": [
                "DECORATED_DEFINITION",
                "DYNAMIC_STRING_NAME_MATCH",
            ],
            "absence": "NEVER_INFERRED",
            "runtime_reachability_claimed": False,
        },
    },
    "existing_authority_owner": "modules.operations.archaeology.judge",
    "existing_counterevidence_owner": "modules.operations.archaeology.counterevidence",
}
CLEANUP_POLICY_SHA256 = sha256_bytes(canonical_bytes(CLEANUP_POLICY))


_DYNAMIC_NAMESPACE_CALLS = frozenset(
    {"__import__", "compile", "eval", "exec", "globals", "locals", "vars"}
)


class _LocalBindingCollector(ast.NodeVisitor):
    """Collect one callable's local bindings without entering nested scopes."""

    def __init__(self) -> None:
        self.names: list[str] = []
        self._seen: set[str] = set()

    def bind(self, name: str | None) -> None:
        if name and name not in self._seen:
            self._seen.add(name)
            self.names.append(name)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.bind(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.bind(alias.asname or alias.name.partition(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.bind(alias.asname or alias.name)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.bind(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        self.bind(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        self.bind(node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.bind(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.bind(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.bind(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


class _AlphaRename(ast.NodeTransformer):
    """Rename only proven callable-local bindings; preserve external names exactly."""

    def __init__(self, bindings: Mapping[str, str]) -> None:
        self.bindings = bindings

    def visit_Name(self, node: ast.Name) -> ast.Name:
        return ast.copy_location(
            ast.Name(id=self.bindings.get(node.id, node.id), ctx=node.ctx), node
        )

    def visit_arg(self, node: ast.arg) -> ast.arg:
        return ast.copy_location(
            ast.arg(
                arg=self.bindings.get(node.arg, node.arg),
                annotation=copy.deepcopy(node.annotation),
                type_comment=node.type_comment,
            ),
            node,
        )

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AnnAssign:
        return ast.copy_location(
            ast.AnnAssign(
                target=self.visit(node.target),
                annotation=copy.deepcopy(node.annotation),
                value=self.visit(node.value) if node.value else None,
                simple=node.simple,
            ),
            node,
        )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        value = self.generic_visit(node)
        if isinstance(value, ast.ExceptHandler) and value.name:
            value.name = self.bindings.get(value.name, value.name)
        return value

    def visit_MatchAs(self, node: ast.MatchAs) -> ast.MatchAs:
        value = self.generic_visit(node)
        if isinstance(value, ast.MatchAs) and value.name:
            value.name = self.bindings.get(value.name, value.name)
        return value

    def visit_MatchStar(self, node: ast.MatchStar) -> ast.MatchStar:
        value = self.generic_visit(node)
        if isinstance(value, ast.MatchStar) and value.name:
            value.name = self.bindings.get(value.name, value.name)
        return value


def _span(node: ast.AST) -> dict[str, int]:
    return {
        "line_start": int(getattr(node, "lineno", 0)),
        "column_start": int(getattr(node, "col_offset", 0)),
        "line_end": int(getattr(node, "end_lineno", getattr(node, "lineno", 0))),
        "column_end": int(
            getattr(node, "end_col_offset", getattr(node, "col_offset", 0))
        ),
    }


def _is_docstring(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _call_leaf(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _function_structure(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    path: str,
    qualified_name: str,
    content_sha256: str,
    symbol_kind: str,
) -> tuple[dict[str, Any] | None, str | None]:
    body = list(node.body)
    if body and _is_docstring(body[0]):
        body = body[1:]
    nested = tuple(
        item
        for statement in body
        for item in ast.walk(statement)
        if isinstance(
            item,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
        )
    )
    if nested:
        return None, "nested-definitions-or-lambdas"
    if any(
        isinstance(item, (ast.Global, ast.Nonlocal))
        for statement in body
        for item in ast.walk(statement)
    ):
        return None, "global-or-nonlocal-declarations"
    if any(
        isinstance(item, ast.Call) and _call_leaf(item) in _DYNAMIC_NAMESPACE_CALLS
        for statement in body
        for item in ast.walk(statement)
    ):
        return None, "dynamic-namespace-access"

    collector = _LocalBindingCollector()
    arguments = (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    )
    for argument in arguments:
        collector.bind(argument.arg)
    if node.args.vararg:
        collector.bind(node.args.vararg.arg)
    if node.args.kwarg:
        collector.bind(node.args.kwarg.arg)
    for statement in body:
        collector.visit(statement)
    bindings = {name: f"LOCAL_{index}" for index, name in enumerate(collector.names)}
    normalized_body = _AlphaRename(bindings).visit(
        ast.Module(body=copy.deepcopy(body), type_ignores=[])
    )
    ast.fix_missing_locations(normalized_body)
    statement_count = sum(
        isinstance(item, ast.stmt) for item in ast.walk(normalized_body)
    )
    ast_node_count = sum(1 for _item in ast.walk(normalized_body))
    if statement_count < PYTHON_STRUCTURE_POLICY["minimum_statements"]:
        return None, "below-minimum-statements"
    if ast_node_count < PYTHON_STRUCTURE_POLICY["minimum_ast_nodes"]:
        return None, "below-minimum-ast-nodes"

    signature = {
        "asynchronous": isinstance(node, ast.AsyncFunctionDef),
        "positional_only": len(node.args.posonlyargs),
        "positional_or_keyword": len(node.args.args),
        "keyword_only": len(node.args.kwonlyargs),
        "var_positional": node.args.vararg is not None,
        "var_keyword": node.args.kwarg is not None,
        "parameter_annotations": [
            ast.dump(argument.annotation, include_attributes=False)
            if argument.annotation
            else None
            for argument in arguments
        ],
        "return_annotation": ast.dump(node.returns, include_attributes=False)
        if node.returns
        else None,
        "defaults": [
            ast.dump(value, include_attributes=False)
            for value in (*node.args.defaults, *node.args.kw_defaults)
            if value is not None
        ],
        "decorators": [
            ast.dump(value, include_attributes=False) for value in node.decorator_list
        ],
    }
    normalized = {
        "body": ast.dump(
            normalized_body, annotate_fields=True, include_attributes=False
        ),
        "policy": PYTHON_STRUCTURE_POLICY_VERSION,
        "signature": signature,
    }
    return (
        {
            "ast_node_count": ast_node_count,
            "content_sha256": content_sha256,
            "fingerprint_sha256": sha256_bytes(canonical_bytes(normalized)),
            "normalization_policy_sha256": PYTHON_STRUCTURE_POLICY_SHA256,
            "path": path,
            "qualified_name": qualified_name,
            "span": _span(node),
            "statement_count": statement_count,
            "symbol_kind": symbol_kind,
        },
        None,
    )


class _FunctionStructureVisitor(ast.NodeVisitor):
    def __init__(self, path: str, module: str, content_sha256: str) -> None:
        self.path = path
        self.scopes = [module]
        self.scope_kinds = ["MODULE"]
        self.content_sha256 = content_sha256
        self.fingerprints: list[dict[str, Any]] = []
        self.skipped: dict[str, int] = {}
        self.functions_total = 0

    @property
    def scope(self) -> str:
        return self.scopes[-1]

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.functions_total += 1
        qualified = f"{self.scope}.{node.name}"
        symbol_kind = "METHOD" if self.scope_kinds[-1] == "CLASS" else "FUNCTION"
        if isinstance(node, ast.AsyncFunctionDef):
            symbol_kind = f"ASYNC_{symbol_kind}"
        fingerprint, reason = _function_structure(
            node,
            path=self.path,
            qualified_name=qualified,
            content_sha256=self.content_sha256,
            symbol_kind=symbol_kind,
        )
        if fingerprint is not None:
            self.fingerprints.append(fingerprint)
        else:
            key = reason or "unknown"
            self.skipped[key] = self.skipped.get(key, 0) + 1
        self.scopes.append(qualified)
        self.scope_kinds.append("FUNCTION")
        self.generic_visit(node)
        self.scope_kinds.pop()
        self.scopes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes.append(f"{self.scope}.{node.name}")
        self.scope_kinds.append("CLASS")
        self.generic_visit(node)
        self.scope_kinds.pop()
        self.scopes.pop()


def extract_python_structural_fingerprints(
    *, path: str, module: str, content_sha256: str, tree: ast.Module
) -> Mapping[str, Any]:
    """Return conservative source-local implementation fingerprints.

    Equality proves only that the closed normalized representation is identical.
    It never proves semantic equivalence, ownership, cleanup safety or dead code.
    """

    visitor = _FunctionStructureVisitor(path, module, content_sha256)
    visitor.visit(tree)
    return {
        "eligible": len(visitor.fingerprints),
        "fingerprints": sorted(
            visitor.fingerprints,
            key=lambda item: (
                item["span"]["line_start"],
                item["span"]["column_start"],
                item["qualified_name"],
            ),
        ),
        "functions_total": visitor.functions_total,
        "policy": PYTHON_STRUCTURE_POLICY_VERSION,
        "policy_sha256": PYTHON_STRUCTURE_POLICY_SHA256,
        "skipped": {key: visitor.skipped[key] for key in sorted(visitor.skipped)},
    }


def safe_exact_duplicate_groups(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Return exact semantic-safe groups and the number skipped by policy."""

    by_digest: dict[str, list[dict[str, Any]]] = {}
    skipped_digests: set[str] = set()
    for record in records:
        digest = record.get("content_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            continue
        if record.get("semantic_eligible") != 1:
            skipped_digests.add(digest)
            continue
        by_digest.setdefault(digest, []).append(dict(record))
    groups = [
        {
            "content_sha256": digest,
            "members": sorted(members, key=lambda item: item["path"]),
        }
        for digest, members in sorted(by_digest.items())
        if len(members) > 1 and digest not in skipped_digests
    ]
    return groups, len(skipped_digests)


def safe_structural_duplicate_groups(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Group exact normalized Python fingerprints without semantic promotion."""

    by_fingerprint: dict[str, list[dict[str, Any]]] = {}
    malformed = 0
    for value in records:
        record = dict(value)
        fingerprint = record.get("fingerprint_sha256")
        if (
            not isinstance(fingerprint, str)
            or len(fingerprint) != 64
            or record.get("normalization_policy_sha256")
            != PYTHON_STRUCTURE_POLICY_SHA256
            or not isinstance(record.get("path"), str)
            or not isinstance(record.get("qualified_name"), str)
            or record.get("symbol_kind")
            not in {"FUNCTION", "ASYNC_FUNCTION", "METHOD", "ASYNC_METHOD"}
            or not isinstance(record.get("span"), Mapping)
        ):
            malformed += 1
            continue
        by_fingerprint.setdefault(fingerprint, []).append(record)

    groups: list[dict[str, Any]] = []
    exact_file_groups_omitted = 0
    for fingerprint, members in sorted(by_fingerprint.items()):
        unique = {
            (
                member["path"],
                member["qualified_name"],
                member["span"]["line_start"],
                member["span"]["column_start"],
            ): member
            for member in members
        }
        ordered = [unique[key] for key in sorted(unique)]
        if len(ordered) < 2:
            continue
        paths = {member["path"] for member in ordered}
        content_hashes = {member.get("content_sha256") for member in ordered}
        if len(paths) > 1 and len(content_hashes) == 1:
            exact_file_groups_omitted += 1
            continue
        groups.append(
            {
                "fingerprint_sha256": fingerprint,
                "members": ordered,
                "normalization_policy_sha256": PYTHON_STRUCTURE_POLICY_SHA256,
            }
        )
    return groups, {
        "exact_file_groups_omitted": exact_file_groups_omitted,
        "malformed_records": malformed,
    }
