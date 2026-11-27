"""Tests for the Phase 0 star-history probe (no live network)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import httpx


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_phase0.py"
_spec = importlib.util.spec_from_file_location("_validate_phase0_under_test", SCRIPT)
assert _spec is not None and _spec.loader is not None
validate_phase0 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = validate_phase0
_spec.loader.exec_module(validate_phase0)

TOKEN = "super-secret-token"

RATE_HEADERS = {
    "X-RateLimit-Limit": "5000",
    "X-RateLimit-Remaining": "4999",
    "X-RateLimit-Used": "1",
    "X-RateLimit-Reset": "1765000000",
    "X-RateLimit-Resource": "core",
}


def make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_check_star_history_parses_list_response():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers.get("Authorization", "")
        seen["api_version"] = request.headers.get("X-GitHub-Api-Version", "")
        return httpx.Response(
            200,
            json=[
                {"starred_at": "2026-11-20T10:00:00Z", "user": {"login": "alice"}},
                {"starred_at": "2026-11-21T10:00:00Z", "user": {"login": "bob"}},
            ],
            headers={
                "Link": (
                    '<https://api.github.com/repos/pallets/flask/stargazers/history?page=2>; rel="next", '
                    '<https://api.github.com/repos/pallets/flask/stargazers/history?page=42>; rel="last"'
                ),
                "X-Github-Api-Version-Selected": "2026-03-10",
                **RATE_HEADERS,
            },
        )

    with make_client(handler) as http:
        result = validate_phase0.check_star_history(TOKEN, http=http)

    assert result["status"] == 200
    assert result["rows"] == 2
    assert result["value_count"] == 2
    assert result["first_starred_at"] == "2026-11-20T10:00:00Z"
    assert result["first_login"] == "alice"
    assert result["api_version"] == "2026-03-10"
    assert result["last_page"] == 42
    assert result["rate_limit"] == RATE_HEADERS
    assert "per_page=3" in seen["url"]
    assert seen["authorization"] == f"Bearer {TOKEN}"
    assert seen["api_version"] == validate_phase0.API_VERSION
    payload = json.dumps(result)
    assert TOKEN not in payload


def test_check_star_history_non_200_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            text='{"message": "API rate limit exceeded"}',
            headers={"X-RateLimit-Remaining": "0"},
        )

    with make_client(handler) as http:
        result = validate_phase0.check_star_history(None, http=http)

    assert result["status"] == 403
    assert result["rows"] == 0
    assert result["value_count"] == 0
    assert result["first_starred_at"] is None
    assert result["first_login"] is None
    assert result["last_page"] is None
    assert "error" not in result
    assert result["rate_limit"] == {"X-RateLimit-Remaining": "0"}
    json.dumps(result)


def test_check_star_history_tolerates_malformed_and_unexpected_shapes():
    cases = [
        ("malformed", lambda: httpx.Response(200, text="not-json")),
        ("empty", lambda: httpx.Response(200, json=[])),
        ("unexpected dict", lambda: httpx.Response(200, json={"message": "ok"})),
        (
            "legacy dict",
            lambda: httpx.Response(
                200,
                json={"Count": 1, "value": [{"week": "2026-W47", "total": 9, "days": [1, 2]}]},
            ),
        ),
    ]

    for name, factory in cases:
        def handler(request: httpx.Request, factory=factory) -> httpx.Response:
            return factory()

        with make_client(handler) as http:
            result = validate_phase0.check_star_history(TOKEN, http=http)

        assert isinstance(result, dict), name
        assert result["url"] == validate_phase0.STAR_HISTORY
        payload = json.dumps(result)
        assert TOKEN not in payload
        if name == "malformed":
            assert result["status"] is None
            assert "error" in result
        else:
            assert result["status"] == 200
            assert "error" not in result
        if name in {"empty", "unexpected dict"}:
            assert result["rows"] == 0
            assert result["first_login"] is None
        if name == "legacy dict":
            assert result["rows"] == 1
            assert result["value_count"] == 1
            assert result["first_week"] == "2026-W47"
            assert result["days_len"] == 2
            assert result["count"] == 1


def test_check_star_history_redacts_token_in_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        raise RuntimeError(f"upstream failed with {TOKEN}")

    with make_client(handler) as http:
        result = validate_phase0.check_star_history(TOKEN, http=http)

    assert result["status"] is None
    assert "[REDACTED]" in result["error"]
    assert TOKEN not in json.dumps(result)
