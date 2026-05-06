# Artifact Preview Specification

## ADDED Requirement: Read Artifact Content

The system SHALL expose project-scoped artifact content reads for registered artifacts and workspace-relative artifact paths.

### Scenario: Read JSON chart artifact

Given a project has a registered chart artifact pointing to `artifacts/charts/gmv_trend.json`
When the frontend requests artifact content
Then the API returns `{ ok: true, data: { encoding: "json", content_type: "application/json", data: ... } }`
And the content read is constrained to the project's workspace.

### Scenario: Reject path traversal

Given a project exists
When a client requests artifact content using a path outside the project workspace
Then the API rejects the request with a client error
And no filesystem content outside the workspace is returned.

## ADDED Requirement: Render Chart Artifacts

The dashboard SHALL render supported chart JSON artifacts as visible charts rather than only listing file paths.

### Scenario: Dashboard renders chart evidence

Given chart artifacts are registered for a project
When the user opens the dashboard
Then the dashboard fetches chart content
And renders supported line, bar, and distribution chart payloads with source metadata and limitations.
