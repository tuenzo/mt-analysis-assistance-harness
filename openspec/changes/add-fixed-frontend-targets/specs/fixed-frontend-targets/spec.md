## ADDED Requirements

### Requirement: Fixed frontend targets
The harness SHALL define stable/manual and dedicated test frontend targets in a workspace-local target resolver.

#### Scenario: Resolve stable manual target
- **WHEN** a caller requests the stable or manual frontend target
- **THEN** the resolver returns the fixed harness stable URL without starting a new frontend process

#### Scenario: Resolve dedicated test target
- **WHEN** a caller requests the test frontend target
- **THEN** the resolver returns the fixed harness test URL on `127.0.0.1:4180` and marks the target as startable

### Requirement: Dedicated test frontend launcher
The harness SHALL provide a launcher that starts the Next.js frontend for the dedicated test target rather than serving files from another repository.

#### Scenario: Launch test frontend
- **WHEN** the test frontend launcher is run for port `4180`
- **THEN** it starts the harness Next.js frontend with the configured API base URL

### Requirement: Frontend lifecycle observation
The harness SHALL provide probe and monitor commands for fixed frontend targets and SHALL log observations to ignored local runtime storage.

#### Scenario: Probe all targets
- **WHEN** a caller probes all frontend targets
- **THEN** the command records a health result for both manual and test targets without modifying source-controlled runtime files

### Requirement: E2E target selection
The harness SHALL provide an E2E entry point that selects the frontend target through environment variables or command-line arguments.

#### Scenario: Run E2E against test target
- **WHEN** a caller runs E2E with the test target
- **THEN** Playwright starts or reuses the dedicated test frontend and runs smoke checks against the resolved URL

#### Scenario: Run E2E against manual target
- **WHEN** a caller runs E2E with the manual target
- **THEN** Playwright uses the fixed manual URL without attempting to start or replace the stable frontend process
