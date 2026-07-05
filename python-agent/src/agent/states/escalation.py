"""ESCALATION node (spec User Story 4). Irreversible for the remainder of the session
(constitution V.4/V.4, FR-009) — once this node runs, `escalated` stays True and no other
node in this session will ever flip it back."""

from datetime import UTC, datetime

from agent.tools.escalate_to_human import escalate_to_human
from config.circuit_breaker import TechnicalFailure

# POC business-hours window (UTC, Mon-Fri 08:00-19:00) — a real implementation would source
# this from tenant_config per retailer/timezone; kept simple here since it's not otherwise
# modeled in data-model.md.
_BUSINESS_HOURS_START = 8
_BUSINESS_HOURS_END = 19


def _is_outside_business_hours(now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    is_weekend = now.weekday() >= 5
    is_outside_hours = not (_BUSINESS_HOURS_START <= now.hour < _BUSINESS_HOURS_END)
    return is_weekend or is_outside_hours


_REASON_LABELS = {
    "identification_failed": "unable to verify the customer's identity after 2 attempts",
    "qualification_unclear": "unable to determine the customer's request after 2 clarifications",
    "service_unavailable": "a backend service was unavailable",
    "amount_above_threshold": "the amount exceeds the auto-refund threshold",
    "legal_warranty": "the complaint is past the standard return window but within the legal warranty period",
    "repeated_complaint": "the customer has complained about this item before",
    "technical_action_failed": "a technical error occurred while finalizing the action",
}


def _build_summary(state: dict) -> str:
    reason = state.get("escalation_reason", "unspecified")
    label = _REASON_LABELS.get(reason, reason)
    order_id = state.get("order_id", "unknown")
    intent = state.get("intent", "unspecified")
    exchange_count = len(state.get("messages", []))
    return f"Escalated ({label}). Order: {order_id}. Intent: {intent}. Messages exchanged: {exchange_count}."


async def escalation_node(state: dict) -> dict:
    order_data = state.get("order_data") or {}
    summary = _build_summary(state)

    try:
        ticket = await escalate_to_human(
            order_id=state.get("order_id") or "unknown",
            tenant_id=state["tenant_id"],
            reason=state.get("escalation_reason", "unspecified"),
            summary=summary,
            client_email=state.get("client_email") or "unknown",
            amount=order_data.get("amount", 0.0),
            channel=state["channel"],
            session_id=state["session_id"],
            article_name=(state.get("article_data") or {}).get("name", "N/A"),
        )
        ticket_id = ticket.get("ticketId")
        delay = ticket.get("delay", "as soon as possible")
    except TechnicalFailure:
        # Even if ticket creation itself fails, the customer-facing outcome MUST still be an
        # honest "you're being escalated" message (constitution VI.1 — never a raw error) —
        # escalated stays True either way; a human will need to pick this up out-of-band.
        ticket_id = None
        delay = "as soon as possible"

    reply = (
        "I'm sorry I couldn't fully resolve this myself — I've passed your case to a "
        f"member of our team, who will get back to you {delay}."
        + (f" Your reference is {ticket_id}." if ticket_id else "")
    )
    if _is_outside_business_hours():
        # Edge case (spec User Story 4): escalation outside business hours -> waiting
        # message with an expected response time, rather than implying someone is online now.
        reply += " Our team is currently offline outside business hours, so it may take a little longer than usual."

    return {
        **state,
        # Irreversible: escalated is already True from whichever node triggered this, and
        # stays True — this node never resets it, regardless of outcome.
        "escalated": True,
        "ticket_id": ticket_id,
        "case_id": state.get("case_id") or ticket_id,
        "current_state": "ESCALATION",
        "reply": reply,
    }
