"""Tests for classify_message (research.md §4's LLM-based intent classification). The
Claude client is mocked throughout (constitution VII.2: never the real API in tests)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.classify_message import classify_message
from config.circuit_breaker import TechnicalFailure


def _fake_tool_use_response(category: str):
    message = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"category": category}
    message.content = [tool_block]
    return message


@pytest.mark.asyncio
async def test_happy_path_returns_the_classified_category():
    with patch("agent.tools.classify_message._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_fake_tool_use_response("non_delivery"))
        mock_get_client.return_value = mock_client

        result = await classify_message("Je n'ai jamais reçu mon colis.")

    assert result == "non_delivery"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "classify_customer_message"}


@pytest.mark.asyncio
async def test_classifies_closing_message():
    with patch("agent.tools.classify_message._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_fake_tool_use_response("closing"))
        mock_get_client.return_value = mock_client

        result = await classify_message("ok merci")

    assert result == "closing"


@pytest.mark.asyncio
async def test_edge_case_unrecognized_category_value_falls_back_to_ambiguous():
    # Defensive: the enum constraint should prevent this, but never trust an external
    # response blindly (constitution VI.1) — an unexpected value must not silently pass
    # through as if it were a real, routable category.
    with patch("agent.tools.classify_message._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_fake_tool_use_response("something_unexpected"))
        mock_get_client.return_value = mock_client

        result = await classify_message("...")

    assert result == "ambiguous"


@pytest.mark.asyncio
async def test_edge_case_no_tool_use_block_raises_technical_failure():
    message = MagicMock()
    message.content = []

    with patch("agent.tools.classify_message._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=message)
        mock_get_client.return_value = mock_client

        with pytest.raises(TechnicalFailure):
            await classify_message("...")


@pytest.mark.asyncio
async def test_edge_case_llm_call_failure_raises_technical_failure():
    with patch("agent.tools.classify_message._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("connection reset"))
        mock_get_client.return_value = mock_client

        with pytest.raises(TechnicalFailure):
            await classify_message("...")
