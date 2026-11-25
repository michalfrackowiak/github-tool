"""Print a reviewable sample of extracted commands with README context.

Usage:
    python scripts/audit_extraction.py --db path/to.db --limit 50

This is deliberately human-readable: it does not judge semantics, it puts the
command next to the lines around it so a reviewer can decide whether it is an
installation step, an example, or a false positive.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

DEFAULT_DB = Path(os.environ.get("GITHUB_TOOL_DB") or Path.home() / ".github-tool" / "github-tool.db")

# Words in the preceding lines that suggest a command may be illustrative
# rather than a real instruction for this repository.
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


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1250
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=50, help="number of repos to sample")
    parser.add_argument("--json", type=Path, help="also write the sample as JSON")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    repos = conn.execute(
        """
        SELECT r.id, r.full_name, r.readme_text
        FROM repos r
        WHERE r.readme_text IS NOT NULL
          AND EXISTS (SELECT 1 FROM install_commands c WHERE c.repo_id=r.id)
        ORDER BY r.id
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

    sample: list[dict[str, object]] = []
    flagged = 0
    for repo in repos:
        lines = repo["readme_text"].splitlines()
        commands = conn.execute(
            "SELECT cmd, source_line, confidence, command_type "
            "FROM install_commands WHERE repo_id=? ORDER BY source_line",
            (repo["id"],),
        ).fetchall()
        print(f"\n=== {repo['full_name']} ({len(commands)} commands) ===")
        for command in commands:
            line_no = int(command["source_line"])
            lo, hi = max(0, line_no - 3), min(len(lines), line_no + 1)
            context = [
                {"line": n, "text": lines[n - 1][:200]} for n in range(lo + 1, hi + 1)
            ]
            caution = [
                item["text"]
                for item in context
                if any(word in item["text"].lower() for word in _CAUTION_WORDS)
            ]
            if caution:
                flagged += 1
            entry = {
                "repo": repo["full_name"],
                "cmd": command["cmd"],
                "source_line": line_no,
                "confidence": command["confidence"],
                "command_type": command["command_type"],
                "context": context,
                "caution": caution,
            }
            sample.append(entry)
            marker = " [CAUTION]" if caution else ""
            print(
                f"  L{line_no} {command['confidence']:>6} "
                f"{command['command_type']:<7} {command['cmd'][:110]}{marker}"
            )
            for item in context:
                print(f"      {item['line']:>6} | {item['text'][:160]}")

    print(
        f"\nSampled {len(repos)} repos, {len(sample)} commands, "
        f"{flagged} with caution words in nearby lines."
    )
    if args.json:
        args.json.write_text(json.dumps(sample, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
