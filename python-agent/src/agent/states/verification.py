"""VERIFICATION node (spec User Story 3, AC2): calls verify_eligibility and traces the
applied_rule (constitution V.3). A technical failure here always escalates
(data-model.md State Machine: "VERIFICATION: eligibility service unavailable -> ESCALATION")."""

from agent.tools.verify_eligibility import verify_eligibility
from config.circuit_breaker import TechnicalFailure


async def verification_node(state: dict) -> dict:
    article_data = state.get("article_data") or {}

    try:
        result = await verify_eligibility(
            order_id=state["order_id"],
            tenant_id=state["tenant_id"],
            reason=state.get("reason", "other"),
            article_data=article_data,
            request_type=state.get("intent", "return"),
        )
    except TechnicalFailure:
        return {
            **state,
            "escalated": True,
            "escalation_reason": "service_unavailable",
            "current_state": "VERIFICATION",
            "reply": (
                "J'ai des difficultés à vérifier votre éligibilité en ce moment — je fais "
                "intervenir un collègue pour vous aider."
            ),
        }

    return {
        **state,
        "eligible": result["eligible"],
        "applied_rule": result["appliedRule"],
        "action_result": {
            **(state.get("action_result") or {}),
            "eligibility_reason": result["reason"],
            "auto_approvable": result["autoApprovable"],
        },
        "current_state": "VERIFICATION",
    }
