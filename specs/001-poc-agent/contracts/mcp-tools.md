# Contract: MCP Tools (Python Agent → Java internal REST)

Each tool is invoked by the LangGraph agent and calls the corresponding Java internal
endpoint (`X-Internal-Token` authenticated, per constitution IV.2). Every tool call is
wrapped with the Java timeout (10s) and circuit breaker (`MAX_RETRIES=2`) from constitution
VI.2; on exhaustion the calling state transitions to `ESCALATION`.

| Tool | Input | Output | Java endpoint |
|---|---|---|---|
| `check_order` | `order_id`, `email`, `tenant_id` | `order_data`, `article_id`, or `not_found` | `GET /internal/orders/{id}` |
| `verify_eligibility` | `order_id`, `reason`, `article_data`, `tenant_id` | `eligible` (bool), `reason`, `applied_rule` | `POST /internal/eligibility/check` |
| `create_return_label` | `order_id`, `reason`, `tenant_id` | `label_url`, `return_id` | `POST /internal/returns` |
| `trigger_refund` | `order_id`, `amount`, `tenant_id` | `refund_id`, `delay` | `POST /internal/refunds` |
| `escalate_to_human` | `order_id`, `reason`, `summary`, `tenant_id` | `ticket_id`, `delay` | `POST /internal/tickets` |

## Notes per tool

- **`check_order`**: `not_found` MUST NOT distinguish "wrong tenant" from "wrong number" in
  its message to the customer — both surface as a generic "order not found" per the
  identification edge cases in spec User Story 1 (avoids leaking cross-tenant existence).
- **`verify_eligibility`**: `applied_rule` MUST always be populated when `eligible` is
  determined, so the Dossier/Case can be traced back to the specific policy rule
  (constitution V.3 — every decision traced with reason and applied rule). Eligibility is
  computed from the retailer's Drive-sourced policy (via `verify_eligibility`'s server-side
  RAG lookup), never from LLM judgment.
- **`create_return_label`** / **`trigger_refund`**: only called after `verify_eligibility`
  returns `eligible: true` and the amount is at/below the auto-refund threshold; amounts
  above threshold instead call `escalate_to_human`.
- **`escalate_to_human`**: MUST always trigger the Slack MCP notification as a side effect
  (constitution V.4 — escalation always triggers Slack) — sent directly from the Python
  Agent via the Slack MCP; the Java Gateway is never involved in the Slack call, the same
  way `rag_indexer.py` calls the Google Drive MCP directly rather than through Java.
  `ticket_id` is returned so the agent can reference it in the customer-facing confirmation
  (User Story 6).

## Failure contract

Every tool call MUST surface one of exactly three outcomes to the calling LangGraph node:
`success(data)`, `business_failure(reason)` (e.g. `not_found`, `not_eligible` — a normal,
expected outcome the agent should handle conversationally), or `technical_failure` (timeout,
5xx, connection error — always routes to `ESCALATION`, never surfaced as a raw error to the
customer, per constitution VI.1).
