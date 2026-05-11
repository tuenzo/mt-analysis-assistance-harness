## Why

The current standalone static mock does not demonstrate the actual Next.js workspace shell, project navigation, Agent analysis surface, or dashboard component structure. The Keemart showcase needs to live inside the real frontend while remaining isolated from production APIs, backend state, tests, and review data.

## What Changes

- Add a dedicated Keemart project branch inside the existing `/projects/[project_id]` frontend routes.
- Reuse the normal `AgentAnalysisPage` layout and components for the Keemart Agent flow, replacing only the data source and local event stream.
- Render a report-backed result dashboard using the existing dashboard component contract and data extracted from the final Keemart report.
- Keep all Keemart showcase data as frontend-only constants. Do not call backend APIs or mutate project state for the Keemart project branch.

## Impact

- Frontend-only implementation.
- No database, backend, workspace, or test fixture changes.
- Existing project routes keep their current API-backed behavior unless the project ID resolves to the Keemart showcase project.
