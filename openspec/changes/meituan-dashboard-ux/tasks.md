## 1. Discovery and Contracts

- [x] 1.1 Inspect frontend shell, dashboard, agent command center, theme, and API/type entry points
- [x] 1.2 Confirm the safest source for model label and dashboard snapshot data without changing backend contracts

## 2. Theme and Navigation

- [x] 2.1 Apply Meituan yellow theme through global CSS/Tailwind/shared layout surfaces
- [x] 2.2 Simplify project navigation around Data, Agent Analysis, Dashboard, and secondary review surfaces

## 3. Agent Model Label

- [x] 3.1 Add a visible model label to the agent command center using configured model metadata or Meituan fallback
- [x] 3.2 Ensure the model label preserves the existing message-first agent input behavior

## 4. Business Dashboard

- [x] 4.1 Add a typed campaign analysis dashboard snapshot/view model for MVP display
- [x] 4.2 Render activity before/during/after metric cards and trend comparison
- [x] 4.3 Render DID evaluation with effect, confidence/significance cue, and interpretation
- [x] 4.4 Render uplift quadrants with segment counts, meanings, and recommended actions
- [x] 4.5 Render executive recommendations, conclusions, and caveats above supporting detail
- [x] 4.6 Reorganize the result dashboard into a stable responsive 2×2 quadrant layout with unified chart-left and summary-right card structure
- [x] 4.7 Add business chart essentials: axis names, units, ticks, legends, category/date labels, and key values

## 5. Quality Checks

- [x] 5.1 Run frontend build and relevant lint/type checks available in the project
- [x] 5.2 Use browser-based visual checks for dashboard and agent pages at desktop and mobile widths
- [x] 5.3 Review git diff for secrets, unrelated churn, and OpenSpec/task consistency
- [x] 5.4 Re-run build and browser checks after responsive quadrant layout refinement
