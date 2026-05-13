## ADDED Requirements

### Requirement: Amount units come from source table metadata
The system SHALL derive amount display units from raw source table metadata or mapped source column names during panel build.

#### Scenario: Raw GMV column has no explicit unit marker
- **WHEN** the mapped GMV source column is `gmv`
- **THEN** `panel_summary.json` records the GMV unit as an undeclared source unit
- **AND** frontend and report surfaces label GMV values with the source-unit label rather than guessing a currency

#### Scenario: Raw GMV column has an explicit unit marker
- **WHEN** the mapped GMV source column includes an explicit unit marker such as `gmv_yuan`, `gmv_fen`, `gmv_usd`, or `gmv_sar`
- **THEN** `panel_summary.json` records the explicit unit label and provenance
- **AND** frontend and report surfaces use that label without magnitude-based conversion

### Requirement: Short or sparse analysis is downgraded
The system SHALL mark analysis outputs as limited when the data window, baseline support, or attribution support is insufficient for stable conclusions.

#### Scenario: Panel covers fewer than 14 days
- **WHEN** the category-day panel covers fewer than 14 distinct dates
- **THEN** panel summary includes a limited analysis-readiness status with a short-coverage reason
- **AND** downstream dashboard/report surfaces present results as smoke-test or limited evidence

#### Scenario: LocalGap lacks enough attribution support
- **WHEN** LocalGap can estimate total gap but cannot estimate exposure, discount, or payday model terms
- **THEN** LocalGap method status is limited
- **AND** channel-attribution and action recommendations are presented as small-scale validation rather than confident scaling advice

### Requirement: Real result surfaces respect quality gates
Frontend project surfaces SHALL use quality metadata from real artifacts to determine recommendation strength and explanatory copy.

#### Scenario: Latest result is limited
- **WHEN** latest results include limited panel or LocalGap quality metadata
- **THEN** dashboard recommendation groups do not classify categories as priority boost solely by uplift score
- **AND** the core conclusion includes a limited-evidence caveat
