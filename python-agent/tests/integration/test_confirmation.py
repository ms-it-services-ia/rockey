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
async def test_non_closing_message_after_confirmation_acknowledges_without_repeating():
    state = _base_state(
        decision="auto",
        case_id="RET-abcd1234",
        action_result={"summary": "your return has been approved"},
        _confirmation_shown=True,
        reply="Here's a summary of your request...",
        _latest_message="Actually, what about my other order?",
    )

    result = await confirmation_node(state)

    assert "RET-abcd1234" not in result["reply"]
    assert not result.get("_session_ended")
