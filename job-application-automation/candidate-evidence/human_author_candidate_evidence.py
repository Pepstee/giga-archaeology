"""Human-triggered, deterministic materialisation of approved JAA evidence.

Codex may stage this script and its reviewed packet, but must not execute it.
The named human authority executes it personally after exact-statement review.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: human_author_candidate_evidence.py PACKET TARGET")
    packet_path = Path(sys.argv[1]).resolve()
    target = Path(sys.argv[2]).resolve()
    packet_text = packet_path.read_text(encoding="utf-8")
    packet = json.loads(packet_text)
    if packet.get("human_authority") != "gutu.artiom444@gmail.com":
        raise SystemExit("unexpected human authority")
    statements = packet.get("statements")
    if not isinstance(statements, list) or len(statements) != 18:
        raise SystemExit("expected exactly 18 approved statements")
    valid_proofs = {
        "credential",
        "employment_record",
        "external_outcome",
        "portfolio_artifact",
        "test_result",
        "verified_claim",
        "work_artifact",
    }
    records = []
    seen = set()
    for item in statements:
        evidence_id = str(item["id"])
        statement = str(item["statement"])
        proof_class = str(item["proof_class"])
        if evidence_id in seen or proof_class not in valid_proofs or not statement.strip():
            raise SystemExit(f"invalid approved statement: {evidence_id}")
        seen.add(evidence_id)
        records.append(
            {
                "evidence_id": evidence_id,
                "version": 1,
                "statement": statement,
                "demonstrates": [f"operator-approved:{evidence_id}"],
                "proof_class": proof_class,
                "approval_state": "approved",
                "epistemic_state": "evidence",
                "verification_decision": "approved",
                "verification_method": "personal review and exact wording approval by Artiom Gutu",
                "content_sha256": sha256_text(statement),
                "valid_until": None,
                "negative": False,
                "claim_lineage": [],
                "evidence_provenance": {
                    "provenance_id": f"operator-approval-20260728:{evidence_id}",
                    "source_kind": str(item["kind"]),
                    "source_locator": str(packet_path),
                    "source_sha256": sha256_text(packet_text),
                    "human_authority": packet["human_authority"],
                    "approved_at": packet["approved_at"],
                },
            }
        )
    document = {
        "schema_version": "jaa05.candidate-evidence.v1",
        "human_authority": packet["human_authority"],
        "status": "HUMAN_AUTHORED_AND_APPROVED",
        "source_packet_sha256": sha256_text(packet_text),
        "records": records,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing production evidence: {target}")
    target.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"AUTHORED {target}")
    print(f"RECORDS {len(records)}")
    print(f"SHA256 {hashlib.sha256(target.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
