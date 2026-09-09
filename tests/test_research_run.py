from __future__ import annotations

import json
import socket
import threading
from pathlib import Path

import pytest

from twin_core import scientific_pipeline_cli
from twin_core.research_export import (
    OUTLINE_PROPOSAL_SCHEMA,
    SYNTHESIS_PROPOSAL_SCHEMA,
    ResearchExportError,
    apply_reviewed_outline,
    build_synthesis_packet,
    render_synthesis_article,
    validate_outline_proposal,
    validate_synthesis_proposal,
)
from twin_core.research_project import (
    PROJECT_SCHEMA,
    ResearchProjectError,
    ResearchProjectStore,
)
from twin_core.research_run import (
    PARALLEL_RUN_SCHEMA,
    execute_parallel_research_runs,
    execute_research_run,
)
from twin_core.web_acquisition import PublicWebAcquirer, WebResponse


class FakeProvider:
    name = "fixture"

    def __init__(self) -> None:
        self.calls = 0

    def search(self, query: str, *, language: str, limit: int = 10) -> dict:
        self.calls += 1
        return {
            "schema_version": "giga.research-source-discovery.v1",
            "provider": self.name,
            "language": language,
            "query": query,
            "search_receipt_sha256": "a" * 64,
            "search_receipt_path": "/private/search-receipt",
            "results": [
                {
                    "rank": 1,
                    "title": "Primary evidence",
                    "source_url": "https://evidence.example/primary",
                    "snippet": "Approach comparison outcomes",
                    "provider_id": "one",
                    "updated_at": None,
                    "authority_tier": "general",
                    "authority_score": 0.5,
                },
                {
                    "rank": 2,
                    "title": "Independent evidence",
                    "source_url": "https://independent.example/study",
                    "snippet": "Independent approach outcomes comparison",
                    "provider_id": "two",
                    "updated_at": None,
                    "authority_tier": "general",
                    "authority_score": 0.5,
                },
            ],
            "result_count": 2,
            "claim_authority": False,
        }


class FakeTransport:
    name = "fake:static"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch(self, url: str, *, timeout_seconds: int) -> WebResponse:
        self.calls.append(url)
        body = (
            b"<script>no visible evidence</script>"
            if "empty" in url
            else (
                f"Comparative outcomes for approach A and approach B are reported by {url}. "
                "This archived evidence requires human interpretation."
            ).encode()
        )
        return WebResponse(
            url=url,
            status=200,
            headers={
                "content-type": "text/html" if "empty" in url else "text/plain"
            },
            body=body,
            fetched_at="2026-08-30T12:00:00+00:00",
        )


def _resolver(host: str, port: int, *, type: int) -> list[tuple]:
    assert type == socket.SOCK_STREAM
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _plan() -> dict:
    return {
        "schema_version": PROJECT_SCHEMA,
        "project_id": "run-project",
        "question": "Does approach A outperform approach B?",
        "created_at": "2026-08-30T12:00:00+00:00",
        "perspectives": [
            {"id": "comparison", "label": "Comparison", "rationale": "Compare outcomes."}
        ],
        "subquestions": [
            {
                "id": "Q1",
                "perspective_id": "comparison",
                "question": "报告了哪些比较结果？",
                "search_terms": ["approach A approach B outcomes"],
                "source_types": ["public_web"],
                "priority": 1,
            }
        ],
        "stopping_conditions": {
            "maximum_sources": 4,
            "maximum_depth": 1,
            "minimum_source_diversity": 1,
            "require_contradiction_search": False,
        },
    }


def _project_plan(project_id: str) -> dict:
    plan = json.loads(json.dumps(_plan()))
    plan["project_id"] = project_id
    return plan


def _local_plan() -> dict:
    plan = _plan()
    plan["subquestions"][0]["source_types"] = ["local_document"]
    return plan


def _child_result(project_id: str) -> dict:
    return {
        "schema_version": "giga.research-run.v1",
        "project_id": project_id,
        "run_id": ("a" if project_id.endswith("1") else "b") * 64,
        "bundle_sha256": "c" * 64,
        "claim_authority": False,
    }


def test_parallel_runs_preflight_all_approvals_then_execute_concurrently(
    tmp_path: Path,
) -> None:
    store = ResearchProjectStore(tmp_path / "private" / "projects.sqlite3")
    first = store.create(_project_plan("parallel-1"))
    store.approve(
        "parallel-1", plan_sha256=first["plan_sha256"], approved_by="operator"
    )
    second = store.create(_project_plan("parallel-2"))
    invoked: list[str] = []

    with pytest.raises(ResearchProjectError, match="parallel-2"):
        execute_parallel_research_runs(
            store,
            ["parallel-1", "parallel-2"],
            runner=lambda project_id: invoked.append(project_id) or _child_result(project_id),
            configuration={"language": "en"},
            maximum_workers=2,
        )
    assert invoked == []

    store.approve(
        "parallel-2", plan_sha256=second["plan_sha256"], approved_by="operator"
    )
    barrier = threading.Barrier(2, timeout=2)

    def runner(project_id: str) -> dict:
        barrier.wait()
        return _child_result(project_id)

    result = execute_parallel_research_runs(
        store,
        ["parallel-1", "parallel-2"],
        runner=runner,
        configuration={"language": "en", "sources_per_subquestion": 2},
        maximum_workers=2,
    )

    assert result["schema_version"] == PARALLEL_RUN_SCHEMA
    assert result["execution_state"] == "completed"
    assert result["completed_projects"] == 2
    assert result["failed_projects"] == 0
    assert [row["project_id"] for row in result["outcomes"]] == [
        "parallel-1",
        "parallel-2",
    ]
    assert result["specification"]["maximum_workers"] == 2
    assert result["batch_sha256"]


def test_parallel_runs_preserve_partial_failure_receipt(tmp_path: Path) -> None:
    store = ResearchProjectStore(tmp_path / "private" / "projects.sqlite3")
    for project_id in ("parallel-1", "parallel-2"):
        created = store.create(_project_plan(project_id))
        store.approve(
            project_id,
            plan_sha256=created["plan_sha256"],
            approved_by="operator",
        )

    def runner(project_id: str) -> dict:
        if project_id == "parallel-2":
            raise RuntimeError("observed provider outage")
        return _child_result(project_id)

    result = execute_parallel_research_runs(
        store,
        ["parallel-1", "parallel-2"],
        runner=runner,
        configuration={"language": "en"},
        maximum_workers=2,
    )

    assert result["execution_state"] == "partial_failure"
    assert result["completed_projects"] == 1
    assert result["failed_projects"] == 1
    assert result["outcomes"][1] == {
        "project_id": "parallel-2",
        "status": "failed",
        "error_type": "RuntimeError",
        "error": "observed provider outage",
    }






def test_local_only_cli_archives_researches_and_resumes_without_web(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    database = tmp_path / "private" / "projects.sqlite3"
    archive = tmp_path / "archive"
    runs = tmp_path / "runs"
    document = tmp_path / "operator-notes.md"
    document.write_text(
        "# Comparative outcomes\n\n"
        "Approach A and approach B outcomes were compared in a controlled evaluation. "
        "Approach A reduced median latency, while reliability was similar.\n",
        encoding="utf-8",
    )
    store = ResearchProjectStore(database)
    created = store.create(_local_plan())
    store.approve(
        "run-project", plan_sha256=created["plan_sha256"], approved_by="operator"
    )

    def forbidden_web(_: object) -> dict[str, object]:
        raise AssertionError("local-only run attempted to construct web providers")

    monkeypatch.setattr(scientific_pipeline_cli, "_run_providers", forbidden_web)
    arguments = [
        "project",
        "--project-database",
        str(database),
        "run",
        "run-project",
        "--local-only",
        "--local-source",
        "Q1",
        str(document),
        "--local-archived-at",
        "2026-08-30T12:00:00+00:00",
        "--repository-root",
        str(repository),
        "--archive-root",
        str(archive),
        "--run-root",
        str(runs),
        "--sources-per-subquestion",
        "1",
        "--passages-per-subquestion",
        "2",
    ]
    assert scientific_pipeline_cli.main(arguments) == 0
    first = json.loads(capsys.readouterr().out)
    bundle = json.loads(Path(first["bundle_path"]).read_text(encoding="utf-8"))
    specification_text = json.dumps(bundle["specification"], sort_keys=True)

    assert first["sources_acquired"] == 1
    assert first["evidence_spans"] >= 1
    assert bundle["specification"]["discovery_mode"] == "local_only"
    assert bundle["specification"]["providers"] == []
    assert str(document.resolve()) not in specification_text
    assert bundle["discoveries"][0]["result"]["provider"] == "operator-local-only"
    assert bundle["discoveries"][0]["result"]["claim_authority"] is False
    assert bundle["acquisitions"][0]["source_kind"] == "local_document"
    assert bundle["acquisitions"][0]["trust_class"] == (
        "operator_selected_local_document_untrusted_content"
    )
    assert "local-document://" in bundle["acquisitions"][0]["source_url"]
    local_packet = build_synthesis_packet(_local_plan(), bundle)
    assert local_packet["evidence"][0]["fetched_at"] == "2026-08-30T12:00:00+00:00"
    assert "Extractive research article" in Path(
        first["extractive_article_path"]
    ).read_text(encoding="utf-8")

    resumed_arguments = list(arguments)
    resumed_arguments[resumed_arguments.index("2026-08-30T12:00:00+00:00")] = (
        "2026-08-30T13:00:00+00:00"
    )
    assert scientific_pipeline_cli.main(resumed_arguments) == 0
    resumed = json.loads(capsys.readouterr().out)
    assert resumed["resumed"] is True
    assert resumed["run_id"] == first["run_id"]
    assert resumed["bundle_sha256"] == first["bundle_sha256"]


def test_local_only_run_requires_permitted_source_and_complete_coverage(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    archive = tmp_path / "archive"
    document = tmp_path / "evidence.md"
    document.write_text("Approach A approach B outcomes comparison.", encoding="utf-8")
    local_acquirer = scientific_pipeline_cli.LocalDocumentAcquirer(
        repository_root=repository,
        archive_root=archive,
    )
    receipt = local_acquirer.acquire(
        document, archived_at="2026-08-30T12:00:00+00:00"
    ).receipt_path
    web_acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=archive,
        transport=FakeTransport(),
        resolver=_resolver,
    )

    disallowed_store = ResearchProjectStore(tmp_path / "private" / "web.sqlite3")
    created = disallowed_store.create(_plan())
    disallowed_store.approve(
        "run-project", plan_sha256=created["plan_sha256"], approved_by="operator"
    )
    with pytest.raises(ResearchProjectError, match="does not permit local_document"):
        execute_research_run(
            disallowed_store,
            "run-project",
            acquirer=web_acquirer,
            providers={},
            repository_root=repository,
            run_root=tmp_path / "web-runs",
            local_receipts={"Q1": [receipt]},
            local_only=True,
        )

    local_store = ResearchProjectStore(tmp_path / "private" / "local.sqlite3")
    created = local_store.create(_local_plan())
    local_store.approve(
        "run-project", plan_sha256=created["plan_sha256"], approved_by="operator"
    )
    with pytest.raises(ResearchProjectError, match="requires a local source"):
        execute_research_run(
            local_store,
            "run-project",
            acquirer=web_acquirer,
            providers={},
            repository_root=repository,
            run_root=tmp_path / "local-runs",
            local_only=True,
        )


def test_local_cli_preflights_approval_before_archiving(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    database = tmp_path / "private" / "projects.sqlite3"
    archive = tmp_path / "archive"
    document = tmp_path / "evidence.md"
    document.write_text("Approach A approach B outcomes comparison.", encoding="utf-8")
    ResearchProjectStore(database).create(_local_plan())

    result = scientific_pipeline_cli.main(
        [
            "project",
            "--project-database",
            str(database),
            "run",
            "run-project",
            "--local-only",
            "--local-source",
            "Q1",
            str(document),
            "--repository-root",
            str(repository),
            "--archive-root",
            str(archive),
            "--run-root",
            str(tmp_path / "runs"),
        ]
    )

    assert result == 2
    assert "requires human approval" in capsys.readouterr().err
    assert not archive.exists()


def test_run_rejects_http_success_with_no_retrievable_text(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    store = ResearchProjectStore(tmp_path / "private" / "projects.sqlite3")
    created = store.create(_plan())
    store.approve("run-project", plan_sha256=created["plan_sha256"], approved_by="operator")
    transport = FakeTransport()
    acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=tmp_path / "archive",
        transport=transport,
        resolver=_resolver,
    )
    provider = FakeProvider()
    original = provider.search

    def empty_search(query: str, *, language: str, limit: int = 10) -> dict:
        result = original(query, language=language, limit=limit)
        result["results"] = [
            {
                **result["results"][0],
                "source_url": "https://evidence.example/empty",
            }
        ]
        return result

    provider.search = empty_search  # type: ignore[method-assign]
    with pytest.raises(ResearchProjectError, match="no usable sources"):
        execute_research_run(
            store,
            "run-project",
            acquirer=acquirer,
            providers={provider.name: provider},
            repository_root=repository,
            run_root=tmp_path / "runs",
        )
    assert store.status("run-project")["source_count"] == 0


def test_new_run_reuses_verified_attached_source_at_source_ceiling(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    store = ResearchProjectStore(tmp_path / "private" / "projects.sqlite3")
    plan = _plan()
    plan["stopping_conditions"]["maximum_sources"] = 1
    created = store.create(plan)
    store.approve("run-project", plan_sha256=created["plan_sha256"], approved_by="operator")
    transport = FakeTransport()
    acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=tmp_path / "archive",
        transport=transport,
        resolver=_resolver,
    )
    provider = FakeProvider()

    first = execute_research_run(
        store,
        "run-project",
        acquirer=acquirer,
        providers={provider.name: provider},
        repository_root=repository,
        run_root=tmp_path / "runs",
        sources_per_subquestion=1,
        passages_per_subquestion=1,
    )
    second = execute_research_run(
        store,
        "run-project",
        acquirer=acquirer,
        providers={provider.name: provider},
        repository_root=repository,
        run_root=tmp_path / "runs",
        language="zh",
        sources_per_subquestion=1,
        passages_per_subquestion=1,
    )

    assert first["run_id"] != second["run_id"]
    assert store.status("run-project")["source_count"] == 1
    assert transport.calls == ["https://evidence.example/primary"]
    second_bundle = json.loads(Path(second["bundle_path"]).read_text(encoding="utf-8"))
    assert second_bundle["acquisitions"][0]["acquisition_mode"] == (
        "verified_attached_receipt_reuse"
    )


def test_run_acquires_operator_pinned_source_before_ranked_discovery(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    store = ResearchProjectStore(tmp_path / "private" / "projects.sqlite3")
    created = store.create(_plan())
    store.approve("run-project", plan_sha256=created["plan_sha256"], approved_by="operator")
    transport = FakeTransport()
    acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=tmp_path / "archive",
        transport=transport,
        resolver=_resolver,
    )
    pinned_url = "https://authoritative.example/exact-study"
    provider = FakeProvider()

    def unavailable_search(query: str, *, language: str, limit: int = 10) -> dict:
        raise RuntimeError("discovery provider unavailable")

    provider.search = unavailable_search  # type: ignore[method-assign]

    result = execute_research_run(
        store,
        "run-project",
        acquirer=acquirer,
        providers={"fixture": provider},
        repository_root=repository,
        run_root=tmp_path / "runs",
        sources_per_subquestion=1,
        passages_per_subquestion=1,
        pinned_sources={"Q1": [pinned_url]},
    )

    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    assert transport.calls == [pinned_url]
    assert bundle["specification"]["pinned_sources"] == {"Q1": [pinned_url]}
    assert bundle["discoveries"][0]["result"]["provider"] == "operator-pinned-only"
    assert bundle["selections"][0]["result"]["pinned_source_urls"] == [pinned_url]
    assert bundle["acquisitions"][0]["source_url"] == pinned_url


def test_run_rejects_pin_for_unselected_subquestion(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    store = ResearchProjectStore(tmp_path / "private" / "projects.sqlite3")
    created = store.create(_plan())
    store.approve("run-project", plan_sha256=created["plan_sha256"], approved_by="operator")
    acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=tmp_path / "archive",
        transport=FakeTransport(),
        resolver=_resolver,
    )

    with pytest.raises(ResearchProjectError, match="unselected subquestion"):
        execute_research_run(
            store,
            "run-project",
            acquirer=acquirer,
            providers={"fixture": FakeProvider()},
            repository_root=repository,
            run_root=tmp_path / "runs",
            pinned_sources={"Q9": ["https://authoritative.example/exact-study"]},
        )


def test_run_rejects_archived_source_without_relevant_evidence(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    store = ResearchProjectStore(tmp_path / "private" / "projects.sqlite3")
    created = store.create(_plan())
    store.approve("run-project", plan_sha256=created["plan_sha256"], approved_by="operator")
    transport = FakeTransport()

    def unrelated_fetch(url: str, *, timeout_seconds: int) -> WebResponse:
        transport.calls.append(url)
        return WebResponse(
            url=url,
            status=200,
            headers={"content-type": "text/plain"},
            body=b"Bananas ripen yellow beside an unrelated orchard inventory.",
            fetched_at="2026-08-30T12:00:00+00:00",
        )

    transport.fetch = unrelated_fetch  # type: ignore[method-assign]
    acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=tmp_path / "archive",
        transport=transport,
        resolver=_resolver,
    )

    with pytest.raises(ResearchProjectError, match="no relevant evidence passages"):
        execute_research_run(
            store,
            "run-project",
            acquirer=acquirer,
            providers={"fixture": FakeProvider()},
            repository_root=repository,
            run_root=tmp_path / "runs",
            sources_per_subquestion=1,
        )


def test_implementation_identity_uses_installed_allowlist_not_evidence_root(tmp_path):
    from twin_core.research_run import _implementation_identity, RESEARCH_SOURCE_FILES

    first = _implementation_identity(tmp_path)
    (tmp_path / "private-notes.txt").write_text("synthetic excluded text")
    second = _implementation_identity(tmp_path)
    assert first == second
    assert first["research_source_files"] == len(RESEARCH_SOURCE_FILES) > 0


def test_implementation_identity_rejects_missing_or_symlinked_code(tmp_path, monkeypatch):
    from twin_core import research_run

    package = tmp_path / "twin_core"
    package.mkdir()
    monkeypatch.setattr(research_run, "__file__", str(package / "research_run.py"))
    with pytest.raises(ResearchProjectError, match="implementation source unavailable"):
        research_run._implementation_identity(tmp_path)
    for name in research_run.RESEARCH_SOURCE_FILES:
        (package / name).write_text("# synthetic implementation\n")
    original = package / "source_quality.py"
    original.unlink()
    original.symlink_to(package / "research_export.py")
    with pytest.raises(ResearchProjectError, match="implementation source unavailable"):
        research_run._implementation_identity(tmp_path)


def test_parallel_cli_writes_owner_only_batch_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "private" / "projects.sqlite3"
    store = ResearchProjectStore(database)
    for project_id in ("parallel-1", "parallel-2"):
        created = store.create(_project_plan(project_id))
        store.approve(
            project_id,
            plan_sha256=created["plan_sha256"],
            approved_by="operator",
        )
    repository = tmp_path / "repository"
    repository.mkdir()
    barrier = threading.Barrier(2, timeout=2)

    def fake_run(store: ResearchProjectStore, project_id: str, **kwargs: object) -> dict:
        del store, kwargs
        barrier.wait()
        return _child_result(project_id)

    monkeypatch.setattr(scientific_pipeline_cli, "execute_research_run", fake_run)
    output = tmp_path / "private" / "parallel-receipt.json"
    assert (
        scientific_pipeline_cli.main(
            [
                "project",
                "--project-database",
                str(database),
                "run-parallel",
                "parallel-1",
                "parallel-2",
                "--maximum-workers",
                "2",
                "--repository-root",
                str(repository),
                "--archive-root",
                str(tmp_path / "archive"),
                "--run-root",
                str(tmp_path / "runs"),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    batch = json.loads(output.read_text(encoding="utf-8"))
    assert summary["execution_state"] == "completed"
    assert summary["completed_projects"] == 2
    assert batch["batch_sha256"] == summary["batch_sha256"]
    assert batch["specification"]["maximum_workers"] == 2
    assert output.stat().st_mode & 0o777 == 0o600


def test_approved_project_run_is_grounded_append_only_and_resumable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    store = ResearchProjectStore(tmp_path / "private" / "projects.sqlite3")
    created = store.create(_plan())
    store.approve(
        "run-project", plan_sha256=created["plan_sha256"], approved_by="operator"
    )
    transport = FakeTransport()
    acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=tmp_path / "archive",
        transport=transport,
        resolver=_resolver,
    )
    provider = FakeProvider()

    result = execute_research_run(
        store,
        "run-project",
        acquirer=acquirer,
        providers={provider.name: provider},
        repository_root=repository,
        run_root=tmp_path / "runs",
        sources_per_subquestion=2,
        passages_per_subquestion=2,
    )
    assert result["sources_acquired"] == 2
    assert result["evidence_spans"] == 2
    assert result["claim_authority"] is False
    brief = Path(result["evidence_brief_path"]).read_text(encoding="utf-8")
    assert "machine-retrieved evidence brief" in brief
    assert "Archived text offset" in brief
    assert "No claim in this brief has been proposed" in brief
    article = Path(result["extractive_article_path"]).read_text(encoding="utf-8")
    assert "Extractive research article" in article
    assert "https://evidence.example/primary" in article
    assert "https://independent.example/study" in article
    assert "Generation mode: `deterministic-extractive`" in article
    assert result["official_evaluation_state"] == "raw_article_ready_not_judged"
    run_bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    packet = build_synthesis_packet(_plan(), run_bundle)
    assert packet["outline_review"] == {
        "state": "approved_plan_projection",
        "claim_authority": False,
    }
    outline_input = {
        "schema_version": OUTLINE_PROPOSAL_SCHEMA,
        "packet_sha256": packet["packet_sha256"],
        "project_id": packet["project_id"],
        "run_id": packet["run_id"],
        "sections": [
            {
                "section_id": "Q1",
                "heading": "Human-reviewed comparison",
                "rationale": "Lead with the approved comparison question and its evidence.",
            }
        ],
    }
    validated_outline = validate_outline_proposal(packet, outline_input)
    outline_path = tmp_path / "outline-proposal.json"
    outline_path.write_text(json.dumps(outline_input), encoding="utf-8")
    assert (
        scientific_pipeline_cli.main(
            [
                "project",
                "--project-database",
                str(store.database),
                "propose-outline",
                "run-project",
                result["bundle_path"],
                str(outline_path),
                "model",
                "--recorded-at",
                "2026-08-30T12:10:00+00:00",
            ]
        )
        == 0
    )
    outline_receipt = json.loads(capsys.readouterr().out)
    assert outline_receipt["outline_sha256"] == validated_outline["outline_sha256"]
    assert (
        scientific_pipeline_cli.main(
            [
                "project",
                "--project-database",
                str(store.database),
                "review-outline",
                "run-project",
                outline_receipt["outline_id"],
                "accept",
                "operator",
                "Section order and emphasis checked against the evidence.",
                "--reviewed-at",
                "2026-08-30T12:11:00+00:00",
            ]
        )
        == 0
    )
    review_receipt = json.loads(capsys.readouterr().out)
    with pytest.raises(ResearchProjectError, match="already has a human review"):
        store.review_outline(
            "run-project",
            outline_id=outline_receipt["outline_id"],
            decision="accept",
            reviewed_by="operator",
            notes="Duplicate decision.",
        )
    accepted = store.accepted_outline(
        "run-project", packet_sha256=packet["packet_sha256"]
    )
    assert accepted is not None
    reviewed_packet = apply_reviewed_outline(packet, accepted)
    assert reviewed_packet["outline"][0]["heading"] == "Human-reviewed comparison"
    assert reviewed_packet["outline_review"]["state"] == "human_accepted"
    assert reviewed_packet["outline_review"]["reviewer_kind"] == "human"
    controlled_canary_packet = apply_reviewed_outline(
        packet, {**accepted, "reviewer_kind": "controlled_canary"}
    )
    assert (
        controlled_canary_packet["outline_review"]["state"]
        == "controlled_canary_accepted"
    )
    with pytest.raises(ResearchProjectError, match="reviewer kind"):
        store.review_outline(
            "run-project",
            outline_id=outline_receipt["outline_id"],
            decision="accept",
            reviewed_by="fixture",
            reviewer_kind="model",
            notes="Invalid actor kind.",
        )
    with pytest.raises(ResearchExportError, match="invalid reviewer kind"):
        apply_reviewed_outline(packet, {**accepted, "reviewer_kind": "model"})
    assert reviewed_packet["outline_review"]["review_event_sha256"] == review_receipt[
        "event_sha256"
    ]
    assert reviewed_packet["packet_sha256"] != packet["packet_sha256"]
    packet_output = tmp_path / "reviewed-packet.json"
    assert (
        scientific_pipeline_cli.main(
            [
                "project",
                "--project-database",
                str(store.database),
                "synthesis-packet",
                "run-project",
                result["bundle_path"],
                str(packet_output),
            ]
        )
        == 0
    )
    packet_receipt = json.loads(capsys.readouterr().out)
    cli_packet = json.loads(packet_output.read_text(encoding="utf-8"))
    assert packet_receipt["outline_review_state"] == "human_accepted"
    assert cli_packet == reviewed_packet
    bypassed_outline = {
        "schema_version": SYNTHESIS_PROPOSAL_SCHEMA,
        "packet_sha256": reviewed_packet["packet_sha256"],
        "run_id": reviewed_packet["run_id"],
        "sections": [
            {
                "section_id": "Q1",
                "heading": packet["outline"][0]["heading"],
                "paragraphs": [
                    {
                        "text": "Comparative outcomes for approach A and approach B are reported.",
                        "evidence_ids": ["E1"],
                    }
                ],
            }
        ],
    }
    with pytest.raises(ResearchExportError, match="heading differs"):
        validate_synthesis_proposal(reviewed_packet, bypassed_outline)
    reviewed_synthesis = json.loads(json.dumps(bypassed_outline))
    reviewed_synthesis["sections"][0]["heading"] = "Human-reviewed comparison"
    assert validate_synthesis_proposal(reviewed_packet, reviewed_synthesis)["sections"][0][
        "section_id"
    ] == "Q1"
    missing_section = {**outline_input, "sections": []}
    with pytest.raises(ResearchExportError, match="non-empty array"):
        validate_outline_proposal(packet, missing_section)
    stale_review = {**accepted, "packet_sha256": "0" * 64}
    with pytest.raises(ResearchExportError, match="stale"):
        apply_reviewed_outline(packet, stale_review)
    supplement_plan = json.loads(json.dumps(_plan()))
    supplement_plan["project_id"] = "run-project-supplement"
    supplement_run = json.loads(json.dumps(run_bundle))
    supplement_run["project_id"] = "run-project-supplement"
    supplement_run["run_id"] = "supplement-run"
    supplement_run["specification"]["project_id"] = "run-project-supplement"
    composite = build_synthesis_packet(
        _plan(), run_bundle, supplements=[(supplement_plan, supplement_run)]
    )
    assert composite["run_id"].startswith("composite-")
    assert len(composite["component_runs"]) == 2
    assert len(composite["evidence"]) == len(packet["evidence"])
    assert composite["outline"][0]["section_id"] == "run-project:Q1"
    assert composite["outline"][1]["section_id"] == "run-project-supplement:Q1"
    assert composite["evidence"][0]["source_project_id"] == "run-project"
    assert composite["packet_sha256"] != packet["packet_sha256"]
    proposal = {
        "schema_version": SYNTHESIS_PROPOSAL_SCHEMA,
        "packet_sha256": packet["packet_sha256"],
        "run_id": packet["run_id"],
        "sections": [
            {
                "section_id": "Q1",
                "heading": packet["outline"][0]["heading"],
                "paragraphs": [
                    {
                            "text": (
                                "Comparative outcomes for approach A and approach B are reported. "
                                "[Untrusted link](https://untrusted.example)"
                            ),
                        "evidence_ids": ["E1"],
                    }
                ],
            }
        ],
    }
    validated = validate_synthesis_proposal(packet, proposal)
    synthesis = render_synthesis_article(packet, proposal)
    assert validated["validation"]["citation_coverage"] == 1.0
    assert "[E1](https://" in synthesis
    assert "https://evidence.example/primary" in synthesis
    assert "https://independent.example/study" in synthesis
    assert "\\[Untrusted link\\]\\(https://untrusted.example\\)" in synthesis
    assert "Semantic entailment: `not established`" in synthesis
    broken = {**proposal, "packet_sha256": "0" * 64}
    with pytest.raises(ResearchExportError, match="different evidence packet"):
        validate_synthesis_proposal(packet, broken)
    tampered_packet = {**packet, "question": "A different question"}
    with pytest.raises(ResearchExportError, match="packet hash mismatch"):
        validate_synthesis_proposal(tampered_packet, proposal)
    assert store.run_state("run-project", result["run_id"])["completed"] is True
    assert store.status("run-project")["source_count"] == 2

    resumed = execute_research_run(
        store,
        "run-project",
        acquirer=acquirer,
        providers={provider.name: provider},
        repository_root=repository,
        run_root=tmp_path / "runs",
        sources_per_subquestion=2,
        passages_per_subquestion=2,
    )
    assert resumed["resumed"] is True
    assert resumed["bundle_sha256"] == result["bundle_sha256"]
    assert provider.calls == 1
    assert len(transport.calls) == 2
