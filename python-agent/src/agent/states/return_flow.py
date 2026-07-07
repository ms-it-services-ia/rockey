"""RETURN_FLOW node (spec User Story 3, AC1): collects the return reason via interpret_turn
(research.md §4 applied one level deeper than intent classification — see
tools/interpret_turn.py for why a per-node hand-rolled enum kept missing real-world outcomes),
then hands off to VERIFICATION — unless the LLM signals genuine ambiguity, in which case it
asks for clarification (up to 2 times, mirroring complaint_flow.py/qualification.py) rather
than silently proceeding with a guessed reason.
"""

import logging

from agent.rag.rag_query import get_article_by_id
from agent.tools.interpret_turn import TurnCategory, interpret_turn
from config.circuit_breaker import TechnicalFailure, call_with_breaker

logger = logging.getLogger(__name__)

MAX_CLARIFICATIONS = 2

_REASON_CONTEXT = "The customer already indicated they want to return an item they have in hand; classify why."

_REASON_CATEGORIES = [
    TurnCategory("wrong_size", "the item doesn't fit — too small, too big, wrong size"),
    TurnCategory(
        "change_of_mind",
        "the customer simply no longer wants the item, changed their mind, or has a "
        "different preference — unrelated to any defect",
    ),
    TurnCategory(
        "non_conforming",
        "the item doesn't match its listing (wrong material, wrong color) but the customer "
        "has it in hand and isn't describing damage or a missing item",
    ),
    TurnCategory("not_received", "the customer never received the item, it's lost, missing, or untraceable"),
    TurnCategory("other", "a genuine, understood return reason that just doesn't fit any of the above categories"),
]


async def return_flow_node(state: dict) -> dict:
    message = state.get("_latest_message", "")

    try:
        interpretation = await interpret_turn(message, _REASON_CONTEXT, _REASON_CATEGORIES)
    except TechnicalFailure:
        return {
            **state,
            "escalated": True,
            "escalation_reason": "service_unavailable",
            "current_state": "RETURN_FLOW",
            "reply": (
                "J'ai des difficultés à traiter votre demande en ce moment — je vous "
                "transfère à un collègue."
            ),
        }

    if interpretation.signal in ("closing", "resolved"):
        # Nothing has been recorded yet — the customer is withdrawing the return before
        # we've done anything technical with it; end warmly rather than forcing a category.
        return {
            **state,
            "current_state": "CONFIRMATION",
            "reply": "Entendu, n'hésitez pas si vous avez besoin d'autre chose.",
            "_session_ended": True,
        }

    if interpretation.signal == "case_status_question":
        return {
            **state,
            "current_state": "RETURN_FLOW",
            "_return_needs_clarification": True,
            "reply": (
                "Je n'ai pas encore de dossier en cours — dites-moi la raison de ce retour "
                "et je m'en occupe."
            ),
        }

    reason = interpretation.category if interpretation.signal == "on_topic" else "ambiguous"

    if reason == "ambiguous":
        reformulations = state.get("reformulation_count", 0) + 1
        logger.warning("RETURN_REASON_AMBIGUOUS message=%r reformulation=%d", message, reformulations)
        if reformulations <= MAX_CLARIFICATIONS:
            reply = (
                "Pourriez-vous m'en dire un peu plus sur la raison de ce retour ? Par "
                "exemple, la taille, la couleur, ou un changement d'avis ?"
            )
            return {
                **state,
                "reformulation_count": reformulations,
                "_return_needs_clarification": True,
                "current_state": "RETURN_FLOW",
                "reply": reply,
            }

        # Still unclear after MAX_CLARIFICATIONS -> escalate, same policy as
        # complaint_flow.py/qualification.py (constitution V.3 never lets an unclassified
        # case slide through to auto-approval).
        logger.error("RETURN_REASON_ESCALATED_AMBIGUOUS message=%r after %d clarifications", message, reformulations)
        return {
            **state,
            "reformulation_count": reformulations,
            "reason": "other",
            "escalated": True,
            "escalation_reason": "qualification_unclear",
            "current_state": "RETURN_FLOW",
            "reply": (
                "Je ne parviens pas à cerner clairement la raison malgré nos échanges — "
                "je fais intervenir un collègue qui pourra l'examiner plus en détail."
            ),
        }

    article_id = (state.get("order_data") or {}).get("articleId")
    article_data = await call_with_breaker(
        "pgvector", lambda: get_article_by_id(article_id, state["tenant_id"])
    )

    return {
        **state,
        "reason": reason,
        "article_data": article_data,
        "_return_needs_clarification": False,
        "current_state": "RETURN_FLOW",
    }
