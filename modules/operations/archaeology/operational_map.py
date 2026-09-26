"""Closed deterministic classifiers for M05 operational map facts.

These helpers classify source declarations only.  They never claim that a database, artifact,
workflow or deployment exists at runtime.  The deliberately small SQL grammar prefers explicit
unsupported coverage over guessing.
"""

from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

from .evidence import canonical_bytes, sha256_bytes


OPERATIONAL_POLICY_VERSION = "giga.archaeologist.operational-policy.v1"
SQL_LITERAL_GRAMMAR = "sqlite-literal-single-statement.v1"
BUILD_ROLE_POLICY = "giga-build-path-roles.v1"

_IDENTIFIER = r'(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][A-Za-z0-9_$.]*)'
_CREATE_TABLE = re.compile(
    rf"^CREATE\s+(?:TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<table>{_IDENTIFIER})\b",
    re.IGNORECASE | re.DOTALL,
)
_ALTER_TABLE = re.compile(
    rf"^ALTER\s+TABLE\s+(?P<table>{_IDENTIFIER})\b", re.IGNORECASE | re.DOTALL
)
_DROP_TABLE = re.compile(
    rf"^DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?P<table>{_IDENTIFIER})\b",
    re.IGNORECASE | re.DOTALL,
)
_INSERT = re.compile(
    rf"^INSERT\s+(?:OR\s+\w+\s+)?INTO\s+(?P<table>{_IDENTIFIER})\b",
    re.IGNORECASE | re.DOTALL,
)
_UPDATE = re.compile(
    rf"^UPDATE\s+(?:OR\s+\w+\s+)?(?P<table>{_IDENTIFIER})\b",
    re.IGNORECASE | re.DOTALL,
)
_DELETE = re.compile(
    rf"^DELETE\s+FROM\s+(?P<table>{_IDENTIFIER})\b", re.IGNORECASE | re.DOTALL
)
_FROM_OR_JOIN = re.compile(
    rf"\b(?:FROM|JOIN)\s+(?P<table>{_IDENTIFIER})\b", re.IGNORECASE | re.DOTALL
)
_LEADING_COMMENT = re.compile(r"\A(?:\s|--[^\n]*(?:\n|\Z)|/\*.*?\*/)*", re.DOTALL)

_BUILD_EXACT_NAMES = {
    "BUNDLE.json": "BUNDLE_MANIFEST",
    "Cargo.lock": "DEPENDENCY_LOCK",
    "Cargo.toml": "SOURCE_MANIFEST",
    "Containerfile": "CONTAINER_BUILD",
    "Dockerfile": "CONTAINER_BUILD",
    "Makefile": "BUILD_SCRIPT",
    "go.mod": "SOURCE_MANIFEST",
    "go.sum": "DEPENDENCY_LOCK",
    "package-lock.json": "DEPENDENCY_LOCK",
    "package.json": "SOURCE_MANIFEST",
    "poetry.lock": "DEPENDENCY_LOCK",
    "pyproject.toml": "SOURCE_MANIFEST",
    "requirements.txt": "DEPENDENCY_MANIFEST",
    "uv.lock": "DEPENDENCY_LOCK",
}
_SAFE_DECLARATION_KEYS = {
    "activated",
    "activation",
    "artifact_sha256",
    "candidate_commit",
    "candidate_tree",
    "payload_sha256",
    "product_commit",
    "product_tree",
    "schema",
    "selected",
    "selector_sha256",
    "source_commit",
    "source_tree",
    "status",
}


def _normalized_identifier(value: str) -> str:
    if value[:1] == value[-1:] and value[:1] in {'"', "`"}:
        value = value[1:-1]
    elif value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return value.casefold()


def parse_sql_literal(value: object) -> dict[str, Any] | None:
    """Parse one conservative literal SQL statement without executing it."""

    if (
        not isinstance(value, str)
        or not value
        or "\x00" in value
        or len(value) > 1_000_000
    ):
        return None
    statement = _LEADING_COMMENT.sub("", value).strip()
    if statement.endswith(";"):
        statement = statement[:-1].rstrip()
    if not statement or ";" in statement:
        return None
    patterns = (
        (_CREATE_TABLE, "SCHEMA_WRITE"),
        (_ALTER_TABLE, "SCHEMA_WRITE"),
        (_DROP_TABLE, "SCHEMA_WRITE"),
        (_INSERT, "WRITE"),
        (_UPDATE, "WRITE"),
        (_DELETE, "WRITE"),
    )
    for pattern, operation in patterns:
        match = pattern.match(statement)
        if match is not None:
            return {
                "grammar": SQL_LITERAL_GRAMMAR,
                "operation": operation,
                "statement_sha256": sha256_bytes(value.encode("utf-8")),
                "tables": [_normalized_identifier(match.group("table"))],
            }
    if re.match(r"^SELECT\b", statement, re.IGNORECASE):
        tables = sorted(
            {
                _normalized_identifier(match.group("table"))
                for match in _FROM_OR_JOIN.finditer(statement)
            }
        )
        if tables:
            return {
                "grammar": SQL_LITERAL_GRAMMAR,
                "operation": "READ",
                "statement_sha256": sha256_bytes(value.encode("utf-8")),
                "tables": tables,
            }
    return None


def build_asset_role(path: str) -> str | None:
    """Return a deterministic source/build role; never a deployment status."""

    pure = PurePosixPath(path)
    name = pure.name
    if name in _BUILD_EXACT_NAMES:
        return _BUILD_EXACT_NAMES[name]
    if path.startswith(".github/workflows/") and pure.suffix in {".yaml", ".yml"}:
        return "CI_WORKFLOW"
    if path.startswith("deploy/releases/"):
        if pure.suffix == ".sha256":
            return "RELEASE_CHECKSUM"
        if pure.suffix == ".json":
            return "RELEASE_DECLARATION"
    if path.startswith("deploy/") and pure.suffix in {
        ".json",
        ".plist",
        ".yaml",
        ".yml",
    }:
        return "DEPLOYMENT_DECLARATION"
    if path.endswith((".tar.gz", ".tgz", ".whl", ".zip")):
        return "PACKAGE_ARTIFACT"
    return None


def _closed_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def safe_build_declarations(path: str, raw: bytes) -> list[dict[str, Any]]:
    """Extract an allowlisted declaration projection from safe release manifests."""

    if len(raw) > 1_000_000 or not (
        PurePosixPath(path).name == "BUNDLE.json" or path.startswith("deploy/releases/")
    ):
        return []
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_closed_object)
    except (UnicodeError, json.JSONDecodeError, ValueError):
        return []
    found: list[dict[str, Any]] = []

    def visit(value: object, key_path: tuple[str, ...] = ()) -> None:
        if isinstance(value, Mapping):
            for key in sorted(value):
                visit(value[key], (*key_path, key))
            return
        if (
            key_path
            and key_path[-1] in _SAFE_DECLARATION_KEYS
            and isinstance(value, (str, int, bool))
            and not isinstance(value, float)
        ):
            found.append({"key_path": ".".join(key_path), "value": value})

    visit(payload)
    return found


OPERATIONAL_POLICY_SHA256 = sha256_bytes(
    canonical_bytes(
        {
            "build_exact_names": _BUILD_EXACT_NAMES,
            "build_role_policy": BUILD_ROLE_POLICY,
            "declaration_keys": sorted(_SAFE_DECLARATION_KEYS),
            "policy": OPERATIONAL_POLICY_VERSION,
            "sql_grammar": SQL_LITERAL_GRAMMAR,
        }
    )
)
