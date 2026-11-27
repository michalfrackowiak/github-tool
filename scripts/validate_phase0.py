#!/usr/bin/env python3
"""Phase 0 validation: link patterns, API calls, rate-limit headers, keyword map.

Run from the repo root:

    .venv\\Scripts\\python.exe scripts\\validate_phase0.py
    .venv\\Scripts\\python.exe scripts\\validate_phase0.py --skip-network
    .venv\\Scripts\\python.exe scripts\\validate_phase0.py --json docs\\phase0-results.json

A token is optional. Set GITHUB_TOKEN or GH_TOKEN to validate the authenticated
limits; without one the script warns and continues unauthenticated. Tokens and
Authorization headers are never printed.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from github_tool.config import API_VERSION, Settings  # noqa: E402
from github_tool.github import GitHubClient  # noqa: E402
from github_tool.keywords import write_keyword_map  # noqa: E402

USER_AGENT = "github-tool-phase0/0.1"
KEYWORD_MAP = ROOT / "docs" / "keyword-map.json"
SEARCH_QUERY = "RAG language:Python"
STAR_HISTORY = "https://api.github.com/repos/pallets/flask/stargazers/history"

LINK_CHECKS = [
    ("github-search", "https://github.com/search?q=RAG+language:Python&type=repositories&s=stars&o=desc"),
    ("github-trending", "https://github.com/trending/python?since=weekly"),
    ("github-topic", "https://github.com/topics/rag?l=python"),
    ("oss-insight", "https://api.ossinsight.io/v1/trends/repos/?period=past_week&language=Python"),
]

RATE_HEADERS = (
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Used",
    "X-RateLimit-Reset",
    "X-RateLimit-Resource",
)


def check_link(http: httpx.Client, name: str, url: str) -> dict[str, object]:
    try:
        response = http.get(url, headers={"User-Agent": USER_AGENT})
        return {"name": name, "url": url, "status": response.status_code, "bytes": len(response.content)}
    except Exception as exc:  # noqa: BLE001 - link checks are best-effort
        return {"name": name, "url": url, "status": None, "error": f"{type(exc).__name__}: {exc}"}


def check_star_history(
    token: str | None, *, http: httpx.Client | None = None
) -> dict[str, object]:
    """Probe the stargazer history endpoint.

    GitHub returns a JSON list of stargazers (``starred_at`` + ``user``), not
    an object with a ``value`` key; older/proxy shapes are still accepted.
    ``http`` is injectable so tests can use ``httpx.MockTransport``. The CLI
    keeps calling ``check_star_history(token)`` and gets a normal client.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        context = (
            nullcontext(http)
            if http is not None
            else httpx.Client(timeout=30.0, follow_redirects=True)
        )
        with context as client:
            response = client.get(STAR_HISTORY, params={"per_page": 3}, headers=headers)

        data: object = response.json() if response.status_code == 200 else None
        rows: list[object] = []
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            for key in ("value", "items", "rows"):
                candidate = data.get(key)
                if isinstance(candidate, list):
                    rows = candidate
                    break
        first = rows[0] if rows and isinstance(rows[0], dict) else {}
        user = first.get("user") if isinstance(first.get("user"), dict) else {}
        days = first.get("days")
        link = response.headers.get("Link", "")
        last_page = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link)
        return {
            "url": STAR_HISTORY,
            "status": response.status_code,
            "api_version": response.headers.get("X-Github-Api-Version-Selected"),
            "rows": len(rows),
            "first_starred_at": first.get("starred_at"),
            "first_login": user.get("login") or first.get("login"),
            "value_count": len(rows),  # backwards-compatible alias for "rows"
            "count": data.get("Count") if isinstance(data, dict) else None,
            "first_week": first.get("week"),
            "first_total": first.get("total"),
            "days_len": len(days) if isinstance(days, list) else 0,
            "last_page": int(last_page.group(1)) if last_page else None,
            "rate_limit": {k: response.headers[k] for k in RATE_HEADERS if k in response.headers},
        }
    except Exception as exc:  # noqa: BLE001 - network failures are expected on bad days
        message = f"{type(exc).__name__}: {exc}"
        if token:
            message = message.replace(token, "[REDACTED]")
        return {"url": STAR_HISTORY, "status": None, "error": message}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GitHub-Tool Phase 0 assumptions.")
    parser.add_argument("--skip-network", action="store_true", help="Only regenerate the keyword map.")
    parser.add_argument("--json", metavar="PATH", help="Write the JSON summary to PATH.")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None
    if not token:
        print("warning: no GITHUB_TOKEN/GH_TOKEN set; continuing unauthenticated (60 core req/hr, 10 search req/min).")

    write_keyword_map(KEYWORD_MAP)
    summary: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "authenticated": bool(token),
        "api_version": API_VERSION,
        "keyword_map": str(KEYWORD_MAP),
    }

    if not args.skip_network:
        settings = Settings()
        with httpx.Client(timeout=30.0, follow_redirects=True) as http:
            summary["links"] = [check_link(http, name, url) for name, url in LINK_CHECKS]

        result: dict[str, object] = {}
        with GitHubClient(settings) as client:
            try:
                page = client.search_repositories(SEARCH_QUERY, per_page=2)
                result["search"] = {
                    "query": SEARCH_QUERY,
                    "total_count": page.total_count,
                    "items": len(page.items),
                    "rate_limit": {
                        "limit": page.rate_limit.limit,
                        "remaining": page.rate_limit.remaining,
                        "reset": page.rate_limit.reset,
                        "resource": page.rate_limit.resource,
                    },
                }
                summary["rate_limits"] = {"search": result["search"]["rate_limit"]}  # type: ignore[index]
            except Exception as exc:  # noqa: BLE001
                result["search"] = {"query": SEARCH_QUERY, "error": f"{type(exc).__name__}: {exc}"}

            try:
                oss = client.oss_insight_trends("past_week", "Python")
                result["oss_insight"] = {
                    "status": 200,
                    "rows": len(oss.rows),
                    "available": oss.available,
                    "note": oss.note,
                }
            except Exception as exc:  # noqa: BLE001
                result["oss_insight"] = {"error": f"{type(exc).__name__}: {exc}"}

        star = check_star_history(token)
        result["star_history"] = star
        summary["api"] = result
        limiter = summary.setdefault("rate_limits", {})
        if isinstance(limiter, dict) and isinstance(star.get("rate_limit"), dict) and star["rate_limit"]:
            limiter.setdefault("core", star["rate_limit"])

        for entry in summary.get("links", []):  # type: ignore[union-attr]
            print(f"link {entry['name']}: {entry.get('status') or 'ERROR'}")
        print("rate limits:")
        for bucket, limits in summary.get("rate_limits", {}).items():  # type: ignore[union-attr]
            print(f"  {bucket}: " + ", ".join(f"{k}={v}" for k, v in limits.items()))

    print(json.dumps(summary, indent=2))
    if args.json:
        target = Path(args.json)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - unexpected failure
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
