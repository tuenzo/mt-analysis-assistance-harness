## Context

The current `MessageRuntime.handle_message()` creates a turn, calls the adapter synchronously, writes all events, then returns the `MessageResponse`. The frontend cannot subscribe to SSE until that response arrives, so long SDK thinking periods appear frozen. The SDK adapter also maps text deltas but does not expose `ThinkingBlock` content or streaming `thinking_delta` content.

The implementation must show useful thinking/progress without treating the Codex or model session as the project fact source. It also needs to keep raw private reasoning separate from final answers. The event should represent displayable thought/progress content only.

## Goals / Non-Goals

**Goals:**
- Let the frontend connect to SSE immediately after message submission.
- Surface public thinking/progress text while the agent is working.
- Keep thought content visually distinct from final assistant messages.
- Support mock runtime and real Claude Agent SDK runtime.
- Preserve the single `business_analysis` tool gateway boundary.

**Non-Goals:**
- No new business tool actions.
- No database schema changes.
- No attempt to expose hidden chain-of-thought beyond provider/runtime content intentionally emitted for display.

## Decisions

### Background turn worker

`handle_message()` will persist the turn and return the response immediately, then start a daemon worker that runs the adapter and appends events. The SSE route already polls `MessageRuntime.get_events()`, so this keeps the HTTP contract stable while making events arrive during execution.

Alternative considered: keep the request synchronous and only add UI text. That does not solve long thinking because the browser cannot receive events until the message response is returned.

### Public thought event

Use a new `assistant_thought_delta` event with `delta`, `phase`, and `visibility` fields. The event is rendered as an activity/thought panel, not appended to the final assistant answer.

Alternative considered: reuse `assistant_message_delta`. That would mix draft/thought text into the final answer transcript and make it hard to distinguish reasoning progress from user-facing conclusions.

### SDK thinking mapping

When the SDK emits `ThinkingBlock` or stream `thinking_delta`, the adapter maps it into `assistant_thought_delta`. When only structural milestones are available, the runtime emits short progress lines such as "Reading project context" and "Preparing final answer".

Alternative considered: wait for every provider to expose the same thought schema. The harness needs immediate visibility for both mock and real providers, so safe milestone events are a practical fallback.

## Risks / Trade-offs

- Background workers can finish after the original request scope. -> Each worker opens its own database session through runtime helpers and records terminal error events on exceptions.
- Some SDK thinking content may be verbose. -> Frontend caps retained thought events and renders them in a bounded scrollable area.
- Tests that previously expected events immediately after POST may need to poll briefly. -> Add polling helper in relevant tests instead of relying on synchronous completion.
