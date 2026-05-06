## Design

The agent receives a deterministic data-load protocol in both prompt composers:

1. Call `project.get_state` to inspect current files, stage, and saved `data_source_path`.
2. Call `data.discover_source_files` with the user-provided absolute path, or `{}` if the project already has a saved source path.
3. Inspect candidates returned by the backend only: filename, headers, preview, skipped status, and skip reason.
4. Classify CSV candidates into `order_info`, `exposure_info`, `activity_timeline`, or `unknown`.
5. Call `data.ingest` with `selected_files` for only confidently classified direct-child CSVs.
6. Call `schema.infer`.
7. Call `data.validate`.
8. If any step fails or validation remains partial, explain the exact issue and propose next user actions.

The real Claude Agent SDK already supports multi-turn tool use through `max_turns`; this change tightens the tool contract and makes the mock adapter emit the same multi-call skeleton for MVP validation.

## Completion Semantics

Data load is considered complete only when:

- At least one CSV has been imported into the workspace.
- Schema inference has run on registered project files.
- `data.validate` has succeeded.

Partial is acceptable only as an explicit diagnostic outcome. When partial, the final answer must include which roles/files are missing or invalid, what the model already tried, and what the user can change.

## Diagnostics

Tool results include stronger `assistant_hint` values:

- Discovery with no CSV candidates tells the assistant to ask for a directory containing first-level CSV files.
- Ingest with no imports summarizes skipped selections and asks the assistant to fix selection, role mapping, or path issues.
- Validation failure returns role/file details that the assistant should surface.

## Safety

- The agent never reads external source files directly.
- `data.discover_source_files` remains read-only and bounded.
- `data.ingest` remains the only workspace-writing data load action.
- Existing approval behavior for workspace modification is preserved.
