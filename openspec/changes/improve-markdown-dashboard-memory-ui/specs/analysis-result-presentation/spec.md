## ADDED Requirements

### Requirement: Markdown Analysis Content Rendering

The frontend SHALL render analysis text that contains Markdown using a shared Markdown renderer.

#### Scenario: Assistant message contains a table

- **GIVEN** an assistant message contains a Markdown table
- **WHEN** the Agent Command Center displays the message
- **THEN** the table is rendered as a formatted table
- **AND** the message is not shown as raw Markdown text

#### Scenario: Memory content contains Markdown

- **GIVEN** a memory candidate or stored project memory contains Markdown headings, lists, or emphasis
- **WHEN** the Memory Review page displays the content
- **THEN** the content is rendered with readable Markdown formatting

### Requirement: Result-First Dashboard

The Dashboard SHALL show current analysis results directly instead of requiring the user to open a report first.

#### Scenario: Report exists

- **GIVEN** a project has a latest Markdown report
- **WHEN** the Dashboard loads
- **THEN** it displays key metrics, an executive snapshot, category results, and latest artifacts on the Dashboard page
- **AND** the user can still navigate to the full report

#### Scenario: Report does not exist

- **GIVEN** a project has no latest report
- **WHEN** the Dashboard loads
- **THEN** it displays available project state and artifacts
- **AND** it shows a clear empty state for report-derived results
