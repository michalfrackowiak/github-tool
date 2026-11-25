"""Tests for link-out URL builders (no network, no database)."""

from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from github_tool import links


TODAY = date(2026, 11, 24)


def _query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


def test_github_search_url_encodes_query_and_qualifiers():
    url = links.github_search_url("topic:rag language:Python", "Python", "30d", sort="stars", order="desc", today=TODAY)
    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert parsed.path == "/search"
    q = _query(url)
    assert q["type"] == ["repositories"]
    assert q["s"] == ["stars"]
    assert q["o"] == ["desc"]
    assert q["q"] == ["topic:rag language:Python pushed:>=2026-10-25 language:Python"]
    assert "pushed" in q["q"][0]


@pytest.mark.parametrize(
    ("window", "expected"),
    [
        ("7d", "2026-11-17"),
        ("30d", "2026-10-25"),
        ("90d", "2026-08-26"),
    ],
)
def test_github_search_url_uses_pushed_for_short_windows(window: str, expected: str):
    url = links.github_search_url("rag", today=TODAY, window=window)
    assert f"pushed:>={expected}" in _query(url)["q"][0]


def test_github_search_url_uses_created_for_last_year():
    url = links.github_search_url("rag", today=TODAY, window="365d")
    q = _query(url)["q"][0]
    assert "created:>=2025-11-24" in q
    assert "pushed:" not in q


def test_github_search_url_adds_language_once():
    url = links.github_search_url("rag", language="Rust", window="7d", today=TODAY)
    assert _query(url)["q"][0] == "rag pushed:>=2026-11-17 language:Rust"


@pytest.mark.parametrize(
    ("window", "since"),
    [("today", "daily"), ("7d", "weekly"), ("30d", "monthly")],
)
def test_trending_url_mapping(window: str, since: str):
    url = links.trending_url(window=window)
    assert url is not None
    assert _query(url)["since"] == [since]
    assert urlparse(url).path == "/trending"


def test_trending_url_optional_language():
    url = links.trending_url("Python", "7d")
    assert urlparse(url).path == "/trending/python"
    assert _query(url)["since"] == ["weekly"]


@pytest.mark.parametrize("window", ["90d", "365d"])
def test_trending_url_unsupported_windows(window: str):
    assert links.trending_url(window=window) is None


@pytest.mark.parametrize(
    ("window", "period"),
    [("today", "past_24_hours"), ("7d", "past_week"), ("30d", "past_month"), ("90d", "past_3_months")],
)
def test_oss_insight_url_mapping(window: str, period: str):
    url = links.oss_insight_url(window=window)
    assert url is not None
    assert _query(url)["period"] == [period]


def test_oss_insight_url_unsupported_window():
    assert links.oss_insight_url(window="365d") is None


def test_topic_url_lowercases_language():
    url = links.topic_url("rag", "Python")
    assert urlparse(url).path == "/topics/rag"
    assert _query(url)["l"] == ["python"]


def test_generate_links_last_year_fallback():
    views = links.generate_links("rag", "Python", "365d", today=TODAY)
    ids = {v.id for v in views}
    assert ids == {"github-search", "github-search-created", "github-topic"}
    assert "github-trending" not in ids
    assert "oss-insight" not in ids
    created = next(v for v in views if v.id == "github-search-created")
    assert "created:>=2025-11-24" in _query(created.url)["q"][0]


def test_generate_links_marks_oss_unavailable_and_includes_topic():
    views = links.generate_links("rag", "Python", "30d", today=TODAY)
    ids = {v.id for v in views}
    assert "github-topic" in ids
    assert "github-trending" in ids
    oss = next(v for v in views if v.id == "oss-insight")
    assert oss.available is False
    assert links.OSS_INSIGHT_TRENDING_AVAILABLE is False
    topic = next(v for v in views if v.id == "github-topic")
    assert topic.url.endswith("?l=python")


def test_generate_links_unknown_window_raises():
    with pytest.raises(ValueError):
        links.generate_links("rag", window="2d")


def test_web_search_links_mapping():
    mapping = links.web_search_links("rag", "Python", "7d")
    assert "github-search" in mapping
    assert mapping["github-trending"].startswith("https://github.com/trending")
