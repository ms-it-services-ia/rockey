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

    # Edge case (spec US5): vague defect description -> ask up to 2 clarifying questions.
    if _is_vague(message) and state.get("reformulation_count", 0) < MAX_CLARIFICATIONS:
        reformulations = state.get("reformulation_count", 0) + 1
        reply = (
            "Could you tell me a bit more about the problem? For example, what exactly is "
            "wrong with the item?"
        )
        return {
            **state,
            "reformulation_count": reformulations,
            "_complaint_needs_clarification": True,
            "current_state": "COMPLAINT_FLOW",
            "reply": reply,
        }

    reason = _classify_reason(message)
    article_id = (state.get("order_data") or {}).get("articleId")
    article_data = await call_with_breaker(
        "pgvector", lambda: get_article_by_id(article_id, state["tenant_id"])
    )

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
                "I can see you've reported an issue with this item before — let me bring in "
                "a colleague who can look at the full history and help resolve this."
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
