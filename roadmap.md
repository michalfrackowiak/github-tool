# GitHub-Tool — Build Roadmap

**Status:** Phases 0–10 implemented and validated. One item remains operator-only (creating a fine-grained read-only token); an independent human spot-check of extraction is optional — an agent semantic review covered all 190 extracted commands. Every other checkbox below is complete. Seven independent reviewer passes plus a maintainer self-review are recorded in `docs/review-fixes.md`; 200 tests pass with no skips/xfails. **Approach:** link-out views for instant answers first (Phases 0–1), then a local index and crawler for offline use and trend windows (Phases 2–7). Full background, architecture, and constraints: see `context.md`.

| Phase | Focus | Estimate |
|---|---|---|
| 0 | Validate | ½ day |
| 1 | Link-out MVP | ~1 day |
| 2 | On-demand API search | 2–3 days |
| 3 | Local index & crawler | 3–5 days |
| 4 | Trend engine | 3–4 days |
| 5 | UI & export | 2–3 days |
| 6 | Install commands & hardware requirements | 3–5 days |
| 7 | Hardening | ~2 days |

## Phase 0 — Validate (½ day)

- [x] Open the linkable views (search, trending, topics, OSS Insight) in a browser to confirm the URL patterns still hold. — HTTP 200 verified for all four; browser click-through is optional.
- [ ] Create a read-only GitHub token. — **Operator action**; validation used an existing `gh` token. Steps are in `docs/phase0-validation.md`.
- [x] Call search, star history, and OSS Insight once each; log the rate-limit response headers. — See [`docs/phase0-validation.md`](docs/phase0-validation.md).
- [x] Pin the star-history endpoint's API version header (`2026-03-10`). — Verified in live response headers.
- [x] Prototype queries with `gh search repos` (topic, language, sort, created, JSON output). — Verified.
- [x] Build the keyword map: map generic terms ("DB", "API") to a `topic:` qualifier plus one or two phrases; run one query per variant and per selected language, then merge locally. — All 12 keywords count-tested for Python; see `docs/keyword-tests.json`.

**Done when:** every predefined keyword has a tested query and you know the per-call costs. — Met; exhaustive per-language counts belong to the crawl itself.

## Phase 1 — Link-out MVP (~1 day)

- [x] Build keyword chips, language checkboxes, and a time-window selector.
- [x] Generate the GitHub search URL (with date qualifiers).
- [x] Generate the Trending URL for daily/weekly/monthly.
- [x] Generate the OSS Insight link for 24h/week/month/3 months.
- [x] For "last year", fall back to the `created:` search link.
- [x] No token or database needed yet.

**Done when:** one click opens the right view for any combination. — Met and unit-tested.

## Phase 2 — On-demand API search (2–3 days)

- [x] Build a REST search client with token auth.
- [x] Add backoff on 403/429. — Includes HTTP-date `Retry-After` and rate-limit reset handling.
- [x] Add an ETag cache. — Applied on endpoints that return ETags; GitHub search itself does not.
- [x] Add a results table sortable by stars, forks, or updated date.
- [x] Fetch the README lazily on click.

**Done when:** typical queries return in seconds and a normal session never hits a rate limit. — Met; min-interval pacing, backoff, and ETag/304 reuse are covered by tests and live validation.

## Phase 3 — Local index and crawler (3–5 days)

- [x] Build the schema (see `context.md`). — Includes additive migrations and FTS5 triggers.
- [x] Build a query planner that slices by date or star ranges. — Bounded count budget, overflow flags, explicit `stars:0..N` qualifiers.
- [x] Define crawl profiles (keyword set × languages).
- [x] Add resumable runs with checkpoints. — REST pages and GraphQL cursors persist; wedge-at-limit fixed.
- [x] Dedupe by repo ID. — Renames/new owners handled without unique-name conflicts.
- [x] Fetch READMEs only when new or changed (via ETag).
- [x] Add full-text search (FTS) over READMEs.
- [x] Add an offline mode that reads only from the local DB.
- [x] Once stable, move discovery to GraphQL (100 repos + stats per call). — Optional `--discovery graphql` mode with checkpointed cursors.

**Done when:** a full crawl profile runs unattended, can be stopped and resumed, and the app works with the network off. — Verified live with a paused/resumed smoke profile.

## Phase 4 — Trend engine (3–4 days)

- [x] Backfill star history for candidates, skipping archived repos, forks, and tiny repos.
- [x] Take daily snapshots via batched GraphQL so the system doesn't depend on a single endpoint.
- [x] Compute star gains for 1/7/30/90/365-day windows. — Incomplete daily coverage is no longer presented as a complete window.
- [x] Offer sorts: most gained; fastest relative growth; accelerating (7-day rate vs. 30-day rate); "new & rising" (created within 90 days). — Sorts now use the requested window.
- [x] Use OSS Insight and Trending only as discovery hints for repos the keyword search missed. — OSS Insight adapter degrades gracefully; Trending has no stable API, so its HTML is parsed by `hints --source trending` (15 live Python hints stored). Neither source is ranked.

**Done when:** your 7-day view for a language roughly agrees with OSS Insight's. — **Deviation:** OSS Insight ranking unavailable since 2026-03-01; cross-checked against GitHub star-history sums instead. See `docs/live-validation.md`.

## Phase 5 — UI and export (2–3 days)

- [x] Build a local web UI or TUI. — FastAPI + Jinja2, no CDN.
- [x] Add saved searches. — POST/DELETE now handle names containing `/`.
- [x] Add CSV/Markdown export. — Formula injection neutralized; exports honor displayed filters.
- [x] Add a per-repo page with README and a star-history sparkline. — Includes snapshot fallback and lazy README revalidation.
- [x] Add filters for min stars, license, archived, and forks. — On both Trends and Search.

**Done when:** "what's hot in Rust + LLM this week" takes seconds, offline. — Verified with a TestClient against the live crawl DB in offline mode.

## Phase 6 — Install commands and hardware requirements (3–5 days)

- [x] Extract from the README, and optionally Dockerfile/pyproject/requirements files. — `extract --manifests` fetches and persists hints; live-checked on `Graphify-Labs/graphify`.
- [x] Use heuristics for code fences under "Install" or "Quickstart" headings.
- [x] Add an LLM pass with a strict JSON schema for remaining cases. — Mock-tested; no live LLM key was configured.
- [x] Store each extracted item with its source line and a confidence flag. — 190/190 live command lines verified against their README line.
- [x] Re-run extraction only when the README hash changes. — Requires both matching hash and `extracted_at`, so crawler-written hashes do not suppress first extraction.
- [x] Semantically review a sample of extracted commands. — All 190 commands across 47 repos were reviewed with `scripts/audit_extraction.py`; 6 template commands were filtered and 4 multi-line commands joined.
- [ ] Independent human spot-check of ~50 repos. — **Optional human action** for business-critical use; the agent review is recorded in `docs/extraction-validation.md`. A ready-to-tick review packet (46 repos / 184 commands) is generated at [`docs/extraction-spotcheck.md`](docs/extraction-spotcheck.md) via `scripts/make_spotcheck.py`; only the human sign-off remains.

**Done when:** a hand-check of ~50 repos looks trustworthy. — Automated line check 190/190 and recorded agent semantic review; see `docs/extraction-validation.md`.

## Phase 7 — Hardening (~2 days)

- [x] Add a scheduler (cron or systemd). — Also GitHub Actions with DB cache restore.
- [x] Add tests against recorded API fixtures. - 200 tests pass; `httpx.MockTransport` fixtures cover retry/backoff, ETag/304, README, star history, GraphQL, OSS Insight, and Trending HTML.
- [x] Add logging and token hygiene. — Token redaction, `Settings` repr excludes secrets, httpx noise suppressed.
- [x] If scheduling via GitHub Actions, use a PAT — the built-in `GITHUB_TOKEN` is capped at 1,000 requests/hour/repository. — `secrets.GH_TOOL_TOKEN` with an explicit warning.
- [x] Add a short doc of rate limits and policy rules for future reference. — `docs/rate-limits.md`.

## Phase 8 — Improvements and extensions

Derived from gaps and risks in `context.md` that were not needed for Phases 0–7. Each task has a regression test; the phase is done only when all boxes below are checked and the full suite is green.

- [x] Add `in:readme` as an opt-in qualifier for CLI search and crawls, so keyword matching can include README text as described in the search-scope constraint. — `--in-readme` on `search` and `crawl`; planner propagates the qualifier through every slice.
- [x] Add a cheap inflated-star sanity filter: optional max fork/star ratio on trend ranking (CLI + web + exports), defaulting to no filtering. — `--max-fork-ratio` / `max_fork_ratio`, with `fork_ratio` added to exports.
- [x] Add a web JSON export endpoint sharing the same filters as the CSV/Markdown exports, for offline analysis. — `/export.json`, linked from the search and trends views.
- [x] Verify index usage for bulk trend reads and add indexes only where a scan remains. — `EXPLAIN QUERY PLAN` shows both bulk queries using the existing `(repo_id, day)` primary-key indexes on `star_daily` and `snapshots`; no redundant index added.
- [x] Document the new options and refresh validation/test-count evidence. — README CLI table/examples, `docs/live-validation.md` Phase 8 section, with counts kept current (200 tests after Phase 10).

**Done when:** all Phase 8 boxes are checked and the full pytest suite passes with no skipped/xfailed tests.

## Phase 9 — Search parity and activity signal

- [x] Add an `in:readme` checkbox to web search for API-source queries, matching the CLI/crawl option. — Preserved in sort and export links.
- [x] Add an optional "active within N days" filter to trend ranking (CLI + web + exports) based on each repo's `pushed_at`, as a cheap real-activity proxy. — `--active-within` / `active_within`.
- [x] Add regression tests and update user-facing docs for both options. — 200 tests pass; README and validation notes updated.

**Done when:** all Phase 9 boxes are checked and the full pytest suite passes with no skipped/xfailed tests.

## Phase 10 — Fork search scope

GitHub excludes forks from repository search unless `fork:true` is present; the previous "Include forks" option only post-filtered results, so it could never surface forks from the API.

- [x] Add `include_forks` to the planner and crawler so `fork:true` reaches every generated slice. — `compose_query()` / `plan_slices()` / `Crawler.plan_profile()` / `Crawler.run()`.
- [x] Add `--include-forks` to CLI `search` and `crawl`, appending `fork:true` to API queries. — Web search now adds the same qualifier when the checkbox is checked.
- [x] Add regression tests and update docs. — 200 tests pass; README and validation notes updated.

**Done when:** all Phase 10 boxes are checked and the full pytest suite passes with no skipped/xfailed tests.
