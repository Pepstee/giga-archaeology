from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from twin_core.web_acquisition import PublicWebAcquirer, WebResponse
from twin_core.web_discovery import (
    DISCOVERY_SCHEMA,
    DuckDuckGoSearchProvider,
    OpenAlexSearchProvider,
    WebDiscoveryError,
    WikipediaSearchProvider,
    fuse_discoveries,
    select_relevant_discoveries,
)


class FakeTransport:
    name = "fake:static"

    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.urls: list[str] = []

    def fetch(self, url: str, *, timeout_seconds: int) -> WebResponse:
        self.urls.append(url)
        return WebResponse(
            url=url,
            status=200,
            headers={"content-type": "application/json"},
            body=json.dumps(self.payload).encode(),
            fetched_at="2026-08-30T10:00:00+00:00",
        )


def _resolver(host: str, port: int, *, type: int) -> list[tuple]:
    assert host in {
        "api.openalex.org",
        "en.wikipedia.org",
        "html.duckduckgo.com",
        "zh.wikipedia.org",
    }
    assert type == socket.SOCK_STREAM
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("208.80.154.224", port))]


def _provider(tmp_path: Path, payload: object) -> tuple[WikipediaSearchProvider, FakeTransport]:
    repository = tmp_path / "repository"
    repository.mkdir(parents=True)
    transport = FakeTransport(payload)
    acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=tmp_path / "archive",
        transport=transport,
        resolver=_resolver,
    )
    return WikipediaSearchProvider(acquirer), transport


def test_discovers_bilingual_sources_with_archived_query_receipt(tmp_path: Path) -> None:
    provider, transport = _provider(
        tmp_path,
        {
            "query": {
                "search": [
                    {
                        "ns": 0,
                        "title": "Retrieval-augmented generation",
                        "pageid": 123,
                        "snippet": "A <span class='searchmatch'>retrieval</span> technique.",
                        "timestamp": "2026-08-01T00:00:00Z",
                    }
                ]
            }
        },
    )
    result = provider.search("retrieval generation", language="en", limit=5)
    assert result["result_count"] == 1
    assert result["results"][0]["source_url"].endswith("Retrieval-augmented_generation")
    assert result["results"][0]["snippet"] == "A retrieval technique."
    assert result["search_receipt_sha256"]
    assert Path(result["search_receipt_path"]).is_file()
    assert "srsearch=retrieval+generation" in transport.urls[0]
    assert result["claim_authority"] is False


def test_provider_rejects_bad_language_limit_and_malformed_results(tmp_path: Path) -> None:
    provider, _ = _provider(tmp_path, {"query": {"search": []}})
    with pytest.raises(WebDiscoveryError, match="language"):
        provider.search("query", language="ko")
    with pytest.raises(WebDiscoveryError, match="limit"):
        provider.search("query", language="en", limit=0)

    malformed, _ = _provider(tmp_path / "other", {"query": {"search": [{"title": "No id"}]}})
    with pytest.raises(WebDiscoveryError, match="malformed"):
        malformed.search("query", language="zh")


def test_openalex_discovery_and_provider_fusion_preserve_cost_and_diversity(tmp_path: Path) -> None:
    provider, _ = _provider(
        tmp_path,
        {
            "meta": {"cost_usd": 0.001},
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.1/example",
                    "display_name": "A primary paper",
                    "publication_year": 2025,
                    "primary_location": {
                        "landing_page_url": "https://aclanthology.org/2025.example",
                        "is_oa": True,
                        "raw_source_name": "ACL",
                    },
                    "relevance_score": 100,
                    "abstract_inverted_index": {
                        "Retrieval": [0],
                        "evidence": [1],
                        "supports": [2],
                        "citations": [3],
                    },
                }
            ],
        },
    )
    scholarly = OpenAlexSearchProvider(provider.acquirer).search(
        "retrieval", language="en", limit=5
    )
    assert scholarly["results"][0]["source_url"].startswith("https://aclanthology.org/")
    assert "Retrieval evidence supports citations" in scholarly["results"][0]["snippet"]
    assert scholarly["provider_reported_cost_usd"] == 0.001
    assert scholarly["operator_billed_cost_usd"] == 0.0

    wikipedia = {
        "schema_version": DISCOVERY_SCHEMA,
        "provider": "wikipedia",
        "language": "en",
        "query": "retrieval",
        "search_receipt_sha256": "a" * 64,
        "search_receipt_path": "/private/receipt",
        "results": [
            {
                "rank": 1,
                "title": "Overview",
                "source_url": "https://en.wikipedia.org/wiki/Retrieval",
            }
        ],
    }
    fused = fuse_discoveries([wikipedia, scholarly], limit=2, per_domain=1)
    assert [row["provider"] for row in fused["results"]] == ["wikipedia", "openalex"]
    assert len(fused["search_receipts"]) == 2


def test_source_selection_rejects_high_rank_irrelevance_and_explains_overlap() -> None:
    selected = select_relevant_discoveries(
        "retrieval augmented generation citation correctness",
        [
            {
                "rank": 1,
                "title": "SciPy algorithms",
                "snippet": "Scientific computing in Python.",
                "source_url": "https://example.com/scipy",
                "authority_score": 1.0,
            },
            {
                "rank": 2,
                "title": "Retrieval-augmented generation with correct citations",
                "snippet": "Evidence grounding for generated answers.",
                "source_url": "https://example.com/rag",
                "authority_score": 0.8,
            },
        ],
    )
    assert [row["source_url"] for row in selected["accepted"]] == [
        "https://example.com/rag"
    ]
    assert selected["accepted"][0]["discovery_overlap_count"] >= 2
    assert selected["accepted"][0]["discovery_relevance_score"] >= 4
    assert selected["rejected"][0]["rejection_reason"] == "insufficient_query_overlap"


def test_source_selection_prefers_primary_authority_after_relevance_gate() -> None:
    selected = select_relevant_discoveries(
        "bird migration navigation cues",
        [
            {
                "rank": 1,
                "title": "Bird migration navigation cues guide",
                "snippet": "Bird migration navigation cues.",
                "source_url": "https://example.com/guide",
                "authority_score": 0.4,
            },
            {
                "rank": 2,
                "title": "Bird migration navigation study",
                "snippet": "Migration cues tested experimentally.",
                "source_url": "https://nature.com/articles/example",
                "authority_score": 1.0,
            },
        ],
    )
    assert selected["accepted"][0]["source_url"].startswith("https://nature.com/")


def test_duckduckgo_general_web_results_are_decoded_and_archived(tmp_path: Path) -> None:
    document = b"""
    <div class="result">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Faclanthology.org%2Fpaper%3Fx%3D1&amp;rut=ignored">Ground Every Sentence</a>
      <a class="result__snippet">Retrieval <b>citations</b> improve evidence grounding.</a>
    </div>
    <div class="result">
      <a class="result__a" href="http%3A%2F%2Finsecure.example">Reject insecure</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://example.com:invalid/">Reject invalid port</a>
    </div>
    """

    class HtmlTransport:
        name = "fake:static"

        def fetch(self, url: str, *, timeout_seconds: int) -> WebResponse:
            return WebResponse(
                url=url,
                status=200,
                headers={"content-type": "text/html"},
                body=document,
                fetched_at="2026-08-30T10:00:00+00:00",
            )

    repository = tmp_path / "repository"
    repository.mkdir()
    acquirer = PublicWebAcquirer(
        repository_root=repository,
        archive_root=tmp_path / "archive",
        transport=HtmlTransport(),
        resolver=_resolver,
    )
    result = DuckDuckGoSearchProvider(acquirer).search(
        "retrieval citation grounding", language="en", limit=5
    )
    assert result["result_count"] == 1
    assert result["results"][0]["source_url"] == "https://aclanthology.org/paper?x=1"
    assert result["results"][0]["snippet"] == (
        "Retrieval citations improve evidence grounding."
    )
    assert Path(result["search_receipt_path"]).is_file()


@pytest.mark.parametrize("provider", ["wikipedia", "all"])
def test_discover_web_cli_archives_provider_responses_with_injected_transport(
    tmp_path, monkeypatch, capsys, provider
):
    from twin_core import scientific_pipeline_cli as cli

    repository = tmp_path / "repository"
    repository.mkdir()
    archive = tmp_path / "archive"
    output = tmp_path / "discovery.json"

    class Transport:
        name = "fake:static"

        def __init__(self):
            self.urls = []

        def fetch(self, url, *, timeout_seconds):
            self.urls.append(url)
            if "wikipedia.org" in url:
                payload = {"query": {"search": [{"ns": 0, "title": "Synthetic Evidence", "pageid": 123, "snippet": "Evidence", "timestamp": "2026-08-01T00:00:00Z"}]}}
                body, content_type = json.dumps(payload).encode(), "application/json"
            elif "openalex.org" in url:
                body, content_type = b'{"results": []}', "application/json"
            else:
                body, content_type = b'<div class="result"><a class="result__a" href="https://example.com/synthetic">Synthetic Result</a><a class="result__snippet">Synthetic evidence.</a></div>', "text/html"
            return WebResponse(url=url, status=200, headers={"content-type": content_type}, body=body, fetched_at="2026-08-30T10:00:00+00:00")

    transport = Transport()
    monkeypatch.setattr(cli, "ScraplingTransport", lambda mode: transport)
    monkeypatch.setattr(cli, "PublicWebAcquirer", lambda **kwargs: PublicWebAcquirer(resolver=_resolver, **kwargs))
    assert cli.main([
        "discover-web", "synthetic evidence", "--language", "en", "--provider", provider,
        "--repository-root", str(repository), "--archive-root", str(archive), "--output", str(output),
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == json.loads(output.read_text())
    assert result["claim_authority"] is False
    assert len(result["results"]) == (2 if provider == "all" else 1)
    assert len(transport.urls) == (3 if provider == "all" else 1)
    assert list(archive.rglob("*.json"))


def test_discover_web_cli_reports_malformed_provider_results(tmp_path, monkeypatch, capsys):
    from twin_core import scientific_pipeline_cli as cli

    repository = tmp_path / "repository"
    repository.mkdir()
    transport = FakeTransport({"query": {"search": [{"title": "Missing page id"}]}})
    monkeypatch.setattr(cli, "ScraplingTransport", lambda mode: transport)
    monkeypatch.setattr(cli, "PublicWebAcquirer", lambda **kwargs: PublicWebAcquirer(resolver=_resolver, **kwargs))
    assert cli.main([
        "discover-web", "synthetic", "--language", "en", "--provider", "wikipedia",
        "--repository-root", str(repository), "--archive-root", str(tmp_path / "archive"),
    ]) == 2
    assert "malformed" in capsys.readouterr().err
