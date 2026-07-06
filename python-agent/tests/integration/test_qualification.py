"""Integration test: intent classification for return / non-delivery / complaint / other
(spec US2). classify_message is mocked throughout (constitution VII.2: LangGraph tests use
LLM mocks, never the real API) — see test_classify_message.py for the LLM tool-use wiring
itself."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.states.qualification import qualification_node
from config.circuit_breaker import TechnicalFailure


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


def _mock_classify(category: str) -> AsyncMock:
    return AsyncMock(return_value=category)


@pytest.mark.asyncio
async def test_classifies_return_intent():
    with patch("agent.states.qualification.classify_message", new=_mock_classify("return_request")):
        result = await qualification_node(_state("I'd like to return this dress, it's the wrong size."))

    assert result["intent"] == "return"
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_classifies_complaint_intent():
    with patch("agent.states.qualification.classify_message", new=_mock_classify("quality_complaint")):
        result = await qualification_node(_state("The coat I received is damaged and defective."))

    assert result["intent"] == "complaint"


@pytest.mark.asyncio
async def test_classifies_out_of_scope_and_redirects_without_processing():
    with patch("agent.states.qualification.classify_message", new=_mock_classify("other")):
        result = await qualification_node(_state("What's the discount on your next promo?"))

    assert result["intent"] == "other"
    assert not result.get("escalated")
    assert "service client" in result["reply"]


@pytest.mark.asyncio
async def test_non_delivery_routes_to_complaint_flow_pre_marked_as_already_checked():
    """Return Policy §12/§9: routes into COMPLAINT_FLOW like a quality complaint, but
    pre-marks the verification round as already done — complaint_flow_node's own
    _non_delivery_checked branch then always escalates the customer's next reply rather
    than ever reaching the return-label pipeline."""
    with patch("agent.states.qualification.classify_message", new=_mock_classify("non_delivery")):
        result = await qualification_node(
            _state("mon article n'est pas encore reçu et je ne le trouve pas donc je voudrai avoir un remboursement")
        )

    assert result["intent"] == "complaint"
    assert result["reason"] == "not_received"
    assert result["_non_delivery_checked"] is True
    assert not result.get("escalated")
    assert "vérifier" in result["reply"]


@pytest.mark.asyncio
async def test_ambiguous_asks_a_clarifying_question_then_escalates_after_max_attempts():
    with patch("agent.states.qualification.classify_message", new=_mock_classify("ambiguous")):
        first = await qualification_node(_state("hmm", reformulation_count=0))
        second = await qualification_node(_state("still hmm", reformulation_count=1))
        third = await qualification_node(_state("still unclear", reformulation_count=2))

    assert first["reformulation_count"] == 1
    assert not first.get("escalated")
    assert second["reformulation_count"] == 2
    assert not second.get("escalated")
    assert third["escalated"] is True
    assert third["escalation_reason"] == "qualification_unclear"


@pytest.mark.asyncio
async def test_technical_failure_escalates_rather_than_guessing():
    with patch(
        "agent.states.qualification.classify_message",
        new=AsyncMock(side_effect=TechnicalFailure("llm", RuntimeError("timeout"))),
    ):
        result = await qualification_node(_state("Bonjour"))

    assert result["escalated"] is True
    assert result["escalation_reason"] == "service_unavailable"
