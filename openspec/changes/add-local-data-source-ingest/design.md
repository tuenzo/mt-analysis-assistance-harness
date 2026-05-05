## Design

The backend owns all filesystem access. A project stores an optional `data_source_path`, which is treated as a user-approved local directory. Ingest copies CSV files into the project workspace and never modifies source files.

`ProjectService` exposes shared file registration helpers so multipart upload and local directory ingest both create `ProjectFile` rows, compute checksums, update project status, refresh the project manifest, and refresh the context summary.

`business_analysis` keeps a single external tool surface. The agent calls `data.ingest` with either no source path, meaning use the saved project source, or a temporary absolute `source_path`. The action remains Level 3 (`modify_workspace`) and is high risk when invoked through the gateway.

## Data Flow

1. User saves a local absolute directory on the project.
2. UI or agent triggers ingest.
3. Backend scans only first-level `.csv` files.
4. Each CSV is copied to `data/raw/`; name collisions receive a stable `__N` suffix.
5. DB `project_files`, manifest, and context summary are updated.
6. The response lists imported and skipped files with role guesses and checksums.

## Constraints

- No recursive scanning.
- No source file mutation.
- Only CSV files are imported in this change.
- Project workspace remains the fact source after import.
