## 1. Backend Runtime

- [x] 1.1 Run agent turns in a background worker after returning `MessageResponse`.
- [x] 1.2 Emit public `assistant_thought_delta` events for runtime milestones and mock adapter branches.
- [x] 1.3 Map Claude Agent SDK `ThinkingBlock` and streaming thinking deltas to thought events.

## 2. Frontend Display

- [x] 2.1 Add `assistant_thought_delta` to frontend SSE types and agent store state.
- [x] 2.2 Render thought/progress content in the project agent page.
- [x] 2.3 Render thought/progress content in the standalone agent analysis test harness.

## 3. Validation

- [x] 3.1 Add or update backend tests for async turn response and thought event delivery.
- [x] 3.2 Run relevant backend pytest tests.
- [x] 3.3 Run frontend build validation.
- [x] 3.4 Restart local frontend/backend services after implementation.
