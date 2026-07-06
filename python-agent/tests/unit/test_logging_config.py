"""Tests for structured JSON logging (constitution VI.1: every error is structurally
logged with session_id, tenant_id, timestamp)."""

import json
import logging

from config.logging_config import _ContextFilter, _JsonFormatter, bind_context


def _make_record(message: str = "boom") -> logging.LogRecord:
    return logging.LogRecord(
        name="test.logger", level=logging.ERROR, pathname=__file__, lineno=1, msg=message, args=(), exc_info=None
    )


def test_happy_path_formats_a_log_record_as_json_with_the_required_fields():
    record = _make_record("something failed")
    _ContextFilter().filter(record)
    formatted = _JsonFormatter().format(record)

    payload = json.loads(formatted)
    assert payload["message"] == "something failed"
    assert payload["level"] == "ERROR"
    assert "timestamp" in payload
    assert payload["session_id"] is None
    assert payload["tenant_id"] is None


def test_happy_path_bind_context_injects_session_and_tenant_id_into_log_records():
    with bind_context(session_id="s1", tenant_id="vinted"):
        record = _make_record("inside context")
        _ContextFilter().filter(record)

    payload = json.loads(_JsonFormatter().format(record))
    assert payload["session_id"] == "s1"
    assert payload["tenant_id"] == "vinted"


def test_edge_case_context_resets_after_the_block_exits():
    with bind_context(session_id="s1", tenant_id="vinted"):
        pass

    record = _make_record("after context")
    _ContextFilter().filter(record)
    payload = json.loads(_JsonFormatter().format(record))

    assert payload["session_id"] is None
    assert payload["tenant_id"] is None


def test_edge_case_context_resets_even_if_the_block_raises():
    try:
        with bind_context(session_id="s1", tenant_id="vinted"):
            raise ValueError("boom")
    except ValueError:
        pass

    record = _make_record("after a raising context")
    _ContextFilter().filter(record)
    payload = json.loads(_JsonFormatter().format(record))

    assert payload["session_id"] is None
    assert payload["tenant_id"] is None
