# Quickstart: Validating the Vinted POC Agent

This is a runnable validation guide, not an implementation spec — see `data-model.md` for
entities/state machine and `contracts/` for the exact request/response shapes.

## Prerequisites

- Docker + Docker Compose
- A `.env` populated from `.env.example` with at minimum: `ANTHROPIC_API_KEY`,
  `POSTGRES_PASSWORD`, `DATABASE_URL`, `INTERNAL_SERVICE_TOKEN`,
  `GOOGLE_SERVICE_ACCOUNT_JSON`, `VINTED_DRIVE_FOLDER_ID` (per constitution VIII.2)
- The Vinted Google Drive folder shared with the service account, containing the 5 reference
  documents (return policy, complaint policy, FAQ, catalog, agent config)

## Setup

```bash
docker compose up -d postgres redis
docker compose up -d java-gateway   # runs Flyway migrations + SQL seed (tenant_config, articles, orders)
docker compose up -d python-agent   # syncs Drive -> pgvector on first boot if rag_documents is empty
curl -f http://localhost:8080/actuator/health
curl -f http://localhost:8000/health
```

Expected: both health checks return `200`. On first boot, `python-agent` logs should show a
successful Drive sync (chunk counts per document) rather than a fatal error — a fatal error
here means `VINTED_DRIVE_FOLDER_ID` is missing/wrong or the service account can't reach the
folder (constitution VIII.4).

## Validation scenarios

Run each of the 5 POC test scenarios from `spec.md` § Success Criteria through the REST
fallback endpoint (`contracts/channel-apis.md`):

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "X-Tenant-ID: vinted" -H "Content-Type: application/json" \
  -d '{"message": "Bonjour, je voudrais retourner un article"}'
```

1. **Eligible return** — identify as Marie Dupont / `CMD-2026-00001` (VTG-001, €68,
   delivered 15 days ago, item intact) → expect a generated return label and a triggered
   refund in the final response's `attachments` and `case_id`.
2. **Return past deadline** — same flow but for an order delivered 45+ days ago → expect a
   refusal reply citing the return window, with an escalation offer in the next turn.
3. **Defective item, amount above threshold** — identify as Sophie Bernard /
   `CMD-2026-00003` (VTG-011, €265, defective) → expect `escalated: true` in the final
   response and a Slack message in the configured `#support-vinted` channel (or a skip
   warning in logs if `SLACK_MCP_TOKEN` is absent).
4. **Non-returnable item** — identify as Lucas Petit / `CMD-2026-00004` (VTG-003, a
   `piece_unique` item, €210) → expect a refusal reply citing the unique-piece exclusion,
   no escalation required unless the customer asks for one.
5. **Failed identification** — send two wrong order numbers in a row → expect the third
   response to offer escalation rather than asking for the order number a third time.

## Pass criteria

- All 5 scenarios complete without a raw technical error ever reaching the simulated
  customer (constitution VI.1).
- Each Dossier/Case row created in PostgreSQL has a non-null `applied_rule` once a decision
  is reached (constitution V.3).
- No response ever contains the words "Rockey", "AI", "algorithm", or "automated system"
  (spec FR-013 / constitution V.1).
- Restarting `python-agent` after the first successful sync does NOT re-trigger a full Drive
  sync (constitution VIII.3 — `rag_documents` already populated → skip).
