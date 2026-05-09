## ADDED Requirements

### Requirement: Stage 1 upgrades existing analytical modules
The system SHALL upgrade existing standard-flow analytical modules toward the reference report and reference skill contracts while preserving existing public action names and artifact compatibility.

#### Scenario: PSM-DID upgraded within existing action
- **WHEN** `business_analysis` executes `analysis.run_psm_did` on a category-day panel with exposure, discount, activity, and GMV fields
- **THEN** the result includes resource-lift treatment definitions, matched sample diagnostics, DID/event-window summaries, placebo or pretrend notes when feasible, and a method-status downgrade when support is insufficient

#### Scenario: LocalGap remains main increment layer
- **WHEN** the full pipeline computes increment accounting
- **THEN** LocalGap remains the primary increment artifact and any DID output is labeled directional support rather than final increment truth

#### Scenario: GPS and uplift produce allocation evidence
- **WHEN** `analysis.run_gps_uplift` runs after LocalGap
- **THEN** the result includes dose-response evidence, uplift ranking, recommendation buckets, warnings, and downgrade reasons when support is thin

### Requirement: Stage 2 adds report-PDF analytical layers
The system SHALL add analytical capabilities that are present in both the reference PDF logic and reference skills but not yet represented as first-class current-flow modules.

#### Scenario: Mechanism regression artifacts are available
- **WHEN** a project has a valid category-day panel or LocalGap-enriched panel
- **THEN** the backend can produce mechanism regression artifacts for GMV, order volume, and AOV or log-AOV using exposure, discount, interaction, and calendar controls where data supports them

#### Scenario: Conversion diagnostics by exposure tier are available
- **WHEN** conversion fields and exposure fields are present
- **THEN** the backend can produce conversion-on-discount diagnostics split by low, mid, and high exposure tiers instead of presenting only a pooled headline result

#### Scenario: Report synthesis follows reference analysis logic
- **WHEN** a report is generated after stage-2 artifacts exist
- **THEN** the report orders evidence as data/EDA, causal direction, increment/mechanism decomposition, GPS/uplift allocation, zero/downgrade checks, and business recommendations

### Requirement: Stage 3 exposes reference-skill-only interfaces
The system SHALL expose interfaces for analytical capabilities present in the reference skill but absent from the reference PDF without inserting them into the standard full pipeline in stage 3.

#### Scenario: User-week panel action exists outside standard flow
- **WHEN** `business_analysis` executes the user-week panel action
- **THEN** the backend validates raw order/activity inputs, writes a documented artifact or limited-status placeholder, and does not run it automatically in the standard full pipeline

#### Scenario: HMM state path action exists outside standard flow
- **WHEN** `business_analysis` executes the HMM state-path action
- **THEN** the backend returns model-selection/state-profile/transition/path artifact contracts or a limited-status result with clear missing-dependency or insufficient-data reasons

### Requirement: Stage 4 integrates stage-3 capabilities into the standard flow
The system SHALL integrate stage-3 capability interfaces into the standard analysis flow only after their artifact contracts and downgrade behavior are implemented.

#### Scenario: HMM integration is gated by data support
- **WHEN** the standard full pipeline reaches the user-state analysis step
- **THEN** the pipeline runs HMM only when required user-week inputs and dependencies are available, otherwise records a limited-status artifact without failing the main report

#### Scenario: Full pipeline remains auditable
- **WHEN** any stage-4 capability runs or downgrades
- **THEN** the job timeline includes tool start/finish events, artifact registration, method status, and warnings through the existing gateway/orchestrator path
