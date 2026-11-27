"""Print a reviewable sample of extracted commands with README context.

Usage:
    python scripts/audit_extraction.py --db path/to.db --limit 50
    python scripts/audit_extraction.py --markdown docs/extraction-spotcheck.md --stratify

The terminal output is deliberately human-readable: it does not judge semantics,
it puts the command next to the lines around it so a reviewer can decide whether
it is an installation step, an example, or a false positive. ``--markdown`` writes
the human sign-off packet using the same renderer as ``make_spotcheck.py``.
``--stratify`` balances the sample across languages for both output modes.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

# Both scripts live in scripts/; make their helpers importable when this file is
# loaded directly by path (e.g. from the test suite) as well as when executed.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from make_spotcheck import CAUTION_WORDS, fetch_repos, write_packet  # noqa: E402

DEFAULT_DB = Path(os.environ.get("GITHUB_TOOL_DB") or Path.home() / ".github-tool" / "github-tool.db")

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1250
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=50, help="number of repos to sample")
    parser.add_argument("--json", type=Path, help="also write the sample as JSON")
    parser.add_argument(
        "--markdown",
        type=Path,
        help="write the human spot-check packet (same renderer as make_spotcheck.py)",
    )
    parser.add_argument(
        "--stratify",
        action="store_true",
        help="balance the sample across languages instead of taking the first N by id",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    repos = fetch_repos(conn, args.limit, stratify=args.stratify)

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
                if any(word in item["text"].lower() for word in CAUTION_WORDS)
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
    if args.markdown:
        n_repos, n_cmds, flagged_in_packet = write_packet(
            args.db, args.limit, args.markdown, stratify=args.stratify
        )
        print(
            f"Wrote {args.markdown}: {n_repos} repos, {n_cmds} commands, "
            f"{flagged_in_packet} flagged with caution words."
        )
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
