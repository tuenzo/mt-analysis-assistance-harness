## Updated Reference Report Gap Audit

This is a planning-only audit. It records where the current system differs from the updated `参考报告pdf/business_analysis_report.pdf` and `参考报告pdf/参考skills.md`. No implementation is included in this change yet.

## Backend Method Gaps

### 1. Panel Builder

Current strengths:

- Accepts the reference raw columns through aliases such as `dt`, `stat_pay_user_id`, `stat_pay_main_order_id`, `category_name_cn`, `base_sku_id`, `sku_sale_amt`, `biz_total_discount_amt`, `view_uv`, and `buy_uv`.
- Builds a balanced category-day panel and already exposes compatibility fields such as `gmv`, `order_count`, `discount_amount`, `view_uv`, `buy_uv`, `conversion_rate`, `weekday`, `month`, and payday-related fields.

Updated-report gaps to plan:

- Add a structured raw-table audit to `panel_summary.json`: date ranges by table, activity-date coverage, duplicate aggregation checks, SKU-category mapping coverage, exposure SKU unmapped share, and mapping conflict count.
- Emit reference aliases without breaking existing consumers: `sku_sale_amt`, `sku_sale_num`, `biz_total_discount_amt`, `order_cnt`, `order_line_cnt`, `order_user_cnt`, `order_sku_cnt`, `gross_sale_amt`, `has_order`, `has_exposure`, `exposure_sku_cnt`.
- Add model-ready fields: `discount_rate_for_model`, `discount_rate_pp`, `aov`, `net_unit_price`, `conversion_per_10k_uv`, `log_gmv`, `log_order_cnt`, `log_aov`, `log_view_uv`, `day_of_month`, `day_of_week`, `dist2pay`, `dist2pay_sq`, `is_payday_window`.
- Add stable campaign segmentation: `activity_window`, `activity_day_index`, and `activity_stage` early/middle/late.

Priority: highest, because downstream report sections and diagnostics depend on these fields.

### 2. Descriptive Diagnostics

Current strengths:

- Produces GMV trend, activity-vs-non-activity summary, payday overlap, weekday context, category concentration, warnings, and non-causal interpretation rules.

Updated-report gaps to plan:

- Expand activity-vs-non-activity comparison beyond GMV to orders, AOV, discount rate, exposure UV, buy UV, and conversion.
- Add report slices by month, activity name, and category size group in addition to weekday.
- Add explicit `metric_activity_comparison` rows that can feed report tables and dashboard badges.
- Keep statistical tests lightweight unless dependencies are added; use available approximate tests and label them descriptive.

Priority: high, because the updated PDF starts causal interpretation only after this broader descriptive context.

### 3. LocalGap / LMDI

Current strengths:

- LocalGap already uses historical non-activity same-weekday/fallback baselines.
- It emits a non-sparse sample summary, component baselines (`cf_order_count`, `cf_aov`, `cf_component_gmv`), monthly decomposition, category decomposition, and additive LMDI for overall/month/category.

Updated-report gaps to plan:

- Add compatibility aliases expected by the reference skill: `cf_order_cnt`, `cf_sku_sale_amt`, and activity-stage/window fields in enriched output when present.
- Expand LMDI summary levels to activity window, activity stage, activity-by-stage, category size group, exposure level, and payday vs non-payday where panel fields exist.
- Optionally expose conventional processed files such as non-sparse and counterfactual panels, while preserving existing `localgap_enriched_panel.*`.
- Ensure retained GMV share and dropped-category reasons are visible enough for report appendix/caveats.

Priority: high, because LocalGap remains the main increment accounting layer.

### 4. Mechanism And Conversion Diagnostics

Current strengths:

- Actions and result sources already exist for mechanism regression and conversion diagnostics.
- Result index/report helpers already know about `mechanism` and `conversion`.

Updated-report gaps to plan:

- Audit whether mechanism output separately covers order volume, log AOV, log GMV, exposure, discount, interaction, and payday controls.
- Audit whether conversion diagnostics expose low/mid/high exposure tiers, `conversion_per_10k_uv`, and net conversion/order-volume context.
- Strengthen wording so mechanism results explain channels and do not replace LocalGap increment accounting.

Priority: medium-high, after panel fields and LocalGap aliases are stable.

### 5. User Week / HMM

Current strengths:

- User-week panel and HMM state-path actions exist and are wired into report/result sources.
- The current implementation produces deterministic quantile states and transition summaries with limited method status.

Updated-report gaps to plan:

- Move from three proxy states (`dormant_or_light`, `active`, `core`) to four report-aligned states H0-H3.
- Add RFM-style weekly fields and balanced user-week support: purchase rate, weekly GMV, orders, items, category count, discount dependency, recency/activity context.
- Emit a four-by-four transition matrix, state profile table, representative paths, and dynamic marketing actions.
- Keep `method_status=limited` or similar until a true Gaussian HMM dependency is introduced.

Priority: medium, because it is important for the updated PDF but should follow category-level method contract fixes.

## Report And Frontend Display Gaps

### 1. Report Renderer

Current strengths:

- Generated report already collects diagnostics, PSM-DID, LocalGap, mechanism, conversion, user-week/HMM, and uplift artifacts.
- It writes metadata, plan JSON, evidence index, sections, limitations, and recommended follow-ups.

Updated-report gaps to plan:

- Reorder or relabel sections to match the updated Chinese report story: data/framework, PSM-DID causal direction, increment/mechanism decomposition, GPS/uplift allocation, user hidden states, harness application, recommendations, appendix/balance diagnostics.
- Add appendix-style references to PSM balance/pretrend and method-status caveats when available.
- Keep the renderer deterministic and evidence-backed; do not aim for visual PDF reproduction in this pass.

Priority: medium, after backend artifact fields are stable.

### 2. Dashboard / Existing Result Display

Current strengths:

- The dashboard already has KPI cards, Pareto, LocalGap waterfall, trend comparison, strategy quadrants, recommendation groups, filter controls, drill-down, and export affordance.
- The page already loads project state, artifact list, and latest report.

Updated-report gaps to plan:

- `buildDashboardSummary` currently relies on static/demo-style summary data rather than mapping updated artifacts into dashboard sections.
- Important updated-report evidence is likely missing or under-visible: panel quality/audit, PSM balance/pretrend, mechanism/conversion diagnostics, HMM state path, and method-status caveats.
- First-pass frontend work should avoid major page-function changes. Prefer small visibility upgrades: artifact-backed section labels, status badges, caveat notes, links to report/artifacts, and better grouping of existing cards.

Priority: after backend artifacts and report metadata expose the needed fields.

## Recommended Implementation Order After Approval

1. Backend panel audit and reference field aliases.
2. Backend descriptive diagnostics multi-metric/slice outputs.
3. LocalGap/LMDI aliases and summary levels.
4. User-state H0-H3 artifact contract.
5. Mechanism/conversion audit fixes if gaps remain after fields are available.
6. Report renderer section/order/caveat alignment.
7. Dashboard light-touch result visibility upgrades only where artifacts are currently hidden.

Each implementation slice should have focused tests and a small commit. Frontend build should run only after frontend files are touched.
