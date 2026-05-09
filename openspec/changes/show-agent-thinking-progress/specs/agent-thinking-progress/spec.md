## ADDED Requirements

### Requirement: Immediate message response during long turns
The backend SHALL return the agent message response after creating the turn and SHALL continue runtime execution asynchronously.

#### Scenario: Message accepted before turn completes
- **WHEN** a user submits a natural-language message to `POST /api/agent/messages`
- **THEN** the response contains the `turn_id`, `session_id`, and event stream URL before the adapter finishes producing its final answer

### Requirement: Thought progress SSE events
The backend SHALL emit displayable agent thinking/progress through `assistant_thought_delta` SSE events.

#### Scenario: Runtime starts a turn
- **WHEN** the runtime starts processing a turn
- **THEN** the event stream includes a thought/progress event indicating that project context or runtime state is being read

#### Scenario: SDK emits thinking content
- **WHEN** the Claude Agent SDK emits a thinking block or thinking delta
- **THEN** the adapter maps that displayable content to `assistant_thought_delta` without appending it to the assistant final answer

### Requirement: Thought display in agent UI
The frontend SHALL display thought/progress events while the agent is running and keep them visually separate from the assistant answer transcript.

#### Scenario: Long-running turn streams thoughts
- **WHEN** `assistant_thought_delta` events arrive before `final_answer`
- **THEN** the project agent page displays the thought/progress text in the run activity area

#### Scenario: Final answer arrives
- **WHEN** a `final_answer` event arrives
- **THEN** the final answer remains the assistant message and the thought/progress content remains separate
