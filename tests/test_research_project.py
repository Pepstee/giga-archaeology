from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from twin_core.research_export import (
    PLAN_MIND_MAP_RECEIPT_SCHEMA,
    ResearchExportError,
    citation_trace_view_receipt,
    plan_mind_map_receipt,
    render_citation_trace_view,
    render_plan_mind_map,
)
from twin_core.research_project import (
    FRONTIER_EXTENSION_SCHEMA,
    FRONTIER_PROPOSAL_REQUEST_SCHEMA,
    FRONTIER_PROVIDER_PROPOSAL_SCHEMA,
    FRONTIER_PROVIDER_RESPONSE_SCHEMA,
    FRONTIER_SCHEMA,
    PROJECT_SCHEMA,
    ResearchProjectError,
    ResearchProjectStore,
    build_frontier_proposal_request,
    build_research_frontier,
    propose_frontier_extension,
    propose_provider_frontier_extension,
    validate_frontier_provider_response,
    validate_project_plan,
)
from twin_core.scientific_pipeline_cli import main as pipeline_main
from twin_core.web_acquisition import PublicWebAcquirer, WebResponse

FIXED_TIME = "2026-08-30T12:00:00+00:00"


def _plan() -> dict:
    return {
        "schema_version": PROJECT_SCHEMA,
        "project_id": "project-1",
        "question": "Does approach A outperform approach B?",
        "created_at": FIXED_TIME,
        "perspectives": [
            {"id": "benefits", "label": "Benefits", "rationale": "Find supporting outcomes."},
            {"id": "challenges", "label": "Challenges", "rationale": "Seek contrary evidence."},
        ],
        "subquestions": [
            {
                "id": "Q2",
                "perspective_id": "challenges",
                "question": "What evidence contradicts the main hypothesis?",
                "search_terms": ["approach A limitations"],
                "source_types": ["public_web", "scientific_api"],
                "priority": 2,
            },
            {
                "id": "Q1",
                "perspective_id": "benefits",
                "question": "What comparative outcomes are reported?",
                "search_terms": ["approach A versus B"],
                "source_types": ["scientific_api"],
                "priority": 1,
            },
        ],
        "stopping_conditions": {
            "maximum_sources": 40,
            "maximum_depth": 2,
            "minimum_source_diversity": 2,
            "require_contradiction_search": True,
        },
    }


def _store(tmp_path: Path) -> ResearchProjectStore:
    return ResearchProjectStore(tmp_path / "private" / "projects.sqlite3")


def _plan_sha256(plan: dict) -> str:
    clean = validate_project_plan(plan)
    encoded = json.dumps(
        clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _payload_sha256(value: dict) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_citation_trace_view_is_hash_bound_sanitised_and_inspectable() -> None:
    graph = {
        "schema_version": "giga.research-citation-graph.v1",
        "project_id": "trace-project",
        "nodes": [
            {
                "id": "question:Q1",
                "type": "subquestion",
                "label": "Which result should be reviewed?",
            },
            {
                "id": "claim:C1",
                "type": "claim",
                "label": "The reported result needs review.",
                "position": "supports",
                "confidence": 0.7,
                "review_status": "pending",
                "authority": "proposal_only",
                "effective_authority": "proposal_only",
            },
            {
                "id": "evidence:E1",
                "type": "evidence",
                "label": "<img src=x onerror=alert(1)>",
                "quote_sha256": "a" * 64,
                "locator": "paragraph 1",
                "trust_class": "archived_public_web",
            },
            {
                "id": "source:S1",
                "type": "source",
                "label": "Archived fixture",
                "receipt_sha256": "b" * 64,
                "trust_class": "archived_public_web",
                "authority_tier": "primary",
            },
        ],
        "edges": [
            {
                "source": "question:Q1",
                "target": "evidence:E1",
                "relation": "has_evidence",
            },
            {
                "source": "claim:C1",
                "target": "evidence:E1",
                "relation": "cites",
            },
            {
                "source": "evidence:E1",
                "target": "source:S1",
                "relation": "from_source",
            },
        ],
        "counts": {
            "nodes": 4,
            "edges": 3,
            "sources": 1,
            "evidence_spans": 1,
            "claims": 1,
            "claim_relations": 0,
            "accepted_relations": 0,
            "rejected_relations": 0,
            "pending_relations": 0,
        },
        "claim_boundary": "Only a human review can change claim authority.",
    }
    graph["graph_sha256"] = _payload_sha256(graph)

    document = render_citation_trace_view(graph)
    assert document == render_citation_trace_view(graph)
    assert "Claim and evidence trace" in document
    assert "Content-Security-Policy" in document
    assert "connect-src 'none'" in document
    assert 'id="citation-graph-data"' in document
    assert "textContent" in document
    assert "<img src=x" not in document
    assert r"\u003cimg src=x onerror=alert(1)\u003e" in document
    assert "fetch(" not in document
    assert "innerHTML" not in document

    receipt = citation_trace_view_receipt(graph, document)
    assert receipt["graph_sha256"] == graph["graph_sha256"]
    assert receipt["format"] == "self_contained_html"
    assert receipt["claim_authority"] == "human_review_state_only"
    assert receipt["bytes"] == len(document.encode("utf-8"))
    assert len(receipt["trace_view_sha256"]) == 64

    tampered = dict(graph)
    tampered["graph_sha256"] = "0" * 64
    with pytest.raises(ResearchExportError, match="hash mismatch"):
        render_citation_trace_view(tampered)




def _run_bundle() -> dict:
    return {
        "schema_version": "giga.research-run.v1",
        "run_id": "a" * 64,
        "project_id": "project-1",
        "specification": {
            "plan_sha256": _plan_sha256(_plan()),
            "subquestion_ids": ["Q1"],
        },
        "acquisitions": [
            {
                "subquestion_id": "Q1",
                "status": "acquired",
                "final_url": "https://example.com/evidence",
                "receipt_sha256": "b" * 64,
                "fetched_at": "2026-08-30T11:00:00+00:00",
            },
            {
                "subquestion_id": "Q1",
                "status": "failed",
                "source_url": "https://failed.example/source",
            },
        ],
        "retrievals": [
            {"subquestion_id": "Q1", "result": {"results": [{"passage_id": "P1"}]}}
        ],
        "evidence_spans": [
            {
                "subquestion_id": "Q1",
                "evidence_span_id": "c" * 64,
                "passage_id": "P1",
            }
        ],
    }


def _archived_source(
    tmp_path: Path,
    *,
    source: str = "https://example.com/evidence",
    body: bytes = b"Evidence",
):

    class Transport:
        name = "fake:static"

        def fetch(self, url: str, *, timeout_seconds: int) -> WebResponse:
            return WebResponse(url, 200, {"content-type": "text/plain"}, body, FIXED_TIME)

    def resolver(*args: object, **kwargs: object) -> list[tuple]:
        return [(2, 1, 6, "", ("93.184.216.34", 443))]

    repository = tmp_path / "repo"
    repository.mkdir(exist_ok=True)
    archive = tmp_path / "archive"
    result = PublicWebAcquirer(
        repository_root=repository,
        archive_root=archive,
        transport=Transport(),
        resolver=resolver,
    ).acquire(source)
    return archive, result


def test_plan_requires_perspectives_questions_bounds_and_contradiction_policy() -> None:
    clean = validate_project_plan(_plan())
    assert [row["id"] for row in clean["subquestions"]] == ["Q1", "Q2"]
    broken = _plan()
    broken["subquestions"][0]["perspective_id"] = "missing"
    with pytest.raises(ResearchProjectError, match="unknown perspective"):
        validate_project_plan(broken)


def test_frontier_cross_evaluates_coverage_diversity_freshness_and_contradiction() -> None:
    frontier = build_research_frontier(
        _plan(),
        [_run_bundle()],
        evidence_matrix={"project_id": "project-1", "claims": []},
        evaluated_at="2026-08-30T12:00:00+00:00",
        minimum_evidence_spans=1,
        minimum_distinct_domains=2,
        maximum_age_days=1,
    )

    assert frontier["schema_version"] == FRONTIER_SCHEMA
    assert frontier["frontier_sha256"]
    assert frontier["project_gap_types"] == ["contradiction"]
    assert frontier["next_subquestion_ids"] == ["Q1", "Q2"]
    assert frontier["synthesis_ready"] is False
    nodes = {row["id"]: row for row in frontier["nodes"]}
    assert nodes["Q1"]["status"] == "needs_follow_up"
    assert nodes["Q1"]["gap_types"] == ["source_diversity"]
    assert nodes["Q1"]["checks"]["completeness"]["pass"] is True
    assert nodes["Q1"]["checks"]["plurality"]["pass"] is False
    assert nodes["Q1"]["checks"]["freshness"]["pass"] is True
    assert nodes["Q1"]["source_failures"] == 1
    assert nodes["Q2"]["status"] == "unresearched"
    assert nodes["Q2"]["gap_types"] == [
        "not_researched",
        "evidence_sufficiency",
        "source_diversity",
        "freshness",
    ]


def test_frontier_marks_satisfied_root_and_rejects_future_source_timestamps() -> None:
    first = _run_bundle()
    second = json.loads(json.dumps(first))
    second["run_id"] = "d" * 64
    second["specification"]["subquestion_ids"] = ["Q2"]
    for collection in ("acquisitions", "retrievals", "evidence_spans"):
        for row in second[collection]:
            row["subquestion_id"] = "Q2"
    second["evidence_spans"][0]["evidence_span_id"] = "e" * 64
    frontier = build_research_frontier(
        _plan(),
        [first, second],
        evidence_matrix={
            "project_id": "project-1",
            "claims": [{"position": "contradicts"}],
        },
        evaluated_at=FIXED_TIME,
    )

    assert frontier["synthesis_ready"] is True
    assert frontier["nodes"][0]["status"] == "satisfied"
    assert frontier["next_subquestion_ids"] == []

    future = _run_bundle()
    future["acquisitions"][0]["fetched_at"] = "2026-08-31T12:00:00+00:00"
    with pytest.raises(ResearchProjectError, match="cannot be after"):
        build_research_frontier(
            _plan(),
            [future],
            evaluated_at=FIXED_TIME,
            maximum_age_days=0,
        )


def test_frontier_extension_is_bounded_deduplicated_and_requires_new_approval() -> None:
    frontier = build_research_frontier(
        _plan(),
        [_run_bundle()],
        evidence_matrix={"project_id": "project-1", "claims": []},
        evaluated_at=FIXED_TIME,
        minimum_distinct_domains=2,
    )
    followups = [
        {
            "id": "Q3",
            "parent_subquestion_id": "Q1",
            "question": "Which independent domains report replicated comparative outcomes?",
            "search_terms": ["independent replication comparative outcomes"],
            "gap_types": ["source_diversity"],
            "rationale": "The first round contains evidence from only one registrable domain.",
        }
    ]

    extension = propose_frontier_extension(
        _plan(),
        frontier,
        followups,
        extension_project_id="project-1-followup-1",
        created_at=FIXED_TIME,
    )

    assert extension["schema_version"] == FRONTIER_EXTENSION_SCHEMA
    assert extension["approval_required"] is True
    assert extension["execution_state"] == "awaiting_human_approval"
    assert extension["project_plan"]["project_id"] == "project-1-followup-1"
    assert extension["project_plan"]["stopping_conditions"]["maximum_depth"] == 1
    assert extension["links"] == [
        {
            "parent_subquestion_id": "Q1",
            "child_subquestion_id": "Q3",
            "gap_types": ["source_diversity"],
            "rationale": "The first round contains evidence from only one registrable domain.",
        }
    ]

    duplicate = json.loads(json.dumps(followups))
    duplicate[0]["question"] = "What comparative outcomes are reported?"
    with pytest.raises(ResearchProjectError, match="duplicates Q1"):
        propose_frontier_extension(
            _plan(),
            frontier,
            duplicate,
            extension_project_id="project-1-followup-duplicate",
            created_at=FIXED_TIME,
        )

    repeated_terms = [
        *followups,
        {
            "id": "Q4",
            "parent_subquestion_id": "Q1",
            "question": "Which separate publishers validate the reported comparison?",
            "search_terms": ["independent replication comparative outcomes"],
            "gap_types": ["source_diversity"],
            "rationale": "A second source-diversity proposal must not repeat the first search.",
        },
    ]
    with pytest.raises(ResearchProjectError, match="search terms duplicate Q3"):
        propose_frontier_extension(
            _plan(),
            frontier,
            repeated_terms,
            extension_project_id="project-1-followup-repeated-terms",
            created_at=FIXED_TIME,
        )

    exhausted = _plan()
    exhausted["stopping_conditions"]["maximum_depth"] = 1
    exhausted_frontier = build_research_frontier(
        exhausted,
        [],
        evaluated_at=FIXED_TIME,
    )
    with pytest.raises(ResearchProjectError, match="depth is exhausted"):
        propose_frontier_extension(
            exhausted,
            exhausted_frontier,
            followups,
            extension_project_id="project-1-followup-exhausted",
            created_at=FIXED_TIME,
        )


def test_provider_frontier_proposal_is_minimal_bound_and_costed() -> None:
    frontier = build_research_frontier(
        _plan(),
        [_run_bundle()],
        evidence_matrix={"project_id": "project-1", "claims": []},
        evaluated_at=FIXED_TIME,
        minimum_distinct_domains=2,
    )
    request = build_frontier_proposal_request(
        _plan(),
        frontier,
        requested_at=FIXED_TIME,
        maximum_followups=2,
    )

    assert request["schema_version"] == FRONTIER_PROPOSAL_REQUEST_SCHEMA
    assert request["maximum_followups"] == 2
    assert request["request_sha256"]
    encoded_request = json.dumps(request)
    assert "receipt_sha256s" not in encoded_request
    assert "evidence_span_ids" not in encoded_request
    assert "run_ids" not in encoded_request

    followup = {
        "id": "Q3",
        "parent_subquestion_id": "Q1",
        "question": "Which independent domains replicate the comparative result?",
        "search_terms": ["independent replication comparative result"],
        "gap_types": ["source_diversity"],
        "rationale": "Only one registrable source domain is represented.",
    }
    unsigned_response = {
        "schema_version": FRONTIER_PROVIDER_RESPONSE_SCHEMA,
        "request_sha256": request["request_sha256"],
        "provider": {
            "name": "provider-fixture",
            "model": "model-v1",
            "response_id": "response-123",
            "generated_at": "2026-08-30T12:01:00+00:00",
            "input_tokens": 800,
            "output_tokens": 120,
            "latency_ms": 950,
            "cost_usd": 0.0125,
        },
        "followups": [followup],
    }
    response = {
        **unsigned_response,
        "response_sha256": _payload_sha256(unsigned_response),
    }
    proposal = validate_frontier_provider_response(request, response)
    assert proposal["schema_version"] == FRONTIER_PROVIDER_PROPOSAL_SCHEMA
    assert proposal["provider"]["cost_usd"] == 0.0125
    assert proposal["provider"]["input_tokens"] == 800
    assert proposal["provider"]["measurement_completeness"] == "complete"
    assert proposal["proposal_sha256"]

    unmetered = json.loads(json.dumps(unsigned_response))
    for field in ("input_tokens", "output_tokens", "latency_ms", "cost_usd"):
        unmetered["provider"][field] = None
    unmetered_response = {
        **unmetered,
        "response_sha256": _payload_sha256(unmetered),
    }
    unmetered_proposal = validate_frontier_provider_response(
        request, unmetered_response
    )
    assert unmetered_proposal["provider"]["measurement_completeness"] == "partial"

    provider_extension = propose_provider_frontier_extension(
        _plan(),
        frontier,
        request,
        response,
        extension_project_id="project-1-provider-followup-1",
        created_at="2026-08-30T12:02:00+00:00",
    )
    assert provider_extension["approval_required"] is True
    assert provider_extension["execution_state"] == "awaiting_human_approval"
    assert (
        provider_extension["extension"]["project_plan"]["project_id"]
        == "project-1-provider-followup-1"
    )

    tampered_request = {**request, "maximum_followups": 3}
    with pytest.raises(ResearchProjectError, match="canonical rebuild"):
        propose_provider_frontier_extension(
            _plan(),
            frontier,
            tampered_request,
            response,
            extension_project_id="project-1-provider-tampered",
            created_at="2026-08-30T12:02:00+00:00",
        )

    credentialed = json.loads(json.dumps(unsigned_response))
    credentialed["provider"]["api_key"] = "must-not-persist"
    credentialed["response_sha256"] = _payload_sha256(credentialed)
    with pytest.raises(ResearchProjectError, match="credential field"):
        validate_frontier_provider_response(request, credentialed)






def test_project_is_resumable_but_cannot_acquire_before_exact_human_approval(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    created = store.create(_plan())
    assert created["status"] == "awaiting_human_approval"
    assert store.status("project-1")["status"] == "awaiting_human_approval"
    archive, source = _archived_source(tmp_path)
    with pytest.raises(ResearchProjectError, match="human approval"):
        store.attach_web_source("project-1", source.receipt_path, archive)
    with pytest.raises(ResearchProjectError, match="plan hash differs"):
        store.approve("project-1", plan_sha256="0" * 64, approved_by="operator")
    store.approve(
        "project-1",
        plan_sha256=created["plan_sha256"],
        approved_by="operator",
        approved_at=FIXED_TIME,
    )
    attached = store.attach_web_source("project-1", source.receipt_path, archive)
    duplicate = store.attach_web_source("project-1", source.receipt_path, archive)
    resumed = store.status("project-1")
    assert resumed["status"] == "active"
    assert resumed["source_count"] == 1
    assert resumed["source_receipt_sha256s"] == [attached["receipt_sha256"]]
    assert duplicate["status"] == "already_attached"


def test_project_ledger_is_owner_only_append_only_and_audited(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create(_plan())
    assert store.database.stat().st_mode & 0o777 == 0o600
    with store._connection() as connection:
        with pytest.raises(Exception, match="append-only"):
            connection.execute("DELETE FROM research_project_events")
        connection.execute("PRAGMA writable_schema = OFF")
    assert store.status("project-1")["last_event_sha256"]


def test_receipt_attachment_rejects_tampered_content(tmp_path: Path) -> None:
    store = _store(tmp_path)
    created = store.create(_plan())
    store.approve("project-1", plan_sha256=created["plan_sha256"], approved_by="operator")
    archive, source = _archived_source(tmp_path)
    receipt = json.loads(source.receipt_path.read_text(encoding="utf-8"))
    object_path = archive / "objects" / receipt["content_sha256"][:2] / receipt["content_sha256"]
    object_path.write_bytes(b"tampered")
    with pytest.raises(ResearchProjectError, match="missing or differs"):
        store.attach_web_source("project-1", source.receipt_path, archive)


def test_near_duplicate_source_is_preserved_as_rejection_not_counted_twice(tmp_path: Path) -> None:
    store = _store(tmp_path)
    created = store.create(_plan())
    store.approve("project-1", plan_sha256=created["plan_sha256"], approved_by="operator")
    archive, first = _archived_source(
        tmp_path,
        source="https://example.com/original",
        body=b"A research system preserves exact sources and verifies every citation.",
    )
    store.attach_web_source("project-1", first.receipt_path, archive)
    _, mirror = _archived_source(
        tmp_path,
        source="https://mirror.example/copy",
        body=b"A research system preserves exact sources and verifies every citation.",
    )
    rejected = store.attach_web_source("project-1", mirror.receipt_path, archive)
    assert rejected["status"] == "rejected_near_duplicate"
    assert store.status("project-1")["source_count"] == 1


def test_refetched_exact_source_reuses_its_canonical_receipt(tmp_path: Path) -> None:
    store = _store(tmp_path)
    created = store.create(_plan())
    store.approve("project-1", plan_sha256=created["plan_sha256"], approved_by="operator")
    archive, first = _archived_source(
        tmp_path,
        source="https://example.com/original",
        body=b"Stable evidence from the same source.",
    )
    attached = store.attach_web_source("project-1", first.receipt_path, archive)
    _, refetched = _archived_source(
        tmp_path,
        source="https://example.com/original",
        body=b"Stable evidence from the same source.",
    )

    reused = store.attach_web_source("project-1", refetched.receipt_path, archive)

    assert reused["status"] in {"already_attached", "already_attached_equivalent"}
    assert reused["receipt_sha256"] == attached["receipt_sha256"]
    assert store.status("project-1")["source_count"] == 1






def test_claim_review_is_single_decision_and_project_bound(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create(_plan())
    with pytest.raises(ResearchProjectError, match="not a proposal"):
        store.review_claim(
            "project-1",
            claim_id="0" * 64,
            decision="accept",
            reviewed_by="operator",
            notes="No such claim.",
        )


def test_project_cli_create_approve_status_round_trip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_plan()), encoding="utf-8")
    database = tmp_path / "projects.sqlite3"
    assert (
        pipeline_main(["project", "--project-database", str(database), "create", str(plan_path)])
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(database),
                "approve",
                "project-1",
                created["plan_sha256"],
                "operator",
                "--approved-at",
                FIXED_TIME,
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        pipeline_main(["project", "--project-database", str(database), "status", "project-1"]) == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "ready"


def test_project_report_separates_review_states_and_escapes_source_html(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = _store(tmp_path)
    created = store.create(_plan())
    store.approve("project-1", plan_sha256=created["plan_sha256"], approved_by="operator")
    archive, source = _archived_source(tmp_path, body=b"Evidence <script>alert(1)</script>")
    attached = store.attach_web_source("project-1", source.receipt_path, archive)
    evidence = store.add_evidence_span(
        "project-1",
        receipt_sha256=attached["receipt_sha256"],
        archive_root=archive,
        quote="Evidence <script>alert(1)</script>",
        locator="exact text",
        subquestion_ids=["Q1"],
    )
    claim = store.propose_claim(
        "project-1",
        claim="The source contains evidence.",
        evidence_span_ids=[evidence["evidence_span_id"]],
        position="supports",
        confidence=0.8,
        proposed_by="model",
    )
    store.review_claim(
        "project-1",
        claim_id=claim["claim_id"],
        decision="accept",
        reviewed_by="operator",
        notes="Checked.",
    )
    report = tmp_path / "report.md"
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "report",
                "project-1",
                str(report),
            ]
        )
        == 0
    )
    rendered = report.read_text(encoding="utf-8")
    assert "## Human-accepted claims" in rendered
    assert "Evidence &lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "[S1](https://example.com/evidence)" in rendered
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["sha256"]


def test_project_plan_mind_map_is_hash_bound_sanitised_and_runnable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = _plan()
    plan["question"] = "<img src=x onerror=alert(1)> How should the plan be reviewed?"
    store = _store(tmp_path)
    created = store.create(plan)

    pending_map = store.plan_map("project-1")
    assert pending_map == store.plan_map("project-1")
    assert pending_map["counts"] == {
        "nodes": 5,
        "edges": 4,
        "perspectives": 2,
        "subquestions": 2,
    }
    assert pending_map["plan_approved"] is False
    assert {node["type"] for node in pending_map["nodes"]} == {
        "project",
        "perspective",
        "subquestion",
    }
    assert len(pending_map["plan_map_sha256"]) == 64

    document = render_plan_mind_map(pending_map)
    assert document == render_plan_mind_map(pending_map)
    assert "Research plan map" in document
    assert "Content-Security-Policy" in document
    assert "connect-src 'none'" in document
    assert 'id="plan-map-data"' in document
    assert "textContent" in document
    assert "questionsByPerspective" in document
    assert "questionsByPerspective.get(perspective.id).has(question.id)" in document
    assert "question.perspective_id === perspective.id" not in document
    assert "<img src=x" not in document
    assert r"\u003cimg src=x onerror=alert(1)\u003e" in document
    assert "fetch(" not in document
    assert "innerHTML" not in document
    receipt = plan_mind_map_receipt(pending_map, document)
    assert receipt["schema_version"] == PLAN_MIND_MAP_RECEIPT_SCHEMA
    assert receipt["plan_map_sha256"] == pending_map["plan_map_sha256"]
    assert receipt["plan_authority"] == "human_approval_only"
    assert receipt["claim_authority"] == "none"
    assert receipt["bytes"] == len(document.encode("utf-8"))

    tampered = dict(pending_map)
    tampered["plan_map_sha256"] = "0" * 64
    with pytest.raises(ResearchExportError, match="hash mismatch"):
        render_plan_mind_map(tampered)

    store.approve(
        "project-1", plan_sha256=created["plan_sha256"], approved_by="operator"
    )
    approved_map = store.plan_map("project-1")
    assert approved_map["plan_approved"] is True
    assert approved_map["plan_map_sha256"] != pending_map["plan_map_sha256"]
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "plan-map",
                "project-1",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == approved_map
    map_path = tmp_path / "exports" / "project-1-plan-map.html"
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "mind-map",
                "project-1",
                str(map_path),
            ]
        )
        == 0
    )
    cli_receipt = json.loads(capsys.readouterr().out)
    assert cli_receipt["plan_map_sha256"] == approved_map["plan_map_sha256"]
    assert cli_receipt["mind_map_sha256"] == hashlib.sha256(map_path.read_bytes()).hexdigest()
    assert cli_receipt["output"] == str(map_path.resolve())


def test_frontier_cli_exports_owner_only_plan_that_reenters_exact_approval_gate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = _store(tmp_path)
    created = store.create(_plan())
    store.approve("project-1", plan_sha256=created["plan_sha256"], approved_by="operator")
    run_path = tmp_path / "run.json"
    run_path.write_text(json.dumps(_run_bundle()), encoding="utf-8")
    frontier_path = tmp_path / "private" / "FRONTIER.json"

    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "frontier",
                "project-1",
                "--run",
                str(run_path),
                "--evaluated-at",
                FIXED_TIME,
                "--minimum-distinct-domains",
                "2",
                "--output",
                str(frontier_path),
            ]
        )
        == 0
    )
    frontier_receipt = json.loads(capsys.readouterr().out)
    assert frontier_receipt["execution_state"] == "follow_up_proposal_required"
    assert frontier_path.stat().st_mode & 0o777 == 0o600

    followups_path = tmp_path / "followups.json"
    followups_path.write_text(
        json.dumps(
            {
                "followups": [
                    {
                        "id": "Q3",
                        "parent_subquestion_id": "Q1",
                        "question": "Which independent domains replicate the comparative result?",
                        "search_terms": ["independent replication comparative result"],
                        "gap_types": ["source_diversity"],
                        "rationale": "Only one registrable source domain is represented.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    extension_path = tmp_path / "private" / "EXTENSION.json"
    plan_path = tmp_path / "private" / "PLAN.json"
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "extend-frontier",
                "project-1",
                str(frontier_path),
                str(followups_path),
                "project-1-followup-1",
                "--created-at",
                FIXED_TIME,
                "--output",
                str(extension_path),
                "--plan-output",
                str(plan_path),
            ]
        )
        == 0
    )
    extension_receipt = json.loads(capsys.readouterr().out)
    assert extension_receipt["approval_required"] is True
    assert plan_path.stat().st_mode & 0o777 == 0o600

    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "create",
                str(plan_path),
            ]
        )
        == 0
    )
    proposed = json.loads(capsys.readouterr().out)
    assert proposed["status"] == "awaiting_human_approval"


def test_provider_frontier_cli_preserves_provenance_and_reenters_approval_gate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = _store(tmp_path)
    created = store.create(_plan())
    store.approve("project-1", plan_sha256=created["plan_sha256"], approved_by="operator")
    frontier = build_research_frontier(
        _plan(),
        [_run_bundle()],
        evidence_matrix={"project_id": "project-1", "claims": []},
        evaluated_at=FIXED_TIME,
        minimum_distinct_domains=2,
    )
    frontier_path = tmp_path / "frontier.json"
    frontier_path.write_text(json.dumps(frontier), encoding="utf-8")
    request_path = tmp_path / "private" / "REQUEST.json"
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "frontier-request",
                "project-1",
                str(frontier_path),
                "--requested-at",
                FIXED_TIME,
                "--maximum-followups",
                "1",
                "--output",
                str(request_path),
            ]
        )
        == 0
    )
    request_summary = json.loads(capsys.readouterr().out)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request_summary["execution_state"] == "awaiting_provider_response"
    assert request_path.stat().st_mode & 0o777 == 0o600

    unsigned_response = {
        "schema_version": FRONTIER_PROVIDER_RESPONSE_SCHEMA,
        "request_sha256": request["request_sha256"],
        "provider": {
            "name": "provider-fixture",
            "model": "model-v1",
            "response_id": "response-cli-1",
            "generated_at": "2026-08-30T12:01:00+00:00",
            "input_tokens": 700,
            "output_tokens": 100,
            "latency_ms": 800,
            "cost_usd": 0.01,
        },
        "followups": [
            {
                "id": "Q3",
                "parent_subquestion_id": "Q1",
                "question": "Which independent domains replicate the comparative result?",
                "search_terms": ["independent replication comparative result"],
                "gap_types": ["source_diversity"],
                "rationale": "Only one registrable source domain is represented.",
            }
        ],
    }
    response = {
        **unsigned_response,
        "response_sha256": _payload_sha256(unsigned_response),
    }
    response_path = tmp_path / "response.json"
    response_path.write_text(json.dumps(response), encoding="utf-8")
    provider_output = tmp_path / "private" / "PROVIDER_EXTENSION.json"
    plan_output = tmp_path / "private" / "PROVIDER_PLAN.json"
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "extend-frontier-provider",
                "project-1",
                str(frontier_path),
                str(request_path),
                str(response_path),
                "project-1-provider-followup-1",
                "--created-at",
                "2026-08-30T12:02:00+00:00",
                "--output",
                str(provider_output),
                "--plan-output",
                str(plan_output),
            ]
        )
        == 0
    )
    provider_summary = json.loads(capsys.readouterr().out)
    assert provider_summary["provider"]["response_id"] == "response-cli-1"
    assert provider_summary["provider"]["cost_usd"] == 0.01
    assert provider_summary["approval_required"] is True
    assert provider_output.stat().st_mode & 0o777 == 0o600
    assert plan_output.stat().st_mode & 0o777 == 0o600

    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "create",
                str(plan_output),
            ]
        )
        == 0
    )
    proposed = json.loads(capsys.readouterr().out)
    assert proposed["status"] == "awaiting_human_approval"


def test_exact_evidence_claims_contradictions_and_human_review_matrix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = _store(tmp_path)
    created = store.create(_plan())
    store.approve("project-1", plan_sha256=created["plan_sha256"], approved_by="operator")
    archive, source = _archived_source(tmp_path)
    attached = store.attach_web_source("project-1", source.receipt_path, archive)
    with pytest.raises(ResearchProjectError, match="not verbatim"):
        store.add_evidence_span(
            "project-1",
            receipt_sha256=attached["receipt_sha256"],
            archive_root=archive,
            quote="Invented quote",
            locator="page text",
            subquestion_ids=["Q1"],
        )
    evidence = store.add_evidence_span(
        "project-1",
        receipt_sha256=attached["receipt_sha256"],
        archive_root=archive,
        quote="Evidence",
        locator="page text",
        subquestion_ids=["Q1", "Q2"],
        recorded_at=FIXED_TIME,
    )
    with pytest.raises(ResearchProjectError, match="require evidence spans"):
        store.propose_claim(
            "project-1",
            claim="Unsupported claim",
            evidence_span_ids=[],
            position="supports",
            confidence=0.5,
            proposed_by="model",
        )
    with pytest.raises(ResearchProjectError, match="not lexically supported"):
        store.propose_claim(
            "project-1",
            claim="An unrelated weather forecast predicts rain.",
            evidence_span_ids=[evidence["evidence_span_id"]],
            position="supports",
            confidence=0.9,
            proposed_by="model",
        )
    supporting = store.propose_claim(
        "project-1",
        claim="The source reports evidence.",
        evidence_span_ids=[evidence["evidence_span_id"]],
        position="supports",
        confidence=0.8,
        proposed_by="model",
        recorded_at=FIXED_TIME,
    )
    contradicting = store.propose_claim(
        "project-1",
        claim="The evidence may not generalise.",
        evidence_span_ids=[evidence["evidence_span_id"]],
        position="contradicts",
        confidence=0.4,
        proposed_by="model",
    )
    store.review_claim(
        "project-1",
        claim_id=supporting["claim_id"],
        decision="accept",
        reviewed_by="operator",
        notes="Quote and interpretation checked.",
        reviewed_at=FIXED_TIME,
    )
    with pytest.raises(ResearchProjectError, match="distinct claims"):
        store.propose_claim_relation(
            "project-1",
            source_claim_id=supporting["claim_id"],
            target_claim_id=supporting["claim_id"],
            relation="contradicts",
            rationale="A claim cannot contradict itself.",
            proposed_by="model",
        )
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "propose-claim-relation",
                "project-1",
                supporting["claim_id"],
                contradicting["claim_id"],
                "contradicts",
                "model",
                "The scope caveat limits the supporting interpretation.",
                "--recorded-at",
                FIXED_TIME,
            ]
        )
        == 0
    )
    relation = json.loads(capsys.readouterr().out)
    duplicate = store.propose_claim_relation(
        "project-1",
        source_claim_id=contradicting["claim_id"],
        target_claim_id=supporting["claim_id"],
        relation="contradicts",
        rationale="Reversed symmetric duplicate.",
        proposed_by="another-model",
    )
    assert duplicate == {
        "project_id": "project-1",
        "relation_id": relation["relation_id"],
        "status": "already_proposed",
    }
    with pytest.raises(ResearchProjectError, match="both endpoint claims"):
        store.review_claim_relation(
            "project-1",
            relation_id=relation["relation_id"],
            decision="accept",
            reviewed_by="operator",
            notes="One endpoint is still pending.",
        )
    store.review_claim(
        "project-1",
        claim_id=contradicting["claim_id"],
        decision="accept",
        reviewed_by="operator",
        notes="Caveat is supported and useful.",
    )
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "review-claim-relation",
                "project-1",
                relation["relation_id"],
                "accept",
                "operator",
                "Both claims and the limiting relationship were checked.",
            ]
        )
        == 0
    )
    capsys.readouterr()
    matrix = store.evidence_matrix("project-1")
    assert matrix["counts"] == {"accept": 2, "reject": 0, "pending": 0}
    assert matrix["contradiction_claim_count"] == 1
    assert matrix["claims"][0]["evidence"][0]["quote"] == "Evidence"
    assert matrix["claims"][0]["evidence"][0]["source"]["final_url"] == source.final_url
    assert matrix["sources"][0]["receipt_sha256"] == attached["receipt_sha256"]
    assert {row["authority"] for row in matrix["claims"]} == {"proposal_only"}
    graph = store.citation_graph("project-1")
    assert graph == store.citation_graph("project-1")
    assert graph["counts"] == {
        "nodes": 6,
        "edges": 6,
        "sources": 1,
        "evidence_spans": 1,
        "claims": 2,
        "claim_relations": 1,
        "accepted_relations": 1,
        "rejected_relations": 0,
        "pending_relations": 0,
    }
    relation_edge = next(edge for edge in graph["edges"] if edge.get("id"))
    assert relation_edge["relation"] == "contradicts"
    assert relation_edge["directed"] is False
    assert relation_edge["review_status"] == "accept"
    assert relation_edge["authority"] == "proposal_only"
    assert relation_edge["effective_authority"] == "human_accepted"
    assert {
        node["effective_authority"]
        for node in graph["nodes"]
        if node["type"] == "claim"
    } == {"human_accepted"}
    assert len(graph["graph_sha256"]) == 64
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "citation-graph",
                "project-1",
            ]
        )
        == 0
    )
    rendered_graph = capsys.readouterr().out
    assert json.loads(rendered_graph) == graph
    assert rendered_graph == json.dumps(
        graph, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    trace_path = tmp_path / "exports" / "project-1-trace.html"
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "trace-view",
                "project-1",
                str(trace_path),
            ]
        )
        == 0
    )
    trace_receipt = json.loads(capsys.readouterr().out)
    assert trace_path.is_file()
    assert trace_receipt["graph_sha256"] == graph["graph_sha256"]
    assert trace_receipt["trace_view_sha256"] == hashlib.sha256(
        trace_path.read_bytes()
    ).hexdigest()
    assert trace_receipt["output"] == str(trace_path.resolve())
    assert "Claim and evidence trace" in trace_path.read_text(encoding="utf-8")


def test_local_document_cli_archives_attaches_retrieves_and_ledgers_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    archive = tmp_path / "private-archive"
    document = tmp_path / "operator-note.md"
    document.write_text(
        "Approach A improved comparative recovery by twelve percent in the pilot.",
        encoding="utf-8",
    )
    plan = _plan()
    plan["subquestions"][0]["source_types"] = ["local_document"]
    store = _store(tmp_path)
    created = store.create(plan)
    store.approve(
        "project-1", plan_sha256=created["plan_sha256"], approved_by="operator"
    )

    assert (
        pipeline_main(
            [
                "acquire-local",
                str(document),
                "--repository-root",
                str(repository),
                "--archive-root",
                str(archive),
                "--archived-at",
                FIXED_TIME,
            ]
        )
        == 0
    )
    acquired = json.loads(capsys.readouterr().out)
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "attach-local-document",
                "project-1",
                acquired["receipt_path"],
                str(archive),
                "--recorded-at",
                FIXED_TIME,
            ]
        )
        == 0
    )
    attached = json.loads(capsys.readouterr().out)
    assert (
        pipeline_main(
            [
                "retrieve-passages",
                str(archive),
                "comparative recovery pilot",
                acquired["receipt_path"],
            ]
        )
        == 0
    )
    retrieval = json.loads(capsys.readouterr().out)
    assert retrieval["results"][0]["text"] == document.read_text(encoding="utf-8")
    assert retrieval["results"][0]["authority"] == "evidence_candidate_only"
    quote = tmp_path / "quote.txt"
    quote.write_text(retrieval["results"][0]["text"], encoding="utf-8")
    assert (
        pipeline_main(
            [
                "project",
                "--project-database",
                str(store.database),
                "add-evidence",
                "project-1",
                attached["receipt_sha256"],
                str(archive),
                str(quote),
                "complete local document",
                "--subquestion",
                "Q2",
                "--recorded-at",
                FIXED_TIME,
            ]
        )
        == 0
    )
    evidence = json.loads(capsys.readouterr().out)
    matrix = store.evidence_matrix("project-1")
    assert matrix["sources"][0]["source_kind"] == "local_document"
    assert matrix["sources"][0]["authority_tier"] == "local_unassessed"
    assert store.status("project-1")["source_count"] == 1
    graph = store.citation_graph("project-1")
    assert graph["counts"]["sources"] == 1
    evidence_node = next(node for node in graph["nodes"] if node["type"] == "evidence")
    assert (
        evidence_node["trust_class"]
        == "operator_selected_local_document_untrusted_content"
    )
    assert evidence["evidence_span_id"]
