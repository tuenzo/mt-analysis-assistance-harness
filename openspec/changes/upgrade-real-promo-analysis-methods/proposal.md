## Why

The current full pipeline can run end to end, but several analysis modules remain simplified: diagnostics provide basic GMV comparisons, LocalGap uses a coarse global category baseline, PSM-DID is explicitly marked simplified, and GPS/Uplift is directional but not aligned with the richer promo-causal-analysis skill scripts. This change upgrades the isolated branch toward a real usable promotion analysis strategy without touching the MVP1 frozen framework.

## What Changes

- Upgrade GMV diagnostics to produce business-ready descriptive statistics, activity/non-activity tests when available, weekday/payday context, and data quality flags.
- Upgrade LocalGap to use historical same-weekday local baselines with recent/fallback windows, baseline quality, row-level enriched panel output, and channel decomposition based on excess exposure/discount/payday terms.
- Upgrade GPS/Uplift to use LocalGap-enriched outcomes, supported treatment ranges, GPS diagnostics, time-safe uplift folds, stability-based action buckets, and explicit downgrade warnings.
- Preserve current action names and artifact paths so the frontend and full pipeline continue to work.
- Avoid adding heavyweight new dependencies; use pandas/numpy and degrade gracefully when sample support is thin.

## Capabilities

### New Capabilities

- `real-promo-analysis-methods`: Production-leaning promotion diagnostics, LocalGap, GPS, and uplift method behavior for the isolated analysis branch.

### Modified Capabilities

- `business-analysis-system`: Existing analysis actions now return richer method diagnostics and downgrade metadata while preserving API shape.

## Impact

- Backend analysis pipeline modules under `backend/app/analysis/pipelines/`.
- Existing analysis tests plus new regression tests for richer outputs and downgrade behavior.
- Report/result downstream metadata may expose additional fields but keeps prior files and top-level keys.
