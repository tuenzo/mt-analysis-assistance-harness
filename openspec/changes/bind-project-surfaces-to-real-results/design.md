## Design

Normal project result surfaces now use a shared view-model adapter in `frontend/src/features/dashboard/dashboard-data.ts`.

The adapter accepts the usual project state, artifact list, and latest report metadata plus optional raw JSON loaded from:

- `.analysis/latest_result.json`
- `.analysis/panel_summary.json`

It builds a `DashboardSummary` from real diagnostics, LocalGap, and recommended-action sections. If those artifacts are missing, it returns an explicit pending state with empty charts and "待分析" labels. It does not return demo categories, demo dates, or demo KPI values for normal projects.

The Keemart showcase remains intentionally separate through `isKeemartPromoProject(projectId)`, so curated demo pages still use `keemart-demo-data.ts`.

## Key Choices

- **No backend contract change:** the artifact content endpoint already supports reading `.analysis` JSON safely inside a project workspace.
- **One adapter for multiple surfaces:** the Agent inspector and project dashboard use the same `DashboardSummary` builder, reducing drift.
- **Truthful limited decomposition:** when LocalGap exists but exposure/discount decomposition is zero or unavailable, the UI shows that as `0` and keeps the remaining contribution in `残差/未拆分` instead of inventing attribution.
- **No fake fallback:** missing real result artifacts render pending states.
