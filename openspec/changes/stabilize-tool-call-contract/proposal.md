## Why

Recent real LLM turns can produce semantically valid `business_analysis` calls whose payload shape does not exactly match backend tool handlers, such as `{"charts":["all"]}` for `chart.render_dashboard`. This causes avoidable tool failures, noisy UI state, and brittle demos even though the intended action is clear.

## What Changes

- Introduce a stable tool-call contract layer between the Claude Agent SDK adapter and `AnalysisToolGateway`.
- Normalize LLM-generated `business_analysis` envelopes and action payload aliases into canonical backend payloads before execution.
- Add action-specific Pydantic payload schemas and normalizers for high-traffic actions, starting with `chart.render_dashboard`.
- Return structured, retryable validation feedback when a payload cannot be safely normalized.
- Persist raw payload, normalized payload, normalization warnings, and validation errors for audit/debugging.
- Add contract-corpus tests built from observed LLM payload variants and browser smoke tests for the Agent page tool-call lifecycle.

## Capabilities

### New Capabilities
- `tool-call-contract-stability`: Defines canonicalization, validation, retry guidance, auditability, and regression coverage for LLM-generated `business_analysis` tool calls.

### Modified Capabilities
- None.

## Impact

- Affected backend modules: `backend/app/agent/claude_agent_sdk_adapter.py`, `backend/app/tools/gateway.py`, `backend/app/tools/registry.py`, `backend/app/tools/schemas.py`, action tool modules such as `backend/app/tools/chart_tools.py`.
- Affected tests: backend contract/unit tests, gateway tests, and browser automation for `/projects/{project_id}/agent`.
- No external dependency is expected beyond Pydantic already used by the backend.
