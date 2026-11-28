"""Normalized definitions for automatically saved searches.

The web UI and CLI produce differently shaped inputs. This module reduces them
to one replayable parameter dict so history entries can be linked straight back
to ``/search`` without duplicating result repositories.
"""

from __future__ import annotations

from typing import Any, Mapping

# Allowlisted keys kept in a history entry. Stored JSON is key-sorted by
# Database.record_search(); this order is for readability only.
HISTORY_KEYS = (
    "keyword",
    "q",
    "window",
    "source",
    "language",
    "sort",
    "limit",
    "min_stars",
    "license",
    "archived",
    "forks",
    "in_readme",
    "readme_q",
)


def _clean(value: Any) -> str | list[str] | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "1" if value else None
    if isinstance(value, (list, tuple, set)):
        items = [str(v).strip() for v in value if str(v).strip()]
        return items or None
    text = str(value).strip()
    return text or None


def normalize_search_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Return only the non-empty, replayable subset of ``params``.

    Boolean-ish flags are stored as ``"1"`` because that is what the web form
    and replay links use. Zero values are dropped for optional numeric filters
    so a history entry does not claim a filter the user never set.
    """
    out: dict[str, Any] = {}
    for key in HISTORY_KEYS:
        if key not in params:
            continue
        value = params[key]
        if key in {"min_stars", "limit"}:
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if number > 0:
                out[key] = str(number)
            continue
        cleaned = _clean(value)
        if cleaned is not None:
            out[key] = cleaned
    return out
