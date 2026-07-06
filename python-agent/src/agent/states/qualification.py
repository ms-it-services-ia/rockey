"""QUALIFICATION node (spec User Story 2, FR-003/FR-004). Classifies intent as a return
request, a non-delivery claim, a quality complaint, or out-of-scope, via an LLM call
(research.md §4) — asking at most 2 clarifying questions when the LLM itself signals genuine
ambiguity, never by matching exact phrases.

Constitution V.3 still holds: classify_message only classifies *what the customer is asking
for* — it never decides an eligibility/refund outcome, which stays 100% rule-based in Java's
EligibilityService.
"""

import logging

from agent.tools.classify_message import classify_message
from config.circuit_breaker import TechnicalFailure

logger = logging.getLogger(__name__)

MAX_CLARIFICATIONS = 2

_CATEGORY_TO_INTENT = {
    "return_request": "return",
    "quality_complaint": "complaint",
    "other": "other",
}


async def qualification_node(state: dict) -> dict:
    message = state.get("_latest_message", "")

    try:
        category = await classify_message(message)
    except TechnicalFailure:
        return {
            **state,
            "escalated": True,
            "escalation_reason": "service_unavailable",
            "current_state": "QUALIFICATION",
            "reply": "J'ai des difficultés à traiter votre demande en ce moment — je vous transfère à un collègue.",
        }

    return route_by_category(state, category)


def route_by_category(state: dict, category: str) -> dict:
    """Everything qualification_node does once a category is known — factored out so
    confirmation_node can reuse it for a new/unrelated request classified after a case has
    already been closed, reusing the classify_message call it already made instead of a
    second one (see confirmation.py)."""
    message = state.get("_latest_message", "")

    if category == "other":
        reply = (
            "Cela sort un peu de ce que je peux traiter ici — je m'occupe des retours et "
            "des réclamations qualité. Pour cette question, notre service client habituel "
            "sera mieux placé pour vous répondre."
        )
        return {**state, "intent": "other", "current_state": "QUALIFICATION", "reply": reply}

    if category == "non_delivery":
        # Return Policy §12/§9: a non-delivery claim has no physical item to return, so it
        # must never flow into the standard return/complaint reason pipeline. Routes into
        # COMPLAINT_FLOW (same as a quality complaint) but pre-marks it as already past its
        # one verification round — complaint_flow_node's own _non_delivery_checked branch
        # (constitution V.4) then always escalates the customer's next reply, rather than
        # ever reaching VERIFICATION/DECISION/AUTO_ACTION's return-label pipeline.
        reply = (
            "Je suis désolée de l'apprendre. Avant d'aller plus loin, pourriez-vous "
            "vérifier auprès des personnes de votre foyer, de la réception de votre "
            "immeuble ou de vos voisins, au cas où le colis aurait été réceptionné par "
            "quelqu'un d'autre ?"
        )
        return {
            **state,
            "intent": "complaint",
            "reason": "not_received",
            "_non_delivery_checked": True,
            "current_state": "QUALIFICATION",
            "reply": reply,
        }

    intent = _CATEGORY_TO_INTENT.get(category)
    if intent in ("return", "complaint"):
        reply = (
            "Compris — il semble que vous souhaitiez faire un retour. "
            if intent == "return"
            else "Je suis désolée de l'apprendre — voyons comment régler cela. "
        ) + "Pourriez-vous m'en dire plus sur la raison ?"
        return {**state, "intent": intent, "current_state": "QUALIFICATION", "reply": reply}

    # category == "ambiguous" (or an unrecognized value) -> ask a clarifying question, up to
    # MAX_CLARIFICATIONS times (FR-003), then escalate. Logged at each step so real
    # ambiguous phrasing patterns can be reviewed over time.
    reformulations = state.get("reformulation_count", 0) + 1
    logger.warning("QUALIFICATION_AMBIGUOUS message=%r reformulation=%d", message, reformulations)
    if reformulations <= MAX_CLARIFICATIONS:
        reply = (
            "Pour être sûre de bien vous aider — souhaitez-vous retourner un article, ou "
            "signaler un problème avec quelque chose que vous avez reçu ?"
        )
        return {**state, "reformulation_count": reformulations, "current_state": "QUALIFICATION", "reply": reply}

    # Still unclear after 2 clarifications -> escalate (data-model.md State Machine table).
    logger.error("QUALIFICATION_ESCALATED_AMBIGUOUS message=%r after %d clarifications", message, reformulations)
    return {
        **state,
        "reformulation_count": reformulations,
        "escalated": True,
        "escalation_reason": "qualification_unclear",
        "current_state": "QUALIFICATION",
        "reply": (
            "Je tiens à ce que vous receviez la bonne aide, je fais donc intervenir un "
            "collègue qui pourra vous accompagner davantage."
        ),
    }


def route_intent(state: dict) -> str:
    """Decides the next node from qualification's output (intent/escalated) — shared by
    graph.py's _route_after_qualification and confirmation.py's post-resolution re-entry, so
    both apply the exact same transition rules instead of duplicating them."""
    if state.get("escalated"):
        return "ESCALATION"
    intent = state.get("intent")
    if intent == "return":
        return "RETURN_FLOW"
    if intent == "complaint":
        return "COMPLAINT_FLOW"
    if intent == "other":
        return "CONFIRMATION"
    return "QUALIFICATION"
