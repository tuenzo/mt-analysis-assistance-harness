## Why

Local users currently need to install backend and frontend dependencies, copy dotenv files, edit model settings, and start two services by hand. A setup entrypoint lowers the barrier for Windows and macOS users and makes the MVP harness easier to validate outside the developer's machine.

## What Changes

- Add a cross-platform setup program that runs on Windows and macOS.
- Let users enter or edit their model provider, model name, API key, and optional API base URL.
- Generate or update the project-level `.env` without committing secrets.
- Install backend and frontend dependencies when requested.
- Start FastAPI and Next.js services with the generated configuration.
- Add thin platform launchers so Windows users can run PowerShell and macOS users can run a shell script.
- Document the setup flow and follow-up `.env` editing workflow.

## Capabilities

### New Capabilities
- `local-setup-automation`: User-facing local setup, configuration editing, dependency installation, and service startup for Windows and macOS.

### Modified Capabilities

## Impact

- Adds scripts under `scripts/`.
- Adds or updates setup documentation.
- Updates `.env.example` to make model configuration understandable.
- Does not change backend API routes, frontend routes, analysis pipelines, or persisted project schemas.
