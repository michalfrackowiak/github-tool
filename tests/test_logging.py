"""Tests for logging redaction and setup."""

from __future__ import annotations

import logging

from github_tool import logging as tool_logging


def _clear_tool_handlers() -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_github_tool", False):
            root.removeHandler(handler)
            handler.close()


def test_redact_removes_explicit_token():
    assert tool_logging.redact("using token abc123def456 here", "abc123def456") == "using token *** here"


def test_redact_removes_authorization_bearer_values():
    text = "GET /x\nAuthorization: Bearer ghp_supersecret123\n"
    redacted = tool_logging.redact(text)
    assert "ghp_supersecret123" not in redacted
    assert "Authorization: Bearer ***" in redacted


def test_redact_removes_token_assignments():
    assert tool_logging.redact("token=abcdefgh12345") == "token=***"
    assert tool_logging.redact("token: abcdefgh12345") == "token: ***"


def test_redact_filter_sanitises_record_including_args():
    token = "supersecretvalue"
    record = logging.LogRecord(
        name="github_tool.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Authorization: Bearer %s",
        args=(token,),
        exc_info=None,
    )
    log_filter = tool_logging.RedactFilter(token)
    assert log_filter.filter(record) is True
    assert record.getMessage() == "Authorization: Bearer ***"
    assert record.args == ()


def test_configure_logging_is_idempotent():
    _clear_tool_handlers()
    try:
        tool_logging.configure_logging(level="DEBUG", token="tok-123")
        tool_logging.configure_logging(level="WARNING", token="tok-123")
        handlers = [h for h in logging.getLogger().handlers if getattr(h, "_github_tool", False)]
        assert len(handlers) == 1
        assert isinstance(handlers[0].filters[0], tool_logging.RedactFilter)
    finally:
        _clear_tool_handlers()
