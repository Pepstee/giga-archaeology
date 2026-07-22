"""Integrity checks for immutable source evidence.

The baseline itself is deliberately a plain sha256sum-compatible file.  This module only
reads the named artefacts; it never repairs, rewrites or normalises them.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_hash_baseline(root: Path, baseline: Path) -> dict[str, Any]:
    """Verify every relative path in ``baseline`` without modifying any source file."""
    root = root.resolve()
    baseline = baseline.resolve()
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    if not baseline.exists():
        return {
            "ok": False,
            "baseline": str(baseline),
            "files": results,
            "errors": ["integrity baseline is missing"],
        }

    for number, raw in enumerate(baseline.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or not SHA256.fullmatch(parts[0]):
            errors.append(f"line {number}: expected '<sha256>  <relative path>'")
            continue
        expected, relative = parts[0], parts[1].strip()
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append(f"line {number}: path escapes GIGA root: {relative}")
            continue
        if not candidate.is_file():
            results.append({
                "path": relative,
                "expected_sha256": expected,
                "actual_sha256": None,
                "ok": False,
                "error": "missing or not a regular file",
            })
            continue
        actual = sha256_file(candidate)
        results.append({
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "ok": actual == expected,
        })

    return {
        "ok": not errors and bool(results) and all(item["ok"] for item in results),
        "baseline": str(baseline),
        "files": results,
        "errors": errors,
    }
