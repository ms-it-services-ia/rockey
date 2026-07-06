"""Tests for classify_reason (research.md §4's LLM-based classification, applied one level
deeper to COMPLAINT_FLOW/RETURN_FLOW's reason). The Claude client is mocked throughout
(constitution VII.2: never the real API in tests)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.classify_reason import (
    classify_complaint_reason,
    classify_return_reason,
    classify_verification_reply,
)
from config.circuit_breaker import TechnicalFailure


def _fake_tool_use_response(category: str):
    message = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"category": category}
    message.content = [tool_block]
    return message


@pytest.mark.asyncio
async def test_complaint_reason_happy_path_returns_the_classified_category():
    with patch("agent.tools.classify_reason._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_fake_tool_use_response("damaged_on_delivery"))
        mock_get_client.return_value = mock_client

        result = await classify_complaint_reason("Le colis est arrivé écrasé, l'article est abîmé.")

    assert result == "damaged_on_delivery"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "classify_complaint_reason"}


@pytest.mark.asyncio
async def test_return_reason_happy_path_returns_the_classified_category():
    with patch("agent.tools.classify_reason._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_fake_tool_use_response("wrong_size"))
        mock_get_client.return_value = mock_client

        result = await classify_return_reason("La robe est trop petite, je fais du 38 d'habitude.")

    assert result == "wrong_size"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "classify_return_reason"}


@pytest.mark.asyncio
async def test_verification_reply_happy_path_returns_the_classified_category():
    with patch("agent.tools.classify_reason._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_fake_tool_use_response("not_yet_checked"))
        mock_get_client.return_value = mock_client

        result = await classify_verification_reply("not yet, I'll check tonight")

    assert result == "not_yet_checked"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "classify_verification_reply"}


@pytest.mark.asyncio
async def test_edge_case_unrecognized_category_value_falls_back_to_ambiguous():
    # Defensive: the enum constraint should prevent this, but never trust an external
    # response blindly (constitution VI.1) — an unexpected value must not silently pass
    # through as if it were a real, routable category.
    with patch("agent.tools.classify_reason._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_fake_tool_use_response("something_unexpected"))
        mock_get_client.return_value = mock_client

        result = await classify_complaint_reason("...")

    assert result == "ambiguous"


@pytest.mark.asyncio
async def test_edge_case_no_tool_use_block_raises_technical_failure():
    message = MagicMock()
    message.content = []

    with patch("agent.tools.classify_reason._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=message)
        mock_get_client.return_value = mock_client

        with pytest.raises(TechnicalFailure):
            await classify_return_reason("...")


@pytest.mark.asyncio
async def test_edge_case_llm_call_failure_raises_technical_failure():
    with patch("agent.tools.classify_reason._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("connection reset"))
        mock_get_client.return_value = mock_client

        with pytest.raises(TechnicalFailure):
            await classify_complaint_reason("...")
