"""Tests for generate_decision_explanation (constitution I.7 RAG grounding + VI.1 graceful
degradation) — the LLM only composes the refusal's phrasing, never the decision itself."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.generate_decision_explanation import generate_decision_explanation


@pytest.mark.asyncio
async def test_success_path_returns_llm_composed_text_grounded_in_retrieved_policy():
    fake_message = MagicMock()
    fake_message.content = [MagicMock(text="Here's why, per our return policy: ...")]

    with (
        patch(
            "agent.tools.generate_decision_explanation.get_tenant_config",
            new=AsyncMock(
                return_value={
                    "agentFirstName": "Léa",
                    "agentTone": "warm",
                    "agentFormality": "formal",
                    "agentLanguage": "French",
                }
            ),
        ),
        patch(
            "agent.tools.generate_decision_explanation.query_policy",
            new=AsyncMock(return_value=["Items marked piece_unique are excluded from returns."]),
        ),
        patch("agent.tools.generate_decision_explanation._get_client") as mock_get_client,
    ):
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=fake_message)
        mock_get_client.return_value = mock_client

        result = await generate_decision_explanation(
            tenant_id="vinted",
            channel="web",
            current_state="DECISION",
            question="Explain the refusal: piece_unique",
            article_context="Vintage silk scarf",
            fallback_text="fallback text",
        )

    assert result == "Here's why, per our return policy: ..."
    mock_client.messages.create.assert_awaited_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "piece_unique are excluded" in call_kwargs["system"]


@pytest.mark.asyncio
async def test_falls_back_to_deterministic_text_when_llm_call_fails():
    with (
        patch(
            "agent.tools.generate_decision_explanation.get_tenant_config",
            new=AsyncMock(return_value={"agentFirstName": "Léa"}),
        ),
        patch(
            "agent.tools.generate_decision_explanation.query_policy",
            new=AsyncMock(return_value=[]),
        ),
        patch("agent.tools.generate_decision_explanation._get_client") as mock_get_client,
    ):
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("network down"))
        mock_get_client.return_value = mock_client

        result = await generate_decision_explanation(
            tenant_id="vinted",
            channel="web",
            current_state="DECISION",
            question="Explain the refusal",
            article_context="",
            fallback_text="fallback text",
        )

    assert result == "fallback text"


@pytest.mark.asyncio
async def test_falls_back_when_tenant_lookup_itself_fails():
    """Constitution VI.1: any failure anywhere in this best-effort pipeline must degrade to
    the deterministic reply, never raise or block the customer-facing flow."""
    with patch(
        "agent.tools.generate_decision_explanation.get_tenant_config",
        new=AsyncMock(side_effect=RuntimeError("java unreachable")),
    ):
        result = await generate_decision_explanation(
            tenant_id="vinted",
            channel="web",
            current_state="DECISION",
            question="Explain the refusal",
            article_context="",
            fallback_text="fallback text",
        )

    assert result == "fallback text"
