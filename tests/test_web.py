"""Tests for the FastAPI web UI, always with an injected fake client."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from github_tool.github import GitHubError
from github_tool.models import RateLimit, ReadmeResult, Repo, SearchPage, StarDay
from github_tool.web.app import create_app, run_crawl_job


def _today():
    return datetime.now(timezone.utc).date()


class FakeClient:
    def __init__(self, repos: list[Repo] | None = None, readme_text: str | None = None):
        self.repos = repos or []
        self.readme_text = readme_text
        self.search_calls: list[tuple[str, dict]] = []
        self.readme_calls: list[str] = []
        self.closed = False

    def search_repositories(self, query: str, **kwargs):
        self.search_calls.append((query, kwargs))
        return SearchPage(
            items=list(self.repos),
            total_count=len(self.repos),
            rate_limit=RateLimit(limit=30, remaining=29, reset=0, resource="search"),
        )

    def count_search(self, query: str) -> int:
        return len(self.repos)

    def get_readme(self, full_name: str, etag: str | None = None) -> ReadmeResult:
        self.readme_calls.append(full_name)
        return ReadmeResult(text=self.readme_text, etag='"readme-etag"')

    def close(self) -> None:
        self.closed = True


class ExplodingClient(FakeClient):
    def search_repositories(self, query, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("offline local search must not call the GitHub client")

    def get_readme(self, full_name, etag=None):  # pragma: no cover - must not run
        raise AssertionError("offline local search must not call the GitHub client")


class FailingClient(FakeClient):
    def search_repositories(self, query, **kwargs):
        raise GitHubError("search unavailable")


@pytest.fixture
def web(settings, db):
    def _make(*, offline: bool = False, client=None):
        active = replace(settings, offline=offline)
        app = create_app(active, db, client=client)
        return TestClient(app)

    return _make


def test_home_shows_keyword_chips(web):
    client = web(client=FakeClient())
    response = client.get("/")
    assert response.status_code == 200
    assert "RAG" in response.text
    assert "Vector DB" in response.text
    assert "Local index" in response.text


def test_home_shows_offline_banner(web):
    client = web(offline=True, client=FakeClient())
    response = client.get("/")
    assert response.status_code == 200
    assert "Offline mode" in response.text


def test_links_page_contains_github_search_url(web):
    client = web(client=FakeClient())
    response = client.get("/links?keyword=rag&language=Python&window=7d")
    assert response.status_code == 200
    assert "https://github.com/search?" in response.text
    assert "https://github.com/trending/python" in response.text


def test_local_search_returns_repo_and_escapes_description(web, db, make_repo):
    db.upsert_repo(
        make_repo(
            201,
            "acme/escape",
            description="<script>alert(1)</script>",
            language="Python",
            stars=123,
        )
    )
    client = web(client=FakeClient())
    response = client.get("/search?keyword=rag&source=local&language=Python")
    assert response.status_code == 200
    assert "acme/escape" in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
    assert "<script>alert(1)</script>" not in response.text


def test_api_search_returns_and_stores_repo(web, db, make_repo):
    repo = make_repo(202, "acme/api-result", language="Python", stars=500)
    fake = FakeClient(repos=[repo])
    client = web(client=fake)

    response = client.get("/search?keyword=rag&source=api&language=Python")
    assert response.status_code == 200
    assert "acme/api-result" in response.text

    assert fake.search_calls
    query, _kwargs = fake.search_calls[0]
    assert "language:Python" in query
    assert db.get_repo(202) is not None


def test_trends_page_shows_gain_and_new_badge(web, db, make_repo):
    today = _today()
    created = (today - timedelta(days=10)).isoformat() + "T00:00:00Z"
    db.upsert_repo(make_repo(203, "acme/rising", stars=100, created_at=created))
    db.save_star_days(203, [StarDay(today, 10), StarDay(today - timedelta(days=1), 5)])

    client = web(client=FakeClient())
    response = client.get("/trends?window=7d")
    assert response.status_code == 200
    assert "acme/rising" in response.text
    assert "+15" in response.text
    assert "new" in response.text


def test_repo_page_sanitises_readme_and_extracts_install_command(web, db, make_repo):
    readme = (
        "# Demo\n\n"
        "<script>alert(1)</script>\n\n"
        "```bash\npip install demo\n```\n"
    )
    db.upsert_repo(
        make_repo(
            204,
            "acme/demo",
            readme_text=readme,
            description="Demo project",
            stars=250,
        )
    )
    today = _today()
    db.save_star_days(204, [StarDay(today, 3), StarDay(today - timedelta(days=1), 2)])

    client = web(client=FakeClient())
    response = client.get("/repo/acme/demo")
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text
    assert "pip install demo" in response.text
    assert '<svg class="sparkline"' in response.text


def test_missing_repo_offline_returns_404(web):
    client = web(offline=True, client=ExplodingClient())
    response = client.get("/repo/missing/repo")
    assert response.status_code == 404
    assert "not in the local index" in response.text


def test_saved_search_post_get_and_delete(web, db):
    client = web(client=FakeClient())
    response = client.post(
        "/saved",
        data={
            "name": "myragsearch",
            "keyword": "rag",
            "window": "7d",
            "source": "local",
            "sort": "stars",
            "language": "Python",
            "q": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    listing = client.get("/saved")
    assert listing.status_code == 200
    assert "myragsearch" in listing.text

    deleted = client.post("/saved/delete", data={"name": "myragsearch"}, follow_redirects=False)
    assert deleted.status_code == 303
    assert "myragsearch" not in client.get("/saved").text


def test_export_csv_and_markdown(web, db, make_repo):
    db.upsert_repo(make_repo(205, "acme/exportable", description="A row, with comma"))
    client = web(client=FakeClient())

    csv_response = client.get("/export.csv")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=github-tool.csv" in csv_response.headers["content-disposition"]
    assert "full_name" in csv_response.text
    assert "acme/exportable" in csv_response.text

    md_response = client.get("/export.md")
    assert md_response.status_code == 200
    assert md_response.headers["content-type"].startswith("text/markdown")
    assert "attachment; filename=github-tool.md" in md_response.headers["content-disposition"]
    assert "acme/exportable" in md_response.text


def test_health_json(web, db, make_repo):
    db.upsert_repo(make_repo(206, "acme/health"))
    client = web(client=FakeClient())
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["repos"] == 1
    assert payload["offline"] is False


def test_web_search_in_readme_reaches_api_query(web):
    api = FakeClient()
    client = web(client=api)

    response = client.get("/search?keyword=rag&source=api&in_readme=1")

    assert response.status_code == 200
    assert api.search_calls
    assert all("in:readme" in query for query, _ in api.search_calls)
    assert "in_readme=1" in response.text
    assert "Match README text" in response.text


def test_web_search_include_forks_reaches_api_query(web):
    api = FakeClient()
    client = web(client=api)

    response = client.get("/search?keyword=rag&source=api&forks=1")

    assert response.status_code == 200
    assert api.search_calls
    assert all("fork:true" in query for query, _ in api.search_calls)
    assert "forks=1" in response.text


def test_offline_local_search_never_calls_client(web, db, make_repo):
    db.upsert_repo(make_repo(207, "acme/offline", language="Python"))
    client = web(offline=True, client=ExplodingClient())
    response = client.get("/search?keyword=rag&source=local&language=Python")
    assert response.status_code == 200
    assert "acme/offline" in response.text


def test_web_search_auto_saves_replayable_history(web, db, make_repo):
    db.upsert_repo(make_repo(208, "acme/history-web", description="rag", language="Python"))
    client = web(client=FakeClient())

    response = client.get(
        "/search?keyword=rag&source=local&language=Python&sort=stars&limit=5"
    )
    assert response.status_code == 200

    entries = db.list_search_history()
    assert len(entries) == 1
    assert entries[0]["source"] == "local"
    assert entries[0]["result_count"] == 1
    assert entries[0]["params"]["keyword"] == "rag"
    assert entries[0]["params"]["language"] == ["Python"]
    assert entries[0]["params"]["limit"] == "5"

    saved = client.get("/saved")
    assert "Automatic search history" in saved.text
    assert "Replay" in saved.text
    assert "keyword=rag" in saved.text

    cleared = client.post("/saved/history/clear", follow_redirects=False)
    assert cleared.status_code == 303
    assert db.list_search_history() == []


def test_crawl_button_rejects_offline(web):
    client = web(offline=True, client=FakeClient())
    response = client.post("/crawl", data={"profile": "ai"}, follow_redirects=False)
    assert response.status_code == 503
    assert "offline" in response.text.lower()


def test_crawl_button_is_single_flight(web):
    client = web(client=FakeClient())
    client.app.state.crawl_runner = lambda job_id, params: None  # leave job queued

    first = client.post("/crawl", data={"profile": "ai"}, follow_redirects=False)
    assert first.status_code == 303
    assert first.headers["location"].startswith("/crawl?job=")

    second = client.post("/crawl", data={"profile": "ai"}, follow_redirects=False)
    assert second.status_code == 409
    assert "already running" in second.text.lower()


def test_crawl_button_runs_crawler_and_persists_repos(web, db, make_repo):
    from github_tool.crawler import CrawlSummary
    from github_tool.web.app import run_crawl_job

    class WorkerClient:
        def close(self):
            pass

    class FakeCrawler:
        def __init__(self, settings, database, client):
            self.database = database

        def run(self, **kwargs):
            assert kwargs["profile"] == "ai"
            assert kwargs["max_slices"] == 1
            assert kwargs["max_pages_per_slice"] == 2
            self.database.upsert_repo(make_repo(209, "acme/web-crawled"), keyword="rag")
            return CrawlSummary(
                run_id="web-run-id",
                profile="ai",
                status="completed",
                slices_total=1,
                slices_done=1,
                repos_seen=1,
                repos_inserted=1,
            )

    client = web(client=FakeClient())

    def runner(job_id, params):
        run_crawl_job(
            client.app.state.settings,
            job_id,
            params,
            db,
            crawler_factory=FakeCrawler,
            client_factory=lambda settings, database: WorkerClient(),
        )

    client.app.state.crawl_runner = runner
    response = client.post(
        "/crawl",
        data={"profile": "ai", "max_slices": "1", "max_pages_per_slice": "2"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    job_id = response.headers["location"].split("job=")[1]

    status = client.get(f"/crawl/status/{job_id}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "completed"
    assert payload["run_id"] == "web-run-id"
    assert payload["summary"]["repos_inserted"] == 1
    assert db.get_repo(209) is not None

    page = client.get(f"/crawl?job={job_id}")
    assert "web-run" in page.text
    assert "1 new" in page.text


def test_crawl_status_tracks_run_started_after_job(web, db):
    client = web(client=FakeClient())
    client.app.state.crawl_runner = lambda job_id, params: None
    response = client.post("/crawl", data={"profile": "ai"}, follow_redirects=False)
    job_id = response.headers["location"].split("job=")[1]

    run_id = db.start_run("ai")
    status = client.get(f"/crawl/status/{job_id}")
    assert status.status_code == 200
    assert status.json()["run"]["id"] == run_id


def test_app_startup_releases_stale_crawl_job(settings, db):
    from github_tool.web.app import create_app

    db.claim_crawl_job("stale-web", "ai", {"profile": "ai"})
    with db.connect() as conn:
        conn.execute(
            "UPDATE crawl_jobs SET updated_at='2020-01-01T00:00:00Z' WHERE id='stale-web'"
        )

    create_app(settings, db, client=FakeClient())

    assert db.active_crawl_job() is None
    assert db.get_crawl_job("stale-web")["status"] == "failed"


def test_failed_api_search_does_not_create_history(web, db):
    client = web(client=FailingClient())

    response = client.get("/search?keyword=rag&source=api")

    assert response.status_code == 200
    assert "search unavailable" in response.text
    assert db.list_search_history() == []


def test_history_write_failure_does_not_hide_search_results(web, db, make_repo, monkeypatch):
    db.upsert_repo(make_repo(210, "acme/history-failure", description="rag", language="Python"))

    def fail_history(*args, **kwargs):
        raise RuntimeError("history storage unavailable")

    monkeypatch.setattr(db, "record_search", fail_history)
    client = web(client=FakeClient())

    response = client.get("/search?keyword=rag&source=local&language=Python")

    assert response.status_code == 200
    assert "acme/history-failure" in response.text


def test_crawl_form_validates_and_caps_numeric_options(web, db):
    client = web(client=FakeClient())
    client.app.state.crawl_runner = lambda job_id, params: None

    assert client.post("/crawl", data={"profile": "not-a-profile"}).status_code == 400
    assert client.post("/crawl", data={"profile": "ai", "max_slices": "abc"}).status_code == 400

    response = client.post(
        "/crawl",
        data={"profile": "ai", "max_slices": "99", "max_pages_per_slice": "99"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    job = db.active_crawl_job()
    assert job["params"]["max_slices"] == 5
    assert job["params"]["max_pages_per_slice"] == 3


def test_crawl_setup_failure_marks_job_failed(web, db):
    client = web(client=FakeClient())
    app = client.app

    def bad_factory(settings, database):
        raise RuntimeError("client setup failed")

    app.state.crawl_runner = lambda job_id, params: run_crawl_job(
        app.state.settings, job_id, params, db, client_factory=bad_factory
    )
    response = client.post("/crawl", data={"profile": "ai"}, follow_redirects=False)

    assert response.status_code == 303
    job_id = response.headers["location"].split("job=")[1]
    status = client.get(f"/crawl/status/{job_id}").json()
    assert status["status"] == "failed"
    assert "client setup failed" in status["error"]
    assert db.active_crawl_job() is None


def test_crawl_runner_exception_marks_job_failed(web, db):
    client = web(client=FakeClient())

    def boom(job_id, params):
        raise RuntimeError("runner failed")

    client.app.state.crawl_runner = boom
    response = client.post("/crawl", data={"profile": "ai"}, follow_redirects=False)

    assert response.status_code == 303
    job_id = response.headers["location"].split("job=")[1]
    status = client.get(f"/crawl/status/{job_id}").json()
    assert status["status"] == "failed"
    assert "runner failed" in status["error"]
    assert db.active_crawl_job() is None


def test_crawl_auto_refresh_is_in_document_head(web):
    client = web(client=FakeClient())
    client.app.state.crawl_runner = lambda job_id, params: None
    response = client.post("/crawl", data={"profile": "ai"}, follow_redirects=False)
    job_id = response.headers["location"].split("job=")[1]

    page = client.get(f"/crawl?job={job_id}").text
    head = page.split("</head>", 1)[0]
    assert 'http-equiv="refresh"' in head
    assert 'http-equiv="refresh"' not in page.split("</head>", 1)[1]
