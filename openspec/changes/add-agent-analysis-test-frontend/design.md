## Context

The existing frontend already has an Agent Command Center inside each project route and a shared API/SSE layer for `POST /api/agent/messages`, session events, approvals, and artifacts. For agent analysis QA, that route carries too much surrounding workspace UI and does not make the backend contract checklist explicit enough.

This change adds a separate App Router page that reuses the existing backend contract and store behavior. It is intentionally a frontend-only harness unless implementation exposes an API gap.

## Goals / Non-Goals

**Goals:**
- Provide a standalone route for testing the agent analysis runtime end to end.
- Support project selection and lightweight test project creation from the page.
- Preserve the message-first architecture by sending test prompts through `POST /api/agent/messages`.
- Show enough runtime evidence to judge completeness: session, connection state, messages, tool calls, jobs, approvals, artifacts, and errors.
- Keep the page useful for both mock and real Claude Agent SDK providers.

**Non-Goals:**
- No new agent backend route.
- No direct frontend calls to analysis tool actions.
- No new analysis algorithm behavior.
- No database schema changes.
- No replacement of the production project Agent Command Center.

## Decisions

### Add a route-level test harness

Use a new App Router route outside `/projects/[project_id]` so testers can enter the harness directly and switch projects without the project workspace layout. This keeps QA focused on the agent analysis loop while preserving the production UI.

Alternative considered: add a "test mode" inside the existing project agent page. That would be smaller, but it keeps the same layout noise and makes it easier to confuse QA-only shortcuts with production workflow.

### Reuse API client, SSE hook, and agent store

The harness should reuse `api.createMessage`, `useAgentEvents`, and `useAgentStore` rather than creating a parallel protocol implementation. This gives the test page the same failure modes as production and avoids contract drift.

Alternative considered: write raw `fetch` and `EventSource` calls inside the page. That would expose low-level debugging, but it would be more likely to diverge from the actual frontend contract.

### Show a contract checklist in the UI

The page should derive pass/fail style indicators from observed state: message response, SSE connection, assistant final answer, tool calls, approvals, jobs, artifacts, and errors. These indicators are only frontend observations; they do not claim backend correctness beyond events received.

Alternative considered: hard-code a scripted test runner. That belongs later once backend fixtures and deterministic mock scenarios are stable.

## Risks / Trade-offs

- Test project creation can still fail if the backend is not running. -> Surface API errors clearly and keep manual project ID entry available.
- Reusing the global agent store means state can carry across project switches. -> Clear harness state when switching project or resetting the test run.
- Some checks depend on the prompt and provider behavior. -> Label them as observed runtime signals, not mandatory success criteria for every prompt.
