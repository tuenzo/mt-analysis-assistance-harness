## Context

The frontend is a Next.js App Router application. Project pages already live under `src/app/projects/[project_id]/` and use Zustand stores plus `api-client.ts` to load projects, agent messages, project state, artifacts, and reports. The current layout has a yellow sidebar and several mojibake strings; the dashboard and Agent pages also use different visual structures.

Next 16 documentation confirms pages are leaf route components, layouts wrap route segments, and active navigation that depends on `usePathname` belongs in Client Components. The implementation will keep project route components as Client Components because they rely on stores, SSE, and local UI state.

## Goals / Non-Goals

**Goals:**
- Give Agent analysis and result dashboard the same sidebar, top project header, spacing, color tokens, and page background.
- Keep message-first Agent behavior intact and route all typed prompts through existing `sendMessage`, which calls `POST /api/agent/messages`.
- Provide feature-complete visual states for plans, tool calls, approvals, artifacts, progress, dashboard filters, charts, recommendations, drawer, and export modal.
- Structure data models and mock adapters so real backend results can replace mock dashboard summaries later.

**Non-Goals:**
- Do not add or change backend endpoints.
- Do not change analysis algorithms, workspace manifests, artifacts, permissions, or memory synchronization behavior.
- Do not introduce a charting dependency during this visual refactor.
- Do not build a marketing landing page or detach project pages from `/projects/[project_id]`.

## Decisions

1. Keep project routes and refactor content components under the existing App Router paths.
   - Rationale: `/projects/[project_id]/agent` and `/projects/[project_id]/dashboard` already encode project context and avoid a migration.
   - Alternative considered: top-level `/agent-analysis` and `/dashboard`; rejected because it would require new project selection behavior.

2. Implement shared shell in `features/layout` and reusable UI primitives in `components/ui`.
   - Rationale: the repository already uses `features` for business UI and `components/ui` for common controls.
   - Alternative considered: move everything into `src/layouts` and `src/pages`; rejected to avoid a broad filesystem churn that conflicts with the repo-specific frontend rules.

3. Use SVG/CSS chart primitives for the dashboard.
   - Rationale: the requested charts can be represented clearly without new dependencies, and the MVP needs stable mock-to-API interfaces more than advanced charting.
   - Alternative considered: add Recharts; rejected because it adds dependency and integration scope not required for this build.

4. Use snapshot builders for demo/dashboard data.
   - Rationale: the current backend may not always have every chart-ready metric, so the UI can render a polished state while keeping project/artifact data integration points.
   - Alternative considered: render only backend PNG artifacts; rejected because the requested drill-down and hover interactions need local data structures.

## Risks / Trade-offs

- [Risk] SVG chart primitives are less powerful than a charting library. -> Mitigation: keep chart components small, typed, and replaceable.
- [Risk] Dashboard mock values may diverge from real analysis outputs. -> Mitigation: isolate sample summary construction in dashboard data modules.
- [Risk] Large visual refactor could break existing Agent SSE behavior. -> Mitigation: reuse the existing agent store, event hook, approval methods, and message send flow.
- [Risk] Long Chinese labels can overflow compact controls. -> Mitigation: use stable dimensions, truncation, wrapping, and responsive grid fallbacks.

## Migration Plan

1. Add shared design tokens and shell components.
2. Replace Agent page content while preserving state/store wiring.
3. Replace dashboard content with typed summary data and interactive components.
4. Run frontend lint/build and fix regressions.
5. Rollback strategy: revert this branch/change; no database or backend migrations are involved.
