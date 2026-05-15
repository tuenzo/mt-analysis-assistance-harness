## Why

Recent real agent runs produced analysis outputs that diverged sharply from the updated reference report because project lineage, source-table roles, demo fixtures, and downstream artifacts were not guarded before interpretation. We need a deterministic quality gate and reference-trend score so the agent can diagnose bad runs before it narrates them as business evidence.

## What Changes

- Add `quality.audit_lineage` and `quality.score_reference_alignment` actions under the existing single `business_analysis` gateway.
- Generate project-local quality artifacts: `.analysis/reference_alignment_score.json` and `artifacts/tables/reference_alignment_diffs.csv`.
- Add hard caps for lineage failure, demo/mock contamination, missing required source roles, and failed fatal pipeline steps with downstream artifacts.
- Make the approved full pipeline fail fast after blocking steps such as source lineage, data validation, and category-day panel build.
- Prevent static dashboard PNG generation when evidence artifacts are missing or invalid.
- Harden local DB resolution so the default SQLite path is stable relative to the repository root unless `APP_DATABASE_URL` is explicitly configured.
- Improve data ingest role inference so processed panels are not silently imported as raw order data.

## Capabilities

### New Capabilities

- `reference-alignment-quality`: Reference-report trend scoring, lineage audit, quality caps, and score artifact outputs.

### Modified Capabilities

- `business-analysis-system`: The standard analysis flow must run lineage/quality gates, stop on fatal source or panel failures, and prevent evidence-free dashboard/report outputs.

## Impact

- Backend tools, registry, permissions, pipeline runner, chart renderer, data ingest, database config, and report/result helpers.
- New backend tests under `backend/app/tests/`.
- No new public tool surface outside `business_analysis(project_id, action, payload, reason)`.
