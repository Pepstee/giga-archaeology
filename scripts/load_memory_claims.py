#!/usr/bin/env python3
"""Validate and load Tier-3 claims into the derived unified-memory database."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    db = args.db.expanduser().resolve()
    claims_path = args.claims.expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve()
    payload = json.loads(claims_path.read_text(encoding="utf-8"))
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("claims file must contain a non-empty claims list")
    claim_ids = [item.get("claim_id") for item in claims]
    if len(set(claim_ids)) != len(claim_ids) or any(not item for item in claim_ids):
        raise ValueError("claim IDs must be present and unique")

    connection = sqlite3.connect(db)
    connection.row_factory = sqlite3.Row
    record_to_pk = {
        row["record_id"]: row["message_pk"]
        for row in connection.execute("SELECT record_id,message_pk FROM messages")
    }
    missing = sorted({
        evidence["record_id"]
        for claim in claims
        for evidence in claim.get("evidence", [])
        if evidence.get("record_id") not in record_to_pk
    })
    if missing:
        raise ValueError(f"{len(missing)} missing evidence record IDs: {missing[:10]}")

    with connection:
        connection.execute("DELETE FROM claim_evidence")
        connection.execute("DELETE FROM memory_claims")
        for claim in claims:
            confidence = float(claim["confidence"])
            if not 0 <= confidence <= 1:
                raise ValueError(f"{claim['claim_id']}: confidence outside 0..1")
            connection.execute(
                """
                INSERT INTO memory_claims(
                    claim_id,claim_type,label,description,valid_from,valid_to,
                    confidence,status,method,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    claim["claim_id"],
                    claim["claim_type"],
                    claim["label"],
                    claim["description"],
                    claim.get("valid_from"),
                    claim.get("valid_to"),
                    confidence,
                    claim["status"],
                    claim["method"],
                    payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
                ),
            )
            for evidence in claim.get("evidence", []):
                connection.execute(
                    "INSERT INTO claim_evidence(claim_id,message_pk,evidence_role) VALUES (?,?,?)",
                    (
                        claim["claim_id"],
                        record_to_pk[evidence["record_id"]],
                        evidence["role"],
                    ),
                )
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    claim_count = connection.execute("SELECT COUNT(*) FROM memory_claims").fetchone()[0]
    evidence_count = connection.execute("SELECT COUNT(*) FROM claim_evidence").fetchone()[0]
    view_count = connection.execute("SELECT COUNT(*) FROM tier3_memory_map").fetchone()[0]
    connection.close()
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["database_sha256"] = file_digest(db)
    manifest["tier3"] = {
        "claims_source": str(claims_path),
        "claims_source_sha256": file_digest(claims_path),
        "claim_count": claim_count,
        "claim_evidence_edges": evidence_count,
        "tier3_view_rows": view_count,
        "status": "evidence-linked hypotheses awaiting operator calibration",
    }
    manifest["integrity_check"] = integrity
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    db.chmod(0o600)
    manifest_path.chmod(0o600)
    print(json.dumps({
        "database": str(db),
        "database_sha256": manifest["database_sha256"],
        "claims": claim_count,
        "evidence_edges": evidence_count,
        "tier3_view_rows": view_count,
        "integrity_check": integrity,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
