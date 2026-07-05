"""Contract test for the trigger_refund MCP tool (contracts/mcp-tools.md)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.tools.trigger_refund import trigger_refund


@pytest.mark.asyncio
async def test_trigger_refund_returns_refund_id_and_delay():
    fake_response = AsyncMock()
    fake_response.raise_for_status = lambda: None
    fake_response.json = lambda: {"refundId": "RFD-abcd1234", "delay": "3-5 business days"}

    with patch("httpx.AsyncClient.post", return_value=fake_response):
        result = await trigger_refund(order_id="CMD-2026-00001", tenant_id="vinted", amount=68.0)

    assert result["refundId"] == "RFD-abcd1234"
    assert result["delay"] == "3-5 business days"
