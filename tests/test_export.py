"""Tests for CSV and Markdown export."""

from __future__ import annotations

import csv
import io

import pytest

from github_tool.export import REPO_COLUMNS, to_csv, to_markdown, write_export


def sample_rows():
    return [
        {
            "id": 1,
            "full_name": "acme/demo",
            "url": "https://github.com/acme/demo",
            "description": "A demo, with a comma",
            "language": "Python",
            "stars": 100,
            "forks": 5,
            "license": "MIT",
            "created_at": "2025-01-01T00:00:00Z",
            "pushed_at": "2026-11-01T00:00:00Z",
            "archived": False,
            "fork": False,
        },
        {
            "id": 2,
            "full_name": "acme/quote",
            "url": "https://github.com/acme/quote",
            "description": 'He said "hi"\nand left',
            "language": "Go",
            "stars": 7,
            "forks": 0,
            "license": "",
            "created_at": "",
            "pushed_at": "",
            "archived": True,
            "fork": True,
        },
    ]


def test_csv_header_and_rows():
    text = to_csv(sample_rows())
    parsed = list(csv.reader(io.StringIO(text)))
    assert parsed[0] == list(REPO_COLUMNS)
    assert len(parsed) == 3
    assert parsed[1][1] == "acme/demo"
    assert parsed[1][3] == "A demo, with a comma"
    assert parsed[2][3] == 'He said "hi" and left'
    assert parsed[1][10] == "no"
    assert parsed[2][10] == "yes"
    assert parsed[2][11] == "yes"


def test_csv_empty_rows_uses_default_header():
    text = to_csv([])
    lines = text.splitlines()
    assert lines == [",".join(REPO_COLUMNS)]


def test_csv_newlines_are_flattened():
    text = to_csv([{"id": 1, "full_name": "a/b", "description": "line1\nline2\r\nline3"}], columns=["id", "full_name", "description"])
    assert len(text.splitlines()) == 2
    assert "line1 line2  line3" in text


def test_markdown_escapes_pipes_and_newlines_and_links_urls():
    rows = sample_rows()
    text = to_markdown(rows)
    assert text.startswith("# GitHub-Tool export\n")
    assert "| Id | Full Name | Url |" in text
    assert "|---" in text
    # URL cells become Markdown links.
    assert "[link](https://github.com/acme/demo)" in text
    # Newlines become spaces and pipes are escaped.
    text2 = to_markdown(
        [{"id": 1, "full_name": "a/b", "description": "a | b\nc", "url": ""}],
        columns=["id", "full_name", "description", "url"],
    )
    assert r"a \| b c" in text2


def test_markdown_empty_rows():
    text = to_markdown([], title="Nothing here")
    assert text == "# Nothing here\n\n_No rows._\n"


def test_write_export_supported_formats_and_error(tmp_path):
    csv_path = write_export(sample_rows(), tmp_path / "out.csv", fmt="csv")
    assert csv_path.exists()
    assert csv_path.read_text(encoding="utf-8").startswith("id,full_name")

    md_path = write_export(sample_rows(), tmp_path / "out.md", fmt="markdown")
    assert md_path.read_text(encoding="utf-8").startswith("# GitHub-Tool export")

    with pytest.raises(ValueError):
        write_export([], tmp_path / "bad.txt", fmt="yaml")
