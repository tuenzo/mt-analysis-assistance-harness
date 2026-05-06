## Context

MVP1 has a working message-first agent runtime, real Claude Agent SDK integration, project workspace isolation, and one external `business_analysis` tool. The current analysis flow is still backend-led: fixed pipeline actions are implemented in code and the model mainly decides when to call them.

The new capability should let the model lead analysis strategy design and flow design, but it must not mutate the stable MVP1 framework directly. The first isolated version therefore treats model-led framework changes as versioned strategy artifacts and backend change proposals, stored inside the project workspace for review and promotion.

## Goals / Non-Goals

**Goals:**

- Let the model create and revise analysis strategy blueprints.
- Let the model design an analysis flow as ordered stages, required data inputs, expected artifacts, assumptions, and tool/action recommendations.
- Persist strategy lab outputs in `.analysis/strategy_lab/` with version metadata and audit-friendly rationale.
- Expose the capability only through the existing `business_analysis(project_id, action, payload, reason)` gateway.
- Keep MVP1 behavior unchanged unless a user runs the isolated branch and explicitly asks for strategy lab actions.

**Non-Goals:**

- No arbitrary backend source-code writing by the model.
- No automatic promotion of generated strategy designs into production pipeline code.
- No changes to the existing full-pipeline behavior in MVP1.
- No external sync or user-level memory writes.

## Decisions

1. Strategy artifacts live under `.analysis/strategy_lab/`.

   Rationale: The project workspace remains the fact source, and `.analysis/` is already reserved for system-managed analysis state. Storing strategy lab artifacts there keeps them isolated from raw data, reports, and source code.

   Alternative considered: commit generated designs directly into `backend/app/analysis`. This was rejected because it would make the model a direct code author in the stable framework.

2. Add `strategy.*` actions to the existing business tool instead of exposing a new MCP tool.

   Rationale: The architecture requires a single external custom tool. `strategy.design_blueprint`, `strategy.design_flow`, and `strategy.propose_backend_change` can be routed through the same gateway, permission checks, and logging.

   Alternative considered: expose a second `framework_editor` tool. This was rejected because it expands the external tool surface and weakens the existing permission boundary.

3. Persist JSON first, Markdown second.

   Rationale: JSON makes frontend rendering and validation easier; Markdown gives humans a readable review artifact. Both can be generated from the same validated payload.

   Alternative considered: free-form Markdown only. This was rejected because downstream promotion and testing need structured fields.

4. Treat backend framework modification as proposal generation, not direct source mutation.

   Rationale: The model can autonomously design strategy and flow, but code changes must remain auditable and reviewable. A proposed backend change can later be implemented by Codex or a human on a separate branch.

   Alternative considered: let the model write Python files in `backend/app`. This was rejected for MVP1+1 because it creates high risk around permissions, broken imports, and accidental changes to demo-critical code.

## Risks / Trade-offs

- [Risk] The model may output vague or inconsistent strategies. → Mitigation: validate required fields and persist assumptions, risks, and success criteria explicitly.
- [Risk] Users may expect generated strategy designs to run immediately. → Mitigation: label outputs as draft or approved strategy artifacts and keep runtime execution separate.
- [Risk] Strategy lab artifacts could drift from actual pipeline capabilities. → Mitigation: require each flow stage to declare either an existing action or a proposed backend change.
- [Risk] Future promotion may become complex. → Mitigation: keep version, parent version, status, and source turn metadata in every artifact.

## Migration Plan

1. Create the isolated Git branch from the MVP1 tag.
2. Add strategy lab actions and service code only on the isolated branch.
3. Add tests proving artifacts stay under `.analysis/strategy_lab/`.
4. Keep MVP1 tag and branch available for rollback.
5. Promote only after user review and a separate merge decision.

## Open Questions

- Should the frontend expose a dedicated strategy lab panel, or should the first version rely on the test agent frontend event stream?
- Should approved strategy blueprints later become selectable pipeline profiles?
- What minimum validation should be required before a proposed flow can be promoted into executable backend code?
