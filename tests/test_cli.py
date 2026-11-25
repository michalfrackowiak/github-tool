"""Tests for the command-line interface (no live network)."""

from __future__ import annotations

import json

from github_tool.cli import main


def test_init_db_creates_database(tmp_path, capsys):
    db_path = tmp_path / "cli.db"
    code = main(["init-db", "--db", str(db_path)])
    out = capsys.readouterr()
    assert code == 0
    assert db_path.exists()
    assert "Database ready" in out.out


def test_keywords_json_writes_twelve_keywords(tmp_path, capsys):
    path = tmp_path / "keywords.json"
    code = main(["keywords", "--json", str(path)])
    out = capsys.readouterr()
    assert code == 0
    assert path.exists()
    assert "Wrote" in out.out
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["keywords"]) == 12


def test_links_prints_search_and_trending_urls(capsys):
    code = main(["links", "rag", "--language", "Python", "--window", "7d"])
    out = capsys.readouterr().out
    assert code == 0
    assert "https://github.com/search?" in out
    assert "https://github.com/trending/python?since=weekly" in out
    assert "pushed%3A%3E%3D" in out


def test_schedule_cron(capsys):
    code = main(["schedule", "--format", "cron"])
    out = capsys.readouterr().out
    assert code == 0
    assert "15 2 * * *" in out
    assert "crawl --profile default" in out


def test_trends_empty_state_returns_zero(tmp_path, capsys):
    db_path = tmp_path / "trends.db"
    code = main(["trends", "--db", str(db_path), "--limit", "5"])
    out = capsys.readouterr().out
    assert code == 0
    assert "No rows" in out


def test_extract_manifests_fetches_requirements_variants(monkeypatch, capsys, db, make_repo):
    from github_tool import cli

    db.upsert_repo(make_repo(710, "acme/multi-manifest"))
    db.update_readme(710, "## Install\n\npip install demo\n", '"etag"', "hash")

    class ManifestClient:
        def __init__(self):
            self.fetched: list[str] = []

        def repo_root_files(self, full_name):
            return [
                "requirements.txt",
                "requirements-dev.txt",
                "pyproject.toml",
                "docs",
            ]

        def get_file(self, full_name, path):
            self.fetched.append(path)
            return "requests==2.31.0\n"

        def close(self):
            pass

    client = ManifestClient()
    monkeypatch.setattr(cli, "_client", lambda settings, database: client)

    code = cli.main(["extract", "--db", str(db.path), "--manifests", "--limit", "1"])

    assert code == 0
    assert client.fetched == ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
    assert "Extracted 1 repos" in capsys.readouterr().out


def test_search_in_readme_flag_reaches_the_query(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace

    from github_tool import cli

    class Client:
        query = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def search_repositories(self, query, **kwargs):
            self.query = query
            return SimpleNamespace(
                items=[], total_count=0,
                rate_limit=SimpleNamespace(remaining=None, limit=None),
            )

    client = Client()
    monkeypatch.setattr(cli, "_client", lambda settings, database: client)

    code = cli.main(
        ["search", "rag", "--db", str(tmp_path / "search.db"), "--in-readme", "--limit", "1"]
    )

    assert code == 0
    assert "in:readme" in client.query


def test_search_include_forks_flag_reaches_the_query(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from github_tool import cli

    class Client:
        query = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def search_repositories(self, query, **kwargs):
            self.query = query
            return SimpleNamespace(
                items=[], total_count=0,
                rate_limit=SimpleNamespace(remaining=None, limit=None),
            )

    client = Client()
    monkeypatch.setattr(cli, "_client", lambda settings, database: client)

    code = cli.main(
        ["search", "rag", "--db", str(tmp_path / "search.db"), "--include-forks", "--limit", "1"]
    )

    assert code == 0
    assert "fork:true" in client.query


def test_unknown_keyword_returns_error(capsys):
    code = main(["links", "not-a-keyword"])
    captured = capsys.readouterr()
    assert code != 0
    assert "Unknown keyword" in captured.err
