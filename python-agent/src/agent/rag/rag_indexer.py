"""Google Drive -> pgvector RAG indexing (constitution I.7, III.6).

Google Drive is the single source of truth for RAG documents. This module reads a tenant's
Drive folder via the Google Drive MCP / API, extracts text per format, chunks it (500 chars
max, split on line breaks, chunks under 50 chars discarded), embeds each chunk locally with
paraphrase-multilingual-MiniLM-L12-v2, and upserts into `rag_documents`.
"""

import base64
import io
import json
import logging
from typing import Any

import asyncpg
import mammoth
import openpyxl
import pymupdf
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from sentence_transformers import SentenceTransformer

from config.settings import settings

logger = logging.getLogger(__name__)

_MODEL: SentenceTransformer | None = None
CHUNK_SIZE = 500
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_EXPORTABLE_MIME_TO_MIME = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}


def get_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _MODEL


def get_drive_service():
    sa_json = base64.b64decode(settings.google_service_account_json)
    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def list_drive_files(service, folder_id: str) -> list[dict[str, Any]]:
    mime_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
    ]
    query = f"'{folder_id}' in parents AND trashed=false AND (" + " or ".join(
        f"mimeType='{m}'" for m in mime_types
    ) + ")"
    result = service.files().list(q=query, fields="files(id,name,mimeType)").execute()
    return result.get("files", [])


def extract_text_from_drive(service, file: dict[str, Any]) -> str:
    mime = file["mimeType"]
    if mime in _EXPORTABLE_MIME_TO_MIME:
        data = service.files().export(fileId=file["id"], mimeType=_EXPORTABLE_MIME_TO_MIME[mime]).execute()
        return data.decode("utf-8")

    data = service.files().get_media(fileId=file["id"]).execute()
    buf = io.BytesIO(data)
    if mime == "application/pdf":
        doc = pymupdf.open(stream=buf, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    if "wordprocessingml" in mime:
        return mammoth.extract_raw_text(buf).value
    if "spreadsheetml" in mime:
        wb = openpyxl.load_workbook(buf)
        lines = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                line = " | ".join(str(c) for c in row if c is not None)
                if line.strip():
                    lines.append(line)
        return "\n".join(lines)
    raise ValueError(f"Unsupported Drive format: {mime}")


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    lines = text.split("\n")
    chunks: list[str] = []
    current = ""
    for line in lines:
        if len(current) + len(line) > size and current:
            chunks.append(current.strip())
            current = line
        else:
            current += "\n" + line
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 50]


def detect_type(filename: str) -> str:
    name = filename.lower()
    if "policy" in name or "return" in name or "complaint" in name:
        return "policy"
    if "faq" in name:
        return "faq"
    if "catalog" in name:
        return "catalogue"
    return "config"


async def embed_seed_articles(conn: asyncpg.Connection, tenant_id: str) -> int:
    """Embeds any catalog articles that don't yet have an embedding, so
    `rag_query.query_article`'s semantic search (contracts/mcp-tools.md) has vectors to
    compare against. Seed data is inserted via SQL migration without embeddings; this fills
    them in from each article's name + description.
    """
    model = get_model()
    rows = await conn.fetch(
        "SELECT id, name, description FROM articles WHERE tenant_id = $1 AND embedding IS NULL",
        tenant_id,
    )
    for row in rows:
        text = f"{row['name']}. {row['description'] or ''}"
        embedding = model.encode(text).tolist()
        await conn.execute(
            "UPDATE articles SET embedding = $1 WHERE id = $2", str(embedding), row["id"]
        )
    return len(rows)


async def sync_from_drive(tenant_id: str, folder_id: str) -> int:
    """Full re-sync of a tenant's RAG documents. Returns the number of chunks indexed."""
    service = get_drive_service()
    files = list_drive_files(service, folder_id)
    model = get_model()

    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute("DELETE FROM rag_documents WHERE tenant_id = $1", tenant_id)
        total = 0
        for file in files:
            try:
                text = extract_text_from_drive(service, file)
                chunks = chunk_text(text)
                for i, chunk in enumerate(chunks):
                    embedding = model.encode(chunk).tolist()
                    await conn.execute(
                        """
                        INSERT INTO rag_documents (tenant_id, source, type, chunk_index, content, embedding)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (tenant_id, source, chunk_index) DO UPDATE
                            SET content = EXCLUDED.content, embedding = EXCLUDED.embedding
                        """,
                        tenant_id,
                        file["name"],
                        detect_type(file["name"]),
                        i,
                        chunk,
                        str(embedding),
                    )
                    total += 1
                logger.info("Indexed %s -> %d chunks", file["name"], len(chunks))
            except Exception:
                logger.exception("Failed to index Drive file %s", file.get("name"))

        await conn.execute(
            "UPDATE tenant_config SET last_sync_at = NOW(), last_sync_status = 'success' WHERE tenant_id = $1",
            tenant_id,
        )
        logger.info("Drive sync complete for '%s': %d chunks", tenant_id, total)
        return total
    finally:
        await conn.close()
