"""Edge-case tests for COMPLAINT_FLOW/DECISION (spec User Story 5 edge cases)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import run_turn
from agent.states.complaint_flow import MAX_CLARIFICATIONS, complaint_flow_node


def _complaint_state(**overrides) -> dict:
    state = {
        "session_id": "s5",
        "tenant_id": "vinted",
        "channel": "web",
        "client_email": "emma.richard@email.com",
        "order_id": "CMD-2026-00005",
        "order_data": {"id": "CMD-2026-00005", "articleId": "VTG-012", "amount": 179.0},
        "intent": "complaint",
        "reformulation_count": 0,
        "escalated": False,
        "current_state": "COMPLAINT_FLOW",
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_vague_description_asks_for_clarification():
    """Edge case: vague defect description -> agent asks up to 2 clarifying questions."""
    state = _complaint_state(_latest_message="it's bad")

    result = await complaint_flow_node(state)

    assert result["current_state"] == "COMPLAINT_FLOW"
    assert result["_complaint_needs_clarification"] is True
    assert result["reformulation_count"] == 1
    assert not result.get("escalated")
    assert "more about the problem" in result["reply"]


@pytest.mark.asyncio
async def test_still_vague_after_max_clarifications_proceeds_anyway():
    """After MAX_CLARIFICATIONS, the agent stops asking and proceeds with what it has,
    rather than blocking the customer forever."""
    state = _complaint_state(_latest_message="bad", reformulation_count=MAX_CLARIFICATIONS)

    with (
        patch(
            "agent.states.complaint_flow.get_article_by_id",
            new=AsyncMock(return_value={"id": "VTG-012", "returnable": True, "non_return_reason": None}),
        ),
        patch(
            "agent.states.complaint_flow.record_complaint",
            new=AsyncMock(return_value={"priorComplaintCount": 0, "isRepeat": False}),
        ),
    ):
        result = await complaint_flow_node(state)

    assert result.get("_complaint_needs_clarification") is False
    assert result["reason"] == "other"


@pytest.mark.asyncio
async def test_complaint_past_return_window_escalates_under_legal_warranty():
    """Edge case: complaint filed after the standard return window -> legal warranty
    applies -> escalation with a note explaining why (not a refusal, not silently resolved)."""
    state = _complaint_state(_latest_message="This coat turned out to be defective after all.")

    with (
        patch(
            "agent.states.complaint_flow.get_article_by_id",
            new=AsyncMock(return_value={"id": "VTG-012", "returnable": True, "non_return_reason": None}),
        ),
        patch(
            "agent.states.complaint_flow.record_complaint",
            new=AsyncMock(return_value={"priorComplaintCount": 0, "isRepeat": False}),
        ),
        patch(
            "agent.states.verification.verify_eligibility",
            new=AsyncMock(
                return_value={
                    "eligible": True,
                    "autoApprovable": False,
                    "reason": "Past the standard return window — legal warranty applies",
                    "appliedRule": "legal_warranty:730d",
                }
            ),
        ),
        patch(
            "agent.states.escalation.escalate_to_human",
            new=AsyncMock(return_value={"ticketId": "TCK-warranty1", "delay": "within 24 business hours"}),
        ),
    ):
        result = await run_turn(state)

    assert result["current_state"] == "CONFIRMATION"
    assert result["escalated"] is True
