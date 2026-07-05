# Implementation Plan: AI Customer Service Agent (Vinted POC)

**Branch**: `001-poc-agent` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-poc-agent/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Deliver the POC of **Rockey**'s conversational customer-service agent for the demo retailer
**Vinted** (persona **Léa**): identify the customer, classify their request (return vs.
complaint), decide autonomously against the retailer's own policy, and either resolve the
case or escalate it to a human with full context — consistently across the Web Widget,
Email, and Slack-escalation channels. Technical approach: a Java Gateway (Spring Boot)
handling auth/routing/channel adapters, a Python Agent (FastAPI + LangGraph + Claude Sonnet
4.6) owning the conversational state machine and RAG-based policy decisions, PostgreSQL +
pgvector for both relational and vector data, and Redis for short-lived session state — per
the technology choices already mandated in `.specify/memory/constitution.md` (v5.0.0).

## Technical Context

**Language/Version**: Java 21 (LTS) for the Gateway and business services; Python 3.12 for
the AI Agent — no other JVM or scripting language, per constitution I.1/I.2.

**Primary Dependencies**: Spring Boot 3.x (Java Gateway); FastAPI + LangGraph + Anthropic SDK
(Claude Sonnet 4.6) + `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`, local
embeddings) + `asyncpg`/`pgvector-python` for direct vector access (Python Agent); Google
Drive MCP, Slack MCP, Gmail MCP, and a custom Java MCP for business tools.

**Storage**: PostgreSQL 16 with the `pgvector` extension only (`rag_documents`, `articles`,
`orders`, `dossiers`, `client_history`, `tenant_config`) — ChromaDB is forbidden; Redis 7 for
session state (TTL 30 min).

**Testing**: JUnit + Spring Boot Test for Java services, written test-first (red → green),
coverage > 70%; pytest with LLM and Java mocks for the Python agent (never the real Claude
API in tests); contract tests for each MCP tool against a Java mock.

**Target Platform**: Linux containers via Docker Compose (4 services: `java-gateway`,
`python-agent`, `postgres`, `redis`) — no cloud deployment at POC.

**Project Type**: Multi-service backend (two cooperating backend services: Java Gateway +
business services, and a Python AI agent) with a thin embeddable JS widget snippet for the
Web Widget channel; no standalone frontend application.

**Performance Goals**: 90% of agent responses delivered in under 10 seconds (spec SC-006);
LLM calls timeout at 30s and Java calls at 10s before automatic escalation/circuit-breaking
(constitution I.4); at least 10 simultaneous sessions supported at POC.

**Constraints**: pgvector is the only vector store (no ChromaDB); inter-service calls are
synchronous REST/JSON only (no Kafka at POC); Python never queries relational tables
directly — only through Java REST (constitution III.5); maximum 3 reformulations and maximum
2 identification attempts before mandatory escalation.

**Scale/Scope**: 1 demo retailer (Vinted) at POC with ~14 seed catalog articles and 7 seed
orders; architecture designed multi-tenant (every request carries `tenant_id`) but only one
tenant is configured; 3 channels (Web Widget, Email, Slack for escalation only).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Requirement | Status |
|---|---|---|
| 0 (Product Identity) | Agent never reveals "Rockey", "AI", "algorithm", or "automated system"; responds only as the retailer's persona | PASS — FR-013 |
| I (Tech Stack) | Java 21/Spring Boot 3, Python 3.12/FastAPI/LangGraph, Claude Sonnet 4.6, pgvector-only with HNSW index, sync REST/JSON, no Kafka | PASS — Technical Context above matches exactly |
| I.4b (Channels) | Web Widget + Email + Slack (escalation-only), identical internal format across channels | PASS — FR-011, User Story 7 |
| III.1 (Separation of concerns) | No business logic in the Gateway; no direct DB calls from Python; no intelligence in Java | PASS — Java Gateway routes only, Python owns decisions, Java services execute actions |
| III.3 (Multi-tenant) | No data from one retailer can leak to another | PASS — FR-014, all data scoped by `tenant_id` |
| III.4 (State Machine) | Explicit LangGraph states, transitions persisted in Redis, max 3 reformulations before escalation | PASS — carried into Phase 1 state-machine design |
| III.5 (pgvector access) | Vector data accessed directly from Python; relational data only via Java REST | PASS |
| V (Agent Guardrails) | Mandatory identification (max 2 attempts), decision from policy not LLM intuition, escalation irreversible | PASS — FR-002, FR-005, FR-006, FR-009 |
| VI (Error Handling) | Every external call wrapped with timeout; normalized customer messages; RAG fallback to static rules | Carried forward to Phase 1 design (data-model.md / quickstart.md validation) |
| VII (Tests) | TDD for Java services, coverage > 70%, contract tests per MCP tool | Carried forward to `tasks.md` (Phase 2, not created by this command) |

No violations identified. Complexity Tracking table below is not needed.

**Post-Phase 1 re-check**: `data-model.md` and `contracts/` were reviewed against the same
table above after design. No new violations introduced — in particular, `contracts/mcp-tools.md`'s
failure contract enforces VI.1 (no raw technical error ever surfaces; every technical failure
routes to `ESCALATION`), and `contracts/channel-apis.md` keeps Slack strictly outbound/escalation-only
per I.4b. Gate remains PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-poc-agent/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
rockey/
├── docker-compose.yml
├── .env.example
│
├── tests/fixtures/vinted/           # Mock RAG files for unit tests ONLY (no live Drive in tests)
│   ├── return-policy.pdf
│   ├── faq.docx
│   └── product-catalog.xlsx
│
├── java-gateway/                    # Java Gateway + Business Services
│   └── src/main/java/com/rockey/
│       ├── gateway/
│       │   ├── controller/          # WebChatController, EmailController, AdminController
│       │   ├── adapter/             # WebChatAdapter, EmailAdapter
│       │   ├── filter/               # InternalTokenFilter
│       │   └── dto/                  # InternalMessage, AgentResponse
│       ├── order/                    # OrderService, OrderRepository
│       ├── eligibility/              # EligibilityService (standalone lib), PolicyLoader
│       ├── returns/                  # ReturnService (standalone lib), ReturnLabelGenerator
│       ├── refunds/                  # RefundService (standalone lib)
│       ├── tickets/                  # TicketService
│       └── config/                   # SecurityConfig
│   └── src/test/java/com/rockey/     # JUnit + Spring Boot Test, TDD (red -> green)
│
└── python-agent/                    # Python AI Agent
    └── src/
        ├── main.py                   # FastAPI app + startup RAG-sync check
        ├── agent/
        │   ├── graph.py               # LangGraph state machine
        │   ├── states/                # greeting, identification, qualification, return_flow,
        │   │                          # complaint_flow, verification, decision, auto_action,
        │   │                          # escalation, confirmation
        │   ├── tools/                 # MCP tools -> Java REST (check_order, verify_eligibility,
        │   │                          # create_return_label, trigger_refund, escalate_to_human)
        │   ├── memory/                # session_store.py (Redis), history_store.py (via Java)
        │   ├── rag/                   # rag_indexer.py (Drive -> pgvector), rag_query.py
        │   ├── integrations/          # slack_notifier.py (Slack MCP, called directly, like Drive MCP)
        │   └── prompts/               # system_prompt.py (templated, no retailer hardcoded)
        ├── config/settings.py         # Pydantic BaseSettings
        └── tests/                     # pytest, LLM + Java mocks, contract tests per MCP tool
```

**Structure Decision**: Two cooperating backend services (per constitution III.1's mandatory
separation of concerns) rather than a single monolith or a frontend+backend split: the Java
Gateway owns auth/routing/channel adapters/business actions, the Python Agent owns
conversational intelligence and RAG. There is no dedicated frontend project — the Web Widget
channel is served by a thin embeddable JS snippet hosted by the Java Gateway, not a separate
application. MCP integrations (Google Drive, Slack) are called directly by the Python Agent
rather than proxied through Java — the Java Gateway is never involved in the Slack
escalation notification, consistent with how `rag_indexer.py` already calls the Google
Drive MCP directly.

## Complexity Tracking

*No constitution violations were identified — this section is not needed.*
