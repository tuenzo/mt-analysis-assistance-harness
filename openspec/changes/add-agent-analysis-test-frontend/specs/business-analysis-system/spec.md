## ADDED Requirements

### Requirement: Agent analysis test harness preserves runtime boundaries
Any frontend surface built for testing agent analysis SHALL preserve the message-first runtime path and SHALL NOT call internal analysis actions directly from natural-language input.

#### Scenario: Tester submits natural language
- **WHEN** a tester submits a natural-language analysis request from a test harness
- **THEN** the request is routed through `POST /api/agent/messages`
- **AND** any business analysis execution is decided by the agent runtime and performed through the registered `business_analysis` gateway

#### Scenario: Tester observes tool behavior
- **WHEN** a tester uses the harness to inspect tool behavior
- **THEN** the frontend displays events emitted by the backend runtime rather than fabricating successful tool results
