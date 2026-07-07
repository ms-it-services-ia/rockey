"""COMPLAINT_FLOW node (spec User Story 5, AC1-2): collects the complaint reason via
interpret_turn (research.md §4, one level deeper than intent classification — see
tools/interpret_turn.py for why a per-node hand-rolled enum kept missing real-world outcomes
nobody thought to enumerate), detects repeated complaints on the same item, and asks for
clarification only when the LLM itself signals genuine ambiguity.
"""

import logging

from agent.memory.history_store import record_complaint
from agent.rag.rag_query import get_article_by_id
from agent.tools.interpret_turn import TurnCategory, interpret_turn
from config.circuit_breaker import TechnicalFailure, call_with_breaker

logger = logging.getLogger(__name__)

MAX_CLARIFICATIONS = 2

_REASON_CONTEXT = (
    "The customer already indicated they have a quality complaint about an item they "
    "received; classify why."
)

_REASON_CATEGORIES = [
    TurnCategory(
        "quality_defect",
        "the item is defective, faulty, broken, or doesn't work, for reasons other than "
        "shipping damage",
    ),
    TurnCategory(
        "damaged_on_delivery",
        "the item arrived visibly damaged or broken, consistent with shipping/transit damage",
    ),
    TurnCategory(
        "non_conformity",
        "the item doesn't match its listing — wrong material, wrong color, or otherwise "
        "different from what was described — but the customer has it in hand",
    ),
    TurnCategory("wrong_item", "an entirely different item than what was ordered was sent"),
    TurnCategory(
        "not_received",
        "the customer never received the item, it's lost, missing, or untraceable — no "
        "physical item in hand",
    ),
    TurnCategory("other", "a genuine, understood quality issue that just doesn't fit any of the above categories"),
]

VERIFICATION_CONTEXT = (
    "The customer was asked to check with household members, building reception, or "
    "neighbors for a package they say never arrived, and is now replying."
)

VERIFICATION_CATEGORIES = [
    TurnCategory("confirmed_not_found", "checked (or already knew for certain) and the package genuinely isn't there"),
    TurnCategory("not_yet_checked", "hasn't completed the verification yet — hasn't checked, will check later"),
]

_VERIFICATION_ESCALATION_REPLY = (
    "Je comprends, je fais intervenir un collègue pour investiguer ce qui s'est passé avec "
    "la livraison et trouver la meilleure solution."
)

_NO_LONGER_AN_ISSUE_REPLY = "Je suis ravie de l'apprendre ! N'hésitez pas si vous avez besoin d'autre chose."

# Deliberately separate from VERIFICATION_CONTEXT/VERIFICATION_CATEGORIES above: those assume
# the household/neighbors question was actually asked and the customer is now replying to it
# — reusing that premise for already_verified_from_message's *proactive* check (nothing was
# asked yet) biased the LLM into reading a bare "my package never arrived" as if it already
# confirmed a completed check, when it hadn't mentioned checking at all.
_UNPROMPTED_VERIFICATION_CONTEXT = (
    "The customer is describing a package they say never arrived. No one has asked them "
    "yet whether they checked with household members, building reception, or neighbors — "
    "determine only whether they already volunteered that information unprompted."
)

_UNPROMPTED_VERIFICATION_CATEGORIES = [
    TurnCategory(
        "confirmed_not_found",
        "the message states they already made a genuine effort to locate the package — "
        "checking their mailbox, around their home/building, with household members, "
        "building reception, or neighbors — and it's confirmed genuinely missing. Does "
        "not require every single one of those specific people/places to be named; "
        "checking their mailbox and around their home already counts",
    ),
    TurnCategory(
        "not_yet_checked",
        "the message does not mention having looked for or checked on the package at "
        "all, or explicitly says they haven't yet — this is the default when "
        "verification simply isn't mentioned",
    ),
]


async def already_verified_from_message(message: str) -> bool:
    """True if the message already states, unprompted, that the customer checked with their
    household/neighbors and the package is confirmed missing — used to skip re-asking the
    verification question when the customer volunteered the answer before it was even asked
    (e.g. in their initial message, before identification even completed — see
    qualification.py).

    A technical failure here is not escalation-worthy on its own: the caller's primary
    classification already succeeded, so falling back to asking the question normally is a
    safe, non-breaking degradation — this only decides whether to skip a question, not
    whether to escalate, so there is nothing to silently guess about the actual claim."""
    try:
        interpretation = await interpret_turn(
            message, _UNPROMPTED_VERIFICATION_CONTEXT, _UNPROMPTED_VERIFICATION_CATEGORIES
        )
    except TechnicalFailure:
        return False
    return interpretation.signal == "on_topic" and interpretation.category == "confirmed_not_found"


async def complaint_flow_node(state: dict) -> dict:
    message = state.get("_latest_message", "")

    # Follow-up to the non-delivery verification question below — the customer is reporting
    # back whether they found the package, not restating the complaint reason, so this must
    # not be re-classified from scratch.
    if state.get("_non_delivery_checked"):
        try:
            interpretation = await interpret_turn(message, VERIFICATION_CONTEXT, VERIFICATION_CATEGORIES)
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

        if interpretation.signal in ("resolved", "closing"):
            # The customer found the package (or no longer needs help) — there's no claim to
            # escalate; end warmly rather than treating this as if they'd confirmed it was
            # still missing (the exact bug this rewrite exists to fix).
            return {
                **state,
                "reason": None,
                "_non_delivery_checked": False,
                "current_state": "CONFIRMATION",
                "reply": _NO_LONGER_AN_ISSUE_REPLY,
                "_session_ended": True,
            }

        if interpretation.signal == "case_status_question":
            return {
                **state,
                "current_state": "COMPLAINT_FLOW",
                "_complaint_needs_clarification": True,
                "reply": (
                    "Nous n'avons pas encore transmis votre dossier — je voulais d'abord "
                    "vérifier avec vous si le colis avait pu être réceptionné par quelqu'un "
                    "d'autre. Avez-vous pu vérifier ?"
                ),
            }

        # Return Policy §12 only wants an escalation once the customer has actually checked
        # and it's still missing — "I haven't checked yet" is not the same answer, and must
        # not be treated as if it were.
        if interpretation.signal == "on_topic" and interpretation.category == "not_yet_checked":
            reformulations = state.get("reformulation_count", 0) + 1
            logger.warning("NON_DELIVERY_VERIFICATION_PENDING message=%r attempt=%d", message, reformulations)
            if reformulations <= MAX_CLARIFICATIONS:
                return {
                    **state,
                    "reformulation_count": reformulations,
                    "_complaint_needs_clarification": True,
                    "current_state": "COMPLAINT_FLOW",
                    "reply": (
                        "Pas de souci, prenez le temps de vérifier auprès des personnes de "
                        "votre foyer, de la réception de votre immeuble ou de vos voisins, "
                        "et dites-moi ce qu'il en est."
                    ),
                }
            # Still not checked after MAX_CLARIFICATIONS -> escalate anyway (Return Policy
            # §12 always routes a non-delivery claim to human investigation eventually;
            # asking indefinitely serves no one).
            logger.warning("NON_DELIVERY_VERIFICATION_TIMEOUT message=%r after %d attempts", message, reformulations)

        # confirmed_not_found, or ambiguous (constitution V.3: never let an unclear
        # verification silently drop a claim — a genuine SNAD claim always needs human
        # investigation regardless, so ambiguous is safe to treat the same as confirmed).
        return {
            **state,
            "reason": "not_received",
            "escalated": True,
            "escalation_reason": "non_delivery_claim",
            "current_state": "COMPLAINT_FLOW",
            "reply": _VERIFICATION_ESCALATION_REPLY,
        }

    try:
        interpretation = await interpret_turn(message, _REASON_CONTEXT, _REASON_CATEGORIES)
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

    if interpretation.signal in ("closing", "resolved"):
        # Nothing has been recorded yet at this point — the customer is withdrawing the
        # complaint before we've done anything technical with it; end warmly.
        return {
            **state,
            "current_state": "CONFIRMATION",
            "reply": _NO_LONGER_AN_ISSUE_REPLY,
            "_session_ended": True,
        }

    if interpretation.signal == "case_status_question":
        return {
            **state,
            "current_state": "COMPLAINT_FLOW",
            "_complaint_needs_clarification": True,
            "reply": (
                "Je n'ai pas encore de dossier en cours — dites-moi ce qui s'est passé avec "
                "l'article et je regarde ça avec vous."
            ),
        }

    reason = interpretation.category if interpretation.signal == "on_topic" else "ambiguous"

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
        if await already_verified_from_message(message):
            # The customer already said, unprompted, that they checked and it's still
            # missing — asking again would ignore what they just told us (Return Policy §12
            # still always routes this to human investigation, just without a redundant
            # round-trip first).
            return {
                **state,
                "reason": reason,
                "complaint_description": message,
                "article_data": article_data,
                "escalated": True,
                "escalation_reason": "non_delivery_claim",
                "current_state": "COMPLAINT_FLOW",
                "reply": (
                    "Je suis désolée de l'apprendre. Puisque vous avez déjà vérifié auprès "
                    "de votre foyer et de vos voisins, je transmets directement votre "
                    "dossier à un collègue pour investiguer et trouver la meilleure "
                    "solution."
                ),
            }
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
