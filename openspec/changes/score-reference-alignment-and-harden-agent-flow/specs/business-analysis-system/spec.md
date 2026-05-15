## ADDED Requirements

### Requirement: Full pipeline blocking gates
The backend SHALL stop the approved full pipeline after fatal source lineage, validation, or category-day panel failures instead of continuing into downstream models, dashboard charts, latest-result aggregation, or report generation.

#### Scenario: Validation failure stops downstream execution
- **WHEN** `analysis.run_full_pipeline` runs and `data.validate` returns `ok=false`
- **THEN** the job records the validation failure and does not execute panel build, analysis, dashboard chart, latest-result, or report steps

#### Scenario: Panel failure stops downstream execution
- **WHEN** `analysis.run_full_pipeline` runs and `panel.build_category_day` returns `ok=false`
- **THEN** the job records the panel failure and does not execute analysis, dashboard chart, latest-result, or report steps

### Requirement: Evidence-backed dashboard chart rendering
The backend SHALL refuse to render final dashboard PNG artifacts when the project has no usable analysis result artifacts.

#### Scenario: No analysis evidence exists
- **WHEN** `chart.render_dashboard` is called for a project without current diagnostics, LocalGap, PSM-DID, uplift, or latest-result artifacts
- **THEN** the tool returns `ok=false` with an actionable missing-evidence error and writes no dashboard chart files

### Requirement: Stable development database path
The backend SHALL resolve the default SQLite database path relative to the repository root instead of the current shell working directory.

#### Scenario: Backend starts from different working directories
- **WHEN** `APP_DATABASE_URL` is not set and the backend resolves its database URL from either the repository root or the `backend/` directory
- **THEN** both resolutions point to the same repository-root `business_analysis.db`

### Requirement: Raw source role protection
Data ingest SHALL not silently classify processed analysis outputs as raw order, exposure, or activity inputs.

#### Scenario: Processed panel appears in source directory
- **WHEN** source discovery sees a file such as `category_date_panel.csv` or a header set that already looks like a category-day panel
- **THEN** the file is classified as an existing panel candidate or unknown source and is not imported as `order_info` unless explicitly selected with a valid raw role and reason
