"""Complaint intake (User Story 5, P2) — out of scope for this implementation batch
(Setup/Foundational/US1-US4 only). Present as a minimal pass-through so the graph compiles
and routes correctly; full implementation (reason + free-text description collection,
constitution-aligned) belongs to Phase 7 / tasks T064-T069.
"""


async def complaint_flow_node(state: dict) -> dict:
    # TODO(US5, T066): collect complaint reason + free-text description.
    return {**state, "reason": state.get("reason") or "unspecified"}
