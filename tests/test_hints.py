"""Discovery hints: OSS Insight adapter plus GitHub Trending HTML collector."""

from __future__ import annotations

import httpx

from github_tool.github import GitHubClient, OssInsightResult
from github_tool.models import Repo
from github_tool.trends import discover_hints

TRENDING_HTML = """
<html><body>
  <h2 class="h3 lh-condensed">
    <a data-hydro-click="x" href="/acme/one?tab=repositories">acme / one</a>
  </h2>
  <h2 class="h3 lh-condensed"><a href="/acme/two">acme / two</a></h2>
  <h2 class="h3 lh-condensed"><a href="/acme/one">duplicate</a></h2>
</body></html>
"""


def test_parse_trending_html_deduplicates_owner_repo_links():
    assert GitHubClient.parse_trending_html(TRENDING_HTML) == ["acme/one", "acme/two"]


def test_github_trending_repos_uses_expected_url(settings, db):
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["accept"] = request.headers.get("accept")
        return httpx.Response(200, text=TRENDING_HTML)

    client = GitHubClient(
        settings,
        transport=httpx.MockTransport(handler),
        cache=db,
        sleep=lambda _: None,
        clock=lambda: 0.0,
    )
    try:
        names = client.github_trending_repos("Python", "weekly")
    finally:
        client.close()

    assert names == ["acme/one", "acme/two"]
    assert str(seen["url"]).startswith("https://github.com/trending/Python?since=weekly")
    assert seen["accept"] == "text/html"


class FakeHintClient:
    def __init__(self, repos: list[Repo]):
        self.repos = repos
        self.oss_calls = 0
        self.trending_calls = 0
        self.stats_calls: list[list[str]] = []

    def oss_insight_trends(self, **kwargs):
        self.oss_calls += 1
        return OssInsightResult(available=False, note="unavailable")

    def github_trending_repos(self, language=None, period="weekly"):
        self.trending_calls += 1
        assert period == "weekly"
        return ["acme/one", "acme/two"]

    def repo_stats(self, names):
        self.stats_calls.append(names)
        return [
            repo for repo in self.repos if repo.full_name in names
        ]


def test_discover_hints_uses_trending_when_oss_is_unavailable(db, make_repo):
    repos = [
        make_repo(1, "acme/one", stars=10),
        make_repo(2, "acme/two", stars=20),
    ]
    client = FakeHintClient(repos)

    hints = discover_hints(client, db, period="past_week")

    assert [r.full_name for r in hints] == ["acme/one", "acme/two"]
    assert client.oss_calls == 1
    assert client.trending_calls == 1
    assert client.stats_calls == [["acme/one", "acme/two"]]
    assert db.get_repo(1) is not None
    assert db.get_repo(2) is not None


def test_discover_hints_can_limit_sources(db, make_repo):
    client = FakeHintClient([make_repo(1, "acme/one")])

    assert discover_hints(client, db, source="oss") == []
    assert client.trending_calls == 0
    assert client.stats_calls == []


class BrokenStatsClient(FakeHintClient):
    def repo_stats(self, names):
        raise RuntimeError("GraphQL is down")


def test_discover_hints_swallows_repo_stats_failures(db):
    assert discover_hints(BrokenStatsClient([]), db) == []


def test_repo_root_files_filters_non_files_and_404(settings, db):
    payload = [
        {"name": "requirements.txt", "type": "file"},
        {"name": "requirements-dev.txt", "type": "file"},
        {"name": "pyproject.toml", "type": "file"},
        {"name": "docs", "type": "dir"},
    ]
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if "missing" in request.url.path:
            return httpx.Response(404)
        return httpx.Response(200, json=payload)

    client = GitHubClient(
        settings,
        transport=httpx.MockTransport(handler),
        cache=db,
        sleep=lambda _: None,
    )
    try:
        names = client.repo_root_files("acme/tool")
        assert names == ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
        assert client.repo_root_files("acme/missing") == []
    finally:
        client.close()
    assert all(path.endswith("/contents/") for path in seen)
