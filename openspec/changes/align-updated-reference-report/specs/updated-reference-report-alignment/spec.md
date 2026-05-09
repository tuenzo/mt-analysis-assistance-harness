## ADDED Requirements

### Requirement: Updated reference panel contract
The system SHALL build a report-ready category-day panel from the three raw reference tables while preserving existing pipeline compatibility fields.

#### Scenario: Raw table audit is included
- **WHEN** the panel builder reads order, exposure, and activity inputs
- **THEN** it records date ranges, SKU-category mapping coverage, mapping conflicts, activity-date coverage, and aggregation-level duplicate checks in the result summary

#### Scenario: Panel exposes model-ready fields
- **WHEN** `analysis.build_panel` completes
- **THEN** the panel includes compatibility fields such as `gmv` and `order_count` plus reference fields such as `sku_sale_amt`, `order_cnt`, `order_line_cnt`, `order_user_cnt`, `order_sku_cnt`, `gross_sale_amt`, `discount_rate_for_model`, `discount_rate_pp`, `aov`, `net_unit_price`, `conversion_per_10k_uv`, `log_gmv`, `log_order_cnt`, `log_aov`, `log_view_uv`, `dist2pay`, `dist2pay_sq`, and `is_payday_window`

#### Scenario: Activity windows are stable
- **WHEN** activity dates form one or more contiguous campaign windows
- **THEN** the panel labels activity rows with `activity_window`, `activity_day_index`, and `activity_stage` using stable early/middle/late thirds

### Requirement: Updated descriptive diagnostics
The system SHALL produce descriptive diagnostics that match the updated report's pre-causal context section.

#### Scenario: Multi-metric activity comparison
- **WHEN** diagnostics run on a category-day panel
- **THEN** the result compares activity and non-activity rows across GMV, orders, AOV, discount rate, exposure UV, buy UV, and conversion rate, with raw deltas labeled as descriptive rather than causal

#### Scenario: Context slices are available
- **WHEN** diagnostics have sufficient fields
- **THEN** the result includes summaries by month, weekday, activity name, and category size group when those slices are supported

### Requirement: Updated non-sparse and LMDI contract
The system SHALL expose non-sparse retained-sample and component counterfactual information needed by the updated report.

#### Scenario: Non-sparse retained sample is explicit
- **WHEN** LocalGap/LMDI runs
- **THEN** the result reports retained category count, dropped category count, retained row count, retained GMV share, and downgrade reasons for thin support

#### Scenario: Counterfactual component aliases are present
- **WHEN** counterfactual baselines are created
- **THEN** the enriched panel and summaries expose `cf_order_cnt`, `cf_aov`, `cf_sku_sale_amt`, and LMDI contribution fields without removing existing `cf_order_count` compatibility fields

#### Scenario: Report summary levels match the updated PDF
- **WHEN** LMDI summaries are computed
- **THEN** the result includes overall, month, activity window, activity stage, category, category size group, exposure level, and payday-window summaries when those fields are present

### Requirement: Four-state user path analysis
The system SHALL emit an H0-H3 weekly user state-path artifact matching the updated report narrative.

#### Scenario: H0-H3 state profile is available
- **WHEN** user-state analysis runs with sufficient order history
- **THEN** it returns four states H0, H1, H2, and H3 with purchase rate, weekly GMV, order count, item count, category count, share, and business interpretation

#### Scenario: Transition matrix and marketing actions are available
- **WHEN** at least two user weeks exist
- **THEN** the result includes a four-by-four state transition matrix, representative user paths, and state-based dynamic marketing actions

### Requirement: Updated report and display storyline
The system SHALL present analysis results in the updated PDF's evidence order for both generated reports and the dashboard.

#### Scenario: Generated report follows updated reference order
- **WHEN** a report is generated after the standard pipeline
- **THEN** the sections appear in the order data/framework, PSM-DID causal direction, increment/mechanism decomposition, GPS/uplift allocation, user hidden states, harness application, recommendations, and appendix/balance diagnostics

#### Scenario: Dashboard exposes updated analysis sections
- **WHEN** a user opens the result dashboard after artifacts exist
- **THEN** the display includes cards or sections for data quality, causal direction, increment attribution, resource allocation, user state path, and business application/recommendations
