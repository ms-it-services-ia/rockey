"""Edge-case tests for IDENTIFICATION (spec User Story 1 edge cases)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.states.identification import identification_node


def _base_state(**overrides) -> dict:
    state = {
        "session_id": "s1",
        "tenant_id": "vinted",
        "channel": "web",
        "identification_attempts": 0,
        "escalated": False,
        "current_state": "IDENTIFICATION",
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_cant_find_order_number_gets_guidance_message():
    """Edge case: customer can't find their order number -> agent explains where to find it."""
    state = _base_state(_latest_message="I don't know my order number, where can I find it?")

    result = await identification_node(state)

    assert "confirmation email" in result["reply"]
    assert result["identification_attempts"] == 0  # not a failed attempt — nothing was checked
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_skip_identification_is_blocked():
    """Edge case: customer tries to skip straight to their request -> agent holds the step."""
    state = _base_state(_latest_message="My dress arrived damaged, I want a refund now!")

    result = await identification_node(state)

    assert result["current_state"] == "IDENTIFICATION"
    assert "order number" in result["reply"]
    assert result.get("client_email") is None
    assert result.get("order_id") is None


@pytest.mark.asyncio
async def test_second_failed_attempt_escalates_with_generic_message():
    """After 2 failed attempts, escalate with a message that never reveals *why* the lookup
    failed (constitution III.3 — no cross-tenant leak)."""
    from agent.tools.check_order import OrderNotFound

    state = _base_state(
        identification_attempts=1,
        _latest_message="CMD-2026-00001, marie.dupont@email.com",
    )

    with patch(
        "agent.states.identification.check_order",
        new=AsyncMock(side_effect=OrderNotFound("CMD-2026-00001")),
    ):
        result = await identification_node(state)

    assert result["identification_attempts"] == 2
    assert result["escalated"] is True
    assert result["escalation_reason"] == "identification_failed"
    assert "retailer" not in result["reply"].lower()
    assert "tenant" not in result["reply"].lower()
