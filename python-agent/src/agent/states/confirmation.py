"""CONFIRMATION node (spec User Story 6): closes out every flow with a case number, the
action taken, and an offer of further help — for resolved, refused, and escalated cases
alike (spec FR-010). Also persists a Dossier for refused cases (T072) so every processed
request is tracked, matching what AUTO_ACTION/ESCALATION already do for approved/escalated
ones.

Earlier versions of this node unconditionally recomputed `reply` from scratch, silently
discarding the specific message ESCALATION or DECISION had already composed (e.g.
escalation.py's business-hours note). Fixed here: this node only *composes* the reply for
the happy (auto-approved) path; for escalated/refused/out-of-scope cases it builds on what's
already there.
"""

from agent.tools.record_refusal import record_refusal
from config.circuit_breaker import TechnicalFailure


async def confirmation_node(state: dict) -> dict:
    if state.get("escalated"):
        # escalation.py already composed the full hand-off message (ticket reference,
        # business-hours note if applicable) — nothing to add.
        return {**state, "current_state": "CONFIRMATION"}

    if state.get("intent") == "other":
        # Out-of-scope redirect — qualification.py's reply already stands alone.
        return {**state, "current_state": "CONFIRMATION"}

    if state.get("decision") == "refused":
        order_data = state.get("order_data") or {}
        base_reply = state.get("reply", "This request could not be approved.")
        try:
            refusal_record = await record_refusal(
                order_id=state.get("order_id") or "unknown",
                tenant_id=state["tenant_id"],
                article_id=order_data.get("articleId"),
                client_email=state.get("client_email") or "unknown",
                dossier_type=state.get("intent", "return"),
                reason=(state.get("action_result") or {}).get("eligibility_reason", ""),
                amount=order_data.get("amount", 0.0),
                channel=state["channel"],
                session_id=state["session_id"],
                applied_rule=state.get("applied_rule", ""),
            )
        except TechnicalFailure:
            # Never let a raw technical error reach the customer (constitution VI.1) —
            # the refusal itself already stands; only the case-tracking record failed.
            # base_reply is already a complete, self-contained message (see decision.py's
            # prompt), so nothing further needs to be appended here.
            return {**state, "current_state": "CONFIRMATION", "reply": base_reply}

        # base_reply may be LLM-composed in the tenant's configured language (constitution
        # I.7) and is already a complete, self-contained message — appending an English
        # sentence here would mix languages, so the case reference is tagged in a
        # language-neutral bracketed form instead.
        case_id = refusal_record.get("caseId")
        reply = f"{base_reply} [{case_id}]"
        return {**state, "case_id": case_id, "current_state": "CONFIRMATION", "reply": reply}

    # Auto-approved happy path (decision == "auto"): compose the closing summary here —
    # AUTO_ACTION deliberately leaves the final customer-facing reply to this node.
    action = state.get("action_result") or {}
    case_id = state.get("case_id") or "N/A"
    reply = (
        f"Here's a summary of your request (case {case_id}): "
        f"{action.get('summary', 'your request has been processed')}. "
        "Is there anything else I can help you with?"
    )
    return {**state, "current_state": "CONFIRMATION", "reply": reply}
