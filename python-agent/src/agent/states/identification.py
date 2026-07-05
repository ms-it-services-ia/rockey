"""IDENTIFICATION node (spec User Story 1). Mandatory before any action (constitution V.2):
max 2 identification attempts before escalation.

Note: order number / email extraction here is a simple regex-based parser — a production
build would use Claude's structured extraction, but that requires a live ANTHROPIC_API_KEY
call this POC's automated tests can't depend on. The extraction boundary is isolated in
`_extract_identification` so swapping it for an LLM-based extractor later doesn't touch the
rest of this node's logic.
"""

import re

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

    # Edge case (T024b): customer tries to skip identification (message has neither an
    # order number nor an email) — hold the step without spending an attempt.
    if not order_id or not email:
        reply = (
            "I'll need your order number (e.g. CMD-2026-00001) and the email address used "
            "for that order before I can help — you'll find the order number in your "
            "confirmation email."
        )
        return {**state, "current_state": "IDENTIFICATION", "reply": reply}

    try:
        order_data = await check_order(order_id, email, state["tenant_id"])
    except OrderNotFound:
        attempts = state.get("identification_attempts", 0) + 1
        if attempts < 2:
            # Edge case: order not found on the first attempt — offer to re-verify.
            reply = (
                "I couldn't find an order matching that number and email — could you "
                "double-check them and try again?"
            )
            return {**state, "identification_attempts": attempts, "current_state": "IDENTIFICATION", "reply": reply}

        # 2 failed attempts -> escalate. Deliberately generic (constitution III.3 / T031):
        # this message never reveals whether the order belongs to a different retailer or
        # simply doesn't exist, so no cross-tenant information ever leaks to the customer.
        reply = (
            "I still can't find a matching order after two attempts. Let me transfer you "
            "to a member of our team who can look into this further."
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
            "reply": "I'm having trouble reaching our order system right now — let me transfer you to a colleague.",
        }

    reply = (
        f"Thanks, {order_data['clientName']}! I can see your order for {order_data['articleId']}. "
        "How can I help you with it?"
    )
    return {
        **state,
        "client_email": email,
        "order_id": order_id,
        "order_data": order_data,
        "current_state": "IDENTIFICATION",
        "reply": reply,
    }
