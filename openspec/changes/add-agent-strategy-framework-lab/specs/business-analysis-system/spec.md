## ADDED Requirements

### Requirement: Strategy Actions Through Business Analysis Gateway
The system SHALL expose model-led strategy design only through the existing `business_analysis(project_id, action, payload, reason)` tool gateway.

#### Scenario: Strategy action uses single tool gateway
- **WHEN** the model creates a strategy blueprint, flow design, or backend change proposal
- **THEN** it MUST call the existing `business_analysis` tool with a `strategy.*` action
- **AND** the gateway MUST validate the action, payload, project id, permission level, and audit log entry before execution

#### Scenario: No additional external custom tool
- **WHEN** strategy lab capability is enabled
- **THEN** the system MUST NOT expose a second custom MCP tool for backend framework editing
- **AND** all strategy lab work remains visible as normal business_analysis tool calls in the event stream

### Requirement: Strategy Action Permission Boundary
The system SHALL treat strategy lab actions as workspace-modifying design operations that require controlled persistence but not external sync.

#### Scenario: Strategy actions persist only project-local artifacts
- **WHEN** a strategy action succeeds
- **THEN** the gateway MUST persist only project-local strategy lab artifacts
- **AND** the action MUST NOT write to user-level memory, external services, or unrelated workspaces

#### Scenario: Strategy action audit log
- **WHEN** a strategy action is requested
- **THEN** the tool call log MUST include action name, payload hash, reason, project id, status, and created artifact references
