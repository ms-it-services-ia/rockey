"""Slack escalation notification (constitution I.5, V.4; contracts/channel-apis.md).

Called directly by the Python Agent via the Slack MCP — the Java Gateway is never involved
in the Slack send (see plan.md's Structure Decision and the I1 finding from /speckit-analyze).
If SLACK_MCP_TOKEN is absent, the notification is skipped with a warning log rather than
failing the escalation itself (contracts/channel-apis.md).
"""

import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

SLACK_API_URL = "https://slack.com/api/chat.postMessage"


def _build_blocks(
    *,
    client_email: str,
    order_id: str,
    article_name: str,
    amount: float,
    channel: str,
    escalation_reason: str,
    summary: str,
) -> list[dict]:
    return [
        {"type": "header", "text": {"type": "plain_text", "text": "Escalation — action required"}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Customer:* {client_email}"},
                {"type": "mrkdwn", "text": f"*Order:* {order_id}"},
                {"type": "mrkdwn", "text": f"*Item:* {article_name} ({amount}€)"},
                {"type": "mrkdwn", "text": f"*Channel:* {channel}"},
                {"type": "mrkdwn", "text": f"*Escalation reason:* {escalation_reason}"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Summary:* {summary}"}},
    ]


async def send_escalation_notification(
    *,
    slack_channel: str,
    client_email: str,
    order_id: str,
    article_name: str,
    amount: float,
    channel: str,
    escalation_reason: str,
    summary: str,
) -> None:
    if not settings.slack_mcp_token:
        logger.warning(
            "SLACK_MCP_TOKEN absent — skipping Slack escalation notification for order %s", order_id
        )
        return

    blocks = _build_blocks(
        client_email=client_email,
        order_id=order_id,
        article_name=article_name,
        amount=amount,
        channel=channel,
        escalation_reason=escalation_reason,
        summary=summary,
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SLACK_API_URL,
            headers={"Authorization": f"Bearer {settings.slack_mcp_token}"},
            json={"channel": slack_channel, "blocks": blocks, "text": summary},
        )
        response.raise_for_status()
