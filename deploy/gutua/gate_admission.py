#!/usr/bin/env python3
"""Machine gate between findings and mutable repair dispatch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


APPROVING_DECISIONS = {
    "CONTINUE",
    "REPAIR_WITHIN_SCOPE",
    "APPROVE_SCOPE_EXCEPTION",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decide(
    findings_path: Path,
    ruling_path: Path | None,
    receipt_path: Path | None,
) -> tuple[bool, str]:
    findings = json.loads(findings_path.read_text(encoding="utf-8"))
    expansions = [
        finding
        for finding in findings.get("findings", [])
        if finding.get("status", "open") == "open"
        and finding.get("classification") == "ARCHITECTURE_EXPANSION"
    ]
    if not expansions:
        return True, "no open ARCHITECTURE_EXPANSION finding"
    if ruling_path is None or receipt_path is None:
        return False, "Fable ruling and receipt required"

    ruling = json.loads(ruling_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "giga.fable-gate-receipt.v1":
        return False, "invalid Fable receipt schema"
    if receipt.get("ruling_sha256") != digest(ruling_path):
        return False, "Fable ruling hash does not match receipt"
    if ruling.get("decision") not in APPROVING_DECISIONS:
        return False, f"Fable decision {ruling.get('decision')!r} does not admit repair"

    finding_ids = {str(finding.get("id")) for finding in expansions}
    ratified_ids = {str(value) for value in ruling.get("ratified_finding_ids", [])}
    if not finding_ids <= ratified_ids:
        missing = sorted(finding_ids - ratified_ids)
        return False, f"open expansions lack exact Fable ratification: {missing}"
    return True, "all open architecture expansions have hash-bound Fable ratification"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--findings", required=True, type=Path)
    parser.add_argument("--ruling", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    admitted, reason = decide(args.findings, args.ruling, args.receipt)
    print(json.dumps({"admitted": admitted, "reason": reason}, sort_keys=True))
    return 0 if admitted else 42


if __name__ == "__main__":
    raise SystemExit(main())
