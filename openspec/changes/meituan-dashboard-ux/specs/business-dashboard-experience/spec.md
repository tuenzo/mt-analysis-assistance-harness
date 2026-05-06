## ADDED Requirements

### Requirement: Business-first dashboard summary
The frontend SHALL present a result dashboard centered on campaign business interpretation, including before/during/after campaign metrics, decision recommendations, conclusions, DID evaluation, and uplift quadrant strategy.

#### Scenario: User opens result dashboard after analysis
- **WHEN** a user opens the project dashboard
- **THEN** the dashboard shows a concise campaign snapshot with pre-campaign, in-campaign, and post-campaign metrics
- **AND** it shows decision recommendations and conclusions above lower-priority operational details

### Requirement: DID evaluation visibility
The frontend SHALL display DID evaluation results with effect direction, incremental value, confidence or significance context, and a plain-language interpretation.

#### Scenario: User reviews causal evidence
- **WHEN** DID evaluation data is available or represented by the MVP analysis snapshot
- **THEN** the dashboard shows the DID estimate, baseline comparison, confidence/significance cue, and a conclusion about whether the campaign appears incremental

### Requirement: Uplift quadrant strategy
The frontend SHALL display the uplift strategy quadrants Persuadables, Sure Things, Lost Causes, and Do Not Disturb with category or segment counts, business meaning, and next-action guidance.

#### Scenario: User scans uplift strategy
- **WHEN** a user reviews the uplift section
- **THEN** each quadrant is visible with its strategic meaning and recommended treatment
- **AND** the Persuadables quadrant is visually emphasized as the main targeting opportunity

### Requirement: Meituan yellow theme
The frontend SHALL use a Meituan-inspired yellow theme for the application shell, active navigation, primary actions, key badges, and dashboard highlights while keeping content panels readable.

#### Scenario: User navigates project workspace
- **WHEN** a user views any project page
- **THEN** the shell uses yellow visual identity consistently
- **AND** content panels retain sufficient contrast for scanning metrics, charts, and recommendations

### Requirement: Agent model label
The agent command center SHALL display the configured model name used by the runtime, with a Meituan model fallback when runtime metadata is not exposed.

#### Scenario: User opens agent command center
- **WHEN** a user views the agent command center
- **THEN** the page shows a visible model label near the assistant identity or command header
- **AND** the label does not alter the message-first input flow

### Requirement: Analysis-first navigation
The frontend SHALL simplify project navigation around the user's core workflow of data preparation, agent analysis, result dashboard browsing, and review/export surfaces.

#### Scenario: User follows primary workflow
- **WHEN** a user enters a project workspace
- **THEN** the navigation makes Data Intake, Agent Analysis, and Dashboard the primary path
- **AND** Timeline, Reports, and Memory Review remain accessible as supporting review surfaces
