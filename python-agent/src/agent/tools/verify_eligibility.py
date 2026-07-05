"""`verify_eligibility` MCP tool (contracts/mcp-tools.md) — calls the Java Gateway's
`POST /internal/eligibility/check` endpoint.
"""

import httpx

from config.circuit_breaker import call_with_breaker
from config.settings import settings


async def verify_eligibility(
    order_id: str,
    tenant_id: str,
    reason: str,
    article_data: dict,
    is_international: bool = False,
    request_type: str = "return",
) -> dict:
    """Returns {eligible, autoApprovable, reason, appliedRule}. The article's returnable
    flag and non_return_reason come from `article_data`, already fetched by the caller via
    pgvector (constitution III.5) — Java never queries `articles` itself.

    `request_type` is "return" (US3, default) or "complaint" (US5) — Java applies
    different rules (legal warranty vs. return window) but returns the same response
    shape either way, so `decision.py` handles both identically.
    """

    async def _call() -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.java_services_url}/internal/eligibility/check",
                json={
                    "orderId": order_id,
                    "tenantId": tenant_id,
                    "reason": reason,
                    "articleData": {
                        "returnable": article_data.get("returnable", False),
                        "nonReturnReason": article_data.get("non_return_reason"),
                    },
                    "isInternational": is_international,
                    "type": request_type,
                },
                headers={"X-Internal-Token": settings.internal_service_token},
            )
            response.raise_for_status()
            return response.json()

    return await call_with_breaker("java", _call)
