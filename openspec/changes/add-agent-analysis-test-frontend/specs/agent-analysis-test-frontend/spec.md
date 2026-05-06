## ADDED Requirements

### Requirement: Standalone agent analysis test route
The frontend SHALL provide a standalone agent analysis test route outside the project workspace layout for focused runtime verification.

#### Scenario: Open test harness directly
- **WHEN** a tester navigates to the agent analysis test route
- **THEN** the system displays a dedicated test interface without requiring entry through the project dashboard tabs

### Requirement: Project binding for agent messages
The test harness SHALL require an active project id before sending agent messages and SHALL allow the tester to select an existing project or create a lightweight test project.

#### Scenario: Send with selected project
- **WHEN** a tester selects a project and sends a prompt
- **THEN** the frontend sends the prompt with that project id through the agent messages API

#### Scenario: Create test project
- **WHEN** a tester creates a project from the harness
- **THEN** the project is available as the active project for subsequent agent prompts

### Requirement: Message-first backend connection
The test harness SHALL send natural-language prompts only through `POST /api/agent/messages` and SHALL consume the returned session event stream for runtime updates.

#### Scenario: Start agent turn
- **WHEN** a tester submits a natural-language analysis prompt
- **THEN** the frontend calls `POST /api/agent/messages` and subscribes to the returned session events

### Requirement: Runtime evidence display
The test harness SHALL display observed agent runtime evidence including session metadata, SSE connection state, message transcript, tool calls, job progress, approval requests, artifact events, and errors.

#### Scenario: Tool call event received
- **WHEN** the event stream emits a `tool_call_started` or `tool_call_finished` event
- **THEN** the test harness displays the tool name, action, status, and available payload or summary

#### Scenario: Approval event received
- **WHEN** the event stream emits an approval request or a pending approval is loaded
- **THEN** the test harness displays the approval action, reason, risk level, and approve or reject controls

#### Scenario: Artifact event received
- **WHEN** the event stream emits an `artifact_created` event
- **THEN** the test harness displays the artifact id, name, and path when available

### Requirement: Contract checklist
The test harness SHALL provide visible observed-state checks that help testers judge whether agent analysis is runnable end to end.

#### Scenario: Turn completes
- **WHEN** the event stream emits a final answer for a submitted turn
- **THEN** the checklist marks the message response, event stream, and final answer signals as observed

#### Scenario: Runtime error occurs
- **WHEN** the API call or event stream reports an error
- **THEN** the checklist and error area expose the failure without hiding the transcript or prior events
