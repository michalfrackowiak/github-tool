"""Phase 5: local web UI (FastAPI + Jinja2, no external assets).

Design goals: works offline, server-rendered, and every network call is
explicit. If offline mode is on, routes refuse to touch GitHub.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
import html
from pathlib import Path
import threading
from typing import Any, Iterator
import uuid
from urllib.parse import quote, urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from ..config import Settings
from ..db import Database
from ..export import to_csv, to_markdown
from ..github import GitHubClient, GitHubError, OfflineError
from ..keywords import KEYWORDS, LANGUAGES, WINDOW_DAYS, WINDOW_LABELS, WINDOWS, get_keyword
from ..links import generate_links
from ..models import Repo, TrendRow
from ..search_history import normalize_search_params, record_best_effort
from .crawl import (
    WEB_CRAWL_ALLOWED_PROFILES,
    WEB_CRAWL_MAX_PAGES,
    WEB_CRAWL_MAX_SLICES,
    CrawlRequest,
    resolve_job_run,
    run_crawl_job,
    utc_now,
)

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _sparkline_svg(series: list[tuple[str, int]], width: int = 280, height: int = 64) -> Markup:
    if len(series) < 2:
        return Markup('<span class="muted">No star history yet.</span>')
    values = [v for _, v in series]
    lo, hi = min(values), max(values)
    span = max(hi - lo, 1)
    step = width / max(len(values) - 1, 1)
    points = []
    for i, value in enumerate(values):
        x = round(i * step, 1)
        y = round(height - ((value - lo) / span) * (height - 4) - 2, 1)
        points.append(f"{x},{y}")
    first, last = values[0], values[-1]
    delta = last - first
    label = f"{series[0][0]} → {series[-1][0]} · {delta:+,} stars"
    safe_label = html.escape(label, quote=True)
    return Markup(
        f'<svg class="sparkline" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{safe_label}">'
        f'<polyline fill="none" stroke="currentColor" stroke-width="2" points="{" ".join(points)}"/></svg>'
        f'<div class="muted">{safe_label}</div>'
    )


templates.env.filters["sparkline"] = _sparkline_svg
templates.env.filters["shortdate"] = lambda value: (value or "")[:10]
templates.env.filters["urlencode"] = lambda value: quote(str(value), safe="")


@contextmanager
def _client(app: FastAPI) -> Iterator[GitHubClient | None]:
    injected = getattr(app.state, "client", None)
    if injected is not None:
        yield injected
        return
    client = GitHubClient(app.state.settings, cache=app.state.db)
    try:
        yield client
    finally:
        client.close()


def _langs(request: Request) -> list[str]:
    return [lang for lang in request.query_params.getlist("language") if lang]


def _int_param(request: Request, key: str, default: int, minimum: int = 0, maximum: int = 10_000_000) -> int:
    raw = request.query_params.get(key, "")
    try:
        value = int(raw) if raw != "" else default
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def _readme_query(request: Request, keyword_slug: str) -> str:
    text = request.query_params.get("readme_q", "").strip()
    if not text:
        text = request.query_params.get("q", "").strip()
    if not text:
        try:
            text = get_keyword(keyword_slug).name
        except KeyError:
            text = keyword_slug
    return text


def _readme_matches(database, text: str, limit: int) -> set[int]:
    """Local README-only approximation of GitHub's ``in:readme`` qualifier."""
    terms = [t.lower() for t in re.findall(r"\w+", text) if len(t) > 1]
    if not terms:
        return set()
    return {
        repo.id
        for repo in database.search_fts(text, limit=limit)
        if all(term in (repo.readme_text or "").lower() for term in terms)
    }


def _optional_int_param(request: Request, key: str) -> int | None:
    raw = request.query_params.get(key, "")
    try:
        value = int(raw) if raw else None
    except ValueError:
        return None
    return value if value is not None and value >= 0 else None


def _ratio_param(request: Request, key: str = "max_fork_ratio") -> float | None:
    raw = request.query_params.get(key, "")
    try:
        value = float(raw) if raw else None
    except ValueError:
        return None
    return value if value is not None and value >= 0 else None


def _qs(params: dict[str, Any]) -> str:
    return urlencode([(k, vv) for k, v in params.items() for vv in (v if isinstance(v, list) else [v]) if vv != ""])


def _context(request: Request, **extra: Any) -> dict[str, Any]:
    app = request.app
    return {
        "request": request,
        "keywords": KEYWORDS,
        "languages": LANGUAGES,
        "windows": WINDOWS,
        "window_labels": WINDOW_LABELS,
        "offline": app.state.settings.offline,
        "db_path": str(app.state.settings.db_path),
        "saved": app.state.db.list_saved_searches(),
        "nav": extra.pop("nav", ""),
        **extra,
    }


def _sort_repos(repos: list[Repo], sort: str) -> list[Repo]:
    key = {
        "stars": lambda r: r.stars,
        "forks": lambda r: r.forks,
        "updated": lambda r: r.updated_at or r.pushed_at or "",
    }.get(sort)
    if key is None:
        key = lambda r: r.stars  # noqa: E731
    return sorted(repos, key=key, reverse=True)


def _trend_export_rows(rows: list[TrendRow], window: int) -> list[dict[str, Any]]:
    return [
        {
            "rank": i,
            "full_name": r.repo.full_name,
            "url": r.repo.url,
            "language": r.repo.language or "",
            "stars": r.repo.stars,
            "forks": r.repo.forks,
            "gain": r.gain(window),
            "fork_ratio": round(r.repo.forks / max(r.repo.stars, 1), 3),
            "relative_growth": (
                "" if r.relative_growth_for(window) is None else r.relative_growth_for(window)
            ),
            "acceleration": (
                "" if r.acceleration_for(window) is None else r.acceleration_for(window)
            ),
            "is_new": r.is_new,
            "license": r.repo.license or "",
        }
        for i, r in enumerate(rows, start=1)
    ]


def create_app(settings: Settings | None = None, db: Database | None = None, client: Any | None = None) -> FastAPI:
    settings = settings or Settings()
    database = db or Database(settings.db_path)
    database.initialize()
    database.reap_stale_crawl_jobs()

    app = FastAPI(title="GitHub-Tool", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.db = database
    app.state.client = client
    app.state.crawl_lock = threading.Lock()
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        latest = database.latest_run()
        stats = {
            "repos": database.count_repos(),
            "keywords": len(database.keyword_counts()),
            "latest_run": latest,
        }
        return templates.TemplateResponse(
            request,
            "index.html",
            _context(request, nav="home", stats=stats, keyword="rag", language="Python", window="30d"),
        )

    @app.get("/links", response_class=HTMLResponse)
    def links_page(request: Request) -> HTMLResponse:
        keyword = request.query_params.get("keyword", "rag")
        window = request.query_params.get("window", "30d")
        langs = _langs(request) or [None]
        try:
            groups = [
                {"language": lang, "views": generate_links(keyword, lang, window)}
                for lang in langs
            ]
        except (KeyError, ValueError) as exc:
            return templates.TemplateResponse(
                request, "error.html", _context(request, message=str(exc)), status_code=400
            )
        return templates.TemplateResponse(
            request,
            "links.html",
            _context(request, nav="home", keyword=keyword, window=window, langs=langs, groups=groups),
        )

    @app.get("/search", response_class=HTMLResponse)
    def search_page(request: Request) -> HTMLResponse:
        keyword_slug = request.query_params.get("keyword", "rag")
        window = request.query_params.get("window", "30d")
        sort = request.query_params.get("sort", "stars")
        source = request.query_params.get("source", "api")
        query_override = request.query_params.get("q", "").strip()
        langs = _langs(request)
        limit = _int_param(request, "limit", 50, 1, 100)
        min_stars = _int_param(request, "min_stars", 0, 0)
        license_name = request.query_params.get("license", "").strip().lower() or None
        include_archived = request.query_params.get("archived") == "1"
        include_forks = request.query_params.get("forks") == "1"
        in_readme = request.query_params.get("in_readme") == "1"
        if source not in {"api", "local"}:
            source = "api"
        try:
            kw = get_keyword(keyword_slug)
        except KeyError as exc:
            return templates.TemplateResponse(
                request, "error.html", _context(request, message=str(exc)), status_code=400
            )

        if settings.offline and source == "api":
            source = "local"
        repos: list[Repo] = []
        total = 0
        error = None
        if source == "local":
            if query_override:
                repos = database.search_fts(query_override, limit=limit * 2)
            else:
                repos = []
                for lang in langs or [None]:
                    repos.extend(
                        database.list_repos(
                            language=lang,
                            limit=limit,
                            include_archived=include_archived,
                            include_forks=include_forks,
                        )
                    )
            if langs:
                repos = [r for r in repos if r.language in langs]
            seen: set[int] = set()
            repos = [r for r in repos if not (r.id in seen or seen.add(r.id))]
            if in_readme:
                matching_ids = _readme_matches(
                    database, _readme_query(request, keyword_slug), limit=max(limit * 2, 100)
                )
                repos = [r for r in repos if r.id in matching_ids]
            repos = _sort_repos(repos, sort)[:limit]
            total = len(repos)
        else:
            try:
                with _client(app) as client:
                    assert client is not None
                    seen: dict[int, Repo] = {}
                    for lang in langs or [None]:
                        query = query_override or kw.link_query(lang)
                        if window and not query_override:
                            from ..cli import _window_qualifier  # local helper, no side effects

                            qualifier = _window_qualifier(window)
                            if qualifier:
                                query = f"{query} {qualifier}"
                        if in_readme and "in:readme" not in query:
                            query = f"{query} in:readme"
                        if include_forks and "fork:" not in query:
                            query = f"{query} fork:true"
                        result = client.search_repositories(query, sort=sort, order="desc", per_page=min(limit, 100))
                        total += result.total_count
                        for repo in result.items:
                            seen.setdefault(repo.id, repo)
                    repos = _sort_repos(list(seen.values()), sort)[:limit]
                    for repo in repos:
                        database.upsert_repo(repo, keyword=kw.slug)
            except (GitHubError, OfflineError) as exc:
                error = str(exc)
                repos = []

        def visible(repo: Repo) -> bool:
            if repo.stars < min_stars:
                return False
            if license_name and (repo.license or "").strip().lower() != license_name:
                return False
            if not include_archived and repo.archived:
                return False
            if not include_forks and repo.fork:
                return False
            return True

        repos = [r for r in repos if visible(r)]

        history_params = normalize_search_params(
            {
                "keyword": keyword_slug,
                "q": query_override,
                "window": window,
                "source": source,
                "language": langs,
                "sort": sort,
                "limit": limit,
                "min_stars": min_stars,
                "license": license_name,
                "archived": "1" if include_archived else "",
                "forks": "1" if include_forks else "",
                "in_readme": "1" if in_readme else "",
                "readme_q": _readme_query(request, keyword_slug) if in_readme else "",
            }
        )
        # Record every executed search, including a failed API call with zero
        # results, so /saved always has a replayable definition to show.
        record_best_effort(database, history_params, source, len(repos))

        filter_params: dict[str, Any] = {
            "window": window,
            "source": source,
            "language": langs,
        }
        # Local results are listed by language (or free-text FTS), never by
        # keyword, so carrying a keyword into the export would silently drop
        # rows that are visible on this page.
        if source != "local":
            filter_params["keyword"] = keyword_slug
        if query_override:
            filter_params["q"] = query_override
        if min_stars:
            filter_params["min_stars"] = min_stars
        if license_name:
            filter_params["license"] = license_name
        if include_archived:
            filter_params["archived"] = "1"
        if include_forks:
            filter_params["forks"] = "1"
        if in_readme:
            filter_params["in_readme"] = "1"
            filter_params["readme_q"] = _readme_query(request, keyword_slug)

        sort_urls = {}
        for option in ("stars", "forks", "updated"):
            sort_urls[option] = f"/search?{_qs({**filter_params, 'sort': option})}"
        export_url = f"/export.csv?{_qs({**filter_params, 'sort': sort, 'limit': limit})}"
        export_json_url = f"/export.json?{_qs({**filter_params, 'sort': sort, 'limit': limit})}"
        return templates.TemplateResponse(
            request,
            "search.html",
            _context(
                request,
                nav="search",
                keyword=kw,
                keyword_slug=keyword_slug,
                window=window,
                source=source,
                sort=sort,
                langs=langs,
                repos=repos,
                total=total,
                error=error,
                q=query_override,
                sort_urls=sort_urls,
                export_url=export_url,
                export_json_url=export_json_url,
                min_stars=min_stars,
                license_name=license_name,
                include_archived=include_archived,
                include_forks=include_forks,
                in_readme=in_readme,
            ),
        )

    @app.get("/trends", response_class=HTMLResponse)
    def trends_page(request: Request) -> HTMLResponse:
        from ..trends import get_trending

        window_key = request.query_params.get("window", "7d")
        window = WINDOW_DAYS.get(window_key, 7)
        sort = request.query_params.get("sort", "most_gained")
        language = request.query_params.get("language") or None
        min_stars = _int_param(request, "min_stars", 50, 0)
        license_name = request.query_params.get("license") or None
        include_archived = request.query_params.get("archived") == "1"
        include_forks = request.query_params.get("forks") == "1"
        max_fork_ratio = _ratio_param(request)
        active_within = _optional_int_param(request, "active_within")
        error = None
        rows: list[TrendRow] = []
        try:
            rows = get_trending(
                database,
                window=window,
                sort=sort,
                language=language,
                min_stars=min_stars,
                license=license_name,
                include_archived=include_archived,
                include_forks=include_forks,
                max_fork_ratio=max_fork_ratio,
                active_within_days=active_within,
                limit=100,
            )
        except ValueError as exc:
            error = str(exc)
        params: dict[str, Any] = {
            "window": window_key,
            "sort": sort,
            "language": language or "",
            "min_stars": min_stars,
            "license": license_name or "",
        }
        if include_archived:
            params["archived"] = "1"
        if include_forks:
            params["forks"] = "1"
        if max_fork_ratio is not None:
            params["max_fork_ratio"] = max_fork_ratio
        if active_within is not None:
            params["active_within"] = active_within
        qs = _qs(params)
        export_csv = f"/export.csv?trends=1&{qs}"
        export_md = f"/export.md?trends=1&{qs}"
        export_json = f"/export.json?trends=1&{qs}"
        return templates.TemplateResponse(
            request,
            "trends.html",
            _context(
                request,
                nav="trends",
                rows=rows,
                window=window,
                window_key=window_key,
                sort=sort,
                language=language,
                min_stars=min_stars,
                license_name=license_name,
                include_archived=include_archived,
                include_forks=include_forks,
                max_fork_ratio=max_fork_ratio,
                active_within=active_within,
                error=error,
                export_csv=export_csv,
                export_md=export_md,
                export_json=export_json,
            ),
        )

    @app.get("/repo/{owner}/{name}", response_class=HTMLResponse)
    def repo_page(request: Request, owner: str, name: str) -> HTMLResponse:
        full_name = f"{owner}/{name}"
        repo = database.get_repo(full_name)
        if repo is None and not settings.offline:
            try:
                with _client(app) as client:
                    assert client is not None
                    result = client.search_repositories(f"repo:{full_name}", per_page=1)
                    if result.items:
                        repo = result.items[0]
                        database.upsert_repo(repo)
            except (GitHubError, OfflineError):
                repo = None
        if repo is None:
            return templates.TemplateResponse(
                request,
                "error.html",
                _context(request, message=f"{full_name} is not in the local index. Crawl it or search online."),
                status_code=404,
            )

        readme_error = None
        if not settings.offline:
            try:
                with _client(app) as client:
                    assert client is not None
                    result = client.get_readme(repo.full_name, etag=repo.readme_etag)
                    if result.text:
                        import hashlib

                        database.update_readme(
                            repo.id, result.text, result.etag, hashlib.sha256(result.text.encode()).hexdigest()
                        )
                        repo = database.get_repo(repo.id) or repo
            except (GitHubError, OfflineError) as exc:
                readme_error = str(exc)

        if repo.readme_text:
            try:
                from ..extraction import extract_for_repo

                extract_for_repo(database, repo.id, repo.readme_text)
            except Exception:
                pass
        commands = database.get_install_commands(repo.id)
        hardware = database.get_hw_requirements(repo.id)
        manifest = database.get_manifest_hints(repo.id)
        hardware_primary = [
            h for h in hardware if h.get("gpu") is not None or any(h.get(k) is not None for k in ("vram_gb", "ram_gb", "disk_gb"))
        ]
        hardware_other = [h for h in hardware if h not in hardware_primary]

        from ..trends import star_series

        series = star_series(database, repo.id, days=90) if database.snapshot_count(repo.id) or database.get_star_days(repo.id) else []
        return templates.TemplateResponse(
            request,
            "repo.html",
            _context(
                request,
                nav="search",
                repo=repo,
                commands=commands,
                hardware=hardware,
                hardware_primary=hardware_primary,
                hardware_other=hardware_other,
                manifest=manifest,
                series=series,
                readme_error=readme_error,
                readme_excerpt=(repo.readme_text or "")[:80_000],
            ),
        )

    @app.get("/saved", response_class=HTMLResponse)
    def saved_page(request: Request) -> HTMLResponse:
        saved_links = []
        for item in database.list_saved_searches():
            params = item["params"]
            saved_links.append(
                {
                    **item,
                    "search_url": "/search?" + _qs(params),
                    "trends_url": "/trends?"
                    + _qs(
                        {
                            k: v
                            for k, v in params.items()
                            if k in {"window", "sort", "language", "min_stars", "license"}
                        }
                    ),
                }
            )
        history_links = [
            {
                **item,
                "replay_url": "/search?" + _qs(item["params"]),
            }
            for item in database.list_search_history(limit=20)
        ]
        return templates.TemplateResponse(
            request,
            "saved.html",
            _context(request, nav="saved", saved_links=saved_links, history_links=history_links),
        )

    @app.post("/saved")
    def save_search(
        name: str = Form(...),
        keyword: str = Form("rag"),
        window: str = Form("30d"),
        source: str = Form("api"),
        sort: str = Form("stars"),
        language: str = Form(""),
        q: str = Form(""),
        min_stars: int = Form(0),
        license: str = Form(""),
        archived: str = Form(""),
        forks: str = Form(""),
        in_readme: str = Form(""),
    ) -> RedirectResponse:
        params: dict[str, Any] = {"keyword": keyword, "window": window, "source": source, "sort": sort}
        if language:
            params["language"] = [line for line in language.split(",") if line]
        if q:
            params["q"] = q
        if min_stars:
            params["min_stars"] = min_stars
        if license:
            params["license"] = license
        if archived == "1":
            params["archived"] = "1"
        if forks == "1":
            params["forks"] = "1"
        if in_readme == "1":
            params["in_readme"] = "1"
        database.save_search(name.strip() or "unnamed", params)
        return RedirectResponse("/saved", status_code=303)

    @app.post("/saved/delete")
    def delete_saved(name: str = Form(...)) -> RedirectResponse:
        database.delete_saved_search(name)
        return RedirectResponse("/saved", status_code=303)

    @app.post("/saved/history/clear")
    def clear_history() -> RedirectResponse:
        database.clear_search_history()
        return RedirectResponse("/saved", status_code=303)

    @app.get("/crawl", response_class=HTMLResponse)
    def crawl_page(request: Request) -> HTMLResponse:
        latest = database.latest_run()
        slices = database.slice_counts(latest["id"]) if latest else {}
        active_job = database.active_crawl_job()
        job_id = request.query_params.get("job")
        job = database.get_crawl_job(job_id) if job_id else active_job
        run = resolve_job_run(database, job)
        if run:
            latest = run
            slices = database.slice_counts(run["id"])
        return templates.TemplateResponse(
            request,
            "crawl.html",
            _context(
                request,
                nav="crawl",
                latest=latest,
                slices=slices,
                active_job=active_job,
                job=job,
                profiles=sorted(WEB_CRAWL_ALLOWED_PROFILES),
                max_slices=WEB_CRAWL_MAX_SLICES,
                max_pages=WEB_CRAWL_MAX_PAGES,
            ),
        )

    @app.post("/crawl")
    def start_crawl(
        request: Request,
        profile: str = Form("ai"),
        max_slices: str = Form("1"),
        max_pages_per_slice: str = Form("1"),
        discovery: str = Form("rest"),
        fetch_readmes: str = Form(""),
        in_readme: str = Form(""),
        include_forks: str = Form(""),
    ):
        if settings.offline:
            return templates.TemplateResponse(
                request,
                "error.html",
                _context(request, message="Crawls are disabled in offline mode."),
                status_code=503,
            )
        crawl_request = CrawlRequest.from_form(
            profile,
            max_slices,
            max_pages_per_slice,
            discovery,
            fetch_readmes,
            in_readme,
            include_forks,
        )
        if crawl_request is None:
            return templates.TemplateResponse(
                request,
                "error.html",
                _context(request, message="Invalid crawl options."),
                status_code=400,
            )
        params = crawl_request.as_dict()
        with app.state.crawl_lock:
            job = database.claim_crawl_job(uuid.uuid4().hex, crawl_request.profile, params)
        if job is None:
            return templates.TemplateResponse(
                request,
                "error.html",
                _context(request, message="A crawl is already running. Please wait."),
                status_code=409,
            )
        runner = getattr(app.state, "crawl_runner", None)
        if runner is not None:
            try:
                runner(job["id"], params)
            except Exception as exc:  # noqa: BLE001 - do not strand the slot
                database.update_crawl_job(
                    job["id"],
                    status="failed",
                    phase="error",
                    error=str(exc),
                    finished_at=utc_now(),
                )
        else:
            threading.Thread(
                target=run_crawl_job,
                args=(settings, job["id"], params, database),
                daemon=True,
            ).start()
        return RedirectResponse(f"/crawl?job={job['id']}", status_code=303)

    @app.get("/crawl/status/{job_id}")
    def crawl_status(job_id: str) -> JSONResponse:
        job = database.get_crawl_job(job_id)
        if job is None:
            return JSONResponse({"error": "Unknown crawl job"}, status_code=404)
        run = resolve_job_run(database, job)
        return JSONResponse(
            {
                **job,
                "run": run,
                "slices": database.slice_counts(run["id"]) if run else {},
            }
        )

    def _export_rows(request: Request) -> tuple[list[dict[str, Any]], str]:
        include_archived = request.query_params.get("archived") == "1"
        include_forks = request.query_params.get("forks") == "1"
        license_name = request.query_params.get("license") or None
        if request.query_params.get("trends") == "1":
            from ..trends import SORTS, get_trending

            window_key = request.query_params.get("window", "7d")
            window = WINDOW_DAYS.get(window_key, 7)
            sort = request.query_params.get("sort", "most_gained")
            if sort not in SORTS:
                sort = "most_gained"
            rows = get_trending(
                database,
                window=window,
                sort=sort,
                language=request.query_params.get("language") or None,
                min_stars=_int_param(request, "min_stars", 50, 0),
                license=license_name,
                include_archived=include_archived,
                include_forks=include_forks,
                max_fork_ratio=_ratio_param(request),
                active_within_days=_optional_int_param(request, "active_within"),
                limit=_int_param(request, "limit", 1000, 1, 5000),
            )
            return _trend_export_rows(rows, window), f"Trending {window_key}"
        rows = database.export_rows(
            language=request.query_params.get("language") or None,
            min_stars=_int_param(request, "min_stars", 0, 0),
            limit=_int_param(request, "limit", 1000, 1, 5000),
            include_archived=include_archived,
            include_forks=include_forks,
            keyword=request.query_params.get("keyword") or None,
            license=license_name,
        )
        if request.query_params.get("in_readme") == "1":
            slug = request.query_params.get("keyword", "rag")
            matching_ids = _readme_matches(
                database, _readme_query(request, slug), limit=5000
            )
            rows = [r for r in rows if r["id"] in matching_ids]
        return rows, "Repository index"

    @app.get("/export.csv")
    def export_csv(request: Request) -> PlainTextResponse:
        rows, _ = _export_rows(request)
        return PlainTextResponse(
            to_csv(rows),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=github-tool.csv"},
        )

    @app.get("/export.md")
    def export_md(request: Request) -> PlainTextResponse:
        rows, title = _export_rows(request)
        return PlainTextResponse(
            to_markdown(rows, title=title),
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=github-tool.md"},
        )

    @app.get("/export.json")
    def export_json(request: Request) -> JSONResponse:
        rows, title = _export_rows(request)
        return JSONResponse(
            {"title": title, "rows": rows},
            headers={"Content-Disposition": "attachment; filename=github-tool.json"},
        )

    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "repos": database.count_repos(),
                "offline": settings.offline,
                "authenticated": settings.authenticated,
            }
        )

    @app.exception_handler(GitHubError)
    def handle_github_error(request: Request, exc: GitHubError) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "error.html", _context(request, message=str(exc)), status_code=502
        )

    return app


app = create_app()
