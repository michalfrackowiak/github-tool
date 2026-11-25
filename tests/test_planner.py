"""Tests for the query planner (pure logic, fake count function)."""

from __future__ import annotations

from datetime import date
import re

import pytest

from github_tool.keywords import Keyword
from github_tool.planner import (
    MAX_RESULTS,
    QuerySlice,
    compose_query,
    plan_keyword,
    plan_slices,
)


def test_in_readme_qualifier_is_carried_into_every_slice():
    assert compose_query("rag", "Python", (0, None), in_readme=True) == (
        "rag in:readme language:Python"
    )
    slices = plan_slices("rag", None, lambda query: 5, in_readme=True)
    assert len(slices) == 1
    assert "in:readme" in slices[0].query

    def count_fn(query: str) -> int:
        if "stars:" not in query or "stars:>=" in query:
            return 50_000
        return 100

    split = plan_slices("rag", None, count_fn, in_readme=True)
    assert len(split) > 1
    assert all("in:readme" in sl.query for sl in split)


def test_include_forks_qualifier_is_carried_into_every_slice():
    assert compose_query("rag", "Python", (0, None), include_forks=True) == (
        "rag fork:true language:Python"
    )
    slices = plan_slices("rag", None, lambda query: 5, include_forks=True)
    assert len(slices) == 1
    assert "fork:true" in slices[0].query

    def count_fn(query: str) -> int:
        if "stars:" not in query or "stars:>=" in query:
            return 50_000
        return 100

    split = plan_slices("rag", None, count_fn, include_forks=True)
    assert len(split) > 1
    assert all("fork:true" in sl.query for sl in split)


def test_under_cap_base_query_returns_one_slice_without_star_qualifier():
    slices = plan_slices("rag", "Python", lambda query: 5, today=date(2026, 11, 24))
    assert len(slices) == 1
    only = slices[0]
    assert only.query == "rag language:Python"
    assert "stars:" not in only.query
    assert only.keyword == "rag"
    assert only.language == "Python"
    assert only.estimated_count == 5
    assert only.overflow is False


def test_over_cap_base_query_splits_by_stars_ranges():
    def count_fn(query: str) -> int:
        match = re.search(r"stars:(\d+)\.\.(\d+)", query)
        if match:
            lo, hi = int(match.group(1)), int(match.group(2))
            return (hi - lo + 1) * 3
        if "stars:>=" in query:
            return 800
        return 50_000

    slices = plan_slices("rag", "Python", count_fn, today=date(2026, 11, 24))
    assert len(slices) > 1
    assert all("language:Python" in sl.query for sl in slices)
    assert any(re.search(r"stars:\d+\.\.\d+", sl.query) for sl in slices)
    for sl in slices:
        if not sl.overflow:
            assert sl.estimated_count is not None
            assert sl.estimated_count <= MAX_RESULTS


def test_open_ended_bucket_splits_by_created_date_and_overflows_only_at_leaf():
    def count_fn(query: str) -> int:
        if "created:" in query:
            match = re.search(r"created:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})", query)
            if match:
                start = date.fromisoformat(match.group(1))
                end = date.fromisoformat(match.group(2))
                return 5000 if (end - start).days > 31 else 2000
            return 5000
        if "stars:>=100000" in query:
            return 5000
        if "stars:" in query:
            return 10
        return 20_000

    slices = plan_slices("rag", "Python", count_fn, today=date(2026, 11, 24))
    assert slices
    assert any("created:" in sl.query for sl in slices)

    overflow = [sl for sl in slices if sl.overflow and not sl.truncated]
    assert overflow, "the unsplittable leaf must be flagged"
    for sl in overflow:
        assert sl.created[0] is not None and sl.created[1] is not None
        assert (sl.created[1] - sl.created[0]).days <= 31
    assert any(sl.stars == (100000, None) for sl in overflow)
    for sl in slices:
        if not sl.overflow:
            assert sl.estimated_count <= MAX_RESULTS


def test_plan_keyword_runs_all_variants_and_dedupes():
    from github_tool.keywords import get_keyword

    rag = get_keyword("rag")
    expected_queries = set(rag.variants())
    slices = plan_keyword("rag", "Python", lambda query: 5, today=date(2026, 11, 24))
    queries = [sl.query for sl in slices]
    assert len(slices) == len(expected_queries)
    assert len(queries) == len(set(queries))
    assert {sl.keyword for sl in slices} == {"rag"}
    assert any(q.startswith("topic:rag") for q in queries)
    for variant in expected_queries:
        assert any(q.startswith(variant) for q in queries)

    duplicate = Keyword("Dup", "dup", "dup-topic", ("same phrase", "same phrase"))
    deduped = plan_keyword(duplicate, None, lambda query: 5, today=date(2026, 11, 24))
    queries = [sl.query for sl in deduped]
    assert len(queries) == len(set(queries)) == 2
    assert "topic:dup-topic" in queries[0]


def test_plan_keyword_forwards_in_readme_and_forks():
    slices = plan_keyword(
        "rag",
        "Python",
        lambda query: 5,
        today=date(2026, 11, 24),
        in_readme=True,
        include_forks=True,
    )
    assert slices
    for sl in slices:
        assert "in:readme" in sl.query
        assert "fork:true" in sl.query


def test_compose_query_formats_stars_and_dates():
    assert compose_query("rag", None, (0, None)) == "rag"
    assert compose_query("rag", "Python", (10, 49)) == "rag language:Python stars:10..49"
    assert compose_query("rag", None, (100000, None)) == "rag stars:>=100000"
    assert compose_query("rag", None, (0, 4999), min_stars=10) == "rag stars:10..4999"
    assert (
        compose_query("rag", None, (50, 199), (date(2025, 1, 1), date(2025, 6, 30)))
        == "rag stars:50..199 created:2025-01-01..2025-06-30"
    )
    assert (
        compose_query("rag", None, (0, None), (date(2025, 1, 1), None))
        == "rag created:>=2025-01-01"
    )
    assert (
        compose_query("rag", None, (0, None), (None, date(2025, 1, 1)))
        == "rag created:<=2025-01-01"
    )


def test_zero_to_nine_bucket_gets_an_explicit_star_range():
    def count_fn(query: str) -> int:
        if "stars:0..9" in query:
            return 5
        if "stars:" in query:
            return 5
        return 50_000

    slices = plan_slices("rag", "Python", count_fn, today=date(2026, 11, 24))
    assert any("stars:0..9" in sl.query for sl in slices)


def test_query_slice_as_dict_and_label():
    sl = QuerySlice(
        query="rag language:Python stars:10..49 created:2025-01-01..2025-06-30",
        keyword="rag",
        language="Python",
        stars=(10, 49),
        created=(date(2025, 1, 1), date(2025, 6, 30)),
    )
    payload = sl.as_dict()
    assert payload["query"] == sl.query
    assert "stars 10-49" in sl.label
    assert "created 2025-01-01..2025-06-30" in sl.label


def test_last_allowed_count_is_not_mislabelled_as_overflow():
    def count_fn(query: str) -> int:
        return 5 if "stars:0..9" in query else 5000

    slices = plan_slices(
        "rag", "Python", count_fn, today=date(2026, 11, 24), max_count_calls=2
    )
    small = [sl for sl in slices if "stars:0..9" in sl.query]
    assert small
    assert small[0].estimated_count == 5
    assert small[0].overflow is False


def test_max_slices_emits_one_explicit_truncation_marker():
    slices = plan_slices(
        "rag", "Python", lambda _q: 5000,
        today=date(2026, 11, 24), max_slices=2,
    )
    markers = [sl for sl in slices if sl.truncated]
    assert len(markers) == 1
    assert markers[0].overflow is True
    assert markers[0].estimated_count is None
