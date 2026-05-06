## Why

MVP 0 is broadly implemented as a runnable harness, but the next blocker is that `panel.build_category_day` still behaves like an early mock: it uses hand-rolled CSV aggregation, narrow column assumptions, and weak output metadata. The reference project at `E:\CodingProject\meituancomp` already has a stronger pandas-based panel builder and validation practice that we can adapt without changing this harness architecture.

## What Changes

- Upgrade `panel.build_category_day` to build a real balanced category-day panel from workspace CSV files.
- Add schema inference and validation logic that recognizes common order, exposure, and activity column aliases.
- Preserve existing JSON output compatibility for downstream diagnostics/localgap while also writing CSV and summary artifacts.
- Use the reference project's good practices: pandas parsing, role-specific standardization, compact date support, activity date expansion, and summary metadata.
- Add focused tests that exercise upload-style simple CSVs and reference-style aliased CSVs.

## Capabilities

### New Capabilities
- `real-category-day-panel`: CSV schema inference, validation, and real category-day panel construction for the analysis pipeline.

### Modified Capabilities
- `business-analysis-system`: MVP 1 data intake acceptance now requires real panel output artifacts rather than mock-only aggregation.

## Impact

- Modified: `backend/requirements.txt`
- Modified: `backend/app/analysis/pipelines/build_panel.py`
- Modified: `backend/app/tools/data_tools.py`
- Modified: `backend/app/tests/test_build_panel.py`
- Modified: `backend/app/tests/test_validate.py`
- Validation: backend pytest, frontend build smoke if frontend files remain untouched.
