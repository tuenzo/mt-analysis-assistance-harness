## Overview

The change improves presentation without changing the backend business-analysis contract. A shared Markdown component renders trusted backend-generated text with GitHub-flavored Markdown support. Dashboard consumes the existing project state, artifacts list, and latest report endpoint to build a result-first page.

## Markdown Rendering

Add a `MarkdownView` component with:

- GFM table support.
- Scoped styling for headings, paragraphs, tables, lists, code, blockquotes, and links.
- No raw HTML rendering.
- A compact mode for chat bubbles and memory cards.

Usage:

- Assistant messages use MarkdownView.
- User messages remain plain text.
- Reports and memory content use MarkdownView instead of `<pre>`.
- Dashboard uses MarkdownView for the report highlight block.

## Dashboard Layout

The Dashboard should answer "what happened?" without requiring a click.

Top section:

- Stage
- Latest pipeline status
- Total GMV
- LocalGap increment

Main section:

- A readable "Executive Snapshot" extracted from the latest report.
- Category result table extracted from the report Markdown when present.
- Latest artifact list with clear type and path.
- Report status CTA remains available, but is secondary.

Fallback behavior:

- If no report exists, show available state/artifacts and a clear empty state.
- If report parsing misses a value, show `--` rather than failing.

## Data Sources

Use existing APIs:

- `GET /api/projects/{project_id}/state`
- `GET /api/projects/{project_id}/artifacts`
- `GET /api/projects/{project_id}/reports/latest`

The first implementation derives metrics from the report text. A later backend enhancement can add a dedicated dashboard summary endpoint once artifact content contracts stabilize.

## Risks

- Markdown content can contain long tables; the renderer must allow horizontal scrolling.
- Report text may vary; parsing must be defensive.
- Chat bubbles must keep readable width and not overflow on mobile.
