## MODIFIED Requirements

### Requirement: Message-first data operations
All natural-language data operations SHALL enter through `POST /api/agent/messages` and the agent SHALL use the single `business_analysis` gateway tool for project data actions.

#### Scenario: User requests local data load
- **WHEN** a user asks to load CSV data from a local path or saved data source
- **THEN** the agent does not call project ingest APIs directly
- **AND** the agent does not read source files with built-in filesystem tools
- **AND** the agent uses `data.discover_source_files` before `data.ingest`
- **AND** `data.ingest` uses explicit `selected_files` chosen from discovery output
