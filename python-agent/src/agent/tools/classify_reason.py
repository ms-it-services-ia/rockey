"""LLM-based reason classification for RETURN_FLOW and COMPLAINT_FLOW — the same
keyword-fragility pattern qualification.py had (see classify_message.py), one level deeper:
real customer phrasing ("pas encore reçu" vs "pas reçu") kept outpacing fixed keyword lists,
so this replaces exact-phrase matching for *why* the customer wants a return/refund, not just
*whether* it's a return or a complaint.

Constitution V.3 still holds: this only classifies the customer's stated reason — it never
decides the eligibility/refund outcome, which stays 100% rule-based in Java's
EligibilityService (which doesn't branch its own logic on this reason string at all; it's
used for record-keeping and, for returns, fee-structure context).
"""

from typing import Literal

from anthropic import AsyncAnthropic

from config.circuit_breaker import call_with_breaker
from config.settings import settings

ComplaintReason = Literal[
    "quality_defect", "damaged_on_delivery", "non_conformity", "wrong_item", "not_received", "other", "ambiguous"
]
ReturnReason = Literal["wrong_size", "change_of_mind", "non_conforming", "not_received", "other", "ambiguous"]

_SYSTEM_PROMPT = (
    "You classify a single customer service message for a secondhand fashion marketplace. "
    "The customer may write in French or English. Call the provided tool with the single "
    "best-fitting category, based only on what the customer actually wrote — never guess "
    "beyond the text itself."
)

_COMPLAINT_REASON_TOOL = {
    "name": "classify_complaint_reason",
    "description": "Classifies why a customer is filing a quality complaint.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": [
                    "quality_defect",
                    "damaged_on_delivery",
                    "non_conformity",
                    "wrong_item",
                    "not_received",
                    "other",
                    "ambiguous",
                ],
                "description": (
                    "quality_defect: the item is defective, faulty, broken, or doesn't "
                    "work, for reasons other than shipping damage. "
                    "damaged_on_delivery: the item arrived visibly damaged or broken, "
                    "consistent with shipping/transit damage. "
                    "non_conformity: the item doesn't match its listing — wrong material, "
                    "wrong color, or otherwise different from what was described — but the "
                    "customer has it in hand. "
                    "wrong_item: an entirely different item than what was ordered was sent. "
                    "not_received: the customer never received the item, it's lost, "
                    "missing, or untraceable — there is no physical item in hand. "
                    "other: a genuine, understood quality issue that just doesn't fit any "
                    "of the above categories. "
                    "ambiguous: the message is too vague or unclear to tell which category "
                    "applies, even considering the full message — use this only when "
                    "genuinely undeterminable, not merely because it's brief."
                ),
            },
        },
        "required": ["category"],
    },
}

_RETURN_REASON_TOOL = {
    "name": "classify_return_reason",
    "description": "Classifies why a customer wants to return an item they have in hand.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["wrong_size", "change_of_mind", "non_conforming", "not_received", "other", "ambiguous"],
                "description": (
                    "wrong_size: the item doesn't fit — too small, too big, wrong size. "
                    "change_of_mind: the customer simply no longer wants the item, changed "
                    "their mind, or has a different preference — unrelated to any defect. "
                    "non_conforming: the item doesn't match its listing (wrong material, "
                    "wrong color) but the customer has it in hand and isn't describing "
                    "damage or a missing item. "
                    "not_received: the customer never received the item, it's lost, "
                    "missing, or untraceable. "
                    "other: a genuine, understood return reason that just doesn't fit any "
                    "of the above categories. "
                    "ambiguous: the message is too vague or unclear to tell which category "
                    "applies, even considering the full message — use this only when "
                    "genuinely undeterminable, not merely because it's brief."
                ),
            },
        },
        "required": ["category"],
    },
}

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def _classify(message: str, tool: dict) -> str:
    valid_categories = tool["input_schema"]["properties"]["category"]["enum"]

    async def _call() -> str:
        response = await _get_client().messages.create(
            model=settings.anthropic_model,
            max_tokens=100,
            system=_SYSTEM_PROMPT,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": message}],
        )
        for block in response.content:
            if block.type == "tool_use":
                category = block.input.get("category")
                return category if category in valid_categories else "ambiguous"
        raise ValueError("no tool_use block in classification response")

    return await call_with_breaker("llm", _call)


async def classify_complaint_reason(message: str) -> ComplaintReason:
    """Raises TechnicalFailure (via call_with_breaker) if the LLM call fails after retries —
    the caller must escalate rather than silently guess (constitution VI.1)."""
    return await _classify(message, _COMPLAINT_REASON_TOOL)


async def classify_return_reason(message: str) -> ReturnReason:
    """Raises TechnicalFailure (via call_with_breaker) if the LLM call fails after retries —
    the caller must escalate rather than silently guess (constitution VI.1)."""
    return await _classify(message, _RETURN_REASON_TOOL)
