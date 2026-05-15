## 1. OpenSpec And Contracts

- [x] 1.1 Create OpenSpec change artifacts for the quality scoring and hardening slice.
- [x] 1.2 Validate the OpenSpec change.

## 2. Quality Tools

- [x] 2.1 Add `quality.audit_lineage` and `quality.score_reference_alignment` actions, permissions, and registry wiring.
- [x] 2.2 Implement lineage checks for DB/workspace/manifest/source-role consistency and demo contamination.
- [x] 2.3 Implement reference alignment scoring with caps, sub-scores, JSON artifact, and CSV diff artifact.

## 3. Pipeline And Data Hardening

- [x] 3.1 Anchor default SQLite resolution at the repository root while preserving explicit `APP_DATABASE_URL`.
- [x] 3.2 Harden source discovery/ingest against processed-panel-as-raw-role mistakes.
- [x] 3.3 Make the approved full pipeline fail fast after validation or panel blocking failures.
- [x] 3.4 Require usable analysis evidence before dashboard PNG rendering.

## 4. Verification

- [x] 4.1 Add pytest coverage for demo-contamination scoring caps.
- [x] 4.2 Add pytest coverage for realdata mis-role/missing-source-role scoring caps.
- [x] 4.3 Add pytest coverage for pipeline fail-fast, dashboard evidence gate, ingest role protection, and stable DB path.
- [x] 4.4 Run targeted pytest, OpenSpec validation, and broader backend checks as time allows.
