"""QUALIFICATION node (spec User Story 2, FR-003/FR-004). Classifies intent as a return
request, a non-delivery claim, a quality complaint, or out-of-scope, via interpret_turn
(research.md §4) — asking at most 2 clarifying questions when the LLM itself signals genuine
ambiguity, never by matching exact phrases.

Constitution V.3 still holds: interpret_turn only classifies *what the customer is asking
for* — it never decides an eligibility/refund outcome, which stays 100% rule-based in Java's
EligibilityService.
"""

import logging

from agent.states.complaint_flow import already_verified_from_message
from agent.tools.interpret_turn import TurnCategory, TurnInterpretation, interpret_turn
from config.circuit_breaker import TechnicalFailure

logger = logging.getLogger(__name__)

MAX_CLARIFICATIONS = 2

INTENT_CONTEXT = (
    "The customer is contacting after-sales support and hasn't yet stated a specific reason "
    "for a return or complaint beyond what's given here."
)

INTENT_CATEGORIES = [
    TurnCategory(
        "return_request",
        "wants to send back an item they have in hand, for a change-of-mind reason (wrong "
        "size, no longer wanted, wrong color preference, etc)",
    ),
    TurnCategory(
        "non_delivery",
        "says they never received the item, it's lost, missing, or untraceable — no "
        "physical item in their possession to ship back",
    ),
    TurnCategory(
        "quality_complaint",
        "has the item but it's damaged, defective, not as described, or the wrong item was "
        "sent",
    ),
    TurnCategory(
        "other",
        "unrelated to returns/complaints/delivery — pricing, promotions, general questions, "
        "anything out of scope for after-sales support",
    ),
]

_CATEGORY_TO_INTENT = {
    "return_request": "return",
    "quality_complaint": "complaint",
    "other": "other",
}


def append_context(state: dict, message: str) -> list[str]:
    """Buffers a customer message that couldn't be classified yet (GREETING/IDENTIFICATION
    run before any intent classification happens, constitution V.2) so qualification_node
    can classify everything the customer actually said, not just whichever message happens
    to arrive once identification finally succeeds.

    Idempotent on the last entry: when identification succeeds, graph.py's run_turn
    continues straight into qualification_node in the same turn without a new customer
    message in between — identification.py already appended `_latest_message` itself, so
    qualification_node calling this again on the exact same message must not duplicate it."""
    context = state.get("_qualification_context", [])
    if not message or (context and context[-1] == message):
        return context
    return [*context, message]


async def qualification_node(state: dict) -> dict:
    latest = state.get("_latest_message", "")
    context = append_context(state, latest)
    combined_message = "\n".join(context) if context else latest

    try:
        interpretation = await interpret_turn(combined_message, INTENT_CONTEXT, INTENT_CATEGORIES)
    except TechnicalFailure:
        return {
            **state,
            "escalated": True,
            "escalation_reason": "service_unavailable",
            "current_state": "QUALIFICATION",
            "reply": "J'ai des difficultés à traiter votre demande en ce moment — je vous transfère à un collègue.",
        }

    result = await route_interpretation(state, interpretation, combined_message)
    # A definite classification (intent set) means the buffered pre-identification content
    # has served its purpose — clear it so it can't leak into a later, unrelated request in
    # the same session. Still ambiguous -> keep accumulating for the next clarification round.
    result["_qualification_context"] = [] if result.get("intent") else context
    return result


async def route_interpretation(state: dict, interpretation: TurnInterpretation, message: str) -> dict:
    """Everything qualification_node does once a TurnInterpretation is known — factored out
    so confirmation_node can reuse it for a new/unrelated request classified after a case has
    already been closed, reusing the interpret_turn call it already made instead of a second
    one (see confirmation.py). `message` is the full text to classify against for any
    secondary check within a branch (qualification_node passes its buffered combined
    message, so an "already verified" statement made before identification is still seen)."""
    if interpretation.signal in ("closing", "resolved"):
        # Nothing has been established yet at this point (no case, no escalation) — either
        # signal means the same thing here: end warmly, nothing left to do.
        return {
            **state,
            "current_state": "QUALIFICATION",
            "reply": "Avec plaisir ! N'hésitez pas à revenir vers nous si vous avez besoin d'autre chose.",
            "_session_ended": True,
        }

    if interpretation.signal == "case_status_question":
        return {
            **state,
            "current_state": "QUALIFICATION",
            "reply": (
                "Je ne vois pas encore de demande en cours pour vous — dites-moi ce dont "
                "vous avez besoin (un retour ou un problème avec un article reçu) et je "
                "m'en occupe."
            ),
        }

    if interpretation.signal == "on_topic":
        category = interpretation.category

        if category == "other":
            reply = (
                "Cela sort un peu de ce que je peux traiter ici — je m'occupe des retours et "
                "des réclamations qualité. Pour cette question, notre service client habituel "
                "sera mieux placé pour vous répondre."
            )
            return {**state, "intent": "other", "current_state": "QUALIFICATION", "reply": reply}

        if category == "non_delivery":
            # Return Policy §12/§9: a non-delivery claim has no physical item to return, so
            # it must never flow into the standard return/complaint reason pipeline.
            if await already_verified_from_message(message):
                # The customer already said, unprompted, that they checked and it's still
                # missing (often stated in the very first message, before identification —
                # see qualification.py's _qualification_context buffer) — asking again would
                # ignore what they just told us, so skip straight to escalation.
                return {
                    **state,
                    "intent": "complaint",
                    "reason": "not_received",
                    "escalated": True,
                    "escalation_reason": "non_delivery_claim",
                    "current_state": "QUALIFICATION",
                    "reply": (
                        "Je suis désolée de l'apprendre. Puisque vous avez déjà vérifié "
                        "auprès de votre foyer et de vos voisins, je transmets directement "
                        "votre dossier à un collègue pour investiguer et trouver la "
                        "meilleure solution."
                    ),
                }
            # Otherwise: routes into COMPLAINT_FLOW (same as a quality complaint) but
            # pre-marks it as already past its one verification round —
            # complaint_flow_node's own _non_delivery_checked branch (constitution V.4)
            # then decides from there rather than ever reaching VERIFICATION/DECISION/
            # AUTO_ACTION's return-label pipeline.
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

    # ambiguous (or on_topic with a category outside what's mapped above, defensively) -> ask
    # a clarifying question, up to MAX_CLARIFICATIONS times (FR-003), then escalate. Logged
    # at each step so real ambiguous phrasing patterns can be reviewed over time.
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
    """Decides the next node from qualification's output (intent/escalated/_session_ended) —
    shared by graph.py's _route_after_qualification and confirmation.py's post-resolution
    re-entry, so both apply the exact same transition rules instead of duplicating them."""
    if state.get("escalated"):
        return "ESCALATION"
    if state.get("_session_ended"):
        return "CONFIRMATION"
    intent = state.get("intent")
    if intent == "return":
        return "RETURN_FLOW"
    if intent == "complaint":
        return "COMPLAINT_FLOW"
    if intent == "other":
        return "CONFIRMATION"
    return "QUALIFICATION"
