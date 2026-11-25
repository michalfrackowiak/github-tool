"""Logging setup with token redaction."""

from __future__ import annotations

import logging
import os
import re


_SECRET_PATTERNS = (
    re.compile(r"(Authorization:\s*Bearer\s+)\S+", re.IGNORECASE),
    re.compile(r"(token[=:]\s*)[A-Za-z0-9_\-]{8,}", re.IGNORECASE),
)


def redact(text: str, token: str | None = None) -> str:
    if token:
        text = text.replace(token, "***")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(r"\1***", text)
    return text


class RedactFilter(logging.Filter):
    def __init__(self, token: str | None = None):
        super().__init__()
        self.token = token

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        cleaned = redact(message, self.token)
        if cleaned != message:
            record.msg = cleaned
            record.args = ()
        return True


def configure_logging(level: str | int = "INFO", token: str | None = None) -> None:
    """Configure root logging once, with a redaction filter on the handler."""
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    root = logging.getLogger()
    if any(getattr(h, "_github_tool", False) for h in root.handlers):
        return
    handler = logging.StreamHandler()
    handler._github_tool = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S"))
    handler.addFilter(RedactFilter(token))
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
