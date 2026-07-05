"""`create_return_label` MCP tool (contracts/mcp-tools.md) — calls
`POST /internal/returns`. Only ever called after `verify_eligibility` confirms
eligibility + auto-approval (spec FR-006)."""

import httpx

from config.circuit_breaker import call_with_breaker
from config.settings import settings


async def create_return_label(
    order_id: str,
    tenant_id: str,
    article_id: str,
    client_email: str,
    reason: str,
    amount: float,
    channel: str,
    session_id: str,
    applied_rule: str,
) -> dict:
    """Returns {returnId, labelUrl}."""

    async def _call() -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.java_services_url}/internal/returns",
                json={
                    "tenantId": tenant_id,
                    "orderId": order_id,
                    "articleId": article_id,
                    "clientEmail": client_email,
                    "reason": reason,
                    "amount": amount,
                    "channel": channel,
                    "sessionId": session_id,
                    "appliedRule": applied_rule,
                },
                headers={"X-Internal-Token": settings.internal_service_token},
            )
            response.raise_for_status()
            return response.json()

    return await call_with_breaker("java", _call)
