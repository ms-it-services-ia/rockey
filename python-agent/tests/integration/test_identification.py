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
    # GREETING can't act on the message's content (identification always comes first,
    # constitution V.2) but must not discard it either — see qualification.py.
    assert state["_qualification_context"] == ["Hello"]

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
    assert state["_qualification_context"] == ["Hello", "CMD-2026-00001, marie.dupont@email.com"]


@pytest.mark.asyncio
async def test_customer_states_the_actual_request_before_identification_is_not_lost():
    """Regression test: customers routinely explain their whole request in the very first
    message ("Bonjour, je voudrai faire une réclamation, mon colis n'est jamais arrivé") —
    GREETING/IDENTIFICATION used to discard everything except the order number/email regex
    match, forcing the customer to repeat themselves once QUALIFICATION finally ran on a
    much vaguer follow-up message."""
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
            "_latest_message": "Bonjour, je voudrai faire une réclamation car mon colis n'est jamais arrivé",
        }
        state = await run_turn(state)

    with patch(
        "agent.states.identification.check_order",
        new=AsyncMock(
            return_value={"id": "CMD-2026-00001", "clientName": "Marie Dupont", "articleId": "VTG-001"}
        ),
    ):
        state["_latest_message"] = "CMD-2026-00001, marie.dupont@email.com"
        state = await run_turn(state)

    mock_classify = AsyncMock(return_value="non_delivery")
    with patch("agent.states.qualification.classify_message", new=mock_classify):
        state["_latest_message"] = "je voudrai avoir un remboursement"
        state = await run_turn(state)

    combined = mock_classify.call_args.args[0]
    assert "colis n'est jamais arrivé" in combined
    assert state["intent"] == "complaint"
    assert state["reason"] == "not_received"
