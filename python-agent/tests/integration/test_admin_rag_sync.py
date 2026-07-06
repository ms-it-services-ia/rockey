"""Tests for the manual RAG resync endpoint (T082): lets an operator pick up retailer
policy/catalogue edits in Drive immediately, without restarting python-agent."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from main import trigger_rag_sync


@pytest.mark.asyncio
async def test_happy_path_syncs_from_drive_and_returns_the_indexed_counts():
    fake_conn = AsyncMock()
    with (
        patch(
            "main.get_tenant_config",
            new=AsyncMock(return_value={"driveFolderId": "1JE-rNzM1oi9UznCbeCDU9G_OWRGz4xXu"}),
        ),
        patch("main.settings") as mock_settings,
        patch("main.sync_from_drive", new=AsyncMock(return_value=22)) as mock_sync,
        patch("main.embed_seed_articles", new=AsyncMock(return_value=4)) as mock_embed,
        patch("main.asyncpg.connect", new=AsyncMock(return_value=fake_conn)),
    ):
        mock_settings.internal_service_token = "test-token"
        mock_settings.google_service_account_json = "encoded-creds"
        mock_settings.database_url = "postgresql://fake"

        result = await trigger_rag_sync(tenant_id="vinted", x_internal_token="test-token")

    assert result == {"tenantId": "vinted", "chunksIndexed": 22, "articlesEmbedded": 4}
    mock_sync.assert_awaited_once_with("vinted", "1JE-rNzM1oi9UznCbeCDU9G_OWRGz4xXu")
    mock_embed.assert_awaited_once_with(fake_conn, "vinted")
    fake_conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_edge_case_wrong_token_is_rejected():
    with patch("main.settings") as mock_settings:
        mock_settings.internal_service_token = "test-token"

        with pytest.raises(HTTPException) as exc_info:
            await trigger_rag_sync(tenant_id="vinted", x_internal_token="wrong-token")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_edge_case_drive_not_configured_returns_503_instead_of_syncing():
    with (
        patch("main.get_tenant_config", new=AsyncMock(return_value={"driveFolderId": None})),
        patch("main.settings") as mock_settings,
        patch("main.sync_from_drive", new=AsyncMock()) as mock_sync,
    ):
        mock_settings.internal_service_token = "test-token"
        mock_settings.google_service_account_json = "encoded-creds"

        with pytest.raises(HTTPException) as exc_info:
            await trigger_rag_sync(tenant_id="vinted", x_internal_token="test-token")

    assert exc_info.value.status_code == 503
    mock_sync.assert_not_awaited()
