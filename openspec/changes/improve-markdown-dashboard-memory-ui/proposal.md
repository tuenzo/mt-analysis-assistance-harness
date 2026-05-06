## Why

Agent answers, reports, and memory entries already contain Markdown tables, lists, headings, and emphasis, but the frontend currently renders much of that content as plain text. The Dashboard also hides business results behind artifact links, which weakens the demo and makes users work too hard to understand the analysis.

## What Changes

- Add shared Markdown rendering for assistant messages, report previews, Dashboard narrative blocks, memory candidates, and stored project memory.
- Upgrade the Dashboard into a result-first view that shows key metrics, report highlights, category results, and latest artifacts directly on the page.
- Keep the existing report and artifact APIs; the Dashboard may reuse the latest report content and existing artifact metadata without changing the backend contract.
- Preserve empty, loading, and error states for projects that do not yet have report or artifact output.

## Capabilities

### New Capabilities
- `analysis-result-presentation`: Covers readable Markdown presentation and direct result visibility in the web workspace.

### Modified Capabilities
- `business-analysis-system`: The frontend workspace pages must present Markdown-rich agent, dashboard, and memory content as formatted analysis content instead of raw plaintext.

## Impact

- Affected frontend components:
  - `frontend/src/components/markdown-view.tsx`
  - `frontend/src/features/agent/message-item.tsx`
  - `frontend/src/app/projects/[project_id]/dashboard/page.tsx`
  - `frontend/src/app/projects/[project_id]/memory/page.tsx`
  - `frontend/src/app/projects/[project_id]/reports/page.tsx`
- Dependency impact:
  - Add Markdown/GFM rendering dependencies to the frontend package.
- Verification:
  - Run `npm run build`.
  - Verify Agent, Dashboard, Memory, and Reports in the browser.
