# Rate Limits and Policy Reference

*Snapshot for GitHub-Tool. Budgets are per token (or per IP when unauthenticated) and can change — trust the `X-RateLimit-*` response headers at runtime, not this table.*

## Primary limits

| Resource | Authenticated | Unauthenticated | Notes |
|---|---|---|---|
| REST core | 5,000 req/hour | 60 req/hour | Repo metadata, READMEs, star history, contents |
| REST search | 30 req/min | 10 req/min | Also capped at **1,000 results per query** |
| GraphQL | 5,000 points/hour | — (token required) | Secondary: 100 concurrent requests, 900 points/min |
| OSS Insight (third party) | 600 req/hour/IP | 600 req/hour/IP | Currently returning no trend data; keep optional |

Headers to record: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Used`, `X-RateLimit-Reset` (Unix seconds), `X-RateLimit-Resource` (e.g. `core`, `search`, `graphql`).

Conditional requests that return **304 Not Modified do not count** against the primary limit when authenticated. Always send `If-None-Match` with a stored ETag for READMEs and other stable resources — it saves both bandwidth and quota.

`403`/`429` responses should back off using `Retry-After` when present, otherwise until `X-RateLimit-Reset`. The client (`github_tool/github.py`) already does this with a retry cap.

## Star history

`GET /repos/{owner}/{repo}/stargazers/history` returns weekly buckets of seven daily gain counts, newest first, 30 weeks per page.

- **1–2 core calls per repo** covers every window up to one year (1/7/30/90/365 days). Use only page 1 for short windows; page 2 (or more) only for long history.
- Works without auth for public repos, but then it draws from the 60/hour unauthenticated core budget. Use a token for any real backfill.
- Pin `X-GitHub-Api-Version: 2026-03-10`.
- The old stargazers list is restricted to admins/collaborators; do not build on it.

## Crawl slicing math

REST search stops at 1,000 results per query, so a keyword × language pair must be sliced by star range and/or `created:` dates.

- One slice = **1 count call** (`per_page=1`) + **1 page call per 100 results**, so a full 1,000-result slice costs about **10–11 search calls**.
- At 30 search requests/min, that is roughly **3 slices/min** (~180 slices/hour), minus time for README/core calls.
- Each slice is checkpointed independently, so a crawl can pause and resume without redoing counts.
- GraphQL discovery returns up to 100 repos + stats per call (one rate-limit point); migrating stable discovery to GraphQL cuts REST search pressure roughly tenfold.
- A ~10k-repo first backfill is roughly 2–4 hours of budget; daily refreshes are cheap if batched ~100 repos per GraphQL query.

## Policy notes

GitHub distinguishes API collection from scraping and prohibits excessive automated bulk activity. GitHub-Tool therefore:

- Goes **API-first** for repository data, READMEs, and star history.
- Uses link-out views (search/trending/topics) as browser destinations, not as a scraping target.
- Treats Trending as optional and fetches it at most a few times per day; it has no keyword filter and no documented API.
- Keeps OSS Insight optional and currently disabled; an empty response means its metric is unavailable, not that no repos exist.
- Fetches READMEs only when new or when the ETag changes, and never mirrors GitHub wholesale.

## Token hygiene

- Use a **fine-grained, public read-only** token: Metadata read-only + Contents read-only. No write scopes.
- Supply it through `GITHUB_TOKEN` or `GH_TOKEN` in the environment; never commit it, print it, or place it in URLs.
- Never log request headers (`Authorization` must stay out of diagnostics). `Settings.redacted()` and the validation script emit only safe fields.
- Rotate/revoke tokens on a schedule and immediately if leaked. Use a separate token per machine/automation.
- **GitHub Actions:** the built-in `GITHUB_TOKEN` is capped at **1,000 requests/hour/repository**. For scheduled crawls, use a PAT instead. Never echo the token in workflow logs.

## Re-checking

Run `scripts/validate_phase0.py` (optionally with `--json docs/phase0-results.json`) to capture current status codes and rate-limit headers. It prints headers only — never credentials.
