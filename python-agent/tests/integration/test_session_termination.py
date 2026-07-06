"""Regression tests for the confirmation-loop bug (spec FR-010): a closing acknowledgment
after CONFIRMATION must end the session cleanly, not just keep saving the same repeated
state back to Redis forever."""

from unittest.mock import AsyncMock, patch

import pytest

from config.settings import settings
from main import ChatRequest, process_message


@pytest.mark.asyncio
async def test_session_ended_flag_deletes_the_session_instead_of_saving_it():
    payload = ChatRequest(
        session_id="s1", tenant_id="vinted", channel="web", message="No thanks, that's all!", client_id="c1"
    )

    with (
        patch(
            "main.get_tenant_config",
            new=AsyncMock(return_value={"channelEmailActive": True}),
        ),
        patch("main.session_store.get_session", new=AsyncMock(return_value={"current_state": "CONFIRMATION"})),
        patch(
            "main.run_turn",
            new=AsyncMock(
                return_value={
                    "current_state": "CONFIRMATION",
                    "reply": "Avec plaisir !",
                    "_session_ended": True,
                }
            ),
        ),
        patch("main.session_store.delete_session", new=AsyncMock()) as mock_delete,
        patch("main.session_store.save_session", new=AsyncMock()) as mock_save,
    ):
        response = await process_message(payload, settings.internal_service_token)

    mock_delete.assert_awaited_once()
    mock_save.assert_not_awaited()
    assert response.reply == "Avec plaisir !"


@pytest.mark.asyncio
async def test_normal_turn_without_session_ended_flag_saves_as_usual():
    payload = ChatRequest(
        session_id="s1", tenant_id="vinted", channel="web", message="Bonjour", client_id="c1"
    )

    with (
        patch(
            "main.get_tenant_config",
            new=AsyncMock(return_value={"channelEmailActive": True}),
        ),
        patch("main.session_store.get_session", new=AsyncMock(return_value=None)),
        patch(
            "main.run_turn",
            new=AsyncMock(return_value={"current_state": "IDENTIFICATION", "reply": "Bonjour !"}),
        ),
        patch("main.session_store.delete_session", new=AsyncMock()) as mock_delete,
        patch("main.session_store.save_session", new=AsyncMock()) as mock_save,
    ):
        await process_message(payload, settings.internal_service_token)

    mock_save.assert_awaited_once()
    mock_delete.assert_not_awaited()
