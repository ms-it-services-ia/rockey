"""Edge-case tests for spec User Story 7:
- Customer switches channels mid-request -> treated as a new session, no cross-channel
  handoff (session_store keys sessions by (tenant, channel, client), so a channel switch
  naturally misses the existing key).
- A channel becomes unavailable -> customer sees an error message with an alternative
  channel suggested (main.unavailable_channel_reply)."""

from unittest.mock import patch

import pytest

from agent.memory import session_store
from main import unavailable_channel_reply


class _FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value

    async def delete(self, key: str):
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_switching_channel_mid_request_does_not_resume_the_other_channels_session():
    fake_redis = _FakeRedis()
    with patch("agent.memory.session_store._client", return_value=fake_redis):
        web_key = session_store.build_session_key("vinted", "web", "marie.dupont@email.com")
        await session_store.save_session(web_key, {"current_state": "RETURN_FLOW", "order_id": "CMD-2026-00001"})

        email_key = session_store.build_session_key("vinted", "email", "marie.dupont@email.com")
        resumed_on_email = await session_store.get_session(email_key)

    assert web_key != email_key
    assert resumed_on_email is None


def test_inactive_email_channel_returns_alternative_channel_message():
    tenant_config = {"channelEmailActive": False}

    reply = unavailable_channel_reply(tenant_config, "email")

    assert reply is not None
    assert "web chat" in reply


def test_unsupported_channel_returns_alternative_channel_message():
    tenant_config = {"channelEmailActive": True}

    reply = unavailable_channel_reply(tenant_config, "sms")

    assert reply is not None
    assert "web chat" in reply


def test_active_email_channel_proceeds_normally():
    tenant_config = {"channelEmailActive": True}

    assert unavailable_channel_reply(tenant_config, "email") is None


def test_web_channel_always_available():
    assert unavailable_channel_reply({}, "web") is None


def test_uses_the_tenants_own_configured_message_when_present():
    # Constitution VI.4: the message comes from the retailer's own config, not a hardcoded
    # platform string — this tenant's own copy must win over the module-level fallback.
    tenant_config = {"channelEmailActive": False, "errorMessageChannelUnavailable": "Ce canal est indisponible."}

    reply = unavailable_channel_reply(tenant_config, "email")

    assert reply == "Ce canal est indisponible."
