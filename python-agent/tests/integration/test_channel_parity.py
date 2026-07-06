"""Integration test: identical decision for the same request via Web Widget vs. Email
(spec User Story 7 AC2 / FR-011 — behavior is identical across channels, only response
formatting differs, and formatting is the Java adapter layer's job, not the agent's)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import run_turn


def _return_state(channel: str) -> dict:
    return {
        "session_id": "s1",
        "tenant_id": "vinted",
        "channel": channel,
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


@pytest.mark.asyncio
async def test_same_return_request_yields_identical_decision_on_web_and_email():
    with (
        patch(
            "agent.states.return_flow.classify_return_reason", new=AsyncMock(return_value="wrong_size")
        ),
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
        web_result = await run_turn(_return_state("web"))
        email_result = await run_turn(_return_state("email"))

    for result in (web_result, email_result):
        assert result["current_state"] == "CONFIRMATION"
        assert result["return_id"] == "RET-abcd1234"
        assert result["refund_id"] == "RFD-abcd1234"
        assert not result["escalated"]

    assert web_result["current_state"] == email_result["current_state"]
    assert web_result["return_id"] == email_result["return_id"]
    assert web_result["escalated"] == email_result["escalated"]
