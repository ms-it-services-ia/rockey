"""Contract test for send_escalation_notification (contracts/channel-apis.md).

Regression coverage for a live bug: Slack's chat.postMessage returns HTTP 200 even when the
post itself failed (e.g. "channel_not_found") — the actual outcome is only in the JSON body's
`ok` field. response.raise_for_status() alone treats that as success, so a misconfigured/
missing Slack channel silently drops the notification with no warning at all."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.integrations.slack_notifier import send_escalation_notification

_KWARGS = {
    "slack_channel": "#support-vinted",
    "client_email": "sophie.bernard@email.com",
    "order_id": "CMD-2026-00003",
    "article_name": "70s Wool Cashmere Coat",
    "amount": 265.0,
    "channel": "web",
    "escalation_reason": "amount_above_threshold",
    "summary": "Defective coat, amount above threshold",
}


def _fake_response(body: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = lambda: None
    response.json = lambda: body
    return response


@pytest.mark.asyncio
async def test_ok_true_sends_silently():
    with (
        patch("config.settings.settings.slack_mcp_token", "xoxb-fake-token"),
        patch(
            "httpx.AsyncClient.post", new=AsyncMock(return_value=_fake_response({"ok": True}))
        ) as mock_post,
        patch("agent.integrations.slack_notifier.logger") as mock_logger,
    ):
        await send_escalation_notification(**_KWARGS)

    mock_post.assert_awaited_once()
    mock_logger.warning.assert_not_called()


@pytest.mark.asyncio
async def test_ok_false_logs_a_warning_instead_of_silently_dropping_the_notification():
    """Regression test: this is exactly what happened live — the configured Slack channel
    didn't exist ("channel_not_found"), Slack answered HTTP 200 with ok=false, and the
    escalation completed with no Slack message and no warning telling anyone why."""
    with (
        patch("config.settings.settings.slack_mcp_token", "xoxb-fake-token"),
        patch(
            "httpx.AsyncClient.post",
            new=AsyncMock(return_value=_fake_response({"ok": False, "error": "channel_not_found"})),
        ),
        patch("agent.integrations.slack_notifier.logger") as mock_logger,
    ):
        await send_escalation_notification(**_KWARGS)

    mock_logger.warning.assert_called_once()
    warning_args = mock_logger.warning.call_args.args
    assert "channel_not_found" in warning_args


@pytest.mark.asyncio
async def test_missing_token_skips_without_calling_slack():
    with (
        patch("config.settings.settings.slack_mcp_token", ""),
        patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post,
    ):
        await send_escalation_notification(**_KWARGS)

    mock_post.assert_not_awaited()
