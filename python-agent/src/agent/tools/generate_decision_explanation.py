"""Composes a policy-grounded, LLM-phrased explanation of a return/complaint refusal
(constitution I.7: the retailer's Drive-sourced RAG policy grounds the explanation).

Constitution V.3 requires the eligibility decision itself to stay 100% rule-based (never
LLM intuition) — this function never decides anything, it only composes how an
already-made decision is *explained* to the customer.

Best-effort by design: any failure anywhere in this pipeline (tenant lookup, policy
retrieval, or the LLM call itself) falls back to the caller-supplied deterministic text, so
this can only improve a reply, never break one (constitution VI.1).
"""

import logging

from anthropic import AsyncAnthropic

from agent.prompts.system_prompt import render_system_prompt
from agent.rag.rag_query import query_policy
from agent.tools.tenant_config_client import get_tenant_config
from config.circuit_breaker import call_with_breaker
from config.settings import settings

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def generate_decision_explanation(
    *,
    tenant_id: str,
    channel: str,
    current_state: str,
    question: str,
    article_context: str,
    fallback_text: str,
) -> str:
    try:
        tenant_config = await get_tenant_config(tenant_id)

        policy_chunks = await call_with_breaker(
            "pgvector", lambda: query_policy(tenant_id, question), on_fallback=list
        )
        policy_context = "\n\n".join(policy_chunks)

        system_prompt = render_system_prompt(
            agent_first_name=tenant_config.get("agentFirstName") or "the assistant",
            retailer_name=tenant_id.capitalize(),
            agent_tone=tenant_config.get("agentTone") or "professional",
            agent_formality=tenant_config.get("agentFormality") or "formal",
            agent_language=tenant_config.get("agentLanguage") or "English",
            policy_context=policy_context,
            article_context=article_context,
            channel=channel,
            current_state=current_state,
        )

        async def _call() -> str:
            response = await _get_client().messages.create(
                model=settings.anthropic_model,
                max_tokens=500,
                system=system_prompt,
                messages=[{"role": "user", "content": question}],
            )
            # Some models emit a ThinkingBlock before the TextBlock, so content[0] isn't
            # always the reply text — find the first text block instead.
            for block in response.content:
                if block.type == "text":
                    return block.text.strip()
            raise ValueError("no text block in LLM response")

        return await call_with_breaker("llm", _call, on_fallback=lambda: fallback_text)
    except Exception:
        logger.exception("generate_decision_explanation failed; using deterministic fallback")
        return fallback_text
