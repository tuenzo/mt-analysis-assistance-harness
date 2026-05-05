## Why

Users need the agent to load CSV data that already exists elsewhere on the local machine without manually uploading every file through the browser. The workspace must still remain the project fact source, so external files should be copied into `workspaces/{project_id}/data/raw/` through the backend instead of letting the agent read arbitrary paths directly.

## What Changes

- Add a project-level `data_source_path` setting for a local absolute directory.
- Implement controlled CSV directory ingest through `business_analysis` action `data.ingest`.
- Copy first-level CSV files from the source directory into project `data/raw/`, register them in the database, refresh `.analysis/project_manifest.json`, and refresh `.analysis/context_summary.md`.
- Add Data Intake UI controls to save a source directory and trigger import.
- Keep natural-language agent requests message-first: Claude/Codex must call the single `business_analysis` tool for local data ingestion.

## Impact

- Modified: `backend/app/projects/models.py`
- Modified: `backend/app/projects/schemas.py`
- Modified: `backend/app/projects/service.py`
- Modified: `backend/app/api/projects.py`
- Modified: `backend/app/core/database.py`
- Modified: `backend/app/tools/data_tools.py`
- Modified: `backend/app/core/permissions.py`
- Modified: `backend/app/agent/prompt_composer.py`
- Modified: `backend/app/agent/claude_agent_sdk_adapter.py`
- Modified: `frontend/src/app/projects/[project_id]/data-intake/page.tsx`
- Modified: `frontend/src/lib/api-client.ts`
- Modified: `frontend/src/lib/api-types.ts`
- Tests: backend file ingest, gateway permission/approval, existing upload compatibility
