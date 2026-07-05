"""Reads tenant_config via Java REST (constitution III.5 — relational data is never queried
directly from Python, only through the Java Gateway).
"""

import httpx

from config.circuit_breaker import call_with_breaker
from config.settings import settings


async def get_tenant_config(tenant_id: str) -> dict:
    async def _call() -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.java_services_url}/internal/tenant-config/{tenant_id}",
                headers={"X-Internal-Token": settings.internal_service_token},
            )
            response.raise_for_status()
            return response.json()

    return await call_with_breaker("java", _call)
