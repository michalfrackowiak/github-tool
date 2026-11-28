"""Tests for the SQLite store."""

from __future__ import annotations

from datetime import date, timedelta

from github_tool.db import SCHEMA_VERSION
from github_tool.models import Repo, StarDay


TODAY = date(2026, 11, 24)


def _repo(repo_id: int = 1, *, name: str | None = None, **overrides) -> Repo:
    full_name = name or f"owner{repo_id}/repo{repo_id}"
    values = dict(
        id=repo_id,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        description="A demo repository",
        language="Python",
        topics=["rag", "llm"],
        stars=100,
        forks=5,
    )
    values.update(overrides)
    return Repo(**values)


def test_initialize_is_idempotent_and_sets_version(db):
    db.initialize()
    db.initialize()
    with db.connect() as conn:
        row = conn.execute("SELECT value FROM schema_meta WHERE key='version'").fetchone()
    assert row is not None
    assert int(row["value"]) == SCHEMA_VERSION


def test_upsert_dedupes_by_numeric_id(db):
    first = db.upsert_repo(_repo(1))
    second = db.upsert_repo(_repo(1, stars=200))
    assert first is True
    assert second is False
    assert db.count_repos() == 1
    assert db.get_repo(1).stars == 200


def test_upsert_rename_preserves_readme(db):
    db.upsert_repo(_repo(1, name="old/name", readme_text="README body", readme_etag='"etag-1"'))
    db.upsert_repo(_repo(1, name="new/name", readme_text=None, readme_etag=None))
    repo = db.get_repo(1)
    assert repo.full_name == "new/name"
    assert repo.readme_text == "README body"
    assert repo.readme_etag == '"etag-1"'
    assert db.get_repo("new/name").id == 1


def test_topics_round_trip(db):
    db.upsert_repo(_repo(2, topics=["database", "sql"]))
    repo = db.get_repo(2)
    assert repo.topics == ["database", "sql"]


def test_fts_search_by_readme_and_description(db):
    db.upsert_repo(
        _repo(
            1,
            description="Vector search engine for embeddings",
            readme_text="This library makes retrieval augmented generation easy.",
        )
    )
    db.upsert_repo(_repo(2, description="Unrelated tool", readme_text="Nothing to see here."))

    assert [r.id for r in db.search_fts("retrieval")] == [1]
    assert [r.id for r in db.search_fts("vector")] == [1]
    assert db.search_fts("zzzznotthere") == []


def test_fts_handles_quotes_and_punctuation(db):
    db.upsert_repo(
        _repo(
            1,
            description="A Database toolkit (C++), fast",
            readme_text="Works with PostgreSQL.",
        )
    )
    # These would be FTS5 syntax errors if the input were not sanitised.
    results = db.search_fts('"Database" (C++), toolkit')
    assert [r.id for r in results] == [1]
    assert db.search_fts('"') == []
    assert db.search_fts("!!! ???") == []


def test_keyword_counts(db):
    db.upsert_repo(_repo(1), keyword="rag")
    db.upsert_repo(_repo(2), keyword="rag")
    db.upsert_repo(_repo(3), keyword="llm")
    assert db.keyword_counts() == {"rag": 2, "llm": 1}


def test_star_daily_upsert_and_inclusive_window(db):
    db.upsert_repo(_repo(1))
    db.save_star_days(
        1,
        [
            StarDay(TODAY, 5),
            StarDay(TODAY - timedelta(days=6), 11),
            StarDay(TODAY - timedelta(days=10), 99),
        ],
    )
    db.save_star_days(1, [StarDay(TODAY, 7)])  # upsert replaces today's row

    rows, total = db.sum_star_days(1, 7, today=TODAY)
    assert rows == 2
    assert total == 18  # 7 + 11, the 10-day-old row is outside the window

    stored = db.get_star_days(1, since=TODAY - timedelta(days=6), until=TODAY)
    assert [(d.day, d.gained) for d in stored] == [
        (TODAY - timedelta(days=6), 11),
        (TODAY, 7),
    ]


def test_snapshot_fallback_and_count(db):
    db.upsert_repo(_repo(1))
    assert db.snapshot_gain(1, 7, today=TODAY) is None
    db.save_snapshot(1, 100, 1, day=TODAY - timedelta(days=7))
    db.save_snapshot(1, 150, 2, day=TODAY)
    assert db.snapshot_count(1) == 2
    assert db.snapshot_gain(1, 7, today=TODAY) == 50

    db.save_snapshot(1, 160, 3, day=TODAY)  # upsert same day
    assert db.snapshot_count(1) == 2
    assert db.snapshot_gain(1, 7, today=TODAY) == 60


def test_crawl_run_lifecycle(db):
    run_id = db.start_run("ai")
    run = db.get_run(run_id)
    assert run["profile"] == "ai"
    assert run["status"] == "running"
    assert db.latest_run()["id"] == run_id

    db.add_slices(
        run_id,
        [
            {"query": "topic:rag language:Python", "keyword": "rag", "language": "Python", "total_count": 5},
            {"query": "topic:llm language:Python", "keyword": "llm", "language": "Python", "total_count": 900},
        ],
    )
    pending = db.pending_slices(run_id)
    assert [p["query"] for p in pending] == [
        "topic:rag language:Python",
        "topic:llm language:Python",
    ]

    db.update_slice(pending[0]["id"], status="done", pages_done=1)
    db.update_slice(pending[1]["id"], status="failed", error="boom")
    assert [p["query"] for p in db.pending_slices(run_id)] == ["topic:llm language:Python"]
    assert db.slice_counts(run_id) == {"done": 1, "failed": 1}

    db.update_run(run_id, status="done", cursor='{"next": 2}', finished_at="2026-11-24T00:00:00Z")
    run = db.get_run(run_id)
    assert run["status"] == "done"
    assert run["cursor"] == '{"next": 2}'
    assert run["finished_at"] == "2026-11-24T00:00:00Z"


def test_saved_searches_upsert_list_delete(db):
    db.save_search("Weekly RAG", {"keyword": "rag", "window": "7d"})
    db.save_search("Weekly RAG", {"keyword": "rag", "window": "30d"})
    db.save_search("LLM", {"keyword": "llm"})

    saved = db.list_saved_searches()
    assert [s["name"] for s in saved] == ["LLM", "Weekly RAG"]
    rag = next(s for s in saved if s["name"] == "Weekly RAG")
    assert rag["params"]["window"] == "30d"

    assert db.delete_saved_search("LLM") is True
    assert db.delete_saved_search("LLM") is False
    assert [s["name"] for s in db.list_saved_searches()] == ["Weekly RAG"]


def test_http_cache_round_trip(db):
    assert db.get_http_cache("https://api.github.com/x") is None
    db.put_http_cache("https://api.github.com/x", '"abc"', '{"ok": true}')
    assert db.get_http_cache("https://api.github.com/x") == ('"abc"', '{"ok": true}')

    db.put_http_cache("https://api.github.com/x", '"def"', '{"ok": false}')
    assert db.get_http_cache("https://api.github.com/x") == ('"def"', '{"ok": false}')


def test_extraction_tables_replace_get_and_mark_status(db):
    db.upsert_repo(_repo(1))
    db.replace_install_commands(
        1,
        [
            {"cmd": "pip install demo", "source_line": 3, "confidence": "high"},
            {"cmd": "python -m demo", "source_line": 5, "confidence": "low", "command_type": "run"},
        ],
    )
    commands = db.get_install_commands(1)
    assert [c["cmd"] for c in commands] == ["pip install demo", "python -m demo"]
    assert commands[1]["command_type"] == "run"

    db.replace_install_commands(1, [{"cmd": "uv pip install demo", "source_line": 3, "confidence": "medium"}])
    assert [c["cmd"] for c in db.get_install_commands(1)] == ["uv pip install demo"]

    db.replace_hw_requirements(
        1,
        [{"gpu": True, "vram_gb": 24.0, "source_line": 7, "confidence": "medium"}],
    )
    reqs = db.get_hw_requirements(1)
    assert len(reqs) == 1
    assert reqs[0]["vram_gb"] == 24.0

    assert db.extraction_status(1)["extracted_at"] is None
    db.mark_extracted(1, "hash-abc")
    status = db.extraction_status(1)
    assert status["readme_hash"] == "hash-abc"
    assert status["extracted_at"]


def test_export_rows_filters(db):
    db.upsert_repo(_repo(1, language="Python", stars=500))
    db.upsert_repo(_repo(2, language="Rust", stars=50))
    db.upsert_repo(_repo(3, language="Python", stars=5, archived=True))
    db.upsert_repo(_repo(4, language="Python", stars=900, fork=True))

    names = [r["full_name"] for r in db.export_rows(language="Python")]
    assert names == ["owner1/repo1"]

    assert {r["id"] for r in db.export_rows(min_stars=50)} == {1, 2}
    assert {r["id"] for r in db.export_rows(min_stars=50, include_forks=True)} == {1, 2, 4}
    assert {r["id"] for r in db.export_rows(language="Python", include_archived=True)} == {1, 3}
    assert {r["id"] for r in db.export_rows(language="Python", include_forks=True)} == {1, 4}

    rows = db.export_rows(limit=2)
    assert len(rows) == 2
    assert {"id", "full_name", "url", "description", "language", "stars", "forks", "license"} <= set(rows[0])


def test_search_history_is_separate_from_named_saves(db):
    db.save_search("Weekly RAG", {"keyword": "rag"})
    db.record_search(
        {"keyword": "rag", "source": "local", "language": ["Python"]},
        source="local",
        result_count=3,
    )
    db.record_search({"keyword": "llm", "source": "api"}, source="api", result_count=8)

    history = db.list_search_history()
    assert [entry["source"] for entry in history] == ["api", "local"]
    assert history[0]["params"] == {"keyword": "llm", "source": "api"}
    assert history[1]["result_count"] == 3
    assert [s["name"] for s in db.list_saved_searches()] == ["Weekly RAG"]

    assert db.clear_search_history() == 2
    assert db.list_search_history() == []
    assert [s["name"] for s in db.list_saved_searches()] == ["Weekly RAG"]


def test_crawl_job_claim_is_single_flight_and_updates(db):
    params = {"profile": "ai", "max_slices": 1}
    claimed = db.claim_crawl_job("job-1", "ai", params)
    assert claimed is not None
    assert claimed["status"] == "queued"
    assert db.claim_crawl_job("job-2", "ai", params) is None
    assert db.active_crawl_job()["id"] == "job-1"

    db.update_crawl_job(
        "job-1",
        status="running",
        phase="crawling",
        run_id="run-1",
        summary={"slices_done": 1, "repos_inserted": 2, "repos_updated": 1},
    )
    job = db.get_crawl_job("job-1")
    assert job["status"] == "running"
    assert job["run_id"] == "run-1"
    assert job["summary"]["repos_updated"] == 1
    assert job["params"] == params

    db.update_crawl_job(
        "job-1",
        status="completed",
        phase="done",
        summary={"slices_done": 1},
        finished_at="2026-11-28T00:00:00Z",
    )
    assert db.active_crawl_job() is None
    assert db.get_crawl_job("job-1")["status"] == "completed"
    assert db.claim_crawl_job("job-3", "ai", params) is not None


def test_initialize_upgrades_schema_version_and_adds_phase11_tables(tmp_path):
    from github_tool.db import Database

    path = tmp_path / "old.db"
    database = Database(path)
    database.initialize()
    with database.connect() as conn:
        conn.execute("DROP TABLE search_history")
        conn.execute("DROP TABLE crawl_jobs")
        conn.execute("DELETE FROM schema_meta WHERE key='version'")
        conn.execute("INSERT INTO schema_meta(key, value) VALUES('version', '1')")

    database.initialize()
    with database.connect() as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        version = conn.execute(
            "SELECT value FROM schema_meta WHERE key='version'"
        ).fetchone()[0]
    assert {"search_history", "crawl_jobs"} <= tables
    assert version == "2"


def test_stale_crawl_job_is_released_and_run_lookup_is_time_bounded(db):
    assert db.claim_crawl_job("stale", "ai", {"profile": "ai"}) is not None
    with db.connect() as conn:
        conn.execute(
            "UPDATE crawl_jobs SET updated_at='2020-01-01T00:00:00Z' WHERE id='stale'"
        )
    assert db.reap_stale_crawl_jobs() == 1
    assert db.active_crawl_job() is None
    stale = db.get_crawl_job("stale")
    assert stale["status"] == "failed"
    assert "restart" in stale["error"]

    run_id = db.start_run("ai")
    assert db.latest_run_since("2020-01-01T00:00:00Z")["id"] == run_id
    assert db.latest_run_since("2100-01-01T00:00:00Z") is None
