"""RETURN_FLOW node (spec User Story 3, AC1): collects the return reason via an LLM call
(research.md §4 applied one level deeper than intent classification — see classify_reason.py
for why exact-phrase keyword matching kept getting outpaced by real customer wording), then
hands off to VERIFICATION — unless the LLM signals genuine ambiguity, in which case it asks
for clarification (up to 2 times, mirroring complaint_flow.py/qualification.py) rather than
silently proceeding with a guessed reason.
"""

import logging

from agent.rag.rag_query import get_article_by_id
from agent.tools.classify_reason import classify_return_reason
from config.circuit_breaker import TechnicalFailure, call_with_breaker

logger = logging.getLogger(__name__)

MAX_CLARIFICATIONS = 2


async def return_flow_node(state: dict) -> dict:
    message = state.get("_latest_message", "")

    try:
        reason = await classify_return_reason(message)
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
