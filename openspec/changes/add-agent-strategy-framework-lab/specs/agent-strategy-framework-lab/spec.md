## ADDED Requirements

### Requirement: Strategy Blueprint Artifact
The system SHALL allow the model to create a versioned analysis strategy blueprint artifact inside the project workspace.

#### Scenario: Create strategy blueprint
- **WHEN** the model calls `business_analysis` with action `strategy.design_blueprint` and a valid blueprint payload
- **THEN** the system writes a structured blueprint JSON file under `.analysis/strategy_lab/blueprints/`
- **AND** the tool result returns the strategy id, version, workspace-relative path, and summary

#### Scenario: Reject invalid strategy blueprint
- **WHEN** the model calls `strategy.design_blueprint` without required fields such as objective, decision questions, assumptions, or success criteria
- **THEN** the system rejects the action with a structured tool error
- **AND** no strategy lab artifact is written

### Requirement: Analysis Flow Artifact
The system SHALL allow the model to create a versioned analysis flow artifact that describes the proposed analysis stages, dependencies, inputs, outputs, and expected tool actions.

#### Scenario: Create analysis flow
- **WHEN** the model calls `business_analysis` with action `strategy.design_flow` and a valid flow payload
- **THEN** the system writes a structured flow JSON file under `.analysis/strategy_lab/flows/`
- **AND** the tool result returns the flow id, version, workspace-relative path, and ordered stage count

#### Scenario: Flow declares executable and proposed steps
- **WHEN** a flow stage maps to an existing backend action
- **THEN** the stage record MUST include that action name
- **AND** when a flow stage requires new backend behavior, the stage record MUST include a proposed backend change reference

### Requirement: Backend Change Proposal Artifact
The system SHALL allow the model to create a backend framework change proposal as an artifact, without directly editing backend source code.

#### Scenario: Create backend change proposal
- **WHEN** the model calls `business_analysis` with action `strategy.propose_backend_change` and a valid proposal payload
- **THEN** the system writes a structured proposal JSON file under `.analysis/strategy_lab/backend_changes/`
- **AND** the tool result identifies the affected modules, desired actions, risks, and review status

#### Scenario: Prevent direct source mutation
- **WHEN** the model includes raw source-file write instructions in a strategy proposal payload
- **THEN** the system stores them only as proposal text
- **AND** the system MUST NOT modify files outside the project workspace strategy lab directory

### Requirement: Strategy Lab Version Isolation
The system SHALL isolate all model-generated strategy lab artifacts from the stable MVP1 runtime behavior.

#### Scenario: Strategy lab files are workspace-local
- **WHEN** any strategy lab action succeeds
- **THEN** every created file is inside the current project's `.analysis/strategy_lab/` directory
- **AND** no backend source file, frontend source file, user-level memory, or other project workspace is modified

#### Scenario: Existing pipeline remains unchanged
- **WHEN** the user asks the agent to run the existing full analysis pipeline
- **THEN** the runtime uses the existing `analysis.run_full_pipeline` path
- **AND** strategy lab artifacts are not executed unless a strategy action is explicitly requested
