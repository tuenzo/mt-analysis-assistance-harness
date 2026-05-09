# Add Agent Thread Management

## Why

Agent conversations are already persisted as sessions, but the Agent page only auto-restores one thread. Users need explicit controls to continue previous threads and remove obsolete conversation history.

## What

- Expose project session summaries with last activity, preview, and message count.
- Add a backend delete endpoint for an Agent session.
- Add Agent-page UI for starting a new thread, continuing an existing thread, and deleting a thread.
- Keep project artifacts/results intact when deleting only the conversation thread.

## Impact

- Backend: `app/agent/session_store.py`, `app/api/sessions.py`, `app/api/projects.py`, `app/main.py`
- Frontend: `src/features/agent/agent-analysis-page.tsx`, `src/lib/api-client.ts`, `src/lib/api-types.ts`
- Tests: session list/delete contract coverage
