## Overview

The implementation keeps report generation local and deterministic. Instead of introducing a new report service or API shape, the renderer builds a small `ReportContext`, applies an ordered section plan, writes Markdown plus metadata sidecars, and returns normal `ToolResult` artifacts.

## Report Plan

Each planned section contains:

- `section_id`
- `title`
- `purpose`
- `prompt`
- `tool_calls`
- `evidence_artifacts`
- `assumptions`
- `limitations`
- `recommended_follow_up`

The plan is data-informed but not LLM-generated. It gives Codex and the frontend a clear contract for why a section exists and which artifacts support it.

## Evidence Strategy

The renderer reads:

- `.analysis/latest_result.json`
- `.analysis/panel_summary.json`
- known result files under `.analysis/`
- chart JSON files under `artifacts/charts/`
- `.analysis/project_manifest.json` when present

Missing evidence is not hidden. The report includes limitations and follow-up tool calls for absent outputs such as `chart.render` or `analysis.run_gps_uplift`.

## Compatibility

- `report.generate` still writes `reports/report.md`.
- Returned `ToolResult` fields remain additive only.
- Chart JSON keeps existing top-level plotting fields while adding metadata fields.
- `result.get_latest` still writes `.analysis/latest_result.json` and adds a separate `.analysis/latest_result_index.json`.

## Frontend Review Surface

Dashboard and Report Studio stay file/API driven. They infer readiness from project state, report Markdown, and registered artifacts, then surface:

- KPI and coverage snapshots
- evidence-chain status
- report section navigation
- artifact references
- limitations and follow-up actions
