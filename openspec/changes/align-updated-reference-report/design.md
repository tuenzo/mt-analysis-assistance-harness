## Context

The previous `upgrade-reference-analysis-flow` change completed the four-stage roadmap requested by the user: resource-lift PSM-DID, LocalGap/LMDI, GPS/uplift, mechanism/conversion diagnostics, and user-week/HMM interfaces integrated into the standard flow. The newly updated PDF and `参考skills.md` now make the expected artifact contracts more concrete and more product-facing.

The important deltas are:

- Panel building must expose report-ready raw audit and model fields, not only the minimal fields needed by downstream modules.
- Descriptive diagnostics must compare multiple business metrics before causal language.
- LocalGap must clearly separate non-sparse sample construction, counterfactual component baselines, activity-window/stage summaries, and LMDI contribution outputs.
- User state analysis should describe four hidden states H0-H3 with weekly state profiles, transition matrix, and dynamic marketing actions.
- Reports and dashboards should read like the updated PDF: category-level causal/increment/resource logic first, user-state dynamics second, business-harness application last.

## Execution Boundary

This change starts with planning only. No backend or frontend implementation should begin until the plan is reviewed. The plan should identify method gaps first, then report/display gaps, and should avoid proposing a large frontend page redesign unless later evidence shows the existing layout cannot surface critical results.

## Goals / Non-Goals

**Goals:**

- Implement updated reference-report parity without hard-coding dataset-specific numeric results.
- Preserve existing artifact names and compatibility keys while adding reference-aligned fields.
- Keep downgrade/method-status wording whenever data support is weak or the implementation remains deterministic rather than a full statistical package.
- Use the existing backend virtual environment for tests and all Python verification.
- Add focused tests for the new artifact contracts and keep commits small.
- Prioritize backend business-analysis method gaps before display refinements.
- Keep frontend work to missing-result visibility, clearer labels, caveat surfacing, and small presentation upgrades on existing pages/components.

**Non-Goals:**

- Do not add heavyweight dependencies such as `hmmlearn`, `statsmodels`, or `scikit-learn` in this pass.
- Do not bypass the single `business_analysis` gateway.
- Do not overwrite unrelated dirty workspace changes.
- Do not force exact reproduction of the reference PDF's sample-specific numbers.
- Do not make large frontend feature or navigation changes as part of the first implementation pass.

## Gap Plan

### Backend Method Gaps

1. **Panel audit and feature contract gap.**
   The updated reference skill expects a raw-table audit, SKU-category mapping coverage, activity-date coverage, activity windows, payday controls, and model-ready fields. The current pipeline already builds a category-day panel, but the plan should verify and fill missing reference fields before downstream methods are touched.

2. **Descriptive diagnostics gap.**
   The updated PDF uses raw activity-vs-non-activity comparisons as a business context section across multiple metrics. The current diagnostics should be checked for GMV-only or narrow summaries and then upgraded to multi-metric, multi-slice diagnostics with non-causal language.

3. **Non-sparse and LMDI contract gap.**
   The updated reference flow distinguishes the full panel, non-sparse retained sample, counterfactual component panel, and LMDI summary levels. The plan should preserve existing LocalGap compatibility while adding explicit retained-coverage metadata and summary levels needed for report tables.

4. **Mechanism/conversion interpretation gap.**
   The updated PDF separates increment decomposition from mechanism evidence, including exposure/discount effects and conversion-by-exposure-tier diagnostics. The plan should audit whether existing mechanism and conversion artifacts expose enough information for report interpretation.

5. **User-state method gap.**
   The updated PDF describes four HMM states H0-H3, state profiles, transition matrix, and dynamic marketing actions. The current user-state layer should be planned around a four-state artifact contract first, with explicit method-status wording if the implementation remains deterministic before probabilistic HMM dependencies are added.

### Report And Display Gaps

1. **Generated report storyline gap.**
   The report should be checked for missing or outdated section order. The lightweight target is section ordering and labels that match the updated PDF, not pixel-perfect PDF reproduction.

2. **Dashboard result visibility gap.**
   The dashboard should be audited for whether important backend artifacts are hidden or collapsed: panel quality, PSM balance/pretrend, LocalGap/LMDI, mechanism/conversion, GPS/uplift quadrants, HMM state path, and method caveats.

3. **Presentation upgrade scope.**
   Frontend changes should prefer existing dashboard cards, artifact lists, labels, badges, and method-status notes. New major workflows, navigation changes, or large component rewrites are out of scope for the first implementation pass.

## Decisions

1. Panel fields are added as aliases and derived columns rather than replacing all legacy names.

   Existing modules use `gmv`, `order_count`, `discount_amount`, `view_uv`, and `buy_uv`. The updated reference uses `sku_sale_amt`, `order_cnt`, `biz_total_discount_amt`, `discount_rate_for_model`, `discount_rate_pp`, `conversion_per_10k_uv`, and related log fields. The implementation will emit both families where possible.

2. Activity-window segmentation lives in the panel builder.

   Downstream modules should not re-infer campaign windows differently. The panel builder will attach `activity_window`, `activity_day_index`, and `activity_stage` for activity rows, with early/middle/late thirds inside each contiguous campaign window.

3. Diagnostics stay descriptive and label themselves accordingly.

   Raw activity-vs-non-activity deltas will include approximate p-values when available, but the output must say these are business context only because activity timing overlaps with payday/month-end cycles.

4. The HMM layer becomes a four-state deterministic RFM path model until optional probabilistic HMM dependencies are introduced.

   This matches the PDF's H0-H3 business interpretation and transition matrix contract without pretending to have run a Gaussian HMM. The result will disclose `method_status` and `state_model`.

5. Frontend alignment should be data-contract first and light-touch.

   The result dashboard can render updated report sections and cards from artifact summaries without needing a bespoke chart for every table in the PDF. First-pass frontend work should answer: "Are important results visible, and is their interpretation/caveat clear?"

## Risks / Trade-offs

- [Risk] Changing `discount_rate` semantics could break existing tests or report interpretation. -> Mitigation: keep compatibility fields and add model/report aliases; tests pin both.
- [Risk] Dashboard files have unrelated local edits. -> Mitigation: inspect carefully and stage only our hunks, using synthetic staging if needed.
- [Risk] Deterministic HMM is still lighter than the PDF's Gaussian HMM wording. -> Mitigation: expose four-state artifact contract and method-status transparency until a dependency-backed HMM is added.
- [Risk] Additional panel fields may create all-zero or NaN edge cases. -> Mitigation: derive with safe division helpers, explicit zero fills, and focused tests.

## Verification Plan

- Read-only gap audit lives in `gap_audit.md` for implementation sequencing.
- Run targeted backend tests with `backend\\.venv\\Scripts\\python.exe -m pytest`.
- Run the full backend test suite after backend changes.
- Run `npm run build` from `frontend/` after frontend display changes.
- Review `git diff --cached` before each commit to avoid unrelated dirty files.
