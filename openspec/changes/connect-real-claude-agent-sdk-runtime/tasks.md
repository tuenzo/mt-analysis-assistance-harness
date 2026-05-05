## Tasks

- [x] Add OpenSpec artifacts for the real Claude Agent SDK runtime change.
- [x] Add backend dependency and keep provider configuration centralized.
- [x] Replace the SDK adapter with `claude_agent_sdk` query/options/tool MCP integration.
- [x] Expose exactly one SDK MCP tool, `business_analysis`, backed by `AnalysisToolGateway`.
- [x] Configure allowed tools to include only `mcp__business_analysis__business_analysis` unless read-only built-ins are explicitly enabled.
- [x] Map SDK messages and tool results into existing SSE event dictionaries.
- [x] Persist and resume SDK external session ids through `SessionStore`/`MessageRuntime`.
- [x] Avoid duplicate gateway execution for SDK-emitted tool result events while preserving mock fallback behavior.
- [x] Clean garbled runtime prompt/mock text in the touched agent/config files.
- [x] Run focused SDK contract tests and full backend pytest; document remaining unrelated data-ingest failures.
