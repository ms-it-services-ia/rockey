"""Integration test: eligible-return happy path, spec Scenario 1
(Marie Dupont / CMD-2026-00001, VTG-001 €68, delivered 15 days ago, item intact)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import run_turn


@pytest.mark.asyncio
async def test_eligible_return_generates_label_and_refund_automatically():
    state = {
        "session_id": "s1",
        "tenant_id": "vinted",
        "channel": "web",
        "client_email": "marie.dupont@email.com",
        "order_id": "CMD-2026-00001",
        "order_data": {"id": "CMD-2026-00001", "articleId": "VTG-001", "amount": 68.0, "clientName": "Marie Dupont"},
        "intent": "return",
        "reformulation_count": 0,
        "identification_attempts": 0,
        "escalated": False,
        "current_state": "RETURN_FLOW",
        "_latest_message": "The dress doesn't fit, it's too small.",
    }

    with (
        patch(
            "agent.states.return_flow.get_article_by_id",
            new=AsyncMock(return_value={"id": "VTG-001", "returnable": True, "non_return_reason": None}),
        ),
        patch(
            "agent.states.verification.verify_eligibility",
            new=AsyncMock(
                return_value={
                    "eligible": True,
                    "autoApprovable": True,
                    "reason": "Eligible for return",
                    "appliedRule": "auto_refund_threshold:80.00",
                }
            ),
        ),
        patch(
            "agent.states.auto_action.create_return_label",
            new=AsyncMock(return_value={"returnId": "RET-abcd1234", "labelUrl": "https://returns.vinted.local/LBL-abcd1234.pdf"}),
        ),
        patch(
            "agent.states.auto_action.trigger_refund",
            new=AsyncMock(return_value={"refundId": "RFD-abcd1234", "delay": "3-5 business days"}),
        ),
    ):
        result = await run_turn(state)

    assert result["current_state"] == "CONFIRMATION"
    assert result["return_id"] == "RET-abcd1234"
    assert result["refund_id"] == "RFD-abcd1234"
    assert not result["escalated"]
    assert result["attachments"][0]["type"] == "return_label"
