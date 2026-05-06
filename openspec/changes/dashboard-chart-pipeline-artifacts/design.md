# Design: Dashboard Chart Artifacts in Pipeline

## Approach

`dashboard_chart_renderer` remains the single renderer for dashboard PNGs. It gains a batch helper that renders all known chart IDs or a caller-supplied subset and returns artifact dictionaries compatible with `ToolResult`.

The new `chart.render_dashboard` action is registered in the existing single `business_analysis` tool gateway. The full pipeline invokes this action after analysis results and JSON chart data are prepared, before latest-result aggregation and report generation.

## Artifact Contract

Each generated dashboard image is written under:

```text
artifacts/charts/dashboard/{chart_id}.png
```

Each returned artifact includes:

- `type`: `dashboard_chart`
- `title`: `{chart_id}.png`
- `path`: relative workspace path
- `mime_type`: `image/png`
- `chart_id`
- `generated_at`

## Error Handling

Unknown chart IDs fail the action with `UNKNOWN_CHART_ID`. An empty or omitted chart list renders all dashboard chart IDs.
