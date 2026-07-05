"""Per-dependency circuit breakers (constitution VI.2 / research.md §8).

One breaker per external dependency type (LLM, Java, MCP, pgvector), each with its own
timeout and MAX_RETRIES=2. On exhaustion, callers get a `TechnicalFailure` and MUST route the
calling LangGraph node to ESCALATION — never surface a raw technical error to the customer
(constitution VI.1).
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from config.settings import settings

logger = logging.getLogger(__name__)

_TIMEOUTS = {
    "llm": settings.timeout_llm,
    "java": settings.timeout_java,
    "mcp": settings.timeout_mcp,
    "pgvector": settings.timeout_pgvector,
}


class BusinessFailure(Exception):
    """Base class for expected, non-technical outcomes (e.g. `OrderNotFound`,
    `not_eligible`) — per contracts/mcp-tools.md's failure contract, these are never
    retried and never wrapped into `TechnicalFailure`; they propagate immediately so the
    calling node can handle them conversationally."""


class TechnicalFailure(Exception):
    """Raised when a dependency call exhausts its retries. Callers MUST escalate on this."""

    def __init__(self, dependency: str, cause: Exception):
        self.dependency = dependency
        self.cause = cause
        super().__init__(f"{dependency} failed after {settings.max_retries} retries: {cause}")


async def call_with_breaker[T](
    dependency: str, func: Callable[[], Awaitable[T]], on_fallback: Callable[[], T] | None = None
) -> T:
    """Calls `func` with the dependency's timeout, retrying up to MAX_RETRIES times.

    `BusinessFailure`s (e.g. OrderNotFound) are never retried — they propagate immediately,
    since retrying a definitive "not found" three times would be wasteful and would mask the
    original exception. If all *technical* retry attempts fail and `on_fallback` is provided
    (used for pgvector's static-YAML fallback, constitution VI.3), its result is returned
    instead of raising. Otherwise raises `TechnicalFailure`, which the calling LangGraph node
    must catch and route to ESCALATION.
    """
    timeout = _TIMEOUTS[dependency]
    last_error: Exception | None = None

    for attempt in range(settings.max_retries + 1):
        try:
            return await asyncio.wait_for(func(), timeout=timeout)
        except BusinessFailure:
            raise
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any technical failure counts
            last_error = exc
            logger.warning(
                "dependency=%s attempt=%d/%d failed: %s",
                dependency,
                attempt + 1,
                settings.max_retries + 1,
                exc,
            )

    if on_fallback is not None:
        return on_fallback()

    raise TechnicalFailure(dependency, last_error)
