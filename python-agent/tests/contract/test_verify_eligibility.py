"""Contract test for the verify_eligibility MCP tool (contracts/mcp-tools.md)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.tools.verify_eligibility import verify_eligibility


@pytest.mark.asyncio
async def test_verify_eligibility_returns_eligible_and_applied_rule():
    fake_response = AsyncMock()
    fake_response.raise_for_status = lambda: None
    fake_response.json = lambda: {
        "eligible": True,
        "autoApprovable": True,
        "reason": "Eligible for return",
        "appliedRule": "auto_refund_threshold:80.00",
    }

    with patch("httpx.AsyncClient.post", return_value=fake_response):
        result = await verify_eligibility(
            order_id="CMD-2026-00001",
            tenant_id="vinted",
            reason="wrong_size",
            article_data={"returnable": True, "non_return_reason": None},
        )

    assert result["eligible"] is True
    assert result["appliedRule"] == "auto_refund_threshold:80.00"
