"""Shared fixtures for the github-tool test suite (no live network)."""

from __future__ import annotations

from datetime import date

import pytest

from github_tool.config import Settings
from github_tool.db import Database
from github_tool.models import Repo


FIXED_TODAY = date(2026, 11, 24)


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Isolated settings: temp database, fast tests, fake token."""
    return Settings(
        db_path=tmp_path / "test.db",
        token="test-token",
        search_min_interval=0.0,
        offline=False,
    )


@pytest.fixture
def db(settings: Settings) -> Database:
    database = Database(settings.db_path)
    database.initialize()
    return database


@pytest.fixture
def today() -> date:
    return FIXED_TODAY


@pytest.fixture
def make_repo():
    """Factory returning a Repo with sensible, override-friendly defaults."""

    def _make_repo(
        repo_id: int = 1,
        full_name: str | None = None,
        *,
        stars: int = 100,
        forks: int = 10,
        language: str | None = "Python",
        description: str | None = "A demo repository",
        license: str | None = "MIT",
        created_at: str | None = "2025-01-01T00:00:00Z",
        pushed_at: str | None = "2026-11-01T00:00:00Z",
        updated_at: str | None = "2026-11-02T00:00:00Z",
        archived: bool = False,
        fork: bool = False,
        topics: list[str] | None = None,
        readme_text: str | None = None,
        readme_etag: str | None = None,
    ) -> Repo:
        name = full_name or f"owner{repo_id}/repo{repo_id}"
        return Repo(
            id=repo_id,
            full_name=name,
            url=f"https://github.com/{name}",
            description=description,
            language=language,
            topics=list(topics or []),
            created_at=created_at,
            pushed_at=pushed_at,
            updated_at=updated_at,
            archived=archived,
            fork=fork,
            stars=stars,
            forks=forks,
            license=license,
            readme_text=readme_text,
            readme_etag=readme_etag,
        )

    return _make_repo
