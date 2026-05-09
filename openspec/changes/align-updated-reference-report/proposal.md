## Why

The reference PDF was updated on 2026-05-09 and now contains a more explicit report logic than the previous alignment target: raw-table audit, balanced category-day panel fields, non-sparse counterfactual/LMDI outputs, four-state user HMM, and an application-facing dashboard/report story. The current harness is close but still under-specifies several backend artifacts and does not yet present the updated report structure consistently in generated reports or the frontend result workspace.

## What Changes

- This change is planned first. Implementation will start only after the gap plan is reviewed.
- Backend planning starts from business-analysis method gaps rather than UI changes:
  - align the category-day panel contract with the updated reference skill/report, including SKU-category mapping audit, activity-window segmentation, payday controls, model-ready discount/exposure/conversion fields, and compatibility aliases;
  - upgrade descriptive diagnostics so raw activity-vs-non-activity comparisons cover GMV, orders, AOV, discount, exposure, buy UV, and conversion across overall, month, weekday, activity, and category-size slices;
  - strengthen LocalGap/LMDI outputs around non-sparse retained-sample reporting, counterfactual component aliases, activity stage/window summaries, and the updated decomposition levels used by the report;
  - upgrade the user-state layer from the prior limited three-state proxy to a four-state H0-H3 weekly state-path artifact matching the updated PDF narrative, while keeping method-status transparency when a true probabilistic HMM is not available.
- Report/display planning focuses on missing important result visibility and light presentation upgrades:
  - generated reports should follow the updated Chinese report logic: data framework, PSM-DID causal direction, increment/mechanism decomposition, GPS/uplift allocation, user hidden states, harness application, recommendations, and balance appendix;
  - the frontend result dashboard should reuse existing pages/components where possible, surfacing missing artifacts and method-status caveats without a large functional redesign.

## Capabilities

### New Capabilities

- `updated-reference-report-alignment`: Updated reference-report evidence contract covering panel fields, diagnostics slices, non-sparse/LMDI detail, four-state user HMM, report ordering, and presentation outputs.

### Modified Capabilities

- `business-analysis-system`: The standard analysis flow and report generation requirements change to follow the updated reference PDF and reference skill contracts.
- `shared-analysis-workspace-frontend`: The result dashboard must audit and lightly improve visibility of important updated-report results, without a broad page-function rewrite.

## Impact

- Backend analysis modules under `backend/app/analysis/pipelines/`.
- Pipeline orchestration and report/result aggregation under `backend/app/jobs/`, `backend/app/reports/`, and related tool result helpers when needed.
- Frontend result dashboard and shared API type handling under `frontend/src/`.
- Backend pytest coverage and frontend build validation.
- No new public tool surface outside the existing `business_analysis(project_id, action, payload, reason)` gateway.
