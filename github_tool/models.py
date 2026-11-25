"""Domain models shared by the client, store, and UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any


def parse_datetime(value: str | None) -> str | None:
    """Normalise GitHub ISO timestamps to UTC ISO strings, or None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


@dataclass
class RateLimit:
    limit: int | None = None
    remaining: int | None = None
    reset: int | None = None
    resource: str | None = None

    @classmethod
    def from_headers(cls, headers: Any) -> "RateLimit":
        def _int(name: str) -> int | None:
            raw = headers.get(name) if headers else None
            try:
                return int(raw) if raw is not None else None
            except (TypeError, ValueError):
                return None

        return cls(
            limit=_int("X-RateLimit-Limit"),
            remaining=_int("X-RateLimit-Remaining"),
            reset=_int("X-RateLimit-Reset"),
            resource=headers.get("X-RateLimit-Resource") if headers else None,
        )


@dataclass
class Repo:
    id: int
    full_name: str
    url: str
    description: str | None = None
    language: str | None = None
    topics: list[str] = field(default_factory=list)
    created_at: str | None = None
    pushed_at: str | None = None
    updated_at: str | None = None
    archived: bool = False
    fork: bool = False
    stars: int = 0
    forks: int = 0
    license: str | None = None
    homepage: str | None = None
    default_branch: str | None = None
    readme_text: str | None = None
    readme_etag: str | None = None
    readme_hash: str | None = None
    fetched_at: str | None = None

    @classmethod
    def from_rest(cls, item: dict[str, Any]) -> "Repo":
        license_info = item.get("license") or {}
        return cls(
            id=int(item["id"]),
            full_name=item["full_name"],
            url=item.get("html_url") or f"https://github.com/{item['full_name']}",
            description=item.get("description"),
            language=item.get("language"),
            topics=list(item.get("topics") or []),
            created_at=parse_datetime(item.get("created_at")),
            pushed_at=parse_datetime(item.get("pushed_at")),
            updated_at=parse_datetime(item.get("updated_at")),
            archived=bool(item.get("archived", False)),
            fork=bool(item.get("fork", False)),
            stars=int(item.get("stargazers_count") or 0),
            forks=int(item.get("forks_count") or 0),
            license=license_info.get("spdx_id") or license_info.get("name"),
            homepage=item.get("homepage"),
            default_branch=item.get("default_branch"),
        )

    @classmethod
    def from_graphql(cls, node: dict[str, Any]) -> "Repo":
        language = node.get("primaryLanguage") or {}
        license_info = node.get("licenseInfo") or {}
        return cls(
            id=int(node.get("databaseId") or 0) or _graphql_id_to_int(node.get("id", "")),
            full_name=node["nameWithOwner"],
            url=node.get("url") or f"https://github.com/{node['nameWithOwner']}",
            description=node.get("description"),
            language=language.get("name") if isinstance(language, dict) else None,
            topics=[t["topic"]["name"] if isinstance(t, dict) else str(t) for t in (node.get("repositoryTopics", {}) or {}).get("nodes", [])],
            created_at=parse_datetime(node.get("createdAt")),
            pushed_at=parse_datetime(node.get("pushedAt")),
            updated_at=parse_datetime(node.get("updatedAt")),
            archived=bool(node.get("isArchived", False)),
            fork=bool(node.get("isFork", False)),
            stars=int(node.get("stargazerCount") or 0),
            forks=int(node.get("forkCount") or 0),
            license=license_info.get("spdxId") or license_info.get("name"),
            homepage=node.get("homepageUrl"),
            default_branch=node.get("defaultBranchRef", {}).get("name") if node.get("defaultBranchRef") else None,
        )


def _graphql_id_to_int(node_id: str) -> int:
    """GraphQL node ids are base64("R_kgDO..."); parse the numeric suffix.

    Search results normally include ``databaseId``; this is only a fallback
    used by fixtures that omit it.
    """
    import base64

    try:
        decoded = base64.b64decode(node_id + "===").decode("utf-8", "ignore")
    except Exception:
        return 0
    digits = "".join(ch for ch in decoded if ch.isdigit())
    return int(digits) if digits else 0


@dataclass
class SearchPage:
    items: list[Repo]
    total_count: int
    rate_limit: RateLimit = field(default_factory=RateLimit)
    etag: str | None = None
    from_cache: bool = False


@dataclass
class ReadmeResult:
    text: str | None
    etag: str | None = None
    not_modified: bool = False
    rate_limit: RateLimit = field(default_factory=RateLimit)


@dataclass
class StarDay:
    day: date
    gained: int


# Longer comparison window used to compute acceleration for a given window.
_ACCELERATION_BASELINES: dict[int, int] = {1: 7, 7: 30, 30: 90, 90: 365}


@dataclass
class TrendRow:
    repo: Repo
    gains: dict[int, int]
    relative_growth: float | None
    acceleration: float | None
    is_new: bool
    # Whether each window is backed by a complete history. ``None`` means the
    # caller did not track completeness (e.g. a hand-built row); in that case
    # any window present in ``gains`` is assumed complete.
    has_data: dict[int, bool] | None = None

    def gain(self, window: int) -> int:
        return self.gains.get(window, 0)

    def _complete(self, window: int) -> bool:
        if self.has_data is None:
            return window in self.gains
        return self.has_data.get(window, False)

    def relative_growth_for(self, window: int) -> float | None:
        """Relative growth for an arbitrary, fully covered window."""
        if not self._complete(window):
            return None
        if window == 7:
            return self.relative_growth
        gain = self.gain(window)
        if gain <= 0:
            return 0.0
        return round(gain / max(self.repo.stars - gain, 1) * 100, 2)

    def acceleration_for(self, window: int) -> float | None:
        """Recent daily gain vs the next longer standard window's daily gain.

        ``7`` compares against 30 days (the historical definition). Windows
        without a longer baseline, or with incomplete history, have no
        acceleration and return ``None``.
        """
        baseline = _ACCELERATION_BASELINES.get(window)
        if (
            baseline is None
            or not self._complete(window)
            or not self._complete(baseline)
            or self.gain(baseline) <= 0
        ):
            return None
        return round((self.gain(window) / window) / (self.gain(baseline) / baseline), 3)
