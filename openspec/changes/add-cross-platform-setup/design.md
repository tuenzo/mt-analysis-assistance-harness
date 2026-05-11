## Context

The repository already has separate backend and frontend developer commands, plus a Windows-only demo starter. Normal local use still requires manual dotenv setup, Python virtualenv creation, dependency installation, and two service processes. The setup flow must work from the repository root on Windows and macOS and must not introduce another long-running business service.

## Goals / Non-Goals

**Goals:**
- Provide one user-facing setup entrypoint for configuration, dependency installation, and service startup.
- Keep model configuration in the existing project-level `.env` contract.
- Support Windows PowerShell and macOS shell users with small native launchers.
- Make the setup program reusable for later `.env` editing without reinstalling everything.
- Keep service startup transparent by writing local runtime logs and pid files.

**Non-Goals:**
- Packaging the app as a signed native installer.
- Managing external Python, Node.js, or Git installation.
- Adding cloud deployment or remote hosting.
- Changing runtime provider internals or exposing new backend APIs.

## Decisions

1. Use a Python setup program as the cross-platform orchestrator.

   Python is already required by the backend, supports interactive prompts on Windows and macOS, and can safely edit `.env` without shell-specific quoting. A Node.js setup program was considered, but Node may not be installed before frontend setup. A PowerShell-only script was considered, but it would not be native on macOS.

2. Keep launchers thin.

   `setup.ps1` and `setup.sh` only locate Python and invoke the shared Python script. This avoids duplicating prompt, dotenv, install, and process-management behavior across platforms.

3. Use project-level `.env` as the single editable user configuration file.

   Backend config already loads project-level `.env`; frontend can consume `NEXT_PUBLIC_API_BASE_URL` from the environment passed by the setup process. Keeping the project-level file avoids splitting model settings across backend and frontend directories.

4. Manage services with detached child processes and runtime metadata.

   The setup program starts FastAPI and Next.js in the background, writes logs under `.codex-run/setup/`, and records pid/url metadata. Foreground mode was considered, but it prevents the setup program from finishing and makes first-run guidance harder.

## Risks / Trade-offs

- [Missing Python or Node] -> The setup program will fail fast with actionable messages and keep installation responsibility explicit.
- [Secrets in git] -> `.env` remains ignored, `.env.example` uses placeholders, and the setup program never prints API keys after entry.
- [Stale background processes] -> Runtime metadata and a `stop` command provide a predictable cleanup path.
- [Port conflicts] -> The setup program checks the requested backend and frontend ports before starting services and tells the user which port is blocked.

## Migration Plan

1. Add setup program and platform launchers.
2. Update `.env.example` and setup documentation.
3. Add focused tests for dotenv editing and provider presets.
4. Users can keep any existing `.env`; setup will merge known keys and preserve unrelated custom keys.

Rollback removes the setup scripts and documentation only; no database or project workspace migration is required.
