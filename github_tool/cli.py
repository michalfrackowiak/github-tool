"""Command-line interface for GitHub-Tool."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, timedelta
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

from .config import Settings
from .db import Database
from .github import GitHubClient, GitHubError, OfflineError
from .keywords import KEYWORDS, PROFILES, WINDOW_LABELS, get_keyword, write_keyword_map
from .links import generate_links
from .models import utc_today


def _window_days(value: str | int) -> int:
    if isinstance(value, int):
        return value
    raw = str(value).strip().lower()
    if raw.isdigit():
        return int(raw)
    mapping = {"today": 1, "day": 1, "7d": 7, "30d": 30, "90d": 90, "365d": 365, "year": 365}
    if raw not in mapping:
        raise ValueError(f"Unknown window: {value!r}")
    return mapping[raw]


def _window_qualifier(window: str | None, today: date | None = None) -> str | None:
    if not window:
        return None
    today = today or utc_today()
    try:
        days = _window_days(window)
    except ValueError:
        return None
    cutoff = today - timedelta(days=days)
    qualifier = "created" if days >= 365 else "pushed"
    return f"{qualifier}:>={cutoff.isoformat()}"


def _settings(args: argparse.Namespace) -> Settings:
    settings = Settings()
    changes: dict[str, Any] = {}
    if getattr(args, "db", None):
        changes["db_path"] = Path(args.db)
    if getattr(args, "offline", False):
        changes["offline"] = True
    return replace(settings, **changes) if changes else settings


def _db(settings: Settings) -> Database:
    db = Database(settings.db_path)
    db.initialize()
    return db


def _client(settings: Settings, db: Database) -> GitHubClient:
    return GitHubClient(settings, cache=db)


def _clip(value: Any, width: int) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\n", " ")
    return text if len(text) <= width else text[: max(width - 1, 0)] + "…"


def _table(headers: list[str], rows: list[list[Any]], widths: list[int] | None = None) -> str:
    widths = widths or [max(len(h), *(len(_clip(r[i], 60)) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    widths = [min(w, 60) for w in widths]
    lines = ["  ".join(_clip(h, widths[i]).ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        lines.append("  ".join(_clip(row[i], widths[i]).ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(lines)


def _trend_export_rows(rows: list[Any], window: int = 7) -> list[dict[str, Any]]:
    out = []
    for rank, row in enumerate(rows, start=1):
        out.append(
            {
                "rank": rank,
                "full_name": row.repo.full_name,
                "url": row.repo.url,
                "language": row.repo.language or "",
                "stars": row.repo.stars,
                "forks": row.repo.forks,
                "gain": row.gain(window),
                "fork_ratio": round(row.repo.forks / max(row.repo.stars, 1), 3),
                "relative_growth": (
                    "" if row.relative_growth_for(window) is None
                    else row.relative_growth_for(window)
                ),
                "acceleration": (
                    "" if row.acceleration_for(window) is None
                    else row.acceleration_for(window)
                ),
                "is_new": row.is_new,
                "license": row.repo.license or "",
            }
        )
    return out


# --------------------------------------------------------------------- commands
def cmd_init_db(args: argparse.Namespace) -> int:
    settings = _settings(args)
    db = _db(settings)
    print(f"Database ready: {settings.db_path} ({db.count_repos()} repos)")
    return 0


def cmd_keywords(args: argparse.Namespace) -> int:
    if args.json:
        path = write_keyword_map(args.json)
        print(f"Wrote {path}")
        return 0
    rows = [[k.name, k.topic or "-", "; ".join(k.phrases)] for k in KEYWORDS]
    print(_table(["Keyword", "Topic", "Phrases"], rows, [14, 20, 60]))
    print("\nProfiles:")
    for name, profile in PROFILES.items():
        print(f"  {name}: {len(profile.keywords)} keywords × {len(profile.languages)} languages")
    return 0


def cmd_links(args: argparse.Namespace) -> int:
    try:
        views = generate_links(args.keyword, args.language, args.window)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for view in views:
        flag = "" if view.available else " (unavailable)"
        print(f"{view.label}{flag}\n  {view.url}")
        if view.note:
            print(f"  note: {view.note}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    if args.limit < 1:
        print("error: --limit must be at least 1", file=sys.stderr)
        return 1
    settings = _settings(args)
    db = _db(settings)
    keyword = get_keyword(args.keyword)
    query = args.query or keyword.link_query(args.language)
    qualifier = _window_qualifier(args.window)
    if qualifier:
        query = f"{query} {qualifier}"
    if getattr(args, "in_readme", False) and "in:readme" not in query:
        query = f"{query} in:readme"
    if args.local:
        rows = db.search_fts(args.query or keyword.name, limit=args.limit)
        if not rows:
            print("No local matches. Run a crawl first.")
            return 0
        _print_repos(rows)
        return 0
    with _client(settings, db) as client:
        per_page = min(max(args.limit, 1), 100)
        collected = []
        page = 1
        while len(collected) < args.limit and page <= 10:
            result = client.search_repositories(
                query, sort=args.sort, order=args.order, per_page=per_page, page=page
            )
            collected.extend(result.items)
            if len(result.items) < per_page or len(collected) >= min(result.total_count, 1000):
                break
            page += 1
            per_page = min(100, args.limit - len(collected))
            if per_page <= 0:
                break
        collected = collected[: args.limit]
        if args.save:
            for repo in collected:
                db.upsert_repo(repo, keyword=keyword.slug)
        _print_repos(collected)
        print(f"\n{len(collected)} shown · GitHub total {result.total_count:,}")
        if result.rate_limit.remaining is not None:
            print(f"search rate limit remaining: {result.rate_limit.remaining}/{result.rate_limit.limit}")
    return 0


def _print_repos(repos: list[Any]) -> None:
    rows = [[r.full_name, r.language or "-", f"{r.stars:,}", f"{r.forks:,}", r.license or "-", _clip(r.description, 70)] for r in repos]
    print(_table(["Repository", "Language", "Stars", "Forks", "License", "Description"], rows, [42, 14, 10, 9, 14, 60]))


def cmd_crawl(args: argparse.Namespace) -> int:
    from .crawler import Crawler

    settings = _settings(args)
    db = _db(settings)
    with _client(settings, db) as client:
        crawler = Crawler(settings, db, client)
        if args.plan_only:
            slices = crawler.plan_profile(args.profile, in_readme=args.in_readme)
            for sl in slices:
                flag = " [overflow]" if sl.overflow else ""
                print(f"{sl.estimated_count or 0:>5}  {sl.query}{flag}")
            print(f"\n{len(slices)} slices planned. Estimated count calls: {len(slices)}.")
            return 0
        summary = crawler.run(
            args.profile,
            resume=args.resume,
            fetch_readmes=not args.no_readmes,
            discovery=args.discovery,
            max_slices=args.max_slices,
            in_readme=args.in_readme,
        )
    print(json.dumps(summary.as_dict(), indent=2))
    return 1 if summary.status == "failed" else 0


def cmd_trends(args: argparse.Namespace) -> int:
    from .trends import get_trending

    settings = _settings(args)
    db = _db(settings)
    window = _window_days(args.window)
    rows = get_trending(
        db,
        window=window,
        sort=args.sort,
        language=args.language,
        min_stars=args.min_stars,
        license=args.license,
        include_archived=args.include_archived,
        include_forks=args.include_forks,
        max_fork_ratio=args.max_fork_ratio,
        active_within_days=args.active_within,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps(_trend_export_rows(rows, window), indent=2))
        return 0
    table_rows = [
        [
            i,
            r.repo.full_name,
            r.repo.language or "-",
            f"{r.repo.stars:,}",
            f"+{r.gain(window):,}",
            "-"
            if r.relative_growth_for(window) is None
            else f"{r.relative_growth_for(window):.1f}%",
            "-" if r.acceleration_for(window) is None else f"{r.acceleration_for(window):.2f}",
            "new" if r.is_new else "",
        ]
        for i, r in enumerate(rows, start=1)
    ]
    print(_table(["#", "Repository", "Language", "Stars", f"Gain {window}d", "Growth", "Accel", ""], table_rows, [4, 42, 14, 10, 12, 9, 7, 5]))
    if not rows:
        print("\nNo rows. Crawl/backfill first: python -m github_tool crawl && python -m github_tool backfill")
    return 0


def cmd_backfill(args: argparse.Namespace) -> int:
    from .trends import backfill_star_history

    settings = _settings(args)
    db = _db(settings)
    with _client(settings, db) as client:
        stats = backfill_star_history(
            db,
            client,
            repo_ids=args.ids or None,
            weeks_back=args.weeks,
            min_stars=args.min_stars,
            progress=lambda done, total: print(f"  backfill {done}/{total}", file=sys.stderr),
        )
    print(json.dumps(stats, indent=2))
    return 1 if stats.get("errors") and stats.get("fetched", 0) == 0 else 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    from .trends import take_snapshots

    settings = _settings(args)
    db = _db(settings)
    with _client(settings, db) as client:
        count = take_snapshots(db, client, repo_ids=args.ids or None)
    print(f"Stored {count} snapshots for {utc_today().isoformat()}.")
    return 0


def _llm_complete(settings: Settings):
    import httpx

    def complete(prompt: str) -> str:
        response = httpx.post(
            settings.llm_url or "",
            headers={"Authorization": f"Bearer {settings.llm_key}", "Content-Type": "application/json"},
            json={
                "model": settings.llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

    return complete


def cmd_extract(args: argparse.Namespace) -> int:
    from .extraction import LLMExtractor, extract_for_repo

    settings = _settings(args)
    db = _db(settings)
    repos = db.list_repos(language=args.language, min_stars=args.min_stars, limit=args.limit)
    llm = None
    if args.use_llm:
        if not (settings.llm_url and settings.llm_key and settings.llm_model):
            print("error: LLM settings are incomplete (GITHUB_TOOL_LLM_URL/KEY/MODEL)", file=sys.stderr)
            return 1
        llm = LLMExtractor(_llm_complete(settings))
    client = None
    want_manifests = bool(args.manifests) and not settings.offline
    if (args.fetch_missing or want_manifests) and not settings.offline:
        client = _client(settings, db)
    processed = skipped = commands = hw = 0
    try:
        for repo in repos:
            text = repo.readme_text
            if text is None and client is not None:
                result = client.get_readme(repo.full_name)
                if result.text:
                    import hashlib

                    text = result.text
                    db.update_readme(repo.id, text, result.etag, hashlib.sha256(text.encode()).hexdigest())
            if not text:
                skipped += 1
                continue
            manifests: dict[str, str] = {}
            if want_manifests and client is not None:
                try:
                    root_files = client.repo_root_files(repo.full_name)
                except (GitHubError, RuntimeError, ValueError):
                    root_files = []
                wanted = [
                    name
                    for name in root_files
                    if re.fullmatch(r"requirements.*\.txt", name, re.IGNORECASE)
                    or name.lower() in {"pyproject.toml", "dockerfile"}
                ][:12]
                for path in wanted:
                    content = client.get_file(repo.full_name, path)
                    if content:
                        manifests[path] = content
            result = extract_for_repo(
                db,
                repo.id,
                text,
                force=args.force,
                llm=llm,
                manifests=manifests or None,
            )
            if result is None:
                skipped += 1
                continue
            processed += 1
            commands += len(result.commands)
            hw += len(result.hardware)
    finally:
        if client is not None:
            client.close()
    print(f"Extracted {processed} repos ({commands} install commands, {hw} hardware rows); skipped {skipped}.")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from .export import write_export

    settings = _settings(args)
    db = _db(settings)
    if args.trends:
        from .trends import get_trending

        window = _window_days(args.window)
        rows = _trend_export_rows(
            get_trending(
                db,
                window=window,
                sort=args.sort,
                language=args.language,
                min_stars=args.min_stars,
                limit=args.limit,
            ),
            window,
        )
        title = f"Trending {args.language or 'all languages'} · {WINDOW_LABELS.get(args.window, str(window) + 'd')}"
    else:
        rows = db.export_rows(language=args.language, min_stars=args.min_stars, limit=args.limit)
        title = "Repository index"
    if args.output:
        path = write_export(rows, args.output, fmt=args.format, title=title) if args.format in {"md", "markdown"} else write_export(rows, args.output, fmt=args.format)
        print(f"Wrote {len(rows)} rows to {path}")
    else:
        from .export import to_csv, to_markdown

        print(to_csv(rows) if args.format == "csv" else to_markdown(rows, title=title))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import os
    import uvicorn

    settings = _settings(args)
    _db(settings)
    os.environ["GITHUB_TOOL_DB"] = str(settings.db_path)
    if settings.offline:
        os.environ["GITHUB_TOOL_OFFLINE"] = "1"
    print(f"Serving GitHub-Tool at http://{args.host}:{args.port}" + (" (offline)" if settings.offline else ""))
    uvicorn.run("github_tool.web.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    from .scheduler import render_schedule

    print(render_schedule(args.format, root=args.root, python=args.python))
    return 0


def cmd_hints(args: argparse.Namespace) -> int:
    from .trends import discover_hints

    settings = _settings(args)
    db = _db(settings)
    with _client(settings, db) as client:
        repos = discover_hints(
            client,
            db,
            language=args.language,
            period=args.period,
            source=args.source,
        )
    print(f"Added {len(repos)} hint repositories.")
    for repo in repos[:20]:
        print(f"  {repo.full_name}  {repo.stars:,} stars")
    return 0


def cmd_rate_limit(args: argparse.Namespace) -> int:
    settings = _settings(args)
    with _client(settings, Database(settings.db_path)) as client:
        print(json.dumps(client.rate_limit(), indent=2))
    return 0


# ----------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default=argparse.SUPPRESS, help="Path to the SQLite database")
    common.add_argument("--offline", action="store_true", default=argparse.SUPPRESS, help="Never make network calls")

    parser = argparse.ArgumentParser(prog="github-tool", description="Discover GitHub repos by keyword and recent star growth.")
    parser.add_argument("--db", default=argparse.SUPPRESS, help="Path to the SQLite database")
    parser.add_argument("--offline", action="store_true", default=argparse.SUPPRESS, help="Never make network calls")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init-db", parents=[common], help="Create/upgrade the local database")
    p.set_defaults(func=cmd_init_db)

    p = sub.add_parser("keywords", parents=[common], help="List the keyword map")
    p.add_argument("--json", help="Write the keyword map JSON here")
    p.set_defaults(func=cmd_keywords)

    p = sub.add_parser("links", parents=[common], help="Generate link-out views (no token needed)")
    p.add_argument("keyword", help="Keyword name or slug")
    p.add_argument("--language", help="Limit links to a GitHub language (e.g. Python)")
    p.add_argument(
        "--window", default="30d", choices=["today", "7d", "30d", "90d", "365d"],
        help="Time window used in the generated search links",
    )
    p.set_defaults(func=cmd_links)

    p = sub.add_parser("search", parents=[common], help="On-demand GitHub search")
    p.add_argument("keyword", help="Keyword name or slug")
    p.add_argument("--query", help="Override the generated query")
    p.add_argument("--language", help="Limit to a GitHub language (e.g. Python)")
    p.add_argument("--window", choices=["today", "7d", "30d", "90d", "365d"], help="Restrict to a recent activity window")
    p.add_argument("--sort", default="stars", choices=["stars", "forks", "updated"], help="Sort field")
    p.add_argument("--order", default="desc", choices=["asc", "desc"], help="Sort direction")
    p.add_argument("--limit", type=int, default=30, help="Maximum results to show")
    p.add_argument("--save", action="store_true", help="Store results in the local index")
    p.add_argument("--local", action="store_true", help="Search the local FTS index instead of the API")
    p.add_argument("--in-readme", action="store_true", help="Also match keywords inside README text")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("crawl", parents=[common], help="Run or resume a crawl profile")
    p.add_argument("--profile", default="default", choices=sorted(PROFILES), help="Crawl profile to run")
    p.add_argument("--resume", help="Resume this run id")
    p.add_argument("--no-readmes", action="store_true", help="Skip README fetching")
    p.add_argument("--discovery", default="rest", choices=["rest", "graphql"], help="Discovery API for repository search")
    p.add_argument("--max-slices", type=int, help="Pause after this many slices (resume later)")
    p.add_argument("--plan-only", action="store_true", help="Print the planned slices without crawling")
    p.add_argument("--in-readme", action="store_true", help="Match keywords inside README text while discovering")
    p.set_defaults(func=cmd_crawl)

    p = sub.add_parser("trends", parents=[common], help="Show trending repos from the local index")
    p.add_argument("--window", default="7d", choices=["today", "7d", "30d", "90d", "365d"], help="Ranking window")
    p.add_argument("--sort", default="most_gained", choices=["most_gained", "fastest_growth", "accelerating", "new_rising", "stars", "updated"], help="Ranking strategy")
    p.add_argument("--language", help="Limit to a GitHub language")
    p.add_argument("--min-stars", type=int, default=50, help="Minimum stars")
    p.add_argument("--license", help="Filter by license name")
    p.add_argument("--include-archived", action="store_true", help="Include archived repos")
    p.add_argument("--include-forks", action="store_true", help="Include forks")
    p.add_argument("--max-fork-ratio", type=float, help="Exclude repos whose forks/stars ratio exceeds this value")
    p.add_argument("--active-within", type=int, help="Only include repos pushed to within this many days")
    p.add_argument("--limit", type=int, default=30, help="Maximum rows to show")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    p.set_defaults(func=cmd_trends)

    p = sub.add_parser("backfill", parents=[common], help="Backfill star history for indexed repos")
    p.add_argument("ids", nargs="*", help="Repo ids (default: candidates)")
    p.add_argument("--weeks", type=int, default=53, help="Weeks of star history to backfill")
    p.add_argument("--min-stars", type=int, default=50, help="Minimum stars for candidate repos")
    p.set_defaults(func=cmd_backfill)

    p = sub.add_parser("snapshot", parents=[common], help="Take today's star snapshots via GraphQL")
    p.add_argument("ids", nargs="*", help="Repo ids (default: all indexed repos)")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("extract", parents=[common], help="Extract install commands and hardware requirements")
    p.add_argument("--limit", type=int, default=100, help="Maximum repos to process")
    p.add_argument("--min-stars", type=int, default=0, help="Minimum stars for candidate repos")
    p.add_argument("--language", help="Limit to a GitHub language")
    p.add_argument("--force", action="store_true", help="Re-extract even unchanged READMEs")
    p.add_argument("--fetch-missing", action="store_true", help="Fetch READMEs that are not in the DB")
    p.add_argument("--manifests", action="store_true", help="Also fetch requirements/pyproject/Dockerfile hints")
    p.add_argument("--use-llm", action="store_true", help="Run the optional LLM extraction pass")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("export", parents=[common], help="Export CSV or Markdown")
    p.add_argument("--format", default="csv", choices=["csv", "md", "markdown"], help="Output format")
    p.add_argument("--output", help="Write to this file instead of stdout")
    p.add_argument("--language", help="Limit to a GitHub language")
    p.add_argument("--min-stars", type=int, default=0, help="Minimum stars")
    p.add_argument("--limit", type=int, default=1000, help="Maximum rows to export")
    p.add_argument("--trends", action="store_true", help="Export the trend ranking instead of the repo index")
    p.add_argument("--window", default="7d", choices=["today", "7d", "30d", "90d", "365d"], help="Ranking window for trend exports")
    p.add_argument("--sort", default="most_gained", choices=["most_gained", "fastest_growth", "accelerating", "new_rising", "stars", "updated"], help="Ranking strategy for trend exports")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("serve", parents=[common], help="Run the local web UI")
    p.add_argument("--host", default="127.0.0.1", help="Bind address")
    p.add_argument("--port", type=int, default=8000, help="Bind port")
    p.add_argument("--reload", action="store_true", help="Auto-reload on source changes (development only)")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("schedule", parents=[common], help="Print scheduler snippets")
    p.add_argument("--format", default="cron", choices=["cron", "systemd", "github-actions"], help="Snippet format")
    p.add_argument("--root", default=".", help="Installed project path on the target host")
    p.add_argument("--python", default="python", help="Python executable on the target host")
    p.set_defaults(func=cmd_schedule)

    p = sub.add_parser("hints", parents=[common], help="Discover hint repos from OSS Insight and GitHub Trending")
    p.add_argument("--language", help="Limit Trending to a GitHub language")
    p.add_argument(
        "--period",
        default="past_week",
        choices=("past_24_hours", "past_week", "past_month", "past_3_months"),
        help="Trending period",
    )
    p.add_argument("--source", default="all", choices=("all", "oss", "trending"), help="Hint source")
    p.set_defaults(func=cmd_hints)

    p = sub.add_parser("rate-limit", parents=[common], help="Show GitHub rate limits")
    p.set_defaults(func=cmd_rate_limit)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    from .logging import configure_logging

    configure_logging()
    try:
        return int(args.func(args))
    except (GitHubError, OfflineError, ValueError, KeyError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
