## ADDED Requirements

### Requirement: Implement GPS and uplift analysis
The system SHALL produce deterministic non-stub GPS/uplift outputs from an existing category-day panel.

#### Scenario: GPS uplift analysis succeeds
- **WHEN** `business_analysis` runs `analysis.run_gps_uplift` after `panel.build_category_day`
- **THEN** the tool writes `.analysis/gps_uplift_result.json` and `.analysis/uplift_result.json`
- **AND** `uplift_result.json` has `method_status` of `implemented` or `limited`, never `stub`
- **AND** the output contains dose-response curves, uplift ranking, segment recommendations, warnings, and evidence artifact paths

#### Scenario: Strategy recommendations are generated
- **WHEN** GPS/uplift outputs contain category-level ranking
- **THEN** the system writes `artifacts/tables/category_action_recommendations.csv`
- **AND** each row contains category, action, reason, guardrail, and evidence fields suitable for report generation

#### Scenario: Thin support is downgraded
- **WHEN** the panel has too few categories, dose levels, or activity rows for stable uplift
- **THEN** the output remains deterministic but sets `method_status` to `limited`
- **AND** warnings clearly state that recommendations are directional and require business review
