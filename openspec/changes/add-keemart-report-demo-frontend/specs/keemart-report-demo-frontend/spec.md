## ADDED Requirements

### Requirement: Real Frontend Showcase Route

The frontend SHALL provide an isolated Keemart project route that uses the existing project workspace shell, navigation, and Agent analysis components.

#### Scenario: Open Agent showcase

- **WHEN** the user opens `/projects/keemart-demo/agent`
- **THEN** the frontend SHALL render the normal Agent analysis workspace with Keemart report-backed suggested inputs, messages, execution plan, tool-call cards, and side inspector
- **AND** the page SHALL NOT call backend Agent message APIs or open SSE streams.

#### Scenario: Open dashboard showcase

- **WHEN** the user opens `/projects/keemart-demo/dashboard`
- **THEN** the frontend SHALL render the existing dashboard experience with Keemart report-derived data
- **AND** the page SHALL NOT call project state, artifact, or report APIs.

### Requirement: Report-Based Demo Data

The Keemart showcase SHALL use analysis results extracted from the final report as its display baseline.

#### Scenario: Show core effect metrics

- **WHEN** the dashboard loads
- **THEN** it SHALL show actual GMV `1,334,767.68`, counterfactual GMV `987,564.34`, net increment `347,203.34`, and lift `35.16%` in the result narrative or KPI surface.

#### Scenario: Show strategy conclusions

- **WHEN** the Agent flow or dashboard recommendations are displayed
- **THEN** they SHALL communicate that exposure is the broader growth engine, discounts are precision conversion tools, and the payday window should guide resource timing.
