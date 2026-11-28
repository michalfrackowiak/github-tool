# Live end-to-end validation

*Run 2026-11-24 on Windows, Python 3.14.8, authenticated with the existing `gh` token. Temporary databases under `%TEMP%`; no token values were printed.*

## Summary

| Phase | Check | Result |
|---|---|---|
| 1 | Link-out patterns | Search / Trending / Topic / OSS Insight URLs return HTTP 200 |
| 2 | REST search + ETag | 5-result RAG/Python search; README 200 then 304 with ETag |
| 3 | Crawl + resume | “smoke” profile (RAG × Python, ≥5,000 stars): first run paused after 1 slice, resume completed all 3 slices; 64 repos, 60 READMEs |
| 4 | Backfill + snapshots + trends | 60 repos backfilled (3,420 daily rows, 0 errors), 60 snapshots stored, trend table computed |
| 5 | UI + export | All pages 200 with real data; repo page had install command + sparkline; CSV/Markdown export |
| 4 | Trending discovery hints | GitHub Trending HTML collector fetched 15 Python repos; GraphQL `repo_stats` enriched and stored all 15 |
| 6 | Extraction | 60 READMEs → 190 commands, 727 hardware rows (154 numeric); 190/190 command lines matched their source line; all 190 commands semantically reviewed |
| 6 | Manifest hints | Live `extract --manifests` stored 31 dependency hints and 1 Docker image for `Graphify-Labs/graphify` |
| 7 | Tests / scheduler / logging | 235 pytest tests pass; scheduler snippets render; `httpx` noise suppressed and token redaction active |

## Phase 1 — links

The four roadmap patterns were already confirmed in [`phase0-validation.md`](phase0-validation.md). The generated link for 365 days now contains exactly one language qualifier and a `created:>=YYYY-MM-DD` fallback:

```text
https://github.com/search?q=topic%3Arag+created%3A%3E%3D2025-11-24+language%3APython&type=repositories&s=stars&o=desc
```

## Phase 2 — on-demand search and ETag

- `search_repositories("topic:rag language:Python", per_page=5)` → total 43,093; search budget 30/min.
- README fetch for the first result: 43 KB, ETag present.
- Repeat README fetch with `If-None-Match` → HTTP 304 (`not_modified=True`), preserving local text.
- GraphQL `repo_stats` returned live stars for two repos in one call.
- Rate snapshot after the run: core 4,989/5,000, search 27/30, GraphQL 4,992/5,000.

Note: GitHub's REST **search** endpoint does not send an `ETag`, so search responses cannot be revalidated with 304s. The ETag cache applies where GitHub provides ETags (READMEs, star history, and other conditional endpoints). Rate limiting/backoff remains the protection for search.

## Phase 3 — resumable crawl

A temporary profile `smoke` was injected for the test: keyword `rag`, language `Python`, `min_stars=5000`, READMEs enabled.

| Run | Status | Slices | Pages | Repos seen | Inserted | READMEs | Not modified |
|---|---|---|---|---|---|---|---|
| First (`--max-slices 1`) | paused | 1/3 | 1 | 62 | 62 | 62 | 0 |
| Resume | completed | 3/3 | 2 | 10 | 2 | 2 | 8 |

- Same numeric repo ID appearing in later slices was deduplicated (2 new inserts from 10 hits).
- 8 unchanged READMEs returned 304 and kept their text.
- 64 repos stored; 60 had READMEs (four 404s).
- Offline local FTS query (`"agents"`) returned matches with no network client.

## Phase 4 — trend engine

- `backfill --min-stars 5000 --weeks 8`: 60 requested, 60 fetched, 3,420 daily rows, 0 errors.
- `snapshot`: 60 rows stored for 2026-11-24 via one batched GraphQL call.
- Top 7-day rows (all languages):

| # | Repo | Stars | +7d | Relative | Accel |
|---|---|---|---|---|---|
| 1 | Graphify-Labs/graphify | 152,961 | 3,285 | 2.19% | 0.78 |
| 2 | HKUDS/DeepTutor | 62,285 | 2,128 | 3.54% | 0.47 |
| 3 | bojieli/ai-agent-book | 59,828 | 1,267 | 2.16% | 1.32 |
| 4 | headroomlabs-ai/headroom | 80,770 | 871 | 1.11% | 1.17 |
| 5 | Shubhamsaboo/awesome-llm-apps | 145,598 | 686 | 0.47% | 1.02 |

Cross-check: a direct sum of the star-history daily gains for Graphify-Labs/graphify over the same 7-day window gave 3,284 vs the engine's 3,285 (one-day boundary/partial-day difference).

**Deviation:** the roadmap's done-when was “your 7-day view for a language roughly agrees with OSS Insight's.” OSS Insight's event-derived ranking has been unavailable since 2026-03-01, so this comparison is impossible today. The engine was cross-checked against the underlying GitHub star-history sums instead. OSS Insight remains an optional adapter that degrades to an empty hint list.

**Discovery hints:** because OSS Insight is unavailable, `hints --source trending --language Python --period past_week` was added. It parsed 15 `owner/repo` links from `https://github.com/trending/python?since=weekly` (HTTP 200, matching the regex-parsed names), enriched them with one GraphQL `repo_stats` call, and stored 15 hint repos in a temporary DB. `--source all|oss|trending` selects the source; failures degrade to an empty list.

## Phase 5 — UI and export

Using a `TestClient` with the live crawl database in offline mode:

| Route | Status |
|---|---|
| `/` | 200 |
| `/links?keyword=rag&language=Python&window=7d` | 200 |
| `/search?keyword=rag&source=local&window=7d` | 200 |
| `/trends?window=7d&min_stars=5000` | 200 |
| `/repo/Graphify-Labs/graphify` | 200 |
| `/export.csv?trends=1&window=7d&min_stars=5000` | 200 |
| `/health` | 200 |

The repo page contained the extracted `pip install graphifyy` command and an inline SVG sparkline. CSV and Markdown exports produced the expected trend rows.

## Phase 6 — extraction

See [`extraction-validation.md`](extraction-validation.md) for method and limitations. Headline: 60 READMEs, 190 commands (47 repos with at least one), 727 hardware rows of which 154 carry a numeric/GPU value, a 100% source-line match check, and a semantic review of all 190 commands (6 template placeholders removed, 4 multi-line commands joined). A live `extract --manifests` run on a copy of the crawl DB stored 31 dependency hints and one Docker base image for `Graphify-Labs/graphify`; the repo page renders them.

## Phase 7 — hardening

- Pytest suite: **235 tests pass, 0 skipped/xfailed**. Coverage includes recorded-style API fixtures with `httpx.MockTransport` (304 reuse, 429 backoff, `Retry-After`, GraphQL errors, OSS Insight unavailable, Trending HTML parsing), CLI, web UI, planner, crawler resume, trends, extraction, export, scheduler, and logging redaction, plus regressions for every reviewer finding listed in [`review-fixes.md`](review-fixes.md).
- `github_tool/logging.py` redacts the token and `Authorization: Bearer` values; `httpx`/`httpcore` loggers are quieted at default verbosity.
- `schedule --format cron|systemd|github-actions` prints copy-pasteable snippets. The Actions variant restores the SQLite database with `actions/cache` and uses a PAT secret.
- Token hygiene: tokens come only from the environment, are excluded from `Settings.__repr__`, never appear in URLs, and are not printed by the validator.

## Phase 8 — improvements and extensions

- `search --in-readme` and `crawl --in-readme` add GitHub's `in:readme` qualifier; the planner carries it through every emitted slice, including split/overflow slices.
- Trend ranking accepts an optional fork/star sanity filter (`--max-fork-ratio` / `max_fork_ratio`) and exports a `fork_ratio` column. Default behaviour is unchanged (no filtering).
- `/export.json` returns the same filtered rows as `/export.csv` and `/export.md`; both search and trends pages link to all three formats.
- `EXPLAIN QUERY PLAN` on the bulk trend queries shows both use the existing `(repo_id, day)` primary-key indexes, so no redundant index was added.
- The final reviewer pass found one local-search inconsistency: the archived/fork checkboxes were parsed but not passed to `Database.list_repos` in the language-browse path. Fixed with a regression test.

## Phase 9 — search parity and activity signal

- Web search now exposes the same "Match README text" option as the CLI/crawl `--in-readme` flag; the qualifier is added to API-source queries and preserved in sort/export links.
- Trend ranking accepts `--active-within N` / `active_within=N`, filtering repos whose `pushed_at` is older than N days. It is a cheap activity proxy and is applied to the table and all three export formats.
- Seventh review pass: README-text matching is now applied consistently to the local search page and CSV/JSON exports, and to saved searches; non-finite `--max-fork-ratio` values are rejected instead of silently emptying results.

## Phase 10 — fork search scope

GitHub excludes forks from repository search unless `fork:true` is added (confirmed against the current GitHub search docs). The pre-existing "Include forks" option only post-filtered results, so it could never surface forks from the API. `--include-forks` on `search`/`crawl` and the web checkbox now add `fork:true` to every generated API query, including planner slices.

## Phase 11 — auto-saved searches and web crawl trigger

- Schema version 2 adds `search_history` and `crawl_jobs`. Named `saved_searches` stay unique and user-controlled; automatic history is separate so replays cannot clobber a manual save. `normalize_search_params()` allowlists and trims the query, keyword, window, source, language(s), sort, limit, min stars, license, archived/fork/README flags, and README query.
- Both `/search` and CLI `search` append a replayable entry for every executed search, including failed API searches recorded with zero results; writes are best-effort so a history failure never hides results. CLI local searches store the effective FTS text as `q` and omit the unused language filter; explicit API queries store the effective window qualifier because web replay skips that qualifier when `q` is present. `/saved` renders the last 20 entries with replay and clear-history actions.
- `POST /crawl` starts a bounded background job (max 5 slices, 3 pages per slice, allowlisted profiles/discovery, no host/proxy/token inputs). Offline requests return 503, invalid options 400, and a second concurrent request 409. `/crawl` auto-refreshes while a job is active and `/crawl/status/{job_id}` exposes phase, run, slice counts, summary, and error.
- The worker calls the same `Crawler.run()` as the CLI and writes through the app's `Database` path, so `Crawler._store_repo()` upsert(s) each discovered repo immediately (deduped by numeric GitHub ID). `CrawlSummary` now reports inserted, updated, and README counts. The crawler reports its run id to the job as soon as the run is created, the worker heartbeats every 60 seconds, and setup/dispatch failures are persisted as job errors. Stale jobs are reaped at startup and claim time so a killed worker cannot permanently block the single-flight slot.
- Verified offline with `TestClient`: history auto-save/replay/clear, offline and busy rejections, job status flow, and a fake worker that writes a repo through the app database before the job completes.
- A live bounded crawl was also driven through `POST /crawl` against a temporary DB using a one-keyword/one-language smoke profile: HTTP 303 to a job, then status `paused` (expected because only 1 of 2 planned slices was allowed), `pages_fetched=1`, `repos_seen=62`, `repos_inserted=62`, `error=null`, and 62 repos plus one keyword link present in SQLite. The token was read from `gh auth token` inside that process and never printed. The same crawler path was validated at full scale earlier by run `bfa59f1029f54b479728ee9db6c625ef` (`ai` profile, 173/173 slices, 9,538 repos inserted, 9,574 READMEs fetched); no second DB writer was introduced.
- Suite: **235 tests pass, 0 skipped/xfailed; 87% coverage**.

## Remaining operator actions

1. Create a fine-grained, public read-only token (Contents + Metadata read) instead of the broad `gh` scopes used for validation.
2. Treat OSS Insight and Trending as optional hints; both can be unavailable or empty.
3. If you need independent semantic confidence in Phase 6, hand-review a sample of extracted commands beyond the recorded agent review and source-line check (the LLM pass is implemented and tested with mocks, but no LLM key was configured for this run). The reproducible review aid is `python scripts/audit_extraction.py --db <db> --limit 50`.
