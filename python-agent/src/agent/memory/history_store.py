"""Long-term customer history via Java REST (constitution III.5 — client_history is
relational data, never queried directly from Python).

Used by complaint_flow.py to detect repeated complaints (spec User Story 5 edge case).
"""

import httpx

from config.circuit_breaker import call_with_breaker
from config.settings import settings


async def record_complaint(tenant_id: str, client_email: str) -> dict:
    """Records this complaint contact and returns {priorComplaintCount, isRepeat}."""

    async def _call() -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.java_services_url}/internal/client-history/complaint",
                json={"tenantId": tenant_id, "clientEmail": client_email},
                headers={"X-Internal-Token": settings.internal_service_token},
            )
            response.raise_for_status()
            return response.json()

    return await call_with_breaker("java", _call)
