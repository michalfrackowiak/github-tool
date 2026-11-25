# GitHub-Tool

Discover GitHub repositories by keyword and rank them by popularity **and recent star growth**. GitHub does not natively report "stars gained in the last N days" for a keyword, so GitHub-Tool combines instant link-out views with a local index and its own star-history data.

- **Phases 0–10 implemented** — link-out MVP, on-demand API search, resumable crawler, trend engine, web UI/export, extraction, hardening, README-search parity, activity/inflation sanity filters, and fork-inclusive search are in place. Phase 0 evidence is in [`docs/phase0-validation.md`](docs/phase0-validation.md); live end-to-end checks are in [`docs/live-validation.md`](docs/live-validation.md).
- **Known caveats** — OSS Insight's trend ranking is unavailable (since 2026-03-01; GitHub Trending is used as the live hint source instead); a read-only token still needs to be created by the operator; README extraction is line-verified and semantically reviewed, but an independent human spot-check is still recommended for business-critical use. See [`docs/extraction-validation.md`](docs/extraction-validation.md). Review outcomes are in [`docs/review-fixes.md`](docs/review-fixes.md).

## Quickstart (Windows / PowerShell)

```powershell
cd C:\r\github-tool
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"

# Public data works without a token; set one for the 5,000/hr budget.
$env:GITHUB_TOKEN = "<fine-grained, public read-only token>"

# Offline smoke test: regenerates docs/keyword-map.json only.
python scripts\validate_phase0.py --skip-network
```

Run the live Phase 0 checks (four link patterns, one search, one star-history call, one OSS Insight call):

```powershell
python scripts\validate_phase0.py --json docs\phase0-results.json
```

The script never prints the token or `Authorization` header, and writes the keyword map from code on every run.

## Configuration

The app reads the **process environment**. `.env.example` is a template only — there is no automatic `.env` loader.

| Variable | Purpose | Default |
|---|---|---|
| `GITHUB_TOKEN` / `GH_TOKEN` | API token; optional for public data | unset |
| `GITHUB_TOOL_DB` | SQLite database path | `~/.github-tool/github-tool.db` |
| `GITHUB_TOOL_OFFLINE` | `1` disables all network access | unset |
| `GITHUB_TOOL_LLM_URL` | OpenAI-compatible endpoint for extraction | unset |
| `GITHUB_TOOL_LLM_KEY` | LLM API key | unset |
| `GITHUB_TOOL_LLM_MODEL` | LLM model name | unset |

Recommended token: fine-grained PAT, **Public Repositories (read-only)**, with Metadata read-only (mandatory) and Contents read-only for READMEs. Do not use the broad `repo`/`workflow` scopes the Phase 0 validation happened to have available.

## CLI

The console entry point is `github-tool` (also `python -m github_tool`). All commands are implemented and tested.

| Command | Purpose | Phase |
|---|---|---|
| `github-tool keywords` | Print the keyword map; `--json PATH` writes it (used to regenerate `docs/keyword-map.json`). No token or DB needed. | 1 |
| `github-tool links` | Print GitHub search / Trending / topic / OSS Insight URLs for a keyword, language, and window. No token or DB needed. | 1 |
| `github-tool search` | On-demand REST search, sorted by stars/forks/updated, with backoff and ETag cache; `--local` uses FTS, `--in-readme` matches README text, `--include-forks` adds `fork:true`. | 2 |
| `github-tool init-db` | Create or upgrade the SQLite schema and FTS5 index. | 3 |
| `github-tool crawl` | Run a resumable crawl profile (keyword set × languages), slicing queries to stay under 1,000 results; `--in-readme` includes README text and `--include-forks` includes forks. | 3 |
| `github-tool trends` | Compute 1/7/30/90/365-day star gains and trend sorts from the local index; `--max-fork-ratio` filters inflated star counts and `--active-within N` filters stale repos. | 4 |
| `github-tool backfill` | Backfill star history for candidate repos, skipping archived repos, forks, and tiny repos. | 4 |
| `github-tool snapshot` | Take daily star/fork snapshots, batched via GraphQL. | 4 |
| `github-tool extract` | Extract install commands and hardware requirements (heuristics + optional LLM); `--manifests` adds dependency/base-image hints. | 6 |
| `github-tool export` | Export CSV or Markdown (repos or trends). | 5 |
| `github-tool serve` | Start the local FastAPI + Jinja2 web UI; `/export.csv`, `/export.md`, and `/export.json` share the same view filters. | 5 |
| `github-tool schedule` | Print cron/systemd/GitHub Actions snippets. | 7 |
| `github-tool hints` | Pull discovery hints from GitHub Trending HTML and/or the OSS Insight adapter (`--source all|oss|trending`). | 4 |
| `github-tool rate-limit` | Print current GitHub rate-limit buckets. | 7 |

Example usage:

```powershell
python -m github_tool links rag --language Python --window 30d
python -m github_tool search DB --language Rust --sort stars --limit 50 --in-readme --include-forks
python -m github_tool crawl --profile ai
python -m github_tool backfill --min-stars 50
python -m github_tool snapshot
python -m github_tool trends --window 7d --language Python --sort most_gained --max-fork-ratio 0.5 --active-within 90
python -m github_tool extract --fetch-missing --manifests --limit 50
python -m github_tool hints --source trending --language Python
python -m github_tool serve
```

Global flags `--db PATH` and `--offline` work before or after the subcommand. In offline mode the web UI and `search --local` never touch the network.

## Architecture

Four parts:

1. **Collectors** — REST and GraphQL clients with token auth, retry/backoff, ETag caching, README fetching, and the star-history endpoint. OSS Insight sits behind an optional adapter.
2. **Store** — SQLite with FTS5. Repos are keyed by the **numeric GitHub repo ID**, not the URL, because repos get renamed. Tables cover repos, star history, daily snapshots, keyword membership, crawl runs/slices, saved searches, and later install/hardware extraction.
3. **Trend engine** — computes star gains for today, 7, 30, 90, and 365 days; sorts by absolute gain, relative growth, acceleration, and "new & rising".
4. **UI** — local FastAPI + Jinja2 views (no external assets or CDN), CSV/Markdown export, and an offline mode that reads only from SQLite.

Data flow: keyword map → sliced search queries → repo metadata + README (ETag-aware) → star history + daily snapshots → trend windows → UI/export. Star-history and OSS Insight are both behind adapters so the system can fall back to its own snapshots.

## Windows and star growth

| Window | Source |
|---|---|
| Today, 7d, 30d, 90d, 365d | Star-history endpoint (weekly buckets, 1–2 calls per repo) |
| Fallback / long-term | Daily snapshots taken by the tool |
| Discovery hints only | OSS Insight, GitHub Trending |

**OSS Insight is currently unavailable.** On 2026-11-24 the API returned HTTP 200 with empty rows and `data_quality.status = "unavailable"` since 2026-03-01 (event capture dropped to ~0.3% of baseline). Empty means the metric is missing, not that no repos trend. The link is kept but marked unavailable and nothing blocks on it.

## Rate limits and policy

- Core: 5,000 req/hr authenticated, 60 unauthenticated.
- Search: 30 req/min authenticated, 10 unauthenticated, max 1,000 results per query.
- GraphQL: 5,000 points/hr plus secondary limits.
- Star history: 1–2 core calls per repo for up to one year.
- API-first; no bulk scraping; Trending fetched only a few times a day.
- GitHub Actions' built-in `GITHUB_TOKEN` is capped at 1,000 req/hr/repo — use a PAT for scheduled runs.

Details: [`docs/rate-limits.md`](docs/rate-limits.md) · validation evidence: [`docs/phase0-validation.md`](docs/phase0-validation.md) · background: [`context.md`](context.md) · plan: [`roadmap.md`](roadmap.md).

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**199 tests pass, 0 skipped/xfailed.** The suite covers links, keywords, schema/FTS, the HTTP client with recorded fixtures and `MockTransport` (retry/backoff, ETag/304, README, star history, GraphQL, Trending HTML), the query planner, crawler resume/dedupe, trend math and sorts, extraction (heuristics + strict LLM JSON + manifest hints), export, CLI, scheduler, logging redaction, and the web UI.

Offline validation script (always safe):

```powershell
python scripts\validate_phase0.py --skip-network   # regenerates docs/keyword-map.json
```

## Repository layout

```
github_tool/
  config.py models.py keywords.py links.py       # settings, domain models, keyword map, link-out views
  db.py github.py planner.py crawler.py          # SQLite/FTS, API client, slicing, resumable crawl
  trends.py extraction.py export.py scheduler.py # trend engine, Phase 6 extraction, export, scheduler snippets
  cli.py logging.py __main__.py
  web/                                            # FastAPI app, Jinja2 templates, CSS
tests/                                            # pytest suite + recorded API fixtures
scripts/                                          # validate_phase0.py, audit_extraction.py
docs/                                             # validation reports, rate limits, generated keyword map
context.md roadmap.md pyproject.toml
```
