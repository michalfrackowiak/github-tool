"""Phase 3 crawler: resumable crawl runs over planned search slices.

A crawl run is a set of query slices (one per keyword variant, language and
star bucket) that is persisted up front. Each page is checkpointed so a run can
be interrupted at any point and resumed without re-planning or losing work.
Repositories are keyed by their numeric GitHub id, so the same repo can appear
in many slices and still be stored once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import time
from typing import Any

from . import keywords
from .config import Settings
from .db import Database
from .planner import QuerySlice, plan_slices

MAX_SEARCH_RESULTS = 1000
MAX_PAGES = 10
GRAPHQL_PER_PAGE = 100


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class CrawlSummary:
    run_id: str
    profile: str
    status: str  # completed | paused | failed | already_done
    slices_total: int = 0
    slices_done: int = 0
    pages_fetched: int = 0
    repos_seen: int = 0
    repos_inserted: int = 0
    readmes_fetched: int = 0
    readmes_not_modified: int = 0
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "profile": self.profile,
            "status": self.status,
            "slices_total": self.slices_total,
            "slices_done": self.slices_done,
            "pages_fetched": self.pages_fetched,
            "repos_seen": self.repos_seen,
            "repos_inserted": self.repos_inserted,
            "readmes_fetched": self.readmes_fetched,
            "readmes_not_modified": self.readmes_not_modified,
            "error": self.error,
        }


@dataclass
class _Stats:
    pages_fetched: int = 0
    repos_seen: int = 0
    repos_inserted: int = 0
    readmes_fetched: int = 0
    readmes_not_modified: int = 0


class Crawler:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        client,
        *,
        logger: logging.Logger | None = None,
        sleep=time.sleep,
    ):
        self.settings = settings
        self.db = db
        self.client = client
        self.logger = logger or logging.getLogger("github_tool.crawler")
        self._sleep = sleep

    # ------------------------------------------------------------- planning
    def plan_profile(
        self, profile: str, *, in_readme: bool = False, include_forks: bool = False
    ) -> list[QuerySlice]:
        """Plan every keyword variant x language slice for a crawl profile."""
        crawl_profile = keywords.PROFILES.get(profile)
        if crawl_profile is None:
            raise ValueError(f"Unknown crawl profile: {profile!r}")

        count_fn = self.client.count_search
        seen: set[str] = set()
        memo: dict[str, int] = {}
        slices: list[QuerySlice] = []
        for slug in crawl_profile.keywords:
            keyword = keywords.KEYWORD_BY_SLUG.get(slug) or keywords.get_keyword(slug)
            for language in crawl_profile.languages:
                for variant in keyword.variants():
                    for sl in plan_slices(
                        slug,
                        language,
                        count_fn,
                        base_query=variant,
                        min_stars=crawl_profile.min_stars,
                        max_count_calls=24,
                        memo=memo,
                        in_readme=in_readme,
                        include_forks=include_forks,
                    ):
                        if sl.query in seen:
                            continue
                        seen.add(sl.query)
                        slices.append(sl)
        self.logger.info(
            "planned %d slices for profile %s (%d keywords x %d languages)",
            len(slices),
            profile,
            len(crawl_profile.keywords),
            len(crawl_profile.languages),
        )
        return slices

    # ------------------------------------------------------------------ run
    def run(
        self,
        profile: str = "default",
        *,
        resume: str | None = None,
        fetch_readmes: bool | None = None,
        discovery: str = "rest",
        max_slices: int | None = None,
        max_pages_per_slice: int | None = None,
        in_readme: bool = False,
        include_forks: bool = False,
    ) -> CrawlSummary:
        if discovery not in {"rest", "graphql"}:
            raise ValueError(f"Unknown discovery mode: {discovery!r}")

        stats = _Stats()
        current_slice_id: int | None = None

        if resume is not None:
            run = self.db.get_run(resume)
            if run is None:
                raise ValueError(f"Unknown crawl run: {resume!r}")
            run_id = resume
            profile_name = str(run["profile"])
            crawl_profile = keywords.PROFILES.get(profile_name)
            if fetch_readmes is None:
                fetch_readmes = crawl_profile.fetch_readmes if crawl_profile is not None else False

            counts = self.db.slice_counts(run_id)
            slices_total = sum(counts.values())
            pending = self.db.pending_slices(run_id)
            # REST and GraphQL pagination state are not interchangeable. If a
            # resumed slice carries state from the other mode, restart it from
            # page 1 rather than silently skipping pages.
            reset_any = False
            for sl in pending:
                pages_done = int(sl.get("pages_done") or 0)
                has_cursor = bool(sl.get("graphql_cursor"))
                if (discovery == "graphql" and pages_done > 0 and not has_cursor) or (
                    discovery == "rest" and has_cursor
                ):
                    self.db.update_slice(
                        int(sl["id"]), pages_done=0, graphql_cursor=None, status="running"
                    )
                    reset_any = True
            if reset_any:
                self.logger.warning(
                    "discovery mode is %s; restarting pagination for slices left by the other mode",
                    discovery,
                )
                pending = self.db.pending_slices(run_id)

            if not pending:
                self.db.update_run(run_id, status="completed", error=None, finished_at=_utc_now())
                self.logger.info("run %s already has no pending slices", run_id)
                return CrawlSummary(
                    run_id=run_id,
                    profile=profile_name,
                    status="already_done",
                    slices_total=slices_total,
                    slices_done=counts.get("done", 0),
                )
            slices_to_run = pending
        else:
            crawl_profile = keywords.PROFILES.get(profile)
            if crawl_profile is None:
                raise ValueError(f"Unknown crawl profile: {profile!r}")
            if fetch_readmes is None:
                fetch_readmes = crawl_profile.fetch_readmes

            planned = self.plan_profile(
                profile, in_readme=in_readme, include_forks=include_forks
            )
            run_id = self.db.start_run(profile)
            self.db.add_slices(run_id, [sl.as_dict() for sl in planned])
            profile_name = profile
            slices_total = len(planned)
            slices_to_run = self.db.pending_slices(run_id)

        if max_slices is not None:
            slices_to_run = slices_to_run[: max(1, max_slices)]

        try:
            for sl in slices_to_run:
                current_slice_id = int(sl["id"])
                self.logger.info(
                    "slice %s/%s start: %s",
                    int(sl.get("idx", 0)) + 1,
                    slices_total,
                    sl["query"],
                )
                if discovery == "graphql":
                    self._run_graphql_slice(
                        run_id,
                        sl,
                        fetch_readmes=bool(fetch_readmes),
                        stats=stats,
                        max_pages=max_pages_per_slice,
                    )
                else:
                    self._run_rest_slice(
                        run_id,
                        sl,
                        fetch_readmes=bool(fetch_readmes),
                        stats=stats,
                        max_pages=max_pages_per_slice,
                    )
                self.logger.info(
                    "slice %s done: pages=%d repos_seen=%d inserted=%d",
                    sl["query"],
                    stats.pages_fetched,
                    stats.repos_seen,
                    stats.repos_inserted,
                )
        except KeyboardInterrupt:
            self.db.update_run(run_id, status="paused")
            self.logger.warning("crawl run %s paused by user", run_id)
            return self._summary(run_id, profile_name, "paused", slices_total, stats)
        except Exception as exc:  # noqa: BLE001 - recorded then re-raised
            self.db.update_run(run_id, status="failed", error=str(exc))
            if current_slice_id is not None:
                self.db.update_slice(current_slice_id, status="failed", error=str(exc))
            self.logger.error("crawl run %s failed: %s", run_id, exc)
            raise

        if self.db.pending_slices(run_id):
            self.db.update_run(run_id, status="paused")
            return self._summary(run_id, profile_name, "paused", slices_total, stats)

        self.db.update_run(run_id, status="completed", error=None, finished_at=_utc_now())
        return self._summary(run_id, profile_name, "completed", slices_total, stats)

    # --------------------------------------------------------------- REST path
    def _run_rest_slice(
        self,
        run_id: str,
        sl: dict[str, Any],
        *,
        fetch_readmes: bool,
        stats: _Stats,
        max_pages: int | None,
    ) -> None:
        slice_id = int(sl["id"])
        query = str(sl["query"])
        keyword = sl.get("keyword")
        per_page = max(int(self.settings.search_per_page or 100), 1)
        page_limit = MAX_PAGES if max_pages is None else min(MAX_PAGES, max(1, max_pages))
        page = int(sl.get("pages_done") or 0) + 1
        truncated = bool(sl.get("overflow"))
        estimated = sl.get("estimated_count")
        if estimated is None:
            estimated = sl.get("total_count")

        if page > page_limit:
            # The process may have died after the final page checkpoint but
            # before the slice was marked done. Finalize instead of wedging.
            self.db.update_slice(
                slice_id,
                status="partial" if truncated else "done",
                overflow=1 if truncated else 0,
            )
            return

        while page <= page_limit:
            result = self.client.search_repositories(
                query, sort="stars", order="desc", page=page
            )
            stats.pages_fetched += 1

            for repo in result.items:
                self._store_repo(repo, keyword, fetch_readmes, stats)

            total = int(result.total_count or 0)
            if total > MAX_SEARCH_RESULTS:
                truncated = True
            self.db.update_slice(
                slice_id,
                pages_done=page,
                total_count=total,
                estimated_count=estimated,
                status="running",
            )
            self.db.update_run(
                run_id,
                cursor=json.dumps(
                    {
                        "slice_id": slice_id,
                        "idx": sl.get("idx"),
                        "query": query,
                        "page": page,
                    }
                ),
            )
            self.logger.info(
                "slice %s page %d: %d repos (total=%d)",
                query,
                page,
                len(result.items),
                total,
            )

            if not result.items:
                break
            if page * per_page >= min(total, MAX_SEARCH_RESULTS):
                break
            page += 1

        self.db.update_slice(
            slice_id,
            status="partial" if truncated else "done",
            overflow=1 if truncated else 0,
        )

    # ------------------------------------------------------------ GraphQL path
    def _run_graphql_slice(
        self,
        run_id: str,
        sl: dict[str, Any],
        *,
        fetch_readmes: bool,
        stats: _Stats,
        max_pages: int | None,
    ) -> None:
        slice_id = int(sl["id"])
        query = str(sl["query"])
        keyword = sl.get("keyword")
        page_limit = MAX_PAGES if max_pages is None else min(MAX_PAGES, max(1, max_pages))
        pages_done = int(sl.get("pages_done") or 0)
        page = pages_done + 1
        cursor: str | None = sl.get("graphql_cursor") or None
        truncated = bool(sl.get("overflow"))
        estimated = sl.get("estimated_count")
        if estimated is None:
            estimated = sl.get("total_count")

        if page > page_limit:
            self.db.update_slice(
                slice_id,
                status="partial" if truncated else "done",
                overflow=1 if truncated else 0,
            )
            return

        while page <= page_limit:
            repos, total, next_cursor = self.client.search_graphql(
                query, per_page=GRAPHQL_PER_PAGE, cursor=cursor
            )
            stats.pages_fetched += 1

            for repo in repos:
                self._store_repo(repo, keyword, fetch_readmes, stats)

            total = int(total or 0)
            if total > MAX_SEARCH_RESULTS:
                truncated = True
            self.db.update_slice(
                slice_id,
                pages_done=page,
                total_count=total,
                estimated_count=estimated,
                graphql_cursor=next_cursor,
                status="running",
            )
            self.db.update_run(
                run_id,
                cursor=json.dumps(
                    {
                        "slice_id": slice_id,
                        "idx": sl.get("idx"),
                        "query": query,
                        "page": page,
                        "cursor": next_cursor,
                    }
                ),
            )
            self.logger.info(
                "slice %s graphql page %d: %d repos (total=%d)",
                query,
                page,
                len(repos),
                total,
            )

            if not repos:
                break
            if next_cursor is None:
                break
            if page * GRAPHQL_PER_PAGE >= min(total, MAX_SEARCH_RESULTS):
                break
            cursor = next_cursor
            page += 1

        self.db.update_slice(
            slice_id,
            status="partial" if truncated else "done",
            overflow=1 if truncated else 0,
        )

    # ----------------------------------------------------------------- helpers
    def _store_repo(
        self,
        repo,
        keyword: str | None,
        fetch_readmes: bool,
        stats: _Stats,
    ) -> None:
        existing = self.db.get_repo(repo.id) if fetch_readmes else None
        inserted = self.db.upsert_repo(repo, keyword=keyword)
        stats.repos_seen += 1
        if inserted:
            stats.repos_inserted += 1
        if fetch_readmes:
            self._maybe_fetch_readme(repo, existing, stats)

    def _maybe_fetch_readme(self, repo, existing, stats: _Stats) -> None:
        conditional_etag = None
        if existing is not None and existing.readme_text is not None:
            conditional_etag = existing.readme_etag

        result = self.client.get_readme(repo.full_name, etag=conditional_etag)
        if result.not_modified:
            stats.readmes_not_modified += 1
            return
        if result.text is not None:
            digest = hashlib.sha256(result.text.encode("utf-8")).hexdigest()
            self.db.update_readme(repo.id, result.text, result.etag, digest)
            stats.readmes_fetched += 1

    def _summary(
        self,
        run_id: str,
        profile: str,
        status: str,
        slices_total: int,
        stats: _Stats,
    ) -> CrawlSummary:
        counts = self.db.slice_counts(run_id)
        return CrawlSummary(
            run_id=run_id,
            profile=profile,
            status=status,
            slices_total=slices_total,
            slices_done=counts.get("done", 0),
            pages_fetched=stats.pages_fetched,
            repos_seen=stats.repos_seen,
            repos_inserted=stats.repos_inserted,
            readmes_fetched=stats.readmes_fetched,
            readmes_not_modified=stats.readmes_not_modified,
        )
