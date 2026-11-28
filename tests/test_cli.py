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


def test_search_auto_saves_api_and_local_history(tmp_path, monkeypatch, make_repo):
    from types import SimpleNamespace

    from github_tool import cli
    from github_tool.db import Database

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def search_repositories(self, query, **kwargs):
            return SimpleNamespace(
                items=[make_repo(901, "acme/history", description="rag demo")],
                total_count=1,
                rate_limit=SimpleNamespace(remaining=None, limit=None),
            )

    monkeypatch.setattr(cli, "_client", lambda settings, database: Client())
    db_path = tmp_path / "history.db"
    db = Database(db_path)
    db.initialize()
    db.upsert_repo(make_repo(901, "acme/history", description="rag demo"))

    assert cli.main(
        [
            "search", "rag", "--db", str(db_path), "--in-readme",
            "--include-forks", "--limit", "1",
        ]
    ) == 0
    assert cli.main(["search", "rag", "--db", str(db_path), "--local", "--limit", "1"]) == 0

    entries = db.list_search_history()
    assert [entry["source"] for entry in entries] == ["local", "api"]
    api_params = entries[1]["params"]
    assert api_params["keyword"] == "rag"
    assert api_params["in_readme"] == "1"
    assert api_params["forks"] == "1"
    assert api_params["limit"] == "1"
    assert entries[1]["result_count"] == 1
    assert entries[0]["source"] == "local"
    assert entries[0]["params"]["q"] == "RAG"  # effective local FTS query
    assert "language" not in entries[0]["params"]  # --language is ignored by local search


def test_search_explicit_query_records_effective_window(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from github_tool import cli
    from github_tool.db import Database

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def search_repositories(self, query, **kwargs):
            return SimpleNamespace(
                items=[],
                total_count=0,
                rate_limit=SimpleNamespace(remaining=None, limit=None),
            )

    monkeypatch.setattr(cli, "_client", lambda settings, database: Client())
    db_path = tmp_path / "explicit.db"
    Database(db_path).initialize()

    assert cli.main(
        ["search", "rag", "--db", str(db_path), "--query", "retrieval", "--window", "7d"]
    ) == 0

    entry = Database(db_path).list_search_history()[0]
    assert entry["params"]["q"].startswith("retrieval pushed:>=")
    assert entry["params"]["window"] == "7d"


def test_history_write_failure_does_not_hide_cli_results(tmp_path, monkeypatch, capsys, make_repo):
    from github_tool import cli
    from github_tool.db import Database

    db_path = tmp_path / "history-failure.db"
    db = Database(db_path)
    db.initialize()
    db.upsert_repo(make_repo(902, "acme/cli-history-failure", description="rag"))

    def fail_history(self, *args, **kwargs):
        raise RuntimeError("history storage unavailable")

    monkeypatch.setattr(cli.Database, "record_search", fail_history)

    assert cli.main(["search", "rag", "--db", str(db_path), "--local", "--limit", "1"]) == 0
    assert "acme/cli-history-failure" in capsys.readouterr().out
