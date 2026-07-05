"""`trigger_refund` MCP tool (contracts/mcp-tools.md) — calls `POST /internal/refunds`."""

import httpx

from config.circuit_breaker import call_with_breaker
from config.settings import settings


async def trigger_refund(order_id: str, tenant_id: str, amount: float) -> dict:
    """Returns {refundId, delay}."""

    async def _call() -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.java_services_url}/internal/refunds",
                json={"tenantId": tenant_id, "orderId": order_id, "amount": amount},
                headers={"X-Internal-Token": settings.internal_service_token},
            )
            response.raise_for_status()
            return response.json()

    return await call_with_breaker("java", _call)
