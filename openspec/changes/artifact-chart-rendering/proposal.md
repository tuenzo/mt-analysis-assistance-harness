# Proposal: Artifact Content API and Chart Rendering

## Why

The dashboard can list registered artifacts but cannot read their content. Chart artifacts are currently saved as JSON files, so users see file names rather than the actual evidence visuals.

## What Changes

- Add project-scoped artifact metadata and content read endpoints.
- Return artifact content as structured JSON, text, or base64 for future binary/image artifacts.
- Add a frontend chart artifact renderer for current JSON chart payloads.
- Surface chart evidence directly on the dashboard while preserving artifact provenance.

## Non-Goals

- Server-side PNG rendering and image artifact registration are left for a follow-up export step.
- This change does not replace the existing JSON chart artifact format.
