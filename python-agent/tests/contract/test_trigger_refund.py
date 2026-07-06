"""Contract test for the trigger_refund MCP tool (contracts/mcp-tools.md)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent.tools.trigger_refund import trigger_refund
from config.circuit_breaker import TechnicalFailure


@pytest.mark.asyncio
async def test_trigger_refund_returns_refund_id_and_delay():
    fake_response = AsyncMock()
    fake_response.raise_for_status = lambda: None
    fake_response.json = lambda: {"refundId": "RFD-abcd1234", "delay": "3-5 business days"}

    with patch("httpx.AsyncClient.post", return_value=fake_response) as mock_post:
        result = await trigger_refund(order_id="CMD-2026-00001", tenant_id="vinted", amount=68.0)

    assert result["refundId"] == "RFD-abcd1234"
    assert result["delay"] == "3-5 business days"
    # contracts/mcp-tools.md: POST /internal/refunds with the fields RefundController's DTO
    # expects, plus the X-Internal-Token header.
    args, kwargs = mock_post.call_args
    assert args[0].endswith("/internal/refunds")
    assert kwargs["json"] == {"tenantId": "vinted", "orderId": "CMD-2026-00001", "amount": 68.0}
    assert "X-Internal-Token" in kwargs["headers"]


@pytest.mark.asyncio
async def test_trigger_refund_technical_failure_after_retries_raises_technical_failure():
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("connection refused")):
        with pytest.raises(TechnicalFailure):
            await trigger_refund(order_id="CMD-2026-00001", tenant_id="vinted", amount=68.0)
