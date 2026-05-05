## Design

Demo mode is controlled by `APP_DEMO_MODE`, defaulting to `false`. When enabled, backend startup resets and recreates a fixed demo project id (`APP_DEMO_PROJECT_ID`, default `proj_demo_keemart_promo`) so each demo begins from a predictable state.

The demo seed uses only small fixtures committed in this repository. The seed copies raw data, processed data, reports, chart artifacts, and table artifacts into the workspace, then writes database rows for files, artifacts, reports, a demo session, turns, and events. The workspace manifest, context summary, and latest result are also written so agent context and project state remain workspace-first.

The frontend never auto-redirects. The projects page queries `GET /api/demo/status`; when enabled, it shows a Demo Mode banner and an entry button for the seeded project. The Agent page loads persisted session messages when demo status points to the current project, then continues normal `POST /api/agent/messages` and SSE behavior for new messages.
