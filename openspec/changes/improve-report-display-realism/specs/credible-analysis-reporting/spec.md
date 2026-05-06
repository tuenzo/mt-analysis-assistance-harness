## ADDED Requirements

### Requirement: Generate evidence-backed report plans
The system SHALL generate reports from an explicit report plan containing findings, supporting evidence, assumptions, limitations, and next actions.

#### Scenario: Report generation succeeds
- **WHEN** `business_analysis` runs `report.generate` after analysis results exist
- **THEN** the generated Markdown includes an executive summary, evidence overview, method notes, limitations, strategy recommendations, and artifact references

#### Scenario: Stub or weak methods are present
- **WHEN** a result file indicates stub, partial, or heuristic method status
- **THEN** the report clearly labels the confidence level and avoids overstating causality

### Requirement: Preserve source-of-truth boundaries
The system SHALL use backend result files and artifacts as the factual source for reports.

#### Scenario: Report cites analysis results
- **WHEN** report sections reference metrics or recommendations
- **THEN** those sections cite the result artifact or workspace file that provided the evidence

#### Scenario: Missing results
- **WHEN** report generation is requested before analysis results exist
- **THEN** the tool returns a structured error instead of fabricating conclusions
