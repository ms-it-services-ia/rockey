"""Integration test: session resumes within 30 minutes on the same channel, without asking
the customer to re-identify (spec FR-012 / User Story 7 AC4)."""

from unittest.mock import patch

import pytest

from agent.memory import session_store
from config.settings import settings


class _FakeRedis:
    """In-memory stand-in for redis.asyncio.Redis, sufficient for exercising
    session_store's get/save/delete + TTL contract without a live Redis server."""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.last_ttl: int | None = None

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        self.last_ttl = ex

    async def delete(self, key: str):
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_reconnecting_on_the_same_channel_resumes_the_existing_session():
    fake_redis = _FakeRedis()
    with patch("agent.memory.session_store._client", return_value=fake_redis):
        key = session_store.build_session_key("vinted", "web", "marie.dupont@email.com")

        in_progress_state = {
            "session_id": "s1",
            "current_state": "RETURN_FLOW",
            "order_id": "CMD-2026-00001",
            "identification_attempts": 1,
        }
        await session_store.save_session(key, in_progress_state)

        resumed = await session_store.get_session(key)

    assert resumed == in_progress_state
    assert resumed["current_state"] == "RETURN_FLOW"
    assert resumed["identification_attempts"] == 1


@pytest.mark.asyncio
async def test_session_save_uses_the_30_minute_sliding_ttl():
    fake_redis = _FakeRedis()
    with patch("agent.memory.session_store._client", return_value=fake_redis):
        key = session_store.build_session_key("vinted", "web", "marie.dupont@email.com")
        await session_store.save_session(key, {"current_state": "GREETING"})

    assert fake_redis.last_ttl == settings.session_ttl_seconds == 30 * 60


@pytest.mark.asyncio
async def test_expired_session_is_treated_as_a_fresh_start():
    fake_redis = _FakeRedis()
    with patch("agent.memory.session_store._client", return_value=fake_redis):
        key = session_store.build_session_key("vinted", "web", "marie.dupont@email.com")
        result = await session_store.get_session(key)

    assert result is None
