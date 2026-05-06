## Why

The existing project UI mixes the agent command center with the broader analysis workspace, which makes it harder to isolate whether the agent analysis loop itself is complete and runnable. A dedicated frontend test surface gives us a focused way to exercise the message runtime, SSE stream, tool call reporting, approvals, and artifact events without unrelated navigation or dashboard state.

## What Changes

- Add an isolated frontend route for agent analysis testing.
- Let testers select or create a project before sending agent messages.
- Route every natural-language test prompt through `POST /api/agent/messages`.
- Display the full agent runtime surface needed for verification: session metadata, SSE connection status, message transcript, tool call events, job progress, approval requests, artifacts, and errors.
- Provide quick test prompts for common analysis actions while keeping the prompt editable.
- Keep the existing project workspace UI and backend API contracts unchanged.

## Capabilities

### New Capabilities
- `agent-analysis-test-frontend`: A standalone frontend harness for end-to-end testing of the agent analysis backend contract.

### Modified Capabilities
- `business-analysis-system`: Clarifies that agent analysis testing must still preserve the message-first runtime path and the single `business_analysis` tool gateway boundary.

## Impact

- Frontend App Router route under `frontend/src/app/`.
- New or reused frontend components under `frontend/src/features/agent/`.
- Reuse existing API client and SSE hook contracts in `frontend/src/lib/`.
- No database schema changes.
- No backend route changes expected unless implementation exposes a gap in the existing API contract.
