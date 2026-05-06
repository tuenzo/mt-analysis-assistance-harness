## ADDED Requirements

### Requirement: Realistic GMV Diagnostics
The system SHALL produce descriptive GMV diagnostics that report activity/non-activity comparisons, cyclical context, statistical test availability, and data quality warnings.

#### Scenario: Diagnostics run on panel
- **WHEN** `analysis.run_diagnostics` runs on a valid category-day panel
- **THEN** the output includes GMV trend, category concentration, activity comparison, payday/weekday context, method status, and warnings

### Requirement: LocalGap Main Increment Layer
The system SHALL compute LocalGap using historical non-activity observations matched by category and weekday, with recent and fallback windows.

#### Scenario: LocalGap creates enriched panel
- **WHEN** `analysis.run_localgap` runs on a valid category-day panel
- **THEN** it writes `.analysis/localgap_result.json` and `data/processed/localgap_enriched_panel.csv`
- **AND** the result reports baseline quality, coverage, category decomposition, and downgrade warnings

### Requirement: GPS Dose Response
The system SHALL estimate directional dose-response curves over supported treatment ranges using LocalGap as the preferred outcome.

#### Scenario: GPS returns diagnostics
- **WHEN** `analysis.run_gps_uplift` runs after LocalGap
- **THEN** the GPS result includes supported treatment range, overlap quality, curve shape, warnings, and evidence artifact paths

### Requirement: Time-Safe Uplift Prioritization
The system SHALL assign uplift action buckets using time-safe validation folds when the panel has enough time coverage and treatment variation.

#### Scenario: Uplift returns stable buckets
- **WHEN** enough folds and variation exist
- **THEN** the uplift output includes category-level scores, fold counts, stability, action buckets, and recommendation rows

#### Scenario: Uplift downgrades thin samples
- **WHEN** folds or treatment variation are too thin
- **THEN** the uplift output is marked `limited` and includes explicit downgrade warnings
