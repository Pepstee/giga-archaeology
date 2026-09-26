from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from modules.operations.archaeology.evidence import canonical_bytes, seal_document
from modules.operations.archaeology.governance_map import (
    GovernanceMapError,
    exact_json_path_references,
    explicit_markdown_path_references,
    governed_markdown_headings,
    strict_json_object,
)
from modules.operations.archaeology.mapper import query_mapper, refresh_mapper
from modules.operations.archaeology.navigation_inventory import (
    refresh_navigation_inventory,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


@pytest.fixture()
def governance_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "<redacted-email>")
    (root / "architecture").mkdir()
    (root / "architecture/DECISIONS.md").write_text(
        "# Decisions\n\n"
        "## REQ-001 Preserve exact evidence\n\n"
        "### Rationale\n"
        "A similar sentence without an explicit identifier creates no declaration.\n\n"
        "```markdown\n"
        "## Hidden decision inside fence\n"
        "`src/hidden.py`\n"
        "```\n\n"
        "## Implementation constraints\n"
        "Use `src/app.py` and [schema](contracts/example.schema.json).\n"
        "Retired `missing/removed.py`.\n"
        "See [this decision](DECISIONS.md).\n",
        encoding="utf-8",
    )
    (root / "contracts").mkdir()
    (root / "contracts/example.schema.json").write_text(
        json.dumps({"schema": "fixture.schema.v1", "type": "object"}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    source = root / "src/app.py"
    source.write_text("def capability():\n    return True\n", encoding="utf-8")
    (root / "work_orders").mkdir()
    work_order = root / "work_orders/WO-001.json"
    work_order.write_text(
        json.dumps(
            {"schema": "giga.work-order.v1", "id": "WO-001", "status": "ADMITTED"},
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    work_order_sha = hashlib.sha256(work_order.read_bytes()).hexdigest()
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    receipt_dir = root / "receipts/WO-001"
    receipt_dir.mkdir(parents=True)
    valid = seal_document(
        {
            "schema": "giga.test-attestation.v1",
            "status": "PASS",
            "authority_granted": False,
            "external_path": "/private/tmp/not-a-repository-path",
            "missing_paths": ["missing/removed.py"],
            "source_path": "contracts/example.schema.json",
            "work_order_sha256": work_order_sha,
            "payload": [{"path": "src/app.py", "sha256": source_sha}],
        }
    )
    (receipt_dir / "attestation.json").write_bytes(canonical_bytes(valid))
    invalid = dict(valid)
    invalid["receipt_sha256"] = "0" * 64
    (receipt_dir / "invalid-attestation.json").write_bytes(canonical_bytes(invalid))
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "governance fixture")
    return root


def _compile(root: Path, tmp_path: Path):
    inventory = tmp_path / "inventory"
    mapper = tmp_path / "mapper"
    refresh_navigation_inventory(root, inventory)
    return mapper, refresh_mapper(inventory, mapper)


def test_m09_explicit_ids_and_strict_documents_are_navigable_without_prose_links(
    governance_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(governance_repository, tmp_path)
    assert run.manifest["counts"]["explicit_governed_declarations"] == 1
    assert run.manifest["counts"]["governed_markdown_headings"] == 4
    result = query_mapper(mapper, "REQ-001", maps=("requirements_decisions",))
    declaration = next(
        item for item in result["results"] if item["kind"] == "GOVERNED_DECLARATION"
    )
    assert declaration["attributes"]["line"] == 3
    assert declaration["attributes"]["prose_body_parsed"] is False
    assert result["coverage"][0]["details"]["prose_similarity_links"] is False
    similar = query_mapper(mapper, "similar sentence", maps=("requirements_decisions",))
    assert similar["results"] == []


def test_m52_governed_heading_hierarchy_is_exact_navigable_and_non_authorizing(
    governance_repository: Path, tmp_path: Path
) -> None:
    raw = (governance_repository / "architecture/DECISIONS.md").read_bytes()
    headings = governed_markdown_headings(raw)
    assert [heading["title"] for heading in headings] == [
        "Decisions",
        "REQ-001 Preserve exact evidence",
        "Rationale",
        "Implementation constraints",
    ]
    assert [heading["parent_ordinal"] for heading in headings] == [None, 0, 1, 0]
    assert headings[2]["line"] == 5
    assert (
        raw[headings[2]["span"]["byte_start"] : headings[2]["span"]["byte_end"]]
        == b"### Rationale"
    )

    mapper, run = _compile(governance_repository, tmp_path)
    assert run.manifest["counts"]["governed_heading_hierarchy_links"] == 3
    assert run.manifest["counts"]["governed_heading_declaration_links"] == 1
    result = query_mapper(mapper, "Rationale", maps=("requirements_decisions",))
    heading = next(
        item for item in result["results"] if item["kind"] == "GOVERNED_HEADING"
    )
    assert heading["truth_class"] == "PROVEN"
    assert heading["attributes"]["heading_text_is_authority"] is False
    assert heading["attributes"]["prose_body_parsed"] is False
    assert heading["source"]["location"]["line_start"] == 5
    assert (
        heading["source"]["location"]["byte_start"] == headings[2]["span"]["byte_start"]
    )
    relations = heading["facts"]["relations"]
    assert any(
        item["direction"] == "INCOMING"
        and item["predicate"] == "HEADING_CONTAINS_HEADING"
        and item["other"]["qualified_name"].endswith("#heading:1")
        for item in relations
    )
    assert any(item["predicate"] == "DOCUMENT_CONTAINS_HEADING" for item in relations)
    hidden = query_mapper(
        mapper, "Hidden decision inside fence", maps=("requirements_decisions",)
    )
    assert hidden["results"] == []

    declaration_result = query_mapper(
        mapper, "REQ-001", maps=("requirements_decisions",), fact_limit=50
    )
    declaration_heading = next(
        item
        for item in declaration_result["results"]
        if item["kind"] == "GOVERNED_HEADING" and item["attributes"]["line"] == 3
    )
    assert any(
        relation["predicate"] == "HEADING_DECLARES_EXPLICIT_ID"
        for relation in declaration_heading["facts"]["relations"]
    )


def test_m53_explicit_paths_resolve_to_current_facts_without_governance_inference(
    governance_repository: Path, tmp_path: Path
) -> None:
    raw = (governance_repository / "architecture/DECISIONS.md").read_bytes()
    references = explicit_markdown_path_references(raw)
    assert [item["normalized_path"] for item in references] == [
        "src/app.py",
        "contracts/example.schema.json",
        "missing/removed.py",
        "DECISIONS.md",
    ]
    assert [item["syntax"] for item in references] == [
        "INLINE_CODE",
        "MARKDOWN_LINK_DESTINATION",
        "INLINE_CODE",
        "MARKDOWN_LINK_DESTINATION",
    ]
    assert all(item["normalized_path"] != "src/hidden.py" for item in references)
    assert (
        raw[references[0]["span"]["byte_start"] : references[0]["span"]["byte_end"]]
        == b"src/app.py"
    )

    mapper, run = _compile(governance_repository, tmp_path)
    assert run.manifest["counts"]["governed_markdown_path_references"] == 4
    assert run.manifest["counts"]["governed_markdown_path_references_resolved"] == 3
    assert run.manifest["counts"]["governed_markdown_path_references_unresolved"] == 1
    assert run.manifest["counts"]["governed_markdown_path_references_ambiguous"] == 0
    assert run.manifest["counts"]["governed_path_reference_heading_links"] == 4
    assert run.manifest["counts"]["governed_path_reference_module_links"] == 1

    result = query_mapper(
        mapper, "src/app.py", maps=("requirements_decisions",), fact_limit=50
    )
    reference = next(
        item for item in result["results"] if item["kind"] == "GOVERNED_PATH_REFERENCE"
    )
    assert reference["attributes"]["resolution"] == "EXACT_CURRENT_INVENTORY_PATH"
    assert reference["attributes"]["governance_binding_claimed"] is False
    assert reference["attributes"]["implementation_satisfaction_claimed"] is False
    assert reference["source"]["location"]["line_start"] == 14
    predicates = {relation["predicate"] for relation in reference["facts"]["relations"]}
    assert "DOCUMENT_CONTAINS_EXPLICIT_PATH_REFERENCE" in predicates
    assert "HEADING_CONTAINS_EXPLICIT_PATH_REFERENCE" in predicates
    assert "RESOLVES_TO_CURRENT_OWNERSHIP_PATH" in predicates
    assert "RESOLVES_TO_CURRENT_PYTHON_MODULE" in predicates

    missing = query_mapper(
        mapper, "missing/removed.py", maps=("requirements_decisions",)
    )
    missing_reference = next(
        item for item in missing["results"] if item["kind"] == "GOVERNED_PATH_REFERENCE"
    )
    assert (
        missing_reference["attributes"]["resolution"]
        == "UNRESOLVED_CURRENT_INVENTORY_PATH"
    )
    assert all(
        relation["predicate"] != "RESOLVES_TO_CURRENT_OWNERSHIP_PATH"
        for relation in missing_reference["facts"]["relations"]
    )

    sibling = query_mapper(mapper, "DECISIONS.md", maps=("requirements_decisions",))
    sibling_reference = next(
        item
        for item in sibling["results"]
        if item["kind"] == "GOVERNED_PATH_REFERENCE"
        and item["attributes"]["normalized_path"] == "DECISIONS.md"
    )
    assert sibling_reference["attributes"]["resolution_candidates"] == [
        "DECISIONS.md",
        "architecture/DECISIONS.md",
    ]
    assert sibling_reference["attributes"]["resolved_path"] == (
        "architecture/DECISIONS.md"
    )


def test_m54_governed_json_paths_resolve_by_pointer_without_authority_inference(
    governance_repository: Path, tmp_path: Path
) -> None:
    receipt_path = governance_repository / "receipts/WO-001/attestation.json"
    value = strict_json_object(receipt_path.read_bytes())
    references = exact_json_path_references(value)
    assert [item["json_pointer"] for item in references] == [
        "/missing_paths/0",
        "/payload/0/path",
        "/source_path",
    ]
    assert [item["normalized_path"] for item in references] == [
        "missing/removed.py",
        "src/app.py",
        "contracts/example.schema.json",
    ]
    assert all(item["syntax"] == "JSON_PATH_FIELD" for item in references)
    assert all(
        item["literal"] != "/private/tmp/not-a-repository-path" for item in references
    )

    mapper, run = _compile(governance_repository, tmp_path)
    assert run.manifest["counts"]["governed_json_path_references"] == 6
    assert run.manifest["counts"]["governed_json_path_references_resolved"] == 4
    assert run.manifest["counts"]["governed_json_path_references_unresolved"] == 2
    assert run.manifest["counts"]["governed_json_path_reference_module_links"] == 2

    result = query_mapper(
        mapper,
        "source_path contracts/example.schema.json",
        maps=("requirements_decisions",),
        fact_limit=50,
    )
    reference = next(
        item
        for item in result["results"]
        if item["kind"] == "GOVERNED_JSON_PATH_REFERENCE"
        and item["attributes"]["json_pointer"] == "/source_path"
    )
    assert reference["attributes"]["resolution"] == "EXACT_CURRENT_INVENTORY_PATH"
    assert reference["attributes"]["governance_binding_claimed"] is False
    assert reference["attributes"]["implementation_satisfaction_claimed"] is False
    predicates = {relation["predicate"] for relation in reference["facts"]["relations"]}
    assert "DOCUMENT_CONTAINS_EXPLICIT_JSON_PATH_REFERENCE" in predicates
    assert "RESOLVES_TO_CURRENT_OWNERSHIP_PATH" in predicates

    missing = query_mapper(
        mapper, "missing/removed.py", maps=("requirements_decisions",)
    )
    missing_reference = next(
        item
        for item in missing["results"]
        if item["kind"] == "GOVERNED_JSON_PATH_REFERENCE"
    )
    assert missing_reference["attributes"]["resolution"] == (
        "UNRESOLVED_CURRENT_INVENTORY_PATH"
    )
    assert all(
        not relation["predicate"].startswith("RESOLVES_TO_CURRENT_")
        for relation in missing_reference["facts"]["relations"]
    )


def test_m09_valid_receipt_binds_exact_documents_and_files_but_status_is_only_claimed(
    governance_repository: Path, tmp_path: Path
) -> None:
    mapper, run = _compile(governance_repository, tmp_path)
    assert run.manifest["counts"]["evidence_valid_self_hashes"] == 1
    assert run.manifest["counts"]["exact_governed_document_links"] >= 1
    assert run.manifest["counts"]["exact_evidence_payload_bindings"] == 1
    result = query_mapper(
        mapper, "attestation.json", maps=("evidence_claims",), fact_limit=50
    )
    receipt = next(
        item
        for item in result["results"]
        if item["qualified_name"] == "receipts/WO-001/attestation.json"
    )
    assert receipt["attributes"]["self_hash_state"] == "VALID"
    status = next(
        fact
        for fact in receipt["facts"]["observations"]
        if fact["predicate"] == "DOCUMENT_CLAIMS_STATUS"
    )
    assert status["truth_class"] == "OBSERVED"
    assert status["value"] == {
        "authoritative_outcome": False,
        "self_hash_state": "VALID",
        "status": "PASS",
    }
    predicates = {fact["predicate"] for fact in receipt["facts"]["relations"]}
    assert "EXACT_HASH_REFERENCES_DOCUMENT" in predicates
    assert "BINDS_EXACT_CURRENT_FILE" in predicates
    assert (
        result["coverage"][0]["details"]["document_status_is_verified_outcome"] is False
    )


def test_m53_root_and_document_relative_path_collision_refuses_resolution(
    governance_repository: Path, tmp_path: Path
) -> None:
    (governance_repository / "DECISIONS.md").write_text(
        "# Different root document\n", encoding="utf-8"
    )
    mapper, run = _compile(governance_repository, tmp_path)
    assert run.manifest["counts"]["governed_markdown_path_references_ambiguous"] == 1
    result = query_mapper(
        mapper, "DECISIONS.md", maps=("requirements_decisions",), fact_limit=50
    )
    reference = next(
        item
        for item in result["results"]
        if item["kind"] == "GOVERNED_PATH_REFERENCE"
        and item["attributes"]["normalized_path"] == "DECISIONS.md"
    )
    assert reference["attributes"]["resolution"] == ("AMBIGUOUS_CURRENT_INVENTORY_PATH")
    assert reference["attributes"]["resolved_path"] is None
    assert all(
        not relation["predicate"].startswith("RESOLVES_TO_CURRENT_")
        for relation in reference["facts"]["relations"]
    )


def test_m09_invalid_self_hash_and_duplicate_json_fail_closed(
    governance_repository: Path, tmp_path: Path
) -> None:
    mapper, _run = _compile(governance_repository, tmp_path)
    result = query_mapper(
        mapper, "invalid-attestation.json", maps=("evidence_claims",), fact_limit=50
    )
    receipt = result["results"][0]
    assert receipt["attributes"]["self_hash_state"] == "INVALID"
    assert all(
        fact["predicate"] != "PROVES_CLAIM" for fact in receipt["facts"]["relations"]
    )
    with pytest.raises(GovernanceMapError, match="duplicate governed JSON key"):
        strict_json_object(b'{"schema":"one","schema":"two"}')
