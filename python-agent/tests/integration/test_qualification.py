"""Integration test: intent classification for return / complaint / other (spec US2)."""

import pytest

from agent.states.qualification import qualification_node


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
async def test_classifies_return_intent():
    result = await qualification_node(_state("I'd like to return this dress, it's the wrong size."))
    assert result["intent"] == "return"
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_classifies_complaint_intent():
    result = await qualification_node(_state("The coat I received is damaged and defective."))
    assert result["intent"] == "complaint"


@pytest.mark.asyncio
async def test_classifies_out_of_scope_and_redirects_without_processing():
    result = await qualification_node(_state("What's the discount on your next promo?"))
    assert result["intent"] == "other"
    assert not result.get("escalated")
    assert "customer service team" in result["reply"]
