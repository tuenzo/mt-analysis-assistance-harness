## Design

The existing SDK-native tool path remains authoritative. This change only handles
assistant text containing complete `<longcat_tool_call>...</longcat_tool_call>`
blocks.

When the adapter sees such a block it:

1. Parses `project_id`, `action`, `payload`, and `reason`.
2. Forces `project_id` to the active runtime project, matching the SDK tool
   safeguard.
3. Persists a pending `ToolCall` record with the same helper used by SDK-native
   calls.
4. Executes `BusinessAnalysisMCPServer.handle_tool_call`, which routes through
   `AnalysisToolGateway`.
5. Emits standard SSE tool events and approval events.
6. Records the parsed call signature so repeated LongCat text blocks do not
   execute the same action repeatedly.

If the SDK finishes with a max-turn error after textual tool calls were executed,
the adapter emits a compact final answer summarizing executed tool results instead
of leaving the UI in a failed loop. Future turns still rebuild project context
from the backend workspace and database.
