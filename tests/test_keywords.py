"""Tests for the keyword map and crawl profiles."""

from __future__ import annotations

import json

from github_tool import keywords


def test_exactly_twelve_keywords():
    assert len(keywords.KEYWORDS) == 12


def test_slugs_and_topics_unique():
    slugs = [k.slug for k in keywords.KEYWORDS]
    assert len(slugs) == len(set(slugs))
    topics = [k.topic for k in keywords.KEYWORDS if k.topic]
    assert len(topics) == len(set(topics))


def test_every_keyword_has_variants():
    for kw in keywords.KEYWORDS:
        assert kw.variants(), kw.slug
        assert all(v.strip() for v in kw.variants())


def test_search_queries_include_topic_language_and_stars():
    kw = keywords.KEYWORD_BY_NAME["RAG"]
    queries = kw.search_queries("Python", min_stars=10)
    assert queries
    assert any(q.startswith("topic:rag") for q in queries)
    assert any("retrieval augmented generation" in q for q in queries)
    for q in queries:
        assert "language:Python" in q
        assert "stars:>=10" in q


def test_profiles_reference_valid_keywords_and_languages():
    valid_slugs = {k.slug for k in keywords.KEYWORDS}
    valid_languages = set(keywords.LANGUAGES)
    for profile in keywords.PROFILES.values():
        assert set(profile.keywords) <= valid_slugs, profile.name
        assert set(profile.languages) <= valid_languages, profile.name


def test_default_and_ai_profiles_are_sane():
    default = keywords.PROFILES["default"]
    assert set(default.keywords) == {k.slug for k in keywords.KEYWORDS}
    assert "Python" in default.languages

    ai = keywords.PROFILES["ai"]
    assert "rag" in ai.keywords and "llm" in ai.keywords
    assert "Zig" not in ai.languages


def test_keyword_map_document_shape():
    doc = keywords.keyword_map_document()
    assert doc["generated_for"] == "github-tool"
    assert doc["languages"] == list(keywords.LANGUAGES)
    assert len(doc["keywords"]) == 12
    assert [w["key"] for w in doc["windows"]] == [key for key, _, _ in keywords.WINDOWS]
    assert set(doc["profiles"]) == set(keywords.PROFILES)
    first = doc["keywords"][0]
    assert {"name", "slug", "topic", "phrases", "description", "variants"} <= set(first)


def test_write_keyword_map_round_trip(tmp_path):
    path = tmp_path / "nested" / "keywords.json"
    written = keywords.write_keyword_map(path)
    assert written == path
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert len(loaded["keywords"]) == 12
    assert loaded["keywords"][0]["slug"] == keywords.KEYWORDS[0].slug
