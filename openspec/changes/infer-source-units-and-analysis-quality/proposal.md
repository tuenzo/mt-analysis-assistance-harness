## Why

Real-data runs currently infer display units in the frontend and can present a seven-day smoke-test panel as if it produced actionable promotion strategy. This creates two failures: GMV values may be labeled with the wrong base unit, and weak LocalGap/uplift evidence may be shown as confident recommendations.

## What Changes

- Infer amount-unit metadata from the raw order table mappings during panel build and persist it in `.analysis/panel_summary.json`.
- Treat missing explicit unit markers as "source GMV unit not declared" instead of guessing yuan/ten-thousand yuan in the frontend.
- Add analysis-readiness and LocalGap quality gates for short date coverage, sparse activity rows, weak baselines, and missing attribution terms.
- Propagate limited-evidence status into latest-result/report metadata and dashboard recommendation grouping.
- Update reports and project surfaces to display source units and limited-evidence caveats.

## Capabilities

### New Capabilities
- `source-unit-and-quality-gates`: Defines source-unit provenance and limited-evidence handling for real analysis outputs.

### Modified Capabilities
- `real-result-project-surfaces`: Project surfaces continue to read real artifacts, now including unit and quality metadata.

## Impact

- Backend: panel builder, LocalGap summarizer, result aggregation, report renderer.
- Frontend: dashboard summary adapter, dashboard renderer formatting, recommendation grouping.
- Validation: backend targeted tests, frontend lint/build, rerun real project pipeline, browser smoke check.
