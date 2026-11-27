# Phase 0 Validation Report

*Validated 2026-11-24 on Windows with Python 3.14.8 and `gh` CLI 2.102.0. Evidence: live HTTP/API calls plus the generated keyword map. Reproduce with `scripts/validate_phase0.py`.*

Legend: **Done** = verified live; **Operator** = needs a human action; **Deviation** = live result differs from `context.md`.

## Checklist

| Roadmap item | Status | Evidence |
|---|---|---|
| Confirm linkable view URL patterns | **Done** (HTTP) | Four patterns returned HTTP 200; see table below. Browser confirmation of Trending remains optional. |
| Create a read-only GitHub token | **Done (operator)** | Token supplied by the operator; validation ran with `GITHUB_TOKEN` and reported `"authenticated": true` (core 5,000/hr). Least-privilege guidance remains below. |
| Call search, star history, OSS Insight once; log rate-limit headers | **Done** | Calls and headers below. |
| Pin star-history API version `2026-03-10` | **Done** | `X-GitHub-Api-Version` sent; response confirmed `X-Github-Api-Version-Selected: 2026-03-10`. |
| Prototype `gh search repos` (topic, language, sort, created, JSON) | **Done** | Commands below. |
| Build keyword map (topic + phrases, per language, merge locally) | **Done** | 12 keywords, 4 profiles in `docs/keyword-map.json`, generated from `github_tool/keywords.py`. |

## 1. Link-out URL patterns

All requests were unauthenticated GETs on 2026-11-24.

| View | URL checked | Result | Size |
|---|---|---|---|
| Search, stars, descending | `https://github.com/search?q=RAG+language:Python&type=repositories&s=stars&o=desc` | **200** | 225,081 bytes |
| Trending, Python, weekly | `https://github.com/trending/python?since=weekly` | **200** | 596,954 bytes |
| Topic page, RAG + Python | `https://github.com/topics/rag?l=python` | **200** | 538,523 bytes |
| OSS Insight trends API | `https://api.ossinsight.io/v1/trends/repos/?period=past_week&language=Python` | **200** (empty payload) | — |

Notes:

- These are page fetches, not rendered-browser checks. GitHub serves the search/trending/topic shells server-side, so a 200 with a large body is strong evidence the URL shape is still valid.
- `links.py` builds richer search URLs with `pushed:>=` (≤90 days) or `created:>=` (365-day fallback); the checked URL deliberately omits date qualifiers to test the base pattern.
- Trending has no keyword filter and no documented API. Keep it an optional, low-frequency source.

## 2. Read-only token — supplied by operator

The token is no longer an outstanding item: validation passed it as `GITHUB_TOKEN` (sourced from the authenticated `gh` CLI in this environment) and confirmed `"authenticated": true` with a 5,000/hr core budget. The token value is never stored in the repository; `.env.example` is a template only.

For least-privilege, long-term operation, switch to a fine-grained public read-only token:

**Steps (recommended: fine-grained, public read-only):**

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Name it (e.g. `github-tool-readonly`), set a short expiry, and choose **Public Repositories (read-only)** under Repository access.
3. Repository permissions: **Metadata: Read-only** (mandatory), **Contents: Read-only** (README fetches). Leave everything else at no access. No write scopes.
4. Generate, then expose it only as an environment variable:
   ```powershell
   $env:GITHUB_TOKEN = "<token>"   # current shell only
   ```
   Do not commit it. `.env.example` is a template only; the app reads the process environment and does not load `.env` itself.
5. Re-run `scripts/validate_phase0.py` and confirm the JSON summary says `"authenticated": true`.
6. If the broad-scoped `gh` credential was created for this validation, revoke or rotate it.

Search of public repositories and the public star-history endpoint need no additional scopes. If a fine-grained token unexpectedly blocks search, verify Metadata access before falling back to a classic token.

## 3. API calls and rate-limit headers

| Call | Endpoint | Status | Key result | Rate-limit headers |
|---|---|---|---|---|
| REST search | `GET /search/repositories?q=RAG+language:Python&sort=stars&order=desc&per_page=2` | 200 | `total_count` = 367,114 | search `Limit 30`, `Remaining 28`, `Used 2`, `Reset 1795555030`; core `Limit 5000` |
| Star history | `GET /repos/pallets/flask/stargazers/history?per_page=3` | 200 | `{"value":[{...}], "Count": 3}` | core bucket (authenticated run); public repos work without auth |
| OSS Insight | `GET https://api.ossinsight.io/v1/trends/repos/?period=past_week&language=Python` | 200 | `data_quality.status = "unavailable"` | n/a (third party) |
| Rate-limit snapshot | `GET /rate_limit` | 200 | core 5000 (one used), search 30, graphql 5000 | — |

The validation script records the same buckets in its JSON summary. Never log the `Authorization` header; the script only emits selected `X-RateLimit-*` values and the selected API-version header.

## 4. Star-history endpoint

- Path used: `GET /repos/{owner}/{repo}/stargazers/history` (also available as `/repositories/{id}/stargazers/history`).
- Pinned header: `X-GitHub-Api-Version: 2026-03-10`; the response echoed `X-Github-Api-Version-Selected: 2026-03-10`.
- Response shape (per_page=3):
  ```json
  {"value": [{"week": 1795305600, "total": 94, "days": [22, 19, 53, 0, 0, 0, 0]}, ...], "Count": 3}
  ```
  `week` is a Unix timestamp for the week start; `days` holds seven daily star-gain counts.
- Pagination: with per_page=3 the `Link` header advertised **29 pages**, i.e. the full history in weekly buckets — not just 30 weeks. Flask at per_page=30 is also ~29 pages.
- Cost: 1–2 core calls per repo for windows up to one year (30 weeks/page, newest first). 1/7/30/90-day windows need only the first (or first two) pages; older pages are for long history.
- No authentication is required for public repos, though an authenticated call avoids the 60/hr unauthenticated core budget.

## 5. `gh search repos` prototypes

Both worked and emitted JSON:

```powershell
gh search repos "topic:rag language:Python" --limit 5 --json fullName,stargazersCount,language
gh search repos "DB language:Rust" --limit 5 --json fullName,stargazersCount,language
gh search repos "topic:rag language:Python created:>=2026-01-01" --limit 5 --json fullName,createdAt
```

This confirms the qualifier syntax the crawler will send over REST/GraphQL: `topic:`, `language:`, `created:`, plus sort/order. `gh` is a prototyping convenience; the application talks to the REST API directly.

## 6. Keyword map

`docs/keyword-map.json` is **generated** from `github_tool/keywords.py` (`write_keyword_map()`), never hand-edited. Regenerate with `scripts/validate_phase0.py` (it always rewrites the file) or:

```powershell
.\.venv\Scripts\python.exe -c "from github_tool.keywords import write_keyword_map; write_keyword_map('docs/keyword-map.json')"
```

**Why topic + phrases:** generic terms such as `DB` and `API` are noisy as bare name/description searches. Each keyword therefore expands to a GitHub `topic:` qualifier (when one exists) plus one or two quoted phrases. The crawler runs every variant for each selected language and merges results locally by numeric repo ID.

**Generic-term problem:** `DB` matches unrelated abbreviations, while `topic:database` is curated but narrower and inconsistently applied. Phrases like `"database engine"` recover repos that are not tagged. The union of variants is intentionally broader than any single query; deduplication by repo ID prevents double counting.

| Keyword | Slug | Topic variant | Phrase variants | Notes |
|---|---|---|---|---|
| RAG | `rag` | `topic:rag` | "retrieval augmented generation" | GitHub normalises punctuation; one phrase avoids duplicate results |
| LLM | `llm` | `topic:llm` | "large language model", "llm inference" | — |
| DB | `db` | `topic:database` | "database engine", "sql database" | Canonical generic-term case |
| API | `api` | `topic:api` | "api framework", "rest api" | Generic-term case |
| Agents | `agents` | `topic:ai-agents` | "ai agent", "agentic framework" | Topic differs from display name |
| Vector DB | `vector-db` | `topic:vector-database` | "vector database", "vector search" | — |
| MCP | `mcp` | `topic:mcp` | "model context protocol", "mcp server" | — |
| Inference | `inference` | `topic:inference` | "llm inference", "model serving" | — |
| Embeddings | `embeddings` | `topic:embeddings` | "embedding model", "vector embeddings" | — |
| Fine-tuning | `finetuning` | `topic:fine-tuning` | "fine tuning", lora | `lora` is a single token, unquoted |
| Self-hosted | `self-hosted` | `topic:self-hosted` | "self hosted", self-hosted | Hyphen/space variants |
| Devtools | `devtools` | `topic:developer-tools` | "developer tools", "dev tooling" | — |

**Crawl profiles** (also in the generated JSON):

| Profile | Keywords | Languages | Min stars |
|---|---|---|---|
| `default` | all 12 | Python, TypeScript, JavaScript, Go, Rust, C, C++, Java, PHP | 20 |
| `ai` | rag, llm, agents, vector-db, mcp, inference, embeddings, finetuning | Python, TypeScript, Go, Rust | 20 |
| `systems` | db, inference, api | C, C++, Rust, Go, Zig | 20 |
| `web` | api, self-hosted, devtools, llm | TypeScript, JavaScript, Python, Go, PHP, Ruby | 20 |

Verified after generation: **12 keywords**, **4 profiles**, 15 supported languages. Every keyword has a topic variant plus one or two phrase variants.

Honest scope note: all 12 keywords were count-tested live against `language:Python` (every variant, results in [`keyword-tests.json`](keyword-tests.json)). Those live counts confirmed that most generic keywords exceed the 1,000-result cap and therefore need planner slicing (`DB`'s `"database engine"` variant is the exception at 559; numbers vary with GitHub's index). Exhaustively running every keyword × variant × language belongs to the Phase 3 crawl, which records per-slice counts.

## 7. OSS Insight — deviation from `context.md`

`context.md` describes OSS Insight as a usable unauthenticated trends view (600 req/hr/IP). On 2026-11-24 the endpoint still returns HTTP 200 but no ranking rows:

- `data_quality.status = "unavailable"`
- `unavailable_since = "2026-03-01"`
- reason: event capture dropped to roughly **0.3% of baseline**.

An empty payload means the metric is unavailable, **not** that there are no trending repos. This is a material change.

**Mitigation (already reflected in `links.py`):** keep the adapter and link-out entry, mark it unavailable (`OSS_INSIGHT_TRENDING_AVAILABLE = False`), and never block the trend engine on it. Use the star-history endpoint plus our own daily snapshots as the primary source; treat OSS Insight/Trending only as optional discovery hints. Re-check occasionally in case data capture recovers.

## Done-when statement

Every predefined keyword has tested query patterns and known per-call costs:

- Each keyword has a `topic:` variant plus 1–2 phrase variants; each is combined with `language:` and optional `stars:>=`/date qualifiers.
- Costs per slice: **1 count call** (`per_page=1`) plus **1 page call per 100 results**; a full 1,000-result slice is ~11 search calls.
- Search budget: 30 requests/min authenticated (10 unauthenticated), so ~3 slices/min; 1,000 results maximum per query.
- Core budget: 5,000/hr authenticated; star history costs 1–2 calls per repo for ≤1 year.
- OSS Insight is excluded from the critical path until it reports data again.

## Remaining operator actions

1. If not already done, replace the current credential with a fine-grained public read-only token and expose it as `GITHUB_TOKEN` (steps above).
2. Optionally open `https://github.com/trending/python?since=weekly` in a browser to confirm the rendered list (HTTP already 200).
3. Optionally re-check OSS Insight periodically; leave it disabled until `data_quality.status` is healthy.
4. Revoke/rotate the broad-scoped `gh` credential if it was only for this validation.
