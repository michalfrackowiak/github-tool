"""Tests for scripts/audit_extraction.py (offline, temporary SQLite DB)."""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_extraction.py"
_spec = importlib.util.spec_from_file_location("_audit_extraction_under_test", SCRIPT)
assert _spec is not None and _spec.loader is not None
audit = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = audit
_spec.loader.exec_module(audit)

import make_spotcheck  # noqa: E402 - audit_extraction adds scripts/ to sys.path


README = "# demo\n\nFor example, pip install old-tool\npip install demo\n"
REPOS = [
    (1, "acme/alpha", "Python", "pip install alpha"),
    (2, "acme/beta", "Go", "go install beta"),
    (3, "acme/gamma", "Python", "pip install gamma"),
    (4, "acme/delta", "Rust", "cargo install delta"),
]


def create_db(path: Path, repos=REPOS) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE repos (
            id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            url TEXT NOT NULL,
            language TEXT,
            readme_text TEXT
        );
        CREATE TABLE install_commands (
            id INTEGER PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            cmd TEXT NOT NULL,
            source_line INTEGER NOT NULL,
            confidence REAL NOT NULL,
            command_type TEXT NOT NULL
        );
        """
    )
    for repo_id, full_name, language, cmd in repos:
        conn.execute(
            "INSERT INTO repos VALUES (?, ?, ?, ?, ?)",
            (repo_id, full_name, f"https://github.com/{full_name}", language, README),
        )
        conn.execute(
            "INSERT INTO install_commands (repo_id, cmd, source_line, confidence, command_type) "
            "VALUES (?, ?, 4, 0.9, 'install')",
            (repo_id, cmd),
        )
    conn.commit()
    conn.close()


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "audit.db"
    create_db(path)
    return path


def run_main(monkeypatch: pytest.MonkeyPatch, *extra: str) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_extraction.py", *extra])


def test_terminal_output_and_json(
    db_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    json_path = tmp_path / "sample.json"
    run_main(monkeypatch, "--db", str(db_path), "--limit", "10", "--json", str(json_path))

    assert audit.main() == 0
    out = capsys.readouterr().out
    assert "=== acme/alpha (1 commands) ===" in out
    assert "[CAUTION]" in out
    assert "Sampled 4 repos, 4 commands" in out

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(data) == 4
    assert data[0]["repo"] == "acme/alpha"
    assert data[0]["source_line"] == 4
    assert any(item["line"] == 3 and "For example" in item["text"] for item in data[0]["context"])
    assert data[0]["caution"]


def test_markdown_uses_shared_renderer(
    db_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    packet = tmp_path / "packet.md"
    reference = tmp_path / "reference.md"

    class FixedDate:
        @staticmethod
        def today() -> date:
            return date(2026, 1, 2)

    monkeypatch.setattr(make_spotcheck, "date", FixedDate)
    run_main(monkeypatch, "--db", str(db_path), "--limit", "10", "--markdown", str(packet))

    assert audit.main() == 0
    text = packet.read_text(encoding="utf-8")
    assert "# Extraction spot-check (human review)" in text
    assert "- [ ] `pip install alpha`" in text
    assert "- Language: Python" in text
    assert "## Sign-off" in text
    assert "4 repos, 4 commands" in capsys.readouterr().out

    make_spotcheck.write_packet(db_path, 10, reference)
    assert text == reference.read_text(encoding="utf-8")


def test_stratify_balances_languages(
    db_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packet = tmp_path / "stratified.md"
    run_main(
        monkeypatch,
        "--db",
        str(db_path),
        "--limit",
        "3",
        "--stratify",
        "--markdown",
        str(packet),
    )

    assert audit.main() == 0
    text = packet.read_text(encoding="utf-8")
    assert "Sampled **3 repositories**" in text
    assert "- Language: Go" in text
    assert "- Language: Python" in text
    assert "- Language: Rust" in text
    assert "pip install gamma" not in text  # second Python repo is skipped


def test_empty_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "empty.db"
    create_db(db_path, repos=[])
    run_main(monkeypatch, "--db", str(db_path), "--limit", "5")

    assert audit.main() == 0
    assert "Sampled 0 repos, 0 commands" in capsys.readouterr().out
