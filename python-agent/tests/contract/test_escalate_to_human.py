"""Contract test for the escalate_to_human MCP tool (contracts/mcp-tools.md)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent.tools.escalate_to_human import escalate_to_human
from config.circuit_breaker import TechnicalFailure


@pytest.mark.asyncio
async def test_escalate_to_human_creates_ticket_and_sends_slack_notification():
    fake_ticket_response = AsyncMock()
    fake_ticket_response.raise_for_status = lambda: None
    fake_ticket_response.json = lambda: {"ticketId": "TCK-abcd1234", "delay": "within 24 business hours"}

    with (
        patch("httpx.AsyncClient.post", return_value=fake_ticket_response) as mock_post,
        patch(
            "agent.tools.escalate_to_human.get_tenant_config",
            new=AsyncMock(return_value={"channelSlackActive": True, "channelSlackChannel": "#support-vinted"}),
        ),
        patch(
            "agent.tools.escalate_to_human.send_escalation_notification", new=AsyncMock()
        ) as mock_slack,
    ):
        result = await escalate_to_human(
            order_id="CMD-2026-00003",
            tenant_id="vinted",
            reason="amount_above_threshold",
            summary="Defective coat, amount above threshold",
            client_email="sophie.bernard@email.com",
            amount=265.0,
            channel="web",
            session_id="s3",
        )

    assert result["ticketId"] == "TCK-abcd1234"
    mock_slack.assert_awaited_once()
    # contracts/mcp-tools.md: POST /internal/tickets with the fields TicketController's DTO
    # expects, plus the X-Internal-Token header; escalation always attempts Slack (V.4).
    args, kwargs = mock_post.call_args
    assert args[0].endswith("/internal/tickets")
    assert kwargs["json"]["orderId"] == "CMD-2026-00003"
    assert kwargs["json"]["reason"] == "amount_above_threshold"
    assert "X-Internal-Token" in kwargs["headers"]


@pytest.mark.asyncio
async def test_escalate_to_human_technical_failure_after_retries_raises_technical_failure():
    with (
        patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("connection refused")),
        patch(
            "agent.tools.escalate_to_human.send_escalation_notification", new=AsyncMock()
        ) as mock_slack,
    ):
        with pytest.raises(TechnicalFailure):
            await escalate_to_human(
                order_id="CMD-2026-00003",
                tenant_id="vinted",
                reason="amount_above_threshold",
                summary="summary",
                client_email="sophie.bernard@email.com",
                amount=265.0,
                channel="web",
                session_id="s3",
            )

    # Ticket creation failed technically, so there's nothing to notify Slack about yet —
    # get_tenant_config/Slack are only reached after a successful ticket response.
    mock_slack.assert_not_awaited()


@pytest.mark.asyncio
async def test_escalate_to_human_skips_slack_when_channel_inactive():
    fake_ticket_response = AsyncMock()
    fake_ticket_response.raise_for_status = lambda: None
    fake_ticket_response.json = lambda: {"ticketId": "TCK-abcd1234", "delay": "within 24 business hours"}

    with (
        patch("httpx.AsyncClient.post", return_value=fake_ticket_response),
        patch(
            "agent.tools.escalate_to_human.get_tenant_config",
            new=AsyncMock(return_value={"channelSlackActive": False, "channelSlackChannel": None}),
        ),
        patch(
            "agent.tools.escalate_to_human.send_escalation_notification", new=AsyncMock()
        ) as mock_slack,
    ):
        await escalate_to_human(
            order_id="CMD-2026-00003",
            tenant_id="vinted",
            reason="amount_above_threshold",
            summary="summary",
            client_email="sophie.bernard@email.com",
            amount=265.0,
            channel="web",
            session_id="s3",
        )

    mock_slack.assert_not_awaited()
