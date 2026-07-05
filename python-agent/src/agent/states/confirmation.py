"""Closing confirmation (User Story 6, P2 — full polish out of scope for this batch).

A minimal but FR-010-compliant version is implemented here (case number, action taken, next
step) since every US1-US4 flow terminates through this node; richer formatting (attachments,
"additional help" offer) belongs to Phase 8 / tasks T070-T073.
"""


async def confirmation_node(state: dict) -> dict:
    if state.get("escalated"):
        reply = (
            "Your request has been transferred to a member of our team who will follow up "
            f"with you shortly. Reference: {state.get('ticket_id') or state.get('case_id') or 'pending'}."
        )
    else:
        action = state.get("action_result") or {}
        reply = (
            f"Here is a summary of your request (case {state.get('case_id') or 'N/A'}): "
            f"{action.get('summary', 'your request has been processed')}."
        )

    return {**state, "current_state": "CONFIRMATION", "reply": reply}
