"""Phase 5: CSV and Markdown export."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Iterable


REPO_COLUMNS = (
    "id",
    "full_name",
    "url",
    "description",
    "language",
    "stars",
    "forks",
    "license",
    "created_at",
    "pushed_at",
    "archived",
    "fork",
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _csv_safe(value: Any) -> str:
    text = _clean(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def to_csv(rows: Iterable[dict[str, Any]], columns: Iterable[str] | None = None) -> str:
    rows = list(rows)
    if columns is None:
        columns = REPO_COLUMNS if not rows else tuple(rows[0].keys())
    columns = list(columns)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: _csv_safe(row.get(c)) for c in columns})
    return buffer.getvalue()


def _md_cell(value: Any) -> str:
    return _clean(value).replace("|", "\\|")


def to_markdown(
    rows: Iterable[dict[str, Any]],
    columns: Iterable[str] | None = None,
    title: str = "GitHub-Tool export",
) -> str:
    rows = list(rows)
    if columns is None:
        columns = REPO_COLUMNS if not rows else tuple(rows[0].keys())
    columns = list(columns)
    lines = [f"# {title}", ""]
    if not rows:
        lines.append("_No rows._")
        return "\n".join(lines) + "\n"
    lines.append("| " + " | ".join(c.replace("_", " ").title() for c in columns) + " |")
    lines.append("|" + "|".join("---" for _ in columns) + "|")
    for row in rows:
        cells = []
        for c in columns:
            value = _clean(row.get(c))
            if c == "url" and value:
                value = f"[link]({value})"
            cells.append(_md_cell(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write_export(rows: Iterable[dict[str, Any]], path: str | Path, fmt: str = "csv", **kwargs: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        text = to_csv(rows, **kwargs)
    elif fmt in {"md", "markdown"}:
        text = to_markdown(rows, **kwargs)
    else:
        raise ValueError(f"Unsupported export format: {fmt!r}")
    path.write_text(text, encoding="utf-8")
    return path
