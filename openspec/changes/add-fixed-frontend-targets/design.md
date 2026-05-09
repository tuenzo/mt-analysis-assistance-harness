## Context

The harness repository has a Next.js frontend under `frontend/`, while the main `meituancomp` repository has a different static frontend under `business_analysis_assistant/`. Reusing the main repository's static server on port `4180` leaves the harness test address bound to the wrong project. The harness also has no root `package.json`, so frontend scripts need to live in `frontend/package.json` while root-level helper scripts live under `scripts/`.

## Goals / Non-Goals

**Goals:**
- Resolve stable/manual and test frontend targets from one harness-owned module.
- Start the dedicated test target with the harness Next.js app on `127.0.0.1:4180`.
- Keep lifecycle logs in ignored local runtime storage.
- Let Playwright smoke tests target either the manual stable URL or the dedicated test URL.

**Non-Goals:**
- No new backend routes or database schema changes.
- No replacement for the existing `scripts/start-demo.ps1` development helper.
- No attempt to automatically manage every historical local process from prior experiments.

## Decisions

### Use a Next-aware launcher

The dedicated test frontend will be started with the local Next CLI from `frontend/node_modules` and the requested host/port. By default it uses `next start` against the latest build so it can coexist with the stable `3010` development server from the same checkout. This keeps the `4180` target bound to the harness app instead of serving static files from the main repository.

Alternative considered: copy the static `serve-frontend.mjs` from the main repository. That does not fit this workspace because the harness frontend is not a static `index.html` app.

### Keep runtime logs under `.codex-run`

Lifecycle probe and monitor output will be written to `.codex-run/frontend/frontend-lifecycle.jsonl`, which is already ignored by the repository. This avoids adding runtime noise to source-controlled paths.

Alternative considered: add a new ignored `runtime/` directory. Reusing `.codex-run` is smaller and matches existing local run artifacts.

### Put npm entry points in `frontend/package.json`

The repository root has no npm package. Adding scripts to the existing frontend package lets contributors run commands from the same place they already run `npm run dev` and `npm run build`.

Alternative considered: create a root package solely for orchestration. That would add a second package boundary without enough benefit for this MVP harness.

## Risks / Trade-offs

- The dedicated test target serves the latest production build, so it can be stale after source edits. -> Run `npm run build` before E2E or before starting a long-lived test frontend.
- The stable URL is externally managed. -> Target resolution never auto-starts the stable/manual frontend; probes report whether it is alive.
- Playwright is a new frontend dev dependency. -> Scope tests to smoke checks and reuse the package-local dependency.
