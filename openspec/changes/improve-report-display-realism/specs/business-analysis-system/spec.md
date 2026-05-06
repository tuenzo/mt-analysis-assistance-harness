## MODIFIED Requirements

### Requirement: Report generation produces credible business deliverables
The system SHALL generate reports that connect conclusions to workspace artifacts, explain method confidence, and separate observed evidence from causal interpretation.

#### Scenario: Agent generates a report
- **WHEN** the agent calls `business_analysis(action="report.generate")`
- **THEN** the backend writes `reports/report.md` with evidence-backed sections and returns a report artifact

#### Scenario: User reviews outputs
- **WHEN** the frontend loads Dashboard or Report Studio
- **THEN** the user can inspect metrics, artifacts, report sections, limitations, and next actions from the UI
