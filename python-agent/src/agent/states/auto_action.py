"""AUTO_ACTION node (spec User Story 3, AC3): generates the return label and triggers the
refund for an auto-approved return. A technical failure here always escalates (data-model.md
State Machine: "AUTO_ACTION: action fails -> ESCALATION", reason technical_action_failed)."""

from agent.tools.create_return_label import create_return_label
from agent.tools.trigger_refund import trigger_refund
from config.circuit_breaker import TechnicalFailure


async def auto_action_node(state: dict) -> dict:
    order_data = state.get("order_data") or {}
    amount = order_data.get("amount")

    try:
        return_result = await create_return_label(
            order_id=state["order_id"],
            tenant_id=state["tenant_id"],
            article_id=order_data.get("articleId"),
            client_email=state["client_email"],
            reason=state.get("reason", "other"),
            amount=amount,
            channel=state["channel"],
            session_id=state["session_id"],
            applied_rule=state.get("applied_rule", ""),
        )
        refund_result = await trigger_refund(
            order_id=state["order_id"], tenant_id=state["tenant_id"], amount=amount
        )
    except TechnicalFailure:
        return {
            **state,
            "escalated": True,
            "escalation_reason": "technical_action_failed",
            "current_state": "AUTO_ACTION",
            "reply": (
                "I approved your return, but hit a technical snag finalizing it — "
                "a colleague will pick this up right away."
            ),
        }

    return {
        **state,
        "return_id": return_result["returnId"],
        "refund_id": refund_result["refundId"],
        "case_id": return_result["returnId"],
        "action_result": {
            **(state.get("action_result") or {}),
            "summary": (
                f"your return has been approved — label: {return_result['labelUrl']}, "
                f"refund reference {refund_result['refundId']} ({refund_result['delay']})"
            ),
        },
        "attachments": [{"type": "return_label", "url": return_result["labelUrl"]}],
        "current_state": "AUTO_ACTION",
    }
