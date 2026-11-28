# Reviewer findings and fixes

Seven independent reviewer passes were run near the end of the build, followed by an eighth self-review pass (the reviewer subagents hit their usage limit, so the maintainer reviewed directly). All findings below were addressed; each has a regression test in `tests/test_regressions.py` (or the relevant module test) unless the existing suite already covered it.

## Crawler / planner / trends / extraction

| Finding | Fix |
|---|---|
| Crawler wrote `readme_hash` before extraction, so the first extraction was skipped forever | `extract_for_repo` now requires both a matching hash **and** a non-null `extracted_at` |
| Profile planning could issue hundreds of thousands of `count_search` calls | Shared count memo; per-variant count budget (24) with explicit overflow slices when exhausted |
| Resume wedged when the last page was checkpointed but the slice was not finalized | `_run_rest_slice`/`_run_graphql_slice` finalize stale `running` slices at the page limit |
| >1,000-result slices were silently truncated | `estimated_count`/`overflow` persisted on `crawl_slices`; truncated slices marked `partial`, which is terminal for pending-slice queries |
| GraphQL resume restarted at page 1 | `graphql_cursor` persisted and restored; checkpoint stores the next cursor |
| A renamed repo could collide on `full_name` and abort a crawl | Conflicting name is retired with a `#<id>` suffix before the current owner is upserted |
| Stale snapshot baselines produced bogus short-window gains | Snapshot baselines and latest values must be within 2 days of the window endpoints |
| Partial daily history was reported as a complete window | Coverage checked against window start; partial data still displays its observed gain but is not used for relative growth/acceleration |
| `fastest_growth` / `new_rising` always ranked by 7-day values | `TrendRow.relative_growth_for(window)` added; both sorts now honor the requested window |
| `get_trending` opened ~10 SQLite connections per repo | `Database.trend_windows()` computes all five windows in one connection |
| `stars:0..9` bucket omitted its qualifier | `compose_query()` emits a bounded qualifier whenever `hi is not None` |

## Core / client / DB / web / security

| Finding | Fix |
|---|---|
| Global `--db` / `--offline` before a subcommand were overwritten | Subparser copies use `argparse.SUPPRESS` |
| CSV formula injection from GitHub-controlled cells | Cells starting `= + - @` (or control chars) are prefixed with `'` |
| Unvalidated `limit` / `min_stars` query params raised 500 | `_int_param()` clamps and falls back to defaults |
| Trends/search exports dropped displayed filters | Both export branches and the search export link now carry all filters |
| GitHub Actions schedule never restored its database | `actions/cache` restores `data/` and the WAL is checkpointed by shutdown |
| `Retry-After` HTTP-dates crashed; reset waits were truncated | `_retry_after_seconds()` parses delta-seconds and HTTP dates; long resets fail fast with a clear message |
| `Database(":memory:")` lost its schema between connections | A single in-memory connection is reused |
| No migration path for added columns | Additive `PRAGMA table_info` migrations for `repos` and `crawl_slices` |
| Saved-search Trends link encoded a Python list repr | `_qs()` expands lists into repeated query params |
| Sparkline ignored snapshots; stale READMEs were never revalidated | Snapshot fallback in `star_series`; README conditional GET on every repo-page visit |
| `?source=x` reached the client in offline mode and raised 500 | Unknown source values normalize to `api`, which offline mode maps to `local` |
| `Settings.__repr__` exposed the token | Token and LLM key fields use `repr=False` |
| Saved searches with `/` in the name could not be deleted | Delete is a POST form with a hidden `name` field |
| `search --limit 0` left a result variable unbound | Clean error and non-zero exit |
| Search page had no min-stars / license / archived / forks filters | Filters added to both search and trends, exports, and saved searches |

## Semantic extraction review (post-reviewer pass)

| Finding | Fix |
|---|---|
| 6 extracted commands were templates (`<plugin_name>`, `{version}`, `<...>`) | `_PLACEHOLDER_RE` extended; templates are skipped and a forced re-extraction cleaned the live DB |
| 4 extracted commands stopped at a trailing `\`, producing unusable fragments like `docker run \` | `_extract_commands` joins backslash continuations and reports the starting line; live commands for `kotaemon`, `DeepTutor`, and `crawl4ai` are now complete |
| OSS Insight hints were always empty because its ranking is unavailable | Added a GitHub Trending HTML collector (`--source trending|oss|all`); live run stored 15 Python repos |
| Manifest hints were implemented but never wired into the CLI or repo page | `extract --manifests` fetches requirements/pyproject/Dockerfile hints; they are persisted and rendered; live-checked on `Graphify-Labs/graphify` |
| Generated cron/systemd snippets embedded Windows `C:\...` paths, unusable on their POSIX target hosts | `render_schedule()` emits POSIX paths via `as_posix()`; snippets now explain `--root`/`--python` overrides and tests assert no backslashes |

## Third reviewer pass (spec + runtime correctness)

| Finding | Fix |
|---|---|
| `.env.example` told users to copy to a `.env` file that the app never loads | Header now states it is a template to export in the shell; token guidance points to fine-grained read-only PATs |
| Manifest fetching only checked exact `requirements.txt`, narrower than documented `requirements*.txt` | CLI enumerates the repo root and fetches every `requirements*.txt` plus `pyproject.toml`/`Dockerfile` (max 12); `GitHubClient.repo_root_files()` added |
| Manifest hints were skipped entirely for already-extracted repos, yet the fetches still cost API calls | `extract_for_repo` persists manifest hints before the unchanged-README early return |
| Switching REST↔GraphQL on resume reused incompatible pagination state, silently losing pages | Resume detects the mode switch and restarts those slices from page 1 with a warning |
| `discover_hints()` could raise from an unguarded `repo_stats()` loop despite its never-break contract | Batch loop wrapped so source discovery degrades gracefully to partial/empty hints |
| Planner consumed the last count-budget call then mislabelled a valid under-cap slice as overflow | `emit()` accepts the already-fetched count; exhaustion is only checked when a new count is needed |
| Planner `max_slices` cut ranges with no indication of omission | One explicitly flagged `truncated` overflow slice now stands in for the dropped ranges |
| Web trend exports (`/export.csv`, `/export.md`) returned 500 on an invalid `sort` | Sort is validated against `SORTS` and clamped like other numeric params |
| A resumed/finished crawl kept the stale `error` from an earlier failed run | Completion updates now clear `error` to `None` |
| `docs/keyword-tests.json` retained a stale RAG phrase variant no longer in `keywords.py` | Stale entry removed so evidence matches the current keyword map |

## Fourth reviewer pass (templates, data flow, generated data, CLI docs)

| Finding | Fix |
|---|---|
| Trends view/export showed gain for the selected window next to fixed 7-day relative growth and 7/30-day acceleration, so the displayed values could disagree with the `fastest_growth`/`accelerating` sort order | `TrendRow.relative_growth_for()` and new `acceleration_for()` are window-aware; template, CLI table, and both CSV/JSON export paths use them; `accelerating` sort uses the window-aware helper |
| Local web search listed repos by language/free text (no keyword filter), but the generated export link carried `keyword=`, silently dropping visible rows | `filter_params` only includes `keyword` for API-source searches; local exports now keep every displayed row |
| `keywords` command was implemented but absent from the README CLI table; many flags registered without `help=` | Added the `keywords` row (incl. `--json`) and help text for every CLI flag; regression tests assert all options are documented and README lists the command |

No findings in the fourth pass for undefined template variables/unregistered filters/XSS, stage-to-stage field or date mismatches, or generated-data drift (`docs/keyword-map.json` and `docs/keyword-tests.json` both match `keywords.py` exactly).

## Scale verification (post-reviewer)

| Finding | Fix |
|---|---|
| `get_trending()` opened one SQLite connection per candidate repo (~42 ms each on Windows), so a 10k-repo index would make the trends page take minutes | `Database.bulk_trend_windows()` fetches all candidates' daily/snapshots rows in one connection (batched by 500); `compute_trend_row()` accepts precomputed windows; shared `_windows_from_rows()` keeps the math identical. 300-repo ranking went from 9.49 s to 0.23 s, with bulk results verified equal to per-repo results |

## Source-spec cross-check (post-reviewer)

| Finding | Fix |
|---|---|
| `hints --period past_24h` sent an invalid OSS Insight period (live API returns HTTP 400); the link builder used the correct `past_24_hours`. The 24-hour OSS source silently failed for every call. | CLI choices and the Trending period mapping now use `past_24_hours`; a cross-module test asserts the CLI period set matches `links.OSS_INSIGHT_PERIODS`, all of which were live-checked (200 with the documented `data_quality.status = "unavailable"` payload) |

## Fifth reviewer pass (focused on the latest changes)

| Finding | Fix |
|---|---|
| Window-aware `relative_growth_for()` / `acceleration_for()` derived numbers from partial history: a repo with 7 of 30 days covered displayed a "30-day" growth/acceleration and could outrank complete rows in `fastest_growth`/`accelerating` sorts | `TrendRow` now carries `has_data` from `compute_trend_row()`; both helpers return `None` unless the selected window (and, for acceleration, its baseline window) is complete. CLI/web exports and the template already render `None` as blank/`—`. Regression tests reproduce the partial-history case and assert complete rows outrank incomplete rows in the `accelerating` and `fastest_growth` sorts |

No findings in the fifth pass for the bulk DB path (verified against 300 randomized datasets and 505 repos across the 500-id batch boundary), the OSS period fix, CLI help text, local-search export parity, Jinja2 method calls, or the `truncated` slice field.

## Sixth reviewer pass (final full-state review)

| Finding | Fix |
|---|---|
| Local web search by language ignored the "Include archived" / "Include forks" checkboxes: `Database.list_repos` defaults both to false, so those rows could never appear even with `archived=1` / `forks=1` | `list_repos()` now receives both flags from the parsed query parameters; a regression test confirms the rows appear only when requested |

No other material defects in the final state; the reviewer explicitly cleared the remaining modules.

## Seventh reviewer pass (Phase 8/9 changes)

| Finding | Fix |
|---|---|
| Web search's "Match README text" checkbox changed the API query but was dropped by the CSV/JSON export links, so exports included repos the page did not show | `_export_rows()` now applies the same README-only local filter (`_readme_matches`) and the local search page applies it too, so page, CSV, and JSON agree for both API and local sources; a dedicated `readme_q` parameter carries the exact keyword into local-source export links (local links intentionally omit `keyword`) |
| Saved searches silently dropped `in_readme`: the save form had no hidden input and `save_search()` had no `Form` parameter, so revisiting a saved search lost the qualifier | Added the hidden input and a `in_readme: str = Form("")` parameter; the flag is persisted in `params` and appears in the saved link |
| CLI `--max-fork-ratio nan` passed validation (`nan < 0` is false) and silently emptied results, while the web parser mapped `nan` to `None` and ignored it | `get_trending()` now rejects any non-finite ratio with a clear error; CLI and web behave consistently |

The reviewer explicitly cleared `planner.py` slice propagation, `crawler.py` propagation/resume, `trends.py` `pushed_at` cutoff and UTC parsing, `/export.json` serialization, and the new test coverage.

## Eighth pass (maintainer self-review, Phase 10 follow-up)

| Finding | Fix |
|---|---|
| `plan_keyword()` was the one planner entry point that did not accept or forward `in_readme`/`include_forks`, so any caller using it (it is part of the module's public surface and is unit-tested) silently dropped the `in:readme` / `fork:true` qualifiers that `plan_slices()`, `compose_query()`, and `Crawler.plan_profile()` all propagate | `plan_keyword()` now takes `in_readme`/`include_forks` and forwards them to every generated slice; a regression test asserts both qualifiers appear in all slices |

Cross-module re-check confirmed the CLI, web, crawler, and planner agree on `in_readme`, `include_forks`, `fork:true`, and `in:readme`; templates have no `|safe`/autoescape-off and the sparkline escapes its label; `Settings` redacts the token and LLM key; CSV export neutralizes formula injection. No other material defects found; suite is 231 tests, 0 skipped/xfailed.

## Remaining operator actions (not code defects)

1. Create a fine-grained, public read-only token instead of the broad `gh` scopes used for validation.
2. Independently hand-check a sample of extracted install commands if semantic confidence is business-critical; an agent semantic review covered all 190 commands across 47 repos and the automated line check was 190/190 correct.
3. OSS Insight's ranking is unavailable since 2026-03-01, so the roadmap's cross-check against it cannot be performed; GitHub star-history sums were used instead.
