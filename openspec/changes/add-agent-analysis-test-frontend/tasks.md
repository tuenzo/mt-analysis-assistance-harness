## 1. Test Harness Structure

- [x] 1.1 Add a standalone App Router route for agent analysis testing.
- [x] 1.2 Add a focused client component for project selection, prompt submission, and runtime observation.

## 2. Backend Contract Integration

- [x] 2.1 Reuse the existing API client and SSE hook for `POST /api/agent/messages` and session event streaming.
- [x] 2.2 Support existing project selection and lightweight test project creation.
- [x] 2.3 Display session metadata, connection status, transcript, tool calls, jobs, approvals, artifact events, and errors.
- [x] 2.4 Add an observed-state checklist for message response, SSE, final answer, tool calls, approvals, jobs, artifacts, and errors.
- [x] 2.5 Allow the standalone test route to override the API base URL with `api_base` for isolated backend instances.
- [x] 2.6 Add fixture CSV upload controls so a clean test project can run a real analysis pipeline.
- [x] 2.7 Document the current prompt composition paths and exact prompt templates for collaborative optimization.
- [x] 2.8 Verify the real `claude_agent_sdk` runtime path and bind SDK tool calls to the runtime project id.
- [x] 2.9 Load the project business-analysis skill into real SDK requests and expose loaded skills in diagnostics.
- [x] 2.10 Isolate the Claude SDK config directory so real `.env` API credentials cannot be bypassed by a local Claude Code login.
- [x] 2.11 Pass `.env` credentials as `ANTHROPIC_AUTH_TOKEN` as well as `ANTHROPIC_API_KEY` for Bearer-token compatible gateways.

## 3. Validation

- [x] 3.1 Run frontend lint or build validation.
- [x] 3.2 Run relevant backend tests for agent message contract if backend code changes are needed.
- [x] 3.3 Run in-app browser E2E against an isolated backend/database/workspace.
