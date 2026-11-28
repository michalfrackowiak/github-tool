"""Tests for the normalized, replayable search-history parameters."""

from github_tool.search_history import normalize_search_params


def test_normalize_keeps_replayable_values_only():
    normalized = normalize_search_params(
        {
            "keyword": "  rag ",
            "q": "",
            "window": "30d",
            "source": "api",
            "language": ["Python", "", " Go "],
            "sort": "stars",
            "limit": 25,
            "min_stars": 0,
            "license": None,
            "archived": False,
            "forks": True,
            "in_readme": "1",
            "readme_q": "retrieval",
            "token": "must-not-be-copied",
        }
    )
    assert normalized == {
        "keyword": "rag",
        "window": "30d",
        "source": "api",
        "language": ["Python", "Go"],
        "sort": "stars",
        "limit": "25",
        "forks": "1",
        "in_readme": "1",
        "readme_q": "retrieval",
    }


def test_normalize_accepts_cli_style_flags_and_ignores_invalid_numbers():
    normalized = normalize_search_params(
        {"keyword": "rag", "min_stars": "not-a-number", "limit": 0, "forks": False}
    )
    assert normalized == {"keyword": "rag"}
