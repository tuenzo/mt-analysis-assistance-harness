# Design

## Frontend

`AgentAnalysisPage` owns the project route context, so it should own the per-project restore key. On mount:

1. Try `localStorage["baa.agentSession.<project_id>"]`.
2. Validate it by loading the session and ensuring `project_id` matches.
3. Load session messages and pending approvals.
4. If no valid stored session exists, fetch project sessions from the backend and load the most recent one.
5. Keep the existing demo-session fallback for demo mode.

When a new message creates or resumes a session, update the stored key. When the user clears the conversation, remove the key and reset local session state.

## Backend

Project session listing should return enough data for the frontend to restore a session without additional guessing, including `project_id`, and should be ordered newest first.

## Compatibility

Existing `POST /api/agent/messages` behavior remains unchanged. The restore logic only affects page initialization and clear behavior.
