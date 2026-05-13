## Why

Real analysis projects were still showing frontend snapshot/demo values on business-facing surfaces after the backend had generated true workspace artifacts. This made the UI appear to use mock analysis, with mismatched campaign dates, category names, KPI values, and recommendations.

## What Changes

- Bind the normal project dashboard to `.analysis/latest_result.json` and `.analysis/panel_summary.json` instead of frontend-local snapshot values.
- Keep the independent Keemart showcase path isolated so its curated report demo still uses its own demo data.
- Reuse the same real-result summary model in the Agent side panel for project context and KPI snapshot.
- Remove misleading fallback metrics from generic dashboard drilldowns, artifact cards, header placeholders, and campaign snapshot helpers.
- Treat missing real artifacts as a pending/empty state, not as permission to display demo KPI values.

## Capabilities

### New Capabilities
- `real-result-project-surfaces`: Defines real artifact sourcing for normal project dashboard, Agent inspector, and report-adjacent project surfaces.

### Modified Capabilities
- None.

## Impact

- Affected frontend modules: project dashboard route, dashboard data adapter, result dashboard renderer, Agent analysis page, header, and legacy campaign snapshot helpers.
- Affected validation: frontend lint/build plus browser checks for real project dashboard, Agent panel, and report page.
- Backend API contract is unchanged; the frontend uses the existing artifact-content-by-path endpoint.
