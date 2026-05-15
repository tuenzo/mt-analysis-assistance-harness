## Context

The updated reference report defines a trend-level target rather than a pixel or number reproduction target: three raw tables feed a balanced category-day panel, descriptive checks, PSM-DID support, LocalGap/LMDI increment accounting, mechanism/conversion diagnostics, GPS/uplift prioritization, and caveated reporting. Current failures show the harness can confuse demo fixtures or incomplete source roles with real analysis evidence, and it can still emit static dashboard images after fatal pipeline failures.

## Goals / Non-Goals

**Goals:**

- Score result quality with machine-readable caps and actionable diff reasons.
- Detect demo/mock/fixture contamination before trend scoring.
- Make fatal source and panel failures stop the full pipeline.
- Keep all new actions inside the existing `business_analysis` gateway.
- Add tests for both observed benchmark failures.

**Non-Goals:**

- Do not exactly reproduce the PDF's sample-specific numeric values.
- Do not introduce new statistical dependencies in this pass.
- Do not redesign the frontend result dashboard in this slice.
- Do not bypass existing artifact registration or project workspace contracts.

## Decisions

1. Quality scoring lives in a new backend tool module rather than inside report generation.

   This keeps quality assessment reusable by agent prompts, tests, reports, and future UI surfaces. The report can read the score later, but scoring must be runnable immediately after any analysis stage.

2. Scoring uses caps plus sub-scores.

   Caps protect against polished nonsense: a demo-contaminated or source-incomplete run cannot earn a high score through a few matching trend statements. Sub-scores still explain what would improve once the hard gate is fixed.

3. The first implementation uses deterministic artifact inspection.

   It reads DB records, manifest files, source CSV metadata, existing result artifacts, and report text. It does not rerun models or mutate source analysis outputs.

4. Dashboard PNG rendering requires evidence artifacts.

   Existing static images are useful as visual placeholders, but not as final result artifacts. The backend will refuse `chart.render_dashboard` unless current analysis result files exist and at least one has usable status.

5. Default SQLite resolution is anchored at repository root.

   `sqlite:///./business_analysis.db` previously followed process cwd. Anchoring it under the project root removes the root-vs-backend database split while preserving explicit `APP_DATABASE_URL` overrides.

## Risks / Trade-offs

- [Risk] Existing tests expect dashboard charts to render without results. -> Mitigation: update tests to create minimal evidence or assert the new failure.
- [Risk] Quality scoring may be conservative at first. -> Mitigation: return detailed cap reasons and sub-scores so future rounds can calibrate.
- [Risk] Processed-panel ingestion can be legitimate. -> Mitigation: classify it as an existing panel candidate, not as raw `order_info`, and require explicit handling before full analysis.
