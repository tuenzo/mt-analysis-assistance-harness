## 1. Planning And Reference Diff

- [x] 1.1 Create the OpenSpec proposal, design, specs, and task list for the updated reference PDF alignment.
- [x] 1.2 Commit the OpenSpec planning artifacts separately.
- [x] 1.3 Stop after planning until the user confirms implementation should begin.

## 2. Backend Method Gap Plan

- [x] 2.1 Audit panel-builder gaps against the updated reference skill: raw audit, SKU-category mapping, activity windows, payday controls, and model-ready fields.
- [x] 2.2 Audit descriptive diagnostics gaps: multi-metric activity comparisons and month/weekday/activity/category-size slices.
- [x] 2.3 Audit LocalGap/LMDI gaps: non-sparse retained sample, counterfactual aliases, activity stage/window summaries, and decomposition levels.
- [x] 2.4 Audit mechanism/conversion gaps: exposure/discount effects, conversion by exposure tier, and caveat wording.
- [x] 2.5 Audit user-state gaps: four-state H0-H3 weekly state profile, transition matrix, representative paths, and dynamic marketing actions.

## 3. Report And Frontend Display Gap Plan

- [x] 3.1 Audit generated report section order and labels against the updated Chinese reference report.
- [x] 3.2 Audit whether important backend results are missing from the dashboard or artifact view.
- [x] 3.3 Identify light-touch presentation upgrades only: labels, badges, caveat notes, section grouping, and links to existing artifacts.

## 4. Later Implementation Backlog

- [ ] 4.1 Implement backend method-gap fixes in small commits after plan approval.
- [ ] 4.2 Implement report ordering/label fixes after backend artifact contracts are stable.
- [ ] 4.3 Implement only necessary dashboard visibility/presentation fixes after artifact audit.
- [ ] 4.4 Add focused backend tests and run frontend build only when frontend files are touched.

## 5. Planning Verification

- [x] 5.1 Validate OpenSpec artifacts.
- [x] 5.2 Review planning diff for scope creep, especially frontend overreach.
- [x] 5.3 Commit planning-only artifacts.
