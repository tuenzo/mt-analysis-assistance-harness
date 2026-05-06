## Why

The MVP report path currently produces a flat Markdown file from whatever result JSON happens to exist. Demo runs look more credible when reports show how each conclusion is backed by concrete result and chart artifacts, and when limitations and next steps are explicit instead of implied.

## What Changes

- Add a lightweight report plan in backend code with section purpose, evidence artifacts, prompt/tool-call intent, assumptions, limitations, and recommended follow-up.
- Render Markdown reports from that plan while preserving the existing `report.generate` API and `reports/report.md` output.
- Enrich chart and latest-result tool artifacts with compatible metadata so the agent and UI can see sources, caveats, and recommended next actions.
- Refresh Dashboard and Report Studio so users can review KPIs, evidence coverage, artifacts, caveats, and report sections without opening raw files.
- Add focused tests for report planning/rendering and chart/result metadata.

## Impact

- **Modified**: `backend/app/reports/renderer.py`
- **Modified**: `backend/app/tools/report_tools.py`
- **Modified**: `backend/app/tools/result_tools.py`
- **Modified**: `backend/app/analysis/chart_renderer.py`
- **Modified**: `frontend/src/app/projects/[project_id]/dashboard/page.tsx`
- **Modified**: `frontend/src/app/projects/[project_id]/reports/page.tsx`
- **Tests**: report/chart/result tests only
