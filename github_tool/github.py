"""GitHub API client: token auth, backoff, ETag cache, search, READMEs,
star-history, GraphQL batching, and the OSS Insight adapter.

The client is deliberately synchronous (httpx.Client) so it is easy to drive
from a CLI crawler and from FastAPI handlers without an event loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import re
import time
from typing import Any, Callable, Sequence
from urllib.parse import quote, urlencode

import httpx

from .config import Settings
from .models import RateLimit, ReadmeResult, Repo, SearchPage, StarDay, utc_today


class GitHubError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status = status
        self.url = url


class GitHubNotFound(GitHubError):
    pass


class OfflineError(GitHubError):
    pass


def _retry_after_seconds(value: str, now: float) -> float:
    """Retry-After is either delta-seconds or an HTTP-date (RFC 9110)."""
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        pass
    try:
        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(when.timestamp() - now, 0.0)
    except (TypeError, ValueError, OverflowError):
        return 1.0


@dataclass
class OssInsightResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    available: bool = False
    note: str = ""


def build_search_query(
    base: str,
    language: str | None = None,
    min_stars: int = 0,
    created_after: date | None = None,
    pushed_after: date | None = None,
    stars_range: tuple[int, int | None] | None = None,
) -> str:
    parts = [base]
    if language:
        parts.append(f"language:{language}")
    if min_stars:
        parts.append(f"stars:>={min_stars}")
    if stars_range:
        lo, hi = stars_range
        if hi is None:
            parts.append(f"stars:>={lo}")
        else:
            parts.append(f"stars:{lo}..{hi}")
    if created_after:
        parts.append(f"created:>={created_after.isoformat()}")
    if pushed_after:
        parts.append(f"pushed:>={pushed_after.isoformat()}")
    return " ".join(parts)


class GitHubClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        cache: Any | None = None,
    ):
        self.settings = settings
        self.cache = cache
        self._sleep = sleep
        self._clock = clock
        self._last_search = 0.0
        self.rate_limits: dict[str, RateLimit] = {}
        self._client = httpx.Client(
            transport=transport,
            timeout=settings.request_timeout,
            follow_redirects=True,
        )

    # -------------------------------------------------------------- plumbing
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _headers(self, accept: str = "application/vnd.github+json", extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": self.settings.api_version,
            "User-Agent": self.settings.user_agent,
        }
        if self.settings.token:
            headers["Authorization"] = f"Bearer {self.settings.token}"
        if extra:
            headers.update(extra)
        return headers

    def _track_rate_limit(self, response: httpx.Response) -> RateLimit:
        rl = RateLimit.from_headers(response.headers)
        resource = rl.resource or "core"
        self.rate_limits[resource] = rl
        return rl

    def _raw_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: Any | None = None,
        allow_304: bool = False,
        allow_404: bool = False,
        max_wait: float = 300.0,
    ) -> httpx.Response:
        try:
            self.settings.require_online()
        except RuntimeError as exc:
            raise OfflineError(str(exc)) from exc
        attempt = 0
        while True:
            response = self._client.request(
                method, url, params=params, headers=headers, json=json_body
            )
            rl = self._track_rate_limit(response)
            if response.status_code == 304 and allow_304:
                return response
            if response.status_code == 404 and allow_404:
                return response
            if 200 <= response.status_code < 300:
                return response
            attempt += 1
            if attempt > self.settings.max_retries:
                raise GitHubError(
                    f"GitHub request failed with {response.status_code}",
                    status=response.status_code,
                    url=str(response.request.url),
                )
            if response.status_code in (403, 429):
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    wait = _retry_after_seconds(retry_after, self._clock())
                elif rl.remaining == 0 and rl.reset:
                    wait = max(rl.reset - self._clock() + 1, 1)
                    if wait > max_wait:
                        raise GitHubError(
                            f"GitHub rate limit resets in {int(wait)}s; retry later",
                            status=response.status_code,
                            url=str(response.request.url),
                        )
                else:
                    wait = 2.0 ** attempt
                self._sleep(min(wait, max_wait))
                continue
            if response.status_code >= 500:
                self._sleep(min(2.0 ** attempt, 30.0))
                continue
            raise GitHubError(
                f"GitHub request failed with {response.status_code}: {response.text[:300]}",
                status=response.status_code,
                url=str(response.request.url),
            )

    def _get_json_cached(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        accept: str = "application/vnd.github+json",
    ) -> tuple[Any, str | None, bool, RateLimit]:
        cache_key = url
        if params:
            cache_key = f"{url}?{urlencode(sorted(params.items()))}"
        cached = self.cache.get_http_cache(cache_key) if self.cache is not None else None
        headers = self._headers(accept)
        if cached and cached[0]:
            headers["If-None-Match"] = cached[0]
        response = self._raw_request("GET", url, params=params, headers=headers, allow_304=bool(cached))
        rl = RateLimit.from_headers(response.headers)
        if response.status_code == 304 and cached:
            return json.loads(cached[1]), cached[0], True, rl
        data = response.json()
        etag = response.headers.get("ETag")
        if self.cache is not None and etag:
            self.cache.put_http_cache(cache_key, etag, response.text)
        return data, etag, False, rl

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        data, _etag, _cached, _rl = self._get_json_cached(url, params)
        return data

    def _throttle_search(self) -> None:
        interval = self.settings.search_min_interval
        if interval <= 0:
            self._last_search = self._clock()
            return
        elapsed = self._clock() - self._last_search
        if elapsed < interval:
            self._sleep(interval - elapsed)
        self._last_search = self._clock()

    # ---------------------------------------------------------------- search
    def search_repositories(
        self,
        query: str,
        *,
        sort: str = "stars",
        order: str = "desc",
        per_page: int | None = None,
        page: int = 1,
    ) -> SearchPage:
        self._throttle_search()
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page or self.settings.search_per_page,
            "page": page,
        }
        data, etag, cached, rl = self._get_json_cached(
            f"{self.settings.api_url}/search/repositories", params
        )
        items = [Repo.from_rest(item) for item in data.get("items", [])]
        return SearchPage(
            items=items,
            total_count=int(data.get("total_count") or 0),
            rate_limit=rl,
            etag=etag,
            from_cache=cached,
        )

    def count_search(self, query: str) -> int:
        return self.search_repositories(query, per_page=1).total_count

    # ---------------------------------------------------------------- readmes
    def get_readme(self, full_name: str, etag: str | None = None) -> ReadmeResult:
        headers = self._headers("application/vnd.github.raw+json")
        if etag:
            headers["If-None-Match"] = etag
        response = self._raw_request(
            "GET",
            f"{self.settings.api_url}/repos/{full_name}/readme",
            headers=headers,
            allow_304=True,
            allow_404=True,
        )
        rl = RateLimit.from_headers(response.headers)
        if response.status_code == 304:
            return ReadmeResult(None, etag, not_modified=True, rate_limit=rl)
        if response.status_code == 404:
            return ReadmeResult(None, etag, rate_limit=rl)
        text = response.text
        if len(text) > self.settings.readme_max_bytes:
            text = text[: self.settings.readme_max_bytes]
        return ReadmeResult(text, response.headers.get("ETag"), rate_limit=rl)

    def get_file(self, full_name: str, path: str) -> str | None:
        response = self._raw_request(
            "GET",
            f"{self.settings.api_url}/repos/{full_name}/contents/{path}",
            headers=self._headers("application/vnd.github.raw+json"),
            allow_404=True,
        )
        if response.status_code == 404:
            return None
        return response.text

    def repo_root_files(self, full_name: str) -> list[str]:
        """Names of regular files in a repository root (404 → empty list)."""
        response = self._raw_request(
            "GET",
            f"{self.settings.api_url}/repos/{full_name}/contents/",
            headers=self._headers("application/vnd.github+json"),
            allow_404=True,
        )
        if response.status_code == 404:
            return []
        try:
            entries = response.json()
        except ValueError:
            return []
        if not isinstance(entries, list):
            return []
        return [
            str(entry["name"])
            for entry in entries
            if isinstance(entry, dict) and entry.get("type") == "file" and entry.get("name")
        ]

    # ----------------------------------------------------------- star history
    def star_history(
        self,
        repo_id: int,
        *,
        weeks_back: int = 53,
        today: date | None = None,
        max_pages: int = 8,
    ) -> list[StarDay]:
        """Fetch daily star gains from the star-history endpoint.

        The endpoint returns weekly buckets (a Unix week start plus seven daily
        counts), newest first, 30 weeks per page. A year needs two pages.
        """
        today = today or utc_today()
        cutoff = today - timedelta(weeks=weeks_back)
        by_day: dict[date, int] = {}
        for page in range(1, max_pages + 1):
            data = self._get_json(
                f"{self.settings.api_url}/repositories/{repo_id}/stargazers/history",
                {"per_page": 30, "page": page},
            )
            # Live responses are a bare JSON array; older captures wrapped the
            # same array in {"value": [...], "Count": N}. Support both.
            if isinstance(data, dict):
                weeks = data.get("value") or data.get("items") or []
            else:
                weeks = data or []
            if not weeks:
                break
            oldest: date | None = None
            for week in weeks:
                start_ts = week.get("week")
                if start_ts is None:
                    continue
                start = datetime.fromtimestamp(int(start_ts), tz=timezone.utc).date()
                oldest = start if oldest is None or start < oldest else oldest
                for offset, gained in enumerate(week.get("days") or []):
                    day = start + timedelta(days=offset)
                    if day > today or day < cutoff:
                        continue
                    by_day[day] = int(gained or 0)
            if oldest is not None and oldest < cutoff:
                break
            if len(weeks) < 30:
                break
        return [StarDay(day=d, gained=by_day[d]) for d in sorted(by_day)]

    # ---------------------------------------------------------------- graphql
    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._raw_request(
            "POST",
            self.settings.graphql_url,
            headers=self._headers(),
            json_body={"query": query, "variables": variables or {}},
        )
        payload = response.json()
        if payload.get("errors"):
            raise GitHubError(f"GraphQL error: {payload['errors'][:2]}")
        return payload.get("data") or {}

    def repo_stats(self, full_names: Sequence[str]) -> list[Repo]:
        """Batched GraphQL stats for up to 100 repos (one rate-limit point)."""
        out: list[Repo] = []
        names = list(dict.fromkeys(full_names))
        for i in range(0, len(names), 100):
            chunk = names[i : i + 100]
            var_defs, fields, variables = [], [], {}
            for idx, full_name in enumerate(chunk):
                owner, _, name = full_name.partition("/")
                variables[f"o{idx}"] = owner
                variables[f"n{idx}"] = name
                var_defs.append(f"$o{idx}: String!, $n{idx}: String!")
                fields.append(
                    f'r{idx}: repository(owner: $o{idx}, name: $n{idx}) {{ '
                    "databaseId nameWithOwner url stargazerCount forkCount "
                    "description primaryLanguage { name } createdAt pushedAt updatedAt "
                    "isArchived isFork licenseInfo { spdxId name } homepageUrl "
                    "defaultBranchRef { name } repositoryTopics(first: 20) { nodes { topic { name } } } }"
                )
            query = "query(" + ", ".join(var_defs) + ") {\n" + "\n".join(fields) + "\n}"
            data = self.graphql(query, variables)
            for idx in range(len(chunk)):
                node = data.get(f"r{idx}")
                if node:
                    out.append(Repo.from_graphql(node))
        return out

    def search_graphql(
        self, query: str, *, per_page: int = 100, cursor: str | None = None
    ) -> tuple[list[Repo], int, str | None]:
        gql = """
        query($q: String!, $n: Int!, $cursor: String) {
          search(query: $q, type: REPOSITORY, first: $n, after: $cursor) {
            repositoryCount
            pageInfo { hasNextPage endCursor }
            nodes {
              __typename
              ... on Repository {
                databaseId nameWithOwner url description stargazerCount forkCount
                primaryLanguage { name } createdAt pushedAt updatedAt isArchived isFork
                licenseInfo { spdxId name } homepageUrl defaultBranchRef { name }
                repositoryTopics(first: 20) { nodes { topic { name } } }
              }
            }
          }
        }
        """
        data = self.graphql(gql, {"q": query, "n": min(per_page, 100), "cursor": cursor})
        search = data.get("search") or {}
        nodes = search.get("nodes") or []
        repos = [Repo.from_graphql(n) for n in nodes if n]
        page_info = search.get("pageInfo") or {}
        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None
        return repos, int(search.get("repositoryCount") or 0), next_cursor

    # ---------------------------------------------------- GitHub Trending hints
    @staticmethod
    def parse_trending_html(html: str) -> list[str]:
        """Extract ``owner/repo`` links from a GitHub Trending HTML page."""
        pattern = re.compile(
            r'<h2 class="h3 lh-condensed">\s*<a\b[^>]*href="/([^"]+)"'
        )
        names: list[str] = []
        seen: set[str] = set()
        for match in pattern.finditer(html or ""):
            name = match.group(1).split("?", 1)[0].split("#", 1)[0].strip("/")
            if "/" not in name or name in seen:
                continue
            seen.add(name)
            names.append(name)
        return names

    def github_trending_repos(
        self, language: str | None = None, period: str = "weekly"
    ) -> list[str]:
        """Read GitHub Trending as a discovery hint (no stable public API)."""
        if self.settings.offline:
            raise OfflineError("Offline mode is enabled")
        if period not in {"daily", "weekly", "monthly"}:
            raise ValueError(f"Unknown trending period: {period!r}")
        url = "https://github.com/trending"
        if language:
            url += f"/{quote(language, safe='')}"
        response = self._client.get(
            url,
            params={"since": period},
            headers={
                "User-Agent": self.settings.user_agent,
                "Accept": "text/html",
            },
        )
        if response.status_code != 200:
            raise GitHubError(
                f"GitHub Trending returned {response.status_code}",
                status=response.status_code,
                url=str(response.request.url),
            )
        return self.parse_trending_html(response.text)

    # ------------------------------------------------------- OSS Insight hints
    def oss_insight_trends(self, period: str = "past_week", language: str | None = None) -> OssInsightResult:
        if self.settings.offline:
            raise OfflineError("Offline mode is enabled")
        params = {"period": period}
        if language:
            params["language"] = language
        response = self._client.get(
            "https://api.ossinsight.io/v1/trends/repos/",
            params=params,
            headers={"User-Agent": self.settings.user_agent},
        )
        if response.status_code != 200:
            raise GitHubError(f"OSS Insight returned {response.status_code}", status=response.status_code)
        payload = response.json()
        quality = payload.get("data_quality") or {}
        data = payload.get("data") or {}
        rows = data.get("rows") or []
        note = quality.get("reason") or ""
        available = bool(rows) and quality.get("status") != "unavailable"
        return OssInsightResult(rows=rows, available=available, note=note)

    def rate_limit(self) -> dict[str, Any]:
        return self._get_json(f"{self.settings.api_url}/rate_limit")
