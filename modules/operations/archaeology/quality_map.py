"""Deterministic M06 test and quality artifact classifiers."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

from .evidence import canonical_bytes, sha256_bytes


QUALITY_POLICY_VERSION = "giga.archaeologist.quality-policy.v3"

QUALITY_CHECK_STATUSES = frozenset({"PASS", "FAIL", "REJECT", "ERROR", "SKIP"})
MAX_RECEIPT_PROOFS = 500
MAX_PROOF_TEXT = 4096

_QUALITY_EXACT_NAMES = {
    ".coveragerc": "COVERAGE_CONFIG",
    ".ruff.toml": "QUALITY_CONFIG",
    "coverage.json": "COVERAGE_REPORT",
    "mypy.ini": "QUALITY_CONFIG",
    "pytest.ini": "TEST_CONFIG",
    "ruff.toml": "QUALITY_CONFIG",
    "tox.ini": "TEST_CONFIG",
}


def is_python_test_path(path: str) -> bool:
    pure = PurePosixPath(path)
    return (
        "tests" in pure.parts
        or pure.name.startswith("test_")
        or pure.stem.endswith("_test")
    )


def quality_asset_role(path: str) -> str | None:
    pure = PurePosixPath(path)
    if pure.name in _QUALITY_EXACT_NAMES:
        return _QUALITY_EXACT_NAMES[pure.name]
    if pure.suffix == ".sarif":
        return "QUALITY_REPORT_METADATA"
    return None


def _bounded_text(value: Any, *, ceiling: int = MAX_PROOF_TEXT) -> str | None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > ceiling
        or "\x00" in value
    ):
        return None
    return value


def _quality_check_family(command: Sequence[str]) -> str:
    folded = [value.casefold() for value in command]
    names = [PurePosixPath(value).name.casefold() for value in command]
    if "pytest" in names or any(value.endswith("pytest") for value in names):
        return "PYTEST"
    if "ruff" in names:
        index = names.index("ruff")
        operation = folded[index + 1] if index + 1 < len(folded) else ""
        if operation == "check":
            return "RUFF_CHECK"
        if operation == "format":
            return "RUFF_FORMAT"
        return "RUFF_OTHER"
    if "compileall" in folded or any(
        value.endswith("compileall.py") for value in folded
    ):
        return "PYTHON_COMPILE"
    if "git" in names and "diff" in folded and "--check" in folded:
        return "GIT_DIFF_CHECK"
    if any("validate_foundations.py" in value for value in folded):
        return "FOUNDATION_GATE"
    return "OTHER_CHECK"


def command_repository_path_candidates(command: Sequence[str]) -> list[dict[str, Any]]:
    """Return only exact lexical repository-relative path arguments.

    This does not resolve a process cwd or claim that the named bytes were executed.
    The mapper must separately match candidates against its current inventory.
    """

    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for argument_index, argument in enumerate(command):
        if not isinstance(argument, str) or not argument or argument.startswith("-"):
            continue
        path_text, separator, selector = argument.partition("::")
        if not path_text or path_text == "." or "\\" in path_text:
            continue
        path = PurePosixPath(path_text)
        if (
            path.is_absolute()
            or path.as_posix() != path_text
            or ("/" not in path_text and not path.suffix)
            or any(part in {".", ".."} for part in path.parts)
        ):
            continue
        selector_value = selector if separator else None
        if selector_value is not None and _bounded_text(selector_value) is None:
            continue
        identity = (path_text, selector_value)
        if identity in seen:
            continue
        seen.add(identity)
        candidates.append(
            {
                "argument_index": argument_index,
                "path": path_text,
                "selector": selector_value,
            }
        )
    return candidates


def parse_receipt_quality_claims(value: Mapping[str, Any]) -> dict[str, Any]:
    """Project bounded proof claims without asserting that commands actually ran."""

    raw_proofs = value.get("proofs")
    if not isinstance(raw_proofs, list):
        return {"claims": [], "rejected_items": 0, "proof_array_supported": False}
    if len(raw_proofs) > MAX_RECEIPT_PROOFS:
        return {
            "claims": [],
            "rejected_items": len(raw_proofs),
            "proof_array_supported": False,
        }
    claims: list[dict[str, Any]] = []
    rejected = 0
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_proofs):
        if not isinstance(item, Mapping):
            rejected += 1
            continue
        proof_id = _bounded_text(item.get("id"), ceiling=256)
        status = item.get("status")
        result = _bounded_text(item.get("result"))
        raw_command = item.get("command")
        command = (
            list(raw_command)
            if isinstance(raw_command, list)
            and 1 <= len(raw_command) <= 128
            and all(_bounded_text(part) is not None for part in raw_command)
            else None
        )
        if (
            proof_id is None
            or proof_id in seen_ids
            or status not in QUALITY_CHECK_STATUSES
            or result is None
            or command is None
        ):
            rejected += 1
            continue
        seen_ids.add(proof_id)
        claims.append(
            {
                "index": index,
                "proof_id": proof_id,
                "reported_status": status,
                "reported_result": result,
                "command": command,
                "command_sha256": sha256_bytes(canonical_bytes(command)),
                "command_repository_path_candidates": (
                    command_repository_path_candidates(command)
                ),
                "check_family": _quality_check_family(command),
                "execution_independently_verified": False,
                "source_receipt_self_hash_required": True,
            }
        )
    return {
        "claims": claims,
        "rejected_items": rejected,
        "proof_array_supported": True,
    }


def _closed_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_coverage_json(raw: bytes) -> dict[str, Any] | None:
    """Return a bounded coverage.py JSON projection, never source content."""

    if len(raw) > 20_000_000:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_closed_object)
    except (UnicodeError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, Mapping) or not isinstance(
        payload.get("files"), Mapping
    ):
        return None
    files = payload["files"]
    if len(files) > 100_000:
        return None
    projected = []
    allowed_summary = {
        "covered_lines",
        "excluded_lines",
        "missing_lines",
        "num_statements",
        "percent_covered",
        "percent_covered_display",
    }
    for path in sorted(files):
        record = files[path]
        if (
            not isinstance(path, str)
            or not path
            or "\x00" in path
            or not isinstance(record, Mapping)
            or not isinstance(record.get("summary"), Mapping)
        ):
            return None
        summary: dict[str, Any] = {}
        for key in sorted(allowed_summary):
            value = record["summary"].get(key)
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                continue
            summary[key] = value
        if "num_statements" not in summary:
            return None
        projected.append({"path": path, "summary": summary})
    meta = payload.get("meta")
    safe_meta = {}
    if isinstance(meta, Mapping):
        for key in ("branch_coverage", "format", "version"):
            value = meta.get(key)
            if isinstance(value, (str, int, bool)) and not isinstance(value, float):
                safe_meta[key] = value
    return {
        "files": projected,
        "meta": safe_meta,
        "source_tree_binding": "ABSENT_UNLESS_SEPARATELY_PROVEN",
    }


QUALITY_POLICY_SHA256 = sha256_bytes(
    canonical_bytes(
        {
            "coverage_projection": "coverage.py-json-summary-only",
            "exact_names": _QUALITY_EXACT_NAMES,
            "policy": QUALITY_POLICY_VERSION,
            "receipt_quality_claims": {
                "current_inventory_path_binding": (
                    "lexical-relative-path-match-not-execution-source-binding"
                ),
                "execution_independently_verified": False,
                "max_proofs": MAX_RECEIPT_PROOFS,
                "statuses": sorted(QUALITY_CHECK_STATUSES),
            },
            "test_path_rules": ["tests-part", "test_-prefix", "_test-suffix"],
        }
    )
)
