"""Integration test: closing summary contains case number, action, processing time, next
step (spec User Story 6)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.states.confirmation import confirmation_node


def _base_state(**overrides) -> dict:
    state = {
        "session_id": "s1",
        "tenant_id": "vinted",
        "channel": "web",
        "client_email": "marie.dupont@email.com",
        "order_id": "CMD-2026-00001",
        "order_data": {"articleId": "VTG-001", "amount": 68.0},
        "current_state": "CONFIRMATION",
        "escalated": False,
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_auto_approved_summary_contains_case_number_and_offers_more_help():
    state = _base_state(
        decision="auto",
        case_id="RET-abcd1234",
        action_result={"summary": "your return has been approved — label: https://x/y.pdf"},
    )

    result = await confirmation_node(state)

    assert "RET-abcd1234" in result["reply"]
    assert "approved" in result["reply"]
    assert "aider avec autre chose" in result["reply"]


@pytest.mark.asyncio
async def test_refused_case_is_persisted_and_reply_preserves_the_original_refusal_reason():
    state = _base_state(
        decision="refused",
        intent="return",
        reply="I'm sorry, but this isn't eligible for return: Item excluded from returns: piece_unique.",
        action_result={"eligibility_reason": "Item excluded from returns: piece_unique"},
    )

    with patch(
        "agent.states.confirmation.record_refusal",
        new=AsyncMock(return_value={"caseId": "case-uuid-123"}),
    ) as mock_record:
        result = await confirmation_node(state)

    mock_record.assert_awaited_once()
    assert result["case_id"] == "case-uuid-123"
    assert "piece_unique" in result["reply"]
    assert "case-uuid-123" in result["reply"]


@pytest.mark.asyncio
async def test_escalated_case_preserves_escalation_nodes_reply_unchanged():
    """Regression test: confirmation must NOT recompute/overwrite the reply escalation.py
    already composed (e.g. its business-hours note)."""
    state = _base_state(
        escalated=True,
        ticket_id="TCK-abcd1234",
        reply="I'm sorry I couldn't fully resolve this myself... offline outside business hours.",
    )

    result = await confirmation_node(state)

    assert result["reply"] == state["reply"]


@pytest.mark.asyncio
async def test_out_of_scope_case_preserves_qualifications_redirect_reply():
    state = _base_state(intent="other", reply="That's outside what I can help with here.")

    result = await confirmation_node(state)

    assert result["reply"] == state["reply"]


@pytest.mark.asyncio
async def test_first_visit_marks_confirmation_as_shown():
    state = _base_state(
        decision="auto",
        case_id="RET-abcd1234",
        action_result={"summary": "your return has been approved"},
    )

    result = await confirmation_node(state)

    assert result["_confirmation_shown"] is True


@pytest.mark.asyncio
async def test_closing_message_after_confirmation_ends_the_session_instead_of_repeating():
    """Regression test: previously, every message received after CONFIRMATION re-ran the
    same branch and repeated the exact same closing summary verbatim, forever, since nothing
    looked at the new message content at all."""
    state = _base_state(
        decision="auto",
        case_id="RET-abcd1234",
        action_result={"summary": "your return has been approved"},
        _confirmation_shown=True,
        reply="Here's a summary of your request...",
        _latest_message="No thanks, that's all!",
    )

    result = await confirmation_node(state)

    assert result["reply"] != state["reply"]
    assert "RET-abcd1234" not in result["reply"]
    assert result["_session_ended"] is True


@pytest.mark.asyncio
async def test_case_status_question_after_escalation_gives_honest_answer_not_silence():
    """Regression test: previously EVERY post-confirmation message (closing or not) got the
    identical static "I'm listening" reply — a genuine question about the case's outcome
    ("will I get refunded?") deserves an honest answer grounded in the case's actual state,
    not a non-answer, and constitution V.3 forbids this node from guessing/promising an
    outcome it doesn't own."""
    state = _base_state(
        escalated=True,
        ticket_id="TCK-abcd1234",
        _confirmation_shown=True,
        reply="I'm sorry I couldn't fully resolve this myself...",
        _latest_message="donc c'est possible que je serai remboursé ?",
    )

    with patch(
        "agent.states.confirmation.classify_message", new=AsyncMock(return_value="case_status_question")
    ):
        result = await confirmation_node(state)

    assert result["current_state"] == "CONFIRMATION"
    assert not result.get("_session_ended")
    assert "collègue" in result["reply"]
    assert "garantir" in result["reply"]


@pytest.mark.asyncio
async def test_case_status_question_after_auto_approval_confirms_already_processed():
    state = _base_state(
        decision="auto",
        case_id="RET-abcd1234",
        action_result={"summary": "votre retour a été approuvé"},
        _confirmation_shown=True,
        reply="Voici un résumé de votre demande...",
        _latest_message="donc c'est bien remboursé ?",
    )

    with patch(
        "agent.states.confirmation.classify_message", new=AsyncMock(return_value="case_status_question")
    ):
        result = await confirmation_node(state)

    assert result["current_state"] == "CONFIRMATION"
    assert "déjà été approuvée" in result["reply"]


@pytest.mark.asyncio
async def test_new_return_request_after_confirmation_resets_state_and_reenters_return_flow():
    """Regression test: an unrelated new request arriving after a case is closed must not be
    silently absorbed by the generic reply — it re-enters the same intent-classification
    pipeline QUALIFICATION uses, starting clean (no stale case_id/attachments/decision from
    the case that was just closed)."""
    state = _base_state(
        decision="auto",
        case_id="RET-abcd1234",
        return_id="RET-abcd1234",
        refund_id="RFD-abcd1234",
        action_result={"summary": "votre retour a été approuvé"},
        attachments=[{"type": "return_label", "url": "https://x/y.pdf"}],
        _confirmation_shown=True,
        reply="Voici un résumé de votre demande...",
        _latest_message="En fait, j'ai un autre article à retourner, il est trop grand.",
    )

    with patch(
        "agent.states.confirmation.classify_message", new=AsyncMock(return_value="return_request")
    ):
        result = await confirmation_node(state)

    assert result["intent"] == "return"
    assert result["current_state"] == "RETURN_FLOW"
    assert result["case_id"] is None
    assert result["return_id"] is None
    assert result["attachments"] == []
    assert not result["escalated"]
    assert "RET-abcd1234" not in result["reply"]


@pytest.mark.asyncio
async def test_unrelated_question_after_confirmation_is_answered_and_marked_shown():
    state = _base_state(
        decision="auto",
        case_id="RET-abcd1234",
        action_result={"summary": "votre retour a été approuvé"},
        _confirmation_shown=True,
        reply="Voici un résumé de votre demande...",
        _latest_message="c'est quoi le prix de mon article",
    )

    with patch("agent.states.confirmation.classify_message", new=AsyncMock(return_value="other")):
        result = await confirmation_node(state)

    assert result["intent"] == "other"
    assert result["current_state"] == "CONFIRMATION"
    assert result["_confirmation_shown"] is True
    assert "RET-abcd1234" not in result["reply"]


@pytest.mark.asyncio
async def test_technical_failure_classifying_post_confirmation_message_escalates():
    from config.circuit_breaker import TechnicalFailure

    state = _base_state(
        decision="auto",
        case_id="RET-abcd1234",
        _confirmation_shown=True,
        reply="Voici un résumé de votre demande...",
        _latest_message="et pour mon autre commande ?",
    )

    with patch(
        "agent.states.confirmation.classify_message", side_effect=TechnicalFailure("llm", RuntimeError("boom"))
    ):
        result = await confirmation_node(state)

    assert result["escalated"] is True
    assert result["escalation_reason"] == "service_unavailable"
