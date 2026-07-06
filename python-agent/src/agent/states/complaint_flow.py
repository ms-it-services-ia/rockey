"""COMPLAINT_FLOW node (spec User Story 5, AC1-2): collects the complaint reason and a
free-text description, detects repeated complaints on the same item, and asks for
clarification when the description is too vague to act on.

Note: reason classification and vagueness detection are simple heuristics, same documented
simplification as qualification.py/return_flow.py — a production build would use Claude.
"""

from agent.memory.history_store import record_complaint
from agent.rag.rag_query import get_article_by_id
from config.circuit_breaker import call_with_breaker

MAX_CLARIFICATIONS = 2
_MIN_DESCRIPTION_LENGTH = 15

_REASON_KEYWORDS = {
    "quality_defect": (
        "defective",
        "faulty",
        "broken",
        "doesn't work",
        "poor quality",
        "défectueux",
        "ne fonctionne pas",
        "mauvaise qualité",
    ),
    "damaged_on_delivery": ("damaged", "arrived broken", "smashed", "torn", "endommagé", "abîmé", "cassé", "déchiré"),
    "non_conformity": (
        "not as described",
        "different from",
        "wrong material",
        "wrong color",
        "ne correspond pas",
        "différent de",
        "mauvaise couleur",
    ),
    "wrong_item": (
        "wrong item",
        "not what i ordered",
        "sent me the wrong",
        "mauvais article",
        "pas ce que j'ai commandé",
    ),
    "not_received": (
        "not received",
        "never received",
        "haven't received",
        "hasn't arrived",
        "never arrived",
        "lost",
        "missing",
        "pas reçu",
        "non reçu",
        "jamais reçu",
        "introuvable",
        "perdu",
        "n'est jamais arrivé",
        "colis perdu",
    ),
}


def _classify_reason(message: str) -> str:
    lowered = message.lower()
    for reason, keywords in _REASON_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return reason
    return "other"


def _is_vague(message: str) -> bool:
    return len(message.strip()) < _MIN_DESCRIPTION_LENGTH


async def complaint_flow_node(state: dict) -> dict:
    message = state.get("_latest_message", "")

    # Follow-up to the non-delivery verification question below — the customer is reporting
    # back whether they found the package, not restating the complaint reason, so this must
    # not be re-classified from scratch (a reply like "no one has it" wouldn't match any
    # _REASON_KEYWORDS and would otherwise fall into the vague/unclassifiable branch below).
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

    reason = _classify_reason(message)

    # Too short OR no keyword matched any known reason -> ask up to 2 clarifying questions
    # (Complaint Policy §4), then escalate. Reason classification failing must never
    # silently fall through as "other" and let an unclear case slide into auto-approval —
    # that's exactly what let a real customer's follow-up ("I already said the reason", not
    # matching any keyword) get auto-resolved as if it were a normal, understood complaint.
    if _is_vague(message) or reason == "other":
        reformulations = state.get("reformulation_count", 0) + 1
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
            # vague-description clarification above (_route_after_complaint_flow loops back
            # to COMPLAINT_FLOW either way) — this isn't a vague description, but it equally
            # needs one more round-trip before a decision can be made.
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
