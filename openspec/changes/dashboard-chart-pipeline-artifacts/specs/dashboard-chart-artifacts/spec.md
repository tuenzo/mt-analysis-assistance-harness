## ADDED Requirements

### Requirement: Full Pipeline Generates Dashboard PNG Artifacts
The system SHALL generate backend-rendered dashboard PNG images as part of the full promotion analysis pipeline.

#### Scenario: Approved full pipeline completes
- **WHEN** an approved `analysis.run_full_pipeline` run completes successfully
- **THEN** the pipeline includes a `chart.render_dashboard` step
- **AND** the generated PNGs are persisted as `dashboard_chart` artifacts under `artifacts/charts/dashboard/`

### Requirement: Agent Can Regenerate Dashboard Images
The system SHALL expose dashboard image regeneration through the single `business_analysis` tool gateway.

#### Scenario: Agent requests dashboard image refresh
- **WHEN** the Agent calls `business_analysis` with action `chart.render_dashboard`
- **THEN** the backend regenerates all requested dashboard PNG images
- **AND** returns artifact references with stable workspace-relative POSIX paths and `image/png` MIME type
