# Contract: Unified Internal Message Format

Per constitution I.4b, every channel adapter (Web Widget, Email, Slack) converts its native
format into this single internal shape before handing off to the Python Agent. The agent
never branches on channel-specific fields beyond `channel` itself.

## Request: Gateway → Python Agent

```json
{
  "session_id": "string, required — stable per conversation, used as the Redis key",
  "tenant_id": "string, required — e.g. \"vinted\"",
  "channel": "string, required — one of: \"web\", \"email\"",
  "message": "string, required — the customer's free-text message",
  "client_id": "string, required — channel-specific correlation id (e.g. widget connection id, email Message-ID)"
}
```

- Slack is never an inbound channel for this message — it is escalation-outbound only (see
  `channel-apis.md`).
- `tenant_id` MUST match an existing `TenantConfig.tenant_id`; unknown tenants are rejected
  by the Gateway before reaching the agent (constitution III.3 — no cross-tenant leakage).

## Response: Python Agent → Gateway

```json
{
  "session_id": "string",
  "current_state": "string — LangGraph node name, see data-model.md",
  "reply": "string — the agent's natural-language response, channel-agnostic",
  "attachments": [
    { "type": "return_label", "url": "string" }
  ],
  "escalated": "boolean — true once the session has entered ESCALATION",
  "case_id": "string, nullable — the Dossier/Case id once one exists"
}
```

- The Gateway's channel adapter is solely responsible for turning `reply`/`attachments` into
  the channel's native format (JSON stream for the widget, HTML + PDF attachment for email).
- `attachments` is empty except when a return label has been generated (User Story 3 /
  User Story 6).
