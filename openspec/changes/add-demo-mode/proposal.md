## Why

Live demos currently require manually creating a project, loading CSVs, generating reports, and priming an agent conversation. That makes demos slow and fragile.

## What Changes

- Add an explicit backend demo mode flag.
- Seed a fixed Keemart demo project on backend startup when demo mode is enabled.
- Store a small in-repository demo dataset, reports, chart/table artifacts, and agent conversation history.
- Expose demo status and persisted session messages through backend APIs.
- Add a frontend demo entry button and render seeded data/report/history.

## Impact

- New backend demo seed service and demo API.
- New agent session history API.
- New frontend demo status and history loading calls.
- New demo fixture assets under `backend/app/demo/fixtures`.
