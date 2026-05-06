# Design

## Principles

- Keep `LocalGap` as the main increment accounting layer.
- Treat PSM-DID as directional support and expose diagnostics, not final truth.
- Use GPS as a continuous treatment response layer for scaling logic.
- Use uplift as ranking and allocation logic, not standalone causal proof.

## Implementation Shape

- Add `backend/app/analysis/pipelines/gps_uplift.py` as the shared real analysis script for:
  - dose-response curve generation for exposure and discount intensity,
  - category-level uplift ranking,
  - action bucket classification,
  - recommendation row generation.
- Update `analysis_run_gps_uplift` to call the script and write:
  - `.analysis/gps_uplift_result.json`,
  - `.analysis/uplift_result.json`,
  - `artifacts/tables/category_action_recommendations.csv`.
- Preserve the existing `uplift_result.json` name so report generation and `result.get_latest` remain compatible.
- Add focused pytest coverage using the existing panel fixtures.

## Guardrails

- If panel support is thin, return `method_status: limited` and include warnings.
- Do not call GPS/uplift causal proof. Use language such as response curve, ranking, and directional recommendation.
- Keep technical artifact paths and existing action names stable.
