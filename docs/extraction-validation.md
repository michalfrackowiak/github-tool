# Phase 6 extraction validation

*Run 2026-11-24 against the 60 READMEs collected by the live “smoke” crawl (RAG × Python, ≥5,000 stars). No LLM key was configured; all numbers below are the heuristic pass. A semantic review of every extracted command was added the same day; see below.*

## Corpus

- 64 repos crawled, 60 with a fetched README.
- 47 repos yielded at least one install/run/build/clone command.
- README sizes ranged from a few KB to ~43 KB.

## Results

| Metric | Count |
|---|---|
| Repos processed | 60 |
| Install commands | 190 |
| Commands with `high` confidence | 84 |
| Commands with `medium` confidence | 105 |
| Commands with `low` confidence | 1 |
| Repos with ≥1 command | 47 |
| Hardware rows | 727 |
| Hardware rows with GPU/numeric value | 154 |
| Hardware rows with `high` confidence | 24 |
| Hardware rows with `medium` confidence | 703 |

The original count was 196 commands; the semantic review below removed 6 template placeholders and joined 4 backslash-continued commands (the count stayed the same for those joins).

### Source-line check

For every extracted command, the README line at the recorded 1-based `source_line` was inspected:

- **190 / 190** lines contained the command text or its first token (100%).
- Multi-line commands report the line where the command *starts*; continuation lines are joined into one command.
- Inline shell comments are stripped from commands (e.g. `pip install graphifyy`, not `pip install graphifyy  # may need PATH ...`).
- Commands are deduplicated by `(cmd, source_line)`; the same command on different lines is retained because both are real instructions.

Examples:

| Repo | Line | Confidence | Command |
|---|---|---|---|
| Graphify-Labs/graphify | 197 | medium | `brew install python@3.12 uv` |
| Graphify-Labs/graphify | 229 | high | `pip install graphifyy` |
| langchain-ai/langchain | 32 | high | `uv add langchain` |
| Shubhamsaboo/awesome-llm-apps | 68 | high | `pip install -r requirements.txt` |
| unclecode/crawl4ai | 122 | high | `pip install -U crawl4ai` |

## Hardware extraction notes

- Numeric values are only accepted with an explicit `GB`/`GiB` unit near a hardware keyword, so “1.5 GB of stars” does not become VRAM.
- OS-only mentions (e.g. “Runs on Linux”) are stored as medium-confidence rows. In this corpus that dominates the row count (573 of 727 rows have no numeric value). The repo page shows numeric/GPU rows first and puts OS-only mentions behind a disclosure; the API/DB still retain everything with its source line.
- 154 rows carry a GPU flag or a numeric VRAM/RAM/disk value. These are the rows worth surfacing in a UI.

## Semantic review

`scripts/audit_extraction.py` prints every extracted command next to the README lines around it. All **190 commands across 47 repos** were reviewed in that form (not just the line-number check), with these findings:

| Finding | Action |
|---|---|
| 6 commands were unexpanded templates: `pip install superduper-<plugin_name>`, `pip install 'python-magic-bin=={version}'`, `docker run <...> ...`, two `docker pull ...:<version>` images | `_PLACEHOLDER_RE` now rejects `<name>`, `<...>`, and `{name}` templates; the 6 rows were removed by a forced re-extraction |
| 4 commands were truncated at a trailing `\` (e.g. `docker run \` with arguments on following lines), which is not a usable command | The parser joins backslash continuations and keeps the starting line number; re-extraction produced complete commands for `kotaemon`, `DeepTutor`, and `crawl4ai` |
| 3 commands sat near caution words (“Alternatively”, “e.g.”, “alternative”) | Reviewed: all are genuine optional-install or alternative-backend instructions, so they were kept |
| `bojieli/ai-agent-book` has 17 long chained `git clone … && git … checkout --detach …` commands | Reviewed: these are the book's deliberate chapter setup scripts; they are real commands, though they clone chapter materials rather than installing the book itself |
| `superduper-io/superduper` writes `pip install … >= 0.7.0` and `paper-qa>=5` appears unquoted | Source-faithful extraction; these shell quirks exist in the upstream READMEs and were not rewritten |

After the fixes, a fresh forced extraction over the same DB produced 190 commands and a 190/190 source-line check. The regression is covered in `tests/test_extraction.py`.

## Manifest hints

`extract --manifests` enumerates the repository root and fetches every `requirements*.txt`, plus `pyproject.toml` and `Dockerfile` (max 12 files), for each selected repo and stores bounded hints (dependency names, base images, `ENV` values, GPU words) on the repo row; the repo page displays them. A live check on a copy of the crawl DB fetched and stored hints for `Graphify-Labs/graphify` (31 Python dependencies from pyproject and one Docker base image). Unit tests cover hint parsing, persistence, and rendering.

## Limitations and manual follow-up

- This was an agent semantic review with an automated source-line check, not an independent human review. A human should still spot-check a sample if semantic confidence is business-critical (e.g. commands that are examples for a sub-component). To make that concrete, `scripts/make_spotcheck.py` generates a tick-box review packet at [`docs/extraction-spotcheck.md`](extraction-spotcheck.md) (46 repos / 184 commands, each with its cited README line and context); only the human sign-off remains.
- The optional LLM pass (strict JSON schema, source-line clamping, merge with heuristics) is implemented and tested with mocked responses. It was not run live because no LLM endpoint/key was configured.
- Re-extraction is keyed on the README SHA-256 **and** a non-null `extracted_at`, so a crawler-written hash cannot suppress the first extraction. Use `--force` to re-run after parser changes.
