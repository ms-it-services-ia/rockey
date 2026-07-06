"""DECISION node (spec User Story 3, AC3-4): routes to auto-approval, a clear refusal, or a
mandatory escalation — based only on the policy/threshold outcome from VERIFICATION, never
LLM intuition (constitution V.3)."""

from agent.tools.generate_decision_explanation import generate_decision_explanation

# EligibilityService.java's reason strings are hardcoded English (the eligibility decision
# itself is Java's, constitution V.3) — translated here for the rare fallback_reply path
# (generate_decision_explanation's own Claude-composed text already reads and writes French
# regardless of this; this only covers the case where that call itself fails). Falls back to
# the raw English string if a reason isn't recognized, rather than guessing a translation.
_ELIGIBILITY_REASON_FR = {
    "Return window exceeded": "le délai de retour est dépassé",
    "Legal warranty period expired": "la période de garantie légale est expirée",
    "Item excluded from returns: piece_unique": "cet article est une pièce unique, exclue des retours",
    "Item excluded from returns: destockage": "cet article est un article de déstockage, exclu des retours",
    "Item excluded from returns: bijou": "cet article est un bijou, exclu des retours pour raisons d'hygiène",
    "Item excluded from returns: ceinture": "cette ceinture est exclue des retours pour raisons d'hygiène",
}


async def decision_node(state: dict) -> dict:
    if not state.get("eligible"):
        eligibility_reason = (state.get("action_result") or {}).get("eligibility_reason", "")
        reason_fr = _ELIGIBILITY_REASON_FR.get(eligibility_reason, eligibility_reason)
        fallback_reply = (
            f"Je suis désolée, mais ceci n'est pas éligible au retour : {reason_fr}. Si "
            "vous souhaitez malgré tout qu'un collègue examine votre dossier de plus près, "
            "faites-le-moi savoir."
        )
        # Constitution I.7: ground the refusal's phrasing in the retailer's actual
        # RAG-retrieved policy text via Claude — the refusal itself was already decided by
        # EligibilityService above (constitution V.3), this only composes how it reads.
        reply = await generate_decision_explanation(
            tenant_id=state["tenant_id"],
            channel=state.get("channel", "web"),
            current_state="DECISION",
            question=(
                "Explain to the customer, in 2-3 complete sentences, briefly and kindly, why "
                f"their request was refused: {eligibility_reason}. End with a warm closing "
                "sentence inviting them to reach out if they have further questions. Write the "
                "entire reply in the persona's configured language, and make sure it is fully "
                "self-contained — no other text will be appended after it."
            ),
            article_context=(state.get("article_data") or {}).get("name", ""),
            fallback_text=fallback_reply,
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
