# Proposal: Dashboard Chart Artifacts in Pipeline

## Why

The result dashboard now relies on backend-rendered PNG charts, but those images are generated lazily by the frontend chart endpoint. A full analysis run should produce the dashboard image artifacts as part of the analysis output, and the Agent should be able to explicitly regenerate them when a user asks.

## What Changes

- Add a `chart.render_dashboard` business analysis action for regenerating all or selected dashboard PNGs.
- Include dashboard PNG rendering as a required step in the full analysis pipeline.
- Return dashboard PNG artifacts with stable paths and metadata so pipeline runs and Agent calls can surface them.
- Keep the existing frontend chart endpoint working for on-demand reads.

## Non-Goals

- This change does not redesign the five chart visuals.
- This change does not replace existing JSON chart artifacts used by reports.
