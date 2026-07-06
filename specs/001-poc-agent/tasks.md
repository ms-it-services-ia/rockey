---

description: "Task list template for feature implementation"
---

# Tasks: AI Customer Service Agent (Vinted POC)

**Input**: Design documents from `/specs/001-poc-agent/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution VII mandates TDD for Java services (coverage > 70%,
written before code) and contract tests for every MCP tool, so test tasks are generated
alongside implementation, not treated as optional here.

**Organization**: Tasks are grouped by user story (from spec.md, in priority order) to
enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US7, per spec.md)
- Paths follow plan.md's two-service structure: `java-gateway/` and `python-agent/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create repository skeleton per plan.md: `java-gateway/`, `python-agent/`, `tests/fixtures/vinted/`, `docker-compose.yml`, `.env.example`
- [X] T002 [P] Initialize Java 21 / Spring Boot 3 project in `java-gateway/` (build file, `com.rockey` package layout per plan.md §Project Structure)
- [X] T003 [P] Initialize Python 3.12 / FastAPI project in `python-agent/src/` with dependencies: `fastapi`, `langgraph`, `anthropic`, `sentence-transformers`, `asyncpg`, `pgvector`, `pydantic-settings`
- [X] T004 [P] Configure Java linting/formatting (Checkstyle/Spotless) in `java-gateway/`
- [X] T005 [P] Configure Python linting/formatting (ruff/black) in `python-agent/`
- [X] T006 Write `docker-compose.yml` with the 4 services (`java-gateway`, `python-agent`, `postgres`, `redis`) per plan.md §Project Structure and constitution VIII.1
- [X] T007 [P] Write `.env.example` with every variable from constitution VIII.2 (`ANTHROPIC_API_KEY`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `INTERNAL_SERVICE_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `VINTED_DRIVE_FOLDER_ID`, `VINTED_EMAIL_IMAP/USER/PASSWORD`, `SLACK_MCP_TOKEN`, `GMAIL_MCP_TOKEN`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Create Flyway migration for `tenant_config`, `rag_documents`, `articles`, `orders`, `dossiers`, `client_history` in `java-gateway/src/main/resources/db/migration/` per data-model.md
- [X] T009 Enable `pgvector` and add HNSW indexes (`vector_cosine_ops`, `m=16`, `ef_construction=64`) on `rag_documents.embedding` and `articles.embedding` in the same migration, per research.md §1
- [X] T010 [P] Seed the `tenant_config` row for tenant `vinted` (persona Léa, channels, `drive_folder_id`) in `java-gateway/src/main/resources/db/migration/`
- [X] T011 [P] Seed test `articles` and `orders` data (VTG-001..VTG-050, CMD-2026-00001..7) per constitution II.2, in the same migration path
- [X] T012 Implement `InternalTokenFilter` (`X-Internal-Token` auth) in `java-gateway/src/main/java/com/rockey/gateway/filter/InternalTokenFilter.java`
- [X] T013 [P] Implement `InternalMessage`/`AgentResponse` DTOs in `java-gateway/src/main/java/com/rockey/gateway/dto/` per contracts/internal-message.md
- [X] T014 [P] Implement Redis session store (key: `tenant_id`+`channel`+`client_identifier`, 30-min sliding TTL) in `python-agent/src/agent/memory/session_store.py` per research.md §5
- [X] T015 [P] Implement `rag_indexer.py` (Google Drive → pgvector, chunking per constitution III.6) in `python-agent/src/agent/rag/rag_indexer.py`
- [X] T016 Implement FastAPI startup hook (RAG sync check; fatal error if Drive unreachable and `rag_documents` empty) in `python-agent/src/main.py` per constitution VIII.3/VIII.4
- [X] T017 [P] Implement `rag_query.py` (policy + article pgvector queries) in `python-agent/src/agent/rag/rag_query.py`
- [X] T018 Implement the LangGraph skeleton (`AgentState`, all 10 nodes as stubs, `current_state` persisted to Redis on every transition) in `python-agent/src/agent/graph.py` per data-model.md §State Machine
- [X] T019 [P] Implement per-dependency circuit breakers (LLM 30s, Java 10s, MCP 15s, pgvector 5s, `MAX_RETRIES=2`) in `python-agent/src/config/` per research.md §8
- [X] T020 [P] Implement the static in-memory YAML RAG fallback loader in `python-agent/src/agent/rag/rag_fallback.py` per research.md §7 / constitution VI.3
- [X] T021 Implement the templated system prompt (no retailer hardcoded) in `python-agent/src/agent/prompts/system_prompt.py` per constitution V.1

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Greeting and Identification (Priority: P1) 🎯 MVP

**Goal**: Greet the customer under the retailer's persona and verify their identity
(order number + email) before anything else can happen.

**Independent Test**: Start a session on any channel, provide a valid/invalid order number
and email, and confirm the agent introduces itself, confirms or rejects the order, and
offers escalation after 2 failed attempts.

### Tests for User Story 1

- [X] T022 [P] [US1] Contract test for `check_order` MCP tool in `python-agent/tests/contract/test_check_order.py`
- [X] T023 [P] [US1] Integration test: greeting + successful identification in `python-agent/tests/integration/test_identification.py`
- [X] T024 [P] [US1] Java unit test for `OrderService` lookup (happy path + wrong-tenant edge case) in `java-gateway/src/test/java/com/rockey/order/OrderServiceTest.java`
- [X] T024b [P] [US1] Edge-case tests: "can't find order number" guidance message, "skip identification" is blocked, in `python-agent/tests/integration/test_identification_edge_cases.py`

### Implementation for User Story 1

- [X] T025 [P] [US1] Implement `OrderRepository` + `OrderService` in `java-gateway/src/main/java/com/rockey/order/`
- [X] T026 [US1] Implement `GET /internal/orders/{id}` endpoint in `java-gateway/src/main/java/com/rockey/order/` (depends on T025)
- [X] T027 [P] [US1] Implement `check_order` MCP tool in `python-agent/src/agent/tools/check_order.py` (depends on T026)
- [X] T028 [US1] Implement `greeting.py` LangGraph node (persona introduction) in `python-agent/src/agent/states/greeting.py`
- [X] T029 [US1] Implement `identification.py` LangGraph node (ask order + email, max 2 attempts) in `python-agent/src/agent/states/identification.py` (depends on T027)
- [X] T030 [US1] Wire `GREETING → IDENTIFICATION → QUALIFICATION` transitions and the identification-failed → `ESCALATION` fallback in `python-agent/src/agent/graph.py` (depends on T028, T029)
- [X] T031 [US1] Add the cross-tenant-safe generic "order not found" message (constitution III.3) in `identification.py`

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - Request Qualification (Priority: P1)

**Goal**: Classify an identified customer's free-text request as return, complaint, or
out-of-scope, confirming understanding before proceeding.

**Independent Test**: After identification, send a return-shaped message, a complaint-shaped
message, and an out-of-scope message; confirm each is classified and routed correctly.

### Tests for User Story 2

- [X] T032 [P] [US2] Integration test: intent classification for return / complaint / other in `python-agent/tests/integration/test_qualification.py`
- [X] T032b [P] [US2] Edge-case tests: mixed return+complaint in one message, aggressive/impatient customer tone handling, in `python-agent/tests/integration/test_qualification_edge_cases.py`

### Implementation for User Story 2

- [X] T033 [US2] Implement `qualification.py` LangGraph node (LLM-based intent classification, max 2 clarifying questions) in `python-agent/src/agent/states/qualification.py` per research.md §4
- [X] T034 [US2] Wire `QUALIFICATION → RETURN_FLOW / COMPLAINT_FLOW / ESCALATION` transitions in `python-agent/src/agent/graph.py` (depends on T033)
- [X] T035 [US2] Implement the out-of-scope polite-redirect response path in `qualification.py`

**Checkpoint**: User Stories 1 AND 2 both work independently — customers are identified and
correctly routed.

---

## Phase 5: User Story 3 - Product Return Processing (Priority: P1) 🎯 MVP

**Goal**: Verify return eligibility against the retailer's policy and automatically generate
a return label and trigger a refund when eligible.

**Independent Test**: Submit an eligible return within the policy window and confirm a
return label is generated and a refund is triggered without human involvement (spec
Scenario 1).

### Tests for User Story 3

- [X] T036 [P] [US3] Contract test for `verify_eligibility` MCP tool in `python-agent/tests/contract/test_verify_eligibility.py`
- [X] T037 [P] [US3] Contract test for `create_return_label` MCP tool in `python-agent/tests/contract/test_create_return_label.py`
- [X] T038 [P] [US3] Contract test for `trigger_refund` MCP tool in `python-agent/tests/contract/test_trigger_refund.py`
- [X] T039 [P] [US3] Java unit test for `EligibilityService` (happy path + return-window-exceeded edge case) in `java-gateway/src/test/java/com/rockey/eligibility/EligibilityServiceTest.java`
- [X] T040 [P] [US3] Java unit test for `ReturnService` (happy path + non-returnable-item edge case) in `java-gateway/src/test/java/com/rockey/returns/ReturnServiceTest.java`
- [X] T041 [P] [US3] Integration test: eligible-return happy path, spec Scenario 1 (Marie Dupont / CMD-2026-00001) in `python-agent/tests/integration/test_return_happy_path.py`
- [X] T041b [P] [US3] Edge-case tests: final-clearance item refusal, customer disputes decision (no renegotiation), amount above the auto-refund threshold escalates rather than auto-approving, in `python-agent/tests/integration/test_return_edge_cases.py`

### Implementation for User Story 3

- [X] T042 [P] [US3] Implement `EligibilityService` + `PolicyLoader` (Drive/RAG-sourced thresholds, never LLM judgment) in `java-gateway/src/main/java/com/rockey/eligibility/`
- [X] T043 [US3] Implement `POST /internal/eligibility/check` endpoint in `java-gateway/src/main/java/com/rockey/eligibility/` (depends on T042)
- [X] T044 [P] [US3] Implement `ReturnService` + `ReturnLabelGenerator` in `java-gateway/src/main/java/com/rockey/returns/`
- [X] T045 [US3] Implement `POST /internal/returns` endpoint in `java-gateway/src/main/java/com/rockey/returns/` (depends on T044)
- [X] T046 [P] [US3] Implement `RefundService` in `java-gateway/src/main/java/com/rockey/refunds/`
- [X] T047 [US3] Implement `POST /internal/refunds` endpoint in `java-gateway/src/main/java/com/rockey/refunds/` (depends on T046)
- [X] T048 [P] [US3] Implement `verify_eligibility`, `create_return_label`, `trigger_refund` MCP tools in `python-agent/src/agent/tools/` (depends on T043, T045, T047)
- [X] T049 [US3] Implement `return_flow.py` LangGraph node (collect return reason) in `python-agent/src/agent/states/return_flow.py`
- [X] T050 [US3] Implement `verification.py` LangGraph node (call `verify_eligibility`, trace `applied_rule`) in `python-agent/src/agent/states/verification.py` (depends on T048)
- [X] T051 [US3] Implement `decision.py` LangGraph node (auto vs. escalate routing by threshold) in `python-agent/src/agent/states/decision.py`
- [X] T052 [US3] Implement `auto_action.py` LangGraph node (call `create_return_label`/`trigger_refund`) in `python-agent/src/agent/states/auto_action.py` (depends on T048)
- [X] T053 [US3] Wire `RETURN_FLOW → VERIFICATION → DECISION → AUTO_ACTION/ESCALATION` transitions in `python-agent/src/agent/graph.py` (depends on T049-T052)

**Checkpoint**: User Stories 1-3 deliver the core MVP return journey end-to-end.

---

## Phase 6: User Story 4 - Escalation to Human (Priority: P1) 🎯 MVP

**Goal**: Safely hand off any case the agent can't resolve, with a complete summary, and
notify the retailer's team on Slack.

**Independent Test**: Trigger any escalation condition (e.g. amount above threshold) and
confirm the human advisor's summary is complete and the customer receives a response-time
confirmation.

### Tests for User Story 4

- [X] T054 [P] [US4] Contract test for `escalate_to_human` MCP tool in `python-agent/tests/contract/test_escalate_to_human.py`
- [X] T055 [P] [US4] Java unit test for `TicketService` in `java-gateway/src/test/java/com/rockey/tickets/TicketServiceTest.java`
- [X] T056 [P] [US4] Integration test: escalation produces a Slack notification and full case summary in `python-agent/tests/integration/test_escalation.py`
- [X] T056b [P] [US4] Edge-case tests: escalation outside business hours (waiting message), duplicate escalation in same session (no duplicate ticket), customer refuses escalation and demands an immediate answer (agent explains limits and still escalates), in `python-agent/tests/integration/test_escalation_edge_cases.py`

### Implementation for User Story 4

- [X] T057 [P] [US4] Implement `TicketService` in `java-gateway/src/main/java/com/rockey/tickets/`
- [X] T058 [US4] Implement `POST /internal/tickets` endpoint in `java-gateway/src/main/java/com/rockey/tickets/` (depends on T057)
- [X] T059 [P] [US4] Implement the Slack Block Kit notification helper (per contracts/channel-apis.md), calling the Slack MCP directly, in `python-agent/src/agent/integrations/slack_notifier.py`
- [X] T060 [US4] Implement `escalate_to_human` MCP tool in `python-agent/src/agent/tools/escalate_to_human.py`: calls `POST /internal/tickets` (T058) to create the ticket, then calls the Slack notifier (T059) directly — no Java involvement in the Slack send (depends on T058, T059)
- [X] T061 [US4] Implement `escalation.py` LangGraph node (empathetic hand-off message + full case summary) in `python-agent/src/agent/states/escalation.py` (depends on T060)
- [X] T062 [US4] Wire every fallback edge (identification failed, qualification unclear, verification unavailable, decision ineligible/over-threshold, +3 exchanges without progress, auto-action failed) to `ESCALATION` in `python-agent/src/agent/graph.py`, per data-model.md's State Machine table
- [X] T063 [US4] Make `ESCALATION` irreversible for the remainder of the session in `escalation.py` / the Dossier's status transition

**Checkpoint**: All P1 stories (US1-US4) are complete — the MVP is feature-complete and safe:
every failure path terminates in a proper escalation rather than a stuck or wrong answer.

---

## Phase 7: User Story 5 - Quality Complaint Processing (Priority: P2)

**Goal**: Let customers report a defective/non-conforming item and get it resolved or
escalated with full context.

**Independent Test**: Submit a complaint for a defective item above the auto-refund
threshold and confirm it's qualified then escalated with a complete summary (spec
Scenario 3).

### Tests for User Story 5

- [X] T064 [P] [US5] Integration test: defective-item complaint above threshold, spec Scenario 3 (Sophie Bernard / CMD-2026-00003) in `python-agent/tests/integration/test_complaint_escalation.py`
- [X] T065 [P] [US5] Integration test: repeated complaint on the same item triggers automatic escalation with history in `python-agent/tests/integration/test_complaint_repeat.py`
- [X] T065b [P] [US5] Edge-case tests: vague defect description triggers up to 2 clarifying questions, complaint filed after the standard return window escalates under legal warranty (with an explanatory note), in `python-agent/tests/integration/test_complaint_edge_cases.py`

### Implementation for User Story 5

- [X] T066 [US5] Implement `complaint_flow.py` LangGraph node (reason + free-text description collection) in `python-agent/src/agent/states/complaint_flow.py`
- [X] T067 [US5] Extend `EligibilityService` with complaint-specific rules (legal warranty past the return window) in `java-gateway/src/main/java/com/rockey/eligibility/`
- [X] T068 [US5] Implement `client_history` lookup for repeated-complaint detection in `python-agent/src/agent/memory/history_store.py`
- [X] T069 [US5] Wire `COMPLAINT_FLOW → VERIFICATION` in `python-agent/src/agent/graph.py`, reusing US3's `VERIFICATION`/`DECISION`/`AUTO_ACTION`/`ESCALATION` nodes (depends on T066)

**Checkpoint**: User Stories 1-5 — both return and complaint flows work independently.

---

## Phase 8: User Story 6 - Confirmation and Closure (Priority: P2)

**Goal**: Give every customer a clear, structured summary of what was done and what happens
next, for both resolved and escalated cases.

**Independent Test**: Complete a return or complaint flow and confirm the closing message
contains a case number, action taken, processing time, and next step.

### Tests for User Story 6

- [X] T070 [P] [US6] Integration test: closing summary contains case number, action, processing time, next step in `python-agent/tests/integration/test_confirmation.py`

### Implementation for User Story 6

- [X] T071 [US6] Implement `confirmation.py` LangGraph node (structured summary + offer of additional help) in `python-agent/src/agent/states/confirmation.py`
- [X] T072 [US6] Persist final Dossier status (`resolved`/`escalated`) via the existing MCP tools, called from `confirmation.py`
- [X] T073 [US6] Attach the return label (email PDF / widget link) in the confirmation response per contracts/internal-message.md's `attachments` field

**Checkpoint**: User Stories 1-6 — every resolved or escalated case ends with a proper
customer-facing confirmation.

---

## Phase 9: User Story 7 - Multi-channel Consistency (Priority: P3)

**Goal**: Deliver identical agent behavior on the Web Widget and Email channels, with only
response formatting differing, and support same-channel session resumption.

**Independent Test**: Run the same return request on the Web Widget and via Email and
confirm identical decisions; interrupt a session and resume it within 30 minutes on the same
channel.

### Tests for User Story 7

- [X] T074 [P] [US7] Integration test: identical decision for the same request via Web Widget vs. Email in `python-agent/tests/integration/test_channel_parity.py`
- [X] T075 [P] [US7] Integration test: session resumes within 30 minutes on the same channel in `python-agent/tests/integration/test_session_resume.py`
- [X] T075b [P] [US7] Edge-case tests: mid-request channel switch starts a new session, unavailable channel shows an alternative-channel message, in `python-agent/tests/integration/test_channel_edge_cases.py`

### Implementation for User Story 7

- [X] T076 [P] [US7] Implement `WebChatController` (WebSocket + REST fallback) in `java-gateway/src/main/java/com/rockey/gateway/controller/WebChatController.java` per contracts/channel-apis.md
- [X] T077 [P] [US7] Implement `WebChatAdapter` (native ↔ internal format) in `java-gateway/src/main/java/com/rockey/gateway/adapter/WebChatAdapter.java`
- [X] T078 [P] [US7] Implement `EmailController` (IMAP polling every 2 minutes) in `java-gateway/src/main/java/com/rockey/gateway/controller/EmailController.java`
- [X] T079 [P] [US7] Implement `EmailAdapter` (parse inbound; HTML + PDF outbound) in `java-gateway/src/main/java/com/rockey/gateway/adapter/EmailAdapter.java`
- [X] T080 [US7] Implement the embeddable JS widget snippet (`data-tenant`, `data-position`), served by `java-gateway`
- [X] T081 [US7] Implement per-channel response-length/format adaptation (widget vs. email) in the agent's response-formatting layer

**Checkpoint**: All 7 user stories are independently functional.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T082 [P] Implement `AdminController` with `POST /admin/rag/sync?tenant_id=vinted` in `java-gateway/src/main/java/com/rockey/gateway/controller/AdminController.java`
- [X] T083 [P] Add structured JSON error logging (`session_id`, `tenant_id`, `timestamp`) across Java and Python per constitution VI.1
- [X] T084 [P] Source normalized customer-facing error messages from the retailer's Drive config per constitution VI.4
- [X] T085 Run quickstart.md's 5 POC validation scenarios end-to-end against `docker-compose`
- [X] T086 [P] Verify Java test coverage > 70% (constitution VII.1) and add tests to close any gaps
- [X] T087 [P] Confirm all 5 MCP tools in contracts/mcp-tools.md have a passing contract test
- [X] T088 Security pass: zero hardcoded secrets, `.env.example` complete, `X-Internal-Token` enforced on every `/internal/**` route (constitution IV.1/IV.2)
- [X] T089 Verify no agent response ever contains "Rockey", "AI", "algorithm", or "automated system" across a full quickstart.md run (constitution V.1 / spec FR-013)
- [X] T090 Replace `PolicyLoader`'s bundled `vinted-policy.yaml` with a live Drive-derived source (constitution I.7/V.3): sync the retailer's policy thresholds from their Drive docs into a queryable store on the RAG-sync schedule. `EligibilityService` must not change — it only ever calls `PolicyLoader.load(tenantId)` and consumes the `PolicyThresholds` record, so this is scoped to `PolicyLoader.java` (and `vinted-policy.yaml`'s replacement) alone. Introduced as a documented simplification during Setup/Foundational/US1-4 implementation (see `PolicyLoader.java`'s javadoc).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Stories (Phase 3-9)**: All depend on Foundational completion.
  - US1-US4 (P1) form the MVP loop and are best done in order (US2 needs US1's
    identification; US3 needs US2's routing; US4's escalation wiring needs US1-US3's nodes
    to exist as targets) — see below.
  - US5-US7 (P2/P3) can each start once Foundational is done and layer on top of US1-US4.
- **Polish (Final Phase)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational. First story to implement.
- **US2 (P1)**: Depends on US1 (needs an identified customer to qualify).
- **US3 (P1)**: Depends on US2 (needs a classified "return" intent to act on).
- **US4 (P1)**: Depends on US1-US3 existing as wiring targets for their fallback edges, but
  its own MCP tool/service/endpoint work (T057-T061) can be built in parallel with US2/US3.
- **US5 (P2)**: Depends on US2 (needs a classified "complaint" intent) and reuses US3's
  VERIFICATION/DECISION/AUTO_ACTION/ESCALATION nodes.
- **US6 (P2)**: Depends on US3 and US5 (closes out both return and complaint flows).
- **US7 (P3)**: Depends on US1-US6 already working end-to-end on one channel before
  parity/resumption can be verified.

### Within Each User Story

- Tests are written first and MUST fail before implementation begins.
- Java services/endpoints before the Python MCP tools that call them.
- LangGraph nodes before wiring their transitions into `graph.py`.
- Story complete (checkpoint) before moving to the next priority.

### Parallel Opportunities

- All Setup tasks marked [P] can run together.
- All Foundational tasks marked [P] can run together once T008/T009 (schema) land.
- Within a story, all [P]-marked contract/unit tests can run together, and all [P]-marked
  Java service implementations can run together.
- US4's Java-side work (T057-T058) and Python-side Slack helper (T059) can all proceed in
  parallel with US2/US3's implementation, since none of them depend on US2/US3's internals —
  only `escalate_to_human` (T060) and the `graph.py` wiring (T062) wait on their
  prerequisites.

---

## Parallel Example: User Story 1

```bash
# Tests for User Story 1 together:
Task: "Contract test for check_order MCP tool in python-agent/tests/contract/test_check_order.py"
Task: "Integration test: greeting + successful identification in python-agent/tests/integration/test_identification.py"
Task: "Java unit test for OrderService lookup in java-gateway/src/test/java/com/rockey/order/OrderServiceTest.java"

# Implementation for User Story 1 together (after tests fail red):
Task: "Implement OrderRepository + OrderService in java-gateway/src/main/java/com/rockey/order/"
```

---

## Implementation Strategy

### MVP First (User Stories 1-4)

Unlike a single-P1-story MVP, this feature's four P1 stories form one minimal safe loop —
skipping any one of them leaves either no way to identify customers, no way to route their
request, no way to resolve the most common request (returns), or no safety net when the
agent can't help.

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything)
3. Complete Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (US4)
4. **STOP and VALIDATE**: run quickstart.md Scenarios 1, 2, and 5 (return happy path, return
   past deadline, failed identification) — all exercise only US1-US4.
5. Deploy/demo the MVP.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → US2 → US3 → US4 → MVP complete → validate against quickstart.md → demo.
3. Add US5 (complaints) → validate with Scenario 3 → demo.
4. Add US6 (confirmation) → validate closing messages → demo.
5. Add US7 (multi-channel) → validate channel parity + resumption → demo.
6. Polish phase → full quickstart.md run (all 5 scenarios) + coverage/security checks.

---

## Notes

- [P] tasks touch different files with no unmet dependencies.
- [Story] labels map every user-story-phase task back to spec.md for traceability.
- Escalation (US4) is cross-cutting by nature — its fallback wiring (T062) necessarily
  touches code introduced by US1-US3, which is why it's sequenced after them despite being
  P1 alongside them.
- Commit after each task or logical group; stop at any checkpoint to validate a story
  independently before continuing.
