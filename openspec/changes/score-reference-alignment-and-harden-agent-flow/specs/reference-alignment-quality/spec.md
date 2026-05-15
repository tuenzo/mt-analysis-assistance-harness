## ADDED Requirements

### Requirement: Project lineage audit
The system SHALL expose a `quality.audit_lineage` business-analysis action that inspects project database records, workspace manifest state, source files, demo indicators, and result artifacts without changing source data or model outputs.

#### Scenario: Demo contamination is detected
- **WHEN** a project latest result or metadata indicates demo, mock, fixture, or seeded output
- **THEN** the lineage audit returns `ok=true` with a failing quality gate, cap reason `demo_contamination`, and evidence paths for the contaminated artifacts

#### Scenario: Missing source roles are detected
- **WHEN** a project lacks raw `order_info`, `exposure_info`, or `activity_timeline` inputs and has no explicitly valid prebuilt panel
- **THEN** the lineage audit reports the missing roles and marks the source lineage gate as failed

### Requirement: Reference alignment scoring
The system SHALL expose a `quality.score_reference_alignment` business-analysis action that writes a reference-trend alignment score artifact and a tabular diff artifact for the current project.

#### Scenario: Score is capped by hard gates
- **WHEN** lineage failure, demo contamination, missing source roles, or fatal pipeline failure with downstream artifacts is detected
- **THEN** the final 0-100 score is capped at the configured maximum and the score artifact lists every applied cap

#### Scenario: Score explains trend agreement
- **WHEN** result artifacts are available
- **THEN** the score artifact includes sub-scores for lineage, core trend, resource mechanism, GPS/uplift, and report claim calibration with pass/fail/detail rows

#### Scenario: Score artifacts are registered
- **WHEN** `quality.score_reference_alignment` completes
- **THEN** it returns artifacts for `.analysis/reference_alignment_score.json` and `artifacts/tables/reference_alignment_diffs.csv`
