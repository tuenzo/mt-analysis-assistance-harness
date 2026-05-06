## Context

The repository already has a working category-day panel and full pipeline. A local `promo-causal-analysis` skill contains stronger method guidance and scripts for LocalGap, GPS response, uplift prioritization, and descriptive stats. The backend cannot rely on those scripts directly at runtime because they live in a user skill directory and require optional dependencies that are not installed in this backend.

## Goals / Non-Goals

**Goals:**

- Bring the backend modules closer to the skill method contract.
- Keep the full pipeline action sequence and artifact paths stable.
- Provide explicit method status and downgrade warnings instead of presenting thin data as strong causal evidence.
- Keep implementation local to the isolated branch and backend analysis modules.

**Non-Goals:**

- No new frontend experience in this change.
- No hard dependency on statsmodels, scipy, or sklearn.
- No claim of clean causal identification when input data cannot support it.

## Decisions

1. Use pandas/numpy implementations rather than importing the skill scripts.

   The skill scripts are useful references, but they are outside the repo and assume optional libraries. Reimplementing the core logic inside backend modules keeps deployment self-contained.

2. Treat LocalGap as the main increment layer.

   The upgraded LocalGap will create an enriched panel with row-level local baselines and local_gap. GPS and uplift will read this enriched panel when present.

3. Use time-safe folds for uplift.

   Uplift ranking will train on earlier dates/months and score later periods rather than random row splits. If folds or treatment variation are too thin, the module will return `limited` with warnings.

4. Keep existing artifact names.

   `diagnostics_result.json`, `localgap_result.json`, `gps_uplift_result.json`, `uplift_result.json`, and `category_action_recommendations.csv` remain stable so existing frontend/report code does not break.

## Risks / Trade-offs

- [Risk] Without statsmodels, regression diagnostics are lighter. → Mitigation: use robust numpy least squares plus explicit support/coverage warnings.
- [Risk] Thin sample data can still produce numeric outputs. → Mitigation: mark method status as `limited` and include downgrade reasons.
- [Risk] Existing reports may not use new fields yet. → Mitigation: preserve existing top-level keys and add richer metadata.
