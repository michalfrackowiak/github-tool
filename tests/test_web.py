"""Tests for the FastAPI web UI, always with an injected fake client."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from github_tool.models import RateLimit, ReadmeResult, Repo, SearchPage, StarDay
from github_tool.web.app import create_app


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


def test_offline_local_search_never_calls_client(web, db, make_repo):
    db.upsert_repo(make_repo(207, "acme/offline", language="Python"))
    client = web(offline=True, client=ExplodingClient())
    response = client.get("/search?keyword=rag&source=local&language=Python")
    assert response.status_code == 200
    assert "acme/offline" in response.text
