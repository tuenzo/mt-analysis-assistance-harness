## Overview

The backend keeps `POST /api/agent/messages` as the only natural-language entrypoint. `MessageRuntime` remains responsible for turn persistence, SSE buffering, and replay. The adapter owns the Claude Agent SDK query loop and exposes only the controlled `business_analysis` MCP tool.

## Runtime Flow

1. `MessageRuntime` builds workspace context and composes the user prompt.
2. It creates or resumes an `AnalysisSession` using the configured provider.
3. `ClaudeAgentSDKAdapter` calls Claude Agent SDK `query()` with a project workspace cwd, an SDK MCP server, and `allowed_tools=["mcp__business_analysis__business_analysis"]`.
4. The SDK MCP tool calls `AnalysisToolGateway.execute()` and returns a text content block containing the serialized `ToolResult`; failures return `is_error=True`.
5. SDK messages are mapped into the existing SSE event names and persisted as `AgentEvent` rows.

## Safety

- Built-in SDK tools are excluded unless `APP_AGENT_ALLOW_BUILTIN_READ_TOOLS=true`.
- Business actions still go through `AnalysisToolGateway`; the SDK does not bypass permission, approval, audit, or artifact logic.
- Mock fallback is preserved for local development without credentials.

## Compatibility

- Existing frontend SSE event types remain unchanged.
- Existing mock adapter behavior remains available through provider `mock` or missing SDK/API key.
- Integration tests are opt-in with `RUN_AGENT_SDK_INTEGRATION=1`.
