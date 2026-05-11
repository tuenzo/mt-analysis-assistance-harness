## ADDED Requirements

### Requirement: Interactive Model Configuration
The setup program SHALL let users create or update project-level model configuration without manually editing `.env`.

#### Scenario: First-time configuration
- **WHEN** a user runs setup with no existing `.env`
- **THEN** setup prompts for model provider, model name, API key, optional API base URL, runtime provider, and permission mode, then writes those values to `.env`

#### Scenario: Existing configuration edit
- **WHEN** a user runs setup in configuration mode with an existing `.env`
- **THEN** setup shows existing non-secret defaults, preserves unrelated keys, and updates only the model/runtime keys selected by the user

#### Scenario: Secret handling
- **WHEN** setup prompts for an API key
- **THEN** the entered key is not echoed back to the terminal or printed in the final summary

### Requirement: Cross-Platform Dependency Setup
The setup program SHALL install backend and frontend dependencies from the repository root on Windows and macOS.

#### Scenario: Backend dependency setup
- **WHEN** a user chooses to install dependencies
- **THEN** setup creates or reuses `backend/.venv` and installs packages from `backend/requirements.txt`

#### Scenario: Frontend dependency setup
- **WHEN** a user chooses to install dependencies
- **THEN** setup runs the package manager install command in `frontend/`

### Requirement: Local Service Startup
The setup program SHALL start the backend and frontend services using the generated configuration.

#### Scenario: Services start successfully
- **WHEN** a user chooses to start services
- **THEN** setup starts FastAPI and Next.js, writes logs and pid metadata under `.codex-run/setup/`, and prints the backend health URL and frontend URL

#### Scenario: Port conflict
- **WHEN** the configured backend or frontend port is already in use
- **THEN** setup stops before launching services and reports which port is unavailable

### Requirement: Platform Launchers
The repository SHALL provide small launchers for Windows and macOS users.

#### Scenario: Windows launcher
- **WHEN** a Windows user runs the PowerShell setup launcher
- **THEN** the shared setup program starts with arguments forwarded from the launcher

#### Scenario: macOS launcher
- **WHEN** a macOS user runs the shell setup launcher
- **THEN** the shared setup program starts with arguments forwarded from the launcher

### Requirement: Service Stop Command
The setup program SHALL provide a stop command for services it previously started.

#### Scenario: Stop started services
- **WHEN** a user runs setup stop after services were started by setup
- **THEN** setup reads pid metadata, terminates the backend and frontend processes when still running, and updates runtime metadata
