## Why

The current `claude_agent_sdk` provider still behaves like a mock or a Messages API wrapper. It does not use the Claude Agent SDK agent loop, SDK MCP tools, or runtime session semantics, and `MessageRuntime` can execute tool calls a second time after the adapter has already handled them.

## What Changes

- Replace the pseudo-SDK adapter with a Claude Agent SDK based adapter.
- Register exactly one in-process SDK MCP tool: `business_analysis(project_id, action, payload, reason)`.
- Restrict SDK tool access to `mcp__business_analysis__business_analysis`, with built-in read tools disabled by default.
- Persist configured runtime provider and adapter external session id in `AnalysisSession`.
- Keep mock fallback when the SDK package or API key is unavailable.
- Map SDK assistant, tool, result, and error events into the existing SSE contract.
- Add contract tests and a gated integration smoke test.

## Impact

- Modified: `backend/requirements.txt`
- Modified: `backend/app/core/config.py`
- Modified: `backend/app/agent/claude_agent_sdk_adapter.py`
- Modified: `backend/app/agent/message_runtime.py`
- Modified: `backend/app/agent/session_store.py`
- Modified: `backend/app/agent/prompt_composer.py`
- Added: `backend/app/tests/test_claude_agent_sdk_contract.py`
