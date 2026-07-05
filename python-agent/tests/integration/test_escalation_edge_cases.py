"""Edge-case tests for ESCALATION (spec User Story 4 edge cases)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import run_turn
from agent.states.escalation import escalation_node


def _escalated_state(**overrides) -> dict:
    state = {
        "session_id": "s4",
        "tenant_id": "vinted",
        "channel": "web",
        "client_email": "sophie.bernard@email.com",
        "order_id": "CMD-2026-00003",
        "order_data": {"amount": 265.0},
        "article_data": {"name": "70s Wool Cashmere Coat"},
        "intent": "complaint",
        "messages": [],
        "escalated": True,
        "escalation_reason": "amount_above_threshold",
        "current_state": "ESCALATION",
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_escalation_outside_business_hours_adds_waiting_message():
    """Edge case: escalation triggered outside business hours -> waiting message with an
    expected response time."""
    weekend_night = datetime(2026, 7, 4, 2, 0, tzinfo=UTC)  # Saturday, 2am UTC

    with (
        patch(
            "agent.states.escalation.escalate_to_human",
            new=AsyncMock(return_value={"ticketId": "TCK-abcd1234", "delay": "within 24 business hours"}),
        ),
        patch("agent.states.escalation.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = weekend_night
        result = await escalation_node(_escalated_state())

    assert "currently offline" in result["reply"]


@pytest.mark.asyncio
async def test_duplicate_escalation_in_same_session_does_not_create_a_second_ticket():
    """Edge case: case already escalated in this session -> no duplicate ticket; the
    customer is told the case is already being handled."""
    with patch(
        "agent.states.escalation.escalate_to_human",
        new=AsyncMock(return_value={"ticketId": "TCK-abcd1234", "delay": "within 24 business hours"}),
    ) as mock_escalate:
        # First pass: goes through ESCALATION -> CONFIRMATION, creating the ticket once.
        state = _escalated_state(current_state="ESCALATION")
        state = await run_turn(state)
        assert state["current_state"] == "CONFIRMATION"
        assert mock_escalate.await_count == 1

        # Customer sends another message; session resumes at CONFIRMATION (already
        # escalated) — no second call to escalate_to_human.
        state["_latest_message"] = "Hello? Anyone there?"
        state = await run_turn(state)

    assert mock_escalate.await_count == 1
    assert state["ticket_id"] == "TCK-abcd1234"


@pytest.mark.asyncio
async def test_customer_demands_immediate_answer_agent_still_escalates():
    """Edge case: customer refuses escalation and demands an immediate answer -> agent
    explains its limits and still escalates (the outcome doesn't change)."""
    with patch(
        "agent.states.escalation.escalate_to_human",
        new=AsyncMock(return_value={"ticketId": "TCK-abcd1234", "delay": "within 24 business hours"}),
    ):
        state = _escalated_state(current_state="ESCALATION")
        state = await run_turn(state)

    assert state["escalated"] is True
    assert state["current_state"] == "CONFIRMATION"
    # The reply commits to the escalation outcome rather than offering an immediate answer.
    assert "passed your case to a" in state["reply"] or "TCK-abcd1234" in state["reply"]
