## Why

MVP0 can run end-to-end, but the result display and generated reports still feel like scaffold output: sections are template-like, chart evidence is thin, and the UI does not clearly explain what evidence supports each conclusion. The reference project contains stronger reporting artifacts and analytical framing; this change adapts the useful patterns into prompts, tool contracts, and display design without copying its report content.

## What Changes

- Add a report planning layer that separates findings, evidence, assumptions, limitations, and next actions.
- Improve generated Markdown so it reads like an evidence-backed business analysis deliverable.
- Improve chart/result metadata so reports can cite artifacts and explain confidence.
- Upgrade Dashboard and Report Studio to show KPI snapshots, evidence chains, artifact coverage, limitations, and next-step guidance.
- Use the demo project's real data as the primary verification path.

## Capabilities

### New Capabilities
- `credible-analysis-reporting`: Structured prompt/tool-call design and report output for credible business analysis deliverables.
- `evidence-led-result-display`: Frontend result views that make metrics, evidence, limitations, and artifacts easy to inspect.

### Modified Capabilities
- `business-analysis-system`: Report generation and result dashboard behavior are upgraded from placeholder output to evidence-led MVP1-style outputs.

## Impact

- Modified: backend report generation, result/chart metadata, tests.
- Modified: frontend Dashboard and Report Studio pages/components.
- Added: OpenSpec artifacts documenting report/display contracts.
- Validation: backend pytest, frontend build, local browser review against demo project.
