"""Edge-case tests for COMPLAINT_FLOW/DECISION (spec User Story 5 edge cases)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph import run_turn
from agent.states.complaint_flow import MAX_CLARIFICATIONS, complaint_flow_node
from agent.tools.interpret_turn import TurnInterpretation


def _complaint_state(**overrides) -> dict:
    state = {
        "session_id": "s5",
        "tenant_id": "vinted",
        "channel": "web",
        "client_email": "emma.richard@email.com",
        "order_id": "CMD-2026-00005",
        "order_data": {"id": "CMD-2026-00005", "articleId": "VTG-012", "amount": 179.0},
        "intent": "complaint",
        "reformulation_count": 0,
        "escalated": False,
        "current_state": "COMPLAINT_FLOW",
    }
    state.update(overrides)
    return state


def _mock_interpret(signal: str, category: str | None = None) -> AsyncMock:
    return AsyncMock(return_value=TurnInterpretation(signal=signal, category=category))


@pytest.mark.asyncio
async def test_vague_description_asks_for_clarification():
    """Edge case: vague defect description -> agent asks up to 2 clarifying questions."""
    state = _complaint_state(_latest_message="it's bad")

    with patch("agent.states.complaint_flow.interpret_turn", new=_mock_interpret("ambiguous")):
        result = await complaint_flow_node(state)

    assert result["current_state"] == "COMPLAINT_FLOW"
    assert result["_complaint_needs_clarification"] is True
    assert result["reformulation_count"] == 1
    assert not result.get("escalated")
    assert "plus sur le problème" in result["reply"]


@pytest.mark.asyncio
async def test_still_unclear_after_max_clarifications_escalates():
    """After MAX_CLARIFICATIONS, the agent stops asking and escalates (Complaint Policy §4:
    "If the issue remains unclear after 2 clarifications, escalate to a human agent") — it
    must never silently proceed with an unclassified reason and let the case slide into
    auto-approval (constitution V.3)."""
    state = _complaint_state(_latest_message="bad", reformulation_count=MAX_CLARIFICATIONS)

    with patch("agent.states.complaint_flow.interpret_turn", new=_mock_interpret("ambiguous")):
        result = await complaint_flow_node(state)

    assert result["escalated"] is True
    assert result["escalation_reason"] == "qualification_unclear"
    assert result["reason"] == "other"


@pytest.mark.asyncio
async def test_unclassifiable_but_not_short_reason_still_triggers_clarification():
    """Regression test: a message long enough to pass the length check but matching no known
    reason keyword (e.g. a customer's pushback like "I already said the reason") must not be
    silently treated as an understood, resolvable complaint."""
    state = _complaint_state(_latest_message="I already told you the reason for this")

    with patch("agent.states.complaint_flow.interpret_turn", new=_mock_interpret("ambiguous")):
        result = await complaint_flow_node(state)

    assert result["current_state"] == "COMPLAINT_FLOW"
    assert result["_complaint_needs_clarification"] is True
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_closing_signal_during_reason_classification_ends_session_gracefully():
    state = _complaint_state(_latest_message="actually, never mind, forget it")

    with patch("agent.states.complaint_flow.interpret_turn", new=_mock_interpret("closing")):
        result = await complaint_flow_node(state)

    assert result["current_state"] == "CONFIRMATION"
    assert result["_session_ended"] is True
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_case_status_question_during_reason_classification_is_answered_honestly():
    state = _complaint_state(_latest_message="so is this going to be refunded?")

    with patch("agent.states.complaint_flow.interpret_turn", new=_mock_interpret("case_status_question")):
        result = await complaint_flow_node(state)

    assert result["current_state"] == "COMPLAINT_FLOW"
    assert result["_complaint_needs_clarification"] is True
    assert not result.get("escalated")


@pytest.mark.asyncio
async def test_non_delivery_complaint_asks_to_verify_before_escalating_never_auto_resolves():
    """Return Policy §12/§9: a non-delivery claim has no physical item to return — must ask
    the customer to verify with household/neighbors first, then escalate; must never reach
    VERIFICATION/DECISION/AUTO_ACTION (which would generate a nonsensical return label)."""
    state = _complaint_state(_latest_message="I never received my item, nothing in my mailbox.")

    with (
        patch("agent.states.complaint_flow.interpret_turn", new=_mock_interpret("on_topic", "not_received")),
        patch(
            "agent.states.complaint_flow.get_article_by_id",
            new=AsyncMock(return_value={"id": "VTG-012", "returnable": True, "non_return_reason": None}),
        ),
    ):
        first = await complaint_flow_node(state)

    assert first["current_state"] == "COMPLAINT_FLOW"
    assert first["reason"] == "not_received"
    assert not first.get("escalated")
    assert "vérifier" in first["reply"]

    second_state = {**first, "_latest_message": "I checked, no one has it, still missing."}
    with patch(
        "agent.states.complaint_flow.interpret_turn",
        new=_mock_interpret("on_topic", "confirmed_not_found"),
    ):
        second = await complaint_flow_node(second_state)

    assert second["escalated"] is True
    assert second["escalation_reason"] == "non_delivery_claim"
    assert second["reason"] == "not_received"


@pytest.mark.asyncio
async def test_non_delivery_verification_not_yet_done_asks_again_instead_of_escalating():
    """Regression test: a customer replying "I haven't checked yet" to the household/
    neighbors verification question must not be treated as if they'd confirmed the package
    is missing — the bot previously escalated unconditionally on any reply at all."""
    state = _complaint_state(
        _latest_message="not yet, I'll check tonight",
        reason="not_received",
        _non_delivery_checked=True,
    )

    with patch(
        "agent.states.complaint_flow.interpret_turn",
        new=_mock_interpret("on_topic", "not_yet_checked"),
    ):
        result = await complaint_flow_node(state)

    assert not result.get("escalated")
    assert result["current_state"] == "COMPLAINT_FLOW"
    assert result["_complaint_needs_clarification"] is True
    assert "vérifier" in result["reply"]


@pytest.mark.asyncio
async def test_non_delivery_verification_stalled_escalates_after_max_clarifications():
    state = _complaint_state(
        _latest_message="I still haven't had time to check",
        reason="not_received",
        _non_delivery_checked=True,
        reformulation_count=2,
    )

    with patch(
        "agent.states.complaint_flow.interpret_turn",
        new=_mock_interpret("on_topic", "not_yet_checked"),
    ):
        result = await complaint_flow_node(state)

    assert result["escalated"] is True
    assert result["escalation_reason"] == "non_delivery_claim"


@pytest.mark.asyncio
async def test_customer_found_the_package_during_verification_is_not_escalated():
    """Regression test: this is the exact bug that motivated consolidating classification
    into interpret_turn — classify_verification_reply's fixed enum
    (confirmed_not_found | not_yet_checked | ambiguous) had no room for "I found it", so it
    got folded into ambiguous and escalated anyway. The universal "resolved" signal fixes
    this at every node, not just this one."""
    state = _complaint_state(
        _latest_message="Oh actually I found it, it was at my neighbor's, sorry for the trouble!",
        reason="not_received",
        _non_delivery_checked=True,
    )

    with patch("agent.states.complaint_flow.interpret_turn", new=_mock_interpret("resolved")):
        result = await complaint_flow_node(state)

    assert not result.get("escalated")
    assert result["current_state"] == "CONFIRMATION"
    assert result["_session_ended"] is True
    assert result["reason"] is None


@pytest.mark.asyncio
async def test_case_status_question_during_verification_is_answered_and_loops_back():
    state = _complaint_state(
        _latest_message="donc c'est possible que je serai remboursé ?",
        reason="not_received",
        _non_delivery_checked=True,
    )

    with patch("agent.states.complaint_flow.interpret_turn", new=_mock_interpret("case_status_question")):
        result = await complaint_flow_node(state)

    assert not result.get("escalated")
    assert result["current_state"] == "COMPLAINT_FLOW"
    assert result["_complaint_needs_clarification"] is True


@pytest.mark.asyncio
async def test_complaint_past_return_window_escalates_under_legal_warranty():
    """Edge case: complaint filed after the standard return window -> legal warranty
    applies -> escalation with a note explaining why (not a refusal, not silently resolved)."""
    state = _complaint_state(_latest_message="This coat turned out to be defective after all.")

    with (
        patch("agent.states.complaint_flow.interpret_turn", new=_mock_interpret("on_topic", "quality_defect")),
        patch(
            "agent.states.complaint_flow.get_article_by_id",
            new=AsyncMock(return_value={"id": "VTG-012", "returnable": True, "non_return_reason": None}),
        ),
        patch(
            "agent.states.complaint_flow.record_complaint",
            new=AsyncMock(return_value={"priorComplaintCount": 0, "isRepeat": False}),
        ),
        patch(
            "agent.states.verification.verify_eligibility",
            new=AsyncMock(
                return_value={
                    "eligible": True,
                    "autoApprovable": False,
                    "reason": "Past the standard return window — legal warranty applies",
                    "appliedRule": "legal_warranty:730d",
                }
            ),
        ),
        patch(
            "agent.states.escalation.escalate_to_human",
            new=AsyncMock(return_value={"ticketId": "TCK-warranty1", "delay": "within 24 business hours"}),
        ),
    ):
        result = await run_turn(state)

    assert result["current_state"] == "CONFIRMATION"
    assert result["escalated"] is True
