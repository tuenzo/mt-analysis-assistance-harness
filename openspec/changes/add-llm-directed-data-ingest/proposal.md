## Why

The current local ingest flow imports every CSV from a configured directory and guesses roles from filenames. The desired behavior is LLM-directed: the model should inspect controlled metadata and previews, decide which files matter, assign business roles, then import only selected files.

## What Changes

- Add `data.discover_source_files` as a controlled business_analysis action.
- Change `data.ingest` so it requires explicit `selected_files` with `source_path`, `role`, and `reason`.
- Keep backend ownership of filesystem access and workspace writes.
- Update prompts so agents discover before ingesting local data.
- Update Data Intake UI to discover candidates and present selected files instead of importing all CSV files.

## Impact

- Modified: backend tool action enum, registry, permissions, data tools, project service, project API schemas.
- Modified: agent prompt and mock adapter behavior.
- Modified: frontend data intake page and API types/client.
- Tests: discover previews, selected-file ingest, path confinement, gateway permission, and UI build.
