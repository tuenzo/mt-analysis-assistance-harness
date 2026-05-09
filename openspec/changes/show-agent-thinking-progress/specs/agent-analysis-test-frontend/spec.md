## MODIFIED Requirements

### Requirement: Runtime evidence display
The test harness SHALL display observed agent runtime evidence including session metadata, SSE connection state, thought/progress stream, message transcript, tool calls, job progress, approval requests, artifact events, and errors.

#### Scenario: Tool call event received
- **WHEN** the event stream emits a `tool_call_started` or `tool_call_finished` event
- **THEN** the test harness displays the tool name, action, status, and available payload or summary

#### Scenario: Thought progress event received
- **WHEN** the event stream emits an `assistant_thought_delta` event
- **THEN** the test harness displays the thought/progress text in runtime evidence without merging it into the final assistant answer

#### Scenario: Approval event received
- **WHEN** the event stream emits an approval request or a pending approval is loaded
- **THEN** the test harness displays the approval action, reason, risk level, and approve or reject controls

#### Scenario: Artifact event received
- **WHEN** the event stream emits an `artifact_created` event
- **THEN** the test harness displays the artifact id, name, and path when available
