"""Contract test for the check_order MCP tool (contracts/mcp-tools.md)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.tools.check_order import OrderNotFound, check_order


@pytest.mark.asyncio
async def test_check_order_success_returns_order_data():
    fake_response = AsyncMock()
    fake_response.status_code = 200
    fake_response.raise_for_status = lambda: None
    fake_response.json = lambda: {
        "id": "CMD-2026-00001",
        "tenantId": "vinted",
        "clientEmail": "marie.dupont@email.com",
        "clientName": "Marie Dupont",
        "articleId": "VTG-001",
        "amount": 68.0,
    }

    with patch("httpx.AsyncClient.get", return_value=fake_response):
        result = await check_order("CMD-2026-00001", "marie.dupont@email.com", "vinted")

    assert result["clientName"] == "Marie Dupont"
    assert result["articleId"] == "VTG-001"


@pytest.mark.asyncio
async def test_check_order_not_found_raises_order_not_found():
    fake_response = AsyncMock()
    fake_response.status_code = 404

    with patch("httpx.AsyncClient.get", return_value=fake_response):
        with pytest.raises(OrderNotFound):
            await check_order("CMD-9999-99999", "nobody@email.com", "vinted")
