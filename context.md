# GitHub-Tool — Project Context

*Reference context for building GitHub-Tool. Pair with `roadmap.md` for the phased build plan.*

## Overview

GitHub-Tool is an application for discovering GitHub repositories by keyword, ranked by popularity (stars, etc.), with support for both quick on-demand lookups and a longer background crawl that builds a local database for offline use. The core challenge: nothing on GitHub natively reports "stars gained in the last N days" for a keyword — that has to be computed from your own data.

## Goals & Requirements

**Search**
- Predefined keyword set (e.g. `RAG`, `DB`, `LLM`, `API`, etc.)
- Language filter checkboxes: Python, JavaScript, Go, Rust, C, C++, Java, PHP, etc.
- On-demand search for immediate results.
- A longer-running crawl mode that populates a local database for later offline use.

**Data stored (v1)**
- Repository URL
- `README.md` contents
- Basic statistics (stars, forks, language, etc.)

**Planned for later versions**
- Install commands extracted from each repo.
- Hardware requirements extracted from each repo.

**Display / ranking**
- "Most popular" time windows: today, last 7 days, last 30 days, last 90 days, last year.
- Surfacing the most trendy / "cutting-edge" repos — not just the ones with the most total stars.

## Key Research Findings

1. GitHub shipped a **star-history endpoint** in October 2026 that makes exact time windows (7/30/90/365 days) cheap to compute per repo.
2. The old **stargazers list is now restricted** to admins/collaborators, so rebuilding star history from it no longer works — the star-history endpoint is the practical replacement.

**Recommended approach:** a hybrid of (a) link-out views for instant answers, and (b) a local index for offline use and trend windows.

> These URL patterns come from GitHub's docs and from tools that already use them, not from opening github.com directly during this research. Roadmap Phase 0 includes a quick manual check to confirm they still hold.

## Views You Can Link To (no crawling needed)

| View | URL pattern | Time windows | Keyword filter | Notes |
|---|---|---|---|---|
| GitHub Search, sorted by stars | `https://github.com/search?q=<keyword>+language:<lang>&type=repositories&s=stars&o=desc` | `created:>YYYY-MM-DD` (new repos) / `pushed:>YYYY-MM-DD` (active repos) — ISO dates, ranges supported | Yes | Best link-only answer for "cutting edge," but ranks by total stars, not recent growth. (Existing third-party GitHub search CLIs build links with these same params.) |
| GitHub Trending | `https://github.com/trending/<language>?since={daily, weekly, monthly}` | Daily / weekly / monthly only | No | No 90-day or 1-year view, no documented API; third-party scrapers see only ~12–25 repos/list and it sometimes returns empty |
| GitHub Topic pages | `https://github.com/topics/<topic>?l=<language>` | None | Tag-based | Good for curated lists like `rag` or `llm` |
| OSS Insight (3rd party) | `https://api.ossinsight.io/v1/trends/repos/?period=past_week&language=Python` | 24h / week / month / 3 months (daily recompute) | No | No auth needed; capped at 600 req/hour/IP; still in beta; no 1-year window |

## Constraints That Shape the Design

**Search cap** — REST search returns at most 1,000 results per query. Authenticated search is limited to 30 requests/minute (10 unauthenticated). A crawl must slice each keyword/language query by `created:` or star ranges to stay under 1,000 results — about 10 calls per slice, roughly 3 slices/minute.

**Search scope** — By default only name, description, and topics are searched; matching inside the README requires `in:readme`. Forks are excluded unless `fork:true` is added.

**Star windows** — The stargazers list is now limited to admins/collaborators. The replacement, `GET /repos/{owner}/{repo}/stargazers/history`, returns up to 30 weeks of daily star counts per request with no identities, and works without auth for public repos (day/week boundaries aren't guaranteed to match UTC exactly). 7/30/90-day windows cost one call per repo; a full year costs two.

**Rate budget** — Unauthenticated: 60 requests/hour. With a token: 5,000/hour. GraphQL has its own 5,000 points/hour, with secondary limits of 100 concurrent requests and 900 points/minute. Authenticated conditional requests that return 304 don't count against the primary limit. A first backfill of ~10k repos costs roughly 2–4 hours of budget; daily refreshes are cheap if batched ~100 repos per GraphQL query.

**Policy** — GitHub treats scraping and API collection as different things, and prohibits excessive automated bulk activity. Go API-first, and treat Trending as optional, fetched only a few times a day.

## Architecture (v1)

Four parts: **collectors**, a **store**, a **trend engine**, and a **UI**.

- Default stack: Python (`httpx`, SQLite with FTS5, FastAPI + HTMX).
- Alternative: Go, if a single binary is preferred.
- SQLite keeps offline use trivial; move to Postgres later if concurrent writers are needed.
- Key repos on the numeric GitHub repo ID, not the URL — repos get renamed.

```
repos(id PK = GitHub numeric id, full_name, url, language, topics, created_at, pushed_at,
      archived, fork, stars, forks, readme_text, readme_etag, fetched_at)
star_daily(repo_id, day, stars_gained)      -- from the star-history endpoint
snapshots(repo_id, day, stars, forks)       -- your own daily counts (fallback)
repo_keywords(repo_id, keyword)
crawl_runs(id, profile, started_at, finished_at, cursor, status)
crawl_jobs(id, run_id, profile, params, status, phase, summary, error, created_at, updated_at)
saved_searches(name UNIQUE, params)                 -- user-named, unchanged
search_history(params, source, result_count, created_at) -- automatic, replayable
-- v2: install_commands(repo_id, cmd, source_line, confidence)
--     hw_requirements(repo_id, gpu, vram_gb, ram_gb, disk_gb, os, source_line, confidence)
```

The UI keeps search *definitions* in `search_history` (never a second copy of result repos) and starts bounded, single-flight crawls in the background through the same `Crawler.run()` as the CLI. It is intended for loopback use unless authentication is added.

## Risks to Watch

- The star-history endpoint is only ~6 weeks old, and OSS Insight is a third-party beta — keep each behind an adapter, with your own snapshots as fallback.
- Treat "today" as approximate: calendar boundaries and removed stars still affect what the endpoint returns.
- Star counts can be inflated — later, add cheap sanity filters (fork/star ratio, contributor count, real commit activity).
- READMEs carry their repos' licenses — fine for a personal local index, but check before sharing the database with others.
