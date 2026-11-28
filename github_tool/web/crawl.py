"""Bounded web crawl requests, job lifecycle, and worker orchestration.

Keeping this separate from the FastAPI routes gives the crawl options one typed
owner and lets status semantics live next to the worker that persists them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
import threading
from typing import Any

from ..config import Settings
from ..crawler import Crawler
from ..db import Database
from ..github import GitHubClient

WEB_CRAWL_MAX_SLICES = 5
WEB_CRAWL_MAX_PAGES = 3
# Curated subset: leave out `default`, which expands to every keyword and nine
# languages. The web trigger gets bounded, reviewable profiles only.
WEB_CRAWL_ALLOWED_PROFILES = frozenset({"ai", "systems", "web"})


@dataclass(frozen=True)
class CrawlRequest:
    """Validated options accepted by the web crawl trigger."""

    profile: str
    max_slices: int
    max_pages_per_slice: int
    discovery: str = "rest"
    fetch_readmes: bool = False
    in_readme: bool = False
    include_forks: bool = False

    @staticmethod
    def _bounded_int(raw: str, cap: int) -> int | None:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return max(1, min(value, cap))

    @classmethod
    def from_form(
        cls,
        profile: str,
        max_slices: str,
        max_pages_per_slice: str,
        discovery: str,
        fetch_readmes: str,
        in_readme: str,
        include_forks: str,
    ) -> CrawlRequest | None:
        """Return validated options, or ``None`` for an invalid request."""
        slices = cls._bounded_int(max_slices, WEB_CRAWL_MAX_SLICES)
        pages = cls._bounded_int(max_pages_per_slice, WEB_CRAWL_MAX_PAGES)
        if (
            profile not in WEB_CRAWL_ALLOWED_PROFILES
            or discovery not in {"rest", "graphql"}
            or slices is None
            or pages is None
        ):
            return None
        return cls(
            profile=profile,
            max_slices=slices,
            max_pages_per_slice=pages,
            discovery=discovery,
            fetch_readmes=fetch_readmes == "1",
            in_readme=in_readme == "1",
            include_forks=include_forks == "1",
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CrawlRequest:
        """Rebuild a request from the JSON stored on a job row."""
        allowed = {field.name for field in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def crawl_job_status(summary_status: str) -> tuple[str, str]:
    """Map a ``CrawlSummary`` status to the job's ``(status, phase)`` pair."""
    mapping = {
        "completed": ("completed", "done"),
        "failed": ("failed", "failed"),
        "paused": ("paused", "paused"),
    }
    return mapping.get(summary_status, ("paused", "paused"))


def resolve_job_run(database: Database, job: dict[str, Any] | None) -> dict[str, Any] | None:
    """Resolve the run belonging to a web job, including while it is starting."""
    if not job:
        return None
    if job.get("run_id"):
        run = database.get_run(job["run_id"])
        if run is not None:
            return run
    if job["status"] in {"queued", "running"}:
        # Crawler.run() creates the run_id after the job is claimed; until it
        # finishes, match runs started after the job rather than an older run.
        return database.latest_run_since(job["created_at"])
    return None


def run_crawl_job(
    settings: Settings,
    job_id: str,
    request: CrawlRequest | Mapping[str, Any],
    database: Database | None = None,
    *,
    crawler_factory: Any = None,
    client_factory: Any = None,
) -> None:
    """Run one bounded web crawl using the crawler's normal DB writer.

    ``crawler_factory`` and ``client_factory`` are injection seams for tests;
    production uses the same ``Crawler``/``GitHubClient`` classes as the CLI.
    Every failure path — including setup — is persisted on the job row so the
    single-flight slot is never stranded.
    """
    params = request if isinstance(request, CrawlRequest) else CrawlRequest.from_dict(request)
    database = database or Database(settings.db_path)
    client: Any = None
    heartbeat_thread: threading.Thread | None = None
    stop_heartbeat = threading.Event()
    current_phase = "planning"
    try:
        database.initialize()
        client = (
            GitHubClient(settings, cache=database)
            if client_factory is None
            else client_factory(settings, database)
        )
        crawler = (crawler_factory or Crawler)(settings, database, client)
        database.update_crawl_job(job_id, status="running", phase=current_phase)

        def set_phase(phase: str) -> None:
            nonlocal current_phase
            current_phase = phase
            try:
                database.update_crawl_job(job_id, phase=phase)
            except Exception:  # noqa: BLE001 - progress must not fail a crawl
                pass

        def heartbeat() -> None:
            while not stop_heartbeat.wait(60):
                try:
                    database.update_crawl_job(job_id, phase=current_phase)
                except Exception:  # noqa: BLE001 - a failed heartbeat is harmless
                    pass

        heartbeat_thread = threading.Thread(
            target=heartbeat, daemon=True, name=f"crawl-heartbeat-{job_id[:8]}"
        )
        heartbeat_thread.start()

        def on_run_start(run_id: str) -> None:
            database.update_crawl_job(job_id, run_id=run_id)

        summary = crawler.run(
            profile=params.profile,
            fetch_readmes=params.fetch_readmes,
            discovery=params.discovery,
            max_slices=params.max_slices,
            max_pages_per_slice=params.max_pages_per_slice,
            in_readme=params.in_readme,
            include_forks=params.include_forks,
            on_run_start=on_run_start,
            on_progress=set_phase,
        )
        data = summary.as_dict()
        job_status, phase = crawl_job_status(str(data.get("status", "failed")))
        database.update_crawl_job(
            job_id,
            status=job_status,
            phase=phase,
            run_id=data.get("run_id"),
            summary=data,
            error=data.get("error"),
            finished_at=utc_now(),
        )
    except Exception as exc:  # noqa: BLE001 - persisted so the UI can show it
        database.update_crawl_job(
            job_id,
            status="failed",
            phase="error",
            error=str(exc),
            finished_at=utc_now(),
        )
    finally:
        stop_heartbeat.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=1.0)
        close = getattr(client, "close", None)
        if callable(close):
            close()
