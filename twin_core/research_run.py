"""Resumable orchestration over approved research projects and archived public evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from .passage_retrieval import index_archived_receipts, retrieve_passages
from .research_export import render_evidence_brief, render_extractive_article
from .research_project import ResearchProjectError, ResearchProjectStore
from .web_acquisition import (
    LOCAL_SOURCE_SCHEMA,
    PublicWebAcquirer,
    WebAcquisitionError,
    archived_source_json,
    load_archived_text,
)
from .web_discovery import fuse_discoveries, select_relevant_discoveries

RUN_SCHEMA = "giga.research-run.v1"
RUN_ALGORITHM_VERSION = "2026-08-30.11"
PARALLEL_RUN_SCHEMA = "giga.research-parallel-run.v1"
PARALLEL_RUN_ALGORITHM_VERSION = "2026-08-31.1"
DEFAULT_RUN_ROOT = Path.home() / ".giga" / "research-runs"


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, *, language: str, limit: int = 10) -> dict[str, Any]: ...


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


# Exact runtime closure. Never scan the mixed source/private repository.
RESEARCH_SOURCE_FILES = (
    "__init__.py", "source_quality.py", "web_acquisition.py", "research_export.py",
    "research_project.py", "passage_retrieval.py", "web_discovery.py",
    "research_run.py", "scientific_pipeline_cli.py",
)


def _implementation_identity(repository_root: Path) -> dict[str, Any]:
    # repository_root constrains evidence placement, not which implementation runs.
    # Hash the executing package so installed wheels and synthetic work roots cannot
    # silently acquire the identity of an empty or unrelated source directory.
    module = Path(__file__).absolute().parent
    root = module.parent
    rows = []
    for name in sorted(RESEARCH_SOURCE_FILES):
        path = module / name
        if path.is_symlink() or not path.is_file():
            raise ResearchProjectError(f"research implementation source unavailable: {name}")
        rows.append({"path": f"twin_core/{name}", "sha256": _sha256(path.read_bytes())})
    if not rows:
        raise ResearchProjectError("research implementation identity cannot be empty")
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all", "--",
             *[row["path"] for row in rows]],
            cwd=root, check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        commit = None
        dirty = None
    return {
        "repository_commit": commit,
        "repository_dirty": dirty,
        "research_source_files": len(rows),
        "research_source_sha256": _sha256(_canonical_bytes(rows)),
    }


def _private_run_root(path: Path, repository_root: Path) -> Path:
    repository = repository_root.resolve(strict=True)
    root = path.expanduser().resolve()
    if root == repository or repository in root.parents:
        raise ResearchProjectError("research run artifacts must remain outside the repository")
    if root.exists() and root.is_symlink():
        raise ResearchProjectError("research run root cannot be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root


def _write_artifact(directory: Path, label: str, value: object) -> tuple[Path, str]:
    data = _canonical_bytes(value)
    digest = _sha256(data)
    path = directory / f"{label}-{digest}.json"
    if path.exists() and path.read_bytes() != data:
        raise ResearchProjectError("content-addressed research run artifact differs")
    if not path.exists():
        path.write_bytes(data)
        os.chmod(path, 0o600)
    return path, digest


def _read_artifact(details: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(str(details["artifact_path"])).resolve(strict=True)
    raw = path.read_bytes()
    if _sha256(raw) != details.get("artifact_sha256"):
        raise ResearchProjectError("recorded research run artifact differs")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ResearchProjectError("research run artifact must contain an object")
    return value


def execute_parallel_research_runs(
    store: ResearchProjectStore,
    project_ids: Sequence[str],
    *,
    runner: Callable[[str], Mapping[str, Any]],
    configuration: Mapping[str, Any],
    maximum_workers: int = 3,
) -> dict[str, Any]:
    """Run independent approved projects concurrently after an all-project preflight."""
    if isinstance(project_ids, (str, bytes)) or not 2 <= len(project_ids) <= 32:
        raise ResearchProjectError("parallel research requires from 2 to 32 projects")
    clean_ids: list[str] = []
    for project_id in project_ids:
        if not isinstance(project_id, str) or not project_id.strip():
            raise ResearchProjectError("parallel project_id must be a non-empty string")
        if project_id in clean_ids:
            raise ResearchProjectError("parallel project_ids must be unique")
        clean_ids.append(project_id)
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise ResearchProjectError("maximum_workers must be from 1 to 8")
    if not isinstance(configuration, Mapping):
        raise ResearchProjectError("parallel run configuration must be an object")
    clean_configuration = json.loads(_canonical_bytes(configuration))

    projects = []
    for project_id in clean_ids:
        state = store.export_state(project_id)
        if not state["status"]["approved"]:
            raise ResearchProjectError(
                f"project plan requires human approval before parallel run: {project_id}"
            )
        projects.append(
            {
                "project_id": project_id,
                "plan_sha256": state["status"]["plan_sha256"],
            }
        )
    workers = min(maximum_workers, len(clean_ids))
    specification = {
        "algorithm_version": PARALLEL_RUN_ALGORITHM_VERSION,
        "projects": projects,
        "maximum_workers": workers,
        "configuration": clean_configuration,
    }
    batch_id = _sha256(_canonical_bytes(specification))
    outcomes: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(
        max_workers=workers,
        thread_name_prefix="giga-research-frontier",
    ) as executor:
        future_projects = {
            executor.submit(runner, project_id): project_id for project_id in clean_ids
        }
        for future in as_completed(future_projects):
            project_id = future_projects[future]
            try:
                result = future.result()
                if not isinstance(result, Mapping):
                    raise ResearchProjectError("parallel child result must be an object")
                clean_result = json.loads(_canonical_bytes(result))
                if (
                    clean_result.get("schema_version") != RUN_SCHEMA
                    or clean_result.get("project_id") != project_id
                ):
                    raise ResearchProjectError(
                        "parallel child result does not match its approved project"
                    )
                outcomes[project_id] = {
                    "project_id": project_id,
                    "status": "completed",
                    "result": clean_result,
                }
            except Exception as exc:
                outcomes[project_id] = {
                    "project_id": project_id,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
    ordered = [outcomes[project_id] for project_id in clean_ids]
    failures = [row for row in ordered if row["status"] == "failed"]
    result = {
        "schema_version": PARALLEL_RUN_SCHEMA,
        "batch_id": batch_id,
        "specification": specification,
        "outcomes": ordered,
        "completed_projects": sum(row["status"] == "completed" for row in ordered),
        "failed_projects": len(failures),
        "execution_state": "partial_failure" if failures else "completed",
        "claim_authority": False,
        "behaviour_lineage": [
            {
                "project": "InternLM/MindSearch",
                "commit": "7952c5f8a956fe6a44228a6a7d528a35340e7c87",
                "licence": "Apache-2.0",
                "adopted": "concurrent execution of independent graph nodes",
            }
        ],
    }
    return {**result, "batch_sha256": _sha256(_canonical_bytes(result))}


def execute_research_run(
    store: ResearchProjectStore,
    project_id: str,
    *,
    acquirer: PublicWebAcquirer,
    providers: Mapping[str, SearchProvider],
    repository_root: Path,
    run_root: Path = DEFAULT_RUN_ROOT,
    language: str = "en",
    maximum_subquestions: int = 1,
    discovery_limit: int = 4,
    sources_per_subquestion: int = 2,
    passages_per_subquestion: int = 4,
    per_domain: int = 1,
    pinned_sources: Mapping[str, Sequence[str]] | None = None,
    local_receipts: Mapping[str, Sequence[Path]] | None = None,
    local_only: bool = False,
) -> dict[str, Any]:
    """Run approved archived-source research, resuming from ledgered artifacts."""
    if language not in {"en", "zh"}:
        raise ResearchProjectError("research run language must be en or zh")
    for field, value in (
        ("maximum_subquestions", maximum_subquestions),
        ("discovery_limit", discovery_limit),
        ("sources_per_subquestion", sources_per_subquestion),
        ("passages_per_subquestion", passages_per_subquestion),
        ("per_domain", per_domain),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ResearchProjectError(f"{field} must be a positive integer")
    if not providers and not local_only:
        raise ResearchProjectError("research run requires at least one discovery provider")

    state = store.export_state(project_id)
    if not state["status"]["approved"]:
        raise ResearchProjectError("project plan requires human approval before a run")
    plan = state["plan"]
    selected_questions = plan["subquestions"][:maximum_subquestions]
    selected_question_ids = {str(row["id"]) for row in selected_questions}
    normalised_pins: dict[str, list[str]] = {}
    for question_id, urls in (pinned_sources or {}).items():
        if question_id not in selected_question_ids:
            raise ResearchProjectError(
                f"pinned source references unselected subquestion {question_id!r}"
            )
        if isinstance(urls, (str, bytes)):
            raise ResearchProjectError("pinned source URLs must be a sequence")
        unique_urls: list[str] = []
        for url in urls:
            if not isinstance(url, str) or not url.strip():
                raise ResearchProjectError("pinned source URL must be a non-empty string")
            if url not in unique_urls:
                unique_urls.append(url)
        if len(unique_urls) > sources_per_subquestion:
            raise ResearchProjectError(
                f"pinned sources for {question_id} exceed sources_per_subquestion"
            )
        if unique_urls:
            normalised_pins[question_id] = unique_urls
    if local_only and normalised_pins:
        raise ResearchProjectError("local-only research cannot include pinned web sources")
    prepared_local: dict[str, list[dict[str, Any]]] = {}
    questions_by_id = {str(row["id"]): row for row in selected_questions}
    for question_id, receipt_paths in (local_receipts or {}).items():
        question = questions_by_id.get(question_id)
        if question is None:
            raise ResearchProjectError(
                f"local source references unselected subquestion {question_id!r}"
            )
        if "local_document" not in question["source_types"]:
            raise ResearchProjectError(
                f"subquestion {question_id!r} does not permit local_document sources"
            )
        if isinstance(receipt_paths, (str, bytes)):
            raise ResearchProjectError("local source receipts must be a sequence of paths")
        rows: list[dict[str, Any]] = []
        for receipt_path in receipt_paths:
            try:
                receipt_sha, receipt, text = load_archived_text(
                    Path(receipt_path), acquirer.archive
                )
            except (OSError, WebAcquisitionError) as exc:
                raise ResearchProjectError(f"local source receipt is invalid: {exc}") from exc
            if (
                receipt.get("schema_version") != LOCAL_SOURCE_SCHEMA
                or receipt.get("source_kind") != "local_document"
            ):
                raise ResearchProjectError("local source receipt has the wrong source type")
            if not text.strip():
                raise ResearchProjectError("local source receipt has no retrievable text")
            if any(row["receipt_sha256"] == receipt_sha for row in rows):
                raise ResearchProjectError("local source receipt list contains a duplicate")
            rows.append(
                {
                    **receipt,
                    "receipt_path": str(Path(receipt_path).resolve(strict=True)),
                    "receipt_sha256": receipt_sha,
                }
            )
        if len(rows) > sources_per_subquestion:
            raise ResearchProjectError(
                f"local sources for {question_id} exceed sources_per_subquestion"
            )
        if rows:
            prepared_local[question_id] = rows
    if local_only:
        missing_local = [
            str(question["id"])
            for question in selected_questions
            if not prepared_local.get(str(question["id"]))
        ]
        if missing_local:
            raise ResearchProjectError(
                "local-only research requires a local source for every selected "
                f"subquestion: {', '.join(missing_local)}"
            )
    specification = {
        "algorithm_version": RUN_ALGORITHM_VERSION,
        "implementation": _implementation_identity(repository_root),
        "project_id": project_id,
        "plan_sha256": state["status"]["plan_sha256"],
        "language": language,
        "subquestion_ids": [row["id"] for row in selected_questions],
        "providers": sorted(providers),
        "discovery_mode": "local_only" if local_only else "web_or_hybrid",
        "discovery_limit": discovery_limit,
        "sources_per_subquestion": sources_per_subquestion,
        "passages_per_subquestion": passages_per_subquestion,
        "per_domain": per_domain,
        "pinned_sources": normalised_pins,
        "local_sources": {
            question_id: [
                {
                    "content_sha256": row["content_sha256"],
                    "text_sha256": row["text_sha256"],
                    "source_uri": row["final_url"],
                    "display_name": row["display_name"],
                }
                for row in rows
            ]
            for question_id, rows in sorted(prepared_local.items())
        },
    }
    run_id = _sha256(_canonical_bytes(specification))
    prior = store.run_state(project_id, run_id)
    if prior["completed"]:
        completed = next(
            row for row in reversed(prior["events"]) if row["event_type"] == "research_run_completed"
        )
        return {**completed["details"], "resumed": True, "run_id": run_id}

    root = _private_run_root(run_root, repository_root)
    run_directory = root / run_id
    run_directory.mkdir(parents=True, exist_ok=True)
    os.chmod(run_directory, 0o700)
    if not prior["events"]:
        store.record_run_event(
            project_id,
            event_type="research_run_started",
            run_id=run_id,
            details={"specification": specification, "started_at": _utc_now()},
        )

    discoveries: list[dict[str, Any]] = []
    acquisitions: list[dict[str, Any]] = []
    retrievals: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    evidence_spans: list[dict[str, str]] = []
    events = store.run_state(project_id, run_id)["events"]
    acquired_by_url = {
        str(row["details"]["source_url"]): row["details"]
        for row in events
        if row["event_type"] == "research_run_source_acquired"
    }
    attached_by_url: dict[str, dict[str, Any]] = {}
    for source in state["matrix"]["sources"]:
        receipt_sha = source.get("receipt_sha256")
        if not isinstance(receipt_sha, str):
            continue
        receipt_path = acquirer.archive / "receipts" / receipt_sha[:2] / f"{receipt_sha}.json"
        try:
            verified_sha, receipt, _ = load_archived_text(receipt_path, acquirer.archive)
        except (OSError, WebAcquisitionError):
            continue
        if verified_sha != receipt_sha:
            continue
        reusable = {
            **receipt,
            "receipt_path": str(receipt_path),
            "receipt_sha256": verified_sha,
        }
        for source_url in (receipt.get("requested_url"), receipt.get("final_url")):
            if isinstance(source_url, str):
                attached_by_url[source_url] = reusable

    try:
        for question in selected_questions:
            question_id = question["id"]
            prior_discovery = next(
                (
                    row
                    for row in events
                    if row["event_type"] == "research_run_discovery_completed"
                    and row["details"].get("subquestion_id") == question_id
                ),
                None,
            )
            if prior_discovery:
                discovery = _read_artifact(prior_discovery["details"])
            else:
                provider_results = []
                search_query = " ".join(question["search_terms"])
                if local_only:
                    discovery = {
                        "schema_version": "giga.research-source-discovery.v1",
                        "provider": "operator-local-only",
                        "language": language,
                        "query": search_query,
                        "search_receipts": [],
                        "results": [],
                        "result_count": 0,
                        "trust_class": "operator_selected_local_documents",
                        "claim_authority": False,
                    }
                else:
                    for provider in providers.values():
                        try:
                            provider_results.append(
                                provider.search(
                                    search_query, language=language, limit=discovery_limit
                                )
                            )
                        except Exception as exc:
                            store.record_run_event(
                                project_id,
                                event_type="research_run_discovery_failed",
                                run_id=run_id,
                                details={
                                    "subquestion_id": question_id,
                                    "provider": provider.name,
                                    "query": search_query,
                                    "error_type": type(exc).__name__,
                                    "error": str(exc),
                                },
                            )
                    if not provider_results:
                        if not normalised_pins.get(question_id):
                            raise ResearchProjectError(
                                f"all discovery providers failed for subquestion {question_id}"
                            )
                        discovery = {
                            "schema_version": "giga.research-source-discovery.v1",
                            "provider": "operator-pinned-only",
                            "language": language,
                            "query": search_query,
                            "search_receipts": [],
                            "results": [],
                            "result_count": 0,
                            "trust_class": "operator_selected_urls_untrusted_external_content",
                            "claim_authority": False,
                        }
                    else:
                        discovery = (
                            fuse_discoveries(
                                provider_results, limit=discovery_limit, per_domain=per_domain
                            )
                            if len(provider_results) > 1
                            else provider_results[0]
                        )
                artifact, digest = _write_artifact(
                    run_directory, f"discovery-{question_id}", discovery
                )
                store.record_run_event(
                    project_id,
                    event_type="research_run_discovery_completed",
                    run_id=run_id,
                    details={
                        "subquestion_id": question_id,
                        "artifact_path": str(artifact),
                        "artifact_sha256": digest,
                        "search_receipt_sha256s": [
                            row["sha256"]
                            for row in discovery.get("search_receipts", [])
                        ]
                        or (
                            [discovery["search_receipt_sha256"]]
                            if discovery.get("search_receipt_sha256")
                            else []
                        ),
                    },
                )
            discoveries.append({"subquestion_id": question_id, "result": discovery})

            selection = select_relevant_discoveries(
                " ".join(question["search_terms"]), discovery["results"]
            )
            pinned_urls = normalised_pins.get(question_id, [])
            acquisition_candidates = [
                {
                    "source_url": url,
                    "selection_reason": "operator_pinned",
                    "authority_tier": "unassessed",
                    "authority_score": 0.0,
                }
                for url in pinned_urls
            ]
            acquisition_candidates.extend(
                candidate
                for candidate in selection["accepted"]
                if candidate["source_url"] not in pinned_urls
            )
            local_source_uris = [
                str(row["final_url"])
                for row in prepared_local.get(question_id, [])
            ]
            selection_record = {
                **selection,
                "pinned_source_urls": pinned_urls,
                "local_source_uris": local_source_uris,
                "acquisition_order": [
                    *local_source_uris,
                    *[row["source_url"] for row in acquisition_candidates],
                ],
            }
            selections.append({"subquestion_id": question_id, "result": selection_record})
            if not local_source_uris and not acquisition_candidates:
                raise ResearchProjectError(
                    f"discovery produced no relevant sources for subquestion {question_id}"
                )

            acquired_for_question: list[Path] = []
            for local in prepared_local.get(question_id, []):
                if len(acquired_for_question) >= sources_per_subquestion:
                    break
                source_url = str(local["final_url"])
                prior_source = acquired_by_url.get(source_url)
                if prior_source:
                    receipt_path = Path(prior_source["receipt_path"])
                    attached = store.attach_local_document(
                        project_id, receipt_path, acquirer.archive
                    )
                    receipt = {
                        **prior_source,
                        "attachment_status": attached.get("status", "attached"),
                        "acquisition_mode": "resumed_local_receipt",
                    }
                else:
                    current_status = store.status(project_id)
                    if (
                        current_status["source_count"]
                        >= plan["stopping_conditions"]["maximum_sources"]
                        and local["receipt_sha256"]
                        not in current_status["source_receipt_sha256s"]
                    ):
                        break
                    receipt_path = Path(local["receipt_path"])
                    attached = store.attach_local_document(
                        project_id, receipt_path, acquirer.archive
                    )
                    if attached.get("status") == "rejected_near_duplicate":
                        rejection = {
                            "source_url": source_url,
                            "subquestion_id": question_id,
                            "error_type": "NearDuplicateSource",
                            "error": "local document was rejected as near-duplicate evidence",
                        }
                        store.record_run_event(
                            project_id,
                            event_type="research_run_source_failed",
                            run_id=run_id,
                            details=rejection,
                        )
                        acquisitions.append({**rejection, "status": "rejected"})
                        continue
                    receipt = {
                        **local,
                        "source_url": source_url,
                        "subquestion_id": question_id,
                        "attachment_status": attached.get("status", "attached"),
                        "acquisition_mode": (
                            "verified_local_receipt_reuse"
                            if attached.get("status")
                            else "operator_selected_local_document"
                        ),
                    }
                    store.record_run_event(
                        project_id,
                        event_type="research_run_source_acquired",
                        run_id=run_id,
                        details=receipt,
                    )
                    acquired_by_url[source_url] = receipt
                acquired_for_question.append(receipt_path)
                acquisitions.append({**receipt, "status": "acquired"})
            for candidate in acquisition_candidates:
                if len(acquired_for_question) >= sources_per_subquestion:
                    break
                source_url = candidate["source_url"]
                prior_source = acquired_by_url.get(source_url)
                if prior_source:
                    receipt_path = Path(prior_source["receipt_path"])
                    attached = store.attach_web_source(project_id, receipt_path, acquirer.archive)
                    receipt = {
                        **prior_source,
                        "attachment_status": attached.get("status", "attached"),
                    }
                elif source_url in attached_by_url:
                    reusable = attached_by_url[source_url]
                    receipt_path = Path(reusable["receipt_path"])
                    attached = store.attach_web_source(project_id, receipt_path, acquirer.archive)
                    receipt = {
                        **reusable,
                        "source_url": source_url,
                        "subquestion_id": question_id,
                        "attachment_status": attached.get("status", "already_attached"),
                        "acquisition_mode": "verified_attached_receipt_reuse",
                    }
                    store.record_run_event(
                        project_id,
                        event_type="research_run_source_acquired",
                        run_id=run_id,
                        details=receipt,
                    )
                    acquired_by_url[source_url] = receipt
                else:
                    if (
                        store.status(project_id)["source_count"]
                        >= plan["stopping_conditions"]["maximum_sources"]
                    ):
                        break
                    try:
                        archived = acquirer.acquire(source_url)
                        if not archived.text_sha256 or archived.text_characters < 1:
                            unusable = {
                                "source_url": source_url,
                                "subquestion_id": question_id,
                                "error_type": "EmptyTextProjection",
                                "error": "archived source has no retrievable text",
                                "receipt_path": str(archived.receipt_path),
                                "receipt_sha256": archived.receipt_sha256,
                            }
                            store.record_run_event(
                                project_id,
                                event_type="research_run_source_failed",
                                run_id=run_id,
                                details=unusable,
                            )
                            acquisitions.append({**unusable, "status": "rejected"})
                            continue
                        attached = store.attach_web_source(
                            project_id, archived.receipt_path, acquirer.archive
                        )
                        receipt = {
                            **archived_source_json(archived),
                            "source_url": source_url,
                            "subquestion_id": question_id,
                            "attachment_status": attached.get("status", "attached"),
                        }
                        if attached.get("status") == "already_attached_equivalent":
                            canonical_sha = str(attached["receipt_sha256"])
                            canonical_path = (
                                acquirer.archive
                                / "receipts"
                                / canonical_sha[:2]
                                / f"{canonical_sha}.json"
                            )
                            canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
                            receipt = {
                                **canonical,
                                "receipt_path": str(canonical_path),
                                "receipt_sha256": canonical_sha,
                                "source_url": source_url,
                                "subquestion_id": question_id,
                                "attachment_status": "already_attached_equivalent",
                            }
                        if attached.get("status") == "rejected_near_duplicate":
                            rejection = {
                                "source_url": source_url,
                                "subquestion_id": question_id,
                                "error_type": "NearDuplicateSource",
                                "error": "source was rejected as near-duplicate evidence",
                            }
                            store.record_run_event(
                                project_id,
                                event_type="research_run_source_failed",
                                run_id=run_id,
                                details=rejection,
                            )
                            acquisitions.append({**receipt, **rejection, "status": "rejected"})
                            continue
                        store.record_run_event(
                            project_id,
                            event_type="research_run_source_acquired",
                            run_id=run_id,
                            details=receipt,
                        )
                        acquired_by_url[source_url] = receipt
                    except Exception as exc:
                        failure = {
                            "source_url": source_url,
                            "subquestion_id": question_id,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                        store.record_run_event(
                            project_id,
                            event_type="research_run_source_failed",
                            run_id=run_id,
                            details=failure,
                        )
                        acquisitions.append({**failure, "status": "failed"})
                        continue
                receipt_path = Path(receipt["receipt_path"])
                acquired_for_question.append(receipt_path)
                acquisitions.append({**receipt, "status": "acquired"})

            if not acquired_for_question:
                raise ResearchProjectError(
                    f"no usable sources were acquired for subquestion {question_id}"
                )
            passages = index_archived_receipts(acquirer.archive, acquired_for_question)
            retrieval_query = " ".join(
                [question["question"], *question["search_terms"]]
            )
            retrieval = retrieve_passages(
                retrieval_query,
                passages,
                limit=passages_per_subquestion,
                per_source=max(1, passages_per_subquestion),
            )
            if not retrieval["results"]:
                raise ResearchProjectError(
                    f"no relevant evidence passages were retrieved for subquestion {question_id}"
                )
            artifact, digest = _write_artifact(
                run_directory, f"retrieval-{question_id}", retrieval
            )
            store.record_run_event(
                project_id,
                event_type="research_run_retrieval_completed",
                run_id=run_id,
                details={
                    "subquestion_id": question_id,
                    "artifact_path": str(artifact),
                    "artifact_sha256": digest,
                    "result_count": len(retrieval["results"]),
                },
            )
            retrievals.append({"subquestion_id": question_id, "result": retrieval})
            for passage in retrieval["results"]:
                span = store.add_evidence_span(
                    project_id,
                    receipt_sha256=passage["receipt_sha256"],
                    archive_root=acquirer.archive,
                    quote=passage["text"],
                    locator=f"text characters {passage['start']}:{passage['end']}",
                    subquestion_ids=[question_id],
                )
                evidence_spans.append(
                    {
                        "subquestion_id": question_id,
                        "passage_id": passage["passage_id"],
                        **span,
                    }
                )

        bundle = {
            "schema_version": RUN_SCHEMA,
            "run_id": run_id,
            "project_id": project_id,
            "specification": specification,
            "discoveries": discoveries,
            "selections": selections,
            "acquisitions": acquisitions,
            "retrievals": retrievals,
            "evidence_spans": evidence_spans,
            "claim_authority": False,
        }
        bundle_path, bundle_sha = _write_artifact(run_directory, "run", bundle)
        brief = render_evidence_brief(plan, bundle)
        brief_bytes = brief.encode("utf-8")
        brief_sha = _sha256(brief_bytes)
        brief_path = run_directory / f"evidence-brief-{brief_sha}.md"
        if not brief_path.exists():
            brief_path.write_bytes(brief_bytes)
            os.chmod(brief_path, 0o600)
        article = render_extractive_article(plan, bundle)
        article_bytes = article.encode("utf-8")
        article_sha = _sha256(article_bytes)
        article_path = run_directory / f"extractive-article-{article_sha}.md"
        if not article_path.exists():
            article_path.write_bytes(article_bytes)
            os.chmod(article_path, 0o600)
        result = {
            "schema_version": RUN_SCHEMA,
            "project_id": project_id,
            "run_id": run_id,
            "bundle_path": str(bundle_path),
            "bundle_sha256": bundle_sha,
            "evidence_brief_path": str(brief_path),
            "evidence_brief_sha256": brief_sha,
            "extractive_article_path": str(article_path),
            "extractive_article_sha256": article_sha,
            "article_generation_mode": "deterministic-extractive",
            "official_evaluation_state": "raw_article_ready_not_judged",
            "sources_acquired": sum(row["status"] == "acquired" for row in acquisitions),
            "source_failures": sum(row["status"] != "acquired" for row in acquisitions),
            "evidence_spans": len(evidence_spans),
            "claim_authority": False,
            "completed_at": _utc_now(),
        }
        store.record_run_event(
            project_id,
            event_type="research_run_completed",
            run_id=run_id,
            details=result,
        )
        return {**result, "resumed": False}
    except Exception as exc:
        store.record_run_event(
            project_id,
            event_type="research_run_failed",
            run_id=run_id,
            details={"error_type": type(exc).__name__, "error": str(exc), "failed_at": _utc_now()},
        )
        raise
