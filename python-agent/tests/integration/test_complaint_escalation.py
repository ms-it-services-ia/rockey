"""Integration test: defective-item complaint above threshold, spec Scenario 3
(Sophie Bernard / CMD-2026-00003, VTG-011 €265, defective coat)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import run_turn
from agent.tools.interpret_turn import TurnInterpretation


@pytest.mark.asyncio
async def test_defective_item_complaint_above_threshold_escalates_with_summary():
    state = {
        "session_id": "s3",
        "tenant_id": "vinted",
        "channel": "web",
        "client_email": "sophie.bernard@email.com",
        "order_id": "CMD-2026-00003",
        "order_data": {"id": "CMD-2026-00003", "articleId": "VTG-011", "amount": 265.0, "clientName": "Sophie Bernard"},
        "intent": "complaint",
        "reformulation_count": 0,
        "identification_attempts": 0,
        "escalated": False,
        "current_state": "COMPLAINT_FLOW",
        "_latest_message": "The cashmere coat I received is defective, there's a large hole in the sleeve.",
    }

    with (
        patch(
            "agent.states.complaint_flow.interpret_turn",
            new=AsyncMock(return_value=TurnInterpretation(signal="on_topic", category="quality_defect")),
        ),
        patch(
            "agent.states.complaint_flow.get_article_by_id",
            new=AsyncMock(
                return_value={
                    "id": "VTG-011",
                    "returnable": True,
                    "non_return_reason": None,
                    "name": "70s Wool Cashmere Coat",
                }
            ),
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
                    "reason": "Eligible complaint",
                    "appliedRule": "manual_review_threshold:200.00",
                }
            ),
        ),
        patch(
            "agent.states.escalation.escalate_to_human",
            new=AsyncMock(return_value={"ticketId": "TCK-abcd1234", "delay": "within 24 business hours"}),
        ) as mock_escalate,
    ):
        result = await run_turn(state)

    assert result["current_state"] == "CONFIRMATION"
    assert result["escalated"] is True
    mock_escalate.assert_awaited_once()
    assert result["reason"] == "quality_defect"
