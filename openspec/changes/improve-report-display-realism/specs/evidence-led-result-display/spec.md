## ADDED Requirements

### Requirement: Show evidence chain on dashboard
The Dashboard SHALL display key metrics, pipeline/result coverage, generated artifacts, limitations, and recommended next actions in a scan-friendly layout.

#### Scenario: Full results are available
- **WHEN** a project has report and artifact outputs
- **THEN** the Dashboard shows a KPI snapshot, evidence coverage, report highlights, and artifact links

#### Scenario: Results are incomplete
- **WHEN** a project lacks reports or charts
- **THEN** the Dashboard shows clear empty states and directs the user to run the next analysis step

### Requirement: Make reports reviewable
The Report Studio SHALL present generated Markdown with report metadata, section navigation, artifact references, and credibility cues.

#### Scenario: Latest report exists
- **WHEN** the user opens Report Studio
- **THEN** the page shows the latest report, source path, section outline, and quality cues without requiring raw file inspection

#### Scenario: Report is missing
- **WHEN** no report has been generated
- **THEN** the page explains the missing prerequisite and offers a refresh path
