"""Integration test: escalation produces a Slack notification and a full case summary
(spec User Story 4)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.states.escalation import escalation_node


@pytest.mark.asyncio
async def test_escalation_hands_off_with_full_summary_and_reference():
    state = {
        "session_id": "s3",
        "tenant_id": "vinted",
        "channel": "web",
        "client_email": "sophie.bernard@email.com",
        "order_id": "CMD-2026-00003",
        "order_data": {"amount": 265.0},
        "article_data": {"name": "70s Wool Cashmere Coat"},
        "intent": "complaint",
        "messages": [{"role": "customer", "content": "hi"}] * 3,
        "escalated": True,
        "escalation_reason": "amount_above_threshold",
        "current_state": "ESCALATION",
    }

    with patch(
        "agent.states.escalation.escalate_to_human",
        new=AsyncMock(return_value={"ticketId": "TCK-abcd1234", "delay": "within 24 business hours"}),
    ) as mock_escalate:
        result = await escalation_node(state)

    mock_escalate.assert_awaited_once()
    call_kwargs = mock_escalate.call_args.kwargs
    assert call_kwargs["order_id"] == "CMD-2026-00003"
    assert "amount exceeds" in call_kwargs["summary"] or "threshold" in call_kwargs["summary"]

    assert result["escalated"] is True
    assert result["ticket_id"] == "TCK-abcd1234"
    assert "TCK-abcd1234" in result["reply"]
