## Requirements

### Requirement: Discover-First Autonomous Data Load
The system SHALL guide agent-run natural-language data-load requests through a controlled discover-first workflow before importing files.

#### Scenario: Valid local data source
- **WHEN** a user asks the assistant to load data from a local directory
- **THEN** the assistant calls `business_analysis` action `project.get_state`
- **AND** calls `data.discover_source_files`
- **AND** calls `data.ingest` with explicit `selected_files` containing `source_path`, `role`, and `reason`
- **AND** follows with `schema.infer` and `data.validate`
- **AND** the final answer reports data load as complete only when validation succeeds

### Requirement: Recoverable Partial Data Load
The system SHALL treat partial data load as a diagnostic state rather than a silent endpoint.

#### Scenario: Missing or unclassifiable files
- **WHEN** discovery or ingest cannot identify the required CSV roles
- **THEN** the assistant explains which files were discovered, which were skipped or left unknown, and why
- **AND** proposes concrete user actions such as adding missing CSV files, renaming files, correcting headers, or choosing a different source directory

#### Scenario: Validation failure after import
- **WHEN** imported data fails `data.validate`
- **THEN** the assistant includes validation issues from the tool result
- **AND** asks the user for the minimum needed correction instead of claiming data load is complete

### Requirement: Mock Runtime Demonstrates Multi-Tool Skeleton
The mock runtime SHALL demonstrate the same controlled tool-call shape used by the real SDK for MVP validation.

#### Scenario: Mock data-load request
- **WHEN** the runtime provider falls back to mock and the user asks to load data
- **THEN** the mock adapter emits sequential tool calls for `project.get_state`, `data.discover_source_files`, `data.ingest`, `schema.infer`, and `data.validate`
- **AND** each call includes the payload required for the message runtime to execute it through the gateway
