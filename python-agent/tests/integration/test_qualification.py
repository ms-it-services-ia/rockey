"""Integration test: intent classification for return / non-delivery / complaint / other
(spec US2). interpret_turn is mocked throughout (constitution VII.2: LangGraph tests use LLM
mocks, never the real API) — see test_interpret_turn.py for the LLM tool-use wiring itself."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.states.qualification import qualification_node
from agent.tools.interpret_turn import TurnInterpretation
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


def _mock_interpret(signal: str, category: str | None = None) -> AsyncMock:
    return AsyncMock(return_value=TurnInterpretation(signal=signal, category=category))


@pytest.mark.asyncio
async def test_classifies_return_intent():
    with patch("agent.states.qualification.interpret_turn", new=_mock_interpret("on_topic", "return_request")):
        result = await qualification_node(_state("I'd like to return this dress, it's the wrong size."))

    assert result["intent"] == "return"
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_classifies_complaint_intent():
    with patch("agent.states.qualification.interpret_turn", new=_mock_interpret("on_topic", "quality_complaint")):
        result = await qualification_node(_state("The coat I received is damaged and defective."))

    assert result["intent"] == "complaint"


@pytest.mark.asyncio
async def test_classifies_out_of_scope_and_redirects_without_processing():
    with patch("agent.states.qualification.interpret_turn", new=_mock_interpret("on_topic", "other")):
        result = await qualification_node(_state("What's the discount on your next promo?"))

    assert result["intent"] == "other"
    assert not result.get("escalated")
    assert "service client" in result["reply"]


@pytest.mark.asyncio
async def test_non_delivery_routes_to_complaint_flow_pre_marked_as_already_checked():
    """Return Policy §12/§9: routes into COMPLAINT_FLOW like a quality complaint, but
    pre-marks the verification round as already done — complaint_flow_node's own
    _non_delivery_checked branch then decides from there rather than ever reaching the
    return-label pipeline."""
    with patch("agent.states.qualification.interpret_turn", new=_mock_interpret("on_topic", "non_delivery")):
        result = await qualification_node(
            _state("mon article n'est pas encore reçu et je ne le trouve pas donc je voudrai avoir un remboursement")
        )

    assert result["intent"] == "complaint"
    assert result["reason"] == "not_received"
    assert result["_non_delivery_checked"] is True
    assert not result.get("escalated")
    assert "vérifier" in result["reply"]


@pytest.mark.asyncio
async def test_closing_signal_ends_the_session_gracefully():
    with patch("agent.states.qualification.interpret_turn", new=_mock_interpret("closing")):
        result = await qualification_node(_state("ok merci, bonne journée"))

    assert result["_session_ended"] is True
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_resolved_signal_ends_the_session_gracefully():
    with patch("agent.states.qualification.interpret_turn", new=_mock_interpret("resolved")):
        result = await qualification_node(_state("actually never mind, I don't need help anymore"))

    assert result["_session_ended"] is True
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_case_status_question_before_any_case_exists_is_answered_honestly():
    """Regression test: this exact category used to have no explicit handling in
    route_by_category and silently fell through to the ambiguous clarification loop."""
    with patch("agent.states.qualification.interpret_turn", new=_mock_interpret("case_status_question")):
        result = await qualification_node(_state("so will I get my money back?"))

    assert result["current_state"] == "QUALIFICATION"
    assert not result.get("escalated")
    assert result.get("reformulation_count", 0) == 0
    assert "pas encore de demande" in result["reply"]


@pytest.mark.asyncio
async def test_ambiguous_asks_a_clarifying_question_then_escalates_after_max_attempts():
    with patch("agent.states.qualification.interpret_turn", new=_mock_interpret("ambiguous")):
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
async def test_buffered_pre_identification_context_is_classified_together_with_latest_message():
    """Regression test: a customer who already explained their request before identification
    succeeded (buffered into _qualification_context by greeting.py/identification.py) must
    not have to repeat themselves — qualification_node classifies the full buffered context,
    not just whatever (often much vaguer) message happens to arrive once identification is
    done."""
    mock_interpret = _mock_interpret("on_topic", "non_delivery")
    with patch("agent.states.qualification.interpret_turn", new=mock_interpret):
        result = await qualification_node(
            _state(
                "je voudrai avoir un remboursement",
                _qualification_context=["Bonjour, mon colis n'est jamais arrivé"],
            )
        )

    combined = mock_interpret.call_args.args[0]
    assert "colis n'est jamais arrivé" in combined
    assert "remboursement" in combined
    assert result["intent"] == "complaint"
    # Definite classification reached -> the buffer has served its purpose.
    assert result["_qualification_context"] == []


@pytest.mark.asyncio
async def test_ambiguous_classification_keeps_accumulating_the_context_buffer():
    with patch("agent.states.qualification.interpret_turn", new=_mock_interpret("ambiguous")):
        result = await qualification_node(_state("hmm", _qualification_context=["Bonjour"]))

    assert result["_qualification_context"] == ["Bonjour", "hmm"]


@pytest.mark.asyncio
async def test_technical_failure_escalates_rather_than_guessing():
    with patch(
        "agent.states.qualification.interpret_turn",
        new=AsyncMock(side_effect=TechnicalFailure("llm", RuntimeError("timeout"))),
    ):
        result = await qualification_node(_state("Bonjour"))

    assert result["escalated"] is True
    assert result["escalation_reason"] == "service_unavailable"
