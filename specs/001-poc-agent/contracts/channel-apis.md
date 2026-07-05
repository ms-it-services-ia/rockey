# Contract: Channel-Facing APIs

These are the externally reachable surfaces of the Java Gateway. All three convert to/from
the unified internal format defined in `internal-message.md`.

## Web Widget

**WebSocket** (primary): `CONNECT /ws/chat/{tenant_id}`, then `SEND /app/chat/{tenant_id}`
with body:
```json
{ "message": "string" }
```
Server pushes to `SUBSCRIBE /topic/chat/{session_id}` with the agent's response (see
`internal-message.md` response shape, minus internal-only fields).

**REST fallback**: `POST /api/v1/chat`
- Headers: `X-Tenant-ID: <tenant_id>`
- Body: `{ "session_id": "string, optional — omit to start a new session", "message": "string" }`
- Response: `200 OK` with the same response shape as the WebSocket push.
- No length limit on the response (constitution I.4b).

## Email

Inbound: IMAP polling every 2 minutes against `TenantConfig.channel_email_imap`. Each unread
message becomes one internal-format request; `client_id` = the email `Message-ID`;
`session_id` is resolved/created per sender+subject thread.

Outbound: SMTP reply to the original sender.
- Format: HTML, using the retailer's branding.
- Subject: `Re: Your customer service request — Case #{case_id}`.
- Return label, if present in `attachments`, is attached as a PDF (constitution I.4b).

## Slack (escalation only — outbound, never inbound)

`POST` via Slack MCP to `TenantConfig.channel_slack_channel` when a case reaches
`ESCALATION`. Block Kit payload:

```json
{
  "blocks": [
    { "type": "header", "text": "Escalation — action required" },
    { "type": "section", "fields": [
      "*Customer:* {client_email}",
      "*Order:* {order_id}",
      "*Item:* {article_name} ({amount}€)",
      "*Channel:* {channel}",
      "*Escalation reason:* {escalation_reason}"
    ]},
    { "type": "section", "text": "*Summary:* {escalation_summary}" }
  ]
}
```

- MUST NOT include a reply/interaction affordance that lets a Slack user impersonate the
  customer-facing agent — Slack is read-only notification for the retailer's team
  (constitution I.4b: "never a customer-facing channel").
- If `SLACK_MCP_TOKEN` is absent, escalation still completes (ticket created, customer
  informed) but the Slack notification step is skipped with a warning log — it does not
  block or fail the escalation itself.
