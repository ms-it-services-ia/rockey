"""Integration test: greeting + successful identification (spec User Story 1)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import run_turn


@pytest.mark.asyncio
async def test_greeting_then_successful_identification():
    with patch(
        "agent.states.greeting.get_tenant_config",
        new=AsyncMock(return_value={"agentFirstName": "Léa"}),
    ):
        state = {
            "session_id": "s1",
            "tenant_id": "vinted",
            "channel": "web",
            "client_id": "c1",
            "messages": [],
            "current_state": "GREETING",
            "identification_attempts": 0,
            "reformulation_count": 0,
            "escalated": False,
            "_latest_message": "Hello",
        }
        state = await run_turn(state)

    assert state["current_state"] == "IDENTIFICATION"
    assert "Léa" in state["reply"]

    with patch(
        "agent.states.identification.check_order",
        new=AsyncMock(
            return_value={
                "id": "CMD-2026-00001",
                "clientName": "Marie Dupont",
                "articleId": "VTG-001",
            }
        ),
    ):
        state["_latest_message"] = "CMD-2026-00001, marie.dupont@email.com"
        state = await run_turn(state)

    assert state["client_email"] == "marie.dupont@email.com"
    assert state["order_id"] == "CMD-2026-00001"
    assert "Marie Dupont" in state["reply"]
    assert state["current_state"] == "QUALIFICATION"
