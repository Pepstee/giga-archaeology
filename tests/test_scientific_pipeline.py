from __future__ import annotations

import hashlib
import json
import sqlite3
import warnings
from pathlib import Path

import pytest

from twin_core import scientific_screening
from twin_core.scientific_pipeline_cli import main as pipeline_main

from twin_core.scientific_campaign import provider_campaign_jobs, validate_campaign
from twin_core.scientific_evidence import ScientificEvidenceError, payload_hash
from twin_core.scientific_fulltext import (
    extract_pmc_xml,
    fetch_europe_pmc_xml,
    plan_full_text,
)
from twin_core.scientific_query_compiler import (
    COMPILED_SCHEMA,
    compile_manifest,
    compile_provider_query,
    embed_compiled_queries,
    validate_ontology,
    validate_search_spec,
)
from twin_core.scientific_readiness import assess_screening_readiness
from twin_core.scientific_review_state import (
    LLM_PROPOSAL_SCHEMA,
    ScientificReviewStore,
)
from twin_core.scientific_saturation import evaluate_saturation
from twin_core.scientific_screening import (
    inspect_historical_rds_performance,
    prepare_historical_ris_corpus,
    write_historical_ris_corpus,
    simulate_active_learning,
    _query_lookup,
    apply_duplicate_decisions,
    deterministic_exclusion_sample,
    exact_deduplicate,
    extract_features,
    negative_control_report,
    normalise_doi,
    normalise_title,
    possible_duplicate_pairs,
    project_group,
    propose_eligibility,
    validate_exclusion_audit,
)


FIXED_TIME = "2026-07-28T18:00:00+00:00"


def _ontology() -> dict:
    return validate_ontology(
        {
            "schema_version": "giga.scientific-search-ontology.v1",
            "ontology_id": "test-ontology",
            "version": "1",
            "conditions": {
                "acne_scar": {
                    "terms": ["atrophic acne scar", "acne scar"],
                    "subject_headings": ["Acne Vulgaris"],
                },
                "low_back_pain": {
                    "terms": ["low back pain"],
                    "subject_headings": ["Low Back Pain"],
                },
            },
            "interventions": {
                "microneedling": {
                    "terms": ["microneedling"],
                    "subject_headings": ["Microneedling"],
                }
            },
            "outcomes": {
                "severity": {
                    "terms": ["scar severity", "ECCA"],
                    "subject_headings": [],
                }
            },
        }
    )


def _spec() -> dict:
    return validate_search_spec(
        {
            "schema_version": "giga.scientific-search-specification.v1",
            "campaign_id": "test-campaign",
            "ontology_id": "test-ontology",
            "ontology_version": "1",
            "queries": [
                {
                    "id": "Q1",
                    "condition_concepts": ["acne_scar"],
                    "intervention_concepts": ["microneedling"],
                    "outcome_concepts": ["severity"],
                    "require_outcomes": False,
                }
            ],
            "negative_controls": [
                {
                    "id": "NC1",
                    "condition_concepts": ["low_back_pain"],
                    "intervention_concepts": ["microneedling"],
                    "outcome_concepts": [],
                    "require_outcomes": False,
                    "expected_disposition": "auto_exclude",
                }
            ],
        },
        ontology=_ontology(),
    )


def _campaign() -> dict:
    return {
        "schema_version": "giga.scientific-search-campaign.v1",
        "campaign_id": "test-campaign",
        "protocol": "protocol.md",
        "created_at": FIXED_TIME,
        "execution_state": "test",
        "defaults": {
            "endpoint": "search/papers",
            "corpus": "pubmed",
            "search_mode": "semantic",
            "max_results": 10,
            "filters": {"retracted": "exclude_retracted"},
        },
        "queries": [
            {
                "id": "Q1",
                "phase": 1,
                "question": "Does microneedling improve acne scars?",
            }
        ],
        "completion_rule": "Stop after test.",
    }


def _record(
    source_id: str,
    *,
    title: str = "Microneedling for atrophic acne scars",
    provider: str = "pubmed",
    doi: str | None = None,
    year: int = 2024,
    abstract: str | None = "Human patients had improved scar severity.",
) -> dict:
    value = {
        "schema_version": "giga.scientific-canonical-record.v1",
        "source_record_id": source_id,
        "acquisition_id": "a" * 64,
        "provider": provider,
        "endpoint": "search/papers",
        "kind": "paper",
        "query_id": "Q1",
        "negative_control": False,
        "title": title,
        "normalised_title": normalise_title(title),
        "abstract": abstract,
        "year": year,
        "doi": doi,
        "pmid": None,
        "pmcid": None,
        "nct_id": None,
        "authors": ["A Author"],
        "venue": "Journal",
        "publication_types": ["Randomized Controlled Trial"],
        "urls": [],
        "open_access_candidate": False,
        "retracted": False,
        "retrieved_at": FIXED_TIME,
        "raw_sha256": "b" * 64,
    }
    value["canonical_record_sha256"] = "c" * 64
    return value


def test_query_compiler_is_provider_specific_and_hashed() -> None:
    ontology, spec, campaign = _ontology(), _spec(), _campaign()
    pubmed = compile_provider_query("pubmed", spec["queries"][0], ontology)
    europe = compile_provider_query("europe_pmc", spec["queries"][0], ontology)
    assert '"Acne Vulgaris"[Mesh]' in pubmed
    assert '"microneedling"[tiab]' in pubmed
    assert 'TITLE_ABS:"microneedling"' in europe
    manifest = compile_manifest(
        campaign,
        ontology,
        spec,
        providers=["europe_pmc", "pubmed"],
    )
    assert manifest["schema_version"] == COMPILED_SCHEMA
    assert len(manifest["manifest_sha256"]) == 64
    assert len(manifest["queries"]) == 2


def test_compiled_campaign_forces_provider_expression() -> None:
    ontology, spec, campaign = _ontology(), _spec(), _campaign()
    manifest = compile_manifest(
        campaign,
        ontology,
        spec,
        providers=["europe_pmc"],
    )
    compiled = validate_campaign(embed_compiled_queries(campaign, manifest))
    job = provider_campaign_jobs(
        compiled["queries"],
        paper_providers=("europe_pmc",),
    )[0]
    assert job["request"]["query"].startswith("(")
    assert job["request"]["query"] != campaign["queries"][0]["question"]


def test_compiled_campaign_fails_if_selected_provider_has_no_expression() -> None:
    ontology, spec, campaign = _ontology(), _spec(), _campaign()
    manifest = compile_manifest(
        campaign,
        ontology,
        spec,
        providers=["europe_pmc"],
    )
    compiled = validate_campaign(embed_compiled_queries(campaign, manifest))
    with pytest.raises(ScientificEvidenceError, match="compiled provider query missing"):
        provider_campaign_jobs(
            compiled["queries"],
            paper_providers=("pubmed",),
        )


def test_query_compiler_fails_closed_for_wrong_concept_kind() -> None:
    payload = {
        "schema_version": "giga.scientific-search-specification.v1",
        "campaign_id": "test-campaign",
        "ontology_id": "test-ontology",
        "ontology_version": "1",
        "queries": [
            {
                "id": "Q1",
                "condition_concepts": ["microneedling"],
                "intervention_concepts": ["microneedling"],
                "outcome_concepts": [],
            }
        ],
        "negative_controls": [
            {
                "id": "NC1",
                "condition_concepts": ["low_back_pain"],
                "intervention_concepts": ["microneedling"],
                "outcome_concepts": [],
            }
        ],
    }
    with pytest.raises(ScientificEvidenceError, match="wrong-kind"):
        validate_search_spec(payload, ontology=_ontology())


def test_normalisation_and_exact_dedup_are_conservative() -> None:
    assert normalise_doi("HTTPS://DOI.ORG/10.1000/ABC.") == "10.1000/abc"
    assert normalise_title("Résumé—Skin!") == "resume skin"
    records = [
        _record("1" * 64, doi="10.1000/same", provider="europe_pmc"),
        _record("2" * 64, doi="10.1000/same", provider="pubmed"),
        _record(
            "3" * 64,
            title="Microneedling for a separate clinical outcome",
            doi="10.1000/other",
        ),
    ]
    assert sorted(len(group) for group in exact_deduplicate(records)) == [1, 2]


def test_fuzzy_duplicates_are_never_auto_merged() -> None:
    groups = [
        project_group(
            [
                _record(
                    "1" * 64,
                    title="Microneedling for atrophic acne scars: a trial",
                    doi="10.1000/one",
                )
            ]
        ),
        project_group(
            [
                _record(
                    "2" * 64,
                    title="Microneedling for atrophic acne scars - a trial",
                    doi="10.1000/two",
                )
            ]
        ),
    ]
    pairs = possible_duplicate_pairs(groups, threshold=0.9)
    assert len(pairs) == 1
    assert pairs[0]["auto_merged"] is False
    assert pairs[0]["disposition"] == "manual_review_required"


def test_human_duplicate_decision_can_merge_only_the_exact_hashed_pair() -> None:
    record_groups = [
        [
            _record(
                "1" * 64,
                title="Microneedling for atrophic acne scars: a trial",
                doi="10.1000/one",
            )
        ],
        [
            _record(
                "2" * 64,
                title="Microneedling for atrophic acne scars - a trial",
                doi="10.1000/two",
            )
        ],
    ]
    groups = [project_group(group) for group in record_groups]
    pairs = possible_duplicate_pairs(groups, threshold=0.9)
    document = {
        "schema_version": "giga.scientific-duplicate-decisions.v1",
        "campaign_id": "test-campaign",
        "pair_set_sha256": payload_hash(pairs),
        "decisions": [
            {
                "pair_sha256": pairs[0]["pair_sha256"],
                "decision": "same_study",
                "decided_by": "reviewer",
                "decided_at": FIXED_TIME,
                "evidence": {"reason": "Same title, author and trial."},
            }
        ],
    }
    merged, unresolved, report = apply_duplicate_decisions(
        record_groups,
        groups,
        pairs,
        document,
        campaign_id="test-campaign",
    )
    assert len(merged) == 1
    assert unresolved == []
    assert report["complete"] is True


def test_eligibility_rules_include_relevant_exclude_unrelated_and_queue_ambiguous() -> None:
    ontology, spec = _ontology(), _spec()
    relevant = project_group([_record("1" * 64)])
    features = extract_features(relevant, ontology)
    assert propose_eligibility(relevant, features, spec)["proposed_status"] == "auto_include"

    unrelated = project_group(
        [
            _record(
                "2" * 64,
                title="Adjunctive antipsychotics for depression",
                abstract="A human randomized clinical trial.",
            )
        ]
    )
    features = extract_features(unrelated, ontology)
    assert propose_eligibility(unrelated, features, spec)["proposed_status"] == "auto_exclude"

    ambiguous = project_group(
        [
            _record(
                "3" * 64,
                title="New treatment of acne scars",
                abstract=None,
            )
        ]
    )
    features = extract_features(ambiguous, ontology)
    assert propose_eligibility(ambiguous, features, spec)["proposed_status"] == "manual_review"


def test_exclusion_audit_sampling_is_deterministic() -> None:
    proposals = [
        {
            "group_id": f"{index:064x}",
            "proposed_status": "auto_exclude",
            "reason_codes": ["EX_TEST"],
            "title": f"Record {index}",
            "year": 2020,
        }
        for index in range(20)
    ]
    assert deterministic_exclusion_sample(
        proposals, per_reason=4
    ) == deterministic_exclusion_sample(proposals, per_reason=4)
    assert len(deterministic_exclusion_sample(proposals, per_reason=4)) == 4


def test_exclusion_audit_requires_complete_human_decisions(tmp_path: Path) -> None:
    expected = [
        {
            "group_id": "1" * 64,
            "title": "Unrelated record",
            "year": 2020,
        }
    ]
    completed = tmp_path / "completed.csv"
    completed.write_text(
        "group_id,title,year,sampled_reason_codes,human_audit_decision,"
        "human_audit_notes,audit_complete\n"
        f"{'1' * 64},Unrelated record,2020,\"[\"\"EX_TEST\"\"]\","
        "correct_exclusion,checked,True\n",
        encoding="utf-8",
    )
    report = validate_exclusion_audit(completed, expected)
    assert report["promotion_gate_passed"] is True
    completed.write_text(
        "group_id,title,year,sampled_reason_codes,human_audit_decision,"
        "human_audit_notes,audit_complete\n"
        f"{'1' * 64},Unrelated record,2020,\"[\"\"EX_TEST\"\"]\","
        "false_exclusion,missed,True\n",
        encoding="utf-8",
    )
    assert (
        validate_exclusion_audit(completed, expected)["promotion_gate_passed"]
        is False
    )


def test_negative_control_gate_requires_all_controls_to_be_excluded() -> None:
    group = {
        "group_id": "1" * 64,
        "negative_control": True,
    }
    passed = negative_control_report(
        [group],
        [
            {
                "group_id": group["group_id"],
                "proposed_status": "auto_exclude",
                "title": "Negative control",
            }
        ],
    )
    assert passed["promotion_gate_passed"] is True
    failed = negative_control_report(
        [group],
        [
            {
                "group_id": group["group_id"],
                "proposed_status": "manual_review",
                "title": "Negative control",
            }
        ],
    )
    assert failed["status"] == "fail"


def test_fulltext_plan_uses_lawful_routes_and_skips_exclusions() -> None:
    group = project_group(
        [
            {
                **_record("1" * 64, doi="10.1000/oa"),
                "pmcid": "PMC123",
                "urls": ["https://repository.example/paper.pdf"],
                "open_access_candidate": True,
            }
        ]
    )
    proposals = [
        {"group_id": group["group_id"], "proposed_status": "auto_include"}
    ]
    plan = plan_full_text([group], proposals)[0]
    route_types = [route["route_type"] for route in plan["routes"]]
    assert route_types[0] == "europe_pmc_fulltext_xml"
    assert "unpaywall_lookup" in route_types
    assert plan["paywall_circumvention_forbidden"] is True


def test_pmc_fetch_and_extraction_are_hash_bound(tmp_path: Path) -> None:
    xml = (
        b"<article><front><article-meta><title-group><article-title>Test paper"
        b"</article-title></title-group><abstract><p>Abstract text.</p></abstract>"
        b"</article-meta></front><body><sec><title>Results</title><p>Result text."
        b"</p></sec></body></article>"
    )
    destination = tmp_path / "PMC123.xml"
    receipt = fetch_europe_pmc_xml(
        "PMC123",
        destination,
        transport=lambda url, timeout: (xml, {"Content-Type": "application/xml"}),
    )
    assert receipt["full_text_status"] == "obtained_unappraised"
    assert receipt["sha256"]
    extraction = extract_pmc_xml(destination)
    assert extraction["source_sha256"] == receipt["sha256"]
    assert extraction["section_count"] >= 3
    assert extraction["full_text_verified"] is False


def test_pmc_fetch_rejects_entity_declarations(tmp_path: Path) -> None:
    with pytest.raises(ScientificEvidenceError, match="forbidden"):
        fetch_europe_pmc_xml(
            "PMC123",
            tmp_path / "bad.xml",
            transport=lambda url, timeout: (
                b'<!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]><article/>',
                {},
            ),
        )


def test_review_state_enforces_actor_boundaries_and_is_idempotent(tmp_path: Path) -> None:
    store = ScientificReviewStore(tmp_path / "review.sqlite3")
    group = "1" * 64
    first = store.transition(
        campaign_id="campaign",
        group_id=group,
        from_state=None,
        to_state="discovered",
        actor_kind="deterministic",
        reason_codes=["DISCOVERED_TEST"],
        evidence={"source": "fixture"},
        recorded_at=FIXED_TIME,
    )
    assert first[1] is True
    assert (
        store.transition(
            campaign_id="campaign",
            group_id=group,
            from_state=None,
            to_state="discovered",
            actor_kind="deterministic",
            reason_codes=["DISCOVERED_TEST"],
            evidence={"source": "fixture"},
            recorded_at=FIXED_TIME,
        )[1]
        is False
    )
    with pytest.raises(ScientificEvidenceError, match="cannot perform"):
        store.transition(
            campaign_id="campaign",
            group_id=group,
            from_state="discovered",
            to_state="triaged",
            actor_kind="human",
            reason_codes=["INVALID_ACTOR_TEST"],
            evidence={"source": "fixture"},
            recorded_at=FIXED_TIME,
        )
    assert store.audit()["ok"] is True


def test_duplicate_decision_is_append_only_and_conflicts_fail(tmp_path: Path) -> None:
    store = ScientificReviewStore(tmp_path / "review.sqlite3")
    pair = "4" * 64
    first = store.record_duplicate_decision(
        campaign_id="campaign",
        pair_sha256=pair,
        decision="different_study",
        decided_by="reviewer",
        evidence={"reason": "Different interventions."},
        decided_at=FIXED_TIME,
    )
    assert first[1] is True
    assert (
        store.record_duplicate_decision(
            campaign_id="campaign",
            pair_sha256=pair,
            decision="different_study",
            decided_by="reviewer",
            evidence={"reason": "Different interventions."},
            decided_at=FIXED_TIME,
        )[1]
        is False
    )
    with pytest.raises(ScientificEvidenceError, match="different immutable"):
        store.record_duplicate_decision(
            campaign_id="campaign",
            pair_sha256=pair,
            decision="same_study",
            decided_by="reviewer",
            evidence={"reason": "Changed mind."},
            decided_at=FIXED_TIME,
        )


def test_llm_proposal_never_changes_state_and_requires_verbatim_span(tmp_path: Path) -> None:
    store = ScientificReviewStore(tmp_path / "review.sqlite3")
    group = "2" * 64
    for from_state, to_state, reason in (
        (None, "discovered", "DISCOVERED_TEST"),
        ("discovered", "triaged", "TRIAGED_TEST"),
        ("triaged", "awaiting_review", "AMBIGUOUS_TEST"),
    ):
        store.transition(
            campaign_id="campaign",
            group_id=group,
            from_state=from_state,
            to_state=to_state,
            actor_kind="deterministic",
            reason_codes=[reason],
            evidence={"source": "fixture", "step": to_state},
            recorded_at=FIXED_TIME,
        )
    proposal = {
        "schema_version": LLM_PROPOSAL_SCHEMA,
        "campaign_id": "campaign",
        "group_id": group,
        "decision": "include",
        "reason_code": "LLM_RELEVANT",
        "rationale": "The supplied title names the target condition.",
        "evidence_spans": [
            {"field": "title", "exact_text": "atrophic acne scars"}
        ],
        "model": "test-model",
        "proposed_at": FIXED_TIME,
    }
    store.record_llm_proposal(
        proposal,
        source_metadata={
            "title": "Microneedling for atrophic acne scars",
            "abstract": None,
        },
    )
    assert store.current_states("campaign")[group] == "awaiting_review"
    assert store.counts("campaign")["llm_proposals"] == 1
    bad = {**proposal, "evidence_spans": [{"field": "title", "exact_text": "invented"}]}
    with pytest.raises(ScientificEvidenceError, match="not verbatim"):
        store.record_llm_proposal(
            bad,
            source_metadata={"title": "Microneedling", "abstract": None},
        )


def test_review_ledger_audit_detects_out_of_band_mutation(tmp_path: Path) -> None:
    store = ScientificReviewStore(tmp_path / "review.sqlite3")
    store.transition(
        campaign_id="campaign",
        group_id="3" * 64,
        from_state=None,
        to_state="discovered",
        actor_kind="deterministic",
        reason_codes=["DISCOVERED_TEST"],
        evidence={"source": "fixture"},
        recorded_at=FIXED_TIME,
    )
    connection = sqlite3.connect(store.database)
    connection.execute("DROP TRIGGER no_update_review_events")
    connection.execute(
        "UPDATE review_events SET evidence_json='{}' WHERE sequence=1"
    )
    connection.commit()
    connection.close()
    audit = store.audit()
    assert audit["ok"] is False
    assert any("evidence hash" in error for error in audit["errors"])


def test_published_llm_contract_matches_runtime_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (
            root
            / "contracts/scientific-llm-eligibility-proposal.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert schema["properties"]["schema_version"]["const"] == LLM_PROPOSAL_SCHEMA
    assert schema["additionalProperties"] is False


def _write_saturation_snapshot(
    directory: Path,
    *,
    snapshot_sha256: str,
    retrieval_records: int,
    candidates: list[tuple[str, list[str]]],
) -> Path:
    directory.mkdir(parents=True)
    groups: list[dict] = []
    proposals: list[dict] = []
    features: list[dict] = []
    for index, (identity, interventions) in enumerate(candidates):
        group_id = f"{index + 1:064x}"
        groups.append(
            {
                "group_id": group_id,
                "canonical_identity": identity,
            }
        )
        proposals.append(
            {
                "group_id": group_id,
                "proposed_status": "auto_include",
            }
        )
        features.append(
            {
                "group_id": group_id,
                "concepts": {"interventions": interventions},
            }
        )

    artifacts = {
        "dedup_groups": ("DEDUP_GROUPS.jsonl", groups),
        "eligibility": ("ELIGIBILITY_PROPOSALS.jsonl", proposals),
        "features": ("FEATURES.jsonl", features),
    }
    receipts: dict[str, dict[str, str]] = {}
    for name, (filename, rows) in artifacts.items():
        path = directory / filename
        text = "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        )
        path.write_text(text, encoding="utf-8")
        receipts[name] = {
            "path": filename,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
    summary = {
        "snapshot_payload_sha256": snapshot_sha256,
        "retrieval_records": retrieval_records,
        "artifacts": receipts,
    }
    summary_path = directory / "SCREENING_SUMMARY.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    return summary_path


def test_saturation_requires_distinct_cumulative_low_yield_snapshots(
    tmp_path: Path,
) -> None:
    candidates = [
        ("doi:10.1000/a", ["microneedling"]),
        ("pmid:123", ["microneedling"]),
    ]
    snapshots = [
        _write_saturation_snapshot(
            tmp_path / f"snapshot-{index}",
            snapshot_sha256=f"{index:064x}",
            retrieval_records=100 + index,
            candidates=candidates,
        )
        for index in (1, 2, 3)
    ]
    report = evaluate_saturation(snapshots)
    assert report["saturated"] is True
    assert all(item["pass"] for item in report["passes"][-2:])

    with pytest.raises(ScientificEvidenceError, match="distinct"):
        evaluate_saturation([snapshots[0], snapshots[0], snapshots[2]])


def test_screening_readiness_is_fail_closed_and_never_authorises_ranking(
    tmp_path: Path,
) -> None:
    campaign_id = "test-campaign"
    group_id = "9" * 64
    store = ScientificReviewStore(tmp_path / "review.sqlite3")
    for from_state, to_state, actor, reason in (
        (None, "discovered", "deterministic", "DISCOVERED_TEST"),
        ("discovered", "triaged", "deterministic", "TRIAGED_TEST"),
        ("triaged", "proposed_include", "deterministic", "PROPOSED_TEST"),
        ("proposed_include", "included", "human", "HUMAN_INCLUDED_TEST"),
    ):
        store.transition(
            campaign_id=campaign_id,
            group_id=group_id,
            from_state=from_state,
            to_state=to_state,
            actor_kind=actor,
            reason_codes=[reason],
            evidence={"source": "fixture", "state": to_state},
            recorded_at=FIXED_TIME,
        )

    report = assess_screening_readiness(
        main_summary={
            "campaign_id": campaign_id,
            "unmapped_records": 0,
            "unique_candidate_groups": 1,
            "duplicate_decisions": {"complete": True},
        },
        negative_control_summary={
            "negative_controls": {"promotion_gate_passed": True}
        },
        review_store=store,
        exclusion_audit_report={"promotion_gate_passed": True},
        saturation_report={"saturated": True},
    )
    assert report["screening_ready"] is True
    assert report["failed_gates"] == []
    assert report["full_text_appraisal_complete"] is False
    assert report["effectiveness_ranking_authorised"] is False

    blocked = assess_screening_readiness(
        main_summary={
            "campaign_id": campaign_id,
            "unmapped_records": 0,
            "unique_candidate_groups": 1,
            "duplicate_decisions": {"complete": True},
        },
        negative_control_summary={
            "negative_controls": {"promotion_gate_passed": True}
        },
        review_store=store,
        exclusion_audit_report=None,
        saturation_report=None,
    )
    assert blocked["screening_ready"] is False
    assert set(blocked["failed_gates"]) == {
        "exclusion_audit_pass",
        "search_saturation_pass",
    }


def test_porcine_collagen_material_is_not_mistaken_for_an_animal_study() -> None:
    record = _record(
        "8" * 64,
        title=(
            "Subcuticular incision versus porcine collagen filler "
            "for acne scars: a randomized split-face comparison"
        ),
        abstract=None,
    )
    record["compiled_query_retrieval"] = True
    group = project_group([record])
    features = extract_features(group, _ontology())
    proposal = propose_eligibility(group, features, _spec())
    assert proposal["proposed_status"] != "auto_exclude"
    assert "EX_NONHUMAN_ONLY" not in proposal["reason_codes"]


def test_editorial_type_conflicting_with_research_design_requires_review() -> None:
    record = _record(
        "7" * 64,
        title="Systematic review of microneedling for atrophic acne scars",
    )
    record["publication_types"] = ["Letter", "Systematic Review"]
    group = project_group([record])
    features = extract_features(group, _ontology())
    proposal = propose_eligibility(group, features, _spec())
    assert proposal["proposed_status"] == "manual_review"
    assert proposal["reason_codes"] == ["MR_NONRESEARCH_PUBLICATION_TYPE"]


def test_query_provenance_uses_request_limit_to_disambiguate_expressions() -> None:
    expression = 'TITLE_ABS:"acne scar"'
    campaign = {
        "defaults": {"max_results": 50},
        "queries": [
            {
                "id": "overview",
                "question": "Overview",
                "max_results": 100,
            },
            {
                "id": "primary",
                "question": "Primary",
                "max_results": 250,
            },
        ],
    }
    manifest = {
        "queries": [
            {
                "id": "overview",
                "negative_control": False,
                "provider_queries": {"europe_pmc": expression},
            },
            {
                "id": "primary",
                "negative_control": False,
                "provider_queries": {"europe_pmc": expression},
            },
        ]
    }
    lookup = _query_lookup(campaign, manifest)
    assert lookup[("europe_pmc", expression, 100)][0] == "overview"
    assert lookup[("europe_pmc", expression, 250)][0] == "primary"
    assert ("europe_pmc", expression, None) not in lookup


def test_control_only_ontology_concepts_do_not_pollute_main_features() -> None:
    record = _record(
        "6" * 64,
        title="Microneedling for acne scars and low back pain",
    )
    group = project_group([record])
    main_features = extract_features(group, _ontology(), _spec())
    assert "low_back_pain" not in main_features["concepts"]["conditions"]
    assert "microneedling" in main_features["concepts"]["interventions"]

    group["negative_control"] = True
    control_features = extract_features(group, _ontology(), _spec())
    assert "low_back_pain" in control_features["concepts"]["conditions"]


def _active_learning_fixture() -> tuple[list[dict], dict, list[str]]:
    ids = {letter: letter * 64 for letter in "abcdefg"}
    groups = [
        {"group_id": ids["a"], "title": "Unrelated endocrine review"},
        {"group_id": ids["c"], "title": "股票金融市场预测"},
        {"group_id": ids["f"], "title": "Unrelated computational model"},
        {"group_id": ids["b"], "title": "视黄醇临床改善光老化皱纹"},
        {"group_id": ids["g"], "title": "股票金融市场走势"},
        {"group_id": ids["d"], "title": "视黄醇临床治疗光老化"},
        {
            "group_id": ids["e"],
            "title": "视黄醇光老化临床研究 Retinoid clinical trial",
        },
    ]
    oracle = {
        "schema_version": "giga.scientific-active-learning-oracle.v1",
        "simulation_id": "screening-canary-fixture-r1",
        "simulation_only": True,
        "fully_labeled": True,
        "labels": [
            {"group_id": ids["a"], "label": "exclude"},
            {"group_id": ids["b"], "label": "include"},
            {"group_id": ids["c"], "label": "exclude"},
            {"group_id": ids["d"], "label": "include"},
            {"group_id": ids["e"], "label": "include"},
            {"group_id": ids["f"], "label": "exclude"},
            {"group_id": ids["g"], "label": "exclude"},
        ],
    }
    return groups, oracle, [ids["b"], ids["c"]]


def test_active_learning_simulation_is_multilingual_deterministic_and_non_authoritative() -> None:
    groups, oracle, seed_ids = _active_learning_fixture()
    result = simulate_active_learning(
        groups,
        oracle,
        seed_group_ids=seed_ids,
        maximum_labels=len(groups),
    )
    repeated = simulate_active_learning(
        groups,
        oracle,
        seed_group_ids=seed_ids,
        maximum_labels=len(groups),
    )
    assert result == repeated
    trace = result["active_learning"]["label_trace"]
    assert [entry["group_id"] for entry in trace] == [
        seed_ids[0],
        seed_ids[1],
        "d" * 64,
        "e" * 64,
    ]
    assert trace[2]["predicted_include_probability"] > 0.5
    assert result["active_learning"]["metrics"]["recall"] == 1.0
    assert result["active_learning"]["metrics"]["labels_to_target_recall"] == 4
    assert result["input_order_baseline"]["metrics"]["labels_to_target_recall"] == 7
    assert result["effect_vs_input_order"]["labels_saved_to_target_recall"] == 3
    assert result["oracle"]["labels_visible_to_ranker_before_selection"] is False
    assert result["authority"] == {
        "simulation_only": True,
        "model_may_prioritise_only": True,
        "model_may_not_decide_eligibility": True,
        "live_review_state_written": False,
        "effectiveness_ranking_authorised": False,
    }


def test_indexed_active_learning_score_matches_legacy_token_lookup() -> None:
    groups, oracle, seed_ids = _active_learning_fixture()
    rows = scientific_screening._active_learning_groups(groups)
    group_ids = [row["group_id"] for row in rows]
    labels = scientific_screening.validate_active_learning_oracle(
        oracle,
        group_ids=group_ids,
    )["labels"]
    tokens_by_group = {row["group_id"]: row["tokens"] for row in rows}
    token_ids_by_token = {
        token: index
        for index, token in enumerate(
            sorted({token for tokens in tokens_by_group.values() for token in tokens})
        )
    }
    model_state = scientific_screening._active_learning_model_state(
        labelled_ids=seed_ids,
        labels=labels,
        tokens_by_group=tokens_by_group,
        token_ids_by_token=token_ids_by_token,
    )
    for group_id, tokens in tokens_by_group.items():
        legacy_score = scientific_screening._active_learning_probability(
            tokens,
            model_state=model_state,
        )
        indexed_score = scientific_screening._indexed_active_learning_probability(
            tuple((token_ids_by_token[token], count) for token, count in tokens.items()),
            model_state=model_state,
        )
        assert indexed_score == legacy_score, group_id


def test_active_learning_builds_revealed_model_once_per_queue_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    groups, oracle, seed_ids = _active_learning_fixture()
    observed_calls: list[tuple[tuple[str, ...], bool, str | None]] = []
    original = scientific_screening._active_learning_model_state

    def observe_state(**kwargs: object) -> object:
        labelled_ids = kwargs["labelled_ids"]
        assert isinstance(labelled_ids, list)
        previous = kwargs["previous_model_state"]
        newly_labelled_id = kwargs["newly_labelled_id"]
        assert newly_labelled_id is None or isinstance(newly_labelled_id, str)
        observed_calls.append(
            (tuple(labelled_ids), previous is not None, newly_labelled_id)
        )
        return original(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(scientific_screening, "_active_learning_model_state", observe_state)
    result = simulate_active_learning(
        groups,
        oracle,
        seed_group_ids=seed_ids,
        maximum_labels=len(groups),
    )
    trace = result["active_learning"]["label_trace"]
    assert len(observed_calls) == len(trace) - len(seed_ids)
    assert observed_calls == [
        (tuple(seed_ids), False, None),
        ((*seed_ids, "d" * 64), True, "d" * 64),
    ]


def test_active_learning_simulation_fails_closed_for_incomplete_or_unbalanced_inputs() -> None:
    groups, oracle, seed_ids = _active_learning_fixture()
    incomplete = {**oracle, "labels": oracle["labels"][:-1]}
    with pytest.raises(ScientificEvidenceError, match="fully label exactly"):
        simulate_active_learning(groups, incomplete, seed_group_ids=seed_ids)
    with pytest.raises(ScientificEvidenceError, match="at least one include and one exclude"):
        simulate_active_learning(groups, oracle, seed_group_ids=[seed_ids[0]])


def test_active_learning_simulation_cli_writes_inspectable_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    groups, oracle, seed_ids = _active_learning_fixture()
    groups_path = tmp_path / "DEDUP_GROUPS.jsonl"
    groups_path.write_text(
        "".join(json.dumps(group, ensure_ascii=False) + "\n" for group in groups),
        encoding="utf-8",
    )
    oracle_path = tmp_path / "ORACLE.json"
    oracle_path.write_text(json.dumps(oracle, ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "SIMULATION.json"
    assert (
        pipeline_main(
            [
                "simulate-active-learning",
                str(groups_path),
                str(oracle_path),
                str(output),
                "--seed-group-id",
                seed_ids[0],
                "--seed-group-id",
                seed_ids[1],
            ]
        )
        == 0
    )
    emitted = json.loads(capsys.readouterr().out)
    assert json.loads(output.read_text(encoding="utf-8")) == emitted
    assert emitted["simulation_id"] == oracle["simulation_id"]
    assert emitted["authority"]["live_review_state_written"] is False


def test_historical_ris_preparation_is_label_blind_and_runs_through_the_public_cli(
    tmp_path: Path,
) -> None:
    included = tmp_path / "included.ris"
    excluded = tmp_path / "excluded.ris"
    included.write_text(
        "TY  - JOUR\n"
        "TI  - Included evidence\n"
        "AB  - Relevant evidence begins here.\n"
        "      It continues on this line.\n"
        "DO  - https://doi.org/10.1000/included\n"
        "PY  - 2024\n"
        "A1  - Included Author\n"
        "UR  - https://example.test/included\n"
        "ER  -\n",
        encoding="utf-8",
    )
    excluded.write_text(
        "TY  - JOUR\n"
        "T1  - Excluded evidence\n"
        "N2  - Irrelevant evidence.\n"
        "DO  - 10.1000/excluded\n"
        "PY  - 2023\n"
        "AU  - Excluded Author\n"
        "ER  -\n",
        encoding="utf-8",
    )
    corpus = prepare_historical_ris_corpus(
        included,
        excluded,
        simulation_id="ris-fixture",
        source_id="fixture-source",
    )
    assert corpus["receipt"]["source_records"] == {
        "total": 2,
        "included": 1,
        "excluded": 1,
        "with_title": 2,
        "with_abstract": 2,
        "with_doi": 2,
    }
    assert corpus["receipt"]["deduplicated_groups"]["cross_label_conflict_count"] == 0
    assert all("label" not in group for group in corpus["groups"])
    swapped = prepare_historical_ris_corpus(
        excluded,
        included,
        simulation_id="ris-fixture",
        source_id="fixture-source",
    )
    assert corpus["groups"] == swapped["groups"]
    assert (
        corpus["receipt"]["input_order_group_ids_sha256"]
        == swapped["receipt"]["input_order_group_ids_sha256"]
    )
    labels = {item["group_id"]: item["label"] for item in corpus["oracle"]["labels"]}
    assert set(labels.values()) == {"include", "exclude"}
    seeds = [
        next(group_id for group_id, label in labels.items() if label == "include"),
        next(group_id for group_id, label in labels.items() if label == "exclude"),
    ]
    simulated = simulate_active_learning(
        corpus["groups"],
        corpus["oracle"],
        seed_group_ids=seeds,
    )
    assert simulated["authority"]["live_review_state_written"] is False
    output = tmp_path / "prepared"
    written = write_historical_ris_corpus(corpus, output)
    assert written["authority"]["simulation_only"] is True
    assert (output / "DEDUP_GROUPS.jsonl").is_file()
    assert (output / "FULLY_LABELLED_SIMULATION_ORACLE.json").is_file()
    cli_output = tmp_path / "cli-prepared"
    assert (
        pipeline_main(
            [
                "prepare-historical-ris",
                str(included),
                str(excluded),
                str(cli_output),
                "--simulation-id",
                "ris-fixture",
                "--source-id",
                "fixture-source",
            ]
        )
        == 0
    )
    assert (cli_output / "HISTORICAL_RIS_IMPORT_RECEIPT.json").is_file()


def test_historical_ris_preparation_fails_closed_for_cross_label_duplicates(
    tmp_path: Path,
) -> None:
    included = tmp_path / "included.ris"
    excluded = tmp_path / "excluded.ris"
    shared = "TY  - JOUR\nTI  - Same evidence\nDO  - 10.1000/shared\nER  -\n"
    included.write_text(shared, encoding="utf-8")
    excluded.write_text(shared, encoding="utf-8")
    with pytest.raises(ScientificEvidenceError, match="conflicting include/exclude"):
        prepare_historical_ris_corpus(
            included,
            excluded,
            simulation_id="ris-conflict",
            source_id="fixture-source",
        )


class _HistoricalRdsFixtureTable:
    columns = (
        "review_authors",
        "screener",
        "TP",
        "TN",
        "FN",
        "FP",
        "recall",
        "spec",
        "bacc",
        "review",
    )
    empty = False

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def to_dict(self, *, orient: str) -> list[dict[str, object]]:
        assert orient == "records"
        return self.rows


class _HistoricalRdsFixtureReader:
    def __init__(self, table: _HistoricalRdsFixtureTable) -> None:
        self.table = table

    def read_rds(self, _: Path) -> _HistoricalRdsFixtureTable:
        warnings.warn(
            'Missing constructor for R class "tbl". The constructor for class "data.frame" will be used instead.',
            UserWarning,
            stacklevel=2,
        )
        return self.table


def test_historical_rds_performance_inspection_is_safe_and_validates_formulas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "performance.rds"
    source.write_bytes(b"synthetic RDS fixture")
    table = _HistoricalRdsFixtureTable(
        [
            {
                "review_authors": "Fixture Authors",
                "screener": "Private Person A",
                "TP": 9,
                "TN": 80,
                "FN": 1,
                "FP": 10,
                "recall": 0.9,
                "spec": 80 / 90,
                "bacc": (0.9 + 80 / 90) / 2,
                "review": "Fixture review",
            },
            {
                "review_authors": "Fixture Authors",
                "screener": "Private Person B",
                "TP": 8,
                "TN": 81,
                "FN": 2,
                "FP": 9,
                "recall": 0.8,
                "spec": 0.9,
                "bacc": 0.85,
                "review": "Fixture review",
            },
        ]
    )
    monkeypatch.setattr(
        scientific_screening,
        "_load_historical_rds_reader",
        lambda: (_HistoricalRdsFixtureReader(table), "fixture-rdata"),
    )
    report = inspect_historical_rds_performance(
        source,
        expected_review="Fixture review",
        expected_review_authors="Fixture Authors",
    )
    assert report["performance"]["row_count"] == 2
    assert report["performance"]["aggregate_confusion_matrix"] == {
        "TP": 17,
        "TN": 161,
        "FN": 3,
        "FP": 19,
    }
    assert report["warnings"]["count"] == 1
    assert report["warnings"]["entries"][0]["category"] == "UserWarning"
    assert report["warnings"]["entries"][0]["code"] == "rdata_missing_constructor"
    assert "message" not in report["warnings"]["entries"][0]
    assert set(report["source"]) == {"kind", "sha256", "bytes"}
    assert report["authority"]["direct_model_human_comparison_produced"] is False
    assert "Private Person A" not in json.dumps(report)
    output = tmp_path / "performance.json"
    assert (
        pipeline_main(
            [
                "inspect-historical-rds-performance",
                str(source),
                str(output),
                "--expected-review",
                "Fixture review",
                "--expected-review-authors",
                "Fixture Authors",
            ]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["report_payload_sha256"] == report[
        "report_payload_sha256"
    ]


def test_historical_rds_performance_inspection_fails_closed_for_formula_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "performance.rds"
    source.write_bytes(b"synthetic RDS fixture")
    table = _HistoricalRdsFixtureTable(
        [
            {
                "review_authors": "Fixture Authors",
                "screener": "Private Person A",
                "TP": 9,
                "TN": 80,
                "FN": 1,
                "FP": 10,
                "recall": 0.1,
                "spec": 80 / 90,
                "bacc": 0.5,
                "review": "Fixture review",
            }
        ]
    )
    monkeypatch.setattr(
        scientific_screening,
        "_load_historical_rds_reader",
        lambda: (_HistoricalRdsFixtureReader(table), "fixture-rdata"),
    )
    with pytest.raises(ScientificEvidenceError, match="recall does not match"):
        inspect_historical_rds_performance(source)


def test_historical_rds_performance_inspection_redacts_unknown_reader_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "performance.rds"
    source.write_bytes(b"synthetic RDS fixture")

    class _PrivateWarningReader(_HistoricalRdsFixtureReader):
        def read_rds(self, _: Path) -> _HistoricalRdsFixtureTable:
            warnings.warn("could not parse Private Person A", UserWarning, stacklevel=2)
            return self.table

    table = _HistoricalRdsFixtureTable(
        [
            {
                "review_authors": "Fixture Authors",
                "screener": "Private Person A",
                "TP": 9,
                "TN": 80,
                "FN": 1,
                "FP": 10,
                "recall": 0.9,
                "spec": 80 / 90,
                "bacc": (0.9 + 80 / 90) / 2,
                "review": "Fixture review",
            }
        ]
    )
    monkeypatch.setattr(
        scientific_screening,
        "_load_historical_rds_reader",
        lambda: (_PrivateWarningReader(table), "fixture-rdata"),
    )
    report = inspect_historical_rds_performance(source)
    warning = report["warnings"]["entries"][0]
    assert warning["code"] == "redacted_reader_warning"
    assert "message" not in warning
    assert "Private Person A" not in json.dumps(report)


def test_historical_rds_performance_inspection_fails_closed_if_source_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "performance.rds"
    source.write_bytes(b"synthetic RDS fixture")
    table = _HistoricalRdsFixtureTable(
        [
            {
                "review_authors": "Fixture Authors",
                "screener": "Private Person A",
                "TP": 9,
                "TN": 80,
                "FN": 1,
                "FP": 10,
                "recall": 0.9,
                "spec": 80 / 90,
                "bacc": (0.9 + 80 / 90) / 2,
                "review": "Fixture review",
            }
        ]
    )

    class _MutatingReader(_HistoricalRdsFixtureReader):
        def read_rds(self, path: Path) -> _HistoricalRdsFixtureTable:
            path.write_bytes(b"changed during read")
            return self.table

    monkeypatch.setattr(
        scientific_screening,
        "_load_historical_rds_reader",
        lambda: (_MutatingReader(table), "fixture-rdata"),
    )
    with pytest.raises(ScientificEvidenceError, match="changed while it was being read"):
        inspect_historical_rds_performance(source)
