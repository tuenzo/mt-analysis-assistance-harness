## ADDED Requirements

### Requirement: Evidence-Backed Report Rendering

`report.generate` SHALL render a Markdown report from a structured backend report plan.

#### Scenario: Results and charts are available

- **GIVEN** a project workspace has latest analysis results and chart artifacts
- **WHEN** `report.generate` runs
- **THEN** it writes `reports/report.md`
- **AND** the report contains planned sections with purpose, evidence, assumptions or limitations, and recommended follow-up
- **AND** the tool result includes additive metadata describing the report plan and evidence artifacts

#### Scenario: Some evidence is missing

- **GIVEN** a project workspace has partial analysis results
- **WHEN** `report.generate` runs
- **THEN** it still writes a report
- **AND** missing evidence is named as a limitation
- **AND** follow-up tool calls are suggested in metadata or report text

### Requirement: Compatible Result and Chart Metadata

Chart and latest-result tools SHALL add metadata that helps the agent explain provenance without removing existing response fields.

#### Scenario: Chart render succeeds

- **GIVEN** a chart can be rendered from an analysis result file
- **WHEN** `chart.render` completes
- **THEN** the chart JSON preserves existing plotting fields
- **AND** includes metadata for source files, interpretation, limitations, and recommended follow-up

#### Scenario: Latest results are aggregated

- **GIVEN** one or more analysis result files exist
- **WHEN** `result.get_latest` runs
- **THEN** `.analysis/latest_result.json` remains keyed by result name
- **AND** `.analysis/latest_result_index.json` describes sources, result statuses, evidence coverage, and recommended next actions

