# Phase 0 Research: AI Customer Service Agent (Vinted POC)

All technology choices for this feature are already mandated by
`.specify/memory/constitution.md` (v5.0.0), so the Technical Context in `plan.md` has no
open `NEEDS CLARIFICATION` markers. This document instead records the concrete design
decisions needed to turn those constraints into an implementable plan, and the alternatives
considered for each.

## 1. Vector storage

- **Decision**: PostgreSQL 16 with the `pgvector` extension, HNSW index
  (`vector_cosine_ops`, `m=16`, `ef_construction=64`) on every `embedding` column.
- **Rationale**: Mandated by constitution I.3 — no additional service to operate at POC,
  single database for relational + vector data.
- **Alternatives considered**: ChromaDB (explicitly forbidden by the constitution); a
  managed vector DB (rejected — adds an external dependency the POC doesn't need).

## 2. Embeddings and LLM

- **Decision**: `paraphrase-multilingual-MiniLM-L12-v2` (local, 384-dim) for embeddings;
  Claude Sonnet 4.6 for generation and intent/eligibility reasoning.
- **Rationale**: Mandated by constitution I.2. Local embeddings avoid an external API call
  and its latency/cost for every RAG lookup; Claude Sonnet 4.6 is the only LLM authorized.
- **Alternatives considered**: OpenAI embeddings/hosted embedding API (rejected — external
  dependency, not authorized by the constitution).

## 3. Conversational orchestration

- **Decision**: LangGraph with explicit states (greeting → identification → qualification →
  return_flow / complaint_flow → verification → decision → auto_action / escalation →
  confirmation), current state persisted in Redis at every transition.
- **Rationale**: Constitution III.4 requires an explicit state machine with no implicit
  flow, and state persisted in Redis so a session can resume mid-flow.
- **Alternatives considered**: An implicit/prompt-only agent loop (rejected — constitution
  forbids implicit flow and it makes the "max 3 reformulations" and "max 2 identification
  attempts" guardrails hard to enforce deterministically).

## 4. Intent classification (return vs. complaint vs. other)

- **Decision**: LLM-based classification (Claude, given the retailer's policy context),
  with a confidence check that triggers at most 2 clarifying questions before defaulting to
  an "other/out-of-scope" redirect (User Story 2).
- **Rationale**: Free-text customer input needs semantic understanding, not just keyword
  matching, per User Story 2's "natural language, no form" requirement.
- **Alternatives considered**: Rule-based keyword matching (rejected — too brittle against
  natural language and mixed-intent messages, an edge case explicitly called out in the
  spec); a dedicated ML intent-classifier service (rejected — adds a component outside the
  constitution's approved stack for no POC-stage benefit).

## 5. Session resumption within 30 minutes

- **Decision**: Redis session keyed by `(tenant_id, channel, client_identifier)` with a
  sliding 30-minute TTL, refreshed on each turn; resuming re-hydrates the LangGraph state
  rather than restarting from greeting.
- **Rationale**: Matches constitution I.2's "Redis TTL 30 min max per session" and directly
  satisfies User Story 7's same-channel resumption acceptance scenario.
- **Alternatives considered**: No resumption, always restart (rejected — fails User Story 7
  acceptance scenario 4); a resumption token requiring customer action (rejected — adds
  friction the spec doesn't ask for).

## 6. RAG chunking and indexing

- **Decision**: Adopt constitution III.6 as-is — startup sync when `rag_documents` is empty
  for the tenant, 500-character max chunks split on line breaks, chunks under 50 characters
  discarded, each chunk tagged with `tenant_id`/`source`/`type`/`chunk_index`.
- **Rationale**: Already fully specified by the constitution; no alternative evaluated.

## 7. RAG fallback on pgvector timeout

- **Decision**: A static, in-memory YAML mirror of the retailer's key policy thresholds,
  loaded at Python Agent startup, used only when a pgvector query exceeds the 5s timeout;
  every use is alert-logged.
- **Rationale**: Constitution VI.3 mandates exactly this fallback so a transient pgvector
  slowdown degrades gracefully instead of failing the whole request.
- **Alternatives considered**: Escalate immediately on any pgvector timeout (rejected — the
  constitution requires the static fallback to be tried first; escalation still happens
  afterward if the fallback can't produce a confident decision).

## 8. Circuit breaker granularity

- **Decision**: One circuit breaker per external dependency type (LLM, Java, MCP,
  pgvector), each with `MAX_RETRIES=2` and its own timeout
  (30s / 10s / 15s / 5s respectively).
- **Rationale**: Constitution VI.2 specifies per-dependency timeouts; a single global
  breaker would over-trip on an unrelated dependency's failure.
- **Alternatives considered**: One global circuit breaker for all external calls (rejected
  — would escalate every session whenever any single dependency has a blip).

## 9. Escalation delivery format

- **Decision**: Slack Block Kit structured message containing customer, order, item and
  amount, channel, and escalation reason/summary, sent via the Slack MCP.
- **Rationale**: Constitution I.4b specifies "structured message with blocks (customer,
  order, reason, summary)" for the Slack channel; this is the only channel Slack is used on
  (escalation, never customer-facing).
- **Alternatives considered**: Plain-text Slack message (rejected — harder for the
  retailer's SAV manager to scan quickly, and contradicts the constitution's explicit
  format).

## 10. Return label generation

- **Decision**: The Java `ReturnService` generates a return label synchronously as part of
  handling `POST /internal/returns`; for the Email channel the label is attached as a PDF,
  for the Web Widget it's returned as a link in the JSON response.
- **Rationale**: Constitution I.4 mandates synchronous REST between services (Kafka
  forbidden at POC), and POC scale (10+ concurrent sessions) doesn't need async processing.
- **Alternatives considered**: Asynchronous label generation via a queue (rejected — Kafka
  is explicitly forbidden at POC scale, and label generation is fast enough to stay within
  the 10s Java timeout).
