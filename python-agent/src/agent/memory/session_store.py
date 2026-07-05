"""Redis-backed session store (constitution I.2: TTL 30 min max per session).

Per research.md §5, sessions are keyed by (tenant_id, channel, client_identifier) with a
sliding TTL, refreshed on every turn, so a customer can resume an interrupted session on the
same channel without re-identifying (spec FR-012 / User Story 7).
"""

import json
from typing import Any

import redis.asyncio as redis

from config.settings import settings

_redis: redis.Redis | None = None


def _client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=0)
    return _redis


def build_session_key(tenant_id: str, channel: str, client_identifier: str) -> str:
    """The resumption key: same customer + same channel = same session within the TTL."""
    return f"session:{tenant_id}:{channel}:{client_identifier}"


async def get_session(session_key: str) -> dict[str, Any] | None:
    raw = await _client().get(session_key)
    if raw is None:
        return None
    return json.loads(raw)


async def save_session(session_key: str, state: dict[str, Any]) -> None:
    """Persists the session and refreshes its TTL (sliding window)."""
    await _client().set(session_key, json.dumps(state), ex=settings.session_ttl_seconds)


async def delete_session(session_key: str) -> None:
    await _client().delete(session_key)
