"""Single LLM-based "turn interpreter" (research.md §4, generalized): every graph node that
needs to understand free-text customer input calls this one function instead of maintaining
its own hand-rolled classifier/enum. Replaces classify_message.py and classify_reason.py.

The problem those four separate classifiers kept hitting, in a different spot each time: a
hand-rolled enum for one specific conversational moment (e.g. "did you check with your
neighbors?") has no room for outcomes nobody thought to enumerate up front — most recently,
classify_verification_reply's `confirmed_not_found | not_yet_checked | ambiguous` had no slot
for "I found it", so a customer saying so got folded into `ambiguous` and escalated anyway.

Every conversational moment splits into two independent questions: (1) is the customer doing
one of a small set of *universal* things any message can always do — ending the conversation,
asking about an existing case, indicating whatever was being asked about no longer applies, or
being genuinely unclear — checked identically everywhere via `signal`; and only if none of
those apply, (2) which node-specific, business-vocabulary category does the message state
(`category`, from the small list the calling node provides). Unifying (1) means a node can no
longer forget to handle "the customer found the package" simply because nobody added it to
that one node's enum — there's only one enum for these cross-cutting cases, not four.

Constitution V.3 still holds: this only classifies what the customer said, never decides an
eligibility/refund outcome — that stays 100% rule-based in Java's EligibilityService.
"""

from dataclasses import dataclass
from typing import Literal

from anthropic import AsyncAnthropic

from config.circuit_breaker import call_with_breaker
from config.settings import settings

Signal = Literal["on_topic", "closing", "case_status_question", "resolved", "ambiguous"]
_SIGNALS: frozenset[str] = frozenset({"on_topic", "closing", "case_status_question", "resolved", "ambiguous"})


@dataclass(frozen=True)
class TurnCategory:
    """One node-specific, business-vocabulary option — e.g. "wrong_size" is only ever a
    meaningful answer to "why do you want to return this", never to "did you check with your
    neighbors", so this part of the classification can't be unified away."""

    value: str
    description: str


@dataclass(frozen=True)
class TurnInterpretation:
    signal: Signal
    category: str | None = None  # populated only when signal == "on_topic"


_SYSTEM_PROMPT_TEMPLATE = (
    "You interpret a single customer service message for a secondhand fashion marketplace. "
    "The customer may write in French or English. Context for this message: {context}\n\n"
    "Call classify_turn with exactly one of:\n"
    '- signal="on_topic" plus the single best-fitting category from the provided list, if '
    "the message directly addresses the context above.\n"
    '- signal="closing" if the customer is ending the whole conversation (thanking, saying '
    "goodbye, nothing else to ask).\n"
    '- signal="case_status_question" if the customer is asking about the status, outcome, or '
    "progress of their request rather than answering or stating something new.\n"
    '- signal="resolved" if whatever is being asked about here is no longer an issue — the '
    "customer found what was missing, changed their mind, or wants to withdraw this "
    "specific request.\n"
    '- signal="ambiguous" only when genuinely unclear which of the above applies, even '
    "considering the full message — never use this merely because it's brief.\n"
    "Base this only on what the customer actually wrote — never guess beyond the text itself."
)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _build_tool(categories: list[TurnCategory]) -> dict:
    category_descriptions = " ".join(f"{c.value}: {c.description}." for c in categories)
    return {
        "name": "classify_turn",
        "description": "Classifies a single customer message within the given conversational context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "signal": {
                    "type": "string",
                    "enum": list(_SIGNALS),
                    "description": (
                        "on_topic: the message directly addresses the current context (see "
                        "'category'). closing: ending the whole conversation. "
                        "case_status_question: asking about an existing request's status "
                        "rather than stating something new. resolved: whatever was being "
                        "asked about no longer applies. ambiguous: genuinely unclear, not "
                        "merely brief."
                    ),
                },
                "category": {
                    "type": "string",
                    "enum": [c.value for c in categories],
                    "description": f"Required when signal is 'on_topic'. {category_descriptions}",
                },
            },
            "required": ["signal"],
        },
    }


async def interpret_turn(message: str, context: str, categories: list[TurnCategory]) -> TurnInterpretation:
    """Raises TechnicalFailure (via call_with_breaker, no on_fallback) if the LLM call fails
    after retries — the caller must escalate rather than silently guess (constitution
    VI.1)."""
    tool = _build_tool(categories)
    valid_categories = {c.value for c in categories}
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(context=context)

    async def _call() -> TurnInterpretation:
        response = await _get_client().messages.create(
            model=settings.anthropic_model,
            max_tokens=150,
            system=system_prompt,
            tools=[tool],
            tool_choice={"type": "tool", "name": "classify_turn"},
            messages=[{"role": "user", "content": message}],
        )
        for block in response.content:
            if block.type == "tool_use":
                signal = block.input.get("signal")
                if signal not in _SIGNALS:
                    signal = "ambiguous"
                if signal != "on_topic":
                    return TurnInterpretation(signal=signal)
                category = block.input.get("category")
                # Defensive: never trust an unrecognized/missing category blindly
                # (constitution VI.1) — a category outside THIS call's valid set is treated
                # as if the model itself weren't sure, rather than silently routed.
                if category not in valid_categories:
                    return TurnInterpretation(signal="ambiguous")
                return TurnInterpretation(signal="on_topic", category=category)
        raise ValueError("no tool_use block in classification response")

    return await call_with_breaker("llm", _call)
