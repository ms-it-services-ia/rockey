"""Rockey Python Agent — FastAPI entrypoint (constitution I.2, VIII.3/VIII.4).

Exposes the internal endpoint the Java Gateway calls with the unified internal message
format (contracts/internal-message.md), and runs the mandatory Drive-sync startup check.
"""

import logging

import asyncpg
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from agent.graph import run_turn
from agent.memory import session_store
from agent.rag.rag_indexer import embed_seed_articles, sync_from_drive
from agent.tools.tenant_config_client import get_tenant_config
from config.logging_config import bind_context, configure_logging
from config.settings import settings

configure_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Rockey Python Agent", version="0.1.0")


class ChatRequest(BaseModel):
    session_id: str
    tenant_id: str
    channel: str
    message: str
    client_id: str


class Attachment(BaseModel):
    type: str
    url: str


class ChatResponse(BaseModel):
    session_id: str
    current_state: str
    reply: str
    attachments: list[Attachment] = []
    escalated: bool = False
    case_id: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


_SUPPORTED_CHANNELS = {"web", "email"}


_FALLBACK_CHANNEL_UNAVAILABLE_MESSAGE = (
    "Désolée, ce canal de contact n'est pas disponible pour le moment. Merci de nous "
    "contacter via notre widget de chat en ligne."
)


def unavailable_channel_reply(tenant_config: dict, channel: str) -> str | None:
    """Spec User Story 7 edge case: 'a channel becomes unavailable -> customer sees an
    error message with an alternative channel suggested'. Returns None when the channel
    is fine to proceed on.

    Constitution VI.4: the message itself comes from the retailer's own config
    (`errorMessageChannelUnavailable`, tenant_config's POC stand-in for a Drive-sourced
    value — see V3__add_error_messages.sql), never a hardcoded platform string; the
    module-level constant here is only the last-resort fallback (constitution VI.1 always
    requires *some* normalized message, even if that field is unset).
    """
    if channel not in _SUPPORTED_CHANNELS or (
        channel == "email" and not tenant_config.get("channelEmailActive", False)
    ):
        return tenant_config.get("errorMessageChannelUnavailable") or _FALLBACK_CHANNEL_UNAVAILABLE_MESSAGE
    return None


@app.post("/v1/messages", response_model=ChatResponse)
async def process_message(
    payload: ChatRequest, x_internal_token: str = Header(default="")
):
    if x_internal_token != settings.internal_service_token:
        raise HTTPException(status_code=401, detail="missing_or_invalid_internal_token")

    with bind_context(session_id=payload.session_id, tenant_id=payload.tenant_id):
        tenant_config = await get_tenant_config(payload.tenant_id)
        unavailable_reply = unavailable_channel_reply(tenant_config, payload.channel)
        if unavailable_reply is not None:
            return ChatResponse(
                session_id=payload.session_id,
                current_state="GREETING",
                reply=unavailable_reply,
            )

        session_key = session_store.build_session_key(
            payload.tenant_id, payload.channel, payload.client_id
        )
        existing_state = await session_store.get_session(session_key)

        state = existing_state or {
            "session_id": payload.session_id,
            "tenant_id": payload.tenant_id,
            "channel": payload.channel,
            "client_id": payload.client_id,
            "messages": [],
            "current_state": "GREETING",
            "identification_attempts": 0,
            "reformulation_count": 0,
            "escalated": False,
        }
        state["messages"] = [*state.get("messages", []), {"role": "customer", "content": payload.message}]
        state["_latest_message"] = payload.message

        result = await run_turn(state)

        await session_store.save_session(session_key, result)

        return ChatResponse(
            session_id=payload.session_id,
            current_state=result.get("current_state", "CONFIRMATION"),
            reply=result.get("reply", ""),
            attachments=[Attachment(**a) for a in (result.get("attachments") or [])],
            escalated=result.get("escalated", False),
            case_id=result.get("case_id"),
        )


@app.post("/internal/rag/sync")
async def trigger_rag_sync(tenant_id: str, x_internal_token: str = Header(default="")):
    """Manual RAG resync (T082): lets an operator pick up retailer policy/catalogue edits in
    Drive immediately, without waiting for a restart — startup_rag_sync only runs once, on
    boot, and skips entirely once rag_documents is non-empty (see below)."""
    if x_internal_token != settings.internal_service_token:
        raise HTTPException(status_code=401, detail="missing_or_invalid_internal_token")

    with bind_context(tenant_id=tenant_id):
        tenant_config = await get_tenant_config(tenant_id)
        drive_folder_id = tenant_config.get("driveFolderId")
        if not settings.google_service_account_json or not drive_folder_id:
            raise HTTPException(
                status_code=503,
                detail="Google Drive is not configured (GOOGLE_SERVICE_ACCOUNT_JSON / drive_folder_id)",
            )

        chunks_indexed = await sync_from_drive(tenant_id, drive_folder_id)
        conn = await asyncpg.connect(settings.database_url)
        try:
            articles_embedded = await embed_seed_articles(conn, tenant_id)
        finally:
            await conn.close()

    return {"tenantId": tenant_id, "chunksIndexed": chunks_indexed, "articlesEmbedded": articles_embedded}


@app.on_event("startup")
async def startup_rag_sync() -> None:
    """Constitution VIII.3/VIII.4: sync Drive on first boot; fatal if Drive is unreachable
    and rag_documents is empty; warn (but start) if Drive is unreachable and data exists.
    """
    tenant_id = "vinted"
    with bind_context(tenant_id=tenant_id):
        # tenant_config is relational data — read via Java REST (constitution III.5), never
        # queried directly here. rag_documents is a vector table, so direct pgvector access is
        # fine for the count check.
        tenant_config = await get_tenant_config(tenant_id)
        conn = await asyncpg.connect(settings.database_url)
        try:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM rag_documents WHERE tenant_id = $1", tenant_id
            )
        finally:
            await conn.close()

        if count and count > 0:
            logger.info("RAG already populated for '%s' (%d chunks) — skipping startup sync", tenant_id, count)
            return

        drive_folder_id = tenant_config.get("driveFolderId")
        if not settings.google_service_account_json or not drive_folder_id:
            raise RuntimeError(
                f"rag_documents is empty for '{tenant_id}' and Google Drive is not configured "
                "(GOOGLE_SERVICE_ACCOUNT_JSON / drive_folder_id) — fatal per constitution VIII.4"
            )

        try:
            logger.info("RAG empty for '%s' — syncing from Google Drive", tenant_id)
            await sync_from_drive(tenant_id, drive_folder_id)
            conn = await asyncpg.connect(settings.database_url)
            try:
                await embed_seed_articles(conn, tenant_id)
            finally:
                await conn.close()
        except Exception as exc:
            raise RuntimeError(
                f"Google Drive unreachable and rag_documents is empty for '{tenant_id}' — "
                "fatal per constitution VIII.4"
            ) from exc
