"""RETURN_FLOW node (spec User Story 3, AC1): collects the return reason, then hands off to
VERIFICATION (which runs immediately after, in the same turn — see graph.py's run_turn)."""

from agent.rag.rag_query import get_article_by_id
from config.circuit_breaker import call_with_breaker

_REASON_KEYWORDS = {
    "wrong_size": (
        "too small",
        "too big",
        "wrong size",
        "doesn't fit",
        "trop petit",
        "trop grand",
        "mauvaise taille",
        "ne me va pas",
    ),
    "change_of_mind": (
        "changed my mind",
        "don't want it",
        "no longer need",
        "changé d'avis",
        "n'en veux plus",
        "n'en ai plus besoin",
    ),
    "non_conforming": (
        "not as described",
        "different from",
        "not what i ordered",
        "ne correspond pas",
        "différent de",
        "pas ce que j'ai commandé",
    ),
}


def _classify_reason(message: str) -> str:
    lowered = message.lower()
    for reason, keywords in _REASON_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return reason
    return "other"


async def return_flow_node(state: dict) -> dict:
    reason = _classify_reason(state.get("_latest_message", ""))
    article_id = (state.get("order_data") or {}).get("articleId")

    article_data = await call_with_breaker(
        "pgvector", lambda: get_article_by_id(article_id, state["tenant_id"])
    )

    return {
        **state,
        "reason": reason,
        "article_data": article_data,
        "current_state": "RETURN_FLOW",
    }
