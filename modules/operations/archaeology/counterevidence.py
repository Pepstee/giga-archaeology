"""Slice 3: static entrypoint and dynamic-use counterevidence.

This module never imports target code.  It records evidence that can falsify a
scanner's unused/duplicate hypothesis; absence of such evidence is UNKNOWN.
"""

from __future__ import annotations

import ast
import json
import os
import re
import stat
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .evidence import (
    EvidenceError,
    canonical_bytes,
    seal_document,
    sha256_bytes,
    validate_self_hash,
    write_atomic,
)
from .hypotheses import HYPOTHESES_SCHEMA
from .inventory import INVENTORY_SCHEMA


COUNTEREVIDENCE_SCHEMA = "giga.archaeologist.counterevidence.v1"
QUOTED_NAME = re.compile(r"'([^']+)'|\"([^\"]+)\"")
DYNAMIC_CALLS = {
    "getattr",
    "import_module",
    "register",
    "route",
    "command",
    "handler",
    "add_parser",
    "load",
    "resolve",
}


class CounterevidenceError(ValueError):
    """Inputs or source state cannot support a trustworthy evidence packet."""


def _load(path: Path, schema: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CounterevidenceError("input is not strict UTF-8 JSON") from exc
    try:
        validate_self_hash(value)
    except EvidenceError as exc:
        raise CounterevidenceError(str(exc)) from exc
    if value.get("schema") != schema:
        raise CounterevidenceError(f"unsupported input schema: {value.get('schema')!r}")
    if (
        value.get("authority_granted") is not False
        or value.get("cleanup_permitted") is not False
    ):
        raise CounterevidenceError("input authority boundary is not closed")
    return value, raw


def _read_exact(root: Path, record: Mapping[str, Any]) -> bytes:
    path = root / record["path"]
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode):
        raise CounterevidenceError(
            f"source is no longer a regular file: {record['path']}"
        )
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        content = b""
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            content += chunk
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    def identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    if identity(before) != identity(opened) or identity(opened) != identity(after):
        raise CounterevidenceError(f"source changed during read: {record['path']}")
    if len(content) != record["bytes"] or sha256_bytes(content) != record["sha256"]:
        raise CounterevidenceError(f"source drifted from inventory: {record['path']}")
    return content


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


class _Usage(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.references: list[dict[str, Any]] = []
        self.imports: list[dict[str, Any]] = []
        self.dynamic: list[dict[str, Any]] = []
        self.decorators: list[dict[str, Any]] = []
        self.module_main: list[dict[str, Any]] = []

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.references.append(
                {"name": node.id, "path": self.path, "line": node.lineno}
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.references.append(
            {"name": node.attr, "path": self.path, "line": node.lineno}
        )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                {
                    "module": alias.name,
                    "name": alias.asname or alias.name,
                    "path": self.path,
                    "line": node.lineno,
                }
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = "." * node.level + (node.module or "")
        for alias in node.names:
            self.imports.append(
                {
                    "module": module,
                    "name": alias.name,
                    "path": self.path,
                    "line": node.lineno,
                }
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        called = _name(node.func)
        leaf = called.rsplit(".", 1)[-1]
        if leaf in DYNAMIC_CALLS:
            literals = [
                arg.value
                for arg in node.args
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
            ]
            self.dynamic.append(
                {
                    "call": called,
                    "literals": literals,
                    "path": self.path,
                    "line": node.lineno,
                }
            )
        self.generic_visit(node)

    def _definition(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
    ) -> None:
        for decorator in node.decorator_list:
            self.decorators.append(
                {
                    "symbol": node.name,
                    "decorator": _name(
                        decorator.func if isinstance(decorator, ast.Call) else decorator
                    ),
                    "path": self.path,
                    "line": node.lineno,
                }
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._definition(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._definition(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._definition(node)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        try:
            test = ast.unparse(node.test)
        except Exception:
            test = ""
        if "__name__" in test and "__main__" in test:
            self.module_main.append({"path": self.path, "line": node.lineno})
        self.generic_visit(node)


def _module_for_path(path: str) -> str | None:
    pure = PurePosixPath(path)
    if pure.suffix not in {".py", ".pyi"}:
        return None
    parts = list(pure.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


def _symbol_from_hypothesis(item: Mapping[str, Any]) -> str | None:
    symbol = item.get("detail", {}).get("symbol")
    if isinstance(symbol, str) and symbol:
        return symbol
    message = item.get("detail", {}).get("message", "")
    match = QUOTED_NAME.search(message) if isinstance(message, str) else None
    if not match:
        return None
    return match.group(1) or match.group(2)


def build_counterevidence(
    inventory_path: Path, hypotheses_path: Path
) -> dict[str, Any]:
    inventory, inventory_raw = _load(inventory_path, INVENTORY_SCHEMA)
    hypotheses, hypotheses_raw = _load(hypotheses_path, HYPOTHESES_SCHEMA)
    if hypotheses["inventory"]["receipt_sha256"] != inventory["receipt_sha256"]:
        raise CounterevidenceError("hypotheses do not bind the supplied inventory")
    if hypotheses["inventory"]["file_sha256"] != sha256_bytes(inventory_raw):
        raise CounterevidenceError("hypothesis inventory file hash mismatch")

    root = Path(inventory["repository"]["root"]).resolve(strict=True)
    references: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    dynamic: list[dict[str, Any]] = []
    decorators: list[dict[str, Any]] = []
    module_main: list[dict[str, Any]] = []
    modules: dict[str, str] = {}
    for record in inventory["files"]:
        if record.get("kind") != "regular" or PurePosixPath(
            record["path"]
        ).suffix not in {
            ".py",
            ".pyi",
        }:
            continue
        content = _read_exact(root, record)
        try:
            tree = ast.parse(content.decode("utf-8", "strict"), filename=record["path"])
        except (UnicodeDecodeError, SyntaxError):
            continue
        usage = _Usage(record["path"])
        usage.visit(tree)
        references.extend(usage.references)
        imports.extend(usage.imports)
        dynamic.extend(usage.dynamic)
        decorators.extend(usage.decorators)
        module_main.extend(usage.module_main)
        module = _module_for_path(record["path"])
        if module:
            modules[module] = record["path"]

    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reference in references:
        by_name[reference["name"]].append(reference)
    imports_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for imported in imports:
        for module, path in modules.items():
            target = imported["module"].lstrip(".")
            if (
                target == module
                or target.startswith(module + ".")
                or module.startswith(target + ".")
            ):
                imports_by_path[path].append(imported)
    declared_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in inventory["declared_entrypoints"]:
        declared_by_path[entry["path"]].append(entry)

    records = []
    for hypothesis in hypotheses["findings"]:
        evidence: list[dict[str, Any]] = []
        symbol = _symbol_from_hypothesis(hypothesis)
        paths = hypothesis["paths"]
        for path in paths:
            for entry in declared_by_path.get(path, []):
                evidence.append(
                    {
                        **entry,
                        "entrypoint_kind": entry["kind"],
                        "kind": "declared-entrypoint-file",
                    }
                )
            for imported in imports_by_path.get(path, []):
                evidence.append({"kind": "module-import", **imported})
        if symbol:
            for entry in inventory["declared_entrypoints"]:
                if entry["target"].endswith(":" + symbol) or entry["target"].endswith(
                    "." + symbol
                ):
                    evidence.append(
                        {
                            **entry,
                            "entrypoint_kind": entry["kind"],
                            "kind": "declared-entrypoint-symbol",
                        }
                    )
            for decorator in decorators:
                if decorator["symbol"] == symbol:
                    evidence.append({"kind": "decorated-symbol", **decorator})
            defining_path = paths[0] if paths else ""
            defining_line = hypothesis.get("detail", {}).get("line")
            for reference in by_name.get(symbol, []):
                if (
                    reference["path"] != defining_path
                    or reference["line"] != defining_line
                ):
                    evidence.append({"kind": "name-reference", **reference})
            for call in dynamic:
                if symbol in call["literals"]:
                    evidence.append({"kind": "dynamic-string-reference", **call})
        unique = {sha256_bytes(canonical_bytes(item)): item for item in evidence}
        bounded = [unique[key] for key in sorted(unique)[:100]]
        records.append(
            {
                "hypothesis_id": hypothesis["id"],
                "hypothesis_state": "OBSERVED",
                "counterevidence_state": "PRESENT" if bounded else "UNKNOWN",
                "evidence": bounded,
                "evidence_truncated": len(unique) > 100,
                "runtime_trace_available": False,
                "authority_granted": False,
                "cleanup_permitted": False,
            }
        )

    present = sum(item["counterevidence_state"] == "PRESENT" for item in records)
    unknown = len(records) - present
    return seal_document(
        {
            "schema": COUNTEREVIDENCE_SCHEMA,
            "authority": "read-only-counterevidence",
            "authority_granted": False,
            "cleanup_permitted": False,
            "inventory": {
                "path": str(inventory_path.resolve(strict=True)),
                "file_sha256": sha256_bytes(inventory_raw),
                "receipt_sha256": inventory["receipt_sha256"],
            },
            "hypotheses": {
                "path": str(hypotheses_path.resolve(strict=True)),
                "file_sha256": sha256_bytes(hypotheses_raw),
                "receipt_sha256": hypotheses["receipt_sha256"],
            },
            "entrypoint_model": {
                "declared": inventory["declared_entrypoints"],
                "module_main_guards": sorted(
                    module_main, key=lambda item: (item["path"], item["line"])
                ),
                "decorators": sorted(
                    decorators,
                    key=lambda item: (item["path"], item["line"], item["symbol"]),
                ),
                "dynamic_calls": sorted(
                    dynamic, key=lambda item: (item["path"], item["line"], item["call"])
                ),
                "imports": sorted(
                    imports,
                    key=lambda item: (
                        item["path"],
                        item["line"],
                        item["module"],
                        item["name"],
                    ),
                ),
                "runtime_trace_available": False,
            },
            "records": sorted(records, key=lambda item: item["hypothesis_id"]),
            "summary": {
                "hypotheses": len(records),
                "counterevidence_present": present,
                "counterevidence_unknown": unknown,
                "declared_entrypoints": len(inventory["declared_entrypoints"]),
                "module_main_guards": len(module_main),
                "decorated_symbols": len(decorators),
                "dynamic_calls": len(dynamic),
                "imports": len(imports),
            },
        }
    )


def render_counterevidence_report(payload: Mapping[str, Any]) -> str:
    summary = payload["summary"]
    return "\n".join(
        [
            "# GIGA Archaeology entrypoint and dynamic-use counterevidence",
            "",
            f"- Hypotheses inspected: {summary['hypotheses']}",
            f"- Counterevidence present: {summary['counterevidence_present']}",
            f"- Counterevidence unknown: {summary['counterevidence_unknown']}",
            f"- Declared entrypoints: {summary['declared_entrypoints']}",
            f"- Module-main guards: {summary['module_main_guards']}",
            f"- Decorated symbols: {summary['decorated_symbols']}",
            f"- Dynamic-use calls: {summary['dynamic_calls']}",
            f"- Import records: {summary['imports']}",
            f"- Receipt SHA-256: `{payload['receipt_sha256']}`",
            "",
            "`PRESENT` is counterevidence against cleanup. `UNKNOWN` is not evidence of absence.",
            "This document changes no hypothesis lifecycle state and grants no cleanup authority.",
            "",
        ]
    )


def write_counterevidence(
    inventory_path: Path, hypotheses_path: Path, output: Path
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    if output.exists() or output.is_symlink():
        raise CounterevidenceError(
            "counterevidence output directory must not already exist"
        )
    payload = build_counterevidence(inventory_path, hypotheses_path)
    output.mkdir(parents=True, mode=0o700)
    try:
        write_atomic(output / "counterevidence.json", canonical_bytes(payload))
        write_atomic(
            output / "COUNTEREVIDENCE_REPORT.md",
            render_counterevidence_report(payload).encode("utf-8"),
        )
    except EvidenceError as exc:
        raise CounterevidenceError(str(exc)) from exc
    return payload
