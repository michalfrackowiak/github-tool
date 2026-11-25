"""Phase 1: link-out views that need no token and no database.

Every helper returns a plain URL so it can be tested without a browser.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import quote, urlencode

from .keywords import Keyword, WINDOW_DAYS, WINDOW_LABELS, get_keyword
from .models import utc_today


GITHUB_SEARCH = "https://github.com/search"
GITHUB_TRENDING = "https://github.com/trending"
GITHUB_TOPICS = "https://github.com/topics"
OSS_INSIGHT_API = "https://api.ossinsight.io/v1/trends/repos/"

# Link-out windows supported by the third-party views.
TRENDING_WINDOWS = {"today": "daily", "7d": "weekly", "30d": "monthly"}
OSS_INSIGHT_PERIODS = {
    "today": "past_24_hours",
    "7d": "past_week",
    "30d": "past_month",
    "90d": "past_3_months",
}

# Live validation on 2026-11-24: the OSS Insight trends endpoint answers 200
# but reports its event-derived ranking as unavailable since 2026-03-01.
OSS_INSIGHT_TRENDING_AVAILABLE = False


@dataclass(frozen=True)
class ViewLink:
    id: str
    label: str
    url: str
    kind: str
    note: str = ""
    available: bool = True


def _date_threshold(window: str, today: date | None = None) -> date:
    days = WINDOW_DAYS.get(window)
    if days is None:
        raise ValueError(f"Unknown window: {window!r}")
    return (today or utc_today()) - timedelta(days=days)


def github_search_url(
    query: str,
    language: str | None = None,
    window: str = "30d",
    sort: str = "stars",
    order: str = "desc",
    today: date | None = None,
) -> str:
    """Build a github.com search URL.

    Up to 90 days we filter on ``pushed:`` (active repos), which is the closest
    link-only proxy for "trending". For a year we fall back to ``created:`` as
    required by the roadmap, because pushed-within-a-year is nearly all repos.
    """
    if window not in WINDOW_DAYS:
        raise ValueError(f"Unknown window: {window!r}")
    cutoff = _date_threshold(window, today)
    qualifier = "created" if window == "365d" else "pushed"
    q = f"{query} {qualifier}:>={cutoff.isoformat()}"
    if language:
        q = f"{q} language:{language}"
    params = urlencode({"q": q, "type": "repositories", "s": sort, "o": order})
    return f"{GITHUB_SEARCH}?{params}"


def trending_url(language: str | None = None, window: str = "7d") -> str | None:
    since = TRENDING_WINDOWS.get(window)
    if since is None:
        return None
    path = f"/{quote(language.lower())}" if language else ""
    return f"{GITHUB_TRENDING}{path}?{urlencode({'since': since})}"


def oss_insight_url(language: str | None = None, window: str = "7d") -> str | None:
    period = OSS_INSIGHT_PERIODS.get(window)
    if period is None:
        return None
    params = {"period": period}
    if language:
        params["language"] = language
    return f"{OSS_INSIGHT_API}?{urlencode(params)}"


def topic_url(topic: str, language: str | None = None) -> str:
    url = f"{GITHUB_TOPICS}/{quote(topic)}"
    if language:
        url = f"{url}?{urlencode({'l': language.lower()})}"
    return url


def generate_links(
    keyword: str | Keyword,
    language: str | None = None,
    window: str = "30d",
    today: date | None = None,
) -> list[ViewLink]:
    kw = get_keyword(keyword) if isinstance(keyword, str) else keyword
    if window not in WINDOW_DAYS:
        raise ValueError(f"Unknown window: {window!r}")
    label = WINDOW_LABELS[window]
    query = kw.variants()[0]
    views = [
        ViewLink(
            "github-search",
            f"GitHub search · stars · {label}",
            github_search_url(query, language, window, today=today),
            "search",
            "Ranks by total stars, filtered to recently active repos."
            if window != "365d"
            else "Last-year fallback: repos created in the last year.",
        )
    ]

    trending = trending_url(language, window)
    if trending:
        views.append(
            ViewLink(
                "github-trending",
                f"GitHub Trending · {TRENDING_WINDOWS[window]}",
                trending,
                "trending",
                "No keyword filter; Trending is a language-level list.",
            )
        )

    oss = oss_insight_url(language, window)
    if oss:
        views.append(
            ViewLink(
                "oss-insight",
                f"OSS Insight · {label}",
                oss,
                "third-party",
                "Third-party beta. Live check on 2026-11-24 returned no ranking data.",
                available=OSS_INSIGHT_TRENDING_AVAILABLE,
            )
        )

    if kw.topic:
        views.append(
            ViewLink(
                "github-topic",
                f"GitHub topic · {kw.topic}",
                topic_url(kw.topic, language),
                "topic",
                "Tag-based; useful for curated lists, not ranked by growth.",
            )
        )

    if window == "365d":
        views.append(
            ViewLink(
                "github-search-created",
                f"GitHub search · created in the last year · {kw.name}",
                github_search_url(query, language, "365d", today=today),
                "search",
                "Explicit last-year fallback (created: qualifier).",
            )
        )
    return views


def web_search_links(keyword: str, language: str | None = None, window: str = "30d") -> dict[str, str]:
    """Convenience mapping for templates."""
    return {view.id: view.url for view in generate_links(keyword, language, window)}
