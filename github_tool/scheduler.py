"""Phase 7: scheduler snippets (cron, systemd, GitHub Actions).

The scheduler is deliberately not installed automatically. ``render_schedule``
returns copy-pasteable text so a user can review it first.
"""

from __future__ import annotations

from pathlib import Path


CRON = """\
# GitHub-Tool maintenance (review before installing with `crontab -e`)
# Paths are POSIX-style; on Windows pass --root /target/path and --python
# /absolute/path/to/python for the host where this snippet will actually run.
# Nightly crawl at 02:15, snapshots at 03:15, weekly star-history backfill at 04:15.
15 2 * * *  cd {root} && {python} -m github_tool crawl --profile default >> {log} 2>&1
15 3 * * *  cd {root} && {python} -m github_tool snapshot >> {log} 2>&1
15 4 * * 0  cd {root} && {python} -m github_tool backfill --weeks 53 >> {log} 2>&1
"""

SYSTEMD = """\
# /etc/systemd/system/github-tool-crawl.service
# Paths are POSIX-style; on Windows pass --root /target/path and --python
# /absolute/path/to/python (systemd requires an absolute ExecStart path).
[Unit]
Description=GitHub-Tool nightly crawl
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory={root}
EnvironmentFile={env_file}
ExecStart={python} -m github_tool crawl --profile default
Nice=10

# /etc/systemd/system/github-tool-crawl.timer
[Unit]
Description=Run GitHub-Tool crawl nightly

[Timer]
OnCalendar=*-*-* 02:15:00
Persistent=true

[Install]
WantedBy=timers.target
"""

GITHUB_ACTIONS = """\
# .github/workflows/github-tool.yml
# Requires a repository secret named GH_TOOL_TOKEN (a PAT). The built-in
# GITHUB_TOKEN is capped at 1,000 requests/hour/repository, which is not
# enough for a full crawl.
name: github-tool
on:
  schedule:
    - cron: "15 2 * * *"
  workflow_dispatch:
permissions:
  contents: read
jobs:
  crawl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e .
      - name: Restore local index
        uses: actions/cache@v4
        with:
          path: data
          key: github-tool-db-${{ github.run_id }}
          restore-keys: |
            github-tool-db-
      - name: Crawl
        env:
          GITHUB_TOKEN: ${{ secrets.GH_TOOL_TOKEN }}
          GITHUB_TOOL_DB: ${{ github.workspace }}/data/github-tool.db
        run: |
          python -m github_tool init-db
          python -m github_tool crawl --profile default
          python -m github_tool snapshot
      - uses: actions/upload-artifact@v4
        with:
          name: github-tool-db
          path: data/github-tool.db
          if-no-files-found: warn
"""


def render_schedule(
    fmt: str = "cron",
    *,
    root: str | Path = ".",
    python: str = "python",
    log: str = "/var/log/github-tool.log",
    env_file: str = "/etc/github-tool.env",
) -> str:
    # cron and systemd run on POSIX hosts; Windows-style separators from the
    # generator's machine would produce an unusable snippet.
    root = Path(root).resolve().as_posix()
    values = {"root": root, "python": python, "log": log, "env_file": env_file}
    if fmt == "cron":
        return CRON.format(**values)
    if fmt == "systemd":
        return SYSTEMD.format(**values)
    if fmt in {"github-actions", "actions", "gha"}:
        return GITHUB_ACTIONS
    raise ValueError(f"Unsupported scheduler format: {fmt!r}")
