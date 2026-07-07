"""Tests for interpret_turn, the single "turn interpreter" LLM call shared by every graph
node that needs to understand free-text customer input (research.md §4, generalized —
replaces classify_message.py/classify_reason.py). The Claude client is mocked throughout
(constitution VII.2: never the real API in tests)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.interpret_turn import TurnCategory, interpret_turn
from config.circuit_breaker import TechnicalFailure

_CATEGORIES = [
    TurnCategory("wrong_size", "the item doesn't fit"),
    TurnCategory("change_of_mind", "no longer wants it"),
]


def _fake_tool_use_response(**input_kwargs):
    message = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = input_kwargs
    message.content = [tool_block]
    return message


@pytest.mark.asyncio
async def test_on_topic_signal_returns_the_classified_category():
    with patch("agent.tools.interpret_turn._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_fake_tool_use_response(signal="on_topic", category="wrong_size")
        )
        mock_get_client.return_value = mock_client

        result = await interpret_turn("Il me faudrait une taille au-dessus.", "why a return?", _CATEGORIES)

    assert result.signal == "on_topic"
    assert result.category == "wrong_size"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "classify_turn"}


@pytest.mark.asyncio
async def test_closing_signal_has_no_category():
    with patch("agent.tools.interpret_turn._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_fake_tool_use_response(signal="closing"))
        mock_get_client.return_value = mock_client

        result = await interpret_turn("ok merci", "any context", _CATEGORIES)

    assert result.signal == "closing"
    assert result.category is None


@pytest.mark.asyncio
async def test_resolved_signal_for_a_customer_who_found_the_missing_package():
    """Regression test: this is the exact case classify_verification_reply's fixed enum had
    no room for — "I found it" must never be forced into a category that doesn't fit."""
    with patch("agent.tools.interpret_turn._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_fake_tool_use_response(signal="resolved"))
        mock_get_client.return_value = mock_client

        result = await interpret_turn("Ah en fait je l'ai retrouvé, merci !", "verification follow-up", _CATEGORIES)

    assert result.signal == "resolved"
    assert result.category is None


@pytest.mark.asyncio
async def test_case_status_question_signal():
    with patch("agent.tools.interpret_turn._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_fake_tool_use_response(signal="case_status_question")
        )
        mock_get_client.return_value = mock_client

        result = await interpret_turn("donc c'est possible que je serai remboursé ?", "any context", _CATEGORIES)

    assert result.signal == "case_status_question"


@pytest.mark.asyncio
async def test_edge_case_on_topic_with_category_outside_the_provided_list_falls_back_to_ambiguous():
    # Defensive: the enum constraint should prevent this, but never trust an external
    # response blindly (constitution VI.1) — a category that isn't even in this call's valid
    # set must not silently pass through as if it were routable.
    with patch("agent.tools.interpret_turn._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_fake_tool_use_response(signal="on_topic", category="something_unexpected")
        )
        mock_get_client.return_value = mock_client

        result = await interpret_turn("...", "any context", _CATEGORIES)

    assert result.signal == "ambiguous"
    assert result.category is None


@pytest.mark.asyncio
async def test_edge_case_unrecognized_signal_value_falls_back_to_ambiguous():
    with patch("agent.tools.interpret_turn._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_fake_tool_use_response(signal="something_unexpected")
        )
        mock_get_client.return_value = mock_client

        result = await interpret_turn("...", "any context", _CATEGORIES)

    assert result.signal == "ambiguous"


@pytest.mark.asyncio
async def test_edge_case_no_tool_use_block_raises_technical_failure():
    message = MagicMock()
    message.content = []

    with patch("agent.tools.interpret_turn._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=message)
        mock_get_client.return_value = mock_client

        with pytest.raises(TechnicalFailure):
            await interpret_turn("...", "any context", _CATEGORIES)


@pytest.mark.asyncio
async def test_edge_case_llm_call_failure_raises_technical_failure():
    with patch("agent.tools.interpret_turn._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("connection reset"))
        mock_get_client.return_value = mock_client

        with pytest.raises(TechnicalFailure):
            await interpret_turn("...", "any context", _CATEGORIES)
