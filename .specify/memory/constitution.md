<!--
Sync Impact Report
==================
Version change: 4.0.1 → 5.0.0

Rationale for MAJOR bump: this amendment edits Article 0 (Product Identity) and
Article I (Technical Stack), both marked **Non-Negotiable**. Per this constitution's
own Governance section, "A section marked Non-Negotiable can only be changed via a
new MAJOR version." The terminology change alone (brand → retailer/tenant) would
touch Article 0; combined with restored principles below, a MAJOR bump is required.

Modified principles:
  - Terminology standardized project-wide: "brand" → "retailer" (external-facing),
    aligning with the "tenant"/`tenant_id`/`tenant_config` naming already used in the
    data model. Affects Article 0, I.4b, I.5, I.7, Article II, IV.2, IX.
  - Product tagline: "Multi-brand AI Customer Support Platform" →
    "Multi-tenant AI Customer Service Platform".
  - I.4b internal channel format: fixed leftover French field name `canal` → `channel`.
  - V.1 Scope: restored explicit prohibition on the agent mentioning "AI", "algorithm",
    or "automated system" (previously narrowed to only prohibiting the word "Rockey").
    Restored explicit topic list (return, complaint, refund, tracking) and the
    "never ignored" / "never promise a refund before verification" clauses.
  - V.3 Automatic decision: restored "never LLM intuition" clause and tied auto-refund
    thresholds explicitly to per-retailer Google Drive config (not the prompt).
  - VI.4 (was VI.3) Normalized customer messages: source of truth changed from a local
    `seuils.yaml` file to per-retailer Google Drive config, for consistency with
    Article I.7 ("Google Drive is the single source of truth").
  - IX.1: fixed leftover French template placeholder `{langue}` → `{language}`.

Added sections:
  - III.3 Multi-tenant (strict data isolation: "no data from one retailer can leak to
    another") — previously only implied, never stated as an explicit rule.
  - III.4 State Machine (LangGraph states are explicit, transitions persisted in Redis,
    maximum 3 reformulations before automatic escalation) — was entirely absent.
  - III.1 gained three explicit non-negotiable rules (no business logic in the Gateway,
    no direct DB calls from Python, no intelligence in Java) and "channel adapters"
    in the Java Gateway's responsibilities.
  - VI.1 General principle (every external call wrapped in try/catch with timeout, no
    raw technical error ever exposed to the customer, structured JSON error logs with
    session_id/tenant_id/timestamp) — was entirely absent.
  - VII.1 gained an explicit Contract tests requirement (each MCP tool verified with a
    Java mock) and an explicit "UI and load tests are out of POC scope" statement.
  - VIII.2 gained the required email-channel environment variables for Vinted
    (VINTED_EMAIL_IMAP, VINTED_EMAIL_USER, VINTED_EMAIL_PASSWORD), matching the
    Email channel already specified in I.4b but previously missing from deployment.

Removed sections: none (all prior content preserved or renumbered).

Renumbered sections (Article III, content preserved):
  - III.2 "Data access from Python" → merged into new III.5 "Python — pgvector direct
    access"
  - III.3 "RAG indexing — rules" → III.6
  - III.4 "pgvector queries — two patterns" → III.7
  - III.5 "Modularity — Library First" → III.2
  - Article VI: former VI.1/VI.2/VI.3 → VI.2/VI.3/VI.4 (VI.1 is new, see above)

Explicitly NOT changed (decided during this amendment):
  - Vinted catalog category values remain the English descriptions (one-of-a-kind,
    jewelry, belt, clearance) rather than the raw French enum values from the
    alternate source document — kept as-is per explicit product owner decision.
  - Python↔pgvector driver reference kept as `psycopg3` (not `asyncpg`) — no request
    to change this implementation detail was made.

Templates requiring updates:
  - .specify/templates/plan-template.md — ✅ no change needed (generic Constitution
    Check gate, no brand/tenant-specific references)
  - .specify/templates/spec-template.md — ✅ no change needed (no brand/tenant-specific
    references)
  - .specify/templates/tasks-template.md — ✅ no change needed (no brand/tenant-specific
    references)
  - .specify/templates/commands/*.md — N/A (directory does not exist in this project)

Follow-up TODOs:
  - TODO(RATIFICATION_DATE_HISTORY): carried over from v4.0.1 — the true original
    ratification date of v1.0 (tracked outside this repo's Spec Kit workflow) remains
    unknown. Ratification date below continues to mark formal adoption into
    `.specify/memory/constitution.md`.
-->

# Constitution — Rockey
> Product: **Rockey** — Multi-tenant AI Customer Service Platform
> Version: 5.0.0 | Status: Immutable | Date: 2026-07-05
> v5 changes: Terminology standardized to retailer/tenant | Restored Multi-tenant isolation,
> State Machine, and general error-handling principles | Fixed `canal`→`channel` |
> Auto-refund thresholds & customer messages now sourced from per-retailer Drive config

This constitution defines the non-negotiable principles of the project.
**No exception is authorized without a formal update of this document.**

---

## Article 0 — Product Identity (Non-Negotiable)

### 0.1 Product name
- The product is called **Rockey**
- Rockey is a **B2B multi-tenant AI customer service platform**
- Rockey is sold to retailers (Vinted, Zara, Nike, Bull & Bear…) who deploy it to their customers

### 0.2 Visibility of the Rockey name
- **"Rockey" is NEVER visible to the retailer's end customer**
- "Rockey" appears only in: source code, internal metadata, B2B communication toward retailers
- The end customer only sees the **persona configured by the retailer** (first name, tone, colors)

### 0.3 Per-tenant persona model
Each retailer configures its own agent on top of Rockey:
```
Rockey (product)
  ├── Vinted     → agent "Léa"    — warm, vintage fashion, FR formal (vouvoiement)
  ├── Zara        → agent "Sofia"  — neutral, fashion, FR/EN/ES
  ├── Nike        → agent "Jordan" — dynamic, sport, EN informal (tutoiement)
  └── Bull & Bear → agent "Bruno"  — professional, finance, FR formal (vouvoiement)
```
- First name, tone, language, and formality are **configured per tenant** in `tenant_config`
- **No persona is hardcoded** in the code — everything comes from config

### 0.4 Demo retailer
- The POC's reference retailer is **Vinted** — a vintage & secondhand fashion store
- Vinted is powered by Rockey with the persona **"Léa"**

---

## Article I — Technical Stack (Non-Negotiable)

### I.1 Backend Gateway & Business Services
- **Language**: Java 21 (LTS) — no other JVM language accepted
- **Framework**: Spring Boot 3.x
- **API**: REST JSON only — no GraphQL, no SOAP in the POC

### I.2 AI Agent
- **Language**: Python 3.12
- **Web framework**: FastAPI
- **Orchestration**: LangGraph — explicit state machine
- **LLM**: Claude Sonnet 4.6 (Anthropic)
- **Embedding model**: `paraphrase-multilingual-MiniLM-L12-v2` (local, no external API)
- **Short-term memory**: Redis (TTL 30 min max per session)
- **Long-term memory**: PostgreSQL + pgvector

### I.3 Vector storage — pgvector ONLY
- **ChromaDB is forbidden** — pgvector is the only authorized vector store
- pgvector is installed via `CREATE EXTENSION vector` on the existing PostgreSQL
- **No additional service** — everything in the same PostgreSQL
- Vector dimension: **384** (paraphrase-multilingual-MiniLM-L12-v2)
- Mandatory index: **HNSW** (`vector_cosine_ops`) on all `embedding` columns
- Two vectorized tables: `rag_documents` (policy) + `articles` (catalog)

### I.4 Inter-Service Communication
- **Pattern**: synchronous REST HTTP/JSON — Kafka forbidden in the POC
- **LLM timeout**: 30 seconds — beyond that, automatic escalation
- **Java timeout**: 10 seconds — beyond that, circuit breaker
- **Internal auth**: `X-Internal-Token` header

### I.4b Channels — POC (Non-Negotiable)
Rockey supports 3 channels in the POC, each with its own dedicated Java adapter:

| Channel | Inbound protocol | Outbound protocol | Usage |
|---|---|---|---|
| **Web Widget** | WebSocket + REST fallback | JSON streaming | End customer on the retailer's site |
| **Email** | IMAP polling (2 min) | SMTP reply | End customer via email |
| **Slack** | — | Slack MCP | Retailer team escalation only |

**Channel rules:**
- The internal format `{ session_id, tenant_id, channel, message, client_id }` is **identical** across all channels
- The Python agent **does not know the channel** — it always receives the internal format
- Response formatting is adapted **by the Java adapter** based on the channel
- Slack is **an escalation channel only** — never a customer-facing channel
- WhatsApp and SMS are **out of POC scope** — planned for V1

**Response format per channel:**
- Web Widget → JSON streaming, no length limit
- Email → formatted HTML, return slip attached as PDF if applicable
- Slack → structured message with blocks (customer, order, reason, summary)

### I.5 MCPs authorized in the POC
- Custom Java MCP (business tools)
- Gmail MCP (email confirmation)
- Slack MCP (escalation)
- **Google Drive MCP** (RAG document sync — single source of truth for retailer docs)
- **No other MCP** without a constitution update

### I.6 Full persistence
```
PostgreSQL 16
  ├── rag_documents    (policy chunks + vectors)
  ├── articles         (product catalog + vectors)
  ├── orders           (orders — test seed)
  ├── dossiers         (support cases)
  ├── client_history   (long-term memory)
  └── tenant_config    (persona + drive_folder_id + channels)

Redis 7
  └── sessions         (current conversation state — TTL 30min)
```

### I.7 RAG data — single source: Google Drive

**Google Drive is the single source of truth for RAG documents.**
Local markdown files are forbidden in production — the local `rag-data/` folder
only exists for unit tests (mocks).

#### Principle
Each retailer has a **dedicated Google Drive folder** shared with the service account.
`rag_indexer.py` reads this folder via the **Google Drive MCP**, extracts text based
on the format, chunks, embeds, and indexes it into pgvector.

```
Google Drive — Folder "Vinted — SAV Docs"  (folder_id: configurable per tenant)
  ├── Return Policy.pdf                → rag_documents (type: policy)
  ├── Complaint Policy.pdf             → rag_documents (type: policy)
  ├── Customer Service FAQ.docx        → rag_documents (type: faq)
  ├── Product Catalog.xlsx             → rag_documents (type: catalogue)
  └── Agent Configuration.docx         → rag_documents (type: config)
```

#### Accepted formats from Google Drive
| Format | Extraction library | Typical usage |
|---|---|---|
| `.pdf` | `pymupdf` | Policies, terms of service, official docs |
| `.docx` | `mammoth` | FAQs, guides, procedures |
| `.xlsx` / Google Sheets | `openpyxl` | Catalogs, pricing, thresholds |
| Google Docs | Auto-export → text | Native Drive documents |
| Google Sheets | Auto-export → CSV | Data tables |

**Local `.md` files are forbidden in production.**
They are tolerated only in Python unit tests (mock fixtures).

#### Per-retailer Drive configuration
```yaml
# In database — tenant_config table
tenant_id: "vinted"
drive_folder_id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"  # Vinted Drive folder ID
drive_sync_mode: "auto"       # "auto" = webhook | "manual" = API-triggered
drive_sync_schedule: "0 2 * * *"  # Re-sync every night at 2am (cron)
```

#### Sync triggers
- **On startup**: if `rag_documents` is empty for this tenant → full sync
- **Drive webhook** (prod): change detected → re-sync of the modified file
- **Manual**: `POST /admin/rag/sync?tenant_id=vinted`
- **Scheduled**: cron every night at 2am (full safety re-sync)

---

## Article II — Demo Retailer: Vinted (powered by Rockey)

### II.1 Vinted is the POC's reference retailer
- All development, tests, and demo data use Vinted
- Vinted is powered by **Rockey** with the persona **"Léa"**
- Léa: warm tone, passionate about vintage fashion | Formal address (vouvoiement) | French
- The 3 active channels for Vinted: **Web Widget + Email + Slack escalation**

### II.2 Non-negotiable Vinted data
The following data is embedded in the PostgreSQL seed and RAG files:

**Vinted return policy:**
- Window: 21 days (30 days international)
- Auto refund: amount ≤ €80
- Manual review: €80 < amount ≤ €200
- Mandatory escalation: amount > €200
- Change-of-mind return fee: €3.90 deducted
- Free return if defective or non-compliant

**Non-returnable items:**
- One-of-a-kind pieces (red tag)
- Flash sale items (< 48h)
- Final clearance
- Jewelry (hygiene)
- Belts (hygiene)
- Personalized items

**Reference catalog (14 seed items):**
- VTG-001 to VTG-050 (dresses, jackets, coats, tops, pants, skirts, accessories)
- Prices from €19 to €265
- Categories: standard, premium, one-of-a-kind, jewelry, belt, clearance

### II.3 Multi-tenant — planned but not implemented in the POC
- Every request carries a `tenant_id` (Vinted = "vinted")
- The code is designed to be multi-tenant — never hardcode Vinted data in the logic
- Adding a new retailer =
  1. Create a Google Drive folder shared with the service account
  2. Drop the docs (PDF, DOCX, XLSX) into the folder
  3. Register the `drive_folder_id` in the database (`tenant_config`)
  4. Call `POST /admin/rag/sync?tenant_id=new_retailer`
  5. The agent is operational — zero code changes

### II.4 Vinted Drive folder (POC)
- **Folder ID**: configured via the `VINTED_DRIVE_FOLDER_ID` env var
- **Documents**: 5 files (return policy, complaints, FAQ, catalog, config)
- **Formats used**: PDF for policies, XLSX for the catalog, DOCX for the FAQ
- **Service account**: `GOOGLE_SERVICE_ACCOUNT_JSON` in `.env`

---

## Article III — Architecture & Design Patterns

### III.1 Separation of concerns (Non-Negotiable)
```
Java Gateway     →  Auth, routing, multi-tenant, channel adapters
Python Agent     →  Intelligence, state, RAG, decisions
Java Services    →  Business logic, eligibility, actions
PostgreSQL       →  Relational data + vectors (pgvector)
Redis            →  Session TTL
```
- **No business logic in the Gateway** — it routes, it does not act
- **No direct database calls from Python** — always through Java REST
- **No intelligence in Java** — Java executes, Python decides

### III.2 Modularity — Library First
- `rag_indexer.py`: standalone module before integration
- `rag_query.py`: standalone module
- `eligibility-checker`: Java lib before becoming an endpoint
- Any feature implemented directly with no abstraction is a violation

### III.3 Multi-tenant
- Every request carries a `tenant_id`
- RAG policy, thresholds, and tone of voice are isolated by `tenant_id`
- **No data from one retailer can leak to another** — strict isolation

### III.4 State Machine
- Agent states are **explicitly defined in LangGraph** — no implicit flow
- Each transition has an **explicit condition** and a **documented fallback**
- The current state is **persisted in Redis** at each transition
- **Maximum 3 reformulations** before automatic escalation

### III.5 Python — pgvector direct access
- **Relational data** (orders, dossiers) → via Java REST only
- **Vector data** (rag_documents, articles) → **direct pgvector access from Python**
- Python never runs SQL queries against relational tables directly
- Python accesses pgvector via `psycopg3` + `pgvector-python`

### III.6 RAG indexing — rules
- Indexing is triggered on startup if `rag_documents` is empty for this tenant
- Manual re-indexing: `docker exec python-agent python rag_indexer.py --tenant vinted`
- Chunk size: 500 characters max, split on line breaks
- Chunks < 50 characters are ignored
- Each chunk carries: `tenant_id`, `source`, `type`, `chunk_index`

### III.7 pgvector queries — two patterns
```python
# Pattern 1 — Policy RAG (pure similarity)
SELECT content, source FROM rag_documents
WHERE tenant_id = 'vinted'
ORDER BY embedding <=> $1 LIMIT 3;

# Pattern 2 — Article lookup (hybrid SQL)
SELECT id, nom, prix, retournable FROM articles
WHERE tenant_id = 'vinted'
  AND retournable = true
  AND prix <= $1
ORDER BY embedding <=> $2 LIMIT 5;
```

---

## Article IV — Security

### IV.1 Secrets
- Zero hardcoded secrets — blocking violation
- Everything in `.env` — never committed
- `.env.example` documents keys without values
- The Google service account JSON **must never appear in the code**
  → stored in `GOOGLE_SERVICE_ACCOUNT_JSON` (base64-encoded JSON content)

### IV.2 Authentication
- Customers → JWT (Spring Security)
- Internal services → `X-Internal-Token`
- Python pgvector connection → via the `DATABASE_URL` variable (never hardcoded)
- Google Drive MCP → service account with **read-only** access to retailer folders
- Drive folders are shared **only with the service account** — never public

### IV.3 Customer data
- Emails encrypted at rest in prod (out of POC scope, prepared for)
- Logs: never plaintext email, name, or order number
- Redis sessions: TTL mandatory

---

## Article V — Agent Guardrails

### V.1 Scope
- The agent handles only customer-service topics (return, complaint, refund, tracking)
- Any out-of-scope request → polite redirection — never ignored
- The agent can **never promise a refund** before technical verification
- **The agent NEVER mentions "Rockey", "AI", "algorithm", or "automated system"** — it responds under the retailer's persona name
- If a customer asks "what software do you use?" → neutral answer, never mention Rockey

### V.2 Mandatory identification
- No action without order number + email
- Maximum 2 attempts before escalation

### V.3 Automatic decision
- Decision based **only** on RAG policy + YAML thresholds — never LLM intuition
- Auto-refund thresholds are **defined in the retailer's Google Drive config** — not in the prompt
- Every decision is logged in the database with the reason and the applied rule

### V.4 Escalation
- Irreversible within the session
- Always triggers Slack MCP
- Cases: amount above threshold, unknown reason, +3 exchanges, service down, customer requests a human

---

## Article VI — Error Handling

### VI.1 General principle
- **Every external call** (LLM, Java, MCP) is wrapped in try/catch with a timeout
- **No raw technical error** is ever exposed to the customer — a normalized message is mandatory
- All errors are **structurally logged** (JSON) with session_id, tenant_id, timestamp

### VI.2 Circuit Breaker
- MAX_RETRIES = 2 on all external calls
- TIMEOUT_LLM = 30s | TIMEOUT_JAVA = 10s | TIMEOUT_MCP = 15s | TIMEOUT_PGVECTOR = 5s
- After failures → escalate, never an infinite loop

### VI.3 RAG fallback
- If pgvector times out → prompt using static YAML rules held in memory
- Alert log mandatory when fallback is activated

### VI.4 Normalized customer messages
- Each error type has a **customer message defined in the retailer's Google Drive config**
- Error messages are empathetic and actionable — never expose technical jargon to the customer
- Message always indicates the next step for the customer

---

## Article VII — Tests

### VII.1 POC test scope
- Java unit tests (eligibility, return, refund services): coverage > 70%
- Integration tests: full return + complaint flow (happy path + escalation), validated
  against the 5 spec.md scenarios with docker-compose
- Contract tests: each MCP tool verified with a Java mock
- Python tests: LLM mocks + Java mocks, never the real API
- UI and load tests are out of POC scope

### VII.2 TDD
- Java tests written before the code (red → green)
- Every Java endpoint: 1 happy path + 1 edge case minimum
- LangGraph tests use LLM mocks — never the real API in tests

---

## Article VIII — Deployment

### VIII.1 Docker Compose — 4 services (no more ChromaDB)
```yaml
services:
  java-gateway   # :8080
  python-agent   # :8000
  postgres       # :5432 — with pgvector
  redis          # :6379
```

### VIII.2 Required variables
```bash
# Core — the project won't start without these
ANTHROPIC_API_KEY               # Claude API
POSTGRES_PASSWORD               # PostgreSQL
DATABASE_URL                    # python-agent → pgvector
INTERNAL_SERVICE_TOKEN          # inter-service auth

# Google Drive — required for RAG in prod
GOOGLE_SERVICE_ACCOUNT_JSON     # base64 service account JSON
VINTED_DRIVE_FOLDER_ID          # Vinted Drive folder ID

# Email channel — Vinted
VINTED_EMAIL_IMAP               # e.g. imap.gmail.com:993
VINTED_EMAIL_USER               # sav@vinted.com
VINTED_EMAIL_PASSWORD           # Gmail App Password

# Optional — features disabled if absent
SLACK_MCP_TOKEN                 # Slack escalation
GMAIL_MCP_TOKEN                 # email confirmation
```

### VIII.3 Startup sequence
```
1. postgres starts + healthcheck
2. redis starts + healthcheck
3. java-gateway starts (Flyway migrations + SQL seed)
4. python-agent starts
   → checks GOOGLE_SERVICE_ACCOUNT_JSON is present
   → if rag_documents empty: Drive sync → extraction → embed → pgvector
   → if rag_documents already present: skip (re-sync via cron or webhook)
5. Agent ready — /health returns 200
```

### VIII.4 Degraded mode — Drive unavailable
- If Google Drive is unreachable on startup AND `rag_documents` is empty → **fatal error**, agent does not start
- If Google Drive is unreachable AND `rag_documents` already exists → **normal startup**, warning logged
- Re-sync is retried every 30 minutes if Drive is unavailable

---

## Article IX — Evolvability

### IX.1 Prepared but not implemented
- Kafka: async-compatible interfaces
- Multi-language: prompts templated with `{language}`
- Anti-fraud: database columns ready
- Claude Vision: `attachments[]` field in the LangGraph state
- New retailers: create Drive folder → share → register folder_id → auto sync
- Drive webhook: change detection → partial re-sync of the modified file (V1)

### IX.2 Out of POC scope
- Retailer admin dashboard
- Fine-tuning
- Analytics
- Cloud deployment
- Automated GDPR compliance

---

## Governance

### Amendment procedure
- Any change to this constitution requires an explicit proposal describing the
  change, its business or technical justification, and its impact on existing articles.
- Amendments touching Article 0 (product identity) or Article I (technical stack)
  require explicit Product Owner approval before merging, as these sections are marked
  **Non-Negotiable**.
- A section marked **Non-Negotiable** can only be changed via a new MAJOR version
  of this constitution.

### Versioning policy (MAJOR.MINOR.PATCH)
- **MAJOR**: removal or incompatible redefinition of a non-negotiable rule
  (e.g., product name change, tech stack change, channel policy change).
- **MINOR**: addition of an article, a section, or a material extension of an existing
  rule that doesn't break the existing one.
- **PATCH**: wording clarifications, typo fixes, non-semantic refinements that don't
  change expected behavior.

### Compliance review
- Every `/speckit-plan` run must validate its "Constitution Check" section against
  the articles above before moving to Phase 0, and again after Phase 1.
- Any deviation found in code review must be documented in the relevant plan or spec,
  with justification, before merging.
- Pull request reviews must check compliance with the Non-Negotiable articles
  (Article 0, Article I) first.

---

**Version**: 5.0.0 | **Ratified**: 2026-07-04 | **Last Amended**: 2026-07-04
