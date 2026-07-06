"""Edge-case tests for QUALIFICATION (spec User Story 2 edge cases). classify_message is
mocked throughout (constitution VII.2: never the real API in tests)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.states.qualification import MAX_CLARIFICATIONS, qualification_node


def _state(message: str, **overrides) -> dict:
    state = {
        "tenant_id": "vinted",
        "reformulation_count": 0,
        "escalated": False,
        "current_state": "QUALIFICATION",
        "_latest_message": message,
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_mixed_return_and_complaint_asks_for_clarification():
    """Edge case: customer mixes a return and a complaint in one message -> the LLM itself
    signals genuine ambiguity (rather than both sets of keywords happening to match), and
    the agent asks for clarification, handling one case at a time (not both at once)."""
    with patch("agent.states.qualification.classify_message", new=AsyncMock(return_value="ambiguous")):
        result = await qualification_node(
            _state("I want to return this AND the other item I got was also damaged.")
        )

    assert result.get("intent") is None
    assert result["reformulation_count"] == 1
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_aggressive_customer_tone_still_handled_calmly():
    """Edge case: aggressive/impatient customer -> agent stays calm and empathetic rather
    than erroring or escalating immediately just because of tone."""
    with patch("agent.states.qualification.classify_message", new=AsyncMock(return_value="quality_complaint")):
        result = await qualification_node(
            _state("This is RIDICULOUS, I want my money back for this broken junk NOW!!!")
        )

    # Tone doesn't block classification, and no escalation is forced purely by aggressive
    # language.
    assert result["intent"] == "complaint"
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_still_unclear_after_max_clarifications_escalates():
    with patch("agent.states.qualification.classify_message", new=AsyncMock(return_value="ambiguous")):
        result = await qualification_node(_state("hmm not sure", reformulation_count=MAX_CLARIFICATIONS))

    assert result["escalated"] is True
    assert result["escalation_reason"] == "qualification_unclear"
