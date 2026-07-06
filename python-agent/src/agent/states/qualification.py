"""QUALIFICATION node (spec User Story 2, FR-003/FR-004). Classifies intent as return,
complaint, or out-of-scope, asking at most 2 clarifying questions when ambiguous.

Note: intent classification here is a simple keyword matcher — a production build would use
Claude (research.md §4), but that requires a live ANTHROPIC_API_KEY call this POC's
automated tests can't depend on. The classification boundary is isolated in `_classify_intent`
so swapping it for an LLM-based classifier later doesn't touch the rest of this node.
"""

MAX_CLARIFICATIONS = 2

# Bilingual (EN/FR) — documented POC limitation (constitution II.1: Léa's persona is French,
# but the keyword matcher was English-only until real customer testing surfaced messages
# like "mon article n'est pas reçu, il est introuvable, je veux un remboursement" being
# permanently unclassifiable, no matter how clearly the customer stated their request).
_RETURN_KEYWORDS = (
    "return",
    "give back",
    "wrong size",
    "doesn't fit",
    "changed my mind",
    "exchange",
    "retour",
    "retourner",
    "renvoyer",
    "mauvaise taille",
    "ne me va pas",
    "j'ai changé d'avis",
    "changé d'avis",
    "échange",
    "échanger",
)
_COMPLAINT_KEYWORDS = (
    "defective",
    "broken",
    "damaged",
    "complaint",
    "faulty",
    "wrong item",
    "not working",
    "not received",
    "never received",
    "haven't received",
    "hasn't arrived",
    "never arrived",
    "lost",
    "missing",
    "défectueux",
    "cassé",
    "abîmé",
    "endommagé",
    "réclamation",
    "ne fonctionne pas",
    "mauvais article",
    "pas reçu",
    "non reçu",
    "jamais reçu",
    "introuvable",
    "perdu",
    "n'est jamais arrivé",
    "colis perdu",
)
_OUT_OF_SCOPE_KEYWORDS = (
    "price",
    "discount",
    "promo",
    "restock",
    "when will you",
    "shipping cost",
    "prix",
    "réduction",
    "promotion",
    "réapprovisionnement",
    "frais de livraison",
)


def _classify_intent(message: str) -> str | None:
    """Returns "return", "complaint", "other", or None (ambiguous — needs clarification)."""
    lowered = message.lower()
    is_return = any(kw in lowered for kw in _RETURN_KEYWORDS)
    is_complaint = any(kw in lowered for kw in _COMPLAINT_KEYWORDS)
    is_out_of_scope = any(kw in lowered for kw in _OUT_OF_SCOPE_KEYWORDS)

    if is_out_of_scope and not is_return and not is_complaint:
        return "other"
    if is_return and not is_complaint:
        return "return"
    if is_complaint and not is_return:
        return "complaint"
    return None  # mixed or unrecognized — ambiguous


async def qualification_node(state: dict) -> dict:
    message = state.get("_latest_message", "")
    intent = _classify_intent(message)

    if intent == "other":
        reply = (
            "Cela sort un peu de ce que je peux traiter ici — je m'occupe des retours et "
            "des réclamations qualité. Pour cette question, notre service client habituel "
            "sera mieux placé pour vous répondre."
        )
        return {**state, "intent": "other", "current_state": "QUALIFICATION", "reply": reply}

    if intent in ("return", "complaint"):
        reply = (
            "Compris — il semble que vous souhaitiez faire un retour. "
            if intent == "return"
            else "Je suis désolée de l'apprendre — voyons comment régler cela. "
        ) + "Pourriez-vous m'en dire plus sur la raison ?"
        return {**state, "intent": intent, "current_state": "QUALIFICATION", "reply": reply}

    # Ambiguous: ask a clarifying question, up to MAX_CLARIFICATIONS times (FR-003).
    reformulations = state.get("reformulation_count", 0) + 1
    if reformulations <= MAX_CLARIFICATIONS:
        reply = (
            "Pour être sûre de bien vous aider — souhaitez-vous retourner un article, ou "
            "signaler un problème avec quelque chose que vous avez reçu ?"
        )
        return {**state, "reformulation_count": reformulations, "current_state": "QUALIFICATION", "reply": reply}

    # Still unclear after 2 clarifications -> escalate (data-model.md State Machine table).
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
