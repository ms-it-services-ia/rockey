"""Contract test for the create_return_label MCP tool (contracts/mcp-tools.md)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.tools.create_return_label import create_return_label


@pytest.mark.asyncio
async def test_create_return_label_returns_label_and_return_id():
    fake_response = AsyncMock()
    fake_response.raise_for_status = lambda: None
    fake_response.json = lambda: {
        "returnId": "RET-abcd1234",
        "labelUrl": "https://labels.rockey.local/LBL-CMD-2026-00001-abcd1234.pdf",
    }

    with patch("httpx.AsyncClient.post", return_value=fake_response):
        result = await create_return_label(
            order_id="CMD-2026-00001",
            tenant_id="vinted",
            article_id="VTG-001",
            client_email="marie.dupont@email.com",
            reason="wrong_size",
            amount=68.0,
            channel="web",
            session_id="s1",
            applied_rule="auto_refund_threshold:80.00",
        )

    assert result["returnId"] == "RET-abcd1234"
    assert result["labelUrl"].endswith(".pdf")
