## Context

The current repository has the right product architecture: Message-first agent runtime, single `business_analysis` tool gateway, workspace-backed project state, and a runnable full pipeline. The analytical layer is partially upgraded: pandas panel building, diagnostics, LocalGap, and GPS/uplift have real logic, while PSM-DID remains simplified and the report-PDF/reference-skill method stack is not yet fully represented.

The reference materials define four useful tiers:

1. Existing but underpowered modules: PSM-DID, LocalGap, GPS/uplift, and report synthesis.
2. Report-PDF modules missing from the current standard flow: TWFE mechanism regressions, conversion-on-discount by exposure tier, and report ordering around causal direction/resource decomposition/resource allocation.
3. Reference-skill-only modules not shown in the PDF: user-week panel and Gaussian HMM state-path analysis.
4. Final standard-flow integration for the stage-3 modules.

## Goals / Non-Goals

**Goals:**

- Implement the user's four-stage roadmap with small, reviewable commits.
- Keep each analytical module self-contained under `backend/app/analysis/pipelines/`.
- Preserve existing action names and artifact paths where possible.
- Add new actions only through `BusinessAnalysisAction`, `ToolRegistry`, and gateway-backed tool wrappers.
- Emit method status, warnings, and downgrade reasons instead of overstating causal strength.
- Add pytest coverage for each new or materially upgraded module.

**Non-Goals:**

- Do not bypass the single `business_analysis` gateway.
- Do not add frontend work until backend artifacts exist.
- Do not require heavyweight optional dependencies in the first upgrade pass.
- Do not automatically sync findings to user-level memory.
- Do not rewrite unrelated dirty files in the current working tree.

## Decisions

1. Stage 1 starts with PSM-DID because it is the largest gap inside an existing standard-flow action.

   Current PSM-DID assigns treatment by the share of activity days, which does not match the reference report. The upgraded module will define exposure and discount resource-lift treatments from activity vs non-activity means, estimate simple propensity scores from pre/non-activity covariates, perform nearest-neighbor matching, and output balance/event-window/placebo diagnostics.

2. LocalGap remains the main increment accounting layer.

   The reference skill and existing code agree that LocalGap outranks DID for increment accounting. Later stage-1 work will add order/AOV component baselines and LMDI-style contribution artifacts without removing the current LocalGap result shape.

3. TWFE and conversion diagnostics are stage-2 modules, not hidden inside LocalGap.

   This keeps the LocalGap result focused on increment accounting and creates explicit artifacts for the report-PDF mechanism section.

4. HMM is introduced first as an interface and artifact contract.

   User-week HMM is in the reference skill but not in the PDF. Stage 3 will add actions and stubs/limited implementations that validate inputs and define outputs. Stage 4 will insert them into the standard full pipeline.

5. Dependencies stay conservative.

   Use pandas/numpy implementations for the first pass. If stronger statistical diagnostics later require sklearn/statsmodels/hmmlearn, add them behind an OpenSpec task with explicit dependency and fallback handling.

6. Agent dialogue runtime inherits the backend venv.

   The Claude Agent SDK child runtime will discover the project or backend `.venv`, set `VIRTUAL_ENV`, prepend the venv `Scripts`/`bin` directory to `PATH`, and expose the resolved interpreter in runtime diagnostics and prompt context. This keeps agent-side analysis behavior aligned with backend pytest/development commands.

## Risks / Trade-offs

- [Risk] Better PSM-DID without sklearn/statsmodels is still lighter than the reference report. -> Mitigation: output matched sample, SMD diagnostics, event windows, and placebo notes with `method_status` downgrade when support is thin.
- [Risk] The current workspace has unrelated dirty files. -> Mitigation: touch only analysis/OpenSpec/test files for this change and stage only those files.
- [Risk] Adding many stages at once could create a hard-to-review diff. -> Mitigation: commit OpenSpec first, then one module or capability per small commit, plus phase summary commits.
- [Risk] Existing reports may expect old keys. -> Mitigation: retain existing top-level keys such as `estimates`, `lift`, `method_status`, and artifact filenames while adding richer fields.
- [Risk] Reference report results are dataset-specific. -> Mitigation: implement methods and artifact contracts, not hard-coded report numbers.
- [Risk] Runtime venv discovery could pick a global interpreter if no venv exists. -> Mitigation: search workspace `.venv` first, then backend `.venv`, and disclose unavailable status in diagnostics.

## Migration Plan

1. Create OpenSpec artifacts for the four-stage roadmap.
2. Stage 1A: upgrade `analysis.run_psm_did` and add tests.
3. Stage 1B: add LocalGap component/LMDI fields and tests.
4. Stage 1C: extend GPS/uplift heterogeneity/quadrants and tests.
5. Stage 2: add mechanism-regression and conversion diagnostics actions, then restructure standard report order.
6. Stage 3: add user-week/HMM action interfaces without standard-flow insertion.
7. Stage 4: insert HMM into the full pipeline with method-status gating.

Rollback is by small git commits: each module upgrade is separately committed before the next stage begins.

## Open Questions

- Whether later stages should add `statsmodels`, `sklearn`, or `hmmlearn` as optional dependencies after the numpy/pandas baseline is in place.
- Whether frontend dashboard tabs should later get dedicated views for TWFE/LMDI/HMM artifacts, or rely on generic artifact display first.
