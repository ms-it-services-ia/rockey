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
    assert "service client" in result["reply"]


@pytest.mark.asyncio
async def test_classifies_return_intent_in_french():
    result = await qualification_node(_state("Je voudrais faire un retour, j'ai changé d'avis."))
    assert result["intent"] == "return"
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_classifies_item_not_received_as_a_complaint_in_french():
    # Found via live testing: a customer stating their item was never received/is lost, in
    # French, was permanently unclassifiable — neither "return" nor "complaint" keywords
    # covered "not received/lost" in either language, so the agent asked the same
    # clarifying question twice before escalating, even though the intent was clear.
    result = await qualification_node(
        _state("Mon article n'est pas reçu, il est introuvable, je veux un remboursement.")
    )
    assert result["intent"] == "complaint"
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_classifies_item_not_received_as_a_complaint_in_english():
    result = await qualification_node(_state("I never received my package, it seems to be lost."))
    assert result["intent"] == "complaint"
