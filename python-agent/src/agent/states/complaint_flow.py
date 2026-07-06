"""COMPLAINT_FLOW node (spec User Story 5, AC1-2): collects the complaint reason via an LLM
call (research.md §4 applied one level deeper than intent classification — see
classify_reason.py for why exact-phrase keyword matching kept getting outpaced by real
customer wording), detects repeated complaints on the same item, and asks for clarification
only when the LLM itself signals genuine ambiguity.
"""

import logging

from agent.memory.history_store import record_complaint
from agent.rag.rag_query import get_article_by_id
from agent.tools.classify_reason import classify_complaint_reason
from config.circuit_breaker import TechnicalFailure, call_with_breaker

logger = logging.getLogger(__name__)

MAX_CLARIFICATIONS = 2


async def complaint_flow_node(state: dict) -> dict:
    message = state.get("_latest_message", "")

    # Follow-up to the non-delivery verification question below — the customer is reporting
    # back whether they found the package, not restating the complaint reason, so this must
    # not be re-classified from scratch.
    if state.get("_non_delivery_checked"):
        return {
            **state,
            "reason": "not_received",
            "escalated": True,
            "escalation_reason": "non_delivery_claim",
            "current_state": "COMPLAINT_FLOW",
            "reply": (
                "Je comprends, je fais intervenir un collègue pour investiguer ce qui "
                "s'est passé avec la livraison et trouver la meilleure solution."
            ),
        }

    try:
        reason = await classify_complaint_reason(message)
    except TechnicalFailure:
        return {
            **state,
            "escalated": True,
            "escalation_reason": "service_unavailable",
            "current_state": "COMPLAINT_FLOW",
            "reply": (
                "J'ai des difficultés à traiter votre demande en ce moment — je vous "
                "transfère à un collègue."
            ),
        }

    # Genuinely undeterminable -> ask up to 2 clarifying questions (Complaint Policy §4),
    # then escalate. The LLM signaling ambiguity replaces the old length-based heuristic and
    # "reason == other" proxy — a classifiable-but-uncommon reason ("other") now proceeds
    # normally instead of being mistaken for vagueness.
    if reason == "ambiguous":
        reformulations = state.get("reformulation_count", 0) + 1
        logger.warning("COMPLAINT_REASON_AMBIGUOUS message=%r reformulation=%d", message, reformulations)
        if reformulations <= MAX_CLARIFICATIONS:
            reply = (
                "Pourriez-vous m'en dire un peu plus sur le problème ? Par exemple, "
                "qu'est-ce qui ne va pas exactement avec l'article ?"
            )
            return {
                **state,
                "reformulation_count": reformulations,
                "_complaint_needs_clarification": True,
                "current_state": "COMPLAINT_FLOW",
                "reply": reply,
            }

        # Still unclear after MAX_CLARIFICATIONS -> escalate (Complaint Policy §4: "If the
        # issue remains unclear after 2 clarifications, escalate to a human agent";
        # constitution V.3 never lets an unclassified case slide through to auto-approval).
        logger.error("COMPLAINT_REASON_ESCALATED_AMBIGUOUS message=%r after %d clarifications", message, reformulations)
        return {
            **state,
            "reformulation_count": reformulations,
            "reason": "other",
            "complaint_description": message,
            "escalated": True,
            "escalation_reason": "qualification_unclear",
            "current_state": "COMPLAINT_FLOW",
            "reply": (
                "Je ne parviens pas à cerner clairement le problème malgré nos échanges — "
                "je fais intervenir un collègue qui pourra l'examiner plus en détail."
            ),
        }

    article_id = (state.get("order_data") or {}).get("articleId")
    article_data = await call_with_breaker(
        "pgvector", lambda: get_article_by_id(article_id, state["tenant_id"])
    )

    # Return Policy §12 / §9: a non-delivery claim has no physical item to return, so it
    # must never flow into the standard return-label + refund pipeline. The policy calls for
    # one round of verification (check with household/neighbors) before treating it as a
    # genuine claim, which then always needs human investigation (constitution V.4) — never
    # a threshold-based auto-decision the way a normal complaint amount would get.
    if reason == "not_received":
        return {
            **state,
            "reason": reason,
            "complaint_description": message,
            "article_data": article_data,
            "_non_delivery_checked": True,
            # Reuses the same "wait for the customer's next message" signal as the
            # ambiguous-description clarification above (_route_after_complaint_flow loops
            # back to COMPLAINT_FLOW either way) — this isn't a vague description, but it
            # equally needs one more round-trip before a decision can be made.
            "_complaint_needs_clarification": True,
            "current_state": "COMPLAINT_FLOW",
            "reply": (
                "Je suis désolée de l'apprendre. Avant d'aller plus loin, pourriez-vous "
                "vérifier auprès des personnes de votre foyer, de la réception de votre "
                "immeuble ou de vos voisins, au cas où le colis aurait été réceptionné "
                "par quelqu'un d'autre ?"
            ),
        }

    # Edge case (spec US5): repeated complaint about the same item -> automatic escalation
    # with the item's complaint history attached.
    history = await record_complaint(state["tenant_id"], state["client_email"])
    if history.get("isRepeat"):
        return {
            **state,
            "reason": reason,
            "complaint_description": message,
            "article_data": article_data,
            "escalated": True,
            "escalation_reason": "repeated_complaint",
            "current_state": "COMPLAINT_FLOW",
            "reply": (
                "Je vois que vous avez déjà signalé un problème avec cet article — je fais "
                "intervenir un collègue qui pourra consulter l'historique complet et vous "
                "aider à résoudre cela."
            ),
        }

    return {
        **state,
        "reason": reason,
        "complaint_description": message,
        "article_data": article_data,
        "_complaint_needs_clarification": False,
        "current_state": "COMPLAINT_FLOW",
    }
