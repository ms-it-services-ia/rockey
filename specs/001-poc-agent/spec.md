# Feature Specification: AI Customer Service Agent (Vinted POC)

**Feature Branch**: `001-poc-agent`

**Created**: 2026-07-05

**Status**: Draft

**Input**: User description: "remplace tout ce qui est vintage par vinted" (applied while
transcribing the reference functional specification for Rockey's POC customer-service agent
into this repository)

**Scope note**: This feature covers the full POC customer-service agent — not just a naming
change. The demo retailer is **Vinted** (persona **Léa**), consistent with
`.specify/memory/constitution.md` v5.0.0. Everywhere the retailer's proper name appears it
reads "Vinted"; the generic adjective "vintage" (clothing style) is left untouched.

## User Scenarios & Testing *(mandatory)*

**In scope for this POC**: product return (return initiation + label generation), quality
complaint / defective item, automatic decision based on the retailer's policy (sourced from
Google Drive per the constitution), escalation to a human for complex cases, on the Web
Widget, Email, and Slack (escalation-only) channels, for one demo retailer (Vinted / agent
Léa).

**Out of scope for this POC**: product exchange, legal disputes, a retailer configuration
dashboard, WhatsApp/SMS channels, attachments or product photos, analytics/reporting, and
GDPR/anonymization tooling.

<!--
  User stories are prioritized as independently testable journeys.
  P1 stories form the minimum safe, viable loop: a customer can identify themselves, state
  their request, get a return processed, and be safely escalated when the agent can't help.
-->

### User Story 1 - Greeting and Identification (Priority: P1)

As a customer contacting customer service, I want to be greeted by the agent and be able to
identify myself, so that I can start processing my request without having to look for a
phone number or wait for a human.

**Why this priority**: Nothing else in the flow can happen safely without identification —
per the constitution's guardrails, no action may be taken without a verified order number
and email. This is the entry point for every other story.

**Independent Test**: Start a new session on any channel and provide an order number and
email; confirm the agent introduces itself under the retailer's persona and either confirms
the order or asks for correction.

**Acceptance Scenarios**:

1. **Given** a new conversation, **When** the customer sends their first message, **Then**
   the agent introduces itself with a first name and the retailer's name.
2. **Given** the agent has introduced itself, **When** it responds again, **Then** it asks
   for the order number and the customer's email address.
3. **Given** a valid order number and matching email, **When** the agent looks up the order,
   **Then** it confirms the customer's first name and the item concerned.
4. **Given** an order number that isn't found, **When** the customer is told, **Then** the
   agent offers to re-verify the number, up to 2 attempts total.
5. **Given** 2 failed identification attempts, **When** the second failure is confirmed,
   **Then** the agent offers to transfer the customer to a human advisor.

**Edge Cases**:

- Customer provides an order number belonging to a different retailer → agent returns an
  adapted error message, not a generic "not found".
- Customer cannot find their order number → agent explains where to find it (e.g. the
  confirmation email).
- Customer tries to skip identification and jump to their request → agent holds the step and
  does not process the request until identification succeeds.

---

### User Story 2 - Request Qualification (Priority: P1)

As an identified customer, I want to explain my request in natural language, so that the
agent understands whether I want a return or a complaint, without filling out a form.

**Why this priority**: Routing to the correct flow (return vs. complaint vs. out-of-scope) is
required before any downstream processing can happen; it's the second mandatory step of every
session.

**Independent Test**: After identification, send a free-text message describing a return or
a complaint; confirm the agent classifies intent correctly and confirms its understanding
before moving on.

**Acceptance Scenarios**:

1. **Given** an identified customer describes their issue, **When** the agent parses the
   message, **Then** it classifies the intent as one of: product return, quality complaint,
   or other.
2. **Given** an ambiguous message, **When** intent cannot be determined, **Then** the agent
   asks a clarifying question, at most twice.
3. **Given** a request outside customer-service scope (e.g. a product question, a promotion
   inquiry), **When** the agent detects this, **Then** it signals the limitation and redirects
   the customer politely, without attempting to process it.
4. **Given** intent has been classified, **When** the agent is ready to proceed, **Then** it
   confirms its understanding with the customer before moving to the next step.

**Edge Cases**:

- Customer mixes a return and a complaint in the same message → agent asks for clarification
  and handles one case at a time.
- Aggressive or impatient customer → agent stays calm and empathetic, and offers escalation
  if needed.
- Out-of-scope request → redirected without being processed as a return or complaint.

---

### User Story 3 - Product Return Processing (Priority: P1)

As a customer wishing to return an item, I want the agent to verify my eligibility and
automatically initiate the return if I'm eligible, so that I receive my return label without
contacting a human.

**Why this priority**: This is the primary value delivered by the POC — the single most
common, standardizable request the agent must be able to fully resolve on its own.

**Independent Test**: Submit a return request for an eligible item within the policy window;
confirm a return label is generated and sent without human involvement.

**Acceptance Scenarios**:

1. **Given** a return request, **When** the agent processes it, **Then** it collects the
   return reason (non-conforming item, change of mind, wrong size, other).
2. **Given** a return reason, **When** the agent checks eligibility, **Then** it verifies
   against the retailer's policy (delay, item condition, product type).
3. **Given** an eligible return, **When** eligibility is confirmed, **Then** the agent
   generates a return label and sends it on the channel used.
4. **Given** an ineligible return, **When** eligibility fails, **Then** the agent clearly
   explains the refusal reason and offers escalation if the customer wants it.
5. **Given** a completed return decision, **When** the flow ends, **Then** the customer
   receives a confirmation summarizing what was decided.

**Vinted demo policy** (used for the POC's eligibility checks):
- Return window: 30 days from receipt (21 days domestic / 30 days international, per the
  retailer's configured policy)
- Condition: unworn, unwashed, tags present
- Exclusions: personalized items, final-clearance items
- Auto-refund: amount ≤ €80
- Manual verification: €80 < amount ≤ €200
- Mandatory escalation: amount > €200

**Edge Cases**:

- Return window exceeded → clear refusal plus an escalation offer.
- Item on final clearance → refusal with the policy reason explained.
- Amount above the auto-refund threshold → escalation to a human with full context passed
  along.
- Customer disputes the decision → escalation offered; the agent never negotiates the
  outcome itself.

---

### User Story 4 - Escalation to Human (Priority: P1)

As a customer whose request exceeds the agent's automatic capabilities, I want to be
transferred to a human advisor with full context, so that I don't have to explain everything
again.

**Why this priority**: Escalation is the safety net for every other story — return,
complaint, and identification flows all depend on it to fail safely rather than getting
stuck or giving a wrong answer.

**Independent Test**: Trigger any escalation condition (e.g. amount above threshold) and
confirm the human advisor receives a complete case summary and the customer gets a
confirmation with an indicative response time.

**Acceptance Scenarios**:

1. **Given** an escalation is triggered, **When** the agent hands off, **Then** it informs
   the customer with an empathetic message.
2. **Given** a handed-off case, **When** the human advisor opens it, **Then** they see a
   complete summary: customer, order, reason, exchange history, and the decision the agent
   attempted.
3. **Given** an escalation has been confirmed, **When** the customer is told, **Then** they
   receive an indicative response time.
4. **Given** any of the following conditions, **When** they occur, **Then** escalation is
   triggered automatically: amount above the auto-refund threshold, an unrecognized
   complaint/return reason, more than 3 exchanges without progress, the technical service is
   unavailable, or the customer explicitly asks for a human.

**Edge Cases**:

- Escalation triggered outside business hours → customer gets a waiting message with an
  expected response time.
- Customer refuses escalation and demands an immediate answer → agent explains its limits
  and still escalates if the case requires it.
- Case is escalated twice in the same session → no duplicate ticket; the customer is told
  the case is already being handled.

---

### User Story 5 - Quality Complaint Processing (Priority: P2)

As a customer who received a defective or non-conforming item, I want to report the issue
and get a resolution quickly, so that I don't have to fight with customer service to
exercise my rights.

**Why this priority**: Second most common request after standard returns; extends the
agent's coverage but the platform still delivers value with only returns (Story 3) and
escalation (Story 4) working.

**Independent Test**: Submit a complaint about a defective item; confirm the agent collects
the reason and description, determines eligibility, and either resolves it or escalates with
a complete summary.

**Acceptance Scenarios**:

1. **Given** a complaint, **When** the agent processes it, **Then** it collects the reason
   (quality defect, item damaged on delivery, non-conformity, wrong size delivered).
2. **Given** a reason has been collected, **When** the agent continues, **Then** it asks for
   a free-text description of the problem.
3. **Given** a description has been collected, **When** the agent evaluates it, **Then** it
   determines whether the complaint is eligible for a refund or a free return.
4. **Given** an eligible complaint, **When** eligibility is confirmed, **Then** the agent
   initiates a free return plus refund or exchange, based on availability.
5. **Given** an ineligible or complex complaint, **When** the agent cannot resolve it,
   **Then** it escalates with a complete summary for the human advisor.
6. **Given** a complaint has been processed, **When** the flow ends, **Then** the customer
   receives a confirmation with next steps.

**Edge Cases**:

- Complaint filed after the standard return window → legal warranty rules apply →
  escalation with a note explaining why.
- Vague defect description → agent asks up to 2 clarifying questions.
- Repeated complaint about the same item → automatic escalation, with the item's complaint
  history attached.

---

### User Story 6 - Confirmation and Closure (Priority: P2)

As a customer whose request has been processed, I want a clear confirmation of what was
done, so that I know exactly what happens next and by when.

**Why this priority**: Closes the loop on every other story; without it customers are left
uncertain even when the agent resolved their request correctly.

**Independent Test**: Complete any return or complaint flow and confirm the customer
receives a structured summary with a case number, the action taken, and the next step.

**Acceptance Scenarios**:

1. **Given** a processed request, **When** it concludes, **Then** the customer receives a
   summary on the channel they used (widget or email).
2. **Given** a summary is sent, **When** the customer reads it, **Then** it contains: case
   number, action taken, processing time, and next step.
3. **Given** a return label was generated, **When** the confirmation is sent, **Then** the
   label is attached or sent by email.
4. **Given** the summary has been delivered, **When** the agent finishes, **Then** it offers
   additional help before closing the session.
5. **Given** a session ends, **When** it's recorded, **Then** it is marked as resolved or
   escalated.

---

### User Story 7 - Multi-channel Consistency (Priority: P3)

As a customer contacting the retailer through different channels, I want the same level of
service whether I use the web widget or email, so that I'm not penalized for my preferred
contact channel.

**Why this priority**: Broadens reach once the core agent behavior (Stories 1-6) already
works reliably on a single channel; channel parity is valuable but not required for the
agent to deliver its core value.

**Independent Test**: Run the same return request on the Web Widget and via Email; confirm
identical decisions and behavior, with only response formatting differing.

**Acceptance Scenarios**:

1. **Given** the agent is deployed, **When** a customer reaches out, **Then** it is
   accessible via both the Web Widget and Email.
2. **Given** the same request submitted on two different channels, **When** the agent
   processes each, **Then** its behavior and decisions are identical.
3. **Given** a channel's characteristics, **When** the agent responds, **Then** the response
   format adapts accordingly (shorter on the widget, more detailed by email).
4. **Given** a customer returns within 30 minutes of an interrupted session, **When** they
   reconnect on the same channel, **Then** the session resumes rather than restarting.

**Edge Cases**:

- Customer switches channels mid-request → treated as a new session; no cross-channel
  continuity at POC.
- A channel becomes unavailable → customer sees an error message with an alternative
  channel suggested.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST greet every new customer under the retailer's configured
  persona (first name, tone) before requesting any information.
- **FR-002**: The agent MUST require an order number and a matching email before taking any
  action on a customer's behalf, with a maximum of 2 identification attempts before
  escalating.
- **FR-003**: The agent MUST classify each identified customer's request as one of: product
  return, quality complaint, or out-of-scope, asking at most 2 clarifying questions when
  intent is ambiguous.
- **FR-004**: The agent MUST redirect out-of-scope requests politely without attempting to
  process them as a return or complaint.
- **FR-005**: The agent MUST evaluate return eligibility strictly against the retailer's
  configured policy (return window, item condition, product type, exclusions) — never on
  its own judgment.
- **FR-006**: The agent MUST auto-approve returns/refunds at or below the retailer's
  auto-refund threshold, and MUST escalate any case above it to a human.
- **FR-007**: The agent MUST evaluate quality complaints for refund/free-return eligibility
  and either resolve them automatically or escalate with a complete case summary.
- **FR-008**: The agent MUST trigger escalation automatically when any of the following
  occurs: amount exceeds the auto-refund threshold, the reason is unrecognized, more than 3
  exchanges pass without progress, the technical service is unavailable, or the customer
  explicitly requests a human.
- **FR-009**: Once triggered, an escalation MUST be irreversible for the remainder of the
  session, and MUST hand the human advisor a complete summary (customer, order, reason,
  exchange history, attempted decision).
- **FR-010**: The agent MUST send the customer a closing confirmation containing a case
  number, the action taken, processing time, and the next step, for every resolved or
  escalated request.
- **FR-011**: The agent MUST behave identically across the Web Widget and Email channels,
  varying only response formatting (length/structure) to fit the channel.
- **FR-012**: The agent MUST resume an interrupted session if the customer returns on the
  same channel within 30 minutes, without asking the customer to re-identify.
- **FR-013**: The agent MUST NOT reveal that it is an AI, "Rockey", an algorithm, or an
  automated system to the customer — it responds only as the retailer's named persona.
- **FR-014**: All customer-facing data (order/return/complaint decisions) MUST be scoped to
  the demo retailer "Vinted" (tenant `vinted`) and MUST NOT be readable by or attributed to
  any other retailer.

### Key Entities

- **Customer**: The end user contacting the retailer; identified by order number + email.
  Not persisted beyond what's needed for the session and case history.
- **Order**: A past purchase belonging to a customer, referencing exactly one article, an
  amount, and delivery status; used to verify identification and return/complaint eligibility.
- **Article**: A catalog item (e.g. a Vinted product) with a price and a returnability flag
  (some categories — final clearance, personalized items — are never returnable).
- **Case (return or complaint)**: A single customer request being processed; tracks type,
  reason, decision (accepted/refused/escalated), the channel used, and the applied policy
  rule.
- **Escalation**: The irreversible hand-off of a case to a human advisor, carrying the full
  case summary and exchange history.
- **Retailer (tenant)**: The business the agent is configured for. For this POC, the sole
  retailer is **Vinted**, with persona **Léa** (warm, formal, French).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 70% of return/complaint requests are resolved without human
  involvement.
- **SC-002**: The average return/complaint session (identification through confirmation)
  takes under 5 minutes.
- **SC-003**: Fewer than 15% of escalations are for cases that could have been resolved
  automatically under the retailer's policy.
- **SC-004**: All 5 POC test scenarios (below) complete end-to-end without the agent getting
  stuck or giving an incorrect decision.
- **SC-005**: 100% of documented edge cases across all user stories are covered by a test.
- **SC-006**: 90% of agent responses are delivered in under 10 seconds.

### POC Test Scenarios

1. **Eligible return (happy path)** — Customer returns an item within the policy window in
   original condition, amount below the auto-refund threshold → return label generated and
   refund triggered automatically.
2. **Return past the deadline (edge case)** — Customer requests a return well past the
   policy window → clear refusal with explanation; escalation offered.
3. **Defective item complaint above threshold** — Customer reports a defective item priced
   above the auto-refund threshold → complaint qualified, then escalated with a complete
   summary due to amount.
4. **Non-returnable item** — Customer requests a return for an item excluded by policy
   (e.g. a final-clearance or personalized item) → clear refusal citing the specific policy
   exclusion.
5. **Failed identification** — Customer provides an incorrect order number twice → escalation
   offered after the second failure.

## Assumptions

- The demo/reference retailer is **Vinted** with persona **Léa** (warm, formal, French),
  matching `.specify/memory/constitution.md` v5.0.0; no other retailer is in scope for this
  POC.
- The retailer's return/complaint policy (thresholds, exclusions, return window) is sourced
  from the retailer's configuration rather than hardcoded in the agent's logic, per the
  constitution's Google-Drive-as-source-of-truth principle.
- Product exchange, legal disputes, a retailer configuration dashboard, WhatsApp/SMS,
  attachments/photos, analytics/reporting, and GDPR/anonymization tooling are explicitly out
  of scope for this POC.
- Slack is used only as an internal escalation channel for the retailer's team — it is never
  customer-facing.
- Cross-channel session continuity (e.g. starting on Email and continuing on Web Widget) is
  out of scope for the POC; only same-channel resumption within 30 minutes is required.
- No live production system or real customer data exists yet — all identification, orders,
  and articles referenced in test scenarios are seed/test data.
