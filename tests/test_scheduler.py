"""Tests for scheduler snippet rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from github_tool.scheduler import render_schedule


def test_cron_format_contains_all_jobs(tmp_path):
    root = tmp_path / "github-tool"
    text = render_schedule("cron", root=root, python="/usr/bin/python3")
    assert "15 2 * * *" in text
    assert "crawl --profile default" in text
    assert "backfill --weeks 53" in text
    assert "snapshot" in text
    assert root.resolve().as_posix() in text
    assert "\\" not in text
    assert "/usr/bin/python3" in text
    assert "/var/log/github-tool.log" in text


def test_systemd_format(tmp_path):
    root = tmp_path / "github-tool"
    text = render_schedule("systemd", root=root, env_file="/etc/github-tool.env")
    assert "[Service]" in text
    assert "[Timer]" in text
    assert f"WorkingDirectory={root.resolve().as_posix()}" in text
    assert "\\" not in text
    assert "EnvironmentFile=/etc/github-tool.env" in text
    assert "crawl --profile default" in text


def test_github_actions_uses_secret_and_warns_about_builtin_token():
    for alias in ("github-actions", "actions", "gha"):
        text = render_schedule(alias)
        assert "${{ secrets.GH_TOOL_TOKEN }}" in text
        assert "GITHUB_TOKEN" in text
        assert "built-in" in text
        assert "capped at 1,000 requests/hour" in text
        assert "crawl --profile default" in text


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        render_schedule("launchd")


def test_root_is_resolved(tmp_path: Path):
    text = render_schedule("cron", root=tmp_path)
    assert tmp_path.resolve().as_posix() in text
