## Design

`data.discover_source_files` scans only the first level of a configured absolute directory. It returns candidate entries with filename, path, size, extension, mtime, skipped status, CSV headers, and preview text. Small CSV files are fully previewed up to a bounded byte limit; larger files return a truncated preview.

`data.ingest` no longer scans by itself. It accepts `selected_files`, each carrying a source path, assigned business role, and LLM reason. The backend validates that every selected path is a direct child of the selected source directory and is a CSV file before copying it into the workspace.

The UI can call discover directly for transparency, but natural-language loading remains message-first: agents call discover, reason over results, then call ingest.

## Safety

- Source files are never modified.
- Subdirectories are not scanned or imported.
- Non-CSV files are visible only as skipped metadata.
- Directory traversal and paths outside the discovered source directory are rejected.
- Workspace remains the project fact source after import.
