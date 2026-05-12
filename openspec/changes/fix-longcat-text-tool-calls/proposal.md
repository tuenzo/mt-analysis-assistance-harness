## Why

Real LongCat runs through `claude_agent_sdk`, but LongCat may emit tool requests as
textual `<longcat_tool_call>` blocks instead of SDK `ToolUseBlock` objects. The
current adapter forwards those blocks as assistant text, no `business_analysis`
gateway call happens, and the SDK turn can end with `Reached maximum number of
turns`.

## What Changes

- Add a narrow LongCat compatibility parser in the Claude Agent SDK adapter.
- Convert textual `business_analysis` tool blocks into the same persisted
  `tool_call_started`, `tool_call_finished`, and approval events used by SDK
  tool calls.
- Deduplicate repeated textual tool blocks inside one turn.
- Suppress raw LongCat tool markup from assistant answer deltas.
- Add focused tests for parsing, dedupe, and event mapping.

## Impact

- Modified: `backend/app/agent/claude_agent_sdk_adapter.py`
- Modified: `backend/app/tests/test_claude_agent_sdk_contract.py`
