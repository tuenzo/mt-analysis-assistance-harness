## Why

The Agent analysis page and result dashboard currently use different layouts and contain garbled Chinese UI copy, which makes the product feel fragmented and harder to validate against the reference designs. This change creates a shared project workspace shell and rebuilds the two primary analysis surfaces so users can move between conversation-driven analysis and dashboard review without losing project context.

## What Changes

- Introduce a shared AppShell visual system for project pages with a white sidebar, fixed primary navigation, recent projects, project header, and light gray workspace background.
- Rebuild the Agent analysis page as a conversation stream plus right-side run inspector while preserving the message-first `POST /api/agent/messages` flow.
- Rebuild the result dashboard as a filter bar, conclusion banner, KPI strip, chart grid, recommendation panel, drill-down drawer, and export modal.
- Add frontend-only typed mock data adapters and chart primitives that can later be replaced by real artifact/API data.
- Fix Chinese display copy in the affected frontend shell and pages.

## Capabilities

### New Capabilities
- `shared-analysis-workspace-frontend`: Covers the shared project AppShell, Agent analysis workspace, and result dashboard presentation/interaction requirements.

### Modified Capabilities
- None.

## Impact

- Affected code: `frontend/src/app/projects/[project_id]/**`, `frontend/src/features/layout/**`, `frontend/src/features/agent/**`, `frontend/src/features/dashboard/**`, shared UI/styles/types under `frontend/src/components`, `frontend/src/lib`, and `frontend/src/app/globals.css`.
- APIs: No backend API contract changes. Natural language messages must continue to use `POST /api/agent/messages`.
- Dependencies: No new package dependencies planned; charts use lightweight SVG/CSS components and existing `lucide-react` icons.
