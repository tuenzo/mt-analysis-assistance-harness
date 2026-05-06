## Why

The current MVP frontend proves the architecture, but the product surface still feels like a scaffold rather than a business analysis workspace. Users need a simpler path from data intake to analysis interpretation, with the dashboard centered on campaign before/during/after evidence, DID results, uplift strategy quadrants, and concrete recommendations.

## What Changes

- Reframe the project UI around the core user flow: upload/prepare data, ask the agent to analyze, browse results, review reports/memory only when needed.
- Redesign the dashboard to show campaign pre/mid/post movement, decision recommendations, conclusions, DID evaluation, and uplift quadrant strategy.
- Apply a Meituan-inspired yellow visual theme across navigation, top surfaces, action controls, badges, and dashboard highlights.
- Label the agent command center with the configured Meituan model name so users can see which model is powering the assistant.
- Reduce visual clutter and secondary feature prominence while preserving access to timeline, report, and memory review pages.

## Capabilities

### New Capabilities
- `business-dashboard-experience`: Defines the business-oriented dashboard, Meituan themed frontend shell, model labeling, and simplified analysis-first navigation behavior.

### Modified Capabilities
- `business-analysis-system`: Clarifies that the frontend result dashboard must prioritize business interpretation and strategy browsing, not only generic placeholder charts.

## Impact

- Affected frontend areas: project layout/navigation, dashboard feature components, agent command center header/model display, shared UI styling, and frontend type/data helpers if needed.
- Affected OpenSpec artifacts: new dashboard experience capability and a delta for the existing business analysis system capability.
- No backend API contract change is expected for this MVP iteration; demo/mock dashboard data can remain frontend-local unless existing artifact data is already available.
