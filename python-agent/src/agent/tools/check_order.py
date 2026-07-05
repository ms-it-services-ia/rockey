"""`check_order` MCP tool (contracts/mcp-tools.md) — calls the Java Gateway's
`GET /internal/orders/{id}` endpoint."""

import httpx

from config.circuit_breaker import BusinessFailure, call_with_breaker
from config.settings import settings


class OrderNotFound(BusinessFailure):
    """Business failure — the order/email/tenant combination doesn't match. Per
    contracts/mcp-tools.md this is deliberately generic: it never distinguishes a wrong
    order number from a cross-tenant lookup (constitution III.3). Extends BusinessFailure
    so call_with_breaker never retries it or wraps it into a TechnicalFailure."""


async def check_order(order_id: str, email: str, tenant_id: str) -> dict:
    """Returns order_data (including article_id) or raises OrderNotFound /
    TechnicalFailure. Callers (identification.py) must catch TechnicalFailure and route to
    ESCALATION — never surface it to the customer directly (constitution VI.1)."""

    async def _call() -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.java_services_url}/internal/orders/{order_id}",
                params={"email": email, "tenantId": tenant_id},
                headers={"X-Internal-Token": settings.internal_service_token},
            )
            if response.status_code == 404:
                raise OrderNotFound(order_id)
            response.raise_for_status()
            return response.json()

    return await call_with_breaker("java", _call)
