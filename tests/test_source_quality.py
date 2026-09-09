from __future__ import annotations

import pytest

from twin_core.source_quality import (
    assess_authority,
    confidence_level,
    content_shingles,
    jaccard_similarity,
    lexical_support,
    nearest_duplicate,
    registrable_domain,
    select_with_domain_cap,
)


def test_authority_is_explainable_and_unknown_is_not_punished() -> None:
    assert assess_authority("https://www.ncbi.nlm.nih.gov/paper").tier == "primary"
    assert assess_authority("https://department.example.edu/paper").score == 1.0
    assert assess_authority("https://www.academia.edu/paper").tier == "unknown"
    assert assess_authority("https://gitee.com/team/project").tier == "reputable"
    unknown = assess_authority("https://specialist.example/research")
    assert unknown.tier == "unknown"
    assert unknown.score == 0.4
    assert "specialist.example" in unknown.reason


def test_registrable_domain_and_cap_preserve_diversity_then_fill_headroom() -> None:
    rows = [
        {"url": "https://en.wikipedia.org/a"},
        {"url": "https://zh.wikipedia.org/b"},
        {"url": "https://example.edu/c"},
        {"url": "https://wikipedia.org/d"},
    ]
    assert registrable_domain(rows[0]["url"]) == "wikipedia.org"
    selected = select_with_domain_cap(rows, url_of=lambda row: row["url"], limit=3, per_domain=1)
    assert [row["url"] for row in selected] == [rows[0]["url"], rows[2]["url"], rows[1]["url"]]


def test_shingle_similarity_detects_syndicated_and_chinese_duplicates() -> None:
    original = "A reliable research system preserves exact sources and verifies every citation."
    syndicated = original + " Updated today."
    unrelated = "A weather forecast predicts rain over the weekend."
    assert jaccard_similarity(content_shingles(original), content_shingles(original)) == 1.0
    duplicate_id, score = nearest_duplicate(
        syndicated,
        [("original", original), ("other", unrelated)],
        threshold=0.60,
    )
    assert duplicate_id == "original"
    assert score >= 0.60
    chinese = "研究系统必须保留准确来源并验证每条引用"
    assert jaccard_similarity(content_shingles(chinese), content_shingles(chinese)) == 1.0


def test_multilingual_lexical_support_scores_claim_against_evidence() -> None:
    assert lexical_support("The source reports evidence", "Evidence from the source") >= 2 / 3
    assert lexical_support("系统验证引用", "研究系统必须验证每条引用并保留来源") > 0.5
    assert lexical_support("Unrelated weather forecast", "Evidence from the source") == 0.0


def test_confidence_is_an_evidence_signal_not_truth_probability() -> None:
    high = confidence_level(source_count=6, citation_scores=[1.0, 0.95, 0.92])
    assert high["level"] == "high"
    assert "not a probability" in high["note"]
    assert confidence_level(source_count=1, citation_scores=[1.0])["level"] == "low"


def test_invalid_shingle_and_duplicate_thresholds_fail() -> None:
    with pytest.raises(ValueError, match="positive"):
        content_shingles("text", 0)
    with pytest.raises(ValueError, match="threshold"):
        nearest_duplicate("text", [], threshold=0)
