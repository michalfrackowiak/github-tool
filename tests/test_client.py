"""Tests for the GitHub API client using an in-process MockTransport."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import json
from pathlib import Path

import httpx
import pytest

from github_tool.config import API_VERSION, Settings
from github_tool.github import (
    GitHubClient,
    GitHubError,
    OfflineError,
)
from github_tool.models import RateLimit


FIXTURES = Path(__file__).parent / "fixtures"
SEARCH_URL = "https://api.github.com/search/repositories"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def build_client(settings: Settings, handler, db=None):
    sleeps: list[float] = []
    client = GitHubClient(
        settings,
        transport=httpx.MockTransport(handler),
        cache=db,
        sleep=lambda seconds: sleeps.append(seconds),
        clock=lambda: 1_000.0,
    )
    return client, sleeps


RATE_HEADERS = {
    "X-RateLimit-Limit": "30",
    "X-RateLimit-Remaining": "29",
    "X-RateLimit-Reset": "1234567890",
    "X-RateLimit-Resource": "search",
}


def test_search_parses_fields_headers_auth_and_params(settings):
    search = load_fixture("search_repositories.json")
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return httpx.Response(200, json=search, headers={**RATE_HEADERS, "ETag": 'W/"search-1"'})

    client, _ = build_client(settings, handler)
    try:
        page = client.search_repositories("topic:rag language:Python", sort="stars", order="desc", page=2)
    finally:
        client.close()

    assert page.total_count == 2
    assert len(page.items) == 2
    first = page.items[0]
    assert first.id == 101
    assert first.full_name == "acme/ragkit"
    assert first.url == "https://github.com/acme/ragkit"
    assert first.language == "Python"
    assert first.stars == 1234 and first.forks == 56
    assert first.topics == ["rag", "llm"]
    assert first.license == "MIT"
    assert first.created_at == "2025-01-01T00:00:00Z"
    assert page.rate_limit == RateLimit(limit=30, remaining=29, reset=1234567890, resource="search")
    assert client.rate_limits["search"].remaining == 29
    assert page.etag == 'W/"search-1"'
    assert page.from_cache is False

    request = seen["request"]
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["X-GitHub-Api-Version"] == API_VERSION
    assert request.url.params["q"] == "topic:rag language:Python"
    assert request.url.params["sort"] == "stars"
    assert request.url.params["order"] == "desc"
    assert request.url.params["per_page"] == str(settings.search_per_page)
    assert request.url.params["page"] == "2"


def test_etag_cache_304_returns_cached_items(settings, db):
    search = load_fixture("search_repositories.json")
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.headers.get("If-None-Match") == 'W/"search-1"':
            return httpx.Response(304, headers=RATE_HEADERS)
        return httpx.Response(200, json=search, headers={**RATE_HEADERS, "ETag": 'W/"search-1"'})

    client, _ = build_client(settings, handler, db=db)
    try:
        first = client.search_repositories("rag")
        second = client.search_repositories("rag")
    finally:
        client.close()

    assert first.from_cache is False
    assert first.etag == 'W/"search-1"'
    assert second.from_cache is True
    assert [r.full_name for r in second.items] == [r.full_name for r in first.items]
    assert second.etag == 'W/"search-1"'
    assert "If-None-Match" not in calls[0].headers
    assert calls[1].headers["If-None-Match"] == 'W/"search-1"'
    # Cache key includes the sorted query parameters; at minimum the URL is cached.
    with db.connect() as conn:
        rows = conn.execute("SELECT url, etag FROM http_cache").fetchall()
    assert rows and rows[0]["etag"] == 'W/"search-1"'


def test_retry_after_429_is_honoured(settings):
    search = load_fixture("search_repositories.json")
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json=search, headers=RATE_HEADERS)

    client, sleeps = build_client(settings, handler)
    try:
        page = client.search_repositories("rag")
    finally:
        client.close()

    assert page.total_count == 2
    assert sleeps == [1.0]
    assert attempts["n"] == 2


def test_retries_are_bounded_then_raise(settings):
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(500, text="server error")

    client, sleeps = build_client(settings, handler)
    try:
        with pytest.raises(GitHubError) as excinfo:
            client.search_repositories("rag")
    finally:
        client.close()

    assert excinfo.value.status == 500
    assert attempts["n"] == settings.max_retries + 1
    assert len(sleeps) == settings.max_retries


def test_readme_raw_etag_304_404_and_truncation(settings):
    readme_calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        readme_calls.append(request)
        etag = request.headers.get("If-None-Match")
        if request.url.path.endswith("/readme"):
            if etag == '"r1"':
                return httpx.Response(304, headers=RATE_HEADERS)
            if request.url.path.startswith("/repos/missing/"):
                return httpx.Response(404, headers=RATE_HEADERS)
            return httpx.Response(200, text="# Demo\n", headers={**RATE_HEADERS, "ETag": '"r1"'})
        return httpx.Response(404)

    client, _ = build_client(settings, handler)
    try:
        raw = client.get_readme("acme/ragkit")
        unchanged = client.get_readme("acme/ragkit", etag=raw.etag)
        missing = client.get_readme("missing/repo")
    finally:
        client.close()

    assert raw.text == "# Demo\n"
    assert raw.etag == '"r1"'
    assert raw.not_modified is False
    assert unchanged.text is None
    assert unchanged.not_modified is True
    assert missing.text is None
    assert missing.not_modified is False
    assert readme_calls[0].headers["Accept"] == "application/vnd.github.raw+json"

    small = replace(settings, readme_max_bytes=5)
    client, _ = build_client(
        small,
        lambda request: httpx.Response(200, text="0123456789", headers={"ETag": '"r2"'}),
    )
    try:
        truncated = client.get_readme("acme/ragkit")
    finally:
        client.close()
    assert truncated.text == "01234"


def test_star_history_filters_and_stops_pagination(settings):
    history = load_fixture("star_history.json")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=history, headers=RATE_HEADERS)

    client, _ = build_client(settings, handler)
    try:
        days = client.star_history(101, weeks_back=2, today=date(2026, 11, 24))
    finally:
        client.close()

    by_day = {d.day: d.gained for d in days}
    assert len(by_day) == 8
    # Week starting 2026-11-09: the 9th is older than the 2-week cutoff.
    assert date(2026, 11, 9) not in by_day
    assert by_day[date(2026, 11, 10)] == 2
    assert by_day[date(2026, 11, 15)] == 7
    # Week starting 2026-11-23: days after "today" are filtered out.
    assert by_day[date(2026, 11, 23)] == 20
    assert by_day[date(2026, 11, 24)] == 21
    assert max(by_day) == date(2026, 11, 24)
    assert len(requests) == 1
    assert requests[0].url.params["page"] == "1"
    assert requests[0].url.params["per_page"] == "30"


def test_graphql_repo_stats_batches_and_parses(settings):
    payload = load_fixture("graphql_repo_stats.json")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    client, _ = build_client(settings, handler)
    try:
        repos = client.repo_stats(["acme/ragkit", "acme/ragflow"])
    finally:
        client.close()

    assert len(requests) == 1
    assert requests[0].method == "POST"
    body = json.loads(requests[0].content)
    assert body["variables"]["o0"] == "acme"
    assert body["variables"]["n1"] == "ragflow"
    assert [r.id for r in repos] == [101, 102]
    assert repos[0].full_name == "acme/ragkit"
    assert repos[0].topics == ["rag", "llm"]
    assert repos[0].language == "Python"
    assert repos[1].archived is True


def test_graphql_errors_raise(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "bad query"}]})

    client, _ = build_client(settings, handler)
    try:
        with pytest.raises(GitHubError):
            client.repo_stats(["acme/ragkit"])
    finally:
        client.close()


def test_oss_insight_unavailable_fixture(settings):
    payload = load_fixture("oss_insight_unavailable.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.ossinsight.io"
        return httpx.Response(200, json=payload)

    client, _ = build_client(settings, handler)
    try:
        result = client.oss_insight_trends(period="past_week", language="Python")
    finally:
        client.close()

    assert result.available is False
    assert "unavailable since 2026-03-01" in result.note
    assert result.rows and result.rows[0]["repo_name"] == "acme/ragkit"


def test_offline_settings_never_touch_transport(db):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        calls["n"] += 1
        raise AssertionError("transport must not be called in offline mode")

    offline = Settings(
        db_path=db.path,
        token="test-token",
        search_min_interval=0.0,
        offline=True,
    )
    client, _ = build_client(offline, handler, db=db)
    try:
        with pytest.raises(RuntimeError) as excinfo:
            client.search_repositories("rag")
    finally:
        client.close()
    assert calls["n"] == 0
    # OfflineError is a RuntimeError subtype raised before the transport runs.
    assert isinstance(excinfo.value, RuntimeError)
    assert isinstance(excinfo.value, OfflineError)


def test_offline_settings_raise_offline_error_before_transport(db):
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("transport must not be called in offline mode")

    offline = Settings(
        db_path=db.path,
        token="test-token",
        search_min_interval=0.0,
        offline=True,
    )
    client, _ = build_client(offline, handler, db=db)
    try:
        with pytest.raises(OfflineError):
            client.search_repositories("rag")
    finally:
        client.close()
