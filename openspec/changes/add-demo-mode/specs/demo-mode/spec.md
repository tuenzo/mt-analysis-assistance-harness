## ADDED Requirements

### Requirement: Demo Mode Startup Seed

When `APP_DEMO_MODE=true`, the backend SHALL reset and recreate a fixed demo project on startup using repository-local fixtures.

#### Scenario: Demo mode disabled

- **GIVEN** `APP_DEMO_MODE` is unset or false
- **WHEN** the API starts
- **THEN** no demo project is seeded
- **AND** `GET /api/demo/status` reports `enabled=false`

#### Scenario: Demo mode enabled

- **GIVEN** `APP_DEMO_MODE=true`
- **WHEN** the API starts
- **THEN** the fixed demo project exists
- **AND** its workspace contains demo data, reports, artifacts, manifest, context summary, and latest result

### Requirement: Demo Frontend Entry

When demo mode is enabled, the frontend SHALL show a user-triggered entry point to the seeded demo project.

#### Scenario: Enter demo project

- **GIVEN** demo mode is enabled
- **WHEN** the user opens the projects page
- **THEN** a Demo Mode entry button links to the seeded project
- **AND** the Agent page loads seeded conversation history
