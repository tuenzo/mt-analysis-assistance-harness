## Overview

The Keemart showcase is implemented as an isolated frontend route branch under the real project workspace URL:

```text
/projects/keemart-demo/agent
/projects/keemart-saudi-promo-review/agent
/projects/keemart-demo/dashboard
/projects/keemart-saudi-promo-review/dashboard
```

This preserves the real application shell, sidebar, header, route hierarchy, Tailwind styling, Agent workspace components, and dashboard rendering model while preventing the showcase branch from touching production runtime state.

## Data

Report-derived constants are stored in a frontend feature module:

```text
frontend/src/features/demo/keemart-demo-data.ts
```

The data includes:

- Observation window and sample sizes.
- PSM-DID headline results.
- Actual GMV, counterfactual GMV, net increment, and factor decomposition.
- GPS/Uplift resource response findings.
- Uplift quadrant examples and HMM user state summaries.
- Presenter script and Agent tool-call transcript.

## Agent Flow

The Keemart Agent flow is implemented inside the normal `AgentAnalysisPage`:

- Uses the same header, quick prompt row, conversation stream, message composer, execution plan, tool-call cards, thread card, and side inspector as ordinary projects.
- Replaces the API-backed send path only when the route is the Keemart project branch.
- Clicking suggested inputs appends normal user messages, `business_analysis` tool-call cards, progress thoughts, artifacts, and assistant answers.
- Links to the result dashboard route.

No backend Agent message API, external SSE stream, database mutation, or workspace mutation is used for the Keemart project branch.

## Dashboard Demo

`KeemartDemoDashboardPage` passes report-backed `DashboardSummary` data into the existing `ResultDashboardPage` component.

Small optional props are added to `ResultDashboardPage` so demo routes can display the correct report time range and default filters without affecting normal dashboards.

## Isolation

Route-level branching and an internal `AgentAnalysisPage` data-source branch are the only integration points:

- `/projects/keemart-demo/agent` and `/projects/keemart-saudi-promo-review/agent` render the normal Agent workspace with Keemart report-backed local events.
- `/projects/keemart-demo/dashboard` renders the frontend-only report dashboard.
- All other `project_id` values continue to use the existing API-backed Agent and dashboard.
