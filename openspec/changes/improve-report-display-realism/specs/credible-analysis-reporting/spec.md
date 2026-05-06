## ADDED Requirements

### Requirement: Generate evidence-backed report plans
The system SHALL generate reports from an explicit report plan containing findings, supporting evidence, assumptions, limitations, and next actions.

#### Scenario: Report generation succeeds
- **WHEN** `business_analysis` runs `report.generate` after analysis results exist
- **THEN** the generated Markdown includes an executive summary, evidence overview, method notes, limitations, strategy recommendations, and artifact references

#### Scenario: Stub or weak methods are present
- **WHEN** a result file indicates stub, partial, or heuristic method status
- **THEN** the report clearly labels the confidence level and avoids overstating causality

#### Scenario: Default report language
- **WHEN** `report.generate` is called without an explicit language override
- **THEN** the generated Markdown report uses Chinese headings and business-facing narrative
- **AND** Dashboard and Report Studio report-review surfaces use Chinese labels, cues, and fallback states by default
- **AND** technical artifact paths and tool action names remain unchanged for traceability

### Requirement: Preserve source-of-truth boundaries
The system SHALL use backend result files and artifacts as the factual source for reports.

#### Scenario: Report cites analysis results
- **WHEN** report sections reference metrics or recommendations
- **THEN** those sections cite the result artifact or workspace file that provided the evidence

#### Scenario: Dashboard consumes report KPIs
- **WHEN** a generated report has `report_metadata.json`
- **THEN** `reports/latest` exposes a structured KPI summary for total GMV, LocalGap increment, and DID estimate
- **AND** Dashboard KPI cards prefer that structured summary before falling back to Markdown parsing

#### Scenario: Missing results
- **WHEN** report generation is requested before analysis results exist
- **THEN** the tool returns a structured error instead of fabricating conclusions
