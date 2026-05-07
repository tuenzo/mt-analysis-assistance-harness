## ADDED Requirements

### Requirement: Result dashboard prioritizes interpretation
The system SHALL treat the result dashboard as the primary business interpretation surface for completed or in-progress campaign analysis, not merely a placeholder chart gallery.

#### Scenario: Analysis artifacts are browsed
- **WHEN** a user browses analysis results in the frontend
- **THEN** the dashboard prioritizes evidence, decisions, recommendations, and caveats derived from diagnostics, DID, LocalGap, GPS, and uplift outputs
- **AND** chart/table details support the interpretation rather than replacing it

### Requirement: Frontend preserves message-first analysis entry
The frontend SHALL keep natural-language analysis requests routed through the agent message entry while allowing dashboard and review pages to browse resulting state and artifacts.

#### Scenario: User asks for analysis
- **WHEN** a user submits a natural-language analysis request from the project workspace
- **THEN** the request goes through the agent message flow
- **AND** dashboard navigation only changes how results are browsed, not how analysis is initiated
