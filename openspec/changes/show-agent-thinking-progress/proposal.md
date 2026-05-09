## Why

Long agent turns currently leave the frontend looking idle because the message request waits for the runtime to finish and the UI only shows generic "processing" text. Users need visible, streaming insight into what the agent is considering while it reads project context, decides tool calls, waits on tools, and prepares the final answer.

## What Changes

- Return `POST /api/agent/messages` immediately after creating the turn and run the adapter in a background turn worker.
- Add a public `assistant_thought_delta` SSE event for displayable thinking/progress text.
- Emit thinking/progress events from mock and Claude Agent SDK paths, including provider-emitted thinking blocks when available and safe runtime milestones otherwise.
- Store thought events in the frontend agent store and render them in both the project agent page and standalone test harness.
- Keep assistant answer deltas and final answers separate from thought/progress content.

## Capabilities

### New Capabilities
- `agent-thinking-progress`: Streaming, visible agent thinking/progress display during long-running agent turns.

### Modified Capabilities
- `agent-analysis-test-frontend`: The test harness observes and displays thought/progress events as part of runtime evidence.

## Impact

- Backend agent runtime execution and event buffering.
- Claude adapter event mapping.
- Agent SSE event type contract.
- Frontend agent store and agent UI surfaces.
- Backend tests and frontend build validation.
