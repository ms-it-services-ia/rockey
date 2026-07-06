"""Contract test for the verify_eligibility MCP tool (contracts/mcp-tools.md)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent.tools.verify_eligibility import verify_eligibility
from config.circuit_breaker import TechnicalFailure


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

    with patch("httpx.AsyncClient.post", return_value=fake_response) as mock_post:
        result = await verify_eligibility(
            order_id="CMD-2026-00001",
            tenant_id="vinted",
            reason="wrong_size",
            article_data={"returnable": True, "non_return_reason": None},
        )

    assert result["eligible"] is True
    assert result["appliedRule"] == "auto_refund_threshold:80.00"
    # contracts/mcp-tools.md: POST /internal/eligibility/check with articleData nested per
    # Java's EligibilityController DTO, plus the X-Internal-Token header.
    args, kwargs = mock_post.call_args
    assert args[0].endswith("/internal/eligibility/check")
    assert kwargs["json"]["orderId"] == "CMD-2026-00001"
    assert kwargs["json"]["articleData"] == {"returnable": True, "nonReturnReason": None}
    assert "X-Internal-Token" in kwargs["headers"]


@pytest.mark.asyncio
async def test_verify_eligibility_technical_failure_after_retries_raises_technical_failure():
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("connection refused")):
        with pytest.raises(TechnicalFailure):
            await verify_eligibility(
                order_id="CMD-2026-00001",
                tenant_id="vinted",
                reason="wrong_size",
                article_data={"returnable": True, "non_return_reason": None},
            )
