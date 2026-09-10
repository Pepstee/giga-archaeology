#!/usr/bin/env python3
"""Deterministically audit the one registered Telegram proposal execution seam.

This is a static, evidence-bound check. It does not execute the provider, grant authority,
or claim coverage of any other GIGA entry point.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from twin_core.execution_policy import ExecutionPolicyError, load_registry  # noqa: E402


AUDIT_SCHEMA = "giga.execution-bypass-audit.v1"
CAPABILITY_ID = "telegram-memory-proposal"
CALLER_ID = "scripts.jarvis_telegram:_process_update"
JARVIS_PATH = "scripts/jarvis_telegram.py"
PIPELINE_PATH = "twin_core/telegram_pipeline.py"
AUDITED_PATHS = (JARVIS_PATH, PIPELINE_PATH)
PROVIDER_MODULE = "twin_core.provider_adapters"
RULES = (
    "jarvis-exact-provider-import",
    "jarvis-single-provider-call-inside-worker",
    "jarvis-single-policy-decision-inside-shadow-route",
    "jarvis-process-event-binds-worker-and-shadow-route",
    "pipeline-has-no-provider-import",
    "public-corpus-guard-before-internal-forwarding",
    "jarvis-public-entrypoint-import",
    "pipeline-single-shadow-observer-before-receipt-before-provider-boundary-before-worker",
)


class BypassAuditError(ValueError):
    """A mechanically provable mismatch in the audited execution seam."""

    def __init__(self, reason: str, message: str):
        super().__init__(f"[{reason}] {message}")
        self.reason = reason


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bound_source(
    root: Path, relative: str, evidence: Mapping[str, Mapping[str, Any]]
) -> tuple[bytes, ast.Module]:
    record = evidence.get(relative)
    if record is None:
        raise BypassAuditError(
            "BYPASS_SOURCE_UNBOUND",
            f"audit source is not capability evidence: {relative}",
        )
    root = root.resolve()
    candidate = Path(relative)
    if (
        candidate.is_absolute()
        or candidate.as_posix() != relative
        or any(part in {".", ".."} for part in candidate.parts)
    ):
        raise BypassAuditError(
            "BYPASS_PATH_INVALID", f"audit source path is not canonical: {relative}"
        )
    declared = root
    for part in candidate.parts:
        declared /= part
        if declared.is_symlink():
            raise BypassAuditError(
                "BYPASS_PATH_SYMLINK", f"audit source contains a symlink: {relative}"
            )
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise BypassAuditError(
            "BYPASS_PATH_ESCAPE", f"audit source escapes root: {relative}"
        ) from exc
    if not resolved.is_file():
        raise BypassAuditError(
            "BYPASS_SOURCE_MISSING", f"audit source is not a regular file: {relative}"
        )
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise BypassAuditError(
            "BYPASS_SOURCE_UNREADABLE", f"audit source is unreadable: {relative}"
        ) from exc
    current = {"path": relative, "sha256": _sha256(raw), "bytes": len(raw)}
    if current != record:
        raise BypassAuditError(
            "BYPASS_SOURCE_DRIFT",
            f"audit source differs from capability evidence: {relative}",
        )
    try:
        tree = ast.parse(raw, filename=relative)
    except (SyntaxError, ValueError) as exc:
        raise BypassAuditError(
            "BYPASS_SOURCE_INVALID", f"audit source is not valid Python: {relative}"
        ) from exc
    return raw, tree


def _functions(tree: ast.AST, name: str) -> list[ast.FunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]


def _one_function(tree: ast.AST, name: str, *, source: str) -> ast.FunctionDef:
    matches = _functions(tree, name)
    if len(matches) != 1:
        raise BypassAuditError(
            "BYPASS_FUNCTION_MISMATCH",
            f"{source} must define exactly one {name}; found {len(matches)}",
        )
    return matches[0]


def _named_calls(tree: ast.AST, name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
    ]


def _attribute_calls(tree: ast.AST, attribute: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attribute
    ]


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    matches = [item.value for item in call.keywords if item.arg == name]
    if len(matches) > 1:
        raise BypassAuditError(
            "BYPASS_CALL_BINDING", f"call contains duplicate {name} keyword"
        )
    return matches[0] if matches else None


def _provider_import_count(tree: ast.AST) -> tuple[int, int]:
    """Return exact direct-symbol imports and every other provider-module import."""
    direct = 0
    other = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            other += sum(
                alias.name == PROVIDER_MODULE
                or alias.name.startswith(f"{PROVIDER_MODULE}.")
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == PROVIDER_MODULE or (
                node.level and module == "provider_adapters"
            ):
                for alias in node.names:
                    if alias.name == "run_proposal" and alias.asname is None:
                        direct += 1
                    else:
                        other += 1
            elif module == "twin_core":
                other += sum(alias.name == "provider_adapters" for alias in node.names)
    return direct, other


def _audit_jarvis(tree: ast.Module) -> dict[str, Any]:
    process_imports = [alias for node in ast.walk(tree)
                       if isinstance(node, ast.ImportFrom)
                       and node.module == "twin_core.telegram_pipeline"
                       for alias in node.names
                       if alias.name == "process_event"]
    private_refs = [node for node in ast.walk(tree)
                    if (isinstance(node, ast.alias) and node.name == "_process_event")
                    or (isinstance(node, ast.Name) and node.id == "_process_event")
                    or (isinstance(node, ast.Attribute) and node.attr == "_process_event")]
    if len(process_imports) != 1 or process_imports[0].asname or private_refs:
        raise BypassAuditError("BYPASS_PUBLIC_ENTRYPOINT", "Jarvis must use the public process_event import")
    provider_imports, other_provider_imports = _provider_import_count(tree)
    if provider_imports != 1 or other_provider_imports:
        raise BypassAuditError(
            "BYPASS_PROVIDER_IMPORT",
            "Jarvis must import exactly unaliased run_proposal from the registered provider module",
        )

    worker = _one_function(tree, "_worker", source=JARVIS_PATH)
    provider_calls = _named_calls(tree, "run_proposal")
    worker_provider_calls = _named_calls(worker, "run_proposal")
    if len(provider_calls) != 1 or provider_calls != worker_provider_calls:
        raise BypassAuditError(
            "BYPASS_PROVIDER_CALL",
            "run_proposal must be called exactly once and only inside _worker",
        )

    shadow = _one_function(tree, "_shadow_route", source=JARVIS_PATH)
    all_decisions = _named_calls(tree, "decide_route")
    shadow_decisions = _named_calls(shadow, "decide_route")
    if len(all_decisions) != 1 or all_decisions != shadow_decisions:
        raise BypassAuditError(
            "BYPASS_POLICY_CALL",
            "decide_route must be called exactly once and only inside _shadow_route",
        )

    process_update = _one_function(tree, "_process_update", source=JARVIS_PATH)
    process_calls = _named_calls(tree, "process_event")
    local_process_calls = _named_calls(process_update, "process_event")
    if len(process_calls) != 1 or process_calls != local_process_calls:
        raise BypassAuditError(
            "BYPASS_PROCESS_CALL",
            "process_event must be called exactly once and only inside _process_update",
        )
    process_call = process_calls[0]
    worker_binding = _keyword(process_call, "worker")
    if not isinstance(worker_binding, ast.Name) or worker_binding.id != "_worker":
        raise BypassAuditError(
            "BYPASS_WORKER_BINDING", "process_event worker must be bound to _worker"
        )
    observer = _keyword(process_call, "route_observer")
    if not isinstance(observer, ast.Lambda):
        raise BypassAuditError(
            "BYPASS_OBSERVER_BINDING",
            "process_event must receive a route-observer lambda",
        )
    observer_calls = _named_calls(observer, "_shadow_route")
    if len(observer_calls) != 1 or not isinstance(observer.body, ast.Call):
        raise BypassAuditError(
            "BYPASS_OBSERVER_BINDING",
            "route-observer lambda must call only _shadow_route",
        )
    if len(observer.args.args) != 1 or observer.args.args[0].arg != "instructions":
        raise BypassAuditError(
            "BYPASS_OBSERVER_BINDING", "route-observer lambda signature drifted"
        )
    call = observer_calls[0]
    if (
        len(call.args) != 2
        or call.keywords
        or not isinstance(call.args[0], ast.Name)
        or call.args[0].id != "event_id"
        or not isinstance(call.args[1], ast.Name)
        or call.args[1].id != "instructions"
    ):
        raise BypassAuditError(
            "BYPASS_OBSERVER_BINDING", "_shadow_route arguments drifted"
        )
    return {
        "provider_imports": 1,
        "provider_calls": 1,
        "policy_calls": 1,
        "process_calls": 1,
        "worker_binding": "_worker",
        "observer_binding": "_shadow_route",
    }


def _audit_public_corpus_guard(node: ast.FunctionDef) -> None:
    def fail(msg: str) -> None:
        raise ValueError(f"public corpus guard mismatch: {msg}")

    if node.decorator_list:
        fail("decorators not allowed")

    args = node.args
    if (args.posonlyargs or args.args or args.vararg or args.kwonlyargs
            or args.kw_defaults or args.defaults):
        fail("signature must have only **kwargs")
    if args.kwarg is None or args.kwarg.arg != "kwargs":
        fail("signature must have only **kwargs")

    body = node.body
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]  # optional docstring

    if len(body) != 2:
        fail("expected exactly two executable statements")
    access_stmt, forward_stmt = body

    if not (isinstance(access_stmt, ast.Expr) and isinstance(access_stmt.value, ast.Call)):
        fail("first statement must be a bare call")
    call = access_stmt.value
    if not (isinstance(call.func, ast.Name) and call.func.id == "_require_corpus_access"):
        fail("first statement must call _require_corpus_access")
    if call.args or call.keywords:
        fail("_require_corpus_access() takes no arguments")

    if not isinstance(forward_stmt, ast.Return):
        fail("second statement must be a return")
    value = forward_stmt.value
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
            and value.func.id == "_process_event"):
        fail("must return direct _process_event(**kwargs)")
    if value.args:
        fail("forwarding must have no positional arguments")
    if len(value.keywords) != 1:
        fail("forwarding must have exactly one **kwargs")
    kw = value.keywords[0]
    if kw.arg is not None or not (isinstance(kw.value, ast.Name) and kw.value.id == "kwargs"):
        fail("forwarding must be exactly **kwargs")


def _audit_pipeline(tree: ast.Module) -> dict[str, Any]:
    direct_provider_imports, other_provider_imports = _provider_import_count(tree)
    if direct_provider_imports or other_provider_imports:
        raise BypassAuditError(
            "BYPASS_PIPELINE_PROVIDER_IMPORT",
            "Telegram pipeline must not import the provider adapter",
        )

    public = _one_function(tree, "process_event", source=PIPELINE_PATH)
    try:
        _audit_public_corpus_guard(public)
    except ValueError as exc:
        raise BypassAuditError("BYPASS_PUBLIC_CORPUS_GUARD", str(exc)) from exc
    process = _one_function(tree, "_process_event", source=PIPELINE_PATH)
    all_observer_calls = _named_calls(tree, "route_observer")
    observer_calls = _named_calls(process, "route_observer")
    all_worker_calls = _named_calls(tree, "worker")
    worker_calls = _named_calls(process, "worker")
    if len(all_observer_calls) != 1 or all_observer_calls != observer_calls:
        raise BypassAuditError(
            "BYPASS_PIPELINE_OBSERVER_CALL",
            "process_event must call route_observer exactly once",
        )
    if len(all_worker_calls) != 1 or all_worker_calls != worker_calls:
        raise BypassAuditError(
            "BYPASS_PIPELINE_WORKER_CALL", "process_event must call worker exactly once"
        )

    route_receipts = []
    provider_receipts = []
    for call in _attribute_calls(process, "record_receipt"):
        operation = _keyword(call, "operation")
        if isinstance(operation, ast.Name) and operation.id == "route_operation":
            route_receipts.append(call)
        if (
            isinstance(operation, ast.Name)
            and operation.id == "PROVIDER_BOUNDARY_OPERATION"
        ):
            provider_receipts.append(call)
    if len(route_receipts) != 1:
        raise BypassAuditError(
            "BYPASS_PIPELINE_RECEIPT",
            "process_event must record exactly one shadow-route receipt",
        )
    if len(provider_receipts) != 1:
        raise BypassAuditError(
            "BYPASS_PIPELINE_PROVIDER_RECEIPT",
            "process_event must record exactly one provider-boundary receipt",
        )
    observer_line = observer_calls[0].lineno
    route_receipt_line = route_receipts[0].lineno
    provider_receipt_line = provider_receipts[0].lineno
    worker_line = worker_calls[0].lineno
    if not observer_line < route_receipt_line < provider_receipt_line < worker_line:
        raise BypassAuditError(
            "BYPASS_PIPELINE_ORDER",
            "shadow decision, route receipt and boundary receipt must precede the worker",
        )
    if _named_calls(process, "run_proposal"):
        raise BypassAuditError(
            "BYPASS_PIPELINE_PROVIDER_CALL",
            "Telegram pipeline must not call run_proposal directly",
        )
    return {
        "observer_calls": 1,
        "shadow_receipts": 1,
        "provider_boundary_receipts": 1,
        "worker_calls": 1,
        "source_order": [
            "route_observer",
            "shadow_receipt",
            "provider_boundary_receipt",
            "worker",
        ],
        "provider_imports": 0,
        "direct_provider_calls": 0,
    }


def audit(root: Path) -> dict[str, Any]:
    """Audit and hash-bind the single observe-only Telegram proposal seam."""
    root = root.resolve()
    try:
        registry, registry_raw = load_registry(root)
    except ExecutionPolicyError as exc:
        raise BypassAuditError(
            "BYPASS_REGISTRY_INVALID", f"execution registry failed closed: {exc.reason}"
        ) from exc
    capabilities = registry["capabilities"]
    matches = [item for item in capabilities if item["capability_id"] == CAPABILITY_ID]
    if len(capabilities) != 1 or len(matches) != 1:
        raise BypassAuditError(
            "BYPASS_CAPABILITY_SCOPE",
            "v1 audit requires exactly the one Telegram proposal capability",
        )
    capability = matches[0]
    if capability["approved_callers"] != [CALLER_ID]:
        raise BypassAuditError(
            "BYPASS_CALLER_SCOPE", "approved caller differs from the audited seam"
        )
    evidence = {item["path"]: item for item in capability["evidence"]}
    source_bytes: dict[str, bytes] = {}
    trees: dict[str, ast.Module] = {}
    for relative in AUDITED_PATHS:
        source_bytes[relative], trees[relative] = _bound_source(
            root, relative, evidence
        )

    findings = {
        JARVIS_PATH: _audit_jarvis(trees[JARVIS_PATH]),
        PIPELINE_PATH: _audit_pipeline(trees[PIPELINE_PATH]),
    }

    for relative, before in source_bytes.items():
        if (root / relative).read_bytes() != before:
            raise BypassAuditError(
                "BYPASS_SOURCE_RACE", f"audit source changed during scan: {relative}"
            )
    capability_sha256 = _sha256(_canonical_bytes(capability))
    receipt: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA,
        "status": "pass",
        "mode": "static-observe-only-audit",
        "coverage_claim": "one-telegram-memory-proposal-seam-only",
        "capability_id": CAPABILITY_ID,
        "caller_id": CALLER_ID,
        "registry_sha256": _sha256(registry_raw),
        "capability_sha256": capability_sha256,
        "audited_sources": [
            {
                "path": relative,
                "sha256": _sha256(source_bytes[relative]),
                "bytes": len(source_bytes[relative]),
            }
            for relative in AUDITED_PATHS
        ],
        "rules": list(RULES),
        "findings": findings,
        "execution_authorized": False,
        "authority_granted": False,
        "command_execution": False,
        "provider_called": False,
        "runtime_enforcement": False,
    }
    receipt["receipt_sha256"] = _sha256(_canonical_bytes(receipt))
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--json", action="store_true", help="emit canonical JSON")
    args = parser.parse_args(argv)
    try:
        receipt = audit(args.root)
    except BypassAuditError as exc:
        error = {"status": "blocked", "reason_code": exc.reason, "message": str(exc)}
        print(json.dumps(error, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 2
    if args.json:
        print(_canonical_bytes(receipt).decode("utf-8"))
    else:
        print(
            "Execution bypass audit PASS: "
            f"{receipt['coverage_claim']} ({receipt['receipt_sha256']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
