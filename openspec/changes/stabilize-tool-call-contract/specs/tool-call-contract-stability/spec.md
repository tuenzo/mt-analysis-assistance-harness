## ADDED Requirements

### Requirement: Tool Calls Are Normalized Before Execution
The system SHALL normalize every LLM-generated `business_analysis` tool call into a canonical action payload before invoking an internal tool handler.

#### Scenario: Equivalent dashboard all-chart aliases
- **WHEN** the Agent calls `business_analysis` with action `chart.render_dashboard` and payload `{"charts":["all"]}`
- **THEN** the gateway normalizes the payload to request all default dashboard chart IDs
- **AND** executes `chart.render_dashboard` without treating `"all"` as a chart ID

#### Scenario: Comma-separated dashboard chart list
- **WHEN** the Agent calls `business_analysis` with action `chart.render_dashboard` and payload `{"chart_ids":"activity_comparison,gmv_trend"}`
- **THEN** the gateway normalizes the payload to `{"chart_ids":["activity_comparison","gmv_trend"]}`
- **AND** executes only those requested charts

### Requirement: Invalid Payloads Return Repairable Feedback
The system SHALL return a structured failed `ToolResult` when a payload cannot be safely normalized or validated.

#### Scenario: Ambiguous dashboard chart request
- **WHEN** the Agent calls `business_analysis` with action `chart.render_dashboard` and a payload that is neither omitted, `"all"`, a comma string, nor a list of known chart IDs
- **THEN** the gateway returns `ok=false` with `error.code` set to `INVALID_PAYLOAD`
- **AND** includes an `assistant_hint` showing a minimal corrected payload shape

### Requirement: Gateway Persists Raw And Canonical Payloads
The system SHALL preserve both the raw LLM payload and the normalized canonical payload for each persisted tool call.

#### Scenario: Normalized tool call is audited
- **WHEN** a persisted `business_analysis` tool call is normalized before execution
- **THEN** the tool-call audit record includes the original payload, the canonical payload, and any normalization warnings

### Requirement: Tool Call Status Cannot Hang On Contract Errors
The system SHALL transition tool calls with normalization or validation failures into a terminal failed state and stream a corresponding event.

#### Scenario: Validation fails before handler execution
- **WHEN** payload validation fails before an internal tool handler is invoked
- **THEN** the persisted tool call status becomes `failed`
- **AND** the event stream emits `tool_call_failed` with the same action and tool call ID

### Requirement: No-Tool Clarification Turns Terminate Thinking State
The system SHALL close an Agent turn with a terminal event when the model replies with assistant text but does not call a tool.

#### Scenario: Agent asks user for missing information
- **WHEN** the runtime receives assistant message deltas explaining that more user input is needed
- **AND** no tool call or explicit final answer event is emitted by the provider
- **THEN** the message runtime emits a `final_answer` event using the streamed assistant text
- **AND** the persisted turn status becomes `completed`
- **AND** the frontend stops showing the turn as actively thinking

#### Scenario: Provider emits empty final result after assistant text
- **WHEN** the runtime receives assistant message deltas followed by an empty `final_answer`
- **THEN** the message runtime replaces the empty final answer with the streamed assistant text
- **AND** the frontend keeps the assistant reply visible while ending the active run state

### Requirement: Contract Corpus Covers Observed LLM Variants
The system SHALL maintain regression tests for observed LLM-generated payload variants for each contracted action.

#### Scenario: Observed payload variant is added
- **WHEN** a tool-call format mismatch is discovered in a real Agent turn
- **THEN** a contract-corpus test is added before or with the fix
- **AND** the test asserts the intended normalization or structured failure behavior

### Requirement: Real Runtime Smoke Test Covers Tool Call Lifecycle
The system SHALL include a browser or integration smoke check that verifies visible Agent-page tool call lifecycle behavior against the real backend runtime configuration.

#### Scenario: Agent refreshes dashboard charts
- **WHEN** the Agent page asks the backend to regenerate dashboard charts through `business_analysis`
- **THEN** the UI observes a started state and a terminal succeeded or failed state
- **AND** successful calls show returned artifact results instead of leaving the tool call pending
