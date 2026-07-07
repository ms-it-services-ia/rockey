"""Integration test: greeting + successful identification (spec User Story 1)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import run_turn
from agent.tools.interpret_turn import TurnInterpretation


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

    # "Hello, CMD-2026-00001, marie.dupont@email.com" carries no actual request beyond
    # identification, so interpret_turn correctly signals ambiguous — this exercises the
    # "identification succeeded, cascade straight into QUALIFICATION" path (see graph.py's
    # run_turn) for the common case where nothing was said yet, not just the rich-content one.
    mock_interpret = AsyncMock(return_value=TurnInterpretation(signal="ambiguous"))
    with (
        patch(
            "agent.states.identification.check_order",
            new=AsyncMock(
                return_value={
                    "id": "CMD-2026-00001",
                    "clientName": "Marie Dupont",
                    "articleId": "VTG-001",
                }
            ),
        ),
        patch("agent.states.qualification.interpret_turn", new=mock_interpret),
    ):
        state["_latest_message"] = "CMD-2026-00001, marie.dupont@email.com"
        state = await run_turn(state)

    assert state["client_email"] == "marie.dupont@email.com"
    assert state["order_id"] == "CMD-2026-00001"
    # Identification's own acknowledgment must survive the same-turn cascade into
    # QUALIFICATION rather than being silently overwritten.
    assert "Marie Dupont" in state["reply"]
    assert state["current_state"] == "QUALIFICATION"
    assert state["_qualification_context"] == ["Hello", "CMD-2026-00001, marie.dupont@email.com"]


@pytest.mark.asyncio
async def test_customer_states_the_actual_request_before_identification_is_not_lost():
    """Regression test: customers routinely explain their whole request in the very first
    message ("Bonjour, je voudrai faire une réclamation, mon colis n'est jamais arrivé") —
    GREETING/IDENTIFICATION used to discard everything except the order number/email regex
    match, and even once buffered (_qualification_context), the turn used to pause right
    after identification and ask "comment puis-je vous aider ?" as if nothing had been said,
    forcing the customer to repeat themselves. Identification succeeding must now cascade
    straight into QUALIFICATION in the same turn and classify the buffered content."""
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

    mock_interpret = AsyncMock(return_value=TurnInterpretation(signal="on_topic", category="non_delivery"))
    with (
        patch(
            "agent.states.identification.check_order",
            new=AsyncMock(
                return_value={"id": "CMD-2026-00001", "clientName": "Marie Dupont", "articleId": "VTG-001"}
            ),
        ),
        patch("agent.states.qualification.interpret_turn", new=mock_interpret),
    ):
        state["_latest_message"] = "CMD-2026-00001, marie.dupont@email.com"
        state = await run_turn(state)

    combined = mock_interpret.call_args.args[0]
    assert "colis n'est jamais arrivé" in combined
    assert state["intent"] == "complaint"
    assert state["reason"] == "not_received"
    # Identification's own acknowledgment is preserved alongside the classification result,
    # instead of a generic "how can I help?" that ignores what was already said.
    assert "Marie Dupont" in state["reply"]
    assert "vérifier" in state["reply"]
    assert state["current_state"] == "COMPLAINT_FLOW"
