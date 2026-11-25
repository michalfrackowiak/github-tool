"""Generate a human review packet for extracted install commands.

Usage:
    python scripts/make_spotcheck.py --db path/to.db --limit 50 --out docs/extraction-spotcheck.md

The packet is a Markdown checklist: one tick-box per sampled repository (and a
sub-box per command) with the command, its confidence, the 1-based source line,
and the surrounding README lines. A reviewer opens the repo, reads the cited
line, and ticks the box if the command is a genuine instruction for that repo.

This does not judge semantics; it only puts each command next to its source so a
human can decide. Pair it with ``scripts/audit_extraction.py`` for a terminal
view of the same data.
"""

from __future__ import annotations

import argparse
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


def _context(lines: list[str], line_no: int, before: int = 2, after: int = 1) -> list[tuple[int, str]]:
    lo = max(1, line_no - before)
    hi = min(len(lines), line_no + after)
    return [(n, lines[n - 1]) for n in range(lo, hi + 1)]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=50, help="number of repos to sample")
    parser.add_argument("--out", type=Path, default=Path("docs/extraction-spotcheck.md"))
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    repos = conn.execute(
        """
        SELECT r.id, r.full_name, r.url, r.readme_text
        FROM repos r
        WHERE r.readme_text IS NOT NULL
          AND EXISTS (SELECT 1 FROM install_commands c WHERE c.repo_id = r.id)
        ORDER BY r.id
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

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
        f"_Generated {__import__('datetime').date.today().isoformat()} from `{args.db}`._",
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
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    conn.close()
    print(
        f"Wrote {args.out}: {len(repos)} repos, {total_commands} commands, "
        f"{total_flagged} flagged with caution words."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())