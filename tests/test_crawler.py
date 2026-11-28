"""Tests for the Phase 3 crawler. No live network is used."""

from __future__ import annotations

import hashlib

import pytest

from github_tool import keywords
from github_tool.config import Settings
from github_tool.crawler import Crawler
from github_tool.db import Database
from github_tool.github import OfflineError
from github_tool.keywords import CrawlProfile
from github_tool.models import ReadmeResult, Repo, SearchPage


def make_repo(repo_id: int, *, stars: int = 100, name: str | None = None) -> Repo:
    full_name = name or f"owner{repo_id}/repo{repo_id}"
    return Repo(
        id=repo_id,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        stars=stars,
        forks=1,
        language="Python",
    )


class FakeClient:
    """A configurable stand-in for GitHubClient."""

    def __init__(
        self,
        *,
        search_results: dict[tuple[str, int], list[Repo]] | None = None,
        total_counts: dict[str, int] | None = None,
        readme_results: dict[str, object] | None = None,
        search_error: Exception | None = None,
    ):
        self.search_results = search_results or {}
        self.total_counts = total_counts or {}
        self.readme_results = readme_results or {}
        self.search_calls: list[tuple[str, int]] = []
        self.readme_calls: list[tuple[str, str | None]] = []
        self.graphql_calls: list[tuple[str, str | None]] = []
        self.count_calls: list[str] = []
        self.fail_page: tuple[str, int] | None = None
        self.search_error: Exception | None = search_error
        self.graphql_pages: list[tuple[list[Repo], int, str | None]] = []

    def count_search(self, query: str) -> int:
        self.count_calls.append(query)
        return int(self.total_counts.get(query, 0))

    def search_repositories(
        self, query: str, *, sort: str = "stars", order: str = "desc",
        per_page: int | None = None, page: int = 1,
    ) -> SearchPage:
        self.search_calls.append((query, page))
        if self.search_error is not None:
            raise self.search_error
        if self.fail_page == (query, page):
            raise KeyboardInterrupt
        items = list(self.search_results.get((query, page), []))
        total = int(self.total_counts.get(query, 0))
        if total == 0 and items:
            total = len(items)
        return SearchPage(items=items, total_count=total)

    def get_readme(self, full_name: str, etag: str | None = None) -> ReadmeResult:
        self.readme_calls.append((full_name, etag))
        value = self.readme_results.get(full_name)
        if callable(value):
            return value(etag)
        if value is None:
            return ReadmeResult(None, None)
        return value  # type: ignore[return-value]

    def search_graphql(
        self, query: str, *, per_page: int = 100, cursor: str | None = None,
    ) -> tuple[list[Repo], int, str | None]:
        idx = len(self.graphql_calls)
        self.graphql_calls.append((query, cursor))
        if idx < len(self.graphql_pages):
            return self.graphql_pages[idx]
        return [], 0, None


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "t.db")
    database.initialize()
    return database


@pytest.fixture
def settings(tmp_path):
    return Settings(db_path=tmp_path / "t.db", search_min_interval=0.0, offline=False)


def seed_run(db: Database, slices: list[dict], profile: str = "tiny") -> str:
    run_id = db.start_run(profile)
    db.add_slices(run_id, slices)
    return run_id


def one_slice(query: str, keyword: str, total_count: int = 0) -> dict:
    return {
        "query": query,
        "keyword": keyword,
        "language": "Python",
        "total_count": total_count,
        "estimated_count": total_count,
        "overflow": False,
    }


def test_resume_switching_discovery_restarts_pagination(db, settings):
    query = "rag language:Python"
    run_id = seed_run(db, [one_slice(query, "rag", total_count=1000)])
    slice_id = db.pending_slices(run_id)[0]["id"]
    db.update_slice(slice_id, pages_done=2, status="running")
    client = FakeClient()
    client.graphql_pages = [
        ([make_repo(i + 1)], 1000, f"cursor-{i + 1}") for i in range(10)
    ]

    summary = Crawler(settings, db, client).run(
        resume=run_id,
        discovery="graphql",
        fetch_readmes=False,
        max_pages_per_slice=10,
    )

    assert summary.status == "completed"
    assert client.graphql_calls[0] == (query, None)
    assert len(client.graphql_calls) == 10
    assert db.slice_counts(run_id) == {"done": 1}


def test_successful_resume_clears_previous_error(db, settings):
    query = "rag language:Python"
    run_id = seed_run(db, [one_slice(query, "rag", total_count=1)])
    db.update_run(run_id, status="failed", error="boom")
    client = FakeClient(
        search_results={(query, 1): [make_repo(1)]}, total_counts={query: 1}
    )

    summary = Crawler(settings, db, client).run(resume=run_id, fetch_readmes=False)

    assert summary.status == "completed"
    assert db.get_run(run_id)["error"] is None


# --------------------------------------------------------------- planning
def test_plan_profile_creates_and_persists_slices(monkeypatch, db, settings):
    monkeypatch.setitem(
        keywords.PROFILES,
        "tiny",
        CrawlProfile("tiny", ("rag",), ("Python",), min_stars=20, fetch_readmes=False),
    )
    client = FakeClient()
    crawler = Crawler(settings, db, client)

    slices = crawler.plan_profile("tiny")

    # 2 variants; each count is under the 1,000 cap, so one slice per variant.
    assert len(slices) == 2
    assert all(s.keyword == "rag" and s.language == "Python" for s in slices)
    assert len({s.query for s in slices}) == len(slices)

    summary = crawler.run(profile="tiny", fetch_readmes=False, max_slices=1)
    assert summary.slices_total == 2
    assert summary.status == "paused"  # max_slices left work behind
    assert sum(db.slice_counts(summary.run_id).values()) == 2


def test_unknown_profile_raises(db, settings):
    crawler = Crawler(settings, db, FakeClient())
    with pytest.raises(ValueError):
        crawler.plan_profile("does-not-exist")
    with pytest.raises(ValueError):
        crawler.run(profile="does-not-exist")


def test_invalid_discovery_raises(db, settings):
    crawler = Crawler(settings, db, FakeClient())
    with pytest.raises(ValueError):
        crawler.run(profile="default", discovery="bogus")


# ------------------------------------------------------------------- REST
def test_one_page_crawl_inserts_repo_and_completes(db, settings):
    repo = make_repo(1, stars=123)
    query = "topic:rag language:Python stars:>=20"
    run_id = seed_run(db, [one_slice(query, "rag", total_count=1)])
    client = FakeClient(
        search_results={(query, 1): [repo]},
        total_counts={query: 1},
        readme_results={repo.full_name: ReadmeResult("hello readme", "etag-1")},
    )
    crawler = Crawler(settings, db, client)

    summary = crawler.run(resume=run_id, fetch_readmes=True)

    assert summary.status == "completed"
    assert summary.slices_done == 1
    assert summary.pages_fetched == 1
    assert summary.repos_seen == 1
    assert summary.repos_inserted == 1
    assert summary.readmes_fetched == 1

    stored = db.get_repo(1)
    assert stored is not None
    assert stored.stars == 123
    assert stored.readme_text == "hello readme"
    assert stored.readme_etag == "etag-1"
    assert stored.readme_hash == hashlib.sha256(b"hello readme").hexdigest()
    assert db.keyword_counts() == {"rag": 1}

    run = db.get_run(run_id)
    assert run["status"] == "completed"
    assert run["finished_at"] is not None


def test_duplicate_repo_across_slices_stored_once_with_both_keywords(db, settings):
    repo = make_repo(7)
    q1 = "topic:rag language:Python stars:>=20"
    q2 = "topic:llm language:Python stars:>=20"
    run_id = seed_run(
        db,
        [one_slice(q1, "rag", total_count=1), one_slice(q2, "llm", total_count=1)],
    )
    client = FakeClient(
        search_results={(q1, 1): [repo], (q2, 1): [repo]},
        total_counts={q1: 1, q2: 1},
    )
    crawler = Crawler(settings, db, client)

    summary = crawler.run(resume=run_id, fetch_readmes=False)

    assert summary.status == "completed"
    assert summary.repos_seen == 2
    assert summary.repos_inserted == 1
    assert summary.repos_updated == 1
    assert db.count_repos() == 1
    assert db.keyword_counts() == {"rag": 1, "llm": 1}


def test_readme_conditional_etag_and_304_preserves_text(db, settings):
    repo = make_repo(3)
    query = "topic:rag language:Python stars:>=20"

    # First pass: fetch without a conditional ETag and store the text.
    run_id = seed_run(db, [one_slice(query, "rag", total_count=1)])
    client = FakeClient(
        search_results={(query, 1): [repo]},
        total_counts={query: 1},
        readme_results={repo.full_name: ReadmeResult("original", "etag-1")},
    )
    Crawler(settings, db, client).run(resume=run_id, fetch_readmes=True)
    assert client.readme_calls == [(repo.full_name, None)]
    assert db.get_repo(3).readme_text == "original"

    # Second pass: the client answers 304; the stored text must survive.
    run_id2 = seed_run(db, [one_slice(query, "rag", total_count=1)])
    client2 = FakeClient(
        search_results={(query, 1): [repo]},
        total_counts={query: 1},
        readme_results={
            repo.full_name: lambda etag: ReadmeResult(None, etag, not_modified=True)
        },
    )
    summary = Crawler(settings, db, client2).run(resume=run_id2, fetch_readmes=True)

    assert client2.readme_calls == [(repo.full_name, "etag-1")]
    assert summary.readmes_not_modified == 1
    assert summary.readmes_fetched == 0
    assert db.get_repo(3).readme_text == "original"


def test_resume_after_interruption_skips_completed_pages(db, settings):
    q = "topic:rag language:Python stars:>=20"
    run_id = seed_run(db, [one_slice(q, "rag", total_count=300)])
    repos = {page: make_repo(page, stars=page * 10) for page in (1, 2, 3)}
    client = FakeClient(
        search_results={(q, page): [repo] for page, repo in repos.items()},
        total_counts={q: 300},
    )
    client.fail_page = (q, 2)

    first = Crawler(settings, db, client).run(resume=run_id, fetch_readmes=False)

    assert first.status == "paused"
    assert first.repos_inserted == 1
    run = db.get_run(run_id)
    assert run["status"] == "paused"
    assert run["finished_at"] is None
    pending = db.pending_slices(run_id)
    assert len(pending) == 1
    assert pending[0]["pages_done"] == 1
    assert pending[0]["status"] == "running"

    client.fail_page = None
    client.search_calls.clear()
    second = Crawler(settings, db, client).run(resume=run_id, fetch_readmes=False)

    assert second.status == "completed"
    assert second.slices_done == 1
    assert second.repos_inserted == 2
    assert [page for _, page in client.search_calls] == [2, 3]
    assert db.count_repos() == 3
    assert db.get_run(run_id)["status"] == "completed"


def test_resume_completed_run_returns_already_done(db, settings):
    q = "topic:rag language:Python stars:>=20"
    run_id = seed_run(db, [one_slice(q, "rag", total_count=1)])
    client = FakeClient(
        search_results={(q, 1): [make_repo(1)]},
        total_counts={q: 1},
    )
    crawler = Crawler(settings, db, client)
    crawler.run(resume=run_id, fetch_readmes=False)

    again = crawler.run(resume=run_id, fetch_readmes=False)
    assert again.status == "already_done"
    assert again.slices_total == 1
    assert again.slices_done == 1
    # No additional network calls were made.
    assert len(client.search_calls) == 1


def test_empty_page_stops_cleanly(db, settings):
    q = "topic:rag language:Python stars:>=20"
    run_id = seed_run(db, [one_slice(q, "rag", total_count=500)])
    client = FakeClient(
        search_results={(q, 1): [make_repo(1)], (q, 2): []},
        total_counts={q: 500},
    )
    summary = Crawler(settings, db, client).run(resume=run_id, fetch_readmes=False)

    assert summary.status == "completed"
    assert summary.pages_fetched == 2
    assert client.search_calls == [(q, 1), (q, 2)]
    assert db.pending_slices(run_id) == []


# ---------------------------------------------------------------- GraphQL
def test_graphql_discovery_stores_repos_and_respects_cap(db, settings):
    q = "topic:rag language:Python stars:>=20"
    run_id = seed_run(db, [one_slice(q, "rag", total_count=5000)])
    client = FakeClient()
    client.graphql_pages = [
        (
            [make_repo(page * 100 + i + 1, stars=page * 100 + i + 1) for i in range(100)],
            5000,
            f"cursor-{page}",
        )
        for page in range(10)
    ]
    crawler = Crawler(settings, db, client)

    summary = crawler.run(resume=run_id, fetch_readmes=False, discovery="graphql")

    assert summary.status == "completed"
    assert summary.pages_fetched == 10
    assert summary.repos_seen == 1000
    assert summary.repos_inserted == 1000
    assert len(client.graphql_calls) == 10
    assert db.count_repos() == 1000
    assert db.get_repo(1).stars == 1


# ----------------------------------------------------------------- offline
def test_offline_error_marks_run_failed_and_reraises(db, settings):
    q = "topic:rag language:Python stars:>=20"
    run_id = seed_run(db, [one_slice(q, "rag", total_count=1)])
    client = FakeClient(search_error=OfflineError("offline mode"))
    crawler = Crawler(settings, db, client)

    with pytest.raises(OfflineError):
        crawler.run(resume=run_id, fetch_readmes=False)

    run = db.get_run(run_id)
    assert run["status"] == "failed"
    assert "offline" in (run["error"] or "")
    failed = db.pending_slices(run_id)
    assert len(failed) == 1
    assert failed[0]["status"] == "failed"
