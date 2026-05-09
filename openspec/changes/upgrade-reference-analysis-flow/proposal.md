## Why

The current harness has a working analysis loop, but several analytical modules remain lighter than the reference report and reference skills: PSM-DID is simplified, increment decomposition is not yet LMDI-grade, GPS/uplift lacks the full heterogeneity and quadrant outputs, and user-week HMM exists only in the reference skill. This change upgrades the system from "pipeline can run" to a reference-aligned promotion analysis engine while preserving the local-first MessageRuntime and single `business_analysis` gateway architecture.

## What Changes

- Upgrade existing flow modules to reference quality:
  - strengthen PSM-DID around resource-lift treatment, matched controls, balance diagnostics, event-window summaries, and placebo/pretrend diagnostics when data supports them;
  - enrich LocalGap with non-sparse sample metadata, counterfactual component baselines, and LMDI-style order/AOV contribution outputs;
  - extend GPS/uplift outputs with exposure and discount curves, heterogeneity slices, rank curves, and marketing quadrant summaries.
- Add report-PDF-aligned capabilities that are not currently in the standard flow:
  - TWFE-style resource mechanism regressions for GMV, order volume, and AOV/log-AOV;
  - exposure-level conversion-on-discount diagnostics;
  - report synthesis ordered around the reference report logic.
- Add reference-skill-only capability interfaces without initially inserting them into the standard full pipeline:
  - user-week panel construction;
  - Gaussian HMM state-path analysis;
  - state-based customer strategy artifacts.
- Later integrate the stage-3 interfaces into the standard flow behind explicit method-status and downgrade controls.
- Ensure agent dialogue analysis inherits the backend Python virtual environment so model-driven analysis commands and diagnostics do not fall back to global Python.
- Keep all public actions routed through the single `business_analysis(project_id, action, payload, reason)` gateway.

## Capabilities

### New Capabilities

- `reference-promo-analysis-flow`: Reference-aligned promotion analysis flow covering upgraded PSM-DID, LocalGap/LMDI, TWFE mechanism diagnostics, GPS/uplift heterogeneity, staged HMM interfaces, and report synthesis order.

### Modified Capabilities

- `business-analysis-system`: Standard full-pipeline behavior changes from the current lightweight sequence to a staged reference-aligned sequence while preserving existing action names and artifact compatibility.

## Impact

- Backend analysis modules under `backend/app/analysis/pipelines/`.
- Tool registry and schema enum for any new actions.
- Full pipeline orchestration in `backend/app/jobs/pipeline_runner.py`.
- Report/result aggregation in `backend/app/reports/` and `backend/app/tools/result_tools.py`.
- Backend pytest coverage in `backend/app/tests/`.
- No frontend changes are required for the first stage unless new artifacts need explicit display support.
