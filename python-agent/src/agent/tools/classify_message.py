"""LLM-based intent classification (research.md §4's original design: "Free-text customer
input needs semantic understanding, not just keyword matching" — keyword matching was
explicitly rejected there as "too brittle against natural language", and was only used as a
POC stopgap since it doesn't need a live ANTHROPIC_API_KEY in automated tests. Replaced after
real customer testing repeatedly proved that rejection right: every fixed keyword list was
outpaced by the next natural phrasing variation ("pas encore reçu" vs "pas reçu", "je ne le
trouve pas" vs "introuvable", etc).

Constitution V.3 still holds: this only classifies *what the customer is asking for*, never
decides an eligibility/refund outcome — those stay 100% rule-based in Java's
EligibilityService, untouched by this module.
"""

from typing import Literal

from anthropic import AsyncAnthropic

from config.circuit_breaker import call_with_breaker
from config.settings import settings

Category = Literal[
    "return_request", "non_delivery", "quality_complaint", "case_status_question", "closing", "other", "ambiguous"
]

_CATEGORIES: tuple[Category, ...] = (
    "return_request",
    "non_delivery",
    "quality_complaint",
    "case_status_question",
    "closing",
    "other",
    "ambiguous",
)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


_CLASSIFY_TOOL = {
    "name": "classify_customer_message",
    "description": "Classifies a customer service message into exactly one category.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": list(_CATEGORIES),
                "description": (
                    "return_request: the customer wants to send back an item they received, "
                    "for a change-of-mind reason (wrong size, no longer wanted, wrong color "
                    "preference, etc) — they have the item in hand. "
                    "non_delivery: the customer says they never received the item, it's "
                    "lost, missing, or they otherwise can't locate/track it down — there is "
                    "no physical item in their possession to ship back. "
                    "quality_complaint: the customer has the item but it's damaged, "
                    "defective, not as described, or the wrong item was sent. "
                    "case_status_question: the customer is asking about the status, outcome, "
                    "or progress of a request they already made — not describing a new "
                    "issue (e.g. \"will I get refunded?\", \"has my case been reviewed?\", "
                    "\"what happens next?\"). "
                    "closing: the customer is ending the conversation — thanking, saying "
                    "goodbye, or otherwise indicating they have nothing further to ask (e.g. "
                    "\"ok merci\", \"c'est tout\", \"au revoir\", \"nothing else, thanks\"). "
                    "other: unrelated to returns/complaints/delivery (pricing, promotions, "
                    "general questions, anything out of scope for after-sales support). "
                    "ambiguous: genuinely unclear which of the above applies even considering "
                    "the full message — use this only when the message truly could not be "
                    "classified, not merely because it's brief."
                ),
            },
        },
        "required": ["category"],
    },
}

_SYSTEM_PROMPT = (
    "You classify a single customer service message for a secondhand fashion marketplace. "
    "The customer may write in French or English. Read the message and call "
    "classify_customer_message with the single best-fitting category, based only on what "
    "the customer actually wrote — never guess intent beyond the text itself."
)


async def classify_message(message: str) -> Category:
    """Returns one of the categories above. Raises TechnicalFailure (via call_with_breaker,
    no on_fallback) if the LLM call fails after retries — the caller must escalate rather
    than silently guess (constitution VI.1)."""

    async def _call() -> Category:
        response = await _get_client().messages.create(
            model=settings.anthropic_model,
            max_tokens=100,
            system=_SYSTEM_PROMPT,
            tools=[_CLASSIFY_TOOL],
            tool_choice={"type": "tool", "name": "classify_customer_message"},
            messages=[{"role": "user", "content": message}],
        )
        for block in response.content:
            if block.type == "tool_use":
                category = block.input.get("category")
                return category if category in _CATEGORIES else "ambiguous"
        raise ValueError("no tool_use block in classification response")

    return await call_with_breaker("llm", _call)
