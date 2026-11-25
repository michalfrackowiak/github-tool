"""Trend engine: star-history backfill, snapshots, gains, and rankings.

The star-history endpoint gives exact daily gains but is young; own snapshots
are the fallback.  Every ranking is computed from those two local sources, so
trend views work offline once data has been collected.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Callable, Sequence

from .github import OssInsightResult
from .models import Repo, StarDay, TrendRow, parse_datetime, utc_today


WINDOWS_DAYS: tuple[int, ...] = (1, 7, 30, 90, 365)

SORTS = (
    "most_gained",
    "fastest_growth",
    "accelerating",
    "new_rising",
    "stars",
    "updated",
)

_UNBOUNDED = 1_000_000


def _today(today: date | None) -> date:
    return today or utc_today()


def _parse_date(value: str | None) -> date | None:
    """Parse an ISO timestamp (or date) to a UTC date, returning None safely."""
    if not value:
        return None
    normalised = parse_datetime(value)
    if not normalised:
        return None
    try:
        return datetime.fromisoformat(normalised.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(normalised[:10])
        except ValueError:
            return None


def _candidates(
    db,
    *,
    min_stars: int = 50,
    include_archived: bool = False,
    include_forks: bool = False,
    language: str | None = None,
    license: str | None = None,
    limit: int | None = None,
    max_fork_ratio: float | None = None,
) -> list[Repo]:
    repos = db.list_repos(
        language=language,
        min_stars=min_stars,
        limit=limit if limit is not None else _UNBOUNDED,
        include_archived=include_archived,
        include_forks=include_forks,
    )
    if license:
        wanted = license.strip().lower()
        repos = [r for r in repos if (r.license or "").strip().lower() == wanted]
    if max_fork_ratio is not None:
        repos = [
            r for r in repos
            if r.forks / max(r.stars, 1) <= max_fork_ratio
        ]
    return repos


def candidate_repos(
    db,
    *,
    min_stars: int = 50,
    include_archived: bool = False,
    include_forks: bool = False,
    limit: int | None = None,
) -> list[Repo]:
    """Eligible repos for trend collection, newest-star order."""
    return _candidates(
        db,
        min_stars=min_stars,
        include_archived=include_archived,
        include_forks=include_forks,
        limit=limit,
    )


def _ineligible(repo: Repo | None, min_stars: int) -> bool:
    return (
        repo is None
        or repo.archived
        or repo.fork
        or repo.stars < min_stars
    )


def backfill_star_history(
    db,
    client,
    repo_ids: Sequence[int] | None = None,
    *,
    weeks_back: int = 53,
    min_stars: int = 50,
    today: date | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, int]:
    """Fetch daily star gains for candidates and store them.

    Explicit ``repo_ids`` are still filtered: archived repos, forks, and repos
    below ``min_stars`` are skipped.  A per-repo API failure is counted and does
    not stop the run.  ``progress(done, total)`` is called after every eligible
    repo, where ``total`` is the number of eligible repos.
    """
    today = _today(today)

    if repo_ids is not None:
        requested_repos: list[Repo | None] = [db.get_repo(rid) for rid in repo_ids]
    else:
        requested_repos = list(candidate_repos(db, min_stars=min_stars))

    requested = len(requested_repos)
    eligible = [r for r in requested_repos if not _ineligible(r, min_stars)]
    skipped = requested - len(eligible)

    result = {
        "requested": requested,
        "fetched": 0,
        "skipped": skipped,
        "days_stored": 0,
        "errors": 0,
    }

    total = len(eligible)
    for done, repo in enumerate(eligible, start=1):
        assert repo is not None
        try:
            days: list[StarDay] = client.star_history(
                repo.id, weeks_back=weeks_back, today=today
            )
            db.save_star_days(repo.id, days)
            result["fetched"] += 1
            result["days_stored"] += len(days)
        except Exception:  # noqa: BLE001 - keep the backfill going
            result["errors"] += 1
        if progress is not None:
            progress(done, total)

    return result


def take_snapshots(
    db,
    client,
    repo_ids: Sequence[int] | None = None,
    *,
    today: date | None = None,
    batch_size: int = 100,
) -> int:
    """Store today's stars/forks for candidates via batched GraphQL calls."""
    today = _today(today)

    if repo_ids is not None:
        repos = [db.get_repo(rid) for rid in repo_ids]
    else:
        repos = list(candidate_repos(db))

    full_names: list[str] = []
    seen: set[str] = set()
    for repo in repos:
        if repo is None:
            continue
        if repo.full_name not in seen:
            seen.add(repo.full_name)
            full_names.append(repo.full_name)

    stored = 0
    size = max(1, min(batch_size, 100))
    for start in range(0, len(full_names), size):
        chunk = full_names[start : start + size]
        for repo in client.repo_stats(chunk):
            db.save_snapshot(repo.id, repo.stars, repo.forks, today)
            stored += 1
    return stored


def star_gain(
    db,
    repo_id: int,
    days: int,
    *,
    today: date | None = None,
    created: date | None = None,
) -> tuple[int, bool]:
    """Star gain over ``days`` plus whether the window is fully covered.

    A single stored day must not be presented as a seven-day gain, so daily
    data is trusted only when it reaches the start of the window (or the repo
    was created inside the window, in which case all of its history fits).
    """
    today = _today(today)

    rows, total = db.sum_star_days(repo_id, days, today)
    if rows > 0:
        first, _ = db.star_day_bounds(repo_id, days, today)
        start = today - timedelta(days=max(days - 1, 0))
        complete = first is not None and (
            first <= start + timedelta(days=2) or (created is not None and created >= start)
        )
        if complete:
            return total, True
        # Partial daily history still shows the observed gain, but it is not
        # treated as a complete window (no relative growth / acceleration).
        snapped = db.snapshot_gain(repo_id, days, today)
        if snapped is not None:
            return snapped, True
        return total, False

    gain = db.snapshot_gain(repo_id, days, today)
    if gain is None:
        return 0, False
    return gain, True


def compute_trend_row(
    db,
    repo: Repo,
    *,
    today: date | None = None,
    windows: dict[int, tuple[int, bool]] | None = None,
) -> TrendRow:
    """Compute all window gains and derived metrics for one repo.

    ``windows`` may be supplied by a bulk query so a ranked view can avoid
    opening one database connection per candidate repo.
    """
    today = _today(today)
    created = _parse_date(repo.created_at)

    gains: dict[int, int] = {}
    has_data: dict[int, bool] = {}
    windows = (
        windows if windows is not None
        else db.trend_windows(repo.id, WINDOWS_DAYS, today, created)
    )
    for window in WINDOWS_DAYS:
        gains[window], has_data[window] = windows[window]

    if has_data[7]:
        relative_growth = round(
            gains[7] / max(repo.stars - gains[7], 1) * 100, 2
        )
    else:
        relative_growth = None

    if has_data[7] and has_data[30] and gains[30] > 0:
        acceleration = round((gains[7] / 7) / (gains[30] / 30), 3)
    else:
        acceleration = None

    is_new = False
    if created is not None:
        age = (today - created).days
        is_new = 0 <= age <= 90

    return TrendRow(
        repo=repo,
        gains=gains,
        relative_growth=relative_growth,
        acceleration=acceleration,
        is_new=is_new,
        has_data=has_data,
    )


def _sorted_rows(rows: list[TrendRow], sort: str, window: int) -> list[TrendRow]:
    if sort == "most_gained":
        return sorted(
            rows,
            key=lambda r: (r.gain(window), r.repo.stars),
            reverse=True,
        )
    if sort == "fastest_growth":
        return sorted(
            rows,
            key=lambda r: (
                r.relative_growth_for(window) is not None,
                r.relative_growth_for(window) or 0,
                r.gain(window),
            ),
            reverse=True,
        )
    if sort == "accelerating":
        return sorted(
            rows,
            key=lambda r: (
                r.acceleration_for(window) is not None,
                r.acceleration_for(window) or 0,
            ),
            reverse=True,
        )
    if sort == "new_rising":
        rising = [r for r in rows if r.is_new]
        return sorted(
            rising,
            key=lambda r: (
                r.gain(window),
                r.relative_growth_for(window) is not None,
                r.relative_growth_for(window) or 0,
            ),
            reverse=True,
        )
    if sort == "stars":
        return sorted(rows, key=lambda r: r.repo.stars, reverse=True)
    if sort == "updated":
        return sorted(
            rows,
            key=lambda r: (
                r.repo.pushed_at is not None,
                parse_datetime(r.repo.pushed_at) or "",
            ),
            reverse=True,
        )
    raise ValueError(f"Unknown trend sort: {sort!r}")


def get_trending(
    db,
    *,
    window: int = 7,
    sort: str = "most_gained",
    language: str | None = None,
    min_stars: int = 50,
    license: str | None = None,
    include_archived: bool = False,
    include_forks: bool = False,
    limit: int | None = 50,
    today: date | None = None,
    max_fork_ratio: float | None = None,
    active_within_days: int | None = None,
) -> list[TrendRow]:
    """Rank candidate repos by recent star activity."""
    if window not in WINDOWS_DAYS:
        raise ValueError(f"window must be one of {WINDOWS_DAYS}, got {window!r}")
    if sort not in SORTS:
        raise ValueError(f"sort must be one of {SORTS}, got {sort!r}")
    if max_fork_ratio is not None and (
        not math.isfinite(max_fork_ratio) or max_fork_ratio < 0
    ):
        raise ValueError("max_fork_ratio must be a finite non-negative number")
    if active_within_days is not None and active_within_days < 0:
        raise ValueError("active_within_days must be non-negative")

    today = _today(today)
    repos = _candidates(
        db,
        min_stars=min_stars,
        include_archived=include_archived,
        include_forks=include_forks,
        language=language,
        license=license,
        max_fork_ratio=max_fork_ratio,
    )
    if active_within_days is not None:
        cutoff = today - timedelta(days=active_within_days)
        repos = [
            r for r in repos
            if (pushed := _parse_date(r.pushed_at)) is not None and pushed >= cutoff
        ]
    by_id = db.bulk_trend_windows(
        [r.id for r in repos],
        WINDOWS_DAYS,
        today,
        {r.id: _parse_date(r.created_at) for r in repos},
    )
    rows = [
        compute_trend_row(db, repo, today=today, windows=by_id.get(repo.id))
        for repo in repos
    ]
    rows = _sorted_rows(rows, sort, window)
    if limit is not None:
        rows = rows[:limit]
    return rows


def discover_hints(
    client,
    db,
    *,
    language: str | None = None,
    period: str = "past_week",
    today: date | None = None,
    source: str = "all",
) -> list[Repo]:
    """Pull discovery hints from OSS Insight and/or GitHub Trending.

    Both sources are third-party hints, never ranked results: OSS Insight has a
    graceful unavailability mode, and GitHub Trending has no stable API so its
    HTML is parsed. Any failure yields an empty contribution rather than an
    exception, so discovery can never break the caller.
    """
    if source not in {"all", "oss", "trending"}:
        raise ValueError(f"Unknown hint source: {source!r}")
    names: list[str] = []
    seen: set[str] = set()

    def collect(values: list[str]) -> None:
        for value in values:
            name = value.strip()
            if "/" in name and name not in seen:
                seen.add(name)
                names.append(name)

    if source in {"all", "oss"}:
        try:
            result: OssInsightResult = client.oss_insight_trends(
                period=period, language=language
            )
            if result and result.available:
                for row in result.rows:
                    if not isinstance(row, dict):
                        continue
                    for key in ("repo_name", "full_name", "name"):
                        value = row.get(key)
                        if isinstance(value, str) and "/" in value:
                            collect([value])
                            break
        except Exception:  # noqa: BLE001 - OSS Insight must never break the caller
            pass

    if source in {"all", "trending"}:
        try:
            trending_period = {
                "past_24_hours": "daily",
                "past_week": "weekly",
                "past_month": "monthly",
                "past_3_months": "monthly",
            }.get(period, "weekly")
            collect(client.github_trending_repos(language, trending_period))
        except Exception:  # noqa: BLE001 - HTML layout may change; stay graceful
            pass

    hints: list[Repo] = []
    for start in range(0, len(names), 100):
        try:
            batch = client.repo_stats(names[start : start + 100])
        except Exception:  # noqa: BLE001 - discovery must never break the caller
            break
        for repo in batch or []:
            db.upsert_repo(repo, keyword="hint")
            hints.append(repo)
    return hints


def star_series(
    db, repo_id: int, *, days: int = 90, today: date | None = None
) -> list[tuple[str, int]]:
    """Cumulative star series for a sparkline (display-only).

    Walks backwards from the repo's current star count, subtracting gains that
    happened after each day, then forwards again.  Gaps are treated as zero
    gain.  Values never go below zero.
    """
    today = _today(today)
    if days <= 0:
        return []

    repo = db.get_repo(repo_id)
    if repo is None:
        return []

    start = today - timedelta(days=days - 1)
    daily = db.get_star_days(repo_id, since=start, until=today)
    if not daily:
        snapshots = db.get_snapshots(repo_id, since=start, until=today)
        if snapshots:
            return [(str(row["day"]), int(row["stars"])) for row in snapshots]
        return [(today.isoformat(), repo.stars)]

    gains = {point.day: point.gained for point in daily}
    value = repo.stars - sum(gains.values())

    series: list[tuple[str, int]] = []
    current = start
    while current <= today:
        value += gains.get(current, 0)
        series.append((current.isoformat(), max(0, value)))
        current += timedelta(days=1)
    return series
