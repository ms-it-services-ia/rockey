"""Static YAML RAG fallback (constitution VI.3).

Loaded once into memory at import time. Used only when a `query_policy`/`query_article` call
exceeds TIMEOUT_PGVECTOR (5s, see config.circuit_breaker). Every use MUST be alert-logged so
the fallback's usage is visible to operators.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_FALLBACK_PATH = Path(__file__).parent / "fallback_policy.yaml"
_fallback_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _fallback_cache
    if _fallback_cache is None:
        with open(_FALLBACK_PATH) as f:
            _fallback_cache = yaml.safe_load(f)
    return _fallback_cache


def get_fallback_policy(tenant_id: str) -> dict[str, Any]:
    """Returns the static policy mirror for a tenant, alert-logging the fallback's use."""
    policy = _load().get(tenant_id)
    if policy is None:
        logger.error("RAG_FALLBACK_MISS tenant_id=%s no static policy configured", tenant_id)
        return {}
    logger.warning("RAG_FALLBACK_USED tenant_id=%s — pgvector timed out, using static policy", tenant_id)
    return policy
