"""Tests for the trend engine (no live network)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from github_tool import trends
from github_tool.db import Database
from github_tool.github import OssInsightResult
from github_tool.models import Repo, StarDay


TODAY = date(2026, 11, 24)


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "trends.db")
    database.initialize()
    return database


def make_repo(
    repo_id: int,
    name: str,
    *,
    stars: int = 100,
    forks: int = 10,
    created_at: str | None = "2025-01-01T00:00:00Z",
    pushed_at: str | None = "2026-11-01T00:00:00Z",
    archived: bool = False,
    fork: bool = False,
    language: str | None = "Python",
    license: str | None = "MIT",
) -> Repo:
    return Repo(
        id=repo_id,
        full_name=name,
        url=f"https://github.com/{name}",
        created_at=created_at,
        pushed_at=pushed_at,
        archived=archived,
        fork=fork,
        stars=stars,
        forks=forks,
        language=language,
        license=license,
    )


def seed_daily(db, repo_id: int, offsets: dict[int, int], today: date = TODAY) -> None:
    db.save_star_days(
        repo_id,
        [StarDay(today - timedelta(days=offset), gain) for offset, gain in offsets.items()],
    )


def seed_week(db, repo_id: int, per_day: int, today: date = TODAY) -> int:
    """Seed the last 7 days (offsets 0..6); return the 7-day total."""
    seed_daily(db, repo_id, {offset: per_day for offset in range(7)}, today)
    return per_day * 7


# ---------------------------------------------------------------- star_gain
def test_star_gain_prefers_daily_data(db):
    repo = make_repo(1, "acme/daily", stars=100)
    db.upsert_repo(repo)
    seed_week(db, repo.id, 10)

    assert trends.star_gain(db, repo.id, 7, today=TODAY) == (70, True)


def test_star_gain_falls_back_to_snapshots(db):
    repo = make_repo(2, "acme/snapshot", stars=100)
    db.upsert_repo(repo)
    db.save_snapshot(repo.id, 80, 0, TODAY - timedelta(days=7))
    db.save_snapshot(repo.id, 100, 0, TODAY)

    assert trends.star_gain(db, repo.id, 7, today=TODAY) == (20, True)


def test_star_gain_without_data(db):
    repo = make_repo(3, "acme/empty", stars=100)
    db.upsert_repo(repo)

    assert trends.star_gain(db, repo.id, 7, today=TODAY) == (0, False)


# ----------------------------------------------------------- compute_trend_row
def test_compute_trend_row_metrics(db):
    repo = make_repo(
        10,
        "acme/trending",
        stars=1000,
        created_at=(TODAY - timedelta(days=30)).isoformat() + "T00:00:00Z",
    )
    db.upsert_repo(repo)
    # 70 stars in the last 7 days, 23 more across days 7..29 => 93 in 30 days.
    seed_daily(db, repo.id, {offset: 10 for offset in range(7)})
    seed_daily(db, repo.id, {offset: 1 for offset in range(7, 30)})

    row = trends.compute_trend_row(db, repo, today=TODAY)

    assert row.gains[1] == 10
    assert row.gains[7] == 70
    assert row.gains[30] == 93
    assert row.relative_growth == pytest.approx(7.53)
    assert row.acceleration == pytest.approx(3.226)
    assert row.is_new is True


def test_compute_trend_row_without_data_has_no_derived_metrics(db):
    repo = make_repo(11, "acme/quiet", stars=1000)
    db.upsert_repo(repo)

    row = trends.compute_trend_row(db, repo, today=TODAY)

    assert row.gains == {1: 0, 7: 0, 30: 0, 90: 0, 365: 0}
    assert row.relative_growth is None
    assert row.acceleration is None
    assert row.is_new is False


# --------------------------------------------------------------------- sorts
def test_get_trending_most_gained_and_stars(db):
    slow = make_repo(20, "acme/slow", stars=9000)
    fast = make_repo(21, "acme/fast", stars=1000)
    starful = make_repo(22, "acme/starful", stars=20000)
    for repo in (slow, fast, starful):
        db.upsert_repo(repo)
    seed_week(db, slow.id, 10)
    seed_week(db, fast.id, 70)

    gained = trends.get_trending(db, window=7, sort="most_gained", today=TODAY)
    assert [r.repo.id for r in gained] == [fast.id, slow.id, starful.id]

    by_stars = trends.get_trending(db, window=7, sort="stars", today=TODAY)
    assert [r.repo.id for r in by_stars] == [starful.id, slow.id, fast.id]


def test_get_trending_fastest_growth_puts_none_last(db):
    small = make_repo(30, "acme/small", stars=100)
    big = make_repo(31, "acme/big", stars=10000)
    nodata = make_repo(32, "acme/nodata", stars=500)
    for repo in (small, big, nodata):
        db.upsert_repo(repo)
    seed_week(db, small.id, 10)   # 10 / 90  => 11.11%
    seed_week(db, big.id, 100)    # 100 / 9900 => 1.01%

    rows = trends.get_trending(db, window=7, sort="fastest_growth", today=TODAY)
    assert [r.repo.id for r in rows] == [small.id, big.id, nodata.id]
    assert rows[-1].relative_growth is None


def test_get_trending_accelerating(db):
    accel = make_repo(40, "acme/accel", stars=1000)
    steady = make_repo(41, "acme/steady", stars=1000)
    nodata = make_repo(42, "acme/nodata", stars=1000)
    for repo in (accel, steady, nodata):
        db.upsert_repo(repo)

    seed_daily(db, accel.id, {offset: 10 for offset in range(7)})
    seed_daily(db, accel.id, {offset: 1 for offset in range(7, 30)})
    seed_daily(db, steady.id, {offset: 1 for offset in range(30)})

    rows = trends.get_trending(db, window=7, sort="accelerating", today=TODAY)
    assert [r.repo.id for r in rows] == [accel.id, steady.id, nodata.id]
    assert rows[0].acceleration == pytest.approx(3.226)
    assert rows[1].acceleration == pytest.approx(1.0)


def test_get_trending_new_rising(db):
    new = make_repo(
        50, "acme/new", stars=100, created_at=(TODAY - timedelta(days=20)).isoformat()
    )
    newer = make_repo(
        51, "acme/newer", stars=100, created_at=(TODAY - timedelta(days=5)).isoformat()
    )
    old = make_repo(
        52, "acme/old", stars=100, created_at=(TODAY - timedelta(days=200)).isoformat()
    )
    for repo in (new, newer, old):
        db.upsert_repo(repo)
    seed_week(db, new.id, 20)
    seed_week(db, newer.id, 5)
    seed_week(db, old.id, 100)

    rows = trends.get_trending(db, window=7, sort="new_rising", today=TODAY)
    assert [r.repo.id for r in rows] == [new.id, newer.id]


def test_get_trending_updated(db):
    older = make_repo(60, "acme/older", stars=100, pushed_at="2026-01-01T00:00:00Z")
    newer = make_repo(61, "acme/newer", stars=100, pushed_at="2026-11-20T00:00:00Z")
    never = make_repo(62, "acme/never", stars=100, pushed_at=None)
    for repo in (older, newer, never):
        db.upsert_repo(repo)

    rows = trends.get_trending(db, window=7, sort="updated", today=TODAY)
    assert [r.repo.id for r in rows] == [newer.id, older.id, never.id]


def test_get_trending_rejects_bad_sort_and_window(db):
    with pytest.raises(ValueError):
        trends.get_trending(db, sort="sideways", today=TODAY)
    with pytest.raises(ValueError):
        trends.get_trending(db, window=3, today=TODAY)


# ------------------------------------------------------------------ filtering
def test_candidate_and_trending_filters(db):
    normal = make_repo(70, "acme/normal", stars=100)
    archived = make_repo(71, "acme/archived", stars=100, archived=True)
    fork = make_repo(72, "acme/fork", stars=100, fork=True)
    tiny = make_repo(73, "acme/tiny", stars=5)
    gopher = make_repo(74, "acme/gopher", stars=100, language="Go", license="Apache-2.0")
    for repo in (normal, archived, fork, tiny, gopher):
        db.upsert_repo(repo)

    candidates = trends.candidate_repos(db, min_stars=50)
    assert {r.id for r in candidates} == {normal.id, gopher.id}

    python = trends.get_trending(db, language="Python", min_stars=50, today=TODAY)
    assert {r.repo.id for r in python} == {normal.id}

    mit = trends.get_trending(db, min_stars=50, license="mit", today=TODAY)
    assert {r.repo.id for r in mit} == {normal.id}

    with_archived = trends.candidate_repos(db, min_stars=50, include_archived=True)
    assert archived.id in {r.id for r in with_archived}

    with_forks = trends.candidate_repos(db, min_stars=50, include_forks=True)
    assert fork.id in {r.id for r in with_forks}


# ------------------------------------------------------- backfill / snapshots
class FakeBackfillClient:
    def __init__(self, *, fail_ids: set[int] | None = None):
        self.fail_ids = fail_ids or set()
        self.calls: list[tuple[int, int, date]] = []

    def star_history(self, repo_id: int, *, weeks_back: int = 53, today=None):
        self.calls.append((repo_id, weeks_back, today))
        if repo_id in self.fail_ids:
            raise RuntimeError("boom")
        return [
            StarDay(today - timedelta(days=1), 3),
            StarDay(today, 5),
        ]


def test_backfill_skips_ineligible_and_reports_progress(db):
    good = make_repo(80, "acme/good", stars=100)
    tiny = make_repo(81, "acme/tiny", stars=10)
    archived = make_repo(82, "acme/archived", stars=100, archived=True)
    fork = make_repo(83, "acme/fork", stars=100, fork=True)
    for repo in (good, tiny, archived, fork):
        db.upsert_repo(repo)

    client = FakeBackfillClient()
    progress_calls: list[tuple[int, int]] = []

    result = trends.backfill_star_history(
        db,
        client,
        [good.id, tiny.id, archived.id, fork.id, 9999],
        min_stars=50,
        today=TODAY,
        progress=lambda done, total: progress_calls.append((done, total)),
    )

    assert result == {
        "requested": 5,
        "fetched": 1,
        "skipped": 4,
        "days_stored": 2,
        "errors": 0,
    }
    assert [call[0] for call in client.calls] == [good.id]
    assert progress_calls == [(1, 1)]
    assert db.sum_star_days(good.id, 7, TODAY) == (2, 8)


def test_backfill_counts_errors_and_keeps_going(db):
    first = make_repo(84, "acme/first", stars=100)
    second = make_repo(85, "acme/second", stars=100)
    db.upsert_repo(first)
    db.upsert_repo(second)

    client = FakeBackfillClient(fail_ids={first.id})
    progress_calls: list[tuple[int, int]] = []

    result = trends.backfill_star_history(
        db,
        client,
        [first.id, second.id],
        today=TODAY,
        progress=lambda done, total: progress_calls.append((done, total)),
    )

    assert result["requested"] == 2
    assert result["fetched"] == 1
    assert result["errors"] == 1
    assert result["days_stored"] == 2
    assert progress_calls == [(1, 2), (2, 2)]


class FakeSnapshotClient:
    def __init__(self, repos: dict[str, Repo]):
        self.repos = repos
        self.chunks: list[list[str]] = []

    def repo_stats(self, full_names):
        names = list(full_names)
        self.chunks.append(names)
        return [self.repos[name] for name in names if name in self.repos]


def test_take_snapshots_batches_and_stores(db):
    repos: dict[str, Repo] = {}
    for index in range(105):
        repo = make_repo(1000 + index, f"acme/repo{index}", stars=100 + index)
        db.upsert_repo(repo)
        repos[repo.full_name] = Repo(
            id=repo.id,
            full_name=repo.full_name,
            url=repo.url,
            stars=repo.stars + 1,
            forks=repo.forks + 2,
        )

    client = FakeSnapshotClient(repos)
    stored = trends.take_snapshots(db, client, today=TODAY)

    assert stored == 105
    assert [len(chunk) for chunk in client.chunks] == [100, 5]
    assert db.snapshot_count(1000) == 1
    assert db.snapshot_gain(1000, 0, TODAY) is not None
    with db.connect() as conn:
        row = conn.execute("SELECT stars, forks FROM snapshots WHERE repo_id=?", (1000,)).fetchone()
    assert (row["stars"], row["forks"]) == (101, 12)


def test_take_snapshots_ignores_missing_repos_and_duplicates(db):
    repo = make_repo(1100, "acme/dupe", stars=100)
    db.upsert_repo(repo)

    # Client knows the repo but not the missing id, which simply returns nothing.
    client = FakeSnapshotClient({repo.full_name: repo})
    stored = trends.take_snapshots(db, client, [repo.id, repo.id, 424242], today=TODAY)

    assert stored == 1
    assert client.chunks == [[repo.full_name]]


# ---------------------------------------------------------------- discovery
class FakeHintsClient:
    def __init__(self, result, repos: dict[str, Repo] | None = None, *, raises: bool = False):
        self.result = result
        self.repos = repos or {}
        self.raises = raises
        self.requested: list[list[str]] = []
        self.period = None
        self.language = None

    def oss_insight_trends(self, period="past_week", language=None):
        if self.raises:
            raise RuntimeError("oss insight down")
        self.period = period
        self.language = language
        return self.result

    def repo_stats(self, full_names):
        names = list(full_names)
        self.requested.append(names)
        return [self.repos[name] for name in names if name in self.repos]


def test_discover_hints_returns_empty_when_unavailable(db):
    client = FakeHintsClient(OssInsightResult(rows=[], available=False))
    assert trends.discover_hints(client, db, today=TODAY) == []
    assert client.requested == []


def test_discover_hints_catches_network_errors(db):
    client = FakeHintsClient(OssInsightResult(), raises=True)
    assert trends.discover_hints(client, db, today=TODAY) == []


def test_discover_hints_parses_names_and_tags_hint(db):
    repos = {
        "acme/one": make_repo(1200, "acme/one", stars=500),
        "acme/two": make_repo(1201, "acme/two", stars=600),
        "acme/three": make_repo(1202, "acme/three", stars=700),
    }
    result = OssInsightResult(
        available=True,
        rows=[
            {"repo_name": "acme/one"},
            {"full_name": "acme/two"},
            {"name": "acme/three"},
            {"name": "not-a-full-name"},
            {"repo_name": "acme/one"},
        ],
    )
    client = FakeHintsClient(result, repos)

    hints = trends.discover_hints(client, db, language="Python", today=TODAY)

    assert client.period == "past_week"
    assert client.language == "Python"
    assert client.requested == [["acme/one", "acme/two", "acme/three"]]
    assert {repo.id for repo in hints} == {1200, 1201, 1202}
    for name in repos:
        stored = db.get_repo(name)
        assert stored is not None
        with db.connect() as conn:
            keywords = {
                row["keyword"]
                for row in conn.execute(
                    "SELECT keyword FROM repo_keywords WHERE repo_id=?", (stored.id,)
                )
            }
        assert "hint" in keywords


# --------------------------------------------------------------- star_series
def test_star_series_cumulative_math(db):
    repo = make_repo(1300, "acme/series", stars=1000)
    db.upsert_repo(repo)
    seed_daily(db, repo.id, {2: 5, 1: 7, 0: 8})

    series = trends.star_series(db, repo.id, days=3, today=TODAY)

    assert series == [
        ((TODAY - timedelta(days=2)).isoformat(), 985),
        ((TODAY - timedelta(days=1)).isoformat(), 992),
        (TODAY.isoformat(), 1000),
    ]


def test_star_series_empty_falls_back_to_current_stars(db):
    repo = make_repo(1301, "acme/plain", stars=500)
    db.upsert_repo(repo)

    assert trends.star_series(db, repo.id, days=90, today=TODAY) == [
        (TODAY.isoformat(), 500)
    ]
    assert trends.star_series(db, 999999, days=90, today=TODAY) == []


def test_star_series_fills_gaps_and_clamps_at_zero(db):
    repo = make_repo(1302, "acme/clamp", stars=10)
    db.upsert_repo(repo)
    seed_daily(db, repo.id, {0: 50})

    series = trends.star_series(db, repo.id, days=3, today=TODAY)

    assert len(series) == 3
    assert all(value >= 0 for _day, value in series)
    assert series[-1] == (TODAY.isoformat(), 10)
