"""Structured JSON logging (constitution VI.1: every error is structurally logged with
session_id, tenant_id, timestamp).

`bind_context` scopes session_id/tenant_id to the current request via contextvars, so every
log call made anywhere downstream of a request entry point (call_with_breaker's retry
warnings, PolicyLoader-equivalent fallback errors, etc.) picks them up automatically without
threading them through every function signature.
"""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime

_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)
_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)


@contextmanager
def bind_context(*, session_id: str | None = None, tenant_id: str | None = None) -> Iterator[None]:
    """Binds session_id/tenant_id to every log record emitted within this block, on this
    task. Always resets to the prior value on exit, even if the block raises."""
    session_token = _session_id.set(session_id)
    tenant_token = _tenant_id.set(tenant_id)
    try:
        yield
    finally:
        _session_id.reset(session_token)
        _tenant_id.reset(tenant_token)


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = _session_id.get()
        record.tenant_id = _tenant_id.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "session_id": getattr(record, "session_id", None),
            "tenant_id": getattr(record, "tenant_id", None),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    """Replaces logging.basicConfig — call exactly once, at process startup."""
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
