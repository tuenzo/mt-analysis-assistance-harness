## MODIFIED Requirements

### Requirement: MVP 1 data intake produces real panel outputs
The system SHALL turn uploaded or ingested order, exposure, and activity CSV files into validated workspace artifacts, including a real category-day panel built from source metrics rather than mock rows.

#### Scenario: Uploaded data advances to panel-ready state
- **WHEN** a project has valid `order_info`, `exposure_info`, and `activity_timeline` CSV files and the agent calls `business_analysis(action="panel.build_category_day")`
- **THEN** the workspace contains `data/processed/category_day_panel.json`, `data/processed/category_day_panel.csv`, and `.analysis/panel_summary.json`

#### Scenario: Existing downstream steps remain compatible
- **WHEN** diagnostics or LocalGap read the generated panel JSON
- **THEN** legacy-compatible fields such as `category`, `gmv`, `discount`, `exposure`, `is_activity`, and `is_payday` are present
