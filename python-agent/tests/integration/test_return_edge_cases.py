"""Edge-case tests for RETURN_FLOW/DECISION (spec User Story 3 edge cases)."""

from unittest.mock import AsyncMock, patch

import pytest

from agent.states.decision import decision_node


def _echo_fallback_mock() -> AsyncMock:
    """decision_node's refusal branch now calls generate_decision_explanation (LLM + RAG,
    constitution I.7), which does real network I/O. Echo back the fallback_text it was
    given, so these tests stay deterministic/offline while still exercising the wiring and
    the exact same reply content as before."""
    return AsyncMock(side_effect=lambda **kwargs: kwargs["fallback_text"])


def _base_state(**overrides) -> dict:
    state = {
        "tenant_id": "vinted",
        "order_id": "CMD-2026-00001",
        "order_data": {"amount": 210.0},
        "current_state": "DECISION",
        "escalated": False,
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_final_clearance_item_is_refused_not_escalated():
    """Edge case: item on final clearance -> refusal with the policy reason explained,
    not an automatic escalation."""
    state = _base_state(
        eligible=False,
        action_result={"eligibility_reason": "Item excluded from returns: destockage"},
    )

    with patch("agent.states.decision.generate_decision_explanation", new=_echo_fallback_mock()):
        result = await decision_node(state)

    assert result["decision"] == "refused"
    assert not result["escalated"]
    assert "destockage" in result["reply"]


@pytest.mark.asyncio
async def test_amount_above_auto_refund_threshold_escalates():
    """Edge case: amount above the auto-refund threshold -> escalation with full context,
    even though the item is otherwise eligible."""
    state = _base_state(
        eligible=True,
        action_result={"eligibility_reason": "Eligible for return", "auto_approvable": False},
    )

    result = await decision_node(state)

    assert result["decision"] == "escalated"
    assert result["escalated"] is True
    assert result["escalation_reason"] == "amount_above_threshold"


@pytest.mark.asyncio
async def test_customer_disputes_decision_agent_never_renegotiates():
    """Edge case: customer disputes the refusal -> escalation may be offered, but the agent
    itself never changes the outcome. Calling decision_node again with the same eligibility
    result (simulating the customer pushing back) must be deterministic, not negotiable."""
    state = _base_state(
        eligible=False,
        action_result={"eligibility_reason": "Return window exceeded"},
        # A hypothetical "the customer is unhappy about it" signal must have no effect —
        # decision_node has no override mechanism and ignores unknown fields.
        customer_disputes=True,
    )

    with patch("agent.states.decision.generate_decision_explanation", new=_echo_fallback_mock()):
        first = await decision_node(state)
        second = await decision_node(state)

    assert first["decision"] == second["decision"] == "refused"
    assert first["reply"] == second["reply"]
