"""pgvector queries used by the agent at runtime (constitution III.5, III.7).

Two patterns: pure-similarity policy RAG, and hybrid SQL + similarity article lookup.
Both are wrapped by the pgvector circuit breaker (research.md §8) at the call site.
"""

import asyncpg

from agent.rag.rag_indexer import get_model
from config.settings import settings


async def query_policy(tenant_id: str, question: str, k: int = 3) -> list[str]:
    embedding = get_model().encode(question).tolist()
    conn = await asyncpg.connect(settings.database_url)
    try:
        rows = await conn.fetch(
            """
            SELECT content FROM rag_documents
            WHERE tenant_id = $1
            ORDER BY embedding <=> $2::vector
            LIMIT $3
            """,
            tenant_id,
            str(embedding),
            k,
        )
        return [r["content"] for r in rows]
    finally:
        await conn.close()


async def query_article(
    tenant_id: str,
    question: str,
    max_price: float | None = None,
    returnable: bool | None = None,
    limit: int = 5,
) -> list[dict]:
    embedding = get_model().encode(question).tolist()
    conn = await asyncpg.connect(settings.database_url)
    try:
        filters = ["tenant_id = $1", "active = true"]
        params: list = [tenant_id, str(embedding)]
        if returnable is not None:
            filters.append(f"returnable = ${len(params) + 1}")
            params.append(returnable)
        if max_price is not None:
            filters.append(f"price <= ${len(params) + 1}")
            params.append(max_price)
        where = " AND ".join(filters)
        rows = await conn.fetch(
            f"""
            SELECT id, name, price, returnable, non_return_reason, article_type
            FROM articles
            WHERE {where}
            ORDER BY embedding <=> $2::vector
            LIMIT {limit}
            """,
            *params,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_article_by_id(article_id: str, tenant_id: str) -> dict | None:
    conn = await asyncpg.connect(settings.database_url)
    try:
        row = await conn.fetchrow(
            """
            SELECT id, name, price, returnable, non_return_reason, article_type, category
            FROM articles
            WHERE id = $1 AND tenant_id = $2 AND active = true
            """,
            article_id,
            tenant_id,
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def rag_documents_count(tenant_id: str) -> int:
    conn = await asyncpg.connect(settings.database_url)
    try:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM rag_documents WHERE tenant_id = $1", tenant_id
        )
    finally:
        await conn.close()
