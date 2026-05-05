## ADDED Requirements

### Requirement: Infer source schema aliases
The system SHALL infer role-specific field mappings for order, exposure, and activity CSV files using known aliases before validation or panel build.

#### Scenario: English aliases are inferred
- **WHEN** an order CSV contains columns such as `pay_date`, `cat_name`, `pay_amount`, and `coupon_amount`
- **THEN** schema inference returns mappings for `date`, `category_name`, `gmv`, and `discount_amount`

#### Scenario: Compact dates are supported
- **WHEN** a source CSV contains dates like `20250927`
- **THEN** validation and panel build parse the values as normalized calendar dates

### Requirement: Build a balanced category-day panel
The system SHALL build a category-by-day panel covering every observed category and every date from the minimum to maximum source date.

#### Scenario: Missing category-day combinations are filled
- **WHEN** a category has no orders on a date inside the source date range
- **THEN** the panel includes that category-date row with zero metric values

#### Scenario: Activity windows are derived
- **WHEN** activity data provides either daily activity rows or start/end date ranges
- **THEN** the panel includes activity flags, payday phase, and pre/post activity window fields

### Requirement: Persist panel artifacts
The system SHALL persist panel output as JSON, CSV, and summary metadata under the project workspace.

#### Scenario: Panel build succeeds
- **WHEN** `business_analysis` runs action `panel.build_category_day`
- **THEN** the tool result includes artifacts for `category_day_panel.json`, `category_day_panel.csv`, and `panel_summary.json`

#### Scenario: Panel build cannot validate inputs
- **WHEN** required order, exposure, or activity fields cannot be inferred
- **THEN** the tool result fails with a structured validation error and does not write a partial panel
