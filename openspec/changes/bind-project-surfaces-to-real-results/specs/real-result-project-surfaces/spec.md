## ADDED Requirements

### Requirement: Normal project surfaces use real workspace results
For non-showcase projects, frontend result surfaces SHALL source analysis dates, KPI values, categories, LocalGap decomposition, and recommendations from project workspace artifacts when those artifacts exist.

#### Scenario: User opens dashboard after a real pipeline run
- **WHEN** `.analysis/latest_result.json` and `.analysis/panel_summary.json` exist for the project
- **THEN** the dashboard time range is derived from the real panel date range
- **AND** KPI cards are derived from real diagnostics, LocalGap, and recommendation data
- **AND** category charts use real category names from the analysis artifacts

### Requirement: Missing results do not show demo values
For non-showcase projects, frontend surfaces SHALL NOT display demo snapshot dates, categories, KPI values, or recommendations when real project artifacts are missing.

#### Scenario: User opens a project before analysis
- **WHEN** the project has no real analysis result artifacts
- **THEN** dashboard and Agent result snapshots show a pending/empty state
- **AND** they do not show demo dates, demo categories, or demo KPI values

### Requirement: Agent inspector mirrors real result summary
The Agent analysis page SHALL use the same real-result summary model as the dashboard for its project context and result snapshot.

#### Scenario: User checks Agent side panel after analysis
- **WHEN** real panel and latest-result artifacts exist
- **THEN** the Agent side panel shows the real data period and real KPI snapshot
- **AND** it does not fall back to hard-coded demo project context values

### Requirement: Showcase demo remains isolated
The curated Keemart showcase SHALL remain isolated from normal project result loading.

#### Scenario: User opens the showcase project
- **WHEN** the project id matches the showcase route
- **THEN** the showcase dashboard, overview, Agent simulation, and memory demo continue using the curated showcase data
- **AND** normal project real-result loading does not alter the showcase output
