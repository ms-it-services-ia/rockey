"""Integration test: repeated complaint on the same item triggers automatic escalation
with history attached (spec User Story 5 edge case)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import run_turn


@pytest.mark.asyncio
async def test_repeated_complaint_escalates_automatically_with_history():
    state = {
        "session_id": "s5",
        "tenant_id": "vinted",
        "channel": "web",
        "client_email": "julie.moreau@email.com",
        "order_id": "CMD-2026-00006",
        "order_data": {"id": "CMD-2026-00006", "articleId": "VTG-002", "amount": 145.0, "clientName": "Julie Moreau"},
        "intent": "complaint",
        "reformulation_count": 0,
        "identification_attempts": 0,
        "escalated": False,
        "current_state": "COMPLAINT_FLOW",
        "_latest_message": "This dress is defective again, same problem as before.",
    }

    with (
        patch(
            "agent.states.complaint_flow.classify_complaint_reason", new=AsyncMock(return_value="quality_defect")
        ),
        patch(
            "agent.states.complaint_flow.get_article_by_id",
            new=AsyncMock(return_value={"id": "VTG-002", "returnable": True, "non_return_reason": None}),
        ),
        patch(
            "agent.states.complaint_flow.record_complaint",
            new=AsyncMock(return_value={"priorComplaintCount": 1, "isRepeat": True}),
        ),
        patch(
            "agent.states.escalation.escalate_to_human",
            new=AsyncMock(return_value={"ticketId": "TCK-repeat1234", "delay": "within 24 business hours"}),
        ) as mock_escalate,
    ):
        result = await run_turn(state)

    assert result["current_state"] == "CONFIRMATION"
    assert result["escalated"] is True
    assert result["escalation_reason"] == "repeated_complaint"
    mock_escalate.assert_awaited_once()
    # Verification/decision are skipped entirely for a repeated complaint — it escalates
    # directly out of COMPLAINT_FLOW.
    assert result.get("eligible") is None
