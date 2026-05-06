# Design

## Backend

Add project-scoped artifact read endpoints under `/api/projects/{project_id}/artifacts`.

- `GET /api/projects/{project_id}/artifacts/{artifact_id}` returns registered artifact metadata.
- `GET /api/projects/{project_id}/artifacts/{artifact_id}/content` reads the file inside the project workspace.
- `GET /api/projects/{project_id}/artifacts/content?path=...` reads a workspace-relative artifact path for file-backed previews.

Content is encoded by file type:

- JSON files parse into `encoding=json` and `data=<object>`.
- Text files return `encoding=text`.
- Binary files return `encoding=base64`, preserving future support for `image/png`.

All reads must resolve within the project workspace to prevent path traversal.

## Frontend

The dashboard filters chart artifacts and reads their content through the new API. Supported chart payloads are rendered with local SVG/CSS primitives:

- `line` for GMV trend.
- `bar` for LocalGap and activity comparison.
- `pie`/distribution payloads as share bars with legend.

The renderer shows provenance metadata and limitations next to the visual rather than presenting charts as standalone proof.
