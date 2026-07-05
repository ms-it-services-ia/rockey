"""DECISION node (spec User Story 3, AC3-4): routes to auto-approval, a clear refusal, or a
mandatory escalation — based only on the policy/threshold outcome from VERIFICATION, never
LLM intuition (constitution V.3)."""


async def decision_node(state: dict) -> dict:
    if not state.get("eligible"):
        eligibility_reason = (state.get("action_result") or {}).get("eligibility_reason", "")
        reply = (
            f"I'm sorry, but this isn't eligible for return: {eligibility_reason}. "
            "If you'd still like a colleague to take a closer look, just let me know."
        )
        return {**state, "decision": "refused", "current_state": "DECISION", "reply": reply}

    if (state.get("action_result") or {}).get("auto_approvable"):
        return {**state, "decision": "auto", "current_state": "DECISION"}

    # Eligible, but not auto-approvable — mandatory escalation (constitution II.2/V.4),
    # never a manual override by the agent itself. Two distinct causes share this branch:
    # a return/complaint above the auto-refund threshold, or a complaint past the standard
    # return window but still within the legal warranty (spec US5 edge case) — the
    # `appliedRule` from EligibilityService tells us which, so the escalation summary
    # (escalation.py's _REASON_LABELS) states the real reason rather than always blaming
    # the amount.
    applied_rule = state.get("applied_rule") or ""
    escalation_reason = "legal_warranty" if applied_rule.startswith("legal_warranty") else "amount_above_threshold"
    return {
        **state,
        "decision": "escalated",
        "escalated": True,
        "escalation_reason": escalation_reason,
        "current_state": "DECISION",
    }
