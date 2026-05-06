## Context

MVP 0 status check:

- Implemented: FastAPI, SQLite project models, workspace creation, manifest/checksum, message runtime and SSE, single `business_analysis` gateway, permission levels, frontend project pages, Data Intake, Agent Command Center, and placeholder dashboard/report/memory pages.
- Implemented beyond pure MVP 0: local data source discovery/ingest, configurable Claude SDK adapter, demo mode, report/artifact/memory stubs, approved full-pipeline orchestration.
- Gaps: several old OpenSpec task files are not checked off even though code exists, `MVP-CHECKLIST.md` is encoding-damaged/stale, schema inference is still stubbed at the tool layer, and the current panel builder is a fragile CSV mock.

Reference repo comparison (`E:\CodingProject\meituancomp`):

- Reference is further along analytically: it has pandas panel building, validators, pipeline smoke/regression tests, strategy/report engines, and more complete agent/task/event tests.
- Harness is further along architecturally for the target product: message-first runtime, workspace manifest, single business tool gateway, FastAPI/Next split, and project-local filesystem state.
- Best practice to import now: pandas-based standardization and balanced panel construction from `business_analysis_assistant/backend/app/analysis/panel_builder.py`, adapted to this harness's tool result and workspace contract.

## Goals / Non-Goals

**Goals:**

- Replace the narrow hand-written panel aggregator with a pandas implementation.
- Keep existing action name, function signature, artifact shape, and downstream `category_day_panel.json` compatibility.
- Improve `data.validate` and `schema.infer` so users can see real field mapping and quality issues before panel build.
- Commit work in small rollback-friendly units.

**Non-Goals:**

- Do not replace diagnostics, PSM-DID, LocalGap, GPS, report generation, or frontend workflows in this change.
- Do not change database schema or expose new tools beyond `business_analysis`.
- Do not import the reference project wholesale.

## Decisions

- Use pandas in `build_panel.py`.
  - Rationale: date parsing, grouping, balanced MultiIndex panels, and numeric coercion are exactly the kind of structured data work pandas handles well.
  - Alternative considered: keep `csv.DictReader`; rejected because alias handling and balanced panels would become brittle.

- Write both `category_day_panel.json` and `category_day_panel.csv`.
  - Rationale: existing downstream MVP0 pipelines read JSON; CSV is easier for users, reports, and future model steps.
  - Alternative considered: switch only to CSV; rejected because it would create unnecessary blast radius.

- Keep schema mapping optional.
  - Rationale: current schema persistence exists but UI mapping is not complete. Automatic aliases should make common datasets work, while explicit mappings can override later.
  - Alternative considered: require `schema.apply_mapping`; rejected for MVP1 ergonomics.

- Add summary output under `.analysis/panel_summary.json`.
  - Rationale: artifact dashboards and agent answers need compact metadata without scanning the full panel.

## Risks / Trade-offs

- [Risk] New pandas/numpy dependency adds environment weight. -> Mitigation: dependency is already used by the reference analysis stack and is appropriate for real pipelines.
- [Risk] Existing diagnostics expect legacy field names like `category`, `discount`, and `exposure`. -> Mitigation: keep those compatibility columns in JSON output.
- [Risk] Chinese source headers can be encoding-varied. -> Mitigation: read CSV with `utf-8-sig` and include alias matching for common English plus known Chinese names.

## Migration Plan

1. Add pandas/numpy dependency.
2. Replace panel builder internals while keeping the public function names.
3. Implement real `schema.infer` through `ProjectService.infer_schema`.
4. Add/adjust tests.
5. Run backend pytest and frontend build.

Rollback is a single commit revert for the implementation commit; the OpenSpec proposal is committed separately.

## Open Questions

- Should archived specs be re-encoded and cleaned up separately? The current change does not touch global spec encoding damage.
- Should `data.validate` persist validation reports into the artifact table outside a full pipeline? That belongs in the existing artifact-service follow-up.
