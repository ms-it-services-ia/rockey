"""IDENTIFICATION node (spec User Story 1). Mandatory before any action (constitution V.2):
max 2 identification attempts before escalation.

Note: order number / email extraction here is a simple regex-based parser — a production
build would use Claude's structured extraction, but that requires a live ANTHROPIC_API_KEY
call this POC's automated tests can't depend on. The extraction boundary is isolated in
`_extract_identification` so swapping it for an LLM-based extractor later doesn't touch the
rest of this node's logic.
"""

import re

from agent.states.qualification import append_context
from agent.tools.check_order import OrderNotFound, check_order
from config.circuit_breaker import TechnicalFailure

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ORDER_RE = re.compile(r"\bCMD-\d{4}-\d+\b", re.IGNORECASE)


def _extract_identification(message: str) -> tuple[str | None, str | None]:
    email_match = _EMAIL_RE.search(message)
    order_match = _ORDER_RE.search(message)
    email = email_match.group(0) if email_match else None
    order_id = order_match.group(0).upper() if order_match else None
    return order_id, email


async def identification_node(state: dict) -> dict:
    message = state.get("_latest_message", "")
    order_id, email = _extract_identification(message)
    # The message that finally identifies the customer often also states their actual
    # request ("CMD-2026-00001, marie@x.com, mon colis n'est jamais arrivé") — the regex
    # extraction above only pulls out order_id/email, so the rest would otherwise be lost
    # the same way a pre-identification message would be (see qualification.py).
    context = append_context(state, message)

    # Edge case (T024b): customer tries to skip identification (message has neither an
    # order number nor an email) — hold the step without spending an attempt.
    if not order_id or not email:
        reply = (
            "J'aurai besoin de votre numéro de commande (par exemple CMD-2026-00001) ainsi "
            "que de l'adresse email utilisée pour cette commande avant de pouvoir vous "
            "aider — vous trouverez le numéro de commande dans votre email de confirmation."
        )
        return {**state, "_qualification_context": context, "current_state": "IDENTIFICATION", "reply": reply}

    try:
        order_data = await check_order(order_id, email, state["tenant_id"])
    except OrderNotFound:
        attempts = state.get("identification_attempts", 0) + 1
        if attempts < 2:
            # Edge case: order not found on the first attempt — offer to re-verify.
            reply = (
                "Je n'ai pas trouvé de commande correspondant à ce numéro et cet email — "
                "pourriez-vous vérifier ces informations et réessayer ?"
            )
            return {
                **state,
                "identification_attempts": attempts,
                "_qualification_context": context,
                "current_state": "IDENTIFICATION",
                "reply": reply,
            }

        # 2 failed attempts -> escalate. Deliberately generic (constitution III.3 / T031):
        # this message never reveals whether the order belongs to a different retailer or
        # simply doesn't exist, so no cross-tenant information ever leaks to the customer.
        reply = (
            "Je ne parviens toujours pas à trouver de commande correspondante après deux "
            "tentatives. Je vous transfère à un membre de notre équipe qui pourra "
            "approfondir la recherche."
        )
        return {
            **state,
            "identification_attempts": attempts,
            "escalated": True,
            "escalation_reason": "identification_failed",
            "current_state": "IDENTIFICATION",
            "reply": reply,
        }
    except TechnicalFailure:
        return {
            **state,
            "escalated": True,
            "escalation_reason": "service_unavailable",
            "current_state": "IDENTIFICATION",
            "reply": (
                "J'ai des difficultés à joindre notre système de commandes en ce moment — "
                "je vous transfère à un collègue."
            ),
        }

    # No "comment puis-je vous aider ?" tail: run_turn always continues straight into
    # QUALIFICATION in the same turn once identification succeeds (see graph.py), so this
    # reply is always immediately followed by the actual classification result — asking how
    # to help right before answering that exact question would be redundant.
    reply = f"Merci, {order_data['clientName']} ! Je vois bien votre commande pour {order_data['articleId']}."
    return {
        **state,
        "client_email": email,
        "order_id": order_id,
        "order_data": order_data,
        "_qualification_context": context,
        "current_state": "IDENTIFICATION",
        "reply": reply,
    }
