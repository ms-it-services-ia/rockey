"""Contract test for the check_order MCP tool (contracts/mcp-tools.md)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent.tools.check_order import OrderNotFound, check_order
from config.circuit_breaker import TechnicalFailure


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

    with patch("httpx.AsyncClient.get", return_value=fake_response) as mock_get:
        result = await check_order("CMD-2026-00001", "marie.dupont@email.com", "vinted")

    assert result["clientName"] == "Marie Dupont"
    assert result["articleId"] == "VTG-001"
    # contracts/mcp-tools.md: GET /internal/orders/{id}, per-tool required fields, and the
    # X-Internal-Token header (constitution IV.2) — the actual outbound shape, not just the
    # response-parsing side of the contract.
    args, kwargs = mock_get.call_args
    assert args[0].endswith("/internal/orders/CMD-2026-00001")
    assert kwargs["params"] == {"email": "marie.dupont@email.com", "tenantId": "vinted"}
    assert "X-Internal-Token" in kwargs["headers"]


@pytest.mark.asyncio
async def test_check_order_not_found_raises_order_not_found():
    fake_response = AsyncMock()
    fake_response.status_code = 404

    with patch("httpx.AsyncClient.get", return_value=fake_response):
        with pytest.raises(OrderNotFound):
            await check_order("CMD-9999-99999", "nobody@email.com", "vinted")


@pytest.mark.asyncio
async def test_check_order_technical_failure_after_retries_raises_technical_failure():
    # Failure contract (contracts/mcp-tools.md): a timeout/connection error/5xx must
    # surface as technical_failure after retries, never a raw error to the caller.
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("connection refused")):
        with pytest.raises(TechnicalFailure):
            await check_order("CMD-2026-00001", "marie.dupont@email.com", "vinted")
