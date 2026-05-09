## Why

Recent frontend target work was split across the main repository and this harness workspace, leaving the dedicated test address served by the wrong project. The harness needs its own fixed frontend target scripts so stable manual use and isolated test runs resolve to predictable, workspace-local URLs.

## What Changes

- Add harness-owned frontend target resolution for manual/stable and dedicated test addresses.
- Add lifecycle probe/monitor logging for those targets under the ignored local run area.
- Add a Next-aware test frontend launcher for `127.0.0.1:4180` instead of reusing the static frontend server from the main repository.
- Add Playwright configuration and a minimal smoke test that can run against either the stable manual target or the dedicated test target.
- Add npm scripts in the existing frontend package for probe, monitor, and E2E entry points.

## Capabilities

### New Capabilities
- `fixed-frontend-targets`: Fixed, workspace-local frontend targets and verification scripts for stable manual use and isolated frontend testing.

### Modified Capabilities
None.

## Impact

- Root scripts under `scripts/`.
- Frontend package scripts and development dependencies.
- Frontend Playwright config and smoke tests.
- OpenSpec artifacts only; no backend API or database contract changes.
