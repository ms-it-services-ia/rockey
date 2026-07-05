"""`record_refusal` tool — calls `POST /internal/dossiers/refusal` so every processed
request gets a persisted Dossier regardless of outcome (spec User Story 6, T072).
Approved cases are recorded by `create_return_label`, escalated ones by
`escalate_to_human`; this fills the third gap."""

import httpx

from config.circuit_breaker import call_with_breaker
from config.settings import settings


async def record_refusal(
    order_id: str,
    tenant_id: str,
    article_id: str,
    client_email: str,
    dossier_type: str,
    reason: str,
    amount: float,
    channel: str,
    session_id: str,
    applied_rule: str,
) -> dict:
    """Returns {caseId}."""

    async def _call() -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.java_services_url}/internal/dossiers/refusal",
                json={
                    "tenantId": tenant_id,
                    "orderId": order_id,
                    "articleId": article_id,
                    "clientEmail": client_email,
                    "type": dossier_type,
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
