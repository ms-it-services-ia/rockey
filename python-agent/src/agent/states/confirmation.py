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

Once shown, any further message was previously swallowed into a single static "I'm
listening" reply no matter what it said — a case-status question ("will I get refunded?")
and a wholly unrelated question (item price) both got the identical non-answer, and neither
was ever actually processed again (spec FR-010 intends a clean close, not a dead end). Fixed
here by reusing classify_message (research.md §4) on every post-confirmation message: a
genuine status question gets an honest answer from the case's own state; anything else is
treated as a new request and re-routed through qualification.route_by_category exactly as a
fresh QUALIFICATION cycle would, keeping the customer already identified.
"""

from agent.states.qualification import route_by_category, route_intent
from agent.tools.classify_message import classify_message
from agent.tools.record_refusal import record_refusal
from config.circuit_breaker import TechnicalFailure

_CLOSING_KEYWORDS = (
    "no thanks",
    "no, thanks",
    "nothing else",
    "that's all",
    "that's it",
    "i'm good",
    "non merci",
    "non, merci",
    "rien d'autre",
    "c'est tout",
    "ça sera tout",
    "c'est bon",
)


def _is_closing_message(message: str) -> bool:
    lowered = message.strip().lower()
    return any(kw in lowered for kw in _CLOSING_KEYWORDS)


def _case_status_reply(state: dict) -> str:
    """An honest answer about the existing case's actual outcome — never a guess or a
    guarantee this node has no authority to make (constitution V.3: the eligibility/refund
    decision is Java's, not this node's)."""
    if state.get("escalated"):
        return (
            "Votre dossier a été transmis à un collègue qui va l'examiner et vous confirmera "
            "l'issue exacte — je ne peux pas garantir le résultat moi-même, mais vous serez "
            "tenu(e) informé(e) sous 24 heures ouvrées."
        )
    if state.get("decision") == "refused":
        return (
            "Comme indiqué précédemment, cette demande n'a pas pu être approuvée. Si vous "
            "souhaitez qu'un collègue réexamine votre dossier, dites-le-moi et je fais le "
            "nécessaire."
        )
    if state.get("intent") == "other":
        return (
            "Je n'ai pas encore traité de retour ou de réclamation pour vous dans cet "
            "échange — dites-moi précisément ce dont vous avez besoin et je m'en occupe."
        )
    return (
        "Votre demande a déjà été approuvée et traitée — le retour ou remboursement indiqué "
        "plus haut est en cours, vous n'avez rien d'autre à faire de votre côté."
    )


# Fields tied to the case that was just closed — reset before re-routing a genuinely new or
# unrelated post-confirmation request through qualification.route_by_category, so it starts
# as cleanly as a fresh QUALIFICATION cycle would (constitution VI.1: no stale case_id/
# attachments/decision leaking into an unrelated new request).
_RESET_FOR_NEW_REQUEST = {
    "intent": None,
    "reason": None,
    "complaint_description": None,
    "escalated": False,
    "escalation_reason": None,
    "decision": None,
    "applied_rule": None,
    "action_result": None,
    "article_data": None,
    "case_id": None,
    "return_id": None,
    "refund_id": None,
    "ticket_id": None,
    "attachments": [],
    "reformulation_count": 0,
    "_confirmation_shown": False,
    "_complaint_needs_clarification": False,
    "_return_needs_clarification": False,
    "_non_delivery_checked": False,
}


async def confirmation_node(state: dict) -> dict:
    # Once CONFIRMATION has been reached and shown once, classify the new message instead of
    # swallowing it into a static reply — a closing acknowledgment ends the session, a
    # question about the existing case gets an honest status answer, and anything else is a
    # new or unrelated request re-routed through the normal intent-classification pipeline.
    if state.get("_confirmation_shown"):
        message = state.get("_latest_message", "")
        if _is_closing_message(message):
            return {
                **state,
                "current_state": "CONFIRMATION",
                "reply": "Avec plaisir ! N'hésitez pas à revenir vers nous si vous avez besoin d'autre chose.",
                "_session_ended": True,
            }

        try:
            category = await classify_message(message)
        except TechnicalFailure:
            return {
                **state,
                "escalated": True,
                "escalation_reason": "service_unavailable",
                "current_state": "CONFIRMATION",
                "reply": (
                    "J'ai des difficultés à traiter votre demande en ce moment — je vous "
                    "transfère à un collègue."
                ),
            }

        if category == "case_status_question":
            return {**state, "current_state": "CONFIRMATION", "reply": _case_status_reply(state)}

        # Any other category — a new return/complaint, or something genuinely unrelated
        # (category "other") — is not a follow-up on the closed case, so it must not ride on
        # its resolved state (constitution V.3: never let a new request slide through
        # unclassified). Reset and hand off to the exact same routing qualification_node
        # uses, reusing the category already classified above instead of a second LLM call.
        result = route_by_category({**state, **_RESET_FOR_NEW_REQUEST}, category)
        next_state = route_intent(result)
        result["current_state"] = next_state
        if next_state == "CONFIRMATION":
            # intent == "other": this result IS the reply the customer gets this turn, so
            # it's already "shown" — otherwise the next message would hit the stale
            # intent == "other" branch below instead of being classified fresh.
            result["_confirmation_shown"] = True
        return result

    if state.get("escalated"):
        # escalation.py already composed the full hand-off message (ticket reference,
        # business-hours note if applicable) — nothing to add.
        return {**state, "current_state": "CONFIRMATION", "_confirmation_shown": True}

    if state.get("intent") == "other":
        # Out-of-scope redirect — qualification.py's reply already stands alone.
        return {**state, "current_state": "CONFIRMATION", "_confirmation_shown": True}

    if state.get("decision") == "refused":
        order_data = state.get("order_data") or {}
        base_reply = state.get("reply", "Cette demande n'a pas pu être approuvée.")
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
            return {**state, "current_state": "CONFIRMATION", "reply": base_reply, "_confirmation_shown": True}

        # base_reply may be LLM-composed in the tenant's configured language (constitution
        # I.7) and is already a complete, self-contained message — appending an English
        # sentence here would mix languages, so the case reference is tagged in a
        # language-neutral bracketed form instead.
        case_id = refusal_record.get("caseId")
        reply = f"{base_reply} [{case_id}]"
        return {
            **state,
            "case_id": case_id,
            "current_state": "CONFIRMATION",
            "reply": reply,
            "_confirmation_shown": True,
        }

    # Auto-approved happy path (decision == "auto"): compose the closing summary here —
    # AUTO_ACTION deliberately leaves the final customer-facing reply to this node.
    action = state.get("action_result") or {}
    case_id = state.get("case_id") or "N/A"
    reply = (
        f"Voici un résumé de votre demande (dossier {case_id}) : "
        f"{action.get('summary', 'votre demande a été traitée')}. "
        "Puis-je encore vous aider avec autre chose ?"
    )
    return {**state, "current_state": "CONFIRMATION", "reply": reply, "_confirmation_shown": True}
