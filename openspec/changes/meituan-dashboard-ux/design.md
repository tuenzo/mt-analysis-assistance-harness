## Context

The MVP frontend already has project routes for intake, agent, timeline, dashboard, reports, and memory review. The next product need is not a new backend workflow; it is a clearer analysis workspace experience that makes business results immediately legible after a campaign analysis run.

The design reference uses a Meituan-style yellow navigation and operational dashboard language. This change should adapt that direction without turning the app into a generic BI clone: the agent remains the reasoning entry point, while the dashboard becomes the place to browse evidence and decisions.

## Goals / Non-Goals

**Goals:**
- Make the dashboard business-first: campaign before/during/after metrics, DID effect, uplift quadrants, recommendations, and conclusions are visible in one scan.
- Make the frontend feel like a Meituan product surface using yellow highlights, restrained work-focused panels, and clear operational navigation.
- Simplify the left/project navigation around the primary workflow: data, agent analysis, dashboard, report/memory review.
- Show the configured Meituan model name in the agent experience.
- Keep the implementation local to frontend display logic unless a lightweight config endpoint already exists.

**Non-Goals:**
- Do not change the message-first agent contract or route natural-language input outside `POST /api/agent/messages`.
- Do not add a new backend analysis API solely for this UI pass.
- Do not implement new causal algorithms in this change.
- Do not remove existing pages; reduce their prominence and improve information hierarchy instead.

## Decisions

1. **Use a frontend dashboard view model for this pass.**
   - Rationale: Existing MVP pipelines may produce artifacts asynchronously and with varying completeness. A typed dashboard view model lets the UI display realistic business states now and later map real artifacts into the same shape.
   - Alternative considered: Query backend artifacts directly in every dashboard widget. Rejected for this pass because it would spread fallback logic across many components and make the UX work dependent on unfinished artifact coverage.

2. **Apply theme through existing Tailwind/CSS entry points and shared shell components.**
   - Rationale: A consistent yellow theme should come from layout, navigation, and reusable UI states rather than one-off widget styles.
   - Alternative considered: Redesign only the dashboard. Rejected because the user specifically asked for the page/theme and frontend logic to feel simpler across the product.

3. **Keep the agent model label close to the command center header.**
   - Rationale: Users ask the agent to analyze and need immediate trust context about the model used. The label should not become a global nav decoration disconnected from the agent.
   - Alternative considered: Add model metadata only to settings. Rejected because it hides the information at the moment of use.

4. **Prioritize dense but readable operational panels.**
   - Rationale: The app is an analysis workspace. The dashboard should support scanning, comparison, and decision review rather than marketing-style presentation.
   - Alternative considered: A hero-like landing dashboard. Rejected because the user needs analysis and data browsing as the primary workflow.

## Risks / Trade-offs

- [Risk] Demo business summary data could be mistaken for computed results. -> Mitigation: label the dashboard state as the current analysis snapshot and keep values in a single replaceable module that can later map real artifacts.
- [Risk] Yellow theme can become visually loud. -> Mitigation: use yellow for shell, active states, accents, and key decisions while keeping content panels white/neutral.
- [Risk] Simplifying navigation may hide secondary MVP pages. -> Mitigation: preserve all routes but group report/memory/timeline as review surfaces rather than equal primary steps.
- [Risk] Model name may not be exposed by backend. -> Mitigation: read from existing frontend env when available and fall back to the known configured Meituan model name from `.env.example`/runtime docs.

## Migration Plan

1. Add the dashboard experience spec and tasks.
2. Update frontend shell/theme and agent model label.
3. Replace or refactor dashboard content into business-oriented widgets.
4. Run frontend build and targeted browser checks at dashboard and agent pages.
5. Leave backend/API contracts unchanged unless existing code already exposes model metadata safely.
