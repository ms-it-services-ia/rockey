"""The agent's LangGraph state machine (constitution III.4).

States are explicit nodes; every transition has an explicit condition; the current state is
persisted to Redis after every turn (see main.py's turn handler, which calls
`session_store.save_session` after invoking the graph). See data-model.md's "State Machine"
section for the full transition table this module implements.
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from agent.states import (
    auto_action,
    complaint_flow,
    confirmation,
    decision,
    escalation,
    greeting,
    identification,
    qualification,
    return_flow,
    verification,
)


class AgentState(TypedDict, total=False):
    session_id: str
    tenant_id: str
    channel: str
    client_id: str
    messages: list[dict]
    current_state: str

    client_email: str | None
    order_id: str | None
    order_data: dict | None
    article_data: dict | None

    intent: str | None
    reason: str | None
    complaint_description: str | None

    policy_rag: list[str] | None
    eligible: bool | None
    applied_rule: str | None
    decision: str | None  # "auto" | "manual" | "escalated"
    action_result: dict | None

    # Two independent counters (data-model.md fix for the earlier retry_count conflation):
    identification_attempts: int
    reformulation_count: int

    escalated: bool
    escalation_reason: str | None
    case_id: str | None
    return_id: str | None
    refund_id: str | None
    ticket_id: str | None

    reply: str | None
    attachments: list[dict] | None


def _route_after_identification(state: AgentState) -> str:
    if state.get("escalated"):
        return "ESCALATION"
    if state.get("client_email") and state.get("order_id"):
        return "QUALIFICATION"
    # Not yet identified and not yet escalated (attempts < max, or the message didn't even
    # contain an order number/email) — loop back and wait for the customer's next reply.
    return "IDENTIFICATION"


def _route_after_qualification(state: AgentState) -> str:
    if state.get("escalated"):
        return "ESCALATION"
    intent = state.get("intent")
    if intent == "return":
        return "RETURN_FLOW"
    if intent == "complaint":
        return "COMPLAINT_FLOW"
    if intent == "other":
        return "CONFIRMATION"  # out-of-scope: qualification already sent the redirect reply
    # intent is still None (ambiguous, asked a clarifying question, not yet at max) — loop
    # back and wait for the customer's clarification.
    return "QUALIFICATION"


def _route_after_verification(state: AgentState) -> str:
    if state.get("escalated"):
        return "ESCALATION"
    return "DECISION"


def _route_after_decision(state: AgentState) -> str:
    # "refused" (policy-ineligible, e.g. window exceeded or excluded article type) ends in a
    # clear refusal via CONFIRMATION — spec US3 AC4 offers escalation on request, it does not
    # force one. Only "escalated" (eligible but above the auto-refund threshold, or an
    # unrecognized reason) is a *mandatory* escalation (constitution II.2 / V.4).
    decision = state.get("decision")
    if decision == "escalated":
        return "ESCALATION"
    if decision == "refused":
        return "CONFIRMATION"
    return "AUTO_ACTION"


def _route_after_auto_action(state: AgentState) -> str:
    return "ESCALATION" if state.get("escalated") else "CONFIRMATION"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("GREETING", greeting.greeting_node)
    graph.add_node("IDENTIFICATION", identification.identification_node)
    graph.add_node("QUALIFICATION", qualification.qualification_node)
    graph.add_node("RETURN_FLOW", return_flow.return_flow_node)
    graph.add_node("COMPLAINT_FLOW", complaint_flow.complaint_flow_node)
    graph.add_node("VERIFICATION", verification.verification_node)
    graph.add_node("DECISION", decision.decision_node)
    graph.add_node("AUTO_ACTION", auto_action.auto_action_node)
    graph.add_node("ESCALATION", escalation.escalation_node)
    graph.add_node("CONFIRMATION", confirmation.confirmation_node)

    graph.set_entry_point("GREETING")
    graph.add_edge("GREETING", "IDENTIFICATION")
    graph.add_conditional_edges(
        "IDENTIFICATION",
        _route_after_identification,
        {"QUALIFICATION": "QUALIFICATION", "ESCALATION": "ESCALATION", "IDENTIFICATION": "IDENTIFICATION"},
    )
    graph.add_conditional_edges(
        "QUALIFICATION",
        _route_after_qualification,
        {
            "RETURN_FLOW": "RETURN_FLOW",
            "COMPLAINT_FLOW": "COMPLAINT_FLOW",
            "ESCALATION": "ESCALATION",
            "CONFIRMATION": "CONFIRMATION",
            "QUALIFICATION": "QUALIFICATION",
        },
    )
    graph.add_edge("RETURN_FLOW", "VERIFICATION")
    graph.add_edge("COMPLAINT_FLOW", "VERIFICATION")
    graph.add_conditional_edges(
        "VERIFICATION", _route_after_verification, {"DECISION": "DECISION", "ESCALATION": "ESCALATION"}
    )
    graph.add_conditional_edges(
        "DECISION",
        _route_after_decision,
        {"AUTO_ACTION": "AUTO_ACTION", "ESCALATION": "ESCALATION", "CONFIRMATION": "CONFIRMATION"},
    )
    graph.add_conditional_edges(
        "AUTO_ACTION", _route_after_auto_action, {"CONFIRMATION": "CONFIRMATION", "ESCALATION": "ESCALATION"}
    )
    graph.add_edge("ESCALATION", "CONFIRMATION")
    graph.add_edge("CONFIRMATION", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    """Returns the compiled LangGraph StateGraph — the canonical, explicit definition of
    every state and transition condition (constitution III.4). Kept for structural
    validation/visualization; see `run_turn` below for how a turn is actually executed.
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


_NODES = {
    "GREETING": greeting.greeting_node,
    "IDENTIFICATION": identification.identification_node,
    "QUALIFICATION": qualification.qualification_node,
    "RETURN_FLOW": return_flow.return_flow_node,
    "COMPLAINT_FLOW": complaint_flow.complaint_flow_node,
    "VERIFICATION": verification.verification_node,
    "DECISION": decision.decision_node,
    "AUTO_ACTION": auto_action.auto_action_node,
    "ESCALATION": escalation.escalation_node,
    "CONFIRMATION": confirmation.confirmation_node,
}

_UNCONDITIONAL_NEXT = {
    "GREETING": "IDENTIFICATION",
    "RETURN_FLOW": "VERIFICATION",
    "COMPLAINT_FLOW": "VERIFICATION",
    "ESCALATION": "CONFIRMATION",
}

_CONDITIONAL_NEXT = {
    "IDENTIFICATION": _route_after_identification,
    "QUALIFICATION": _route_after_qualification,
    "VERIFICATION": _route_after_verification,
    "DECISION": _route_after_decision,
    "AUTO_ACTION": _route_after_auto_action,
}

# States that need the customer's *next* message before they can do meaningful work
# (identify, qualify intent, or state a reason). A turn always pauses right before
# entering one of these — this is what lets a single HTTP call still traverse
# VERIFICATION -> DECISION -> AUTO_ACTION -> ESCALATION -> CONFIRMATION in one shot once
# enough information has already been collected, while GREETING/IDENTIFICATION/QUALIFICATION/
# RETURN_FLOW/COMPLAINT_FLOW each wait for a fresh reply.
_REQUIRES_FRESH_INPUT = {"IDENTIFICATION", "QUALIFICATION", "RETURN_FLOW", "COMPLAINT_FLOW"}


async def run_turn(state: dict) -> dict:
    """Executes one customer turn: runs the node matching the session's `current_state`
    (defaulting to GREETING for a brand-new session), then keeps advancing through nodes
    that don't need fresh customer input, stopping as soon as one does (or at CONFIRMATION).

    This is a deliberate, documented simplification over LangGraph's own `ainvoke`
    traversal: `ainvoke` always starts at the graph's fixed entry point, which doesn't fit a
    stateless-HTTP, resume-from-Redis conversation. The node functions and routing
    conditions above are the single source of truth either way — `get_graph()` and this
    function both dispatch to the exact same functions.
    """
    current = state.get("current_state") or "GREETING"

    while True:
        state = await _NODES[current](state)

        if current == "CONFIRMATION":
            state["current_state"] = "CONFIRMATION"
            return state

        next_state = (
            _CONDITIONAL_NEXT[current](state)
            if current in _CONDITIONAL_NEXT
            else _UNCONDITIONAL_NEXT[current]
        )
        state["current_state"] = next_state

        if next_state in _REQUIRES_FRESH_INPUT:
            return state

        current = next_state
