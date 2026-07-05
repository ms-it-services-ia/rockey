# Phase 1 Data Model: AI Customer Service Agent (Vinted POC)

Entities are grouped by storage per constitution III.5: **relational** data lives in
PostgreSQL and is only ever reached through the Java Gateway/services; **vector** data
(`rag_documents`, `articles`) is also in PostgreSQL (via `pgvector`) but is read/written
directly by the Python Agent; **session** state is ephemeral, in Redis only.

## Relational + vector entities (PostgreSQL 16 + pgvector)

### TenantConfig

Configuration for a single retailer (tenant). One row exists for this POC: `vinted`.

| Field | Type | Notes |
|---|---|---|
| `tenant_id` | string, PK | `"vinted"` for this POC |
| `product` | string | always `"rockey"` |
| `agent_first_name` | string | `"Léa"` |
| `agent_tone` | text | e.g. "warm, empathetic and passionate about vintage fashion" |
| `agent_formality` | enum | `formal` \| `informal` |
| `agent_language` | string | ISO code, `"fr"` |
| `channel_web_active` | boolean | |
| `channel_email_active` | boolean | |
| `channel_email_imap` | string, nullable | e.g. `imap.gmail.com:993` |
| `channel_email_address` | string, nullable | e.g. `sav@vinted.com` |
| `channel_slack_active` | boolean | |
| `channel_slack_channel` | string, nullable | e.g. `#support-vinted` |
| `drive_folder_id` | string, nullable | Google Drive folder ID (source of truth for policy) |
| `drive_sync_mode` | enum | `auto` \| `manual` |
| `drive_sync_cron` | string | default `0 2 * * *` |
| `last_sync_at` / `last_sync_status` | timestamp / string | observability of the RAG sync |

**Validation**: `drive_folder_id` MUST be present before the agent can serve any request for
that tenant (constitution VIII.4 — fatal error at startup otherwise, unless `rag_documents`
already has data for the tenant).

### RagDocument

A chunk of a policy/FAQ/catalog document synced from the retailer's Google Drive folder.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `tenant_id` | string, FK → TenantConfig | |
| `source` | string | original filename, e.g. "Return Policy.pdf" |
| `type` | enum | `policy` \| `faq` \| `catalogue` \| `config` |
| `chunk_index` | integer | position within the source document |
| `content` | text | chunk text (≤ 500 chars, per constitution III.6) |
| `embedding` | vector(384) | HNSW-indexed, cosine similarity |

**Validation**: unique on `(tenant_id, source, chunk_index)`; chunks under 50 characters are
discarded at indexing time and never stored (constitution III.6).

### Article

A catalog item the retailer sells, used for return/complaint eligibility lookups.

| Field | Type | Notes |
|---|---|---|
| `id` | string, PK | e.g. `VTG-001` (catalog SKU prefix unchanged by this feature) |
| `tenant_id` | string, FK → TenantConfig | default `vinted` |
| `name`, `category`, `sub_category` | string | descriptive |
| `price` | decimal | |
| `returnable` | boolean | derived from policy exclusions |
| `non_return_reason` | string, nullable | populated when `returnable = false` |
| `article_type` | enum | `standard` \| `premium` \| `piece_unique` \| `destockage` \| `bijou` \| `ceinture` — internal technical tokens (unaffected by the Vintage→Vinted naming decision, which applies to prose/display, not code enum values) |
| `active` | boolean | |
| `embedding` | vector(384) | for semantic article lookup |

### Order

A past purchase, used to verify customer identification (User Story 1).

| Field | Type | Notes |
|---|---|---|
| `id` | string, PK | e.g. `CMD-2026-00001` |
| `tenant_id` | string, FK → TenantConfig | |
| `client_email`, `client_name` | string | used for identification matching |
| `article_id` | string, FK → Article | |
| `amount` | decimal | drives auto-refund vs. escalation threshold |
| `status` | enum | e.g. `delivered` |
| `order_date`, `delivery_date` | date | delivery date anchors the return-window check |

### Case / Dossier

A single return or complaint request being processed (maps to spec's "Case" entity).

| Field | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `tenant_id` | string, FK → TenantConfig | |
| `client_email` | string | |
| `order_id` | string, FK → Order | |
| `article_id` | string, FK → Article | |
| `type` | enum | `return` \| `complaint` |
| `reason` | string | |
| `status` | enum | `in_progress` \| `resolved` \| `escalated` |
| `decision` | enum, nullable | `accepted` \| `refused` \| `escalated` |
| `amount` | decimal, nullable | |
| `channel` | enum | `web` \| `email` |
| `session_id` | string | correlates to the Redis session that produced this case |
| `applied_rule` | string | the specific policy rule that drove the decision (for traceability, per constitution V.3) |
| `return_id` / `refund_id` / `ticket_id` | string, nullable | references to the action taken |

**State transitions** (`status`): `in_progress → resolved` (auto-approved or manually
confirmed) or `in_progress → escalated` (irreversible, per constitution V.4 — no transition
back to `in_progress` once `escalated`).

### ClientHistory

Long-term memory across sessions for a given customer, used to detect repeated
complaints (spec User Story 5 edge case).

| Field | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `tenant_id` | string, FK → TenantConfig | |
| `client_email` | string | unique per `(tenant_id, client_email)` |
| `return_count`, `complaint_count`, `escalation_count` | integer | running totals |
| `last_contact` | timestamp | |

## Ephemeral entity (Redis only)

### Session

The live conversational state for one customer interaction. Never persisted to PostgreSQL.

| Field | Type | Notes |
|---|---|---|
| `session_id` | string, key | |
| `tenant_id`, `channel` | string | part of the resumption key, per research.md §5 |
| `current_state` | enum | LangGraph node name (see State Machine below) |
| `messages` | list | conversation turns so far |
| `client_email`, `order_id` | string, nullable | filled once identification succeeds |
| `intent`, `reason` | string, nullable | filled during qualification |
| `identification_attempts` | integer | resets to 0 on session start; capped at 2 (constitution V.2) — exceeding it fires the `IDENTIFICATION → ESCALATION` fallback |
| `reformulation_count` | integer | resets to 0 once `IDENTIFICATION` succeeds; capped at 3 (constitution III.4) — exceeding it fires the "+3 exchanges without progress" `ESCALATION` fallback from any state |
| TTL | 30 minutes, sliding | expires the session; matches constitution I.2 |

These are two independent counters, not one — an implementer must not reuse the same
variable across the identification and post-identification phases.

## State Machine (LangGraph nodes, backing the Session's `current_state`)

```
GREETING → IDENTIFICATION → QUALIFICATION → {RETURN_FLOW | COMPLAINT_FLOW} → VERIFICATION
  → DECISION → {AUTO_ACTION | ESCALATION | CONFIRMATION} → CONFIRMATION → END
```

Fallback edges to `ESCALATION` (per constitution III.4 and spec User Story 4):
- `IDENTIFICATION`: after 2 failed attempts → `ESCALATION` (reason: `identification_failed`)
- `QUALIFICATION`: still unclear after 2 clarifications → `ESCALATION` (reason:
  `qualification_unclear`). Intent classified as "other" (out-of-scope) is NOT an escalation
  — it's a polite redirect straight to `CONFIRMATION` (spec FR-004 / User Story 2 AC3).
- `VERIFICATION`: eligibility service unavailable → `ESCALATION` (reason: `service_unavailable`)
- `DECISION`: amount above the auto-refund threshold, or an unrecognized reason →
  `ESCALATION` (mandatory, constitution II.2/V.4). An *ineligible* item (policy exclusion,
  return window exceeded) is NOT an automatic escalation — it's a clear refusal straight to
  `CONFIRMATION`, with escalation offered on request (spec User Story 3 AC4).
- `AUTO_ACTION`: the return/refund action itself fails → `ESCALATION` (reason:
  `technical_action_failed`)
- Any state: more than 3 exchanges without progress → `ESCALATION`

`ESCALATION` and `AUTO_ACTION` both converge on `CONFIRMATION`, which always transitions to
`END`. `ESCALATION` is a terminal decision for the session — no edge leads back out of it.
