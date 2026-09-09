"""Archived, provider-neutral discovery of public research sources."""

from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from typing import Any, Mapping
from urllib.parse import parse_qs, quote, urlencode, urlsplit, urlunsplit

from .source_quality import assess_authority, search_tokens, select_with_domain_cap
from .web_acquisition import (
    PublicWebAcquirer,
    WebAcquisitionError,
    load_archived_bytes,
    load_archived_text,
)


DISCOVERY_SCHEMA = "giga.research-source-discovery.v1"


class WebDiscoveryError(ValueError):
    """A discovery provider returned invalid or unusable evidence."""


@dataclass(frozen=True)
class DiscoveredSource:
    rank: int
    title: str
    source_url: str
    snippet: str
    provider_id: str
    updated_at: str | None
    authority_tier: str
    authority_score: float


def _archived_json(
    acquirer: PublicWebAcquirer, url: str, *, provider: str
) -> tuple[str, str, Mapping[str, Any]]:
    archived = acquirer.acquire(url)
    try:
        receipt_sha, _, text = load_archived_text(archived.receipt_path, acquirer.archive)
        payload = json.loads(text)
    except (WebAcquisitionError, json.JSONDecodeError) as exc:
        raise WebDiscoveryError(f"archived {provider} response is invalid") from exc
    if not isinstance(payload, Mapping) or payload.get("error"):
        raise WebDiscoveryError(f"{provider} returned an API error")
    return receipt_sha, str(archived.receipt_path), payload


def _archived_html(
    acquirer: PublicWebAcquirer, url: str, *, provider: str
) -> tuple[str, str, str]:
    archived = acquirer.acquire(url)
    try:
        receipt_sha, receipt, raw = load_archived_bytes(archived.receipt_path, acquirer.archive)
        if receipt.get("content_type") not in {"text/html", "application/xhtml+xml"}:
            raise WebDiscoveryError(f"{provider} returned non-HTML discovery content")
        document = raw.decode("utf-8")
    except (WebAcquisitionError, UnicodeDecodeError) as exc:
        raise WebDiscoveryError(f"archived {provider} response is invalid") from exc
    return receipt_sha, str(archived.receipt_path), document


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _plain_snippet(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    parser = _TextOnly()
    parser.feed(html.unescape(value))
    return " ".join(" ".join(parser.parts).split())[:2_000]


def _openalex_abstract(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ""
    positioned: list[tuple[int, str]] = []
    for token, positions in value.items():
        if not isinstance(token, str) or not isinstance(positions, list):
            return ""
        for position in positions:
            if isinstance(position, bool) or not isinstance(position, int) or position < 0:
                return ""
            positioned.append((position, token))
    positioned.sort()
    return " ".join(token for _, token in positioned)[:2_000]


def _text(value: Any, field: str, *, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WebDiscoveryError(f"{field} must be non-empty text")
    clean = " ".join(value.split())
    if len(clean) > maximum:
        raise WebDiscoveryError(f"{field} exceeds {maximum} characters")
    return clean


class WikipediaSearchProvider:
    """Discover English or Chinese encyclopaedia pages through MediaWiki's API."""

    name = "wikipedia"

    def __init__(self, acquirer: PublicWebAcquirer) -> None:
        self.acquirer = acquirer

    def search(self, query: str, *, language: str, limit: int = 10) -> dict[str, Any]:
        clean_query = _text(query, "query")
        if language not in {"en", "zh"}:
            raise WebDiscoveryError("Wikipedia discovery language must be en or zh")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise WebDiscoveryError("discovery limit must be from 1 to 20")
        parameters = urlencode(
            {
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "list": "search",
                "srnamespace": 0,
                "srsearch": clean_query,
                "srlimit": limit,
            }
        )
        api_url = f"https://{language}.wikipedia.org/w/api.php?{parameters}"
        receipt_sha, receipt_path, payload = _archived_json(
            self.acquirer, api_url, provider="Wikipedia"
        )
        query_payload = payload.get("query")
        raw_results = query_payload.get("search") if isinstance(query_payload, Mapping) else None
        if not isinstance(raw_results, list):
            raise WebDiscoveryError("Wikipedia response lacks a search result array")
        results: list[DiscoveredSource] = []
        seen_urls: set[str] = set()
        for row in raw_results:
            if not isinstance(row, Mapping) or row.get("ns", 0) != 0:
                continue
            try:
                title = _text(row.get("title"), "result.title", maximum=500)
                page_id = str(int(row["pageid"]))
            except (KeyError, TypeError, ValueError, WebDiscoveryError) as exc:
                raise WebDiscoveryError("Wikipedia returned a malformed search result") from exc
            source_url = (
                f"https://{language}.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='')}"
            )
            if source_url in seen_urls:
                continue
            seen_urls.add(source_url)
            authority = assess_authority(source_url)
            updated = row.get("timestamp")
            results.append(
                DiscoveredSource(
                    rank=len(results) + 1,
                    title=title,
                    source_url=source_url,
                    snippet=_plain_snippet(row.get("snippet")),
                    provider_id=page_id,
                    updated_at=updated if isinstance(updated, str) else None,
                    authority_tier=authority.tier,
                    authority_score=authority.score,
                )
            )
        return {
            "schema_version": DISCOVERY_SCHEMA,
            "provider": self.name,
            "language": language,
            "query": clean_query,
            "search_url": api_url,
            "search_receipt_sha256": receipt_sha,
            "search_receipt_path": receipt_path,
            "results": [asdict(result) for result in results],
            "result_count": len(results),
            "trust_class": "untrusted_external_discovery",
            "claim_authority": False,
        }


class OpenAlexSearchProvider:
    """Discover scholarly works through OpenAlex's public works API."""

    name = "openalex"

    def __init__(self, acquirer: PublicWebAcquirer) -> None:
        self.acquirer = acquirer

    def search(self, query: str, *, language: str, limit: int = 10) -> dict[str, Any]:
        clean_query = _text(query, "query")
        if language not in {"en", "zh"}:
            raise WebDiscoveryError("OpenAlex discovery language must be en or zh")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise WebDiscoveryError("discovery limit must be from 1 to 20")
        parameters = urlencode(
            {
                "per-page": limit,
                "search": clean_query,
                "select": (
                    "id,doi,display_name,publication_year,primary_location,relevance_score,"
                    "abstract_inverted_index"
                ),
            }
        )
        api_url = f"https://api.openalex.org/works?{parameters}"
        receipt_sha, receipt_path, payload = _archived_json(
            self.acquirer, api_url, provider="OpenAlex"
        )
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise WebDiscoveryError("OpenAlex response lacks a result array")
        results: list[DiscoveredSource] = []
        seen_urls: set[str] = set()
        for row in raw_results:
            if not isinstance(row, Mapping):
                raise WebDiscoveryError("OpenAlex returned a malformed result")
            title = _text(row.get("display_name"), "result.display_name", maximum=1_000)
            identifier = _text(row.get("id"), "result.id", maximum=500)
            location = row.get("primary_location")
            landing = location.get("landing_page_url") if isinstance(location, Mapping) else None
            doi = row.get("doi")
            source_url = (
                landing
                if isinstance(landing, str) and landing.startswith("https://")
                else doi
                if isinstance(doi, str) and doi.startswith("https://")
                else identifier
            )
            if not source_url.startswith("https://"):
                raise WebDiscoveryError("OpenAlex result has no safe HTTPS source URL")
            if source_url in seen_urls:
                continue
            seen_urls.add(source_url)
            year = row.get("publication_year")
            open_access = location.get("is_oa") if isinstance(location, Mapping) else None
            source_name = location.get("raw_source_name") if isinstance(location, Mapping) else None
            summary = " · ".join(
                value
                for value in (
                    f"Published {year}" if isinstance(year, int) else None,
                    "open access" if open_access is True else None,
                    source_name if isinstance(source_name, str) else None,
                )
                if value
            )
            abstract = _openalex_abstract(row.get("abstract_inverted_index"))
            if abstract:
                summary = f"{summary}. {abstract}" if summary else abstract
            authority = assess_authority(source_url)
            results.append(
                DiscoveredSource(
                    rank=len(results) + 1,
                    title=title,
                    source_url=source_url,
                    snippet=summary,
                    provider_id=identifier.rsplit("/", 1)[-1],
                    updated_at=None,
                    authority_tier=authority.tier,
                    authority_score=authority.score,
                )
            )
        meta = payload.get("meta")
        api_cost = meta.get("cost_usd") if isinstance(meta, Mapping) else None
        return {
            "schema_version": DISCOVERY_SCHEMA,
            "provider": self.name,
            "language": language,
            "query": clean_query,
            "search_url": api_url,
            "search_receipt_sha256": receipt_sha,
            "search_receipt_path": receipt_path,
            "results": [asdict(result) for result in results],
            "result_count": len(results),
            "provider_reported_cost_usd": api_cost if isinstance(api_cost, (int, float)) else None,
            "operator_billed_cost_usd": 0.0,
            "trust_class": "untrusted_external_discovery",
            "claim_authority": False,
        }


class _DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active: str | None = None
        self.href = ""
        self.parts: list[str] = []
        self.results: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a" or self.active is not None:
            return
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if "result__a" in classes:
            self.active = "title"
        elif "result__snippet" in classes:
            self.active = "snippet"
        else:
            return
        self.href = attributes.get("href") or ""
        self.parts = []

    def handle_data(self, data: str) -> None:
        if self.active and data.strip():
            self.parts.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "a" or self.active is None:
            return
        value = " ".join(" ".join(self.parts).split())
        if self.active == "title" and value and self.href:
            self.results.append({"title": value, "href": self.href, "snippet": ""})
        elif self.active == "snippet" and self.results and value:
            self.results[-1]["snippet"] = value[:2_000]
        self.active = None
        self.href = ""
        self.parts = []


def _duckduckgo_target(value: str) -> str | None:
    candidate = f"https:{value}" if value.startswith("//") else value
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    if parts.hostname in {"duckduckgo.com", "www.duckduckgo.com"} and parts.path == "/l/":
        targets = parse_qs(parts.query).get("uddg", [])
        candidate = targets[0] if targets else ""
        try:
            parts = urlsplit(candidate)
        except ValueError:
            return None
    try:
        port = parts.port
    except ValueError:
        return None
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or port not in {None, 443}
    ):
        return None
    return urlunsplit(("https", parts.netloc, parts.path or "/", parts.query, ""))


class DuckDuckGoSearchProvider:
    """Discover general public-web sources through archived DuckDuckGo HTML results."""

    name = "duckduckgo"

    def __init__(self, acquirer: PublicWebAcquirer) -> None:
        self.acquirer = acquirer

    def search(self, query: str, *, language: str, limit: int = 10) -> dict[str, Any]:
        clean_query = _text(query, "query", maximum=2_000)
        if language not in {"en", "zh"}:
            raise WebDiscoveryError("DuckDuckGo discovery language must be en or zh")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise WebDiscoveryError("discovery limit must be from 1 to 20")
        parameters = urlencode(
            {"q": clean_query, "kl": "us-en" if language == "en" else "cn-zh"}
        )
        search_url = f"https://html.duckduckgo.com/html/?{parameters}"
        receipt_sha, receipt_path, document = _archived_html(
            self.acquirer, search_url, provider="DuckDuckGo"
        )
        parser = _DuckDuckGoResultParser()
        parser.feed(document)
        results: list[DiscoveredSource] = []
        seen_urls: set[str] = set()
        for row in parser.results:
            source_url = _duckduckgo_target(row["href"])
            if not source_url or source_url in seen_urls:
                continue
            seen_urls.add(source_url)
            authority = assess_authority(source_url)
            results.append(
                DiscoveredSource(
                    rank=len(results) + 1,
                    title=_text(row["title"], "result.title", maximum=1_000),
                    source_url=source_url,
                    snippet=row["snippet"],
                    provider_id=source_url,
                    updated_at=None,
                    authority_tier=authority.tier,
                    authority_score=authority.score,
                )
            )
            if len(results) == limit:
                break
        if not results:
            raise WebDiscoveryError("DuckDuckGo returned no usable HTTPS results")
        return {
            "schema_version": DISCOVERY_SCHEMA,
            "provider": self.name,
            "language": language,
            "query": clean_query,
            "search_url": search_url,
            "search_receipt_sha256": receipt_sha,
            "search_receipt_path": receipt_path,
            "results": [asdict(result) for result in results],
            "result_count": len(results),
            "operator_billed_cost_usd": 0.0,
            "trust_class": "untrusted_external_discovery",
            "claim_authority": False,
        }


def fuse_discoveries(
    discoveries: list[Mapping[str, Any]], *, limit: int, per_domain: int = 2
) -> dict[str, Any]:
    """Round-robin provider results, then cap domains without hiding provenance."""
    if not discoveries:
        raise WebDiscoveryError("at least one provider discovery is required")
    if limit < 1 or per_domain < 1:
        raise WebDiscoveryError("fusion limit and per_domain must be positive")
    expected = (discoveries[0].get("language"), discoveries[0].get("query"))
    if any(
        discovery.get("schema_version") != DISCOVERY_SCHEMA
        or (discovery.get("language"), discovery.get("query")) != expected
        for discovery in discoveries
    ):
        raise WebDiscoveryError("provider discoveries must describe the same query and language")
    if any(
        not isinstance(discovery.get("results"), list)
        or not all(isinstance(row, Mapping) for row in discovery["results"])
        for discovery in discoveries
    ):
        raise WebDiscoveryError("provider discovery results must be arrays of objects")
    interleaved: list[dict[str, Any]] = []
    maximum = max(len(discovery["results"]) for discovery in discoveries)
    for index in range(maximum):
        for discovery in discoveries:
            rows = discovery.get("results", [])
            if isinstance(rows, list) and index < len(rows) and isinstance(rows[index], Mapping):
                interleaved.append({**rows[index], "provider": discovery.get("provider")})
    selected = select_with_domain_cap(
        interleaved,
        url_of=lambda row: str(row["source_url"]),
        limit=limit,
        per_domain=per_domain,
    )
    for rank, row in enumerate(selected, start=1):
        row["rank"] = rank
    return {
        "schema_version": DISCOVERY_SCHEMA,
        "provider": "fused",
        "language": discoveries[0].get("language"),
        "query": discoveries[0].get("query"),
        "search_receipts": [
            {
                "provider": discovery.get("provider"),
                "sha256": discovery.get("search_receipt_sha256"),
                "path": discovery.get("search_receipt_path"),
            }
            for discovery in discoveries
        ],
        "results": selected,
        "result_count": len(selected),
        "provider_reported_cost_usd": sum(
            float(discovery.get("provider_reported_cost_usd") or 0.0) for discovery in discoveries
        ),
        "operator_billed_cost_usd": 0.0,
        "trust_class": "untrusted_external_discovery",
        "claim_authority": False,
    }


def select_relevant_discoveries(
    query: str, results: list[Mapping[str, Any]], *, minimum_overlap_terms: int = 2
) -> dict[str, Any]:
    """Rank source candidates by explainable query overlap without hiding rejections."""
    query_terms = set(search_tokens(_text(query, "query", maximum=2_000)))
    if not query_terms:
        raise WebDiscoveryError("source selection query has no searchable terms")
    threshold = min(max(1, minimum_overlap_terms), len(query_terms))
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in results:
        title_overlap = sorted(query_terms & set(search_tokens(str(row.get("title", "")))))
        snippet_overlap = sorted(
            query_terms & set(search_tokens(str(row.get("snippet", ""))))
        )
        overlap = sorted(set(title_overlap) | set(snippet_overlap))
        scored = {
            **dict(row),
            "discovery_overlap_terms": overlap,
            "discovery_overlap_count": len(overlap),
            "discovery_query_coverage": len(overlap) / len(query_terms),
            "discovery_title_overlap_terms": title_overlap,
            "discovery_snippet_overlap_terms": snippet_overlap,
            "discovery_relevance_score": len(title_overlap) * 2 + len(snippet_overlap),
        }
        if len(overlap) >= threshold:
            accepted.append(scored)
        else:
            rejected.append({**scored, "rejection_reason": "insufficient_query_overlap"})
    accepted.sort(
        key=lambda row: (
            -float(row.get("authority_score") or 0.0),
            -row["discovery_relevance_score"],
            -len(row["discovery_title_overlap_terms"]),
            -row["discovery_overlap_count"],
            -row["discovery_query_coverage"],
            int(row.get("rank") or 10_000),
        )
    )
    return {
        "schema_version": "giga.research-source-selection.v1",
        "query": query,
        "minimum_overlap_terms": threshold,
        "accepted": accepted,
        "rejected": rejected,
        "claim_authority": False,
    }
