## 1. Planning And Commit Hygiene

- [x] 1.1 Create the OpenSpec proposal, design, specs, and task list for the four-stage roadmap.
- [x] 1.2 Commit the OpenSpec planning artifacts separately from implementation changes.
- [x] 1.3 Ensure agent dialogue analysis automatically discovers and uses the backend Python virtual environment.
- [x] 1.4 Add runtime-environment tests and commit the venv integration separately.

## 2. Stage 1A - Upgrade Existing PSM-DID

- [x] 2.1 Replace activity-share treatment with exposure-lift and discount-lift treatment definitions.
- [x] 2.2 Add pre/non-activity covariates, propensity scoring, nearest-neighbor matching, and SMD balance diagnostics.
- [x] 2.3 Add event-window and placebo/pretrend diagnostics with method-status downgrades for thin support.
- [x] 2.4 Preserve existing `psm_did_result.json` compatibility keys and add pytest coverage.
- [x] 2.5 Commit the PSM-DID upgrade as a small feature commit.

## 3. Stage 1B - Upgrade Existing LocalGap

- [x] 3.1 Add non-sparse sample metadata and retained-coverage summaries to LocalGap outputs.
- [x] 3.2 Add order/AOV component baselines and counterfactual GMV where source fields support them.
- [x] 3.3 Add additive LMDI contribution summaries with zero-handling flags and reconciliation checks.
- [ ] 3.4 Add focused pytest coverage and commit the LocalGap/LMDI upgrade.

## 4. Stage 1C - Upgrade Existing GPS/Uplift

- [ ] 4.1 Add exposure and discount heterogeneity slices for category size and payday/non-payday windows.
- [ ] 4.2 Add rank-curve and continuous resource quadrant artifacts.
- [ ] 4.3 Add focused pytest coverage and commit the GPS/uplift upgrade.
- [ ] 4.4 Run backend pytest for stage 1 and commit a stage-1 checkpoint.

## 5. Stage 2 - Add Report-PDF Flow Capabilities

- [ ] 5.1 Add mechanism-regression action and pipeline module for GMV/order/AOV resource decomposition.
- [ ] 5.2 Add conversion-on-discount by exposure-tier action and artifact.
- [ ] 5.3 Update full-pipeline ordering and report synthesis to follow the reference PDF logic.
- [ ] 5.4 Add tests and commit stage-2 capability changes.

## 6. Stage 3 - Add Reference-Skill-Only Interfaces

- [ ] 6.1 Add user-week panel action interface with validation and limited-status artifact behavior.
- [ ] 6.2 Add HMM state-path action interface with artifact contract and downgrade behavior.
- [ ] 6.3 Add tests proving the interfaces are registered but not called by the standard full pipeline.
- [ ] 6.4 Commit stage-3 interface changes.

## 7. Stage 4 - Integrate Stage-3 Capabilities

- [ ] 7.1 Insert user-week/HMM steps into the full pipeline with method-status gating.
- [ ] 7.2 Update report synthesis to include HMM only when artifacts exist or explicitly show downgrade status.
- [ ] 7.3 Add tests for standard-flow integration and commit stage-4 changes.

## 8. Final Verification

- [ ] 8.1 Run backend pytest.
- [ ] 8.2 Run frontend build if touched artifacts or report metadata affect frontend contracts.
- [ ] 8.3 Review git diff for secrets, generated cache files, and unrelated changes before final summary.
