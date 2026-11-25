"""Regressions for bugs found during reviewer passes."""

from __future__ import annotations

from datetime import timedelta
import hashlib
from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient

from github_tool.crawler import Crawler, _Stats
from github_tool.extraction import extract_for_repo
from github_tool.export import to_csv
from github_tool.cli import _trend_export_rows
from github_tool.models import Repo, StarDay, TrendRow, utc_today
from github_tool.planner import plan_slices
from github_tool.trends import _sorted_rows, get_trending, star_gain
from github_tool.web.app import create_app


class NoCallsClient:
    def search_repositories(self, *args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("no REST search expected")

    def search_graphql(self, *args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("no GraphQL search expected")

    def get_readme(self, *args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("no README fetch expected")


def test_crawler_written_hash_does_not_suppress_first_extraction(db, make_repo):
    text = "## Install\n\n```bash\npip install demo\n```\n"
    db.upsert_repo(make_repo(1, "acme/demo"))
    # The crawler stores readme_hash without running extraction.
    db.update_readme(1, text, '"etag"', hashlib.sha256(text.encode()).hexdigest())

    result = extract_for_repo(db, 1, text)

    assert result is not None
    assert any(c.cmd == "pip install demo" for c in result.commands)
    assert db.get_install_commands(1)


def test_resume_after_final_page_checkpoint_finalizes_slice(db, settings):
    run_id = db.start_run("smoke")
    db.add_slices(
        run_id,
        [{"query": "rag", "keyword": "rag", "language": "Python", "estimated_count": 5}],
    )
    slice_id = db.pending_slices(run_id)[0]["id"]
    db.update_slice(slice_id, pages_done=10, status="running")
    pending = db.pending_slices(run_id)[0]

    Crawler(settings, db, NoCallsClient())._run_rest_slice(
        run_id,
        pending,
        fetch_readmes=False,
        stats=_Stats(),
        max_pages=None,
    )

    assert db.slice_counts(run_id) == {"done": 1}


def test_repo_name_reuse_after_rename_keeps_both_rows(db, make_repo):
    db.upsert_repo(make_repo(1, "acme/name"))
    db.upsert_repo(make_repo(2, "acme/name"))
    db.upsert_repo(make_repo(1, "acme/renamed"))

    names = {r.id: r.full_name for r in db.list_repos(limit=10)}
    assert {1: "acme/renamed", 2: "acme/name"} == names


def test_stale_snapshot_is_not_reported_as_recent_gain(db, today, make_repo):
    db.upsert_repo(make_repo(500, "acme/stale"))
    db.save_snapshot(500, 10, 0, day=today - timedelta(days=120))
    db.save_snapshot(500, 50, 0, day=today)
    assert star_gain(db, 500, 7, today=today) == (0, False)


def test_partial_daily_data_is_not_a_complete_window(db, today, make_repo):
    db.upsert_repo(make_repo(501, "acme/partial"))
    db.save_star_days(501, [StarDay(today, 5)])
    gain, complete = star_gain(db, 501, 7, today=today)
    assert gain == 5
    assert complete is False


def test_search_filters_apply_to_local_results(settings, db, make_repo):
    db.upsert_repo(make_repo(1, "acme/mit", stars=500, license="MIT"))
    db.upsert_repo(make_repo(2, "acme/apache", stars=10, license="Apache-2.0"))
    app = create_app(settings, db, client=NoCallsClient())
    client = TestClient(app)

    response = client.get(
        "/search?keyword=rag&source=local&min_stars=100&license=MIT"
    )

    assert response.status_code == 200
    assert "acme/mit" in response.text
    assert "acme/apache" not in response.text


def test_csv_formula_cells_are_neutralized():
    assert to_csv([{"full_name": "=cmd|calc"}]) == 'full_name\n\'=cmd|calc\n'


def test_planner_count_budget_is_bounded():
    calls = []

    def count_fn(query: str) -> int:
        calls.append(query)
        return 5000

    slices = plan_slices("rag", "Python", count_fn, max_count_calls=3)

    assert len(calls) <= 3
    assert slices
    assert all(sl.overflow for sl in slices)


def test_manifest_hints_are_extracted_and_stored(db, make_repo):
    text = "## Install\n\n```bash\npip install demo\n```\n"
    db.upsert_repo(make_repo(700, "acme/manifest"))
    manifests = {
        "requirements.txt": "requests==2.31.0\n",
        "Dockerfile": "FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04\nENV CUDA_HOME=/usr/local/cuda\n",
    }

    result = extract_for_repo(db, 700, text, manifests=manifests)

    assert result is not None
    assert result.manifest is not None
    assert "requests==2.31.0" in result.manifest["python_dependencies"]
    assert any("cuda" in image for image in result.manifest["docker_base_images"])
    stored = db.get_manifest_hints(700)
    assert stored == result.manifest


def test_manifest_hints_are_persisted_even_when_readme_is_unchanged(db, make_repo):
    text = "## Install\n\n```bash\npip install demo\n```\n"
    db.upsert_repo(make_repo(702, "acme/no-change"))
    first = extract_for_repo(db, 702, text)
    assert first is not None

    again = extract_for_repo(
        db, 702, text, manifests={"requirements.txt": "requests==2.31.0\n"}
    )

    assert again is None
    assert "requests==2.31.0" in db.get_manifest_hints(702)["python_dependencies"]


def test_invalid_trend_sort_in_export_does_not_500(settings, db, make_repo):
    db.upsert_repo(make_repo(703, "acme/export-sort", stars=100))
    client = TestClient(create_app(settings, db, client=NoCallsClient()))

    assert client.get("/export.csv?trends=1&sort=bogus").status_code == 200
    assert client.get("/export.md?trends=1&sort=bogus").status_code == 200


def test_repo_page_shows_manifest_hints(settings, db, make_repo):
    from dataclasses import replace

    settings = replace(settings, offline=True)
    db.upsert_repo(make_repo(701, "acme/manifest-page"))
    db.update_manifest_hints(
        701,
        {
            "python_dependencies": ["requests==2.31.0"],
            "docker_base_images": ["nvidia/cuda:12.1.0"],
            "docker_env": {"CUDA_HOME": "/usr/local/cuda"},
            "gpu_hints": ["cuda"],
        },
    )
    client = TestClient(create_app(settings, db, client=NoCallsClient()))

    response = client.get("/repo/acme/manifest-page")

    assert response.status_code == 200
    assert "requests==2.31.0" in response.text
    assert "nvidia/cuda:12.1.0" in response.text


def test_window_derived_metrics_follow_selected_window():
    repo = Repo(
        id=900,
        full_name="acme/windows",
        url="https://github.com/acme/windows",
        stars=2000,
    )
    row = TrendRow(
        repo=repo,
        gains={1: 100, 7: 700, 30: 1390, 90: 2000, 365: 3000},
        relative_growth=53.85,
        acceleration=2.158,
        is_new=False,
    )

    assert row.relative_growth_for(7) == 53.85
    assert row.relative_growth_for(30) == pytest.approx(227.87)
    assert row.acceleration_for(7) == pytest.approx(round((700 / 7) / (1390 / 30), 3))
    assert row.acceleration_for(30) == pytest.approx(round((1390 / 30) / (2000 / 90), 3))
    assert row.acceleration_for(365) is None

    exported = _trend_export_rows([row], window=30)
    assert exported[0]["gain"] == 1390
    assert exported[0]["relative_growth"] == pytest.approx(227.87)
    assert exported[0]["acceleration"] == pytest.approx(round((1390 / 30) / (2000 / 90), 3))


def test_trends_page_shows_window_aware_relative_growth(db, settings, make_repo):
    today = utc_today()
    db.upsert_repo(make_repo(901, "acme/page-window", stars=2000))
    db.save_star_days(
        901,
        [StarDay(today - timedelta(days=o), 100) for o in range(7)]
        + [StarDay(today - timedelta(days=o), 30) for o in range(7, 30)],
    )
    client = TestClient(create_app(settings, db, client=NoCallsClient()))

    body = client.get("/trends?window=30d&min_stars=0").text

    assert "+1,390" in body
    assert "227.9%" in body
    assert "53.8%" not in body


def test_local_search_export_keeps_all_displayed_rows(db, settings, make_repo):
    db.upsert_repo(make_repo(902, "acme/rag", stars=200), keyword="rag")
    db.upsert_repo(make_repo(903, "acme/llm", stars=150), keyword="llm")
    client = TestClient(create_app(settings, db, client=NoCallsClient()))

    page = client.get("/search?keyword=rag&source=local&language=Python").text

    assert "acme/llm" in page
    match = re.search(r'href="(/export\.csv\?[^"]+)"', page)
    assert match is not None
    export_url = match.group(1)
    assert "keyword=" not in export_url
    body = client.get(export_url).text
    assert "acme/rag" in body
    assert "acme/llm" in body


def test_local_browse_honors_archived_and_fork_flags(db, settings, make_repo):
    db.upsert_repo(make_repo(930, "acme/normal", stars=200))
    db.upsert_repo(make_repo(931, "acme/old", stars=150, archived=True))
    db.upsert_repo(make_repo(932, "acme/forked", stars=120, fork=True))
    client = TestClient(create_app(settings, db, client=NoCallsClient()))

    plain = client.get("/search?keyword=rag&source=local&language=Python").text
    assert "acme/old" not in plain
    assert "acme/forked" not in plain

    included = client.get(
        "/search?keyword=rag&source=local&language=Python&archived=1&forks=1"
    ).text
    assert "acme/normal" in included
    assert "acme/old" in included
    assert "acme/forked" in included


def test_every_cli_option_has_help_text():
    from github_tool.cli import build_parser

    parser = build_parser()
    subparsers = next(a for a in parser._actions if a.dest == "command")
    for name, sub in subparsers.choices.items():
        for action in sub._actions:
            assert action.help, f"{name}: {action.option_strings or action.dest} lacks help"


def test_incomplete_window_has_no_growth_or_acceleration(db, make_repo):
    today = utc_today()
    db.upsert_repo(
        make_repo(
            920,
            "acme/partial",
            stars=1000,
            created_at=(today - timedelta(days=100)).isoformat(),
        )
    )
    # Only 7 of the 30 days are present, and the repo predates the window.
    db.save_star_days(920, [StarDay(today - timedelta(days=o), 10) for o in range(7)])

    row = get_trending(db, window=30, min_stars=0)[0]

    assert row.gain(30) == 70
    assert row.relative_growth_for(30) is None
    assert row.acceleration_for(30) is None
    out = _trend_export_rows([row], window=30)[0]
    assert out["relative_growth"] == ""
    assert out["acceleration"] == ""


def test_incomplete_windows_sort_below_complete_windows():
    def row(repo_id: int, gain30: int, complete30: bool) -> TrendRow:
        return TrendRow(
            repo=Repo(repo_id, f"acme/r{repo_id}", "https://github.com/acme", stars=5000),
            gains={1: 100, 7: 700, 30: gain30, 90: 9000, 365: 30000},
            relative_growth=14.0 if complete30 else None,
            acceleration=1.0 if complete30 else None,
            is_new=False,
            has_data={1: True, 7: True, 30: complete30, 90: True, 365: False},
        )

    complete = row(1, gain30=3000, complete30=True)
    incomplete = row(2, gain30=9000, complete30=False)

    for sort in ("accelerating", "fastest_growth"):
        ranked = _sorted_rows([incomplete, complete], sort, 30)
        assert ranked[0] is complete, f"{sort} ranked incomplete data first"


def test_max_fork_ratio_filters_inflated_stars(db, make_repo, settings):
    db.upsert_repo(make_repo(940, "acme/clean", stars=1000, forks=10))
    db.upsert_repo(make_repo(941, "acme/inflated", stars=100, forks=500))

    rows = get_trending(db, min_stars=0, max_fork_ratio=0.5)
    names = [r.repo.full_name for r in rows]
    assert "acme/clean" in names
    assert "acme/inflated" not in names
    exported = _trend_export_rows(rows, window=7)
    assert exported[0]["fork_ratio"] == 0.01

    client = TestClient(create_app(settings, db, client=NoCallsClient()))
    page = client.get("/trends?min_stars=0&max_fork_ratio=0.5").text
    assert "acme/clean" in page
    assert "acme/inflated" not in page
    assert "max_fork_ratio=0.5" in page


def test_json_export_shares_csv_filters(db, settings, make_repo):
    db.upsert_repo(make_repo(942, "acme/mit", license="MIT"))
    db.upsert_repo(make_repo(943, "acme/apache", license="Apache-2.0"))
    client = TestClient(create_app(settings, db, client=NoCallsClient()))

    payload = client.get("/export.json?license=MIT").json()
    assert payload["title"] == "Repository index"
    assert [row["full_name"] for row in payload["rows"]] == ["acme/mit"]
    csv_body = client.get("/export.csv?license=MIT").text
    assert "acme/mit" in csv_body
    assert "acme/apache" not in csv_body


def test_exports_honor_in_readme(db, settings, make_repo):
    db.upsert_repo(make_repo(960, "acme/readme-hit", stars=100), keyword="rag")
    db.update_readme(960, "RAG pipeline install guide", '"e1"', "h1")
    db.upsert_repo(make_repo(961, "acme/no-hit", stars=90), keyword="rag")
    db.update_readme(961, "A plain HTTP server", '"e2"', "h2")
    client = TestClient(create_app(settings, db, client=NoCallsClient()))

    payload = client.get("/export.json?keyword=rag&in_readme=1&min_stars=0").json()
    assert [row["full_name"] for row in payload["rows"]] == ["acme/readme-hit"]
    csv_body = client.get("/export.csv?keyword=rag&in_readme=1&min_stars=0").text
    assert "acme/readme-hit" in csv_body
    assert "acme/no-hit" not in csv_body

    page = client.get(
        "/search?keyword=rag&source=local&in_readme=1&min_stars=0"
    ).text
    assert "acme/readme-hit" in page
    assert "acme/no-hit" not in page


def test_local_readme_filter_uses_exact_keyword_in_export(db, settings, make_repo):
    db.upsert_repo(make_repo(962, "acme/mcp-hit", stars=100), keyword="mcp")
    db.update_readme(962, "MCP server install guide", '"e3"', "h3")
    client = TestClient(create_app(settings, db, client=NoCallsClient()))

    page = client.get("/search?keyword=mcp&source=local&in_readme=1&min_stars=0").text
    assert "acme/mcp-hit" in page
    assert "readme_q=MCP" in page
    payload = client.get(
        "/export.json?source=local&in_readme=1&readme_q=MCP&min_stars=0"
    ).json()
    assert [row["full_name"] for row in payload["rows"]] == ["acme/mcp-hit"]


def test_saved_search_keeps_in_readme(db, settings, make_repo):
    client = TestClient(create_app(settings, db, client=NoCallsClient()))
    response = client.post(
        "/saved",
        data={"name": "rag readme", "keyword": "rag", "in_readme": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    saved = client.get("/saved").text
    assert "in_readme=1" in saved


def test_non_finite_fork_ratio_is_rejected(db):
    with pytest.raises(ValueError, match="finite non-negative"):
        get_trending(db, min_stars=0, max_fork_ratio=float("nan"))
    with pytest.raises(ValueError, match="finite non-negative"):
        get_trending(db, min_stars=0, max_fork_ratio=float("inf"))


def test_active_within_filters_stale_repos(db, make_repo, settings):
    today = utc_today()
    db.upsert_repo(
        make_repo(
            950, "acme/fresh", stars=100,
            pushed_at=today.isoformat(),
        )
    )
    db.upsert_repo(
        make_repo(
            951, "acme/stale", stars=100,
            pushed_at=(today - timedelta(days=100)).isoformat(),
        )
    )

    names = [r.repo.full_name for r in get_trending(db, min_stars=0, active_within_days=30)]
    assert names == ["acme/fresh"]

    client = TestClient(create_app(settings, db, client=NoCallsClient()))
    page = client.get("/trends?min_stars=0&active_within=30").text
    assert "acme/fresh" in page
    assert "acme/stale" not in page
    payload = client.get("/export.json?trends=1&min_stars=0&active_within=30").json()
    assert [row["full_name"] for row in payload["rows"]] == ["acme/fresh"]


def test_oss_insight_period_values_match_link_builder():
    from github_tool.cli import build_parser
    from github_tool.links import OSS_INSIGHT_PERIODS

    parser = build_parser()
    commands = next(a for a in parser._actions if a.dest == "command")
    period_action = next(a for a in commands.choices["hints"]._actions if a.dest == "period")

    # The CLI sends these values straight to the OSS Insight API; the link
    # builder uses the same set. Live API check: past_24h returns HTTP 400.
    assert set(period_action.choices) == set(OSS_INSIGHT_PERIODS.values())


def test_readme_documents_keywords_command():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    assert "`github-tool keywords`" in readme


def test_bulk_trend_windows_matches_single_repo_results(db, make_repo):
    db.upsert_repo(make_repo(904, "acme/bulk", stars=2000))
    today = utc_today()
    db.save_star_days(
        904,
        [StarDay(today - timedelta(days=o), 100) for o in range(7)]
        + [StarDay(today - timedelta(days=o), 30) for o in range(7, 30)],
    )
    windows = (1, 7, 30, 90, 365)

    single = db.trend_windows(904, windows, today, None)
    bulk = db.bulk_trend_windows([904], windows, today, {904: None})

    assert bulk == {904: single}


def test_get_trending_does_not_open_a_connection_per_repo(db, make_repo):
    for i in range(5):
        db.upsert_repo(make_repo(910 + i, f"acme/bulk{i}", stars=100))
    original = db.connect
    calls: list[int] = []

    def counted():
        calls.append(1)
        return original()

    db.connect = counted
    try:
        assert len(get_trending(db, window=7, min_stars=0, limit=5)) == 5
    finally:
        db.connect = original

    # One connection for candidate selection plus one for the bulk windows.
    assert len(calls) <= 2
