"""Generate a human review packet for extracted install commands.

Usage:
    python scripts/make_spotcheck.py --db path/to.db --limit 50 --out docs/extraction-spotcheck.md
    python scripts/make_spotcheck.py --stratify --limit 50   # balanced across languages

The packet is a Markdown checklist: one tick-box per sampled repository (and a
sub-box per command) with the command, its confidence, the 1-based source line,
and the surrounding README lines. A reviewer opens the repo, reads the cited
line, and ticks the box if the command is a genuine instruction for that repo.

This does not judge semantics; it only puts each command next to its source so a
human can decide. ``scripts/audit_extraction.py --markdown`` renders the same
packet from the terminal tool, so the two stay in sync.
"""

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import sqlite3
import sys

DEFAULT_DB = Path(os.environ.get("GITHUB_TOOL_DB") or Path.home() / ".github-tool" / "github-tool.db")

_CAUTION_WORDS = (
    "for example",
    "e.g.",
    "instead of",
    "not recommended",
    "deprecated",
    "do not",
    "don't",
    "alternative",
    "if you prefer",
    "uninstall",
)

_SAMPLE_SQL = """
SELECT r.id, r.full_name, r.url, r.language, r.readme_text
FROM repos r
WHERE r.readme_text IS NOT NULL
  AND EXISTS (SELECT 1 FROM install_commands c WHERE c.repo_id = r.id)
ORDER BY r.id
"""


def fetch_repos(conn: sqlite3.Connection, limit: int, stratify: bool = False) -> list[sqlite3.Row]:
    """Repos that have at least one extracted command.

    With ``stratify`` the sample is balanced across languages (round-robin), so a
    small limit still spans the crawl's language coverage instead of being
    dominated by whichever language was seeded first.
    """
    if limit <= 0:
        return []
    if not stratify:
        return conn.execute(_SAMPLE_SQL + " LIMIT ?", (limit,)).fetchall()
    rows = conn.execute(_SAMPLE_SQL).fetchall()

    groups: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        groups.setdefault((row["language"] or "Unknown").strip() or "Unknown", []).append(row)
    ordered_keys = sorted(groups)
    picked: list[sqlite3.Row] = []
    depth = 0
    while len(picked) < limit and any(depth < len(groups[k]) for k in ordered_keys):
        for key in ordered_keys:
            if depth < len(groups[key]) and len(picked) < limit:
                picked.append(groups[key][depth])
        depth += 1
    return picked


def _context(lines: list[str], line_no: int, before: int = 2, after: int = 1) -> list[tuple[int, str]]:
    lo = max(1, line_no - before)
    hi = min(len(lines), line_no + after)
    return [(n, lines[n - 1]) for n in range(lo, hi + 1)]


def build_packet(conn: sqlite3.Connection, repos: list[sqlite3.Row], db_path: Path) -> tuple[str, int, int, int]:
    """Render the Markdown packet. Returns (text, repos, commands, flagged)."""
    total_commands = 0
    total_flagged = 0
    sections: list[str] = []
    for repo in repos:
        lines = (repo["readme_text"] or "").splitlines()
        commands = conn.execute(
            "SELECT cmd, source_line, confidence, command_type "
            "FROM install_commands WHERE repo_id=? ORDER BY source_line",
            (repo["id"],),
        ).fetchall()
        total_commands += len(commands)
        out: list[str] = [f"### {repo['full_name']}", ""]
        out.append(f"- Repo: <{repo['url']}>")
        out.append(f"- Language: {repo['language'] or 'Unknown'}")
        out.append(f"- Commands: {len(commands)}")
        out.append("")
        for command in commands:
            line_no = int(command["source_line"])
            context = _context(lines, line_no)
            caution = [text for _, text in context if any(w in text.lower() for w in _CAUTION_WORDS)]
            if caution:
                total_flagged += 1
            marker = " **⚠ caution**" if caution else ""
            out.append(
                f"- [ ] `{command['cmd']}` "
                f"({command['confidence']} confidence, {command['command_type']}, "
                f"README L{line_no}){marker}"
            )
            for n, text in context:
                out.append(f"  - L{n}: `{text.strip()[:200]}`")
            out.append("")
        sections.append("\n".join(out))

    header = [
        "# Extraction spot-check (human review)",
        "",
        f"_Generated {date.today().isoformat()} from `{db_path}`._",
        "",
        f"Sampled **{len(repos)} repositories** and **{total_commands} install commands**; "
        f"**{total_flagged}** commands sit near caution words (for example / e.g. / alternative / "
        "deprecated). This is the optional independent human spot-check from the roadmap "
        "(Phase 6). The automated source-line check and an agent semantic review already passed; "
        "this packet is for a person to confirm semantic trustworthiness on a sample.",
        "",
        "## How to review",
        "",
        "1. For each repository, open the GitHub URL.",
        "2. For each command, read the cited README line (and the quoted context) and decide "
        "whether it is a genuine install/run/build/clone instruction **for that repository**.",
        "3. Tick the box if it is correct. Leave it unticked and note the reason if it is an "
        "example for a sub-component, a template, or otherwise misleading.",
        "4. Record the result at the bottom and file this document with the validation notes.",
        "",
        "> Tip: `⚠ caution` marks commands whose nearby lines contain hedging words; check those first.",
        "",
        "---",
        "",
    ]
    footer = [
        "---",
        "",
        "## Sign-off",
        "",
        "- Reviewed by: ______________________  Date: ____________",
        f"- Repos reviewed: ______ / {len(repos)}",
        f"- Commands judged correct: ______ / {total_commands}",
        "- False positives / notes:",
        "  - ",
        "",
    ]
    text = "\n".join(header) + "\n\n".join(sections) + "\n" + "\n".join(footer)
    return text, len(repos), total_commands, total_flagged


def write_packet(db_path: Path, limit: int, out: Path, stratify: bool = False) -> tuple[int, int, int]:
    """Build the packet and write it to ``out``. Returns (repos, commands, flagged)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        repos = fetch_repos(conn, limit, stratify=stratify)
        text, n_repos, n_cmds, flagged = build_packet(conn, repos, db_path)
    finally:
        conn.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return n_repos, n_cmds, flagged


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=50, help="number of repos to sample")
    parser.add_argument("--out", type=Path, default=Path("docs/extraction-spotcheck.md"))
    parser.add_argument(
        "--stratify",
        action="store_true",
        help="balance the sample across languages instead of taking the first N by id",
    )
    args = parser.parse_args()

    n_repos, n_cmds, flagged = write_packet(args.db, args.limit, args.out, stratify=args.stratify)
    print(
        f"Wrote {args.out}: {n_repos} repos, {n_cmds} commands, "
        f"{flagged} flagged with caution words."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())