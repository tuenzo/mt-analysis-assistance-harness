## 1. Setup Program

- [x] 1.1 Add a shared Python setup program with commands for configure, install, start, stop, and run-all.
- [x] 1.2 Implement dotenv parsing/writing that preserves unrelated keys and avoids printing secrets.
- [x] 1.3 Add provider presets for common Anthropic-compatible and custom providers.

## 2. Platform Entrypoints

- [x] 2.1 Add a Windows PowerShell launcher that forwards arguments to the shared setup program.
- [x] 2.2 Add a macOS shell launcher that forwards arguments to the shared setup program.

## 3. Documentation and Examples

- [x] 3.1 Refresh `.env.example` with readable model/runtime setup comments.
- [x] 3.2 Add setup usage documentation covering first run, editing `.env`, starting, and stopping services.

## 4. Verification

- [x] 4.1 Add focused tests for dotenv editing and provider presets.
- [x] 4.2 Run backend tests and frontend build checks, or document any blockers.
