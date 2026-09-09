"""Deterministic source quality, diversity, duplication and claim-support signals.

These signals are deliberately explainable and model-free.  They help select and
audit evidence; they do not establish that a source or claim is true.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TypeVar
from urllib.parse import urlsplit


DEFAULT_NEAR_DUPLICATE_THRESHOLD = 0.90
DEFAULT_MINIMUM_LEXICAL_SUPPORT = 0.20
_T = TypeVar("_T")
_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u3400-\u9fff]+", re.IGNORECASE)
_STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "because",
    "been",
    "before",
    "between",
    "both",
    "can",
    "could",
    "does",
    "each",
    "for",
    "from",
    "have",
    "into",
    "its",
    "more",
    "not",
    "other",
    "should",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "used",
    "using",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "will",
    "with",
    "would",
}
_PRIMARY_DOMAINS = {
    "aclanthology.org",
    "acm.org",
    "arxiv.org",
    "clinicaltrials.gov",
    "doi.org",
    "ieee.org",
    "ietf.org",
    "ncbi.nlm.nih.gov",
    "nature.com",
    "openreview.net",
    "pubmed.ncbi.nlm.nih.gov",
    "rfc-editor.org",
    "science.org",
    "w3.org",
}
_REPUTABLE_DOMAINS = {
    "github.com",
    "gitlab.com",
    "gitee.com",
    "stackoverflow.com",
    "stackexchange.com",
    "wikipedia.org",
}
_DOCUMENTATION_PREFIXES = ("docs.", "developer.", "developers.")
_NON_INSTITUTIONAL_EDU_DOMAINS = {"academia.edu"}
_CC_SECOND_LEVEL = {"ac", "co", "com", "edu", "gov", "net", "org"}


@dataclass(frozen=True)
class AuthorityAssessment:
    tier: str
    score: float
    reason: str


def _host(url: str) -> str | None:
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return None
    if not host:
        return None
    result = host.casefold().rstrip(".")
    return result[4:] if result.startswith("www.") else result


def _domain_matches(host: str, domains: set[str]) -> bool:
    return host in domains or any(host.endswith(f".{domain}") for domain in domains)


def assess_authority(url: str) -> AuthorityAssessment:
    """Classify domain authority conservatively; unknown is neutral, never low."""
    host = _host(url)
    if host is None:
        return AuthorityAssessment("unknown", 0.4, "unparseable URL")
    if _domain_matches(host, _NON_INSTITUTIONAL_EDU_DOMAINS):
        return AuthorityAssessment("unknown", 0.4, f"non-institutional .edu host ({host})")
    if re.search(r"\.(gov|edu|mil)$|\.(gov|edu|ac)\.[a-z]{2}$", host):
        return AuthorityAssessment("primary", 1.0, f"government or education domain ({host})")
    if _domain_matches(host, _PRIMARY_DOMAINS):
        return AuthorityAssessment("primary", 1.0, f"primary or official source ({host})")
    if host.startswith(_DOCUMENTATION_PREFIXES):
        return AuthorityAssessment("primary", 1.0, f"official documentation host ({host})")
    if _domain_matches(host, _REPUTABLE_DOMAINS):
        return AuthorityAssessment("reputable", 0.7, f"established reference host ({host})")
    return AuthorityAssessment("unknown", 0.4, f"unclassified domain ({host})")


def registrable_domain(url: str) -> str:
    """Return a conservative eTLD+1 approximation for source-diversity caps."""
    host = _host(url)
    if host is None:
        return url
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    take = 3 if len(labels[-1]) == 2 and labels[-2] in _CC_SECOND_LEVEL else 2
    return ".".join(labels[-take:])


def select_with_domain_cap(
    items: Sequence[_T],
    *,
    url_of: Callable[[_T], str],
    limit: int,
    per_domain: int = 2,
) -> list[_T]:
    """Select in input order while preventing one host from crowding out diversity."""
    if limit <= 0 or per_domain <= 0:
        return []
    selected: list[_T] = []
    overflow: list[_T] = []
    counts: dict[str, int] = {}
    for item in items:
        domain = registrable_domain(str(url_of(item)))
        if counts.get(domain, 0) >= per_domain:
            overflow.append(item)
            continue
        counts[domain] = counts.get(domain, 0) + 1
        selected.append(item)
        if len(selected) == limit:
            return selected
    selected.extend(overflow[: max(0, limit - len(selected))])
    return selected


def _expanded_tokens(text: str, *, drop_stop_words: bool) -> list[str]:
    tokens: list[str] = []
    for match in _TOKEN_RE.finditer(text.casefold()):
        value = match.group(0)
        if "\u3400" <= value[0] <= "\u9fff":
            if len(value) == 1:
                tokens.append(value)
            else:
                tokens.extend(value[index : index + 2] for index in range(len(value) - 1))
            continue
        if drop_stop_words and value in _STOP_WORDS:
            continue
        if value.isdigit() or len(value) >= 2:
            tokens.append(value)
    return tokens


def search_tokens(text: str) -> list[str]:
    """Return deterministic English-token/CJK-bigram terms for lexical retrieval."""
    return _expanded_tokens(text, drop_stop_words=True)


def content_shingles(text: str, size: int = 5) -> frozenset[tuple[str, ...]]:
    """Return word/CJK-bigram n-gram shingles for near-duplicate detection."""
    if size < 1:
        raise ValueError("shingle size must be positive")
    tokens = _expanded_tokens(text, drop_stop_words=False)
    if not tokens:
        return frozenset()
    if len(tokens) < size:
        return frozenset({tuple(tokens)})
    return frozenset(tuple(tokens[index : index + size]) for index in range(len(tokens) - size + 1))


def jaccard_similarity(left: Iterable[object], right: Iterable[object]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    intersection = len(left_set & right_set)
    return intersection / (len(left_set) + len(right_set) - intersection)


def nearest_duplicate(
    candidate_text: str,
    existing: Sequence[tuple[str, str]],
    *,
    threshold: float = DEFAULT_NEAR_DUPLICATE_THRESHOLD,
) -> tuple[str | None, float]:
    """Return the nearest existing source id when similarity crosses threshold."""
    if not 0 < threshold <= 1:
        raise ValueError("near-duplicate threshold must be in (0, 1]")
    candidate = content_shingles(candidate_text)
    best_id: str | None = None
    best_score = 0.0
    for source_id, text in existing:
        score = jaccard_similarity(candidate, content_shingles(text))
        if score > best_score:
            best_id, best_score = source_id, score
    return (best_id, best_score) if best_score >= threshold else (None, best_score)


def lexical_support(claim: str, evidence: str) -> float:
    """Recall of distinct claim tokens in evidence, including Chinese bigrams."""
    claim_tokens = set(_expanded_tokens(claim, drop_stop_words=True))
    if not claim_tokens:
        return 1.0
    evidence_tokens = set(_expanded_tokens(evidence, drop_stop_words=True))
    return len(claim_tokens & evidence_tokens) / len(claim_tokens)


def confidence_level(*, source_count: int, citation_scores: Sequence[float]) -> dict[str, object]:
    """Explainable run confidence; explicitly not a truth probability."""
    mean_support = sum(citation_scores) / len(citation_scores) if citation_scores else 0.0
    if source_count <= 2 or not citation_scores or mean_support < 0.60:
        level = "low"
    elif source_count >= 5 and len(citation_scores) >= 3 and mean_support >= 0.90:
        level = "high"
    else:
        level = "medium"
    return {
        "level": level,
        "source_count": source_count,
        "citation_count": len(citation_scores),
        "mean_lexical_support": mean_support,
        "note": "heuristic evidence coverage signal, not a probability of truth",
    }
