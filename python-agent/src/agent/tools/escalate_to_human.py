"""`escalate_to_human` MCP tool (contracts/mcp-tools.md): creates the ticket via Java, then
sends the Slack notification directly from Python — no Java involvement in the Slack call
(see the I1 fix in specs/001-poc-agent/contracts/mcp-tools.md and plan.md)."""

import httpx

from agent.integrations.slack_notifier import send_escalation_notification
from agent.tools.tenant_config_client import get_tenant_config
from config.circuit_breaker import call_with_breaker
from config.settings import settings


async def escalate_to_human(
    order_id: str,
    tenant_id: str,
    reason: str,
    summary: str,
    client_email: str,
    amount: float,
    channel: str,
    session_id: str,
    article_name: str = "N/A",
) -> dict:
    """Returns {ticketId, delay}. Constitution V.4: escalation always triggers Slack — this
    function always attempts the Slack send (send_escalation_notification itself is what
    decides to skip if SLACK_MCP_TOKEN is absent, never this caller)."""

    async def _create_ticket() -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.java_services_url}/internal/tickets",
                json={
                    "tenantId": tenant_id,
                    "orderId": order_id,
                    "clientEmail": client_email,
                    "reason": reason,
                    "summary": summary,
                    "amount": amount,
                    "channel": channel,
                    "sessionId": session_id,
                },
                headers={"X-Internal-Token": settings.internal_service_token},
            )
            response.raise_for_status()
            return response.json()

    ticket = await call_with_breaker("java", _create_ticket)

    tenant_config = await get_tenant_config(tenant_id)
    slack_channel = tenant_config.get("channelSlackChannel")
    if tenant_config.get("channelSlackActive") and slack_channel:
        await send_escalation_notification(
            slack_channel=slack_channel,
            client_email=client_email,
            order_id=order_id,
            article_name=article_name,
            amount=amount,
            channel=channel,
            escalation_reason=reason,
            summary=summary,
        )

    return ticket
